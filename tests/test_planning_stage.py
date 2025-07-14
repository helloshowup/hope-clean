import unittest
from unittest.mock import patch, AsyncMock

from showup_tools.planning_stage import run_planning_stage

class TestPlanningStage(unittest.IsolatedAsyncioTestCase):
    async def test_prompt_uses_row_values(self):
        row = {
            "Content Outline": "Outline from row",
            "Learner Profile": "Learner from row"
        }
        variables = {
            "content_outline": "Outline from variables",
            "target_learner": "Learner from variables",
            "topic": "Photography"
        }
        row_data_item = {
            "row": row,
            "variables": variables,
            "word_count": 50
        }
        config = {"model_id": "claude-test"}

        prompt_template = "Outline: {{content_outline}} | Learner: {{learner_profile}}"

        with patch("showup_tools.planning_stage.load_prompt", return_value=prompt_template), \
             patch("showup_tools.planning_stage.get_block_type_definitions", return_value=""), \
             patch("showup_tools.planning_stage.generate_with_claude", new=AsyncMock(return_value='{"content_blocks": []}')) as mock_gen, \
             patch("showup_tools.planning_stage.validate_plan") as mock_validate:
            mock_validate.return_value.model_dump.return_value = {"content_blocks": []}
            result = await run_planning_stage(row_data_item, config)

        mock_gen.assert_awaited()
        used_prompt = mock_gen.call_args[0][0]
        self.assertIn("Outline from row", used_prompt)
        self.assertIn("Learner from row", used_prompt)
        self.assertEqual(result["status"], "PLAN_GENERATED")

if __name__ == "__main__":
    unittest.main()
