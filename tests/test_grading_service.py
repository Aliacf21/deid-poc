import unittest
import json
import socketserver
import threading
import time
import requests
from unittest.mock import patch, MagicMock
from server import RAGRequestHandler

PORT = 8002 # Use distinct port
SERVER_URL = f"http://localhost:{PORT}"

class MockServer(socketserver.TCPServer):
    allow_reuse_address = True

class TestGradingService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockServer(("localhost", PORT), RAGRequestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    @patch('server.RAGRequestHandler.grade_answer')
    def test_grade_success(self, mock_grade):
        mock_output = json.dumps({
            "reasoning_trace": "Student thought X",
            "feedback": "Good job."
        })
        mock_grade.return_value = mock_output
        
        payload = {
            "user_answer": "It is X.",
            "expert_context": "It is Y.",
            "phase_name": "Phase 1"
        }
        
        response = requests.post(f"{SERVER_URL}/grade", json=payload)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["feedback"], "Good job.")
        mock_grade.assert_called_once()

    def test_grade_missing_answer(self):
        response = requests.post(f"{SERVER_URL}/grade", json={"expert_context": "..."})
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()

