import unittest
import asyncio
import json
import importlib
import sys
import os
from unittest.mock import patch, mock_open

# setup paths similar to other tests
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
paths = [os.path.join(root_dir, 'showup_tools'), root_dir]
for p in paths:
    if p not in sys.path:
        sys.path.insert(0, p)

# remove stale namespace packages that may block imports
if 'showup_core' in sys.modules:
    del sys.modules['showup_core']

from showup_tools.content_generator import generate_three_versions_from_plan

class TestGenerationStage(unittest.TestCase):
    def test_generate_three_versions_from_plan(self):
        final_plan = {"content_blocks": [{"block_type": "lesson_metadata", "title": "t", "module_id": "m"}]}
        ui_settings = {
            "generation_settings": {
                "max_tokens": 1000,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.2
            },
            "selected_model": "test-model"
        }
        prompt_text = "Prompt for block {{block}}"
        m = mock_open(read_data=prompt_text)
        with patch("builtins.open", m):
            with patch("showup_tools.content_generator.generate_with_claude") as mock_gen:
                mock_gen.side_effect = ["v1", "v2", "v3"]
                result = asyncio.run(generate_three_versions_from_plan(final_plan, ui_settings))

        self.assertEqual(result, ["v1", "v2", "v3"])
        self.assertEqual(mock_gen.call_count, 3)
        called_args = mock_gen.call_args_list[0][1]
        self.assertEqual(called_args["max_tokens"], 1000)
        self.assertEqual(called_args["temperature"], 0.3)
        self.assertEqual(called_args["model"], "test-model")
        self.assertEqual(called_args["frequency_penalty"], 0.1)
        self.assertEqual(called_args["presence_penalty"], 0.2)
        self.assertIn(json.dumps(final_plan["content_blocks"][0]), mock_gen.call_args_list[0][1]["prompt"])

    def test_generate_three_versions_legacy(self):
        final_plan = {"video_title": "t", "scenes": []}
        ui_settings = {"selected_model": "test-model", "use_dynamic_blocks": False,
                       "generation_settings": {"max_tokens": 500}}
        m = mock_open(read_data="legacy {{final_plan}}")
        with patch("builtins.open", m):
            with patch("showup_tools.content_generator.generate_with_claude") as mock_gen:
                mock_gen.side_effect = ["v1", "v2", "v3"]
                result = asyncio.run(generate_three_versions_from_plan(final_plan, ui_settings))

        self.assertEqual(result, ["v1", "v2", "v3"])
        self.assertEqual(mock_gen.call_count, 3)
        self.assertIn(json.dumps(final_plan), mock_gen.call_args_list[0][1]["prompt"])

if __name__ == '__main__':
    unittest.main()
