import os
import re
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 1. Configure Gemini (Get API key from aistudio.google.com)
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    # Fallback or prompt user if not in env
    print("Warning: GOOGLE_API_KEY not found in environment variables.")
    # You might want to set it manually here for testing if not using .env
    # os.environ["GOOGLE_API_KEY"] = "YOUR_GOOGLE_API_KEY"
else:
    genai.configure(api_key=api_key)

def parse_srt(file_path):
    """
    Parses .srt file into a text string with embedded timestamps [T=123].
    """
    if not os.path.exists(file_path):
        return "Error: Transcript file not found."

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to find timestamp blocks
    pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:(?!\n\n).)*)', re.DOTALL)
    matches = pattern.findall(content)

    formatted_transcript = ""
    
    for match in matches:
        start_time_str = match[1]
        text_content = match[3].replace('\n', ' ').strip()
        
        # Convert HH:MM:SS,mmm to total seconds
        h, m, s = start_time_str.replace(',', '.').split(':')
        total_seconds = int(h) * 3600 + int(m) * 60 + float(s)
        
        # Append to a single massive string
        formatted_transcript += f"[T={int(total_seconds)}] {text_content} "
    
    return formatted_transcript

def generate_quiz_with_gemini_3(full_transcript_text):
    # 'gemini-1.5-pro' was not found in the list.
    # 'gemini-2.0-pro-exp' hit quota limits.
    # Trying 'gemini-2.5-pro' which is available in the model list and represents a high-tier reasoning model.
    model_name = 'gemini-2.5-pro' 
    
    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"Error initializing model '{model_name}': {e}")
        return None

    prompt = f"""
### ROLE

You are an expert Program Director for an Infectious Disease and Oncology Fellowship. 

Your goal is to create a high-stakes board review quiz based *strictly* on the provided transcript.

### INPUT CONTEXT

The transcript is a Grand Rounds presentation regarding "Great Mimickers" (infections mimicking malignancies and vice versa).

TRANSCRIPT:

{full_transcript_text}

### PRE-COMPUTATION (INTERNAL CHAIN OF THOUGHT)

Before generating the quiz, analyze the transcript to identify **High-Value Teaching Points**. 

Prioritize the following:

1.  **Complex Synthesis:** Cases requiring the combination of travel history + specific organ involvement (e.g., Israel + Neuro + Bone -> Brucellosis).

2.  **Literature Review:** Specific statistics or findings from the studies cited (e.g., The MD Anderson Bartonella study, the Stanford invasive mold study).

3.  **Counter-Intuitive Mimics:** "Lesser known" mimics highlighted by the speaker (e.g., Angiosarcoma presenting as Cellulitis).

### TASK

Generate 10 Multiple Choice Questions (JSON format) based on the analysis above.

### DIFFICULTY GUIDELINES

1.  **No Simple Recall:** Do not ask "What was the patient's job?". Ask "Given the patient's travel to [Region] and [Symptom], what is the primary differential?".

2.  **Plausible Distractors:** The wrong answers (options) must be clinically realistic "red herrings" mentioned in the differential diagnosis sections of the text.

3.  **Attribution:** The 'rationale' must explicitly reference *why* the answer is correct based on the speaker's specific comments or the literature cited.

### OUTPUT FORMAT

Return **ONLY** valid JSON. Do not include markdown formatting (like ```json). 

Do not output your "thinking" text separately; embed the reasoning into the "rationale" field.

Structure:

{{

    "questions": [

        {{

            "question": "Clinical vignette or literature-based question text",

            "options": ["Option A", "Option B", "Option C", "Option D"],

            "correctAnswer": "Option A",

            "rationale": "Deep explanation linking the clinical clues to the diagnosis, citing the specific study or logic from the transcript.",

            "timestamp": 123 // The integer second marker [T=123] closest to where this answer is discussed.

        }}

    ]

}}
"""

    # Gemini 1.5 Pro/Flash supports system instructions and response_mime_type
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return response.text
    except Exception as e:
        print(f"Error generating content: {e}")
        return None

# --- Execution ---
# Ensure you have your .srt file ready
if __name__ == "__main__":
    input_file = 'requested_transcript.en.srt'
    print(f"Processing {input_file}...")
    
    transcript_text = parse_srt(input_file)
    
    if transcript_text and not transcript_text.startswith("Error"):
        print("Transcript parsed. Generating quiz...")
        json_output = generate_quiz_with_gemini_3(transcript_text)

        if json_output:
            print("Gemini Generation Complete.")
            
            # Save to file
            output_file = 'quiz_data.json'
            with open(output_file, 'w') as f:
                f.write(json_output)
            print(f"Quiz saved to {output_file}")
        else:
            print("Failed to generate quiz.")
    else:
        print(transcript_text)

