import unittest
import asyncio
import sys
import os
from unittest.mock import patch, mock_open

from simplified_workflow.markdown_utils import insert_sections_in_markdown
from simplified_workflow.learning_sections import generate_lo_and_kt_from_content

class TestLearningSections(unittest.TestCase):
    def test_insert_after_intro(self):
        content = "# Title\n\n## Introduction\nIntro text\n\n## Body\nMore"
        section = "## Learning Objectives\n- Obj"
        result = insert_sections_in_markdown(content, section, position='after_intro')
        self.assertIn(section, result)
        self.assertTrue(result.index(section) < result.index('## Body'))

    def test_generate_learning_sections(self):
        prompt = "Prompt {{content}}"
        with patch('builtins.open', mock_open(read_data=prompt)):
            with patch('simplified_workflow.learning_sections.generate_with_claude') as mock_gen:
                mock_gen.return_value = "## Learning Objectives\n- O\n## Key Takeaways\n- K"
                lo, kt = asyncio.run(generate_lo_and_kt_from_content('x', model='m'))
        self.assertEqual(lo, "## Learning Objectives\n- O")
        self.assertEqual(kt, "## Key Takeaways\n- K")

if __name__ == '__main__':
    unittest.main()
