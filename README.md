# **ShowUp AI Content Generation Workflow Overview**

## **Introduction and Launching the Workflow**

This repository implements an **AI-driven content generation pipeline** for educational materials. The workflow is accessible through a Kivy-based GUI launched via **`launch_kivy_app.bat`**, which sets up a Python virtual environment and runs the main Kivy app[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/launch_kivy_app.bat#L46-L54). The Kivy interface allows a developer or content designer to provide inputs (like a CSV of lesson outlines, an optional student handbook file for context, output directory, etc.) and then initiates the automated content generation process. Upon launch, the app prompts you to select a CSV file containing content definitions and (optionally) a student handbook PDF for reference, then you can start the **workflow**.

**Key components on startup:**

* *Environment Setup:* The batch script ensures Python is available, creates/activates a virtual environment, and installs required packages before launching the app[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/launch_kivy_app.bat#L16-L24)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/launch_kivy_app.bat#L34-L42).

* *Kivy App UI:* The GUI (driven by `main.py`) provides fields to input a content CSV, toggle handbook usage, specify output locations, and preview a learner profile[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/main.py#L18-L26)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/main.py#L136-L144). It also shows a status label, progress bar, and output preview area to monitor the workflow stages.

* *Launching Pipeline:* Clicking the **Start Workflow** button now runs the full pipeline using `simplified_workflow.run_workflow`. The progress bar and status messages reflect real execution results.

## Prompt Management System

Prompt templates for each workflow stage are stored under the repository's
`prompts/` directory. Files like `prompts/planning_prompt.txt` define the text
sent to the LLM. Modify these files—or point the configuration at a custom
folder—to change how the models are prompted. Avoid hard-coding large prompt
strings in Python modules.

## **AI Content Generation Pipeline Stages**

Once initiated (either via the GUI or programmatically), the content generation workflow proceeds through several **stages**, each handled by AI models and supporting modules. Below is a high-level overview of the pipeline stages:

### MERMAID
flowchart TD
    A[Start: Launch Kivy App] --> B["Planning Stage<br/>(Generate Lesson Plan)"]
    B --> C["Refinement Stage<br/>(Critique & Improve Plan)"]
    C --> D["Generation Stage<br/>(Create Content Versions)"]
    D --> E["Comparison Stage<br/>(Evaluate & Combine)"]
    E --> F["Review Stage<br/>(Tailor to Learner)"]
    F --> G["Finalization<br/>(Add LO/KT, AI Check, Save)"]
    G --> H[Workflow Complete!]

### **1\. Planning Stage**

**Goal:** Create a structured lesson or content **plan** (in JSON) based on the outline provided.

In this stage, the system uses a prompt template (by default `prompts/planning_prompt.txt`) to guide an AI model (e.g. Anthropic Claude or OpenAI GPT) in generating a sequence of *content blocks* for the lesson[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/prompts/planning_prompt.txt#L14-L22)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/prompts/planning_prompt.txt#L24-L27). The content outline, target learner profile, and rationale from the CSV are injected into the prompt[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/planning_stage.py#L40-L48)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/planning_stage.py#L54-L62). The AI responds with a JSON plan consisting of an ordered list of blocks (e.g. introduction, explanation paragraphs, image placeholders, etc.).

**Dynamic Blocks:** The planner leverages a “block library” of content block definitions to diversify the lesson structure[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/prompts/planning_prompt.txt#L14-L22). For example, the prompt encourages inserting `image_placeholder` or `diagram_placeholder` blocks periodically to create visual breaks in text[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/prompts/planning_prompt.txt#L14-L22). (These placeholders signal where visuals might go, to improve readability.) The plan intentionally **omits learning objectives and key takeaways blocks**, as those will be generated automatically in a later stage[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/prompts/planning_prompt.txt#L16-L19)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/prompts/planning_prompt.txt#L19-L22).

**Output:** An initial content plan (JSON) is produced and stored in `row_data_item["initial_plan"]` if successful[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/planning_stage.py#L92-L100). The status is marked `PLAN_GENERATED` on success[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/planning_stage.py#L94-L101).

### **2\. Refinement Stage**

**Goal:** Refine and finalize the lesson plan from Stage 1\.

The initial AI-generated plan may be further refined through a critique-and-revision step. In refinement, the system prompts the AI (using critique/refinement prompt templates) to review the plan for any issues or gaps and suggest improvements. This stage uses a separate model or prompt (configurable via `refinement_model` and prompt paths) to achieve a higher quality plan[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L346-L355)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L358-L365). The result is a **finalized lesson plan** (`final_plan`) ready for content generation. If refinement succeeds, status updates to `PLAN_FINALIZED`; otherwise an error is logged for this row[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L356-L364).

*(Note: The refinement stage ensures the content outline is instructionally sound and ready for actual content writing. If skipped or if the initial plan was already high-quality, the pipeline can proceed with the original plan.)*

### **3\. Generation Stage**

**Goal:** Produce the actual content (lesson script) based on the finalized plan.

Using the final plan, the workflow now generates **three versions** of the content for each lesson/step. It fills in the detailed content for each block defined in the plan. This is done by calling the AI content generator with the plan and relevant variables. By default, the system generates three alternate versions to later compare[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L367-L375)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L445-L451). Each version is a full draft of the lesson content.

Before generation, the system can inject additional context: if a *Student Handbook* is provided and the user enabled handbook integration, the pipeline performs a **retrieval-augmented generation (RAG)** step. It uses the content outline as a query to fetch relevant snippets from the handbook (via a vector database of the handbook text)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L219-L228)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L241-L250). These retrieved snippets (if any) are appended to the prompt variables as `{{student_handbook_info}}` and the prompt template is adjusted to include this information[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L378-L387)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L389-L397). This ensures the AI can draw on actual handbook policies or facts while generating content, rather than hallucinating. (If no relevant handbook info is found, or no handbook is provided, this step is skipped.)

After optionally adding handbook context, the system sets up the generation parameters (AI model, token limits, temperature, etc.) and calls the Claude API to **generate three content drafts**[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L436-L445)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L447-L456). Each draft is parsed to extract only the educational content portion (stripping any metadata or JSON, if present)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L452-L460)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L462-L470). The raw generations and the extracted clean content are saved to disk (`generation_results/*.json`) for debugging or review[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L459-L467)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L469-L472).

**Output:** `row_data_item["generated_versions"]` contains the three full content drafts, and `["extracted_generations"]` holds the cleaned text for each[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L452-L460)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L462-L470). Status updates to `GENERATION_COMPLETE` if successful.

### **4\. Comparison & Selection Stage**

**Goal:** Evaluate multiple generated versions and pick the best one.

With several candidate contents available, the pipeline automatically **compares and combines** them to select the strongest version. This is handled by `content_comparator.compare_and_combine`, which uses AI to analyze the differences between versions and identify the best elements[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L500-L508)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L516-L524). The comparison may consider factors like alignment with the outline, clarity, and the learner profile. It produces a single **“best” version** of the content and an explanation of why it was chosen.

Internally, the comparator may be prompted with all extracted versions and asked to choose the optimal one (this can involve another AI call). The pipeline provides a comparison context including the target learner profile and adjacent lessons (to maintain continuity)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L500-L508)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L502-L510). If the combine step fails for any reason, the system gracefully falls back to the first generated version as a default[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L540-L548)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L550-L554).

**Output:** `row_data_item["best_version"]` is set to the selected content, and a textual `comparison_explanation` may be stored for reference[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L516-L524)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L526-L534). Intermediate comparison results are saved to `comparison_results/*.json`[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L524-L532)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L533-L539).

### **5\. Review Stage**

**Goal:** Review and refine the chosen content for the target audience.

In this stage, the **best version** of content is passed through a final review tailored to the target learner profile. The `content_reviewer.review_content` function (likely another AI prompt) looks at the lesson through the lens of the given learner profile and makes any necessary edits or suggestions[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L579-L588)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L590-L598). For example, it might simplify language for younger learners, enhance examples, or ensure tone and reading level are appropriate.

The review stage returns an **edited content** (if changes were needed) and an `edit_summary` describing what was adjusted[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L589-L597)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L599-L608). This could involve fixing any lingering issues, improving coherence, and making the content more “human-like” or engaging. On success, the pipeline updates `row_data_item["reviewed_content"]` with the final polished content[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L590-L598)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L602-L608).

*(If the review step fails or produces an error, the system will log it and fall back to the unreviewed best version to ensure the workflow can continue)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L613-L621)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L623-L626).*

### **6\. Finalization Stage**

**Goal:** Apply final touches (learning objectives, key takeaways, AI pattern check) and save the content output.

In the last stage, the system adds any remaining elements and performs quality checks before outputting the content:

* **Automated LO & KT Insertion:** The workflow generates **Learning Objectives (LO)** and **Key Takeaways (KT)** for the lesson using the final reviewed content. It calls an AI prompt designed for this purpose (`learning_sections.generate_lo_and_kt_from_content`) which returns formatted markdown text for the LO and KT sections[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L647-L655). These sections are then inserted into the content at appropriate positions: typically, Learning Objectives are added right after the introduction, and Key Takeaways are appended to the end[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L650-L657)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L653-L656). This automation ensures every lesson has clearly stated objectives and summary points, without requiring the author to write them manually. (If the LO/KT generation fails for some reason, the pipeline logs an error and continues without them[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L657-L665)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L659-L660).)

* **AI-Generated Text Detection:** To maintain quality and authenticity, the pipeline scans the final content for telltale **AI-generated patterns or phrases**. It uses a set of regex patterns and common AI phrases defined in an `ai_patterns.json` to flag sentences that sound overly AI-generated or disclosive of AI (e.g., “As an AI, I ...”)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/ai_detector.py#L432-L441)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/ai_detector.py#L459-L467). This **AI Detection** step (`run_ai_detection_stage`) returns a list of any flagged patterns with their positions[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/ai_detector.py#L432-L440)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/ai_detector.py#L455-L463). These flags (if any) are stored in `ai_detection_flags`[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L657-L665). *(At present, the content is not automatically edited in response to these flags in the Kivy workflow; the flags serve as guidance for a human editor. The companion editor UI, however, has an **AI content editor** that can suggest human-like rewrites for flagged text, see below.)*

* **Saving Output:** Finally, the pipeline saves the completed content to the specified output directory. The content is saved in a structured Markdown format with metadata. The `output_manager.save_as_markdown` function composes a Markdown file that includes front-matter metadata (module, lesson, step, etc.) and the content with appropriate sections[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L669-L677)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L679-L683). A JSON log of the final content and any AI-detected patterns is also saved for reference in `final_content/*.json`[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L685-L693)[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L695-L703). The workflow then marks the status as **completed** for that content piece[GitHub](https://github.com/helloshowup/hope-clean/blob/4fccb1237fdb87e687769a0337dcec36ddc92ed0/showup_tools/workflow.py#L709-L717).

Once finalization is done, the pipeline moves on to the next row in the CSV (if any) or concludes if all content pieces are processed. The Kivy UI would then display a “Workflow Complete\!” message, and the generated content can be reviewed by opening the output files.

### **Key Features and Implemented Enhancements**

This project is under active development and has several recently implemented features. As you onboard, familiarize yourself with the following enhancements that are now part of the repository:

* **Integrated Workflow in Kivy UI:** The Kivy app now runs the real pipeline by invoking `simplified_workflow.run_workflow` in a background thread when you click "Start Workflow," enabling end-to-end content generation directly from the UI.  
* **Automated Learning Objectives & Key Takeaways:** The finalization stage of the workflow now automatically generates and inserts "Learning Objectives" and "Key Takeaways" sections into the content. This feature relies on the AI's ability to correctly format the output with "\#\# Learning Objectives" and "\#\# Key Takeaways" headings. Basic parsing checks and error handling are in place.  
* **Dynamic Handbook RAG:** The dynamic handbook integration is now live. It uses a vector database for retrieval-augmented generation, which injects relevant handbook snippets into the content prompt. A caching layer stores query results, and a `textbook_vector_db` is employed for semantic search.  
* **Flexible Content Structure:** The system now uses a dynamic, block-based content structure for varied and well-paced lessons. The workflow can adapt to different content formats, such as narrative articles, slide decks, or interactive quizzes, by using different prompt templates and block definitions. The selection of templates is handled by a `template_type` field.  
* **AI-Powered Editing:** The finalization stage now flags AI-sounding text, and the `showup_core/ai_logger` and Editor UI contain functions, such as `ai_detector.edit_content`, to rewrite AI-like content using Claude. This is an optional step that can be run automatically if certain AI indicators are detected and the user opts in.



## Repository Structure and Import Strategy
To ensure a clean, maintainable, and robust codebase, the project adheres to standard Python packaging practices. All modules are configured for automatic discovery, eliminating the need for manual `sys.path` modifications or custom import hooks.

**Key Principles:**

* **Standardized Package Naming**: All package directories now follow standard Python naming conventions (e.g., `showup_core` instead of `showup-core`). This ensures consistency between directory names and import statements.
* **Automatic Package Discovery**: The `pyproject.toml` configuration is set up to automatically discover all packages within the project root, simplifying dependency management and installation.
* **No Manual Path Adjustments**: Manual additions to `sys.path` (e.g., `sys.path.insert(0, p)`) and custom import hooks like `ShowupToolsPathFinder` have been removed. The standard Python import mechanism is now fully relied upon. This improves reliability and reduces potential import errors.

Developers should ensure new modules or refactored components adhere to these principles for seamless integration.
