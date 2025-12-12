import unittest
import json
import os
import http.server
import socket
import threading
import requests
from unittest.mock import patch, MagicMock
from scripts.process_video import process_video_url

# --- 1. Unit Tests for Video Processing Script ---
class TestProcessVideo(unittest.TestCase):
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('glob.glob')
    @patch('os.rename')
    def test_process_video_url_success(self, mock_rename, mock_glob, mock_makedirs, mock_exists, mock_run):
        # Setup mocks
        mock_exists.return_value = False # Force makedirs call
        # Mocks finding the downloaded file
        mock_glob.side_effect = [
            [], # Cleanup: no existing files
            ['data/requested_transcript.en.srt'] # Found file after download
        ]
        
        # Execute
        result = process_video_url("https://youtube.com/test", output_dir="data")
        
        # Assertions
        mock_makedirs.assert_called_with("data")
        mock_run.assert_called_once() # Should run yt-dlp
        self.assertEqual(result, 'data/requested_transcript.en.srt')

    @patch('subprocess.run')
    def test_process_video_url_failure(self, mock_run):
        # Setup mocks to simulate error
        import subprocess
        # Correctly simulate the specific error caught by the implementation
        mock_run.side_effect = subprocess.CalledProcessError(1, ['cmd'])
        
        # Execute
        result = process_video_url("https://youtube.com/test", output_dir="data")
        
        # Assertions
        self.assertIsNone(result)

# --- 2. Integration Tests for Server Endpoints ---
from server import RAGRequestHandler

class TestQuizEditorEndpoints(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Start the server on a separate thread
        cls.port = 8004
        cls.server = http.server.HTTPServer(('localhost', cls.port), RAGRequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()
        
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    @patch('server.process_video_url')
    @patch('server.parse_srt')
    @patch('server.generate_quiz_with_gemini_optimized')
    def test_generate_quiz_endpoint_success(self, mock_gen, mock_parse, mock_process):
        # Setup mocks
        mock_process.return_value = "data/test.srt"
        mock_parse.return_value = "Mock Transcript"
        mock_gen.return_value = json.dumps({
            "questions": [{
                "question_text": "Test Q", 
                "options": ["A","B"], 
                "correct_option_index": 0
            }]
        })
        
        # Execute Request
        url = f"http://localhost:{self.port}/generate_quiz"
        resp = requests.post(url, json={"youtube_url": "https://yt.com/test"})
        
        # Assertions
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("questions", data)
        self.assertEqual(data["questions"][0]["question_text"], "Test Q")
        
        # Verify call chain
        mock_process.assert_called_once()
        mock_parse.assert_called_once()
        mock_gen.assert_called_once()

    @patch('server.process_video_url')
    def test_generate_quiz_endpoint_missing_url(self, mock_process):
        url = f"http://localhost:{self.port}/generate_quiz"
        resp = requests.post(url, json={}) # No URL
        self.assertEqual(resp.status_code, 400)

    @patch('server.process_video_url')
    def test_generate_quiz_processing_failure(self, mock_process):
        mock_process.return_value = None # Failure
        
        url = f"http://localhost:{self.port}/generate_quiz"
        resp = requests.post(url, json={"youtube_url": "https://yt.com/fail"})
        
        self.assertEqual(resp.status_code, 500)

    def test_save_quiz_endpoint_success(self):
        # We allow the server to write to the real file 'data/quiz_data.json'
        # This is an integration test.
        
        test_data = {
            "questions": [{"question_text": "Saved Q"}]
        }
        
        # Ensure directory exists
        if not os.path.exists('data'):
            os.makedirs('data')
            
        # Execute
        url = f"http://localhost:{self.port}/save_quiz"
        resp = requests.post(url, json=test_data)
        
        # Assertions
        self.assertEqual(resp.status_code, 200)
        
        # Verify File Content by reading from real disk
        import time
        time.sleep(0.5) # Wait for I/O
        
        self.assertTrue(os.path.exists('data/quiz_data.json'))
        with open('data/quiz_data.json', 'r') as f:
            saved = json.load(f)
        
        self.assertEqual(saved['questions'][0]['question_text'], "Saved Q")

    def test_save_quiz_invalid_payload(self):
        url = f"http://localhost:{self.port}/save_quiz"
        resp = requests.post(url, json={"invalid": "data"})
        self.assertEqual(resp.status_code, 400)

if __name__ == '__main__':
    unittest.main()

