#### **Block Definitions**

**1\. `lesson_metadata`**

* **Purpose:** Provides high-level information about the lesson. This block is typically generated *once* at the very beginning of the plan.  
* **Key Components/Attributes:**  
  * `type: "lesson_metadata"`  
  * `title: str` (e.g., "1.6 Motivation Strategies: Sustaining Your Learning Journey")  
  * `module_id: str` (e.g., "1.6", "1.18")  
  * `subtitle: Optional[str]` (e.g., "Understanding Motivation Cycles")  
  * `purpose: Optional[str]` (e.g., "Introductory", "Core Content", "Evaluation")  
* **Placement Guidelines:** Always the first block in the `content_blocks` array.  
* **Example Usage (in JSON plan):**  
  JSON

```
{
  "block_type": "lesson_metadata",
  "title": "1.6 Motivation Strategies: Sustaining Your Learning Journey",
  "module_id": "1.6",
  "purpose": "Core Content"
}
```

*   
* **Notes:** This block helps contextualize the entire lesson for the AI and for human readers of the plan.

---

**2\. `learning_objectives`**

* **Purpose:** Clearly states what the learner should be able to do after completing the lesson.  
* **Key Components/Attributes:**  
  * `type: "learning_objectives"`  
  * `objectives: List[str]` (e.g., \["Identify cyclical patterns of motivation", "Apply practical strategies"\])  
* **Placement Guidelines:** Typically appears immediately after `lesson_metadata` or `introduction`.  
* **Example Usage:**  
  JSON

```
{
  "block_type": "learning_objectives",
  "objectives": [
    "Evaluate your growth mindset development by identifying specific examples of mindset shifts.",
    "Create personalized growth mindset statements that counter specific fixed mindset triggers."
  ]
}
```

*   
* **Notes:** Objectives should be actionable and measurable.

---

**3\. `introduction`**

* **Purpose:** Engages the learner, provides a high-level overview, and sets the stage for the lesson's content. Often includes a hook.  
* **Key Components/Attributes:**  
  * `type: "introduction"`  
  * `content_summary: str` (A brief summary that the AI will expand upon)  
  * `hook_suggestion: Optional[str]` (e.g., "Start with a relatable question about procrastination.")  
* **Placement Guidelines:** Usually appears after `learning_objectives` or `lesson_metadata`.  
* **Example Usage:**  
  JSON

```
{
  "block_type": "introduction",
  "content_summary": "Explore the cyclical nature of motivation and why it's not constant. Introduce the lesson's focus on practical strategies for sustaining engagement.",
  "hook_suggestion": "Ask: 'Have you ever started a new project with enthusiasm, only to lose steam weeks later?'"
}
```

*   
* **Notes:** The `content_summary` guides the AI in generating the full introductory text.

---

**4\. `section_heading`**

* **Purpose:** Organizes the lesson into logical, thematic sections, improving readability and navigation.  
* **Key Components/Attributes:**  
  * `type: "section_heading"`  
  * `level: int` (e.g., 2 for H2, 3 for H3, corresponds to Markdown `##` or `###`)  
  * `title: str` (e.g., "Understanding Motivation Cycles", "Evaluating Progress Through Specific Examples")  
* **Placement Guidelines:** Precedes related content blocks.  
* **Example Usage:**  
  JSON

```
{
  "block_type": "section_heading",
  "level": 2,
  "title": "Understanding Motivation Cycles"
}
```

*   
* **Notes:** AI should ensure appropriate heading levels for hierarchy.

---

**5\. `explanatory_text`**

* **Purpose:** Delivers core content, concepts, definitions, or detailed explanations.  
* **Key Components/Attributes:**  
  * `type: "explanatory_text"`  
  * `topic: str` (The main subject of this text block)  
  * `key_points: List[str]` (Specific points to cover within the text)  
  * `tone_suggestion: Optional[str]` (e.g., "formal", "conversational", "encouraging")  
* **Placement Guidelines:** Can appear anywhere content is needed, typically following a `section_heading`.  
* **Example Usage:**  
  JSON

```
{
  "block_type": "explanatory_text",
  "topic": "Motivation as a cyclical process",
  "key_points": [
    "Motivation is not constant, but cyclical.",
    "Research shows predictable patterns: initial excitement, dip, stable engagement.",
    "Recognizing cycles and proactive strategies are key."
  ],
  "tone_suggestion": "informative and reassuring"
}
```

*   
* **Notes:** This is the most common block for general content delivery.

---

**6\. `list_block`**

* **Purpose:** Presents discrete points, strategies, steps, or examples in an organized, digestible format.  
* **Key Components/Attributes:**  
  * `type: "list_block"`  
  * `list_type: "numbered" | "bulleted"`  
  * `heading: Optional[str]` (An optional title for the list itself, e.g., "Practical Motivation Maintenance Strategies")  
  * `items_summary: List[str]` (Summaries of each item for the AI to expand)  
* **Placement Guidelines:** Often follows an `explanatory_text` block or a `section_heading`.  
* **Example Usage:**  
  JSON

```
{
  "block_type": "list_block",
  "list_type": "numbered",
  "heading": "Practical Motivation Maintenance Strategies",
  "items_summary": [
    "Set SMART micro-goals: break large tasks into smaller, achievable ones.",
    "Implement the 5-minute rule: commit to working for just 5 minutes.",
    "Create accountability systems: share goals with others.",
    "Use the Pomodoro Technique: focused 25-minute intervals."
  ]
}
```

*   
* **Notes:** The AI needs to expand `items_summary` into full, clear list items.

---

**7\. `example_analysis`**

* **Purpose:** Illustrates concepts with concrete scenarios, demonstrates application, and often involves analysis (e.g., "Before/After").  
* **Key Components/Attributes:**  
  * `type: "example_analysis"`  
  * `example_title: str` (e.g., "Example 1: 'I want to do better in school.'")  
  * `initial_statement: str` (The original, "weak" statement/goal)  
  * `analysis_criteria: List[str]` (Criteria for analysis, e.g., "Specific", "Measurable", "Achievable", "Relevant", "Time-bound")  
  * `improved_version_summary: str` (Summary of how the example is improved)  
  * `explanation_points: List[str]` (Points explaining *why* the improvement works)  
* **Placement Guidelines:** Typically embedded within a section discussing concepts that require practical demonstration.  
* **Example Usage:**  
  JSON

```
{
  "block_type": "example_analysis",
  "example_title": "Example 1: 'I want to do better in school.'",
  "initial_statement": "I want to do better in school.",
  "analysis_criteria": ["Specific", "Measurable", "Achievable", "Relevant", "Time-bound"],
  "improved_version_summary": "Goal specifies subject (Algebra), defines 'better' (A from C), includes timeframe (end of semester), and outlines actions (tutoring).",
  "explanation_points": [
    "Adds specificity about subject and desired grade.",
    "Provides quantifiable metrics for tracking progress.",
    "Sets a clear deadline for accountability."
  ]
}
```

*   
* **Notes:** This block is crucial for practical application lessons.

---

**8\. `process_steps`**

* **Purpose:** Outlines a sequential method, framework, or series of actions that the learner should follow.  
* **Key Components/Attributes:**  
  * `type: "process_steps"`  
  * `process_name: str` (e.g., "The Resilience Process")  
  * `introductory_text: Optional[str]` (Brief intro to the process)  
  * `steps: List[Dict[str, str]]` (Each dict has `step_number`, `title`, `description`)  
* **Placement Guidelines:** Usually appears as a standalone section, often after an introduction to the concept.  
* **Example Usage:**  
  JSON

```
{
  "block_type": "process_steps",
  "process_name": "The Resilience Process",
  "introductory_text": "Academic setbacks are inevitable. The resilience process provides a systematic way to respond to challenges.",
  "steps": [
    {"step_number": "1", "title": "Acknowledge emotions", "description": "Recognize feelings of disappointment or frustration. Practice self-compassion."},
    {"step_number": "2", "title": "Analyze the situation objectively", "description": "What specific factors contributed to the setback? Which were within your control?"}
  ]
}
```

*   
* **Notes:** Ensures clear, actionable instructions for multi-step processes.

---

**9\. `reflection_prompt`**

* **Purpose:** Fosters active learning, encourages self-assessment, and prompts personal connection to the material.  
* **Key Components/Attributes:**  
  * `type: "reflection_prompt"`  
  * `prompt_heading: str` (e.g., "Revisiting Your Initial Growth Mindset Reflection")  
  * `questions: List[str]` (The actual questions or prompts for the learner)  
  * `context_setting: Optional[str]` (Brief text to set up the reflection)  
* **Placement Guidelines:** Can appear at any point where self-assessment or critical thinking is desired.  
* **Example Usage:**  
  JSON

```
{
  "block_type": "reflection_prompt",
  "prompt_heading": "Deepening Your Growth Mindset Practice",
  "context_setting": "It's time to develop more sophisticated growth mindset strategies. This involves moving beyond simply recognizing fixed mindset triggers to actively countering them.",
  "questions": [
    "Are you more likely to seek out challenging material?",
    "Have you developed more effective study strategies?",
    "What specific areas will benefit from fixed mindset reactions?"
  ]
}
```

*   
* **Notes:** The AI should generate the questions clearly.

---

**10\. `key_takeaways`**

* **Purpose:** Reinforces learning and provides a concise summary of the most important points for quick review.  
* **Key Components/Attributes:**  
  * `type: "key_takeaways"`  
  * `points: List[str]` (Key points to summarize)  
* **Placement Guidelines:** Typically the last content block in a lesson.  
* **Example Usage:**  
  JSON

```
{
  "block_type": "key_takeaways",
  "points": [
    "Creating personalized growth mindset statements helps counter fixed mindset triggers.",
    "Developing a growth mindset is a continuous process involving successes and setbacks."
  ]
}
```

*   
* **Notes:** Should be concise and impactful.

---

**11\. `diagram_placeholder`**

* **Purpose:** Indicates where a visual diagram is needed to illustrate a concept.  
* **Key Components/Attributes:**  
  * `type: "diagram_placeholder"`  
  * `concept_to_illustrate: str` (The core concept the diagram should explain)  
  * `description: str` (Detailed description of what the diagram should show, its elements, and relationships)  
  * `caption: Optional[str]` (Suggested caption for the diagram)  
  * `placement_suggestion: Optional[str]` (e.g., "after 'Explanatory Text Block on Photosynthesis'")  
* **Placement Guidelines:** Typically follows an `explanatory_text` block that introduces the concept.  
* **Example Usage:**  
  JSON

```
{
  "block_type": "diagram_placeholder",
  "concept_to_illustrate": "The cyclical nature of motivation",
---

**13\. `image_placeholder`**

* **Purpose:** Marks a generic image to break up long sections of text.
* **Key Components/Attributes:**
  * `type: "image_placeholder"`
  * `description: str` (Brief description of the image or visual)
  * `caption: Optional[str]` (Suggested caption for the image)
  * `placement_suggestion: Optional[str]` (Where the image might appear, e.g., "after the third paragraph")
* **Placement Guidelines:** Use after 2–3 explanatory blocks or around every ~300 words to improve readability.
* **Example Usage:**
  JSON

```json
{
  "block_type": "image_placeholder",
  "description": "A relevant photo or graphic to break up text",
  "placement_suggestion": "after the third paragraph"
}
```

*
* **Notes:** These blocks provide visual rest points and do not need to depict a specific concept.

  "description": "A diagram showing motivation as a cycle: Initial Excitement -> Motivation Dip (challenges) -> Stable Engagement -> Renewal. Include arrows indicating progression.",
  "caption": "Figure 1: The Cyclical Nature of Motivation",
  "placement_suggestion": "after 'Understanding Motivation Cycles' section"
}
```

*   
* **Notes:** The AI should provide enough detail for a human or another tool to create the visual.

---

**12\. `flowchart_placeholder`**

* **Purpose:** Indicates where a visual flowchart is needed to illustrate a process or decision path.  
* **Key Components/Attributes:**  
  * `type: "flowchart_placeholder"`  
  * `process_name: str` (The name of the process the flowchart illustrates)  
  * `description: str` (Detailed description of the flowchart's steps, decision points, and flow)  
  * `caption: Optional[str]` (Suggested caption for the flowchart)  
  * `placement_suggestion: Optional[str]` (e.g., "after 'Process Steps Block on Resilience'")  
* **Placement Guidelines:** Typically follows a `process_steps` block or an `explanatory_text` block describing a process.  
* **Example Usage:**  
  JSON

```
{
  "block_type": "flowchart_placeholder",
  "process_name": "SMART Goal Transformation",
  "description": "A flowchart illustrating the steps to transform a vague goal into a SMART goal. Start with 'Vague Goal', lead to 'Apply SMART Criteria (Specific, Measurable, etc.)', then 'Refine Goal', ending with 'SMART Goal'. Include decision points for each criterion.",
  "caption": "Figure 2: Transforming Goals with the SMART Framework"
}
```

*   
* **Notes:** Similar to diagrams, detailed textual description is key.

