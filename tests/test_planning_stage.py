import unittest
import asyncio
import importlib
import sys
import os
import json
from unittest.mock import patch, MagicMock, mock_open

# setup paths similar to other tests
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
paths = [os.path.join(root_dir, 'showup_tools'), root_dir]
for p in paths:
    if p not in sys.path:
        sys.path.insert(0, p)

# provide stub for openai if missing
if 'openai' not in sys.modules:
    sys.modules['openai'] = MagicMock()

from showup_tools.planning_stage import run_planning_stage

class TestPlanningStage(unittest.TestCase):
    def test_planning_with_claude(self):
        row = {
            "content_outline": "Outline",
            "learner_profile": "Profile",
            "rationale": "Because",
            "word_count": 123,
        }
        config = {"model_id": "claude-3-haiku-20240307"}
        good_plan = {
            "content_blocks": [
                {"block_type": "lesson_metadata", "title": "t", "module_id": "m"}
            ]
        }
        with patch('showup_tools.planning_stage.generate_with_claude') as mock_claude:
            mock_claude.return_value = json.dumps(good_plan)
            result = asyncio.run(run_planning_stage(row, config))
            called_prompt = mock_claude.call_args.args[0]
        self.assertIn("Outline", called_prompt)
        self.assertIn("Profile", called_prompt)
        self.assertIn("Because", called_prompt)
        self.assertIn("123", called_prompt)
        self.assertEqual(result['status'], 'PLAN_GENERATED')
        self.assertEqual(result['initial_plan'], good_plan)
        mock_claude.assert_called()

    def test_planning_with_openai(self):
        row = {
            "content_outline": "Outline",
            "learner_profile": "Profile",
            "rationale": "Because",
            "word_count": 123,
        }
        config = {"model_id": "gpt-4", "openai_api_key": "x"}

        mock_resp = MagicMock()
        mock_choice = MagicMock()
        good_plan = {
            "content_blocks": [
                {"block_type": "lesson_metadata", "title": "t", "module_id": "m"}
            ]
        }
        mock_choice.message.content = json.dumps(good_plan)
        mock_resp.choices = [mock_choice]

        with patch('openai.OpenAI') as mock_openai:
            client = mock_openai.return_value
            client.chat.completions.create.return_value = mock_resp
            result = asyncio.run(run_planning_stage(row, config))
            called_prompt = client.chat.completions.create.call_args.kwargs['messages'][0]['content']
        self.assertIn("Outline", called_prompt)
        self.assertIn("Profile", called_prompt)
        self.assertIn("Because", called_prompt)
        self.assertIn("123", called_prompt)

        self.assertEqual(result['status'], 'PLAN_GENERATED')
        self.assertEqual(result['initial_plan'], good_plan)
        mock_openai.assert_called()

    def test_planning_validation_error(self):
        row = {
            "content_outline": "Outline",
            "learner_profile": "Profile",
            "rationale": "Because",
            "word_count": 123,
        }
        config = {"model_id": "claude-3-haiku-20240307"}
        with patch('showup_tools.planning_stage.generate_with_claude') as mock_claude:
            mock_claude.return_value = '{"bad": true}'
            result = asyncio.run(run_planning_stage(row, config))
        self.assertEqual(result['status'], 'PLAN_FAILED')
        self.assertIn('bad', result.get('error', ''))

    def test_planning_legacy(self):
        row = {
            "content_outline": "Outline",
            "learner_profile": "Profile",
            "rationale": "Because",
            "word_count": 123,
        }
        config = {"model_id": "claude-3-haiku-20240307", "use_dynamic_blocks": False}
        legacy_plan = {"video_title": "t", "scenes": []}
        with patch('showup_tools.planning_stage.generate_with_claude') as mock_claude:
            mock_claude.return_value = json.dumps(legacy_plan)
            with patch('builtins.open', mock_open(read_data='prompt')):
                result = asyncio.run(run_planning_stage(row, config))
        self.assertEqual(result['status'], 'PLAN_GENERATED')
        self.assertEqual(result['initial_plan'], legacy_plan)

    def test_planning_accepts_image_placeholder(self):
        row = {
            "content_outline": "Outline",
            "learner_profile": "Profile",
            "rationale": "Because",
            "word_count": 123,
        }
        config = {"model_id": "claude-3-haiku-20240307"}
        plan = {
            "content_blocks": [
                {"block_type": "lesson_metadata", "title": "t", "module_id": "m"},
                {"block_type": "image_placeholder", "description": "A break"},
            ]
        }
        with patch('showup_tools.planning_stage.generate_with_claude') as mock_claude:
            mock_claude.return_value = json.dumps(plan)
            result = asyncio.run(run_planning_stage(row, config))
        self.assertEqual(result['status'], 'PLAN_GENERATED')
        self.assertEqual(result['initial_plan'], plan)

if __name__ == '__main__':
    unittest.main()
