import unittest
import json
import sys
import os
from unittest.mock import patch, mock_open

# setup paths similar to other tests
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
paths = [os.path.join(root_dir, 'showup_tools'), root_dir]
for p in paths:
    if p not in sys.path:
        sys.path.insert(0, p)

if 'showup_core' in sys.modules:
    del sys.modules['showup_core']

from showup_tools.ai_detector import run_ai_detection_stage

class TestAIDetectionStage(unittest.TestCase):
    def test_detection_basic(self):
        patterns = {
            "patterns": [
                {"category": "digits", "patterns": ["foo\\d+"]}
            ],
            "phrases": ["hello world"]
        }
        content = "Foo123 and hello world!"
        m = mock_open(read_data=json.dumps(patterns))
        with patch("builtins.open", m):
            results = run_ai_detection_stage(content, patterns_file="dummy.json")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["pattern"], "foo\\d+")
        self.assertEqual(results[0]["category"], "digits")
        self.assertEqual(results[0]["start_index"], 0)
        self.assertEqual(results[1]["pattern"], "hello world")
        self.assertEqual(results[1]["category"], "phrase")
        self.assertEqual(results[1]["start_index"], content.lower().index("hello"))

if __name__ == "__main__":
    unittest.main()
