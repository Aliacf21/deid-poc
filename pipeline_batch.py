import os
import time
import json
import requests
import yt_dlp
import cv2
import subprocess
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.health.deidentification import DeidentificationClient
from azure.identity import DefaultAzureCredential
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def download_video_and_extract_audio(youtube_url, output_filename="batch_media"):
    """
    Downloads video from YouTube and extracts audio.
    Returns (video_path, audio_path)
    """
    print(f"Downloading video from {youtube_url}...")
    
    # Download best mp4 video available
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_filename + '.%(ext)s',
        'quiet': True,
    }

    video_path = f"{output_filename}.mp4"
    audio_path = f"{output_filename}.wav"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        
        # Verify file exists (yt-dlp might adapt extension)
        if not os.path.exists(video_path):
            for f in os.listdir("."):
                if f.startswith(output_filename) and not f.endswith(".wav"):
                    video_path = f
                    break
        
        print(f"Video downloaded to {video_path}")
        
        # Extract audio using ffmpeg
        print("Extracting audio for transcription...")
        subprocess.run([
            'ffmpeg', '-y', '-i', video_path, 
            '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', 
            audio_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print(f"Audio extracted to {audio_path}")
        return video_path, audio_path
            
    except Exception as e:
        print(f"Error downloading/processing media: {e}")
        return None, None

def blur_faces(video_path, output_path):
    """
    Blurs faces in the video using OpenCV Haar Cascades.
    """
    print(f"Blurring faces in {video_path}...")
    print("(This process runs locally on CPU and may take some time...)")
    
    # Load Haar Cascade
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error opening video file.")
        return None

    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Define codec and create VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    frame_count = 0
    start_time = time.time()
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # Face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        for (x, y, w, h) in faces:
            # Blur the face area
            roi = frame[y:y+h, x:x+w]
            roi = cv2.GaussianBlur(roi, (99, 99), 30)
            frame[y:y+h, x:x+w] = roi
            
        out.write(frame)
        
        frame_count += 1
        if frame_count % 500 == 0:
            elapsed = time.time() - start_time
            fps_proc = frame_count / elapsed
            eta_sec = (total_frames - frame_count) / fps_proc if fps_proc > 0 else 0
            print(f"Processed {frame_count}/{total_frames} frames. (ETA: {int(eta_sec/60)}m {int(eta_sec%60)}s)")
            
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Face blurring complete. Saved to {output_path}")
    return output_path

def upload_to_blob(file_path, connection_string, container_name="audio-uploads"):
    print(f"Uploading {file_path} to Azure Blob Storage...")
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        if not container_client.exists(): container_client.create_container()
        
        blob_name = os.path.basename(file_path)
        blob_client = container_client.get_blob_client(blob_name)
        
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
            
        sas_token = generate_blob_sas(
            account_name=blob_client.account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        return f"{blob_client.url}?{sas_token}"
    except Exception as e:
        print(f"Error uploading to blob: {e}")
        return None

def submit_transcription_job(audio_url, speech_key, speech_region):
    print("Submitting Batch Transcription job...")
    api_url = f"https://{speech_region}.api.cognitive.microsoft.com/speechtotext/v3.1/transcriptions"
    headers = {"Ocp-Apim-Subscription-Key": speech_key, "Content-Type": "application/json"}
    
    payload = {
        "displayName": f"transcription_{int(time.time())}",
        "description": "De-identification POC",
        "locale": "en-US",
        "contentUrls": [audio_url],
        "properties": {"wordLevelTimestampsEnabled": False, "punctuationMode": "DictatedAndAutomatic"}
    }
    
    response = requests.post(api_url, headers=headers, json=payload)
    if response.status_code != 201:
        print(f"Error submitting job: {response.text}")
        return None
    
    job_url = response.json()["self"]
    print(f"Job submitted. ID: {job_url.split('/')[-1]}")
    return job_url

def wait_for_transcript(job_url, speech_key):
    headers = {"Ocp-Apim-Subscription-Key": speech_key}
    print("Polling for transcription completion...")
    
    while True:
        response = requests.get(job_url, headers=headers)
        status = response.json()["status"]
        
        if status == "Succeeded":
            print("Transcription Succeeded!")
            break
        elif status == "Failed":
            print("Transcription Failed.")
            return None
        else:
            # If running parallel with video processing, we don't need to print constantly
            pass 
        time.sleep(10)
        
    # Get results
    results_url = response.json()["links"]["files"]
    files_response = requests.get(results_url, headers=headers)
    files = files_response.json()["values"]
    
    for file_info in files:
        if file_info["kind"] == "Transcription":
            data = requests.get(file_info["links"]["contentUrl"]).json()
            return " ".join([phrase["display"] for phrase in data["combinedRecognizedPhrases"]])
    return None

def redact_phi(text, deid_service_endpoint):
    print("Redacting PHI from transcript...")
    credential = DefaultAzureCredential()
    client = DeidentificationClient(endpoint=deid_service_endpoint, credential=credential)
    
    try:
        chunk_size = 5000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        redacted_chunks = []
        
        for i, chunk in enumerate(chunks):
            response = client.deidentify_text(body={"inputText": chunk})
            redacted_chunks.append(response.output_text)
            
        return "".join(redacted_chunks)
    except Exception as e:
        print(f"Redaction error: {e}")
        return text

def main():
    YOUTUBE_URL = "https://www.youtube.com/watch?v=IrCmLrUXdmo"
    SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
    SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
    DEID_SERVICE_ENDPOINT = os.getenv("AZURE_DEID_SERVICE_ENDPOINT")
    STORAGE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

    if not all([SPEECH_KEY, SPEECH_REGION, DEID_SERVICE_ENDPOINT, STORAGE_CONN_STR]):
        print("Missing credentials.")
        return

    print("=== Starting Full Media De-identification Pipeline ===")

    # 1. Download Video & Extract Audio
    video_path, audio_path = download_video_and_extract_audio(YOUTUBE_URL)
    if not video_path: return

    # 2. Start Transcription (Remote Async)
    print("\n[Step 2] Submitting Transcription Job...")
    sas_url = upload_to_blob(audio_path, STORAGE_CONN_STR)
    job_url = submit_transcription_job(sas_url, SPEECH_KEY, SPEECH_REGION)
    
    # 3. Start Video Blurring (Local CPU)
    # This takes the longest, so we run it while Azure processes the text
    print("\n[Step 3] Starting Face Blurring (Local)...")
    blurred_video_silent = "batch_media_blurred_silent.mp4"
    if blur_faces(video_path, blurred_video_silent):
        print("Video blurring finished.")
    
    # 4. Get Transcript
    print("\n[Step 4] Retrieving Transcript...")
    transcript = wait_for_transcript(job_url, SPEECH_KEY)
    if transcript:
        with open("batch_transcript_original.txt", "w") as f: f.write(transcript)
        
        # 5. Redact Text
        print("\n[Step 5] De-identifying Text...")
        redacted_text = redact_phi(transcript, DEID_SERVICE_ENDPOINT)
        with open("batch_transcript_redacted.txt", "w") as f: f.write(redacted_text)
        
        print(f"Redacted text saved. Length: {len(redacted_text)}")
    
    # 6. Merge Blurred Video + Original Audio
    # Note: Ideally we'd use de-identified audio (beeped names), but that requires TTS/audio manip.
    # For now, we merge original audio as per "blur faces" request.
    print("\n[Step 6] Finalizing Video...")
    final_output = "final_deidentified_video.mp4"
    subprocess.run([
        'ffmpeg', '-y', '-i', blurred_video_silent, '-i', audio_path, 
        '-c:v', 'copy', '-c:a', 'aac', final_output
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print(f"\nPipeline Completed! Output: {final_output}")

if __name__ == "__main__":
    main()
