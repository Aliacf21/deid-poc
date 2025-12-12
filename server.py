import http.server
import socketserver
import json
import os
import re
import google.generativeai as genai
from dotenv import load_dotenv
from scripts.utils import parse_srt

# Load env vars
load_dotenv()
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

PORT = 8000

# Load transcript once at startup
TRANSCRIPT_TEXT = parse_srt('data/requested_transcript.en.srt')

class RAGRequestHandler(http.server.SimpleHTTPRequestHandler):
    def _rewrite_path(self):
        # Normalize path
        path = self.path.split('?', 1)[0]
        path = path.split('#', 1)[0]

        # Case 1: Data files (allow direct access to /data/)
        if path.startswith('/data/'):
            return # Serve directly from ./data/
            
        # Case 2: Legacy data file access (redirect to /data/)
        if path in ['/quiz_data.json', '/simulation_data.json']:
            self.path = '/data' + self.path
            return

        # Case 3: Root or explicit index
        if path == '/' or path == '/index.html':
            self.path = '/public/index.html'
            return

        # Case 4: Everything else -> Serve from /public/
        # (unless it already starts with /public/)
        if not path.startswith('/public/'):
            self.path = '/public' + self.path

    def do_GET(self):
        self._rewrite_path()
        return super().do_GET()

    def do_HEAD(self):
        self._rewrite_path()
        return super().do_HEAD()

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

