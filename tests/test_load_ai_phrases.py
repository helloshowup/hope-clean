import unittest
import os
import sys
import json

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
