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

from showup_tools.refinement_stage import run_refinement_stage

class TestRefinementStage(unittest.TestCase):
    def test_refinement_with_claude(self):
        row = {"initial_plan": {"plan": "orig"}, "learner_profile": "profile"}
        config = {"model_id": "claude-3-haiku-20240307"}
        with patch('showup_tools.refinement_stage.generate_with_claude') as mock_claude:
            mock_claude.side_effect = ['critique', '{"plan": "improved"}']
            result = asyncio.run(run_refinement_stage(row, config))
        self.assertEqual(result['status'], 'PLAN_FINALIZED')
        self.assertEqual(result['plan_critique'], 'critique')
        self.assertEqual(result['final_plan']['plan'], 'improved')
        self.assertEqual(mock_claude.call_count, 2)

    def test_refinement_with_openai(self):
        row = {"initial_plan": {"plan": "orig"}, "learner_profile": "profile"}
        config = {"model_id": "gpt-4", "openai_api_key": "x"}

        mock_resp1 = MagicMock()
        mock_choice1 = MagicMock()
        mock_choice1.message.content = 'critique'
        mock_resp1.choices = [mock_choice1]

        mock_resp2 = MagicMock()
        mock_choice2 = MagicMock()
        mock_choice2.message.content = '{"plan": "improved"}'
        mock_resp2.choices = [mock_choice2]

        with patch('openai.OpenAI') as mock_openai:
            client = mock_openai.return_value
            client.chat.completions.create.side_effect = [mock_resp1, mock_resp2]
            result = asyncio.run(run_refinement_stage(row, config))

        self.assertEqual(result['status'], 'PLAN_FINALIZED')
        self.assertEqual(result['plan_critique'], 'critique')
        self.assertEqual(result['final_plan']['plan'], 'improved')
        mock_openai.assert_called()

if __name__ == '__main__':
    unittest.main()
