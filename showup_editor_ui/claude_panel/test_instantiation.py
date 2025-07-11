import tkinter as tk
import sys
import os
import logging
import pytest

pytest.skip("Manual GUI test", allow_module_level=True)

# Configure logging to see output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Setup Python Path ---
def setup_paths():
    showup_v4_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    paths_to_add = [
        showup_v4_root,
        os.path.join(showup_v4_root, 'showup-core'),
        os.path.join(showup_v4_root, 'showup_tools')
    ]
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    logger.info(f"PYTHONPATH set to include: {paths_to_add}")

setup_paths()

# --- Import the necessary components ---
try:
    from showup_editor_ui.claude_panel.enrich_lesson import EnrichLessonPanel
    from showup_editor_ui.claude_panel.markdown_editor import MarkdownEditor
    logger.info("Successfully imported panel components.")
except ImportError as e:
    logger.error(f"Failed to import panel components: {e}")
    sys.exit(1)

# --- Main Test Function ---
def main():
    """
    Tests the instantiation of the EnrichLessonPanel to ensure all
    dependencies and constructor arguments are correctly configured.
    """
    logger.info("Starting panel instantiation test...")
    
    try:
        # 1. Create a root Tkinter window
        root = tk.Tk()
        root.withdraw() # Hide the window

        # 2. Create mock parent controller and markdown editor
        mock_parent_controller = object()
        mock_main_frame = tk.Frame(root)
        # The MarkdownEditor itself needs a parent controller, we can use the same mock
        markdown_editor = MarkdownEditor(mock_parent_controller)
        
        # 3. Create a frame for the enrich lesson tab
        enrich_lesson_tab_frame = tk.Frame(root)

        # 4. Attempt to instantiate the EnrichLessonPanel
        logger.info("Attempting to instantiate EnrichLessonPanel...")
        panel = EnrichLessonPanel(
            enrich_tab_frame=enrich_lesson_tab_frame,
            parent_controller=mock_parent_controller,
            markdown_editor=markdown_editor
        )
        logger.info("✅ SUCCESS: EnrichLessonPanel instantiated without errors.")
        
        # 5. Clean up the Tkinter window
        root.destroy()

    except Exception as e:
        logger.error(f"❌ FAILED: An error occurred during panel instantiation.")
        raise e

if __name__ == "__main__":
    main()
