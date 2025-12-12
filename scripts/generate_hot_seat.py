import os
import re
import json
import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import sys

# Add parent directory to path to allow importing utils
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from scripts.utils import parse_srt

load_dotenv()

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# ---------------------------------------------------------
#  IMPROVED SCHEMA (PYDANTIC)
# ---------------------------------------------------------
# We use Pydantic here because it allows us to add 'description' metadata 
# to fields, which acts as a secondary prompt for the model.

class DiagnosticStop(BaseModel):
    sequence_id: int
    title: str = Field(description="A catchy title for this clinical pivot point (e.g., 'The Negative Workup')")
    stop_timestamp_seconds: int = Field(description="The exact second AFTER Seth finishes presenting data but IMMEDIATELY BEFORE Eileen starts analyzing it.")
    resume_timestamp_seconds: int = Field(description="The exact second Eileen begins her expert analysis.")
    question_for_trainee: str = Field(description="A specific question challenging the trainee's differential diagnosis based on the new data.")
    novice_trap: str = Field(description="System 1 thinking: What is the obvious, reflex answer that is likely wrong? (e.g. 'Anchoring on travel history').")
    expert_insight: str = Field(description="System 2 thinking: The nuanced clinical principle the expert uses (e.g. 'Recognizing malignancy mimickers').")
    expert_quote_verbatim: str = Field(description="The direct quote from the transcript where the expert explains the insight. MUST correct ASR errors (e.g. 'birkhold area' -> 'Burkholderia').")
    suggested_visual: str = Field(description="Description of a specific medical image or scan to show during the pause (e.g., 'CT Chest showing halo sign').")

class SimulationOutput(BaseModel):
    case_summary: str
    stops: list[DiagnosticStop]

# ---------------------------------------------------------
#  GENERATION
# ---------------------------------------------------------
def generate_simulation(transcript_text):
    # UPGRADE: Switching to Gemini 2.5 Pro for superior instruction following and reasoning
    print("Initializing Gemini 2.5 Pro model...", flush=True)
    model = genai.GenerativeModel('gemini-2.5-pro') 
    
    # IMPROVED PROMPT: Role-based with explicit speaker definition and cognitive rules
    prompt = f"""
    ### ROLE
    You are a master Clinical Educator conducting a "Clinical Pathological Case" (CPC) simulation. Your goal is to train medical residents in diagnostic reasoning.

    ### CONTEXT & SPEAKERS
    - **The Presenter (Seth):** He presents the patient history, labs, and imaging.
    - **The Expert (Eileen):** She analyzes the data and provides the differential diagnosis.
    - **The Task:** You must identify the exact moments to **PAUSE** the case (stops) to challenge the learner.

    ### INPUT TRANSCRIPT
    {transcript_text}

    ### INSTRUCTIONS FOR STOPS (CRITICAL)
    You must generate exactly 3-4 "Diagnostic Stops" based on the flow of information.
    1. **The Cliffhanger Rule:** The `stop_timestamp_seconds` must be exactly when the data presentation ends, BEFORE the expert (Eileen) or the diagnosis is revealed.
    2. **Resume Timing:** `resume_timestamp_seconds` is when Eileen begins her analysis.
    3. **Novice vs. Expert:**
       - `novice_trap`: Identify "System 1" thinking—what is the obvious, reflex answer that is likely wrong or incomplete? (e.g., "Anchoring on the travel history to Asia").
       - `expert_insight`: Identify "System 2" thinking—what underlying principle is the expert using? (e.g., "The expert reframes the case from 'infection' to 'mimicker' due to the negative cultures").

    ### FORMATTING RULES
    1. **ASR Correction:** The transcript contains errors (e.g., "birkhold area" -> "Burkholderia", "ashpazi" -> "Ashkenazi"). You **MUST** correct these medical terms in your `expert_quote_verbatim` and text outputs.
    2. **Timestamps:** Use the embedded [T=Seconds] markers to find the exact cut points.
    3. **Visuals:** For `suggested_visual`, request a specific medical illustration or radiology scan type that matches the current context.
    4. **Completeness:** You MUST provide non-empty values for ALL fields in the schema, including `expert_quote_verbatim`.

    ### OUTPUT
    Return strictly valid JSON matching the SimulationOutput schema.
    """

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=SimulationOutput, # Passing the Pydantic class
                temperature=0.2 # Low temperature for factual precision
            )
        )
        return response.text
    except Exception as e:
        print(f"Error: {e}")
        return None

# ---------------------------------------------------------
#  MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == "__main__":
    file_name = "data/requested_transcript.en.srt" 
    print("Parsing SRT...", flush=True)
    text_data = parse_srt(file_name)
    
    if text_data:
        print(f"Transcript length: {len(text_data)} chars", flush=True)
        print("Analyzing Clinical Reasoning with Gemini Pro...", flush=True)
        json_result = generate_simulation(text_data)
        
        if json_result:
            # Clean up markdown if present (Flash/Pro sometimes add code blocks)
            cleaned_result = json_result.strip()
            if cleaned_result.startswith("```json"):
                cleaned_result = cleaned_result[7:]
            if cleaned_result.startswith("```"):
                cleaned_result = cleaned_result[3:]
            if cleaned_result.endswith("```"):
                cleaned_result = cleaned_result[:-3]
            
            cleaned_result = cleaned_result.strip()

            # Save to file
            with open("data/simulation_data.json", "w") as f:
                f.write(cleaned_result)
            print("Success! Simulation data saved to data/simulation_data.json")
            
            # Preview for User
            try:
                data = json.loads(cleaned_result)
                print(f"\nCase Summary: {data.get('case_summary')}\n")
                for stop in data.get('stops', []):
                    print(f"--- Node {stop.get('sequence_id', 'N/A')}: {stop.get('title', 'No Title')} ---")
                    print(f"Stop: {stop.get('stop_timestamp_seconds', 'N/A')}s | Resume: {stop.get('resume_timestamp_seconds', 'N/A')}s")
                    print(f"Trap: {stop.get('novice_trap', 'N/A')}")
                    print(f"Insight: {stop.get('expert_insight', 'N/A')}")
                    print(f"Corrected Quote: \"{stop.get('expert_quote_verbatim', 'N/A')[:100]}...\"")
                    print("-" * 30)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                print("Full response saved to simulation_data.json for inspection.")
