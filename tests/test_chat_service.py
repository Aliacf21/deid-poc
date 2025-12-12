import unittest
import json
import socketserver
import threading
import time
import requests
from unittest.mock import patch, MagicMock
from server import RAGRequestHandler

# Mock server setup
PORT = 8001
SERVER_URL = f"http://localhost:{PORT}"

class MockServer(socketserver.TCPServer):
    allow_reuse_address = True

class TestChatService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockServer(("localhost", PORT), RAGRequestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.1) # Wait for startup

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    @patch('server.RAGRequestHandler.query_gemini')
    def test_chat_success(self, mock_gemini):
        mock_gemini.return_value = "This is a mocked response."
        
        response = requests.post(f"{SERVER_URL}/chat", json={"message": "Test question"})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"reply": "This is a mocked response."})
        mock_gemini.assert_called_once()

    def test_chat_missing_message(self):
        response = requests.post(f"{SERVER_URL}/chat", json={})
        self.assertEqual(response.status_code, 400)

    @patch('server.RAGRequestHandler.query_gemini')
    def test_chat_internal_error(self, mock_gemini):
        mock_gemini.side_effect = Exception("Gemini Error")
        
        response = requests.post(f"{SERVER_URL}/chat", json={"message": "Crash me"})
        self.assertEqual(response.status_code, 500)
        self.assertIn("Gemini Error", response.json()["error"])

if __name__ == '__main__':
    unittest.main()

