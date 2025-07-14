{{lesson_metadata.title}}
Module ID: {{lesson_metadata.module_id}}
Subtitle: {{lesson_metadata.subtitle}}
Purpose: {{lesson_metadata.purpose}}

Learning Objectives
{{learning_objectives.objectives[0]}}

{{learning_objectives.objectives[1]}}

{{learning_objectives.objectives[2]}}

... (add more as needed, or dynamically generate)

Introduction
{{introduction.content_summary}}

Hook Suggestion: {{introduction.hook_suggestion}}

{{section_heading.title}}
{{section_heading.level}}
{{explanatory_text.topic}}

Key Points:

{{explanatory_text.key_points[0]}}

{{explanatory_text.key_points[1]}}

...

Tone Suggestion: {{explanatory_text.tone_suggestion}}

{{list_block.heading}}
{{list_block.list_type}} list:
{% for item in list_block.items_summary %}

{{item}}
{% endfor %}

Example Analysis: {{example_analysis.example_title}}
Initial Statement: {{example_analysis.initial_statement}}

Analysis Criteria:

{{example_analysis.analysis_criteria[0]}}

{{example_analysis.analysis_criteria[1]}}

...

Improved Version Summary: {{example_analysis.improved_version_summary}}

Explanation Points:

{{example_analysis.explanation_points[0]}}

{{example_analysis.explanation_points[1]}}

...

Process: {{process_steps.process_name}}
{{process_steps.introductory_text}}

Steps:
{% for step in process_steps.steps %}
{{loop.index}}. {{step.title}}: {{step.description}}
{% endfor %}

Reflection Prompt
{{reflection_prompt.prompt_heading}}

{{reflection_prompt.context_setting}}

Questions:

{{reflection_prompt.questions[0]}}

{{reflection_prompt.questions[1]}}

...

Key Takeaways
{{key_takeaways.points[0]}}

{{key_takeaways.points[1]}}

...
