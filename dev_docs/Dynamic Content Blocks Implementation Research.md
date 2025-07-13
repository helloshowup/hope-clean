# **Dynamic Content Blocks Implementation Research**

## **1\. Prompt Engineering for Dynamic Structure Generation (Planner Agent)**

Designing the Planner Agent’s prompt to include the **Block Library Specification** requires a balance between completeness and token efficiency. Rather than inserting a verbose full JSON Schema (which can consume many tokens and potentially confuse the model), a more concise **type-definition style** description is recommended. For example, we can list each block type with its fields and types in a compact format (similar to a TypeScript interface or a Pydantic model) instead of a verbose schema. This approach significantly reduces token usage **without loss of clarity**[boundaryml.com](https://www.boundaryml.com/blog/type-definition-prompting-baml#:~:text=We%20propose%20using%20type,better%20cost%2C%20latency%20and%20accuracy). In practice, the prompt might include a brief introduction (in natural language) explaining that the AI should output a plan composed of `content_blocks`, followed by a **compact schema-like listing** of each block type. For instance:

text  
CopyEdit  
`Each content_blocks entry has a "block_type" and associated fields:`  
`- **lesson_metadata**: { title: string, module_id: string, subtitle: string (optional), purpose: string (optional) }`  
`- **learning_objectives**: { objectives: list<string> }`  
`- **introduction**: { content_summary: string, hook_suggestion: string (optional) }`  
`... (and so on for each block type)`

This kind of type definition is much shorter than a full JSON Schema but still clearly communicates the required structure. Recent prompting research indicates that using such **structured type definitions** can cut down prompt tokens dramatically (by \~60% compared to full JSON schema) while maintaining or even improving output correctness[boundaryml.com](https://www.boundaryml.com/blog/type-definition-prompting-baml#:~:text=We%20propose%20using%20type,better%20cost%2C%20latency%20and%20accuracy). In other words, *"less is more"* – by giving the model just the essential schema in a lightweight format, we reduce prompt size and possibly improve adherence.

Additionally, it may help to **embed high-level placement guidance in comments or brief notes**. For example, after listing the block types, include a note like: *“The `lesson_metadata` block should come first. A `key_takeaways` block should come last. Other blocks can be repeated or ordered as needed to form a coherent lesson.”* This gives the model context about ordering without heavy-handed natural language. The overall strategy is a **combination approach**: use a structured listing for the schema (for precision) and minimal natural language for instructions (for clarity). By doing this in the `planning_prompt.txt`, the Planner Agent can reliably choose and order blocks when generating the `initial_plan`. This is more token-efficient and maintains clarity for the LLM[boundaryml.com](https://www.boundaryml.com/blog/type-definition-prompting-baml#:~:text=We%20propose%20using%20type,better%20cost%2C%20latency%20and%20accuracy). (In contrast, a huge verbose JSON schema could waste tokens and risk the model focusing on the wrong details.)

Finally, it's worth noting that modern LLM features like OpenAI function calling or JSON mode could enforce structure, but since our pipeline currently feeds the schema via plain prompt text, the above approach is our best practice. In summary, **present the Block Library as a concise schema or type definition within the planning prompt**, rather than a lengthy prose or full JSON schema. This will guide the model to output a JSON `content_blocks` array that matches our specification, in a token-efficient manner[boundaryml.com](https://www.boundaryml.com/blog/type-definition-prompting-baml#:~:text=We%20propose%20using%20type,better%20cost%2C%20latency%20and%20accuracy).

## **2\. Robust Schema Validation for Dynamic Plans**

With the `initial_plan` and `final_plan` now being dynamic (varying block types and structures in a list), it's crucial to **validate these plans programmatically** before using them downstream. Relying on a simple `json.loads` (as currently done in the planning/refinement stages) is not enough – we need to enforce that all required fields are present and of correct types. The best practice here is to use a schema validation library such as **Pydantic** or **jsonschema**.

**Pydantic** (especially Pydantic v2) is an excellent choice for validating LLM outputs. We can define a set of Pydantic `BaseModel` classes corresponding to our content blocks (e.g., a `LessonMetadata` model, a `LearningObjectives` model, etc., and perhaps a parent model with a `content_blocks: list[Union[LessonMetadata, ...]]`). By doing so, we can attempt to parse the AI-generated plan JSON into these models. Pydantic will automatically check types, presence of required fields, and even convert types if possible. If the model fails validation, it will raise a `ValidationError` listing exactly what is wrong (e.g., missing field or wrong type). This gives us a programmatic hook to catch AI errors early. In fact, the Pydantic team explicitly advocates this approach: *“validating structured outputs from language models using Pydantic… to write reliable code”*[pydantic.dev](https://pydantic.dev/articles/llm-intro#:~:text=structured%20data%2C%20we%20have%20found,Pydantic%20is%20even%20more%20effective). Using Pydantic means we codify the block schema in code as well, ensuring consistency between what we prompt the AI and what we accept from it.

Alternatively, a `jsonschema` approach could work: define a JSON Schema for the entire `final_plan` (with `content_blocks` as an array of oneOf the block definitions). Then use a library like `jsonschema` to validate the AI output. This too would catch structural issues. However, writing a full JSON schema might be more cumbersome and less Pythonic than Pydantic models. Given that our project already uses Python and likely can afford adding Pydantic (if not already in use), Pydantic provides a more developer-friendly interface. It can also integrate directly with the AI call if we wanted (for example, Pydantic can generate a JSON schema from the models, which could even be fed into the prompt or used with OpenAI function calling in the future).

In implementation, after getting `new_item["initial_plan"]` from the planning stage, we can run something like:

python  
CopyEdit  
`from pydantic import BaseModel, ValidationError`

`class LessonMetadata(BaseModel):`  
    `block_type: str`  
    `title: str`  
    `module_id: str`  
    `subtitle: str | None = None`  
    `purpose: str | None = None`

`# ... define other block models ...`

`class ContentBlock(BaseModel):`  
    `block_type: str`  
    `# use discriminator or manual parsing to choose the correct model subclass`

`class Plan(BaseModel):`  
    `content_blocks: list[ContentBlock]`

Then do `Plan.model_validate(initial_plan_obj)` to validate. Any error can be logged or even fed back to the AI for refinement. This robust check will ensure that if the AI mistakenly omits a required field or produces an unknown block type, we catch it immediately rather than proceeding with bad data. There are even advanced techniques where you can loop back validation errors into the model for a second attempt[pydantic.dev](https://pydantic.dev/articles/llm-intro#:~:text=Package.model_validate_json%28resp.choices)[pydantic.dev](https://pydantic.dev/articles/llm-intro#:~:text=Ok%20heres%20the%20authors%20of,and%20the%20name%20this%20library), but a simpler approach is to fail the workflow with a clear error for a developer to see, or possibly prompt a refinement with a system message listing the needed fixes.

In summary, **yes** – implement strong schema validation. Using Pydantic is a modern solution (with built-in JSON parsing and detailed error reporting)[pydantic.dev](https://pydantic.dev/articles/llm-intro#:~:text=structured%20data%2C%20we%20have%20found,Pydantic%20is%20even%20more%20effective). If adding new dependencies is a concern, the `jsonschema` library can be used similarly to validate against a hand-written schema. Either way, this gives us confidence that `final_plan['content_blocks']` truly adheres to our specification, preventing downstream stages from encountering unpredictable structures or missing data.

## **3\. Generation Stage Logic for Block-Specific Content**

The **Generation Stage** (Stage 4\) currently takes the `final_plan` JSON and asks the model to produce the full content. In the existing implementation, the code simply injects the entire `final_plan` into a single `generation_prompt` template and asks for the lesson content[GitHub](https://github.com/helloshowup/hope-clean/blob/f4e5ddf9b60e7ef1e6751d6f241822534a8f3cb4/showup_tools/content_generator.py#L178-L186). This means the AI is expected to read the whole plan and write a complete lesson in one go. With the new dynamic blocks, we should consider guiding the model to handle each block appropriately. There are two possible strategies here:

* **Single-Prompt, Structured Guidance:** Continue using one prompt for the entire lesson, but enhance the prompt with explicit instructions on how to expand each block type. For example, the prompt could say (in pseudocode): *“You are given a lesson plan with various content blocks. For each block in `content_blocks`: if `block_type` is 'introduction', write an engaging intro based on the `content_summary`. If it's 'list\_block', present a list (bullet or numbered as specified) expanding on each item in `items_summary`. If 'explanatory\_text', write one or more paragraphs covering the `topic` and touching on the `key_points`. If 'example\_analysis', format it as a clearly labeled example: show the initial statement, then the improved version and explanation points,”* etc. Essentially, the prompt needs to teach the model how to interpret each block’s fields and turn them into the desired prose or format. This could be done with a few-shot style (providing a tiny example of each), or simply enumerated instructions. Since the plan JSON is already structured, a well-instructed model like GPT-4 or Claude should be able to iterate through blocks and do the right thing, especially if we clearly delineate each block.

* **Multi-Prompt (Iterative) Generation:** Alternatively, we could generate content **block by block** in a loop from Python, sending smaller prompts for each block and appending the results. For example, first call the model to generate the introduction text from the intro block, then separately generate the list from the list block, etc., then concatenate. This might give more fine-grained control (and easier debugging per block), but it has drawbacks: ensuring a consistent tone and flow across blocks might be harder if done in isolation, and it would be slower (multiple API calls instead of one). Given that our current system even generates *three versions* by making three parallel calls with one prompt each[GitHub](https://github.com/helloshowup/hope-clean/blob/f4e5ddf9b60e7ef1e6751d6f241822534a8f3cb4/showup_tools/content_generator.py#L180-L189), the single-prompt approach is likely preferred for efficiency and for allowing the model to produce a cohesive lesson narrative.

A good compromise is to **refine the single prompt template to be block-aware**. The existing `generation_prompt.txt` likely contains placeholders for the plan JSON and some general instruction. We should update it to reflect the new schema. For instance, if originally it iterated through `scenes`, we now adapt it to iterate through `content_blocks`. Concretely, the prompt might look like:

“Using the finalized plan below, produce the full lesson content. The plan is a JSON with an array of content\_blocks. Follow these rules:

* Include the lesson title and any subtitle in a header at the top (from lesson\_metadata).

* Write an introduction that hooks the learner (from introduction.content\_summary and hook\_suggestion).

* Present learning objectives in a clear list.

* Use section headings as specified by section\_heading blocks (H2/H3 based on level).

* Where explanatory\_text blocks appear, write informative paragraphs covering the topic and key points.

* Where list\_block appears, output a well-formatted list (numbered or bullet as indicated) expanding on each item.

* For example\_analysis blocks, format them as a mini-case study: state the initial statement, then show the improved version and explanation (this could be a structured sub-list or bold labels like "Before/After").

* For process\_steps, use a numbered list or sub-section for each step, including the step title and description.

* For reflection\_prompt, present the questions as bullet points or a short Q\&A section to prompt the learner.

* For diagram\_placeholder or flowchart\_placeholder, provide a detailed description of the diagram as an **instruction or note for a designer** (not just a caption, but a full explanation of what it should depict).

* End with the key\_takeaways as a summary list of bullet points.”

The above is verbose for explanation, but it illustrates how the generation prompt can explicitly cover each block type’s expansion instructions. This ensures the model knows, for instance, that an `example_analysis` isn’t just text to dump verbatim, but needs special formatting (initial vs improved example).

Implementing this likely means modifying `generation_prompt.txt` to include these guidelines. We might not need separate prompts per block type; a single structured prompt can suffice if done carefully. Claude and GPT-4 are capable of reading a structured plan and following a list of formatting instructions for each section.

One more consideration: the **tone and style**. The plan might include `tone_suggestion` fields (as in `explanatory_text`) or other hints. The generation logic should respect those. We could incorporate conditional wording, e.g., *“If a block has a tone\_suggestion, adapt the writing style accordingly (e.g., conversational if suggested).”* This can be part of the prompt instructions or handled in code by appending style guidelines before the model call.

To summarize, **refactoring `generate_three_versions_from_plan`** would involve: ensuring the `final_plan` JSON is passed into the model with updated instructions for each block type, and possibly iterating or clearly delineating sections in the prompt. The current approach of one prompt per version can be retained – just make that prompt smarter. We likely do not need to make multiple API calls (which keeps things simpler and faster). Instead, we rely on prompt engineering to get the block-specific content correct. By explicitly telling the model how to handle each `block_type`, we guide it to produce the correct output format for each (e.g. lists for list\_block, headings for section\_heading, etc.), all within one cohesive lesson output.

## **4\. Word Count Management Across Dynamic Blocks**

Maintaining the overall lesson length is important for consistency (e.g., some lessons might target \~800 words, others \~1500, as specified in the CSV input). With dynamic blocks, the content length is the sum of all blocks’ expansions, so we need to **distribute the word count across the plan**. There are a few strategies to achieve this:

* **Plan Stage Awareness:** When generating the initial plan, include the target word count in the prompt so the AI plans an appropriate scope. For example, the `planning_prompt.txt` could say: *“The total lesson length should be about **{{word\_count}}** words. Plan a lesson structure (content blocks) that would fit roughly in this length.”* This can guide the AI to not propose 10 extensive blocks for a 300-word lesson, or conversely, not to propose an overly brief plan for a 1500-word target. The Planner could implicitly allocate lengths (maybe via number of bullet points, etc., e.g., if word\_count is small, maybe only 2 objectives instead of 5, etc.). We might even incorporate a heuristic in the plan: e.g., instruct *“for a 500-word lesson, include fewer examples or shorter sections; for a 1500-word lesson, you can include more depth and perhaps multiple sections.”* Because the blocks are modular, the AI can adjust the quantity of blocks or sub-items to meet the length.

* **Refinement Stage Checking:** After initial\_plan, the critique/refinement agent could be tasked to check if the plan seems too ambitious or too sparse for the word count. If the initial plan has, say, 8 blocks including several large lists for only 400 words target, the critique can note “this might overshoot the word count” and suggest trimming or focusing. We can explicitly prompt in `plan_critique_prompt.txt` for something like: *“Check if the scope of the plan matches the target length and adjust if needed.”* Then the refine step can remove or consolidate blocks to better fit the length.

* **Generation Stage Instruction:** Finally, when actually generating the content from the final plan, we should include a direct word count guideline to the model (LLMs respond well to explicit length instructions). In the current code, when using the `generate_content` function for individual steps, they already append a note like *“IMPORTANT: Your response should be approximately N words in length. This is a target, not a strict limit, but aim to keep around this word count.”*[GitHub](https://github.com/helloshowup/hope-clean/blob/f4e5ddf9b60e7ef1e6751d6f241822534a8f3cb4/showup_tools/content_generator.py#L84-L91). We should do the same for the full lesson generation. Since `generate_three_versions_from_plan` uses a custom prompt, we can append a similar instruction at the end of the prompt template, using the `word_count` from our CSV. For example: *“The entire lesson should be roughly **{{word\_count}}** words. Aim to distribute this length across the sections appropriately – not every section will be equal length, but the final output should be near this target.”* This reminds the model to self-regulate verbosity. Empirically, models like GPT-4 do tend to follow such guidance reasonably well (within, say, 10-15% of target).

* **Post-generation Adjustment (if needed):** We could also measure the output length after generation and, if it’s way off, take action. For instance, if the model produces 2000 words when we asked for 1000, the `review_content` stage (if one exists) could note that and we might trigger a trim or summary. However, it’s often better to get it right in the generation step via prompt instructions, rather than pruning after the fact. Given we generate three versions with different temperatures, their lengths may vary slightly; the compare step might choose the one that best fits the target (perhaps that could be a criterion in comparison – to favor the version closest to desired length).

In implementation, passing the `word_count` from the CSV into the planning and generation prompts is straightforward: e.g., `planning_prompt = prompt_template.replace("{{word_count}}", str(row_data_item["Word Count"]))`. Also ensure to propagate it through refinement (the refine prompt might also need the info). And in `generate_three_versions_from_plan`, incorporate it as described. The code already shows usage of a `word_count_instruction` in individual generation[GitHub](https://github.com/helloshowup/hope-clean/blob/f4e5ddf9b60e7ef1e6751d6f241822534a8f3cb4/showup_tools/content_generator.py#L84-L91), so we extend that concept.

To allocate length **across blocks**, we won't micromanage exact word counts per block (that would be overkill), but we expect the model (with its instruction-following ability) to do a reasonable allocation. For example, introduction and conclusion might be shorter, core content sections longer, etc., which is natural. If necessary, we could add hints like *“Devote a few sentences to the introduction and conclusion, and use the majority of words for the main explanatory sections and examples.”* This kind of hint in the generation prompt helps the model distribute content appropriately.

In summary, **use a multi-pronged approach to manage word count**: inform the plan, validate the scope during refinement, and explicitly instruct the generator about the target length. By doing so, we align the sum of all dynamic blocks with the desired overall lesson length. This prevents cases where the dynamic approach might accidentally double the expected length or short-change the lesson content.

*(Note: The system currently had a fixed template with 600-800 words in an example[GitHub](https://github.com/helloshowup/hope-clean/blob/f4e5ddf9b60e7ef1e6751d6f241822534a8f3cb4/showup_tools/content_generator.py#L286-L294). Moving to dynamic blocks with explicit word count input will be a superior, flexible solution.)*

## **5\. Handling Non-Textual Blocks (Diagrams/Flowcharts) in the Generation Stage**

The `diagram_placeholder` and `flowchart_placeholder` blocks are special because they signal **visual content** rather than normal text paragraphs. Our goal is for the Generation Stage to output a **detailed, actionable description** of the diagram or flowchart so that a human designer (or a future image-generation tool) can create it easily. This description will likely be included in the lesson content (possibly as a note or formatted differently), so it should be clear and well-structured.

Key considerations for the diagram/flowchart descriptions:

* **Clarity of Elements:** The AI should list all important components of the diagram. For a flowchart, this means every step or decision node and how they connect. For a conceptual diagram, it means all key concepts or stages shown. For example, if the placeholder description says *"motivation cycle: Initial Excitement \-\> Dip \-\> Engagement \-\> Renewal"*, the output should explicitly mention each of those stages.

* **Relationships and Direction:** The description must explain how the elements connect. In a flowchart, which arrow goes from which node to where (and any conditions on arrows). In a cycle diagram, that it’s a circular progression with arrows looping back to the start. Essentially, describe the **structure** of the diagram (e.g., “arranged in a circle” or “top-down flowchart” or “branching decision tree with two outcomes”, etc.).

* **Visual Hints:** While textual, we can include hints that help a future renderer. For instance, suggesting shapes or icons for clarity: *“use arrows to show progression from stage to stage”*, or *“Stage 2 (Motivation Dip) could be shown in a different color to indicate challenge”* – these are optional, but can add value. If the lesson style guide or consistency demands certain visual style, mention it (for example, *“depict each step in a box, decision points in diamonds”* is typical flowchart advice). We should avoid actual drawing or ASCII art, but provide a narrative of the diagram.

* **Caption and context:** If a caption is provided in the block (like `caption: "Figure 1: ..."`), we should include that as a **bold or italic title** for the description, so it stands out. E.g., **Figure 1: The Cyclical Nature of Motivation** – followed by the description.

To get the AI to do this, our generation prompt should have explicit instructions for these block types. For example: *“If the plan contains a `diagram_placeholder` or `flowchart_placeholder`, do not skip it. Instead, produce a detailed description of the intended visual. Include all steps or components and how they relate. Write it in present tense as if instructing a designer, e.g., 'The diagram shows ...'. Be specific – the more detail, the more accurate the eventual diagram will be[kdnuggets.com](https://www.kdnuggets.com/3-easy-ways-create-flowcharts-diagrams-using-llms#:~:text=Tips%20for%20Effective%20Diagram%20Creation).”* Emphasizing *“the more detail the better”* is important, echoing the guideline that *“Be Specific: The more detail you provide in your description, the more accurate the results will be.”*[kdnuggets.com](https://www.kdnuggets.com/3-easy-ways-create-flowcharts-diagrams-using-llms#:~:text=Tips%20for%20Effective%20Diagram%20Creation). In practice, an output for a flowchart might look like:

*Diagram Note:* **Figure 2: Transforming Goals with the SMART Framework** – *This flowchart should illustrate the process of turning a vague goal into a SMART goal. It starts with a box labeled "Vague Goal". An arrow from "Vague Goal" leads to a process box "Apply SMART Criteria". From this box, five arrows branch out (perhaps as parallel steps or a list) labeled Specific, Measurable, Achievable, Relevant, Time-bound – each pointing to sub-boxes that refine the goal. These then converge into a final box labeled "SMART Goal". Use decision diamond shapes if needed to show checking each criterion, and use arrows to show the sequence from start to finish. The flow should be left-to-right.*

This level of detail leaves little ambiguity for a human illustrator or an automated tool. We might also instruct the AI to use clear language and even break the description into bullet points if multiple elements are involved (bullets could enumerate the entities and relationships, which is very readable). For example, enumerating: *“1. Start Node: 'Vague Goal' \-\> 2\. Action: 'Apply SMART criteria' \-\> ...”*. However, formatting can be decided based on how we want the teacher or content user to see it. Perhaps a descriptive paragraph is enough, or a semi-structured list.

In summary, **design the generation prompt to treat diagram/flowchart placeholders as tasks to produce design directives**. The output should read like an **annotated diagram description**. Include:

* The intended **concept** (what the diagram shows).

* The **components** (steps, stages, nodes).

* The **connections** (arrows, lines, loops, conditions).

* Any relevant **visual styling cues** (optional but useful, e.g., color coding, shapes).

* The **caption** (to label the figure).

By having the AI spell all this out, we ensure that even though the final lesson is text, it contains a blueprint for the diagram. This can later be given to a graphic designer or possibly fed to a tool (like Mermaid, PlantUML, or a custom diagram generator) to create the actual image. The key is that the AI must not gloss over these blocks – it must output *meaningful content* for them, just as it does for explanatory text. Our prompt and few-shot examples (if any) should reinforce that.

As an extra note: we should **not** output actual Markdown image syntax with a dummy path (since we don't have an actual image file at generation time), unless we have a system to post-process that. It might be better to output it as a descriptive blockquote or italicized note. This is more of a content decision. But the main point is, the AI’s text should be sufficient for someone to draw the diagram without needing the original author – all info should be in there. Following these prompting techniques (explicitly asking for detailed descriptions and giving an example format) will achieve that[kdnuggets.com](https://www.kdnuggets.com/3-easy-ways-create-flowcharts-diagrams-using-llms#:~:text=Tips%20for%20Effective%20Diagram%20Creation).

## **6\. Backward Compatibility and Transition Strategy**

Introducing a new schema for plans (moving from a fixed `scenes` structure to flexible `content_blocks`) is a significant change. We must handle this transition carefully to avoid breaking existing functionality. Here are the considerations and strategies:

* **Update All Relevant Code Paths:** First, identify everywhere the old schema was assumed. In our codebase, that includes prompt templates and any code that accessed `initial_plan`/`final_plan` fields. For example, if `generation_prompt.txt` or the critique prompt expected a `scenes` array, those need to be rewritten to use `content_blocks`. In the code, functions like `generate_three_versions_from_plan` simply treat the plan as JSON without internal logic for scenes, so they are easy to adapt (we just ensure the prompt is updated)[GitHub](https://github.com/helloshowup/hope-clean/blob/f4e5ddf9b60e7ef1e6751d6f241822534a8f3cb4/showup_tools/content_generator.py#L178-L186). But if there were any utilities to display the plan in the UI or logging (e.g., showing scene titles), those must now iterate over `content_blocks`. We should comb through the UI layer or any output generation for references to "scene" or assumptions like `plan["scenes"][0]["title"]`. For instance, if the front-end expects to render a plan outline, we might need to change it to read the new structure. Since the repository included a `save_as_markdown` or similar, ensure that if it was formatting scenes, it now formats content blocks appropriately.

**Parallel Support (if needed):** During development, it might be wise to support both schemas until fully migrated. This could mean the Planner Agent outputs both the old and new format for a while (which is messy), or more cleanly, we maintain a conversion utility. For example, after getting a `final_plan` with content\_blocks, we could **programmatically generate a legacy representation** just for any component that still needs it. If an older part of the system absolutely requires `final_plan["scenes"]`, we can do:

 python  
CopyEdit  
`final_plan_legacy = {"scenes": []}`  
`for block in final_plan["content_blocks"]:`  
    `# map content_blocks to a generic "scene" if possible`  
    `final_plan_legacy["scenes"].append({"title": block.get("title",""), "block": block})`

*  This is a bit contrived (and loses nuance, since scenes weren’t 1-to-1 with our new blocks), so a better approach is to **update the consumer** rather than provide a fake scenes list. If, however, we have to maintain backward compatibility with stored data or older courses, we might need a migration script: e.g., converting old `scenes` plans into the new block format, or vice versa, so that nothing is lost.

* **Version Flag:** We can introduce a version indicator in the plan JSON. For example, `final_plan = {"version": 2, "content_blocks": [ ... ]}`. The old scheme might be implicitly version 1 (with `"scenes": [...]`). By checking the presence of `content_blocks` vs `scenes`, the system can route logic accordingly. If some part of code or an external tool gets a new plan and doesn’t understand it, we could at least detect it and warn. Since this is an internal refactor, maybe not many external dependencies exist, but it’s a good practice for data longevity.

* **Testing and Gradual Rollout:** We should run our test suite thoroughly. The existing tests (e.g., `test_planning_stage.py`, `test_workflow_integration.py`) use stubbed JSON like `{"plan": "ok"}`[GitHub](https://github.com/helloshowup/hope-clean/blob/f4e5ddf9b60e7ef1e6751d6f241822534a8f3cb4/tests/test_planning_stage.py#L22-L30). We’ll want to update or add tests that the structure of `initial_plan` and `final_plan` matches the spec. Write tests where a dummy `content_outline` yields an `initial_plan` with content\_blocks array. Also test that a `final_plan` goes through `generate_three_versions_from_plan` and produces content without error. If there’s a UI, perhaps do a dry run to ensure the UI can display the new plan format (if it shows objectives, etc., ensure they appear properly). This transition might be done in a feature branch; during that time, it’s possible to keep the old system running in production (if needed) while new one is tested, then cut over.

* **Backward Compatibility with Existing Data:** If there are saved `final_plan` JSONs in a database or user content, we might consider writing a one-time migration to convert them. Or at least, ensure that the code can handle both formats when reading. For example, `process_row_for_phase` could check if `item["final_plan"]` has `"scenes"` and not `"content_blocks"`, and if so, transform it (or simply treat scenes list as content\_blocks for generation). This way, if a user resumes a workflow that was mid-way, it might still work. This might be overkill if we assume all workflows start fresh with the new system, but it’s worth mentioning.

* **Communicating Changes:** If any stakeholders (like content writers or curriculum designers) interacted with the plan (say, reviewing the AI-generated plan before generation), they should be informed of the new format. For instance, a plan JSON will now have more detail and different keys. We should update any documentation (perhaps the `Blueprint Advanced Content Generation Workflow.md`) to reflect the new structure, so everyone is on the same page.

Fortunately, since the planning, refinement, and generation are fairly encapsulated, the changes mostly involve prompt adjustments and validation as discussed. The core pipeline (plan \-\> refine \-\> generate) remains the same. We just have to ensure nothing *downstream* expects the old schema explicitly. The snippet from `workflow.py` shows that after refinement, we pass `final_plan` into generation without inspecting it in Python[GitHub](https://github.com/helloshowup/hope-clean/blob/f4e5ddf9b60e7ef1e6751d6f241822534a8f3cb4/showup_tools/workflow.py#L2-L5). This is good – it means our Python code is mostly agnostic to the content, and the change is largely within the prompts and how the AI structures data. Thus, updating the prompts and adding validation should not break the Python flow.

To minimize disruption:

* We can implement the new prompts and models **behind a config flag** initially. For example, have an environment switch "USE\_DYNAMIC\_BLOCKS=True". If false, use old prompts; if true, use new. This way, we can toggle for testing.

* Once confident, fully switch to the new system and remove legacy code.

In summary, **the transition strategy is**: update all prompts and parsing to use `content_blocks`; ensure any UI or logging is adapted; possibly handle old format reading gracefully; and test thoroughly. If needed, temporarily support both formats, but ideally switch over completely when ready. By planning this out and perhaps versioning the schema, we can roll out the dynamic block system with minimal hiccups. The result will be a more flexible lesson generation system, while still maintaining stability of the application during the change.

