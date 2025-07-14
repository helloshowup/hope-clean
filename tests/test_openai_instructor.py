import unittest
from unittest.mock import AsyncMock, patch

from showup_tools.openai_dynamic_generation import (
    generate_structured_content,
    repair_generated_json_with_llm,
)
from showup_tools.models import DynamicContentGenerationResult


class TestOpenAIInstructor(unittest.IsolatedAsyncioTestCase):
    async def test_generate_structured_content(self):
        with patch('showup_tools.openai_dynamic_generation.instructor.from_openai') as mock_from_openai, \
             patch('showup_tools.openai_dynamic_generation.AsyncOpenAI'):
            mock_client = mock_from_openai.return_value
            mock_client.chat.completions.create = AsyncMock(return_value='result')
            result = await generate_structured_content('prompt', api_key='k', model='gpt-test')
            mock_from_openai.assert_called()
            mock_client.chat.completions.create.assert_awaited_with(
                model='gpt-test',
                response_model=DynamicContentGenerationResult,
                messages=unittest.mock.ANY,
                max_retries=2,
            )
            self.assertEqual(result, 'result')

    async def test_generate_structured_content_repair_path(self):
        with patch('showup_tools.openai_dynamic_generation.instructor.from_openai') as mock_from_openai, \
             patch('showup_tools.openai_dynamic_generation.AsyncOpenAI'), \
             patch('showup_tools.openai_dynamic_generation.repair_generated_json_with_llm', new=AsyncMock(return_value='fixed')) as mock_repair:
            mock_client = mock_from_openai.return_value
            mock_client.chat.completions.create = AsyncMock(side_effect=Exception('fail'))
            result = await generate_structured_content('prompt', api_key='k', model='gpt-test', raw_llm_output_snippet='{}')
            mock_repair.assert_awaited_with(broken_text='{}', api_key='k', model='gpt-test')
            self.assertEqual(result, 'fixed')


if __name__ == '__main__':
    unittest.main()

