import unittest
import asyncio
import hashlib
import os
import sys
from unittest.mock import MagicMock, patch

from simplified_workflow.workflow import extract_student_handbook_information

class TestDynamicRagWorkflow(unittest.TestCase):
    def test_index_and_query_called(self):
        ui = {}
        handbook_path = 'handbook.md'
        content_outline = 'outline'
        handbook_text = 'some text'
        textbook_id = hashlib.md5(handbook_path.encode()).hexdigest()
        with patch('simplified_workflow.workflow.extract_text_from_file', return_value=handbook_text) as p_extract, \
             patch('simplified_workflow.workflow.get_vector_db') as p_get_db, \
             patch('simplified_workflow.workflow.cache.get', return_value=None), \
             patch('simplified_workflow.workflow.cache.set'):
            mock_db = MagicMock()
            mock_db.query_textbook.return_value = ['chunk']
            p_get_db.return_value = mock_db
            result = asyncio.run(extract_student_handbook_information(content_outline, handbook_path, ui))
            p_extract.assert_called_once_with(handbook_path)
            mock_db.index_textbook.assert_called_once_with(handbook_text, textbook_id)
            mock_db.query_textbook.assert_called_once()
            self.assertIn('chunk', result)

if __name__ == '__main__':
    unittest.main()
