import os
import json
import requests
from azure.health.deidentification import DeidentificationClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def redact_phi(text, deid_service_endpoint):
    """
    Redacts PHI from text using Azure Health Data Services De-identification Service.
    """
    print("Redacting PHI from transcript using Azure Health De-identification Service...")
    
    credential = DefaultAzureCredential()
    client = DeidentificationClient(endpoint=deid_service_endpoint, credential=credential)

    try:
        # Chunking logic
        chunk_size = 5000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        redacted_chunks = []
        
        print(f"Processing {len(chunks)} chunks...")
        
        for i, chunk in enumerate(chunks):
            response = client.deidentify_text(body={"inputText": chunk})
            redacted_chunks.append(response.output_text)
            print(f"Chunk {i+1}/{len(chunks)} processed.")
            
        return "".join(redacted_chunks)

    except Exception as e:
        print(f"Error during redaction: {e}")
        return text

def main():
    DEID_SERVICE_ENDPOINT = os.getenv("AZURE_DEID_SERVICE_ENDPOINT")
    
    # 1. Download the JSON directly from the known URL
    # (This URL is valid for 48 hours)
    transcript_url = "https://spsvcprodeus.blob.core.windows.net/bestor-c6e3ae79-1b48-41bf-92ff-940bea3e5c2d/TranscriptionData/8a3515e4-783c-4c6e-94b8-7f4c68185671_0_0.json?skoid=50c6251a-ac54-47a3-9265-a1e4f84be9b9&sktid=33e01921-4d64-4f8c-a055-5bdaffd5e33d&skt=2025-12-03T16%3A32%3A12Z&ske=2025-12-08T16%3A37%3A12Z&sks=b&skv=2021-08-06&sv=2025-01-05&st=2025-12-03T16%3A32%3A12Z&se=2025-12-04T04%3A37%3A12Z&sr=b&sp=rl&sig=eTXa1INgGjGC4h1FCyXFAXxjY8URi5%2FHK%2BbygK4YPps%3D"
    
    print("Downloading transcript JSON...")
    response = requests.get(transcript_url)
    data = response.json()
    
    # 2. Parse it with fixed logic
    print("Parsing transcript...")
    full_text = ""
    
    # Try accessing 'combinedRecognizedPhrases'
    if "combinedRecognizedPhrases" in data:
        phrases = data["combinedRecognizedPhrases"]
        # Check structure of first phrase
        if len(phrases) > 0:
            first = phrases[0]
            if "display" in first:
                # Structure A: direct access
                full_text = " ".join([p["display"] for p in phrases])
            elif "nBest" in first:
                # Structure B: nBest list
                full_text = " ".join([p["nBest"][0]["display"] for p in phrases])
            else:
                print("Unknown structure in combinedRecognizedPhrases. Keys:", first.keys())
                return
    else:
        print("No combinedRecognizedPhrases found.")
        return

    print(f"\nTranscript Length: {len(full_text)} characters")
    
    with open("batch_transcript_original.txt", "w") as f:
        f.write(full_text)

    # 3. De-identify
    redacted_transcript = redact_phi(full_text, DEID_SERVICE_ENDPOINT)
    
    print("\n--- Redacted Transcript Sample ---\n")
    print(redacted_transcript[:500] + "..." if len(redacted_transcript) > 500 else redacted_transcript)

    with open("batch_transcript_redacted.txt", "w") as f:
        f.write(redacted_transcript)
        
    print("\nRecovery completed. Files saved: batch_transcript_original.txt, batch_transcript_redacted.txt")

if __name__ == "__main__":
    main()

