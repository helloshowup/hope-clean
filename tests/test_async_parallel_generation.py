import unittest
import asyncio
import time
from unittest.mock import patch, mock_open

from showup_tools.content_generator import generate_three_versions_from_plan

class TestAsyncParallelGeneration(unittest.TestCase):
    def test_parallel_speed(self):
        final_plan = {"plan": "x"}
        ui_settings = {}

        async def fake_generate_with_claude(**kwargs):
            await asyncio.sleep(0.1)
            return str(kwargs.get("temperature"))

        m = mock_open(read_data="Prompt {{final_plan}}")
        with patch("builtins.open", m):
            with patch(
                "showup_tools.content_generator.generate_with_claude",
                side_effect=fake_generate_with_claude,
            ):
                start = time.perf_counter()
                result = asyncio.run(
                    generate_three_versions_from_plan(final_plan, ui_settings)
                )
                duration = time.perf_counter() - start

        self.assertEqual(result, ["0.3", "0.5", "1.0"])
        self.assertLess(duration, 0.25)

if __name__ == "__main__":
    unittest.main()
