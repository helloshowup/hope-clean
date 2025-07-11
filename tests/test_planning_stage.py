import unittest
import asyncio
import importlib
import sys
import os
from unittest.mock import patch, MagicMock

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
        row = {"content_outline": "Outline"}
        config = {"model_id": "claude-3-haiku-20240307"}
        with patch('showup_tools.planning_stage.generate_with_claude') as mock_claude:
            mock_claude.return_value = '{"plan": "ok"}'
            result = asyncio.run(run_planning_stage(row, config))
        self.assertEqual(result['status'], 'PLAN_GENERATED')
        self.assertEqual(result['initial_plan']['plan'], 'ok')
        mock_claude.assert_called()

    def test_planning_with_openai(self):
        row = {"content_outline": "Outline"}
        config = {"model_id": "gpt-4", "openai_api_key": "x"}

        mock_resp = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"plan": "ok"}'
        mock_resp.choices = [mock_choice]

        with patch('openai.OpenAI') as mock_openai:
            client = mock_openai.return_value
            client.chat.completions.create.return_value = mock_resp
            result = asyncio.run(run_planning_stage(row, config))

        self.assertEqual(result['status'], 'PLAN_GENERATED')
        self.assertEqual(result['initial_plan']['plan'], 'ok')
        mock_openai.assert_called()

if __name__ == '__main__':
    unittest.main()
