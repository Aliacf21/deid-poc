import unittest
import os
import json

class TestContentIntegrity(unittest.TestCase):
    
    def test_quiz_data_schema(self):
        """Verify quiz_data.json follows expected structure."""
        path = "data/quiz_data.json"
        if not os.path.exists(path):
            self.skipTest(f"{path} not found")
            
        with open(path, 'r') as f:
            data = json.load(f)
            
        self.assertIn("questions", data)
        self.assertIsInstance(data["questions"], list)
        
        if data["questions"]:
            q = data["questions"][0]
            self.assertIn("question_text", q)
            self.assertIn("options", q)
            # Support both correct_option_index or correctAnswer formats
            self.assertTrue("correct_option_index" in q or "correctAnswer" in q)

    def test_simulation_data_schema(self):
        """Verify simulation_data.json follows expected structure."""
        path = "data/simulation_data.json"
        if not os.path.exists(path):
            self.skipTest(f"{path} not found")
            
        with open(path, 'r') as f:
            data = json.load(f)
            
        # Can be list or object with 'stops'
        if isinstance(data, dict):
            self.assertIn("stops", data)
            stops = data["stops"]
        else:
            stops = data
            
        self.assertIsInstance(stops, list)
        if stops:
            s = stops[0]
            self.assertTrue("sequence_id" in s or "id" in s)
            self.assertTrue("question_for_trainee" in s or "question" in s)

    def test_visual_map_exists(self):
        self.assertTrue(os.path.exists("public/visual_map.html"))

if __name__ == '__main__':
    unittest.main()

