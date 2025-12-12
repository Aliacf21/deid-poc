import unittest
import os
import tempfile
from scripts.utils import parse_srt

class TestTranscriptParsing(unittest.TestCase):
    def setUp(self):
        self.test_srt = """1
00:00:01,000 --> 00:00:03,000
Hello world.

2
00:00:03,500 --> 00:00:05,000
This is a test.
"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".srt", mode='w') as f:
            f.write(self.test_srt)
            self.temp_file = f.name

    def tearDown(self):
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def test_parse_with_timestamps(self):
        result = parse_srt(self.temp_file, include_timestamps=True)
        self.assertIn("[T=1] Hello world.", result)
        self.assertIn("[T=3] This is a test.", result)
        
    def test_parse_without_timestamps(self):
        result = parse_srt(self.temp_file, include_timestamps=False)
        self.assertEqual(result.strip(), "Hello world. This is a test.")

    def test_missing_file(self):
        result = parse_srt("nonexistent.srt", include_timestamps=True)
        self.assertEqual(result, "")
        result_none = parse_srt("nonexistent.srt", include_timestamps=False)
        self.assertIsNone(result_none)

if __name__ == '__main__':
    unittest.main()

