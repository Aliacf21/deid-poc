import http.server
import socketserver
import json
import os
import re
import google.generativeai as genai
from dotenv import load_dotenv

# Load env vars
load_dotenv()
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

PORT = 8000

def parse_srt(file_path):
    if not os.path.exists(file_path):
        return ""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Regex to keep timestamps for context if needed, or just raw text.
    # For RAG, keeping [T=123] markers in the text helps the LLM cite sources.
    pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:(?!\n\n).)*)', re.DOTALL)
    matches = pattern.findall(content)
    formatted_transcript = ""
    for match in matches:
        start_time_str = match[1]
        text_content = match[3].replace('\n', ' ').strip()
        
        # Convert HH:MM:SS,mmm to total seconds for reference
        h, m, s = start_time_str.replace(',', '.').split(':')
        total_seconds = int(int(h) * 3600 + int(m) * 60 + float(s))
        
        formatted_transcript += f"[T={total_seconds}] {text_content} "
    return formatted_transcript

# Load transcript once at startup
TRANSCRIPT_TEXT = parse_srt('requested_transcript.en.srt')

class RAGRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/chat':
            self.handle_chat()
        elif self.path == '/grade':
            self.handle_grading()
        else:
            self.send_error(404, "Endpoint not found")

    def handle_chat(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            user_query = data.get('message', '')
            
            if not user_query:
                self._send_response(400, {"error": "No message provided"})
                return

            # Call Gemini
            response_text = self.query_gemini(user_query)
            self._send_response(200, {"reply": response_text})

        except Exception as e:
            print(f"Error processing chat: {e}")
            self._send_response(500, {"error": str(e)})

    def handle_grading(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
            user_answer = data.get('user_answer', '')
            expert_context = data.get('expert_context', '')
            phase_name = data.get('phase_name', 'Unknown Phase')
            novice_trap = data.get('novice_trap', '')
            
            if not user_answer:
                self._send_response(400, {"error": "No answer provided"})
                return

            # Call Gemini for Grading
            grading_json = self.grade_answer(user_answer, expert_context, phase_name, novice_trap)
            self._send_response(200, json.loads(grading_json))

        except Exception as e:
            print(f"Error processing grading: {e}")
            self._send_response(500, {"error": str(e)})

    def _send_response(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def grade_answer(self, user_answer, expert_context, phase_name, novice_trap=None):
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        trap_warning = ""
        if novice_trap:
            trap_warning = f"### COMMON NOVICE ERROR (Did they fall for this?):\n{novice_trap}\n"

        prompt = f"""
### ROLE
You are a master clinician (Senior Attending) grading a Fellow during a complex "Morning Report" case.
The case is a diagnostic mystery. Your goal is to provide Socratic feedback on the Fellow's *reasoning process*.

### CASE PHASE: {phase_name}

### EXPERT'S THINKING (Gold Standard):
"{expert_context}"

{trap_warning}

### FELLOW'S ANSWER:
"{user_answer}"

### INSTRUCTIONS
- Do NOT assign a numerical score.
- Compare the Fellow's logic to the Expert's.
- Be Socratic. Start with a compliment on what they got right, then pivot to the gap.
- If they fell into the "Novice Trap", gently point it out.

### OUTPUT FORMAT (JSON ONLY)
{{
    "reasoning_trace": "Internal thought: User suggested X. Expert suggested Y...",
    "feedback": "<string>"
}}
"""
        try:
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return response.text
        except Exception as e:
            return json.dumps({"feedback": f"Error processing feedback: {e}"})

    def query_gemini(self, query):
        # Using the available Pro model found earlier
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        prompt = f"""
### ROLE
You are the medical expert speaker from the provided transcript. 
You are answering questions from a fellow physician or resident in a "Grand Rounds" Q&A session.

### TRANSCRIPT
{TRANSCRIPT_TEXT}

### INSTRUCTIONS
1. Answer the user's question based **STRICTLY** on the transcript provided.
2. If the answer is not in the transcript, politely state that you did not cover that in this specific lecture.
3. **CRITICAL:** Cite the timestamp using the format `[T=123]` exactly as it appears in the transcript text when referencing specific facts. This allows the UI to link to the video.
4. Keep answers concise and high-yield.

### USER QUESTION
{query}
"""
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"I'm sorry, I encountered an error connecting to the AI service: {e}"

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), RAGRequestHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print("Chatbot backend ready.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()

