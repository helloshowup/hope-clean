# **Guide: Dynamic Content Block Generation Process (Workflow v2)**

## **1\. What is the Block Approach?**

Traditionally, content generation might use a fixed template (e.g., a Markdown file with pre-set headings and sections). The AI would then fill in the blanks.

The **Block Approach** in Workflow v2 is different:

* It's a **dynamic template generation** system. The AI doesn't just fill a template; it *designs* the template itself.  
* It uses a library of modular content "blocks" as its building components.  
* This process primarily occurs in the **Planning Stage (Stage 2\)** and is refined in the **Refinement Stage (Stage 3\)**.

**Goal:** To create highly flexible, pedagogically sound, and visually balanced lesson structures tailored to specific inputs, rather than fitting content into a rigid mold.

## **2\. The "Block Library": Your Content LEGO Bricks**

The foundation of this approach is the **Block Library**. This is a formal specification of all available content components that the AI Planner Agent is explicitly "taught" via its prompt.

Each block type in the library has:

* **`block_type`**: A unique identifier (e.g., `introduction`, `explanatory_text`, `learning_objectives`, `diagram_placeholder`, `audio_placeholder`, `key_takeaways`, `example_analysis`, `process_steps`, `reflection_prompt`, `section_heading`).  
* **`purpose`**: A clear description of what this block is intended to achieve pedagogically (e.g., "to engage the learner," "to deliver core concepts," "to provide a visual break," "to outline a sequential process").  
* **`attributes`**: Specific fields relevant to that block type that the AI needs to populate (e.g., `title`, `content_summary`, `objectives`, `description`, `suggested_duration_seconds`, `example_title`, `steps`).  
* **`placement guidelines`**: General rules about where this block typically appears in a lesson (e.g., `learning_objectives` usually near the start, `key_takeaways` at the end).  
* **`Output Format`**: How the block should be represented in the final generated content (e.g., a Markdown heading, a paragraph, a bulleted list, a specific placeholder tag).

**Where it's defined:** The Block Library specification is embedded within the Planner Agent's prompt (`prompts/planning_prompt.txt`) \[cite: Research Validation of AI Content Generation Workflow.md\], often in a concise, type-definition style to optimize token usage.

## **3\. Stage 2: The Planning Stage (The "Architect")**

In this stage, the AI Planner Agent acts as an "Instructional Design Architect." It receives a comprehensive "brief" for each lesson step, drawn from the CSV input.

**Inputs to the Planner Agent:**

* **`Lesson Title`**: The main heading for the content.  
* **`Content Outline`**: The core subject matter to be covered.  
* **`learner_profile`**: The target audience (influences tone, complexity, block choices).  
* **`rationale`**: The specific purpose or intent of *this particular lesson* (e.g., "provide a concise overview," "deep dive with practical examples"). This is crucial for guiding the AI's structural decisions.  
* **`word_count`**: The target length of the final content.

**The AI's Dynamic Construction Process:**

1. **Block Selection:** Based on the `Content Outline`, `learner_profile`, and especially the `rationale`, the AI intelligently decides *which* block types are most appropriate for this specific lesson. For example, a "deep dive" rationale might lead to more `example_analysis` or `process_steps` blocks, while a "concise overview" might favor `explanatory_text`.  
2. **Block Ordering:** The AI arranges the selected blocks in a logical, pedagogically sound sequence, respecting general flow (e.g., `introduction` before main content, `reflection_prompt` before `key_takeaways`).  
3. **Content Summarization (within blocks):** For each chosen block, the AI populates its specific attributes with concise summaries or descriptions relevant to *this particular lesson*. For instance, an `explanatory_text` block will get a `topic` and `key_points` that outline what that section should cover, but not the full lesson text yet.  
4. **Visual and Media Breaks:** The AI is explicitly guided to strategically insert `image_placeholder`, `audio_placeholder`, or `video_placeholder` blocks. These are placed to break up "walls of text" and enhance visual balance, even if the media is generic. They are balanced with content-specific `diagram_placeholder`/`flowchart_placeholder` blocks when the content outline calls for a specific visual.  
5. **Intentional Omission of LOs/KTs:** The Planner *intentionally omits* `learning_objectives` and `key_takeaways` blocks from this initial plan. This is because these elements are now generated automatically and inserted later in Stage 5, derived directly from the *final, generated content* \[cite: Integrating Visual Breaks and Automated Learning Outcomes.md\].

**Output: The `initial_plan` (The First Draft of the Dynamic Template)**

The output of the Planning Stage is the `initial_plan`. This is a **structured JSON object** (not a Markdown file\!) that represents the dynamically constructed template. It contains a `content_blocks` array, where each element is a JSON object defining a specific content block type with its populated attributes.

Example Structure:

```
{
  "content_title": "Understanding Motivation Cycles",
  "target_audience": "Adult Learners",
  "estimated_word_count": 800,
  "content_blocks": [
    {
      "block_type": "lesson_metadata",
      "title": "1.6 Motivation Strategies",
      "module_id": "1.6"
    },
    {
      "block_type": "introduction",
      "content_summary": "Engage learners with a question about motivation dips.",
      "hook_suggestion": "Relatable scenario."
    },
    {
      "block_type": "section_heading",
      "level": 2,
      "title": "Understanding Motivation Cycles"
    },
    {
      "block_type": "explanatory_text",
      "topic": "Motivation as a cyclical process",
      "key_points": ["Not constant", "Predictable patterns", "Proactive strategies"],
      "tone_suggestion": "informative"
    },
    {
      "block_type": "image_placeholder", // Generic visual break
      "description": "An image of a person overcoming an obstacle.",
      "caption": "Staying motivated through challenges."
    },
    {
      "block_type": "list_block",
      "list_type": "numbered",
      "heading": "Practical Motivation Strategies",
      "items_summary": ["SMART micro-goals", "5-minute rule", "Accountability"]
    },
    {
      "block_type": "audio_placeholder", // Audio break
      "topic": "Expert tips on focus",
      "description": "Short audio clip with a productivity expert.",
      "suggested_duration_seconds": 60
    },
    // ... other blocks ...
  ]
}

```

## **4\. Stage 3: The Refinement Stage (The "Editor")**

The Critic Agent in Stage 3 takes this `initial_plan` (the first draft of the template) and acts as an "Editor."

* It critiques the structure and content summaries within the blocks.  
* It might suggest reordering blocks for better flow, adding a missing block type, removing a redundant block, or fleshing out the `description` or `key_points` within a block if they are too vague.  
* The output of this stage is the `final_plan`, which is the refined version of this dynamic, block-based template.

## **5\. Stage 4: The Generation Stage (Filling the Template)**

Finally, the Content Generator AI in Stage 4 receives this `final_plan`.

* It **iterates through each block** in the `content_blocks` array of the `final_plan`.  
* For each block, it uses targeted prompts to generate the detailed, full-text content for that specific block, thus "filling" the dynamic template.  
* For `diagram_placeholder`, `flowchart_placeholder`, `audio_placeholder`, and `video_placeholder` blocks, the AI generates **detailed textual descriptions** of the required visuals or audio content, making them actionable for later media creation.

## **Benefits of the Block Approach**

* **Flexibility:** No more rigid templates. The lesson structure adapts to the specific content, learner, and rationale.  
* **Pedagogical Soundness:** The AI is guided to build well-structured lessons with appropriate pedagogical elements.  
* **Visual Balance:** Automated insertion of generic image/media placeholders ensures readability and breaks up long text sections.  
* **Modularity:** Content is broken down into manageable, reusable components.  
* **Scalability:** Easier to add new types of content blocks in the future.  
* **Consistency:** Ensures key elements (like LOs/KTs) are always present and correctly formatted, even if generated post-content.

This block-based approach provides a powerful and intelligent way to generate diverse, high-quality educational content.

