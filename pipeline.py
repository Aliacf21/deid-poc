import os
import time
import yt_dlp
import azure.cognitiveservices.speech as speechsdk
from azure.health.deidentification import DeidentificationClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def download_audio(youtube_url, output_filename="downloaded_audio"):
    """
    Downloads audio from a YouTube video using yt-dlp.
    """
    print(f"Downloading audio from {youtube_url}...")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'outtmpl': output_filename,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        
        final_filename = f"{output_filename}.wav"
        if os.path.exists(final_filename):
            print(f"Audio downloaded to {final_filename}")
            return final_filename
        else:
            print("Download completed but file check failed. Checking directory...")
            for file in os.listdir("."):
                if file.startswith(output_filename) and file.endswith(".wav"):
                    return file
            raise Exception("Audio file not found after download.")
            
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None

def transcribe_audio(audio_filename, speech_key, speech_region):
    """
    Transcribes audio file to text using Azure Speech Service.
    """
    print(f"Transcribing {audio_filename}...")
    
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.speech_recognition_language="en-US"
    
    audio_config = speechsdk.audio.AudioConfig(filename=audio_filename)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    done = False
    transcript = []

    def stop_cb(evt):
        print('CLOSING on {}'.format(evt))
        nonlocal done
        done = True

    def recognized_cb(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            # print(f"RECOGNIZED: {evt.result.text}")
            transcript.append(evt.result.text)
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            print("No speech could be recognized: {}".format(evt.result.no_match_details))

    speech_recognizer.recognized.connect(recognized_cb)
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    speech_recognizer.start_continuous_recognition()
    
    while not done:
        time.sleep(.5)

    speech_recognizer.stop_continuous_recognition()
    
    full_text = " ".join(transcript)
    return full_text

def redact_phi(text, deid_service_endpoint):
    """
    Redacts PHI from text using Azure Health Data Services De-identification Service.
    """
    print("Redacting PHI from transcript using Azure Health De-identification Service...")
    
    # Use DefaultAzureCredential which supports AZ CLI login, Environment Vars, etc.
    credential = DefaultAzureCredential()
    
    client = DeidentificationClient(endpoint=deid_service_endpoint, credential=credential)

    try:
        # The service processes text. Check documentation for max length.
        # Assuming we pass the whole text or chunk it. 
        # For preview, let's keep it simple.
        
        response = client.deidentify_text(
            body={"inputText": text, "operation": "Redact"}
        )
        
        # The response structure depends on the service version.
        # Usually returns { "outputText": "..." }
        
        return response.output_text

    except Exception as e:
        print(f"Error during redaction: {e}")
        return text

def main():
    # Configuration
    YOUTUBE_URL = "https://www.youtube.com/watch?v=IrCmLrUXdmo"
    
    # Get credentials
    SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
    SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
    DEID_SERVICE_ENDPOINT = os.getenv("AZURE_DEID_SERVICE_ENDPOINT")

    if not all([SPEECH_KEY, SPEECH_REGION, DEID_SERVICE_ENDPOINT]):
        print("Missing Azure credentials. Please check .env file.")
        print("Required: AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, AZURE_DEID_SERVICE_ENDPOINT")
        return

    print("Starting Pipeline...")

    # 1. Download Audio
    audio_file = download_audio(YOUTUBE_URL)
    if not audio_file:
        return

    # 2. Transcribe
    transcript = transcribe_audio(audio_file, SPEECH_KEY, SPEECH_REGION)
    print(f"\nTranscript Length: {len(transcript)} characters")
    
    with open("transcript_original.txt", "w") as f:
        f.write(transcript)

    # 3. De-identify
    # Note: Ensure you are logged in via 'az login' or have Service Principal env vars set for DefaultAzureCredential
    redacted_transcript = redact_phi(transcript, DEID_SERVICE_ENDPOINT)
    
    print("\n--- Redacted Transcript Sample ---\n")
    print(redacted_transcript[:500] + "..." if len(redacted_transcript) > 500 else redacted_transcript)

    with open("transcript_redacted.txt", "w") as f:
        f.write(redacted_transcript)
        
    print("\nPipeline completed. Files saved: transcript_original.txt, transcript_redacted.txt")

if __name__ == "__main__":
    main()
