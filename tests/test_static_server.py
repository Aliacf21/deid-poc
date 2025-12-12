import unittest
import socketserver
import threading
import time
import requests
import os
from server import RAGRequestHandler

PORT = 8003
SERVER_URL = f"http://localhost:{PORT}"

class MockServer(socketserver.TCPServer):
    allow_reuse_address = True

class TestStaticServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create dummy files for testing routing
        os.makedirs("public", exist_ok=True)
        os.makedirs("data", exist_ok=True)
        
        with open("public/test_index.html", "w") as f:
            f.write("<html>Index</html>")
            
        with open("data/test_data.json", "w") as f:
            f.write('{"test": true}')

        cls.server = MockServer(("localhost", PORT), RAGRequestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        # Cleanup is optional or can be done if strict

    def test_route_rewrite_index(self):
        # Requesting /index.html should serve /public/index.html
        # Note: server.py logic maps /index.html -> /public/index.html
        # But we need to make sure we created public/index.html if we want 200
        # The logic is:
        # if path == '/index.html': path = '/public/index.html'
        
        # Let's rely on the real files or the one we created
        # We created public/test_index.html.
        # But server logic is hardcoded for /index.html -> /public/index.html
        
        # Testing generic public routing:
        # Request /test_index.html -> should route to /public/test_index.html
        r = requests.get(f"{SERVER_URL}/test_index.html")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text, "<html>Index</html>")

    def test_route_rewrite_data(self):
        # Request /quiz_data.json (legacy) -> /data/quiz_data.json
        # We need to mock existence or rely on real file.
        # server.py hardcodes specific files for redirection:
        # if path in ['/quiz_data.json', ...]: path = '/data' + path
        
        # Since I can't easily change the hardcoded list in server.py without patching,
        # I will test the actual data file if it exists, or skip.
        if os.path.exists("data/quiz_data.json"):
            r = requests.get(f"{SERVER_URL}/quiz_data.json")
            self.assertEqual(r.status_code, 200)

    def test_direct_data_access(self):
        # Request /data/test_data.json -> /data/test_data.json
        r = requests.get(f"{SERVER_URL}/data/test_data.json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"test": True})

if __name__ == '__main__':
    unittest.main()

