import unittest
import os
import sys
import logging

if "showup_core" in sys.modules:
    del sys.modules["showup_core"]

from showup_tools.workflow import setup_logging

class TestSetupLogging(unittest.TestCase):
    def test_default_log_level_debug(self):
        root_logger = logging.getLogger()
        prev_level = root_logger.level
        prev_handlers = list(root_logger.handlers)
        try:
            log_file = setup_logging()
            self.assertEqual(root_logger.level, logging.DEBUG)
            self.assertTrue(os.path.exists(log_file))
        finally:
            root_logger.handlers.clear()
            for h in prev_handlers:
                root_logger.addHandler(h)
            root_logger.setLevel(prev_level)
            if os.path.exists(log_file):
                os.remove(log_file)

if __name__ == '__main__':
    unittest.main()
