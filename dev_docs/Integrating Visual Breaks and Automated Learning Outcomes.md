# **Integrating Visual Breaks and Automated Learning Outcomes**

## **Planner Prompt: Inserting Image Placeholders for Visual Balance**

To avoid “walls of text,” we need to guide the Planner agent to add image placeholders at strategic points purely for layout. The planning prompt should include explicit instructions (and possibly new block definitions) for inserting these visual breaks. The emphasis is on distributing images evenly rather than tying every image to specific content. For example, we might add a line in the planning prompt like:

*“Include occasional `image_placeholder` blocks (generic visuals) to break up long sections of text. Aim to insert one roughly after every 2–3 explanatory\_text blocks or \~300 words of continuous text. These images do not need to illustrate a specific point; their purpose is to make the lesson more readable by giving the eye a rest.*”\*

**Heuristics for Placement:** We can provide the AI Planner with concrete rules, such as:

* **Frequency Rule:** After every 2–3 consecutive `explanatory_text` blocks, insert an `image_placeholder` block to break up the content.

* **Length Rule:** If a single explanatory block exceeds \~250–300 words, consider splitting it by inserting an image placeholder in between (or immediately after it).

* **Section Breaks:** At natural transition points (e.g. between major subtopics or sections), add an image placeholder if no other visual (diagram/flowchart) is present.

* **Introduction/Conclusion:** Optionally suggest a placeholder image early on (after introduction) or midway through long lessons, even if it’s just a generic illustrative graphic, to improve visual appeal.

By embedding these guidelines in the Planner’s prompt, the AI will treat visual balance as a requirement. For instance, the prompt could say: *“When planning content\_blocks, ensure no more than 3 text-heavy blocks appear in a row without an image or visual break. Use a `diagram_placeholder` or a generic `image_placeholder` block with a brief description to serve as a visual break.”* This steers the Planner to include placeholders even if they are only loosely related to the surrounding text. The key is to **prioritize readability and layout** – images and graphics “give rest points for the reader’s eyes” even if they are not strictly required by the content.

In terms of implementation, it may be simpler to treat these visual breaks as their own block types (see Block Library updates below). Alternatively, a `layout_suggestion` attribute could be added to an `explanatory_text` block (e.g. `"layout_suggestion": "insert image after"`), but using a dedicated block is more straightforward. The Planner can then output something like:

```json
{
  "block_type": "diagram_placeholder",
  "concept_to_illustrate": "General illustrative image",
  "description": "An image to break up text, showing a relevant scene or concept",
  "placement_suggestion": "after the third paragraph"
}
```

Such a block would signal the generator to insert a generic image description at that point. We can leverage existing placeholder types (like `diagram_placeholder`) for this purpose – e.g., use a `diagram_placeholder` with a generic `"concept_to_illustrate"` if we don’t introduce a new type. The block instructions already support diagram placeholders (they prompt the AI to produce a textual diagram description). By guiding the Planner to include these periodically, we ensure a visually balanced lesson layout.

## **Prompt Structure for Post-Generation Learning Objectives & Key Takeaways**

Once the lesson content is fully written (the `reviewed_content`), we want to derive **Learning Objectives (LOs)** and **Key Takeaways (KTs)** directly from it. We’ll create a specialized prompt (used by a Stage 5 sub-agent) that feeds in the final content and asks for succinct objectives and takeaways. The prompt should instruct the AI to carefully **reflect the actual content** of the lesson in these outputs, since they must align with what was covered.

A strong prompt structure would be:

* **System / Role Prompt:** e.g. *“You are an expert instructional designer. Given a lesson’s content, generate educational summaries.”* This sets the context that we want objectives and summaries from the text.

* **User Prompt Content:** We then provide the final lesson text (perhaps enclosed in triple backquotes or a delimiter) as context. After that, we explicitly ask for:

  1. **Learning Objectives:** “Generate 1–3 clear, measurable learning objectives that a student will achieve by completing the lesson.” We should mention SMART criteria (Specific, Measurable, Achievable, Relevant, Time-bound) and the use of strong action verbs from Bloom’s taxonomy. For example: *“By the end of this lesson, students will be able to… \[objective\].”*

  2. **Key Takeaways:** “Generate 2–4 concise key takeaways summarizing the most critical points of the lesson content.” Emphasize that these should be the *major insights or facts* a learner should remember. They should be written in clear, direct language focusing on practical or memorable points.

* **Formatting Instructions:** Instruct the AI to output the objectives and takeaways in Markdown format, under proper headings. For example, the prompt might say: *“Format your answer as two sections. First, under the heading `## Learning Objectives`, list each objective as a bullet point. Then, under the heading `## Key Takeaways`, list each takeaway as a bullet point.”* This ensures the result is ready to insert. We have evidence that a similar instruction was used in the editor: the tool explicitly told Claude to *“format them as a bulleted list under a 'Learning Objectives' heading at the very beginning of the document”*.

Combining these, an **optimal prompt** to the AI could look like:

```
SYSTEM: You are a veteran curriculum designer. You will read a lesson and extract its learning goals and summary points.

USER: 
""" 
<Lesson Content in Markdown> 
"""

Tasks:
1. **Learning Objectives:** Write 1-3 bullet-point objectives that describe what a learner will be able to do after this lesson. Use SMART criteria – be Specific, Measurable, Achievable, Relevant, and (if applicable) Time-bound:contentReference[oaicite:7]{index=7}. Start each objective with a strong action verb (e.g. *explain, analyze, create*). Ensure the objectives cover the key skills/knowledge from the lesson content.
2. **Key Takeaways:** Write 2-4 bullet-point key takeaways that summarize the most important points or insights from the lesson. These should be the crucial facts or concepts a student should remember. Use clear, concise language:contentReference[oaicite:8]{index=8}.

Format the output in Markdown with the following sections:

## Learning Objectives
- Objective 1...
- Objective 2...

## Key Takeaways
- Takeaway 1...
- Takeaway 2...
```

This prompt explicitly ties the LOs and KTs to the provided `reviewed_content`. It ensures the AI’s output is *grounded in the actual lesson text*. By doing this post-generation (instead of during initial planning), we capture the *actual delivered content* – making the objectives and takeaways accurate reflections of the final lesson.

Notably, this approach leverages the final content, so the AI can scan for the main topics and outcomes. For example, if the lesson covered three main ideas, the objectives should correspond to those ideas (e.g., *“Define X, Explain how Y works, Apply Z in context”*), and the takeaways might echo the conclusions of each section. The SMART criteria reminder ensures objectives are well-formed and actionable, not vague. And the action-verb guidance aligns with best practices (Bloom’s taxonomy).

## **Integrating LO/KT Generation in Stage 5 (Post-Processing)**

We will insert the LO/KT generation step into **Stage 5 of the workflow, right after content review and before AI plagiarism/detector scanning**. In the `finalize` phase of the workflow (Stage 5), the code currently does something like:

```py
reviewed_content = row_data_item["reviewed_content"]
# ... then immediately runs AI detection:
detection_flags = run_ai_detection_stage(reviewed_content, patterns_file=...)
row_data_item["ai_detection_flags"] = detection_flags
```

We want to intervene **after** we have `reviewed_content` but **before** we run `run_ai_detection_stage`. In practice, this means modifying the `finalize` phase in `workflow.py` around where `reviewed_content` is handled. For instance, in the code around saving reviewed\_content we see the detection being called. We will slot our new steps right before line 648 in that snippet.

**Proposed code integration:**

```py
# After obtaining reviewed_content from the review stage:
reviewed_content = row_data_item["reviewed_content"]

# New step: Generate Learning Objectives & Key Takeaways
try:
    lo_section, kt_section = generate_lo_and_kt_from_content(reviewed_content)
    reviewed_content = insert_sections_in_markdown(reviewed_content, lo_section, position="after_intro")
    reviewed_content = insert_sections_in_markdown(reviewed_content, kt_section, position="end")
    row_data_item["reviewed_content"] = reviewed_content
    logger.info("Inserted Learning Objectives and Key Takeaways into content")
except Exception as e:
    logger.error(f"LO/KT generation failed: {e}")
    # (Maybe proceed without halting the workflow, using content without LO/KT if this fails)
    
# Continue with AI detection on the updated reviewed_content
detection_flags = run_ai_detection_stage(reviewed_content, patterns_file=ai_patterns_path)
row_data_item["ai_detection_flags"] = detection_flags
```

In this pseudo-code, `generate_lo_and_kt_from_content()` would encapsulate the AI call described in the prompt above (feeding in `reviewed_content` and returning two strings: one for the “\#\# Learning Objectives” section and one for “\#\# Key Takeaways”). The helper `insert_sections_in_markdown()` would handle inserting a section into the Markdown text at the specified location. We’d implement it to find the correct insertion point:

* For `position="after_intro"` (Learning Objectives): locate the end of the introduction section or the first paragraph. For example, after the first `## Introduction` heading and its content. If the content doesn’t explicitly have an Introduction heading, we could insert right after the main title or after the first paragraph.

* For `position="end"` (Key Takeaways): append at the very end of the content. This likely comes after any conclusion or summary. We might insert before any closing tags if such exist (in some templates they wrap content in `<educational_content>` tags, but typically, we append just before `</educational_content>` or simply at the end of the markdown content).

Crucially, we format `lo_section` and `kt_section` with their Markdown headings included. For example, `lo_section` might be:

```
"## Learning Objectives\n- Students will be able to... (objective 1)\n- Students will be able to... (objective 2)\n"
```

And similarly for key takeaways. By generating the sections with headings, we make insertion straightforward (just find where to put the new block of text). In practice, if the lesson already has a “\#\# Learning Objectives” (from a previous run or plan), our code could replace or update it. But since our new approach keeps LOs out of the initial plan, there shouldn’t be an existing LO section to worry about.

Placing the LO section *towards the beginning* is typically right after the introduction. Many lesson formats present learning objectives upfront (often immediately after the introductory paragraph). Meanwhile, key takeaways often appear at the end as a post-summary reinforcement. By inserting KTs at the very end, we ensure they are the last thing the student sees, which is pedagogically sound (they serve as a recap of everything learned).

Integrating at this stage ensures that our final `reviewed_content` (which will be saved and maybe passed to the AI detector) now contains the newly generated **“Learning Objectives”** and **“Key Takeaways”** sections in the Markdown. The AI detection will then scan the full content including these sections (which is fine, as they are part of the final lesson). Finally, the content is saved to the output file.

## **Refining the Learning\_objectives.txt Prompt for Automation**

Previously, the **Learning\_objectives.txt** prompt (used in a manual editor tool) likely contained detailed instructions for the LLM on how to add objectives to a lesson. It may have included sections titled “Technical Approach,” “Surgical Insertion Procedure,” and “Command Structure.” These were probably guiding a human-in-the-loop or the AI on *how* to carry out the insertion, possibly with placeholders or special markers. Now that this process is automated in code, much of that prompt becomes unnecessary or should be reframed as internal guidance.

We should **strip out any parts of the prompt that describe *how to insert* the objectives into the content or any step-by-step technical method**, because the backend code handles that. For example:

* If *Technical Approach* explained the plan (e.g., “First, the AI will draft objectives, then the user will copy-paste them…”), this is not needed in the prompt anymore. The AI doesn’t need to know the multi-step plan; it just needs to output the objectives.

* If *Surgical Insertion Procedure* told the AI something like “Return the objectives wrapped in special tags so we can find and insert them” or instructing the AI to place them at a certain point in the text, we should remove those instructions. We no longer want the AI to output e.g. `<INSERT AT BEGINNING>` or any markers; the Python code will handle positioning. In automation, we want the AI’s output clean (just the markdown list for LOs and KTs).

* If *Command Structure* was a section detailing how the user or system should call this prompt (for instance, maybe it described a slash command or a specific input format), that too can be removed or turned into comments for developers. The AI doesn’t need to see those; our code will directly call the model with the proper prompt.

In short, the new prompt file for generating LOs might be simplified to just the essential instructions. It would read more like a direct task description (similar to the structure given in the section above) and less like an SOP document. For instance, instead of a long preamble, it might simply say:

*“Generate 3 bullet-point learning objectives for the lesson below, followed by 3-4 bullet-point key takeaways. The objectives should be SMART and start with action verbs. The key takeaways should summarize critical points. Provide them in separate sections with appropriate headings.”*

All the procedural detail about *how* these will be inserted or used can be left out of the prompt. Those details will live in the code (in comments or documentation), or as part of the system message that the AI doesn’t explicitly need to reason about. We already see in the editor’s logic that when the user triggered an LO insertion, the actual instructions to Claude were high-level and outcome-focused (e.g. “Add appropriate learning objectives at the beginning... Create 3-5 clear, measurable LOs... format as bulleted list under 'Learning Objectives' heading...”). There was no mention of *how* to technically insert them beyond their placement at the beginning. We should emulate that style in our automated prompt: focus on *what to produce*, not *how it will be used*.

Therefore, we will remove sections like "Surgical Insertion Procedure" (since our code now performs the insertion into the Markdown string) and any "Command Structure" instructions (which might have been artifacts of the manual UI expecting a certain output format or placeholders). Instead, our prompt can be concise and purely content-focused. Any behind-the-scenes logic (like “take the output and inject it after the title”) will be implemented in Python, not described in the prompt.

To summarize this refinement:

* **Keep**: Instructions about quality and format of LOs and KTs (SMART criteria, use bullet points, headings, action verbs, etc.), because the AI still needs to follow those.

* **Remove or internalize**: Instructions that say *where* to insert or *how* the system will use the output. The AI doesn’t need to output something like “(Insert above the introduction)” – our code knows to do that.

* **Rephrase**: If the prompt had any language like “This will be inserted into the lesson,” we can drop it or just ensure the AI includes the heading in the output (so it’s obvious where it fits). We might simply instruct: “Include a ‘\#\# Learning Objectives’ heading before listing the objectives.”

The result is a cleaner prompt that yields exactly the Markdown we need, without extra metadata. This aligns with the new fully-automated flow – the AI provides content, and the program takes care of integration.

## **Block Library Updates for Layout and Post-Generation Elements**

Given these new requirements, we should update our **Block Library Specification** to account for two things: **layout-driven image placeholders** and the fact that **learning\_objectives/key\_takeaways are now handled differently**.

1. **New Block Type for Image Placeholders:** It may be prudent to introduce a generic `image_placeholder` (or `visual_break`) block type in the library. Currently, we have `diagram_placeholder` and `flowchart_placeholder` which are content-specific (they expect a concept or process description). A new block type could be defined as, for example:

   * **`image_placeholder`**: fields might include `"description": "Optional[str]"` (a brief description of what the image could depict, or simply “(visual break)” if we want a generic label), and perhaps `"caption": "Optional[str]"` if we allow captions, plus a `"placement_suggestion": "Optional[str]"` similar to other placeholders. This block signals a purely decorative or illustrative image to break up text. The Planner can insert this without needing a deep content tie-in. During generation, the `BLOCK_INSTRUCTIONS` for `image_placeholder` could be something like: *“Insert a placeholder image description here (e.g., a relevant photo or graphic) or leave a marker for an image.”* We might even decide that the generator outputs a standard token like `![Image: Some description]()` for these placeholders, which the publishing pipeline can later replace with actual images.

2. If we don’t want a new type, we could repurpose `diagram_placeholder` for generic images by using a general description (since its fields are similar). But defining a new type makes the intent clearer. It also allows us to later handle generic images differently from strict diagrams in any post-processing. For instance, we might want to label them in the markdown as “*(Image depicting XYZ)*” versus “*(Diagram of ABC)*”. A distinct block type helps separate these cases.

3. **Optional Layout Attributes:** As an alternative or addition, we could allow a `layout_suggestion` attribute on content blocks like `explanatory_text`. For example, `explanatory_text` could have an optional field `"layout_suggestion": "image_after"` (or a more general enum like `"insert_break_after": true`). This would tell the planner/generator that after rendering that block’s text, an image break should follow. The advantage of an attribute is that it ties the visual break to a specific block of content. However, this complicates the generation logic (the generator would have to check the attribute and inject an image placeholder mid-content). It might be simpler in the JSON to just have a separate `image_placeholder` block immediately after the text block in the sequence. Given our pipeline, the **separate block approach is cleaner** – each block maps to a self-contained output segment via the BLOCK\_INSTRUCTIONS. Thus, updating the Block Library by adding an `image_placeholder` entry (or clarifying that `diagram_placeholder` can be used generally) is the preferred route.

4. **Learning Objectives and Key Takeaways in the Plan:** The Block Library already defines `learning_objectives` and `key_takeaways` block types, and previously the Planner might have included them in the plan (especially if the prompt or template asked for them). Now, however, we intend to generate those sections after the main content is produced. This means **the initial plan JSON will usually omit** `learning_objectives` and `key_takeaways` blocks. We should update our specification documents to note this change in usage:

   * The Planner prompt can instruct: *“Do not include the final Learning Objectives or Key Takeaways sections in the plan; these will be added automatically later.”* This ensures the AI focuses on the main content blocks and doesn’t allocate part of the word count to objectives that might be redundant.

   * In the Block Library spec, we might add a comment that these two block types are typically **filled in during post-processing**. They remain in the spec for completeness (and in case we ever want the AI to draft them as part of the plan), but our standard workflow now handles them separately. This way, if someone reads the spec, they understand that absence of those blocks in a plan is intentional when using the automated LO/KT generation feature.

5. **Use of Existing Placeholder Types:** We should also clarify in the Block Library that `diagram_placeholder` and `flowchart_placeholder` are meant for content-specific visuals (where the image has pedagogical meaning, like illustrating a concept or outlining a process), whereas the new `image_placeholder` (or whatever we name it) is for generic imagery to enhance layout. The Planner’s reasoning should be: use `diagram_placeholder` if the outline calls for a specific diagram (Priority 2 scenario, content-driven visual), but use a generic image placeholder periodically just for balance (Priority 1 scenario) if no specific visual is called for. If the Planner, for example, sees a subtopic that could benefit from a diagram, it can insert a `diagram_placeholder` with a description of that concept (which the generator will turn into a detailed description for an illustrator). But even if the content doesn’t *need* any diagrams, the Planner should still sprinkle a few `image_placeholder` blocks to avoid long stretches of text.

In the **Block Library Specification document**, we will add the new block type entry, e.g.:

* **image\_placeholder**: { description: Optional\[str\], caption: Optional\[str\], placement\_suggestion: Optional\[str\] }

And update any relevant instructions that the Planner uses. The dynamic planning prompt likely includes a list of block definitions (via `{{block_library}}`). We will incorporate the new `image_placeholder` definition there so the AI knows it’s available. For example, `- **image_placeholder**: { description: Optional[str], caption: Optional[str], placement_suggestion: Optional[str] }` would appear alongside the others.

Finally, regarding **post-generation additions**: since LOs and KTs are not in the initial plan, the content generator (Stage 3\) won’t produce them. That’s expected. Our Stage 5 then appends them. We should ensure this doesn’t confuse any validation or formatting expectations:

* If any part of the code validates that all planned blocks were used, we might need to adjust that logic to allow extra sections at the start or end.

* The output saving function should be fine as it just takes the final markdown string (which now includes those sections).

In summary, the Block Library gets a minor update for the layout placeholders, and a note on LO/KT placement. This empowers the Planner to consciously add visual breaks, and clarifies that some blocks (LO/KT) might be handled outside the planning phase. With these changes, the AI-driven workflow will produce well-structured lessons that are visually engaging *and* have clear objectives and summaries for the learner.

**Sources:**

* Block types for placeholders (diagram/flowchart) in the library.

* Guidelines for using images to break up text.

* Prompt snippet guiding LO insertion at beginning and SMART criteria for objectives.

* Key takeaway enhancement criteria (clear, concise summary of critical points).

* Workflow finalize stage showing where to integrate new steps.

