import os
import re
import json
import typing_extensions
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

# ---------------------------------------------------------
#  IMPROVED SCHEMA
# ---------------------------------------------------------

class DiagnosticStop(typing_extensions.TypedDict):
    sequence_id: int
    title: str # e.g., "The Negative Workup"
    stop_timestamp_seconds: int # Time to PAUSE video/text
    resume_timestamp_seconds: int # Time to PLAY explanation
    question_for_trainee: str
    novice_trap: str # e.g., "Novices will likely anchor on the travel history to Asia."
    expert_insight: str # e.g., "The expert recognizes that angio-invasive patterns exist in malignancy too."
    expert_quote_verbatim: str # The direct quote from the transcript
    suggested_visual: str

class SimulationOutput(typing_extensions.TypedDict):
    case_summary: str
    stops: list[DiagnosticStop]

# ---------------------------------------------------------
#  PARSING LOGIC
# ---------------------------------------------------------
def parse_srt(file_path):
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regex to grab sequence, timestamp, and text
    pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:(?!\n\n).)*)', re.DOTALL)
    matches = pattern.findall(content)
    
    formatted_transcript = ""
    for match in matches:
        start_time_str = match[1]
        # Clean text: remove newlines within a subtitle block
        text_content = match[3].replace('\n', ' ').strip()
        
        # Convert H:M:S,ms to total seconds (integer is usually fine for simulated stops)
        h, m, s = start_time_str.replace(',', '.').split(':')
        total_seconds = int(int(h) * 3600 + int(m) * 60 + float(s))
        
        # Embedding the timestamp explicitly so the LLM can "see" time
        formatted_transcript += f"[T={total_seconds}] {text_content} "
    
    return formatted_transcript

# ---------------------------------------------------------
#  GENERATION
# ---------------------------------------------------------
def generate_simulation(transcript_text):
    # Use Flash for speed/context window, or Pro for better reasoning. 
    # For extraction tasks, 1.5 Pro is usually superior.
    model = genai.GenerativeModel('gemini-2.5-pro') 
    
    # We used the prompt defined in the section above
    prompt = f"""
    ### ROLE
    You are a Clinical Educator creating a "Hot Seat" simulation from a medical transcript.

    ### INPUT TRANSCRIPT
    {transcript_text}

    ### TASK
    Create a JSON object containing 3 specific "Decision Nodes" where the user must answer a question before proceeding.

    ### GUIDELINES
    1. **Stop Timing**: The `stop_timestamp_seconds` must be exactly when the data presentation ends, BEFORE the expert (Eileen) or the diagnosis is revealed.
    2. **Resume Timing**: The `resume_timestamp_seconds` is when the expert starts explaining their thought process.
    3. **Quotes**: `expert_quote_verbatim` must be an exact string match from the transcript.
    4. **Reasoning**: Contrast the `novice_trap` (common errors) with `expert_insight` (the correct mental model).

    ### OUTPUT
    Return strictly valid JSON matching the SimulationOutput schema.
    """

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=SimulationOutput
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
    file_name = "requested_transcript.en.srt" # Ensure this matches your file
    print("Parsing SRT...")
    text_data = parse_srt(file_name)
    
    if text_data:
        print("Analyzing Clinical Reasoning (this may take a moment)...")
        json_result = generate_simulation(text_data)
        
        if json_result:
            # Save to file
            with open("simulation_data.json", "w") as f:
                f.write(json_result)
            print("Success! Simulation data saved to simulation_data.json")
            
            # Preview for User
            data = json.loads(json_result)
            print(f"\nCase: {data.get('case_summary')}\n")
            for stop in data.get('stops', []):
                print(f"--- Node {stop['sequence_id']}: {stop['title']} ---")
                print(f"Stop Video At: {stop['stop_timestamp_seconds']}s")
                print(f"Question: {stop['question_for_trainee']}")
                print(f"Expert Quote: \"{stop['expert_quote_verbatim'][:100]}...\"")
                print("-" * 30)
