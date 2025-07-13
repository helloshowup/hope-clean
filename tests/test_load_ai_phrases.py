import unittest
import os
import sys
import json

# setup import path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
paths = [os.path.join(root_dir, "showup_tools"), root_dir]
for p in paths:
    if p not in sys.path:
        sys.path.insert(0, p)

from showup_tools.ai_detector import _load_ai_phrases

class TestLoadAIPhrases(unittest.TestCase):
    def test_load_ai_phrases_repo_relative(self):
        data = _load_ai_phrases()
        self.assertIsInstance(data, dict)
        self.assertIn("phrases", data)
        self.assertIn("patterns", data)
        # data/ai_phrases.json created for tests contains 'bar'
        self.assertIn("bar", data.get("phrases", []))

if __name__ == "__main__":
    unittest.main()
