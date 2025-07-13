import unittest
import asyncio
import hashlib
import os
import sys
from unittest.mock import MagicMock, patch

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
paths = [os.path.join(root_dir, 'showup_tools'), root_dir]
for p in paths:
    if p not in sys.path:
        sys.path.insert(0, p)

from showup_tools.workflow import extract_student_handbook_information

class TestDynamicRagWorkflow(unittest.TestCase):
    def test_index_and_query_called(self):
        ui = {}
        handbook_path = 'handbook.md'
        content_outline = 'outline'
        handbook_text = 'some text'
        textbook_id = hashlib.md5(handbook_path.encode()).hexdigest()
        with patch('showup_tools.workflow.extract_text_from_file', return_value=handbook_text) as p_extract, \
             patch('showup_tools.workflow.get_vector_db') as p_get_db, \
             patch('showup_tools.workflow.cache.get', return_value=None), \
             patch('showup_tools.workflow.cache.set'):
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
