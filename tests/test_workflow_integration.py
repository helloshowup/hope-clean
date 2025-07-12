import unittest
import asyncio
import sys
import os
from unittest.mock import patch

# setup paths similar to other tests
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
paths = [os.path.join(root_dir, 'showup_tools'), root_dir]
for p in paths:
    if p not in sys.path:
        sys.path.insert(0, p)

from showup_tools.workflow import process_row_for_phase

class TestWorkflowIntegration(unittest.TestCase):
    def test_full_sequence(self):
        row = {
            "Module": "M1",
            "Lesson": "L1",
            "Step number": "1",
            "Step title": "S",
            "Content Outline": "outline",
        }
        result = {"log_entries": []}
        item = {
            "row_index": 0,
            "row": row,
            "variables": {},
            "template": "",
            "context": {},
            "result": result,
            "add_log_entry": lambda *a, **k: None,
        }
        csv_rows = [row]
        ui = {}

        def fake_plan(d, cfg):
            nd = d.copy()
            nd["initial_plan"] = {"plan": "p"}
            nd["status"] = "PLAN_GENERATED"
            return nd

        def fake_refine(d, cfg):
            nd = d.copy()
            nd["final_plan"] = {"plan": "fp"}
            nd["status"] = "PLAN_FINALIZED"
            return nd

        with patch("showup_tools.workflow.run_planning_stage", side_effect=fake_plan), \
             patch("showup_tools.workflow.run_refinement_stage", side_effect=fake_refine), \
             patch("showup_tools.workflow.generate_three_versions_from_plan", return_value=["a", "b", "c"]), \
             patch("showup_tools.workflow.compare_and_combine", return_value=("best", "exp")), \
             patch("showup_tools.workflow.review_content", return_value=("reviewed", "sum")), \
             patch("showup_tools.workflow.run_ai_detection_stage", return_value=[{"pattern": "x"}]), \
             patch("showup_tools.workflow.save_as_markdown", return_value="out.md"):
            phases = ["plan", "refine", "generate", "compare", "review", "finalize"]
            for ph in phases:
                item = asyncio.run(
                    process_row_for_phase(item, ph, csv_rows, ".", "profile", "id", ui)
                )

        self.assertEqual(item["status"], "WORKFLOW_COMPLETE")
        self.assertEqual(item["final_content_path"], "out.md")
        self.assertEqual(item["ai_detection_flags"], [{"pattern": "x"}])

if __name__ == "__main__":
    unittest.main()
