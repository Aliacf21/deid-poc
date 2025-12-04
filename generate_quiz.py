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
    print("Warning: GOOGLE_API_KEY not found in environment variables.")
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

def generate_quiz_with_gemini_optimized(full_transcript_text):
    # Using 'gemini-2.5-pro' as it is available and supports high reasoning.
    model_name = 'gemini-2.5-pro' 
    
    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        print(f"Error initializing model '{model_name}': {e}")
        return None

    # Optimized Prompt for Senior Fellows / Board Review
    prompt = f"""
### ROLE
You are a Senior Item Writer for the American Board of Internal Medicine (ABIM), specifically for the Infectious Disease and Oncology sub-specialty boards. Your audience consists of Senior Fellows who are already experts. 
* **Do not** test them on basic definitions. 
* **Test them** on nuance, clinical judgment, managing uncertainty, and third-order reasoning (why a specific rule-out occurred).

### INPUT CONTEXT
The provided transcript is a Grand Rounds presentation regarding "The Great Mimicker" (Angiosarcoma) and its confusion with infectious etiologies (Bartonella, Brucella, Syphilis, Fungal, Mycobacterial).

**TRANSCRIPT:**
{full_transcript_text}

### INSTRUCTION: STEP-BY-STEP GENERATION

**STEP 1: META-COGNITIVE ANALYSIS (Internal Thought Process)**
Before writing questions, analyze the transcript to identify:
1.  **The "Red Herrings":** What specific clinical features pointed to infection but were actually malignancy? (e.g., The travel history to Israel suggesting Brucella, the cat exposure suggesting Bartonella).
2.  **The Differential Logic:** Why specifically were organisms like Nocardia, Syphilis, or Paragonimus ruled out? (Find the specific lab result or clinical reasoning in the text).
3.  **The Literature Pearls:** Extract specific data points from the cited cohorts (MD Anderson, Japanese cohort) regarding misdiagnosis rates.

**STEP 2: QUESTION GENERATION**
Generate 10 High-Stakes Board Review Questions in JSON format.

### QUESTION DESIGN GUIDELINES

1.  **Vignette-Based Stems:** Do not use phrases like "According to the transcript." Instead, simulate the clinical scenario described or a similar scenario derived from the literature review. 
    * *Bad:* "What did the speaker say about Bartonella?"
    * *Good:* "A patient with a history of cat exposure presents with lymphadenopathy and is initially diagnosed with Lymphoma. Based on the MD Anderson cohort discussed, which organism should be reconsidered?"

2.  **Distractor Engineering (Crucial):** * Distractors must be **clinically plausible** based on the transcript's differential.
    * Use the specific organisms discussed (e.g., Nocardia, Actinomyces, Syphilis, IgG4 disease) as distractors.
    * Avoid obvious wrong answers.

3.  **Rationale Requirement:** * The rationale must explain *why* the correct answer is right.
    * It must also explain *specifically why* the distractors are wrong based on the case facts provided in the transcript (e.g., "Brucella is incorrect because despite the travel to Israel and bone lesions, the serology was negative.").

### OUTPUT FORMAT
Return **ONLY** valid JSON.

{{
    "analysis_of_transcript": "A brief summary of the clinical logic, rule-outs, and key literature citations found in the text...",
    "questions": [
        {{
            "question_id": 1,
            "difficulty": "Fellowship-Level",
            "concept_tested": "Angiosarcoma Mimicry vs. Infectious Etiology",
            "question_text": "A 46-year-old male with a history of repaired right atrial pseudoaneurysm presents with new pulmonary nodules and cerebral lesions. He has extensive travel history to Israel and Southeast Asia. Initial workup for infectious etiologies is negative. Given the clinical progression described, which malignancy is known to specifically mimic this presentation of pericarditis and multifocal disease?",
            "options": [
                "Disseminated Nocardiosis",
                "Primary Cardiac Angiosarcoma",
                "Neuro-Brucellosis",
                "Lymphoma"
            ],
            "correct_option_index": 1,
            "explanation": "CORRECT: The case concludes with a diagnosis of Angiosarcoma, which mimicked pericarditis and multifocal infection. INCORRECT (A): Nocardia was considered due to brain/lung involvement but BAL was negative. INCORRECT (C): Brucella was high on the differential due to Israel travel and bone lesions, but serologies were negative.",
            "timestamp_reference": 1234
        }}
    ]
}}
"""

    # Gemini 1.5 Pro supports response_mime_type to ensure valid JSON
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
if __name__ == "__main__":
    input_file = 'requested_transcript.en.srt'
    print(f"Processing {input_file}...")
    
    transcript_text = parse_srt(input_file)
    
    if transcript_text and not transcript_text.startswith("Error"):
        print("Transcript parsed. Generating Senior Fellow Board Review Quiz...")
        json_output = generate_quiz_with_gemini_optimized(transcript_text)

        if json_output:
            print("Gemini Generation Complete.")
            
            # Save to file
            output_file = 'quiz_data.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"Quiz saved to {output_file}")
            
            # Optional: Print the analysis to show the CoT worked
            try:
                data = json.loads(json_output)
                print("\n--- AI Clinical Analysis ---")
                print(data.get("analysis_of_transcript", "No analysis found."))
            except json.JSONDecodeError:
                pass
        else:
            print("Failed to generate quiz.")
    else:
        print(transcript_text)