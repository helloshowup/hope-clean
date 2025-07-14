# **Refactoring Blueprint for Simplified Kivy Application**

Below is a step-by-step plan to isolate and stabilize the Kivy application (ShowUpSquared Simplified Content Generator). Each task is scoped to be fed into an AI coding assistant (OpenAI Codex) **one at a time**. The tasks are ordered logically, with each step focusing on a coherent set of changes, and include a clear objective and verification criteria.

## **Task 1: Remove Legacy Editor UI Code 🗑️**

**Objective:** Eliminate the old `showup_editor_ui` module (the legacy editor UI) and any references to it, as it’s not needed for the simplified content generator.

* **Remove Directory:** Delete the entire `showup_editor_ui/` folder from the project.

* **Clean up Tests:** Remove or update tests that reference `showup_editor_ui`. In particular, delete `tests/test_claude_modules.py` (which imports `showup_editor_ui.claude_panel` components) and the Tkinter GUI test `showup_editor_ui/claude_panel/test_instantiation.py`. These are no longer relevant.

* **Verify Imports:** Search the codebase for any `import showup_editor_ui` statements (especially in tests or utility scripts) and remove them[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/tests/test_claude_modules.py#L18-L25)[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/showup_editor_ui/claude_panel/test_instantiation.py#L20-L28).

* **Run Tests:** After removal, run the test suite (`pytest`) to ensure no module import errors or test failures occur related to the old UI. Specifically, `TestClaudeModules` and any GUI panel tests should no longer run or should be deleted.

* **Expected Outcome:** The code compiles and tests pass without references to `showup_editor_ui`. The application’s functionality remains unaffected (since this UI was unused in the simplified workflow).

## **Task 2: Remove Archived Scripts 📦 (Completed)**

**Objective:** Delete the `archive/` directory and its contents, which contain deprecated or backup scripts that are no longer in use. This step has been completed.

* **Remove Directory:** Delete the entire `archive/` folder from the repository.

* **Check References:** Ensure no active code references files in `archive/`. Search for strings like `"archive/"` in the repository to confirm nothing important depends on them.

* **Update Documentation:** If the README or any dev docs mention the archive or old scripts, remove or update those sections to avoid confusion.

* **Run Tests:** Run the test suite again to verify nothing was implicitly relying on archive files (for example, some tests might load data or modules from archive by name, but ideally none should).

* **Expected Outcome:** The repository no longer contains `archive` files. All tests still pass, and project documentation no longer references removed scripts.

## **Task 3: Point Kivy App to Simplified Workflow 🚀**

**Objective:** Connect the Kivy GUI (`main.py`) to the simplified content generation pipeline, instead of the old workflow module. This makes the "Start Workflow" button execute the actual generation process.

**Import New Workflow:** In `main.py`, change the import to use the simplified workflow module. For example:

 python  
CopyEdit  
`from simplified_workflow.workflow import run_workflow, setup_logging`

*  instead of importing from `showup_tools.workflow`[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/main.py#L32-L40). Ensure both `run_workflow` and `setup_logging` are imported (export `setup_logging` if needed, or import directly from the submodule).

* **Remove Legacy Fallback:** The try/except around importing `showup_tools.workflow` can be removed or adjusted. We expect `simplified_workflow` to be present, so handle import failure only if truly necessary (e.g., log an error and disable the Start button if not found).

* **Update Usage:** Ensure that in `WorkflowApp.start_workflow`, we call the new `run_workflow` (from `simplified_workflow`). The function signature should remain the same. Confirm that `WorkflowApp.run_workflow_in_thread` uses `asyncio.run_until_complete` on the new `run_workflow` correctly[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/main.py#L198-L206).

* **Planned Enhancements Note:** In README’s **Planned Enhancements** section (if any), update mentions of integrating the UI with `simplified_workflow.run_workflow` – it’s now done, so you can state that the UI triggers the real pipeline (remove any note about simulation)[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/README.md#L7-L11).

* **Verify Behavior:** Manually run the app via `launch_kivy_app.bat`. In the UI, select a sample CSV and start the workflow. The status updates and final output should reflect the pipeline’s real execution (e.g., content gets generated, logs path is shown, etc.). If actual API calls can’t be made in a test environment, rely on the debug log or a dry-run to ensure the thread is started and no exceptions occur.

* **Run Tests:** Execute `pytest tests/test_kivy_app.py`. All tests (e.g., ensuring the status message for a missing CSV, progress updates) should still pass[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/tests/test_kivy_app.py#L24-L32). The core change is internal, so the existing GUI tests should remain valid.

* **Expected Outcome:** The Kivy app is now fully wired to the content generation pipeline. Hitting "Start Workflow" in the GUI will run `simplified_workflow.run_workflow` in a background thread, and the UI will display real-time progress and results.

## **Task 4: Consolidate Pipeline Modules into `simplified_workflow/` 📁**

**Objective:** Move all necessary backend modules into the `simplified_workflow` package, so that the project’s core logic is self-contained and intuitively located. This includes the RAG system and any utility modules still in `showup_tools`.

* **Move RAG System:** Relocate the **RAG (Retrieval-Augmented Generation)** components from `showup_tools/simplified_app/rag_system/` to the `simplified_workflow/` package. Create a new folder `simplified_workflow/rag_system/` and move all files (e.g. `token_counter.py`, `cache_manager.py`, `textbook_vector_db.py`, `ingest_textbook.py`, `rag_integration.py`, etc.) into it[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/showup_tools/workflow.py#L2-L5). Preserve the internal structure and `__init__.py` if any.

  * Update import paths in the codebase: wherever we had `from showup_tools.simplified_app.rag_system import ...` or similar, change it to `from simplified_workflow.rag_system import ...`. For example, in `simplified_workflow/content_generator.py`, the line importing `enhanced_generate_content` should point to the new location[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/simplified_workflow/content_generator.py#L14-L18).

  * Update references in the RAG system itself if it assumed a `showup_tools` base package (e.g., file paths or relative imports in `ingest_textbook.py` might need adjusting after moving).

* **Move Utility Modules:** Transfer essential utility modules from `showup_tools` into `simplified_workflow`:

  * **Learning Sections:** Move `showup_tools/learning_sections.py` → `simplified_workflow/learning_sections.py`. This module generates Learning Objectives and Key Takeaways from content, which we want to retain for finalization steps.

  * **Markdown Utils:** Move `showup_tools/markdown_utils.py` → `simplified_workflow/markdown_utils.py`. It contains helper functions (like `insert_sections_in_markdown`) for inserting generated sections into content.

  * After moving, adjust any imports. For instance, tests referencing `showup_tools.learning_sections` should import `simplified_workflow.learning_sections`[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/tests/test_learning_sections.py#L13-L21). If the `simplified_workflow.workflow` (or other modules) used these, update those imports as well.

* **Verify Package Initialization:** Ensure `simplified_workflow/__init__.py` exposes what’s needed. It already aliases `workflow.main` as `run_workflow`[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/simplified_workflow/__init__.py#L10-L13). Consider adding `from . import rag_system, learning_sections, markdown_utils` if those need to be accessible at package level (not strictly required unless external code expects it).

* **Run Tests:**

  * RAG integration tests: Update and run `tests/test_rag_integration_import.py` – change the import to `importlib.import_module('simplified_workflow.rag_system.rag_integration')` and check `hasattr(module, 'enhanced_generate_content')`[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/tests/test_rag_integration_import.py#L4-L7). It should pass, confirming the module moved successfully.

  * Dynamic RAG workflow test: In `tests/test_rag_dynamic.py`, update the import of `extract_student_handbook_information` to the new module path (now likely `from simplified_workflow.workflow import extract_student_handbook_information`). Adjust the patch targets inside (they should patch `simplified_workflow.workflow.cache`, `.get_vector_db`, etc., instead of the old `showup_tools.workflow` references)[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/tests/test_rag_dynamic.py#L22-L30). Run this test to ensure the handbook extraction logic still works with the new imports.

  * Learning sections test: Update `tests/test_learning_sections.py` to import from `simplified_workflow.learning_sections` and `simplified_workflow.markdown_utils`[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/tests/test_learning_sections.py#L13-L21). Run it to verify that `generate_lo_and_kt_from_content` and `insert_sections_in_markdown` function as before (they should, since we just moved the code).

* **Expected Outcome:** The `simplified_workflow` folder now contains all core components: CSV processing, content generation pipeline, RAG system, and supporting utilities. The codebase has no lingering dependencies on `showup_tools` for active features. All tests related to these components pass with the updated import paths.

## **Task 5: Remove Deprecated Pipeline Code (Old Workflow) 🗃️**

**Objective:** Eliminate the remnants of the old multi-stage workflow that are no longer needed, now that the simplified workflow is in place. This declutters the codebase, leaving only relevant logic.

* **Delete `showup_tools/`:** After Task 4, the critical pieces from `showup_tools` have been moved. Now remove the entire `showup_tools` directory and any submodules within it:

  * This will remove outdated modules such as `planning_stage.py` and `refinement_stage.py` (the legacy planning phases), the old `workflow.py` (which included plan/refine stages), and any other unused utilities.

  * It also removes `showup_tools/simplified_app/` (which should be empty after moving `rag_system`).

  * **Note:** We have already moved `showup_tools/showup_core` in a later task (Task 6), so coordinate the deletion accordingly. Ensure `showup_core` is handled before final removal of `showup_tools`.

* **Adjust Test Configuration:** Many tests previously added `showup_tools` to `sys.path` to import these modules[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/tests/test_planning_stage.py#L10-L18)[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/tests/test_workflow_integration.py#L8-L16). Remove or update those path insertions in the remaining tests to reflect the new structure:

  * For example, in tests that now use `simplified_workflow`, adding the project root to `sys.path` is sufficient (since our modules are at root or under `simplified_workflow/`). You can remove any lines like `paths = [..., os.path.join(root_dir, 'showup_tools')]` from test setup.

* **Remove Obsolete Tests:** Delete tests that targeted the removed functionality:

  * `tests/test_planning_stage.py` – covers `run_planning_stage` with Claude/OpenAI; this is obsolete since planning stage is removed[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/tests/test_planning_stage.py#L20-L28).

  * `tests/test_workflow_integration.py` – integration test for full pipeline including plan/refine/generate/etc. The simplified workflow doesn’t go through “plan” or “refine” phases, so this test of the old sequence should be removed[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/tests/test_workflow_integration.py#L50-L59)[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/tests/test_workflow_integration.py#L100-L108).

  * Any other test exclusively covering removed code (ensure no references remain to `run_planning_stage`, `run_refinement_stage`, or `generate_three_versions_from_plan`).

* **Double-Check Docs:** Update the README if it described the full six-stage workflow (Plan, Refine, Generate, etc.). The simplified app may skip Plan/Refine, but if those concepts still apply (maybe the CSV already provides content outlines, effectively replacing planning), clarify accordingly. You might note that the pipeline now starts at content generation given a provided outline, etc.

* **Run Full Test Suite:** Ensure that after removing `showup_tools`, running `pytest` yields **no import errors or failures**. Particularly, tests for planning/refinement should be gone, and remaining tests (for generation, RAG, UI) pass.

* **Expected Outcome:** The legacy pipeline code is completely removed from the repository. The only workflow code is under `simplified_workflow/`. The test suite is green, covering just the current functionality. The project structure is leaner, containing only the necessary modules for the content generator.

## **Task 6: Extract Core API Client to Project Root 🔑**

**Objective:** Preserve the AI API client functionality (for Claude/OpenAI) but make it a first-class part of the project, not hidden under a removed package. This involves moving `showup_core` out of the now-deleted `showup_tools`.

* **Move `showup_core`:** Take the entire `showup_tools/showup_core/` directory and move it to the repository root as `showup_core/`. This includes `api_client.py`, and any associated modules like `model_config.py`, `api_utils.py`, etc., maintaining the internal structure. Ensure its `__init__.py` (if any) is preserved so it remains a package.

* **Update Imports:** The code already refers to this module as `showup_core` (note: previously it worked because we inserted `showup_tools` into the path). With the folder now at root, `import showup_core.api_client` should work out-of-the-box, given the project root is on `sys.path` (the launcher does this).

  * In case any imports still explicitly had `showup_tools.showup_core`, change them to just `showup_core`. For example, `from showup_tools.showup_core.api_client import generate_with_claude` in any remaining code should become `from showup_core.api_client import generate_with_claude`. (In our earlier steps, `simplified_workflow` modules were already using `showup_core.api_client` without the prefix, which should now resolve correctly).

* **Tests:** Remove any test `sys.path` hacks related to `showup_core`. We likely had none explicitly (they were covered by adding `showup_tools` path), but double-check if any test or script tries to import `showup_tools.showup_core`. After this move, those should be updated to `showup_core` or removed.

* **Integration Check:** The core usage of `showup_core.api_client` is in the content generation process (Claude API calls). To verify everything is wired correctly:

  * Run a quick dry-run of the pipeline (perhaps with `ANTHROPIC_API_KEY` set to a dummy value) to ensure `generate_with_claude` can be called. The absence of import errors will indicate success.

  * Alternatively, run a specific unit test if present for the API client. If none exists, consider writing a minimal test to instantiate `ApiClient` or call `generate_with_claude` with a stub (though this might be overkill for this task).

* **Expected Outcome:** The `showup_core` package sits at the project root and is importable. The application and pipeline find the API client with no issues. The repository structure is now intuitive: `showup_core` contains API interfacing code, and `simplified_workflow` contains the app logic. We have fully severed the dependency on the removed `showup_tools` package.

## **Task 7: Pin and Prune Dependencies 📌**

**Objective:** Create a stable, repeatable environment by pinning all project dependencies to specific versions, and remove any libraries that are not actually used in this simplified application.

* **Review Current Requirements:** The existing `requirements.txt` lists several packages (some with minimum versions, many without versions)[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/requirements.txt#L1-L10)[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/requirements.txt#L11-L20). We will update this file to pin exact versions:

  * **Core runtime libraries** (needed for the app to run):

    * `kivy==2.3.1` (the GUI framework version required, as indicated by `kivy.require('2.3.1')` in code[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/main.py#L1-L9)).

    * `anthropic==0.3.0` (Claude API client library – if we are using the official AnthropIC SDK; otherwise, since our code calls the API via HTTP, this could be optional. But for safety and future-proofing, include the official lib pinned).

    * `openai==0.27.8` (OpenAI API library, if we plan to support OpenAI models as an option; our code references `openai` in tests and config, so pin it).

    * `pandas==1.5.3` (if any part of the pipeline eventually uses pandas; currently CSV reading uses Python’s `csv`, but pandas was in the list, possibly for data manipulation – include it pinned in case).

    * `sentence-transformers==2.2.2` (per requirements, at least 2.2.2 – pin to 2.2.2 or latest stable 2.x – used for embeddings in RAG).

    * `faiss-cpu==1.7.3` (pin a version known to work with `sentence-transformers`; Faiss is C++ backend for vector search).

    * `langchain==0.0.208` and `langchain-community==0.0.4` (pin versions that are compatible; these support the RAG system).

    * `tiktoken==0.4.0` (tokenization library for token counting as used in RAG).

    * `python-dotenv==1.0.0` (for loading API keys from .env).

    * `requests==2.31.0` (the API client likely uses `requests` for HTTP calls to AnthropIC’s API; ensure it’s included).

    * `PyPDF2==3.0.1` and `pdfminer.six==20221105` (for PDF text extraction in handbook processing).

    * `markdown==3.4.3` (if we use the `markdown` library anywhere; possibly not strictly needed unless converting markdown to HTML or such, but it was listed in pyproject).

    * `numpy==1.24.3` and `scikit-learn==1.2.2` (these might be indirectly used by sentence-transformers or FAISS; sentence-transformers often uses numpy, and maybe scikit-learn for certain embedding functionalities or clustering – include if they were listed).

    * `azure-cognitiveservices-speech` – **omit this** if not used (the simplified generator doesn’t do text-to-speech; this was likely for another feature).

    * `python-docx` – **omit or pin** depending on usage (if the simplified workflow doesn’t export .docx files, we can drop this; it was in pyproject, but not used in our pipeline).

    * `aiohttp==3.8.4` (sometimes required by `anthropic` or `openai` libraries for async; include if needed).

    * `loguru` – **omit** if not used (our logging uses standard library `logging`; loguru was listed but not imported anywhere).

    * `Pillow==9.5.0` – **omit** if not used (likely not used unless the old editor dealt with images; our generator doesn’t output images, just placeholders).

    * `pydantic==2.0.3` – (if used by any config or model definitions; it was listed via `pydantic>=2` in requirements. Possibly used by none of our current code, but if it sneaks in via langchain or others, ensure compatibility. We can include `pydantic==2.0.3` as a safe pin).

  * **Dev tools** (for development environment):

    * `black==23.3.0`

    * `flake8==6.0.0`

    * `isort==5.12.0`

    * `pytest==7.4.0` (if we want to pin the test runner as well).

    * (Note: These could optionally go into a separate `requirements-dev.txt`, but since we want one reproducible lock file, including them here or documenting them is fine.)

* **Update `requirements.txt`:** Replace the current contents with the pinned list assembled above. Each line should be `package==X.Y.Z`. Remove any package that we decided to omit (e.g., `azure-cognitiveservices-speech`, `loguru`, etc.).

* **Lock Versions for Venv:** Optionally, after updating, run `pip install -r requirements.txt` in a fresh environment and then use `pip freeze` to double-check that those versions are correct and no additional transient deps are missing. If something was missed (e.g., `transformers` library needed by `sentence-transformers`), consider adding it explicitly with a pin.

* **Test Installation:** As a verification step, use the `launch_kivy_app.bat` script on a system without the dependencies. The script should detect `requirements.txt` and run `pip install -r requirements.txt`[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/launch_kivy_app.bat#L34-L42). This should succeed installing all packages. Then the script launches `main.py` – ensure the app comes up without errors (watch for missing library import errors in the console).

* **Expected Outcome:** The project has a `requirements.txt` with pinned versions, ensuring environment consistency. Unused libraries are pruned, reducing bloat. Anyone (or any CI system) setting up the project with this file will get the correct versions. The app runs successfully in the clean environment, proving that all needed dependencies are present and correctly pinned.

## **Task 8: Update Documentation and Build Instructions 📖**

**Objective:** Rewrite parts of the documentation to reflect the new simplified application structure and provide clear instructions for setup, running, and development.

* **README.md – Introduction:** Update the introduction to emphasize that this repository now focuses on **one** application: the ShowUp AI Content Generator with a Kivy interface. Remove mentions of the old editor UI or any other tools that were stripped out. Make sure the description of launching the app (via `launch_kivy_app.bat`) is accurate and up-to-date[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/README.md#L1-L9).

* **README.md – Workflow Description:** If the README previously outlined a multi-stage workflow (Plan, Refine, etc.), adjust this to the current reality:

  * If the simplified workflow skips the Planning/Refinement because the CSV provides content outlines, explain that the pipeline starts at content generation. (E.g., “**Workflow Stages:** Upon clicking **Start Workflow**, the app will generate content for each step outlined in the CSV, then compare variants, review for the learner profile, run an AI-detection check, and finalize content by adding Learning Objectives/Key Takeaways.”)

  * Remove or alter sections that no longer apply (for example, if planning stage code is gone, you might reduce the detail on it or mark it as an “earlier concept now simplified”).

  * Ensure the Mermaid diagram or any stage listing corresponds to the simplified flow. If needed, add a note that planning is assumed to be done by the user via the CSV outline.

* **README.md – Usage Instructions:** Provide a succinct guide on how to run the application:

  * Environment setup: “Install Python 3.9+ and run `launch_kivy_app.bat` – this will create a virtual environment and install requirements automatically.”

  * Input preparation: describe the expected CSV format (column names like Module, Lesson, Step number, Step title, Content Outline, Rationale, etc. as implied by `csv_processor.py`[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/showup_tools/csv_processor.py#L46-L55)[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/showup_tools/csv_processor.py#L56-L64)). Mention how to include an optional student handbook PDF for context.

  * Running the workflow: “Open the app, browse to your CSV (and handbook if available), then click Start Workflow. Monitor the progress bar and status. On completion, the output markdown files and a log will be saved in an `output/run_<timestamp>` directory, with paths displayed in the app.”

  * What to expect from output: mention that final markdown files will include the generated content, with `<educational_content>` tags (as enforced by prompts[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/simplified_workflow/content_generator.py#L110-L119)) and added LO/KT sections if generated.

* **Development Docs:** Update or add any relevant docs in `dev_docs/`:

  * **Launch & Environment Readiness:** Confirm it reflects using `requirements.txt` for deps. It can note that the batch script handles most setup.

  * **Module Explanations:** If there’s a `dev_docs/Repository Investigation` or similar, update it with the new structure (no showup\_tools, now simplified\_workflow, etc.). This helps future maintainers.

  * **Blueprint Document:** Optionally, include this refactoring plan (or a summary) in the repo’s dev docs for historical context.

* **Build/Packaging Instructions:** If the project is meant to be packaged (e.g., via PyInstaller, since `workflow_app.spec` was present), update those as well:

  * Check `workflow_app.spec` or any PyInstaller configs to ensure they reference the correct modules (e.g., include `simplified_workflow` and `showup_core`, remove `showup_tools`). Update the spec file if needed so that building an executable includes our new packages.

  * Document how to build the standalone app (if that’s a use-case): “Run `pyinstaller workflow_app.spec` to generate an executable” (adjust instructions if different).

* **Verify Documentation Accuracy:** Pretend to be a new developer/user – follow the README steps in a fresh clone of the repository. You should be able to set up and run the app as described. Ensure all commands and file paths mentioned are correct.

* **Expected Outcome:** Documentation is thorough, accurate, and easy to follow. It should be apparent that the project is a single-purpose application. Users and contributors will understand how to set up the environment, what each part of the app does, and how the content generation process works without confusion from legacy references.

## **Task 9: Code Cleanup and Consistency 🎨**

**Objective:** Apply best practices for code style and maintainability across the repository. This includes conforming to PEP 8 standards, ensuring naming consistency, and removing any cruft from the refactoring.

* **PEP8 Compliance:** Run linters/formatters on the code:

  * Use `black` to auto-format the Python files (`simplified_workflow/**/*.py`, `showup_core/**/*.py`, and `main.py`). Ensure line lengths, indentations, etc., are standardized.

  * Use `flake8` or `pylint` to catch any remaining style issues or undefined names. Address warnings such as:

    * Unused imports (perhaps some remained after refactor).

    * Missing docstrings or comments if important (you can add brief comments for clarity in complex sections).

    * Long lines or inconsistent naming.

  * Use `isort` to organize imports (group standard library, third-party, and local imports properly).

* **Consistent Naming:** Check that module and class names follow conventions:

  * All Python files/modules should be snake\_case (they are, mostly).

  * Class names in Kivy UI (if any besides `WorkflowApp`) should be CapWords. Function and variable names should be lowercase\_with\_underscores.

  * For example, if any variable is named in camelCase, convert it to snake\_case for consistency.

  * Ensure the naming of `simplified_workflow` package and its modules is fine (it is descriptive; keep it).

* **Remove Redundant Code/Comments:** During refactoring, some code may have been left commented out or marked TODO. Remove commented-out blocks that are no longer needed and turn TODO comments into actionable items (or remove if outdated).

  * Specifically, if `simplified_workflow.workflow` or others have blocks of code that were disabled (e.g., old batch processing sections, legacy compatibility code), strip those to reduce confusion. For instance, if there's any `# Batch processing functionality removed as per requirement` comments and related code, you can remove those sections entirely to streamline the code[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/showup_tools/workflow.py#L32-L40).

* **Logging Consistency:** Ensure all print statements have been replaced by proper logging (it appears they have). Verify the logging configuration works (should log to both console and file with UTF-8 encoding[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/showup_tools/workflow.py#L43-L51)[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/showup_tools/workflow.py#L75-L84)). No action likely needed here aside from confirming no stray `print()`.

* **Retest After Formatting:** Run the test suite one more time after applying formatting and minor refactors. Occasionally, changing formatting can introduce subtle issues (though black is usually safe). All tests should pass, confirming that our cleanup didn’t alter functionality.

* **Expected Outcome:** The codebase is clean and professional. It adheres to PEP 8 standards, making it easier to read and contribute to. There are no linting errors or warnings. The functionality remains the same after these cosmetic changes (all tests still green).

## **Task 10: Final Verification and Release Prep ✅**

**Objective:** Conduct a final round of testing and prepare the project for stable use or release, making sure all pieces fit together perfectly.

* **Full Integration Test:** Run an end-to-end test of the application:

  * Use a real or sample CSV input and (optionally) a sample PDF handbook. For example, create a small CSV with one or two content entries (with Module, Lesson, Step, etc.) and a short content outline, and use a dummy PDF (or markdown) handbook if available.

  * Launch the Kivy app and execute the workflow. Monitor the logs and UI: the progress bar should move, status messages should update for each stage (“Workflow started…”, “progress: X%”, then “Workflow finished: success” with counts).

  * After completion, open the output directory and inspect the generated markdown file. Ensure it contains the expected content structure (wrapped in `<educational_content>` tags, etc.), and that if a handbook was provided, relevant info was inserted (the RAG system prefixes relevant chunks with `===RELEVANT HANDBOOK SECTIONS===`, which should appear if handbook was used[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/simplified_workflow/content_generator.py#L124-L132)[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/simplified_workflow/content_generator.py#L126-L134)).

  * If multiple steps were in the CSV, verify that multiple output files were created accordingly.

* **Error Handling Checks:** Try a couple of edge cases:

  * Start workflow without selecting a CSV (the default path is provided, but simulate a missing file or an empty CSV). The app should show a red error status (e.g., “CSV file not found”) and not crash[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/main.py#L140-L148)[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/main.py#L142-L145).

  * Provide an invalid handbook path – the app should warn and continue without handbook[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/main.py#L147-L155).

  * Possibly simulate an AI API failure (if feasible, e.g., by providing an invalid API key). The system should catch exceptions and update the UI with an error message (like “Workflow Error: ...” in red) without hanging the UI thread[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/main.py#L210-L219)[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/main.py#L238-L243).

* **Performance Consideration:** If the CSV is large or content generation slow, verify that running in a background thread (with the progress queue) works smoothly, and the UI stays responsive. The design uses a thread and Kivy Clock for progress polling[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/main.py#L97-L101)[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/main.py#L220-L228), which is good. Just confirm no UI freezing during generation.

* **Version Bump:** If using versioning (as in `pyproject.toml` shows version 1.0.0[GitHub](https://github.com/helloshowup/hope-clean/blob/71ef5bde23a2aa89e1c139e4a172e30774690daa/pyproject.toml#L5-L13)), consider bumping the version to `1.1.0` to mark the significant refactor. Update it in `pyproject.toml` and any `__version__` variables if present.

* **Changelog:** It’s good practice to document changes. Create or update a `CHANGELOG.md` summarizing what was done in this refactor (e.g., “Removed legacy UI, streamlined application to single workflow, pinned dependencies, etc.”). This helps users understand the differences if they were using an older version.

* **Git History Check:** Review the Git commit history to ensure each task’s changes are captured in separate commits with clear messages. If any commit is too large or mixes concerns, use interactive rebase to split or reword as needed (this is more of a manual VCS step rather than Codex, but worth noting).

* **Final Commit & Merge:** Once verified, push the changes and merge the refactoring branch into `main` (if using PR workflow). Ensure CI tests (if any) pass on the main branch.

* **Post-merge Smoke Test:** Do one last run of `launch_kivy_app.bat` from the main branch code to double-confirm everything works from a fresh start.

* **Expected Outcome:** The refactored application is thoroughly tested and ready for use. All goals are met: the repository is streamlined to only the necessary code, the Kivy app is stable and tied into the content generator, dependencies are locked down, and documentation is up-to-date. We have high confidence in the app’s functionality and maintainability going forward.

---

By following these tasks sequentially, we will have methodically transformed the project into a clean, focused state. Each step can be executed and verified independently, ensuring that the refactor does not break existing functionality. Good luck with the implementation, and enjoy your simplified ShowUpSquared Content Generator\!

