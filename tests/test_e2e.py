import unittest
import os
import json
import requests
import time
import subprocess
import signal

SERVER_URL = "http://localhost:8000"

class TestEndToEnd(unittest.TestCase):
    
    def test_01_assets_exist(self):
        """Verify that all expected assets have been generated."""
        files_to_check = [
            "data/quiz_data.json",
            "data/simulation_data.json",
            "public/visual_map.html",
            "public/index.html",
            "public/displayed_image.png"
        ]
        for f in files_to_check:
            self.assertTrue(os.path.exists(f), f"File {f} not found.")

    def test_02_json_validity(self):
        """Verify that JSON data files are valid."""
        with open("data/quiz_data.json", 'r') as f:
            data = json.load(f)
            self.assertIn("questions", data)
            self.assertTrue(len(data["questions"]) > 0)
            
        with open("data/simulation_data.json", 'r') as f:
            data = json.load(f)
            self.assertIn("stops", data)
            self.assertTrue(len(data["stops"]) > 0)

    def test_03_html_content(self):
        """Verify index.html has been patched with the visual map."""
        with open("public/index.html", 'r') as f:
            content = f.read()
            self.assertIn('graph TD', content, "Mermaid graph not found in index.html")
            self.assertIn('Phase_1', content, "Expected graph content not found")

    def test_04_server_static_files(self):
        """Test server static file serving (requires server running)."""
        # Test Root
        r = requests.get(f"{SERVER_URL}/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Grand Rounds", r.text)

        # Test Public File
        r = requests.get(f"{SERVER_URL}/visual_map.html")
        self.assertEqual(r.status_code, 200)

        # Test Data File via Redirect/Rewriting
        r = requests.get(f"{SERVER_URL}/quiz_data.json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json())

    def test_05_chat_api(self):
        """Test the Chat API endpoint."""
        payload = {"message": "What is the diagnosis?"}
        try:
            r = requests.post(f"{SERVER_URL}/chat", json=payload)
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertIn("reply", data)
            print(f"\n[Chat Response]: {data['reply'][:100]}...")
        except Exception as e:
            self.fail(f"Chat API failed: {e}")

if __name__ == '__main__':
    unittest.main()

