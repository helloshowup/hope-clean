# **Blueprint: Advanced Content Generation Workflow**

This document outlines the redesigned, multi-stage workflow for the content generator, based on the findings from the research document *"A Technical Guide to Implementing a Plan-Then-Generate Workflow."* This blueprint will serve as the technical specification for the AI Coder to implement the Priority 3 refinements.

### **Guiding Principles**

* **Modular Stages:** Each step in the workflow will be a distinct, self-contained function, making the system easier to test, maintain, and debug.  
* **Structured Data Transfer:** All data passed between stages will be in a structured **JSON** format to ensure reliability and robustness.  
* **Stateful Tracking:** The central `row_data_item` dictionary will be updated at each stage to provide a complete, auditable record of the entire process.

### **The Redesigned Workflow (Per CSV Row)**

This new process expands the original workflow into five distinct, sequential stages.

#### **Stage 1: Initialization & RAG**

*This stage is largely unchanged but sets the foundation for the new steps.*

1. **Input:** A single row from the input CSV file.  
2. **Process:**  
   * The `run_workflow` function reads the row data (`Content Outline`, `Learner Profile`, etc.).  
   * If the "Student Handbook Integration" is enabled, the RAG system is triggered here. It extracts relevant handbook information.  
3. **Output:** The initial `row_data_item` dictionary is created. It contains the raw inputs and any context retrieved from the RAG system.  
   * `row_data_item['status']` is set to `INITIALIZED`.

#### **Stage 2: The Planning Stage (Planner Agent)**

*This is the first new stage, focused on creating a detailed blueprint for the content.*

1. **Input:** The `row_data_item` dictionary, specifically using the `Content Outline`.  
2. **Process:**  
   * A new function, `run_planning_stage`, is called.  
   * It uses the **Hybrid "CREATE" Method Prompt** (Research Example 3\) to instruct the AI to act as a "Planner Agent."  
   * The AI generates a detailed plan for the educational video.  
3. **Output:**  
   * The AI's response is parsed as a **JSON object**.  
   * The `row_data_item` is updated:  
     * `row_data_item['initial_plan']` \= The parsed JSON plan.  
     * `row_data_item['status']` is set to `PLAN_GENERATED`.

#### **Stage 3: The Refinement Stage (Critic Agent)**

*This stage uses a second AI call to critique and improve the initial plan, ensuring pedagogical quality.*

1. **Input:** The `row_data_item`, now containing the `initial_plan` and the `Learner Profile`.  
2. **Process:**  
   * A new function, `run_refinement_stage`, is called.  
   * It uses the **Planner-Critic Prompting Pattern** (Research Section 4). The prompt instructs the AI to act as a "Critic Agent."  
   * The Critic AI evaluates the `initial_plan` against the `Learner Profile` and other criteria.  
3. **Output:**  
   * The AI's response is a single JSON object containing two keys: `critique` and `revised_plan`.  
   * The `row_data_item` is updated:  
     * `row_data_item['plan_critique']` \= The critique text.  
     * `row_data_item['final_plan']` \= The `revised_plan` JSON object.  
     * `row_data_item['status']` is set to `PLAN_FINALIZED`.

#### **Stage 4: The Generation Stage**

*This stage now uses the high-quality, finalized plan to generate the three content versions.*

1. **Input:** The `row_data_item`, specifically using the `final_plan`.  
2. **Process:**  
   * The existing `generate_three_versions` function is called.  
   * Its prompt is re-engineered to take the detailed `final_plan` (not the original `Content Outline`) as its primary instruction set.  
   * **Contextual prompting** is used to prevent repetition between the three versions.  
   * API parameters (`frequency_penalty`, `presence_penalty`) are used as a safeguard against redundancy.  
3. **Output:**  
   * Three distinct versions of the video script content.  
   * The `row_data_item` is updated:  
     * `row_data_item['generated_versions']` \= A list containing the three scripts.  
     * `row_data_item['status']` is set to `GENERATION_COMPLETE`.

#### **Stage 5: Comparison, Review, and AI Detection**

*This final stage combines, reviews, and runs a final quality check on the generated content.*

1. **Input:** The `row_data_item`, containing the `generated_versions`.  
2. **Process:**  
   * **Comparison & Review:** The existing `compare_and_combine` and `review_content` functions are executed sequentially to produce a single, polished draft.  
   * **AI Detection (New Sub-Stage):**  
     * A new function, `run_ai_detection_stage`, is called.  
     * It loads the phrases and regex patterns from the `ai_patterns.json` file.  
     * It scans the polished draft for any matches.  
3. **Output:**  
   * The final, polished content is saved to the output directory.  
   * The `row_data_item` is updated:  
     * `row_data_item['ai_detection_flags']` \= A list of any flagged phrases and their locations in the text.  
     * `row_data_item['final_content_path']` \= The path to the final file.  
     * `row_data_item['status']` is set to `WORKFLOW_COMPLETE`.

This blueprint provides a clear and robust plan for evolving the application into a more powerful and reliable content generation engine.

