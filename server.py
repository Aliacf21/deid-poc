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
                print(f"Error processing request: {e}")
                self._send_response(500, {"error": str(e)})
        else:
            self.send_error(404, "Endpoint not found")

    def _send_response(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

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

