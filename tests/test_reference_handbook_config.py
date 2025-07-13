import unittest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch

from showup_tools.workflow import process_row_for_phase

class TestReferenceHandbookConfig(unittest.TestCase):
    def test_new_config_keys_trigger_handbook_extraction(self):
        row = {"Content Outline": "test outline"}
        item = {
            "row_index": 0,
            "row": row,
            "variables": {},
            "template": "{{content_outline}}",
            "context": {},
            "result": {"log_entries": []},
            "add_log_entry": lambda *a, **k: None,
        }
        ui = {"use_reference_handbook": True, "reference_handbook_path": "handbook.md"}
        async_mock = AsyncMock(return_value="info")
        with patch("os.path.exists", return_value=True), \
             patch("showup_tools.workflow.extract_student_handbook_information", async_mock):
            result = asyncio.run(process_row_for_phase(item, "generate", [row], ".", "profile", "id", ui))
        self.assertIn("reference_handbook_info", result["variables"])
        async_mock.assert_awaited_once_with("test outline", "handbook.md", ui)

if __name__ == "__main__":
    unittest.main()
