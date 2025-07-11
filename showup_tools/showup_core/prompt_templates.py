"""
Prompt Templates module for structured prompt generation.

This module provides a sophisticated template system for creating well-structured
prompts with specific sections for instructions, context, examples, thinking and
answer formatting. It includes pre-defined templates for common educational tasks.
"""

import os
import logging
import re
from typing import Dict, Optional, List, Tuple

# Import from the same package
from .config import DIRS

# Initialize logger
logger = logging.getLogger("prompt_templates")
logger.setLevel(logging.INFO)

class PromptTemplateSystem:
    """
    A system for creating structured prompts with specific sections.
    
    This class provides methods for creating prompts with standardized sections:
    - <instructions>: Main task description and requirements
    - <context>: Background information and existing content
    - <example>: Sample inputs/outputs or content examples
    - <thinking>: Chain-of-thought reasoning sections
    - <answer>: Final output sections
    
    It includes pre-defined templates for common educational tasks like lesson content,
    module analysis, course outlines, and educational assessments.
    """
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize the PromptTemplateSystem with safe fallbacks.
        
        Args:
            template_dir: Optional custom directory for templates
        """
        self.logger = logger
        
        # Safely access templates directory
        if template_dir:
            self.template_dir = template_dir
            self.logger.info(f"Using provided template directory: {template_dir}")
        else:
            try:
                # Check if DIRS['templates']['root'] exists
                if 'templates' in DIRS and isinstance(DIRS['templates'], dict) and 'root' in DIRS['templates']:
                    self.template_dir = os.path.join(DIRS['templates']['root'])
                    self.logger.info(f"Using templates directory from DIRS: {self.template_dir}")
                else:
                    # Fallback to the correct templates path within the project
                    from .config import BASE_DIR
                    self.template_dir = os.path.join(BASE_DIR, 'data', 'input', 'templates')
                    self.logger.warning(f"Templates 'root' key not found in DIRS, using fallback path: {self.template_dir}")
            except Exception as e:
                # Fallback to the correct templates path within the project
                from .config import BASE_DIR
                self.template_dir = os.path.join(BASE_DIR, 'data', 'input', 'templates')
                self.logger.warning(f"Error accessing templates directory: {str(e)}. Using fallback: {self.template_dir}")
        
        self.template_cache = {}  # Cache templates to avoid repeated file reads
        
        # Check if template directory exists
        if not os.path.exists(self.template_dir):
            try:
                os.makedirs(self.template_dir, exist_ok=True)
                self.logger.info(f"Created template directory: {self.template_dir}")
            except Exception as e:
                self.logger.error(f"Failed to create template directory: {str(e)}, some features may not work properly")
        
        # Pre-defined role prompts
        self.role_prompts = {
            "educator": "You are an experienced educator who specializes in explaining technical concepts clearly. You break down complex ideas into understandable parts and provide helpful examples.",
            "instructional_designer": "You are an expert instructional designer with years of experience in curriculum development. You focus on creating clear learning objectives, well-structured content, and effective assessments.",
            "editor": "You are a skilled educational editor who refines content to be clear, engaging, and accessible. You maintain the educational value while improving the presentation and flow.",
            "reviewer": "You are a thorough reviewer who carefully examines educational content for clarity, accuracy, and effectiveness. You provide specific, actionable feedback."
        }
        
        # Load pre-defined templates
        self.templates = self._load_predefined_templates()
        logger.info("PromptTemplateSystem initialized")
    
    def _load_predefined_templates(self) -> Dict[str, str]:
        """
        Load pre-defined templates for common educational tasks.
        
        Returns:
            Dict mapping template names to template content
        """
        # Start with built-in templates
        templates = {
            "LessonContent": self._create_lesson_content_template(),
            "ModuleAnalysis": self._create_module_analysis_template(),
            "CourseOutline": self._create_course_outline_template(),
            "EducationalAssessment": self._create_educational_assessment_template(),
            "LessonFlow": self._create_lesson_flow_template()
        }
        
        # Try to load external templates from template directory
        try:
            external_templates = self._load_external_templates()
            # Add external templates, preferring them over built-in if names clash
            templates.update(external_templates)
            
            # Log the number of external templates loaded
            num_external = len(external_templates)
            if num_external > 0:
                self.logger.info(f"Loaded {num_external} external templates from {self.template_dir}")
        except Exception as e:
            self.logger.warning(f"Error loading external templates: {str(e)}")
        
        return templates
    
    def _load_external_templates(self) -> Dict[str, str]:
        """
        Load external templates from the template directory.
        
        Returns:
            Dict mapping template names to template content
        """
        external_templates = {}
        
        # Check for template directory
        if not os.path.exists(self.template_dir):
            self.logger.warning(f"Template directory not found: {self.template_dir}")
            return external_templates
        
        # Look for template files with supported extensions
        template_files = []
        for ext in ['.md', '.txt', '.template']:
            template_files.extend([f for f in os.listdir(self.template_dir) if f.endswith(ext)])
        
        # Load each template file
        for filename in template_files:
            try:
                # Get template name from filename (without extension)
                template_name = os.path.splitext(filename)[0]
                
                # Skip if name starts with underscore (private templates)
                if template_name.startswith('_'):
                    continue
                
                # Load template content
                filepath = os.path.join(self.template_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                # Convert to CamelCase for consistency
                template_name = ''.join(word.capitalize() for word in template_name.split('_'))
                
                # Add to templates dict
                external_templates[template_name] = template_content
                self.logger.info(f"Loaded external template: {template_name}")
            except Exception as e:
                self.logger.warning(f"Error loading template {filename}: {str(e)}")
        
        return external_templates
    
    def _create_lesson_content_template(self) -> str:
        """
        Create template for lesson content generation tasks.
        
        Returns:
            Template string for lesson content generation
        """
        return """
<instructions>
As an experienced instructional designer with expertise in curriculum development, create engaging and educational content for {topic}. Your content should:

- Present concepts clearly with a logical progression from basic to advanced
- Include practical examples that illustrate key points
- Address common misconceptions or areas of confusion
- Use appropriate terminology consistently throughout
- Incorporate opportunities for active learning and reflection
- Balance theory with practical application
- Consider the needs of diverse learners
- Maintain educational continuity with adjacent learning content

{additional_requirements}
</instructions>

<context>
Target audience: {target_audience}
Learning objectives: {learning_objectives}
Prior knowledge: {prior_knowledge}

Educational continuity:
Previous module context: {previous_module_context}
Next module context: {next_module_context}
Previous lesson context: {previous_lesson_context}
Next lesson context: {next_lesson_context}
Previous step context: {previous_step_context}
Next step context: {next_step_context}

This content's position in learning sequence:
Module {module_number}: {module_title}
Lesson {lesson_number}: {lesson_title}
Step {step_number}: {step_title}

{additional_context}
</context>

<example>
{example_content}
</example>

<thinking>
Let me think through this lesson content systematically:
1. First, I'll identify the core concepts students need to understand
2. Then, I'll organize these concepts in a logical sequence
3. For each concept, I'll plan clear explanations with specific examples
4. I'll identify potential misconceptions and address them
5. I'll incorporate opportunities for practice and application
6. I'll ensure this content connects smoothly with previous and next content
7. I'll reference previous concepts that students should already understand
8. I'll foreshadow upcoming concepts to create an integrated learning experience

{additional_thinking}
</thinking>

<answer>
# {lesson_title}

## Introduction
{introduction_placeholder}

## Learning Objectives
By the end of this lesson, students will be able to:
- {objective_1}
- {objective_2}
- {objective_3}

## Main Content
{main_content_placeholder}

### {subtopic_1}
{subtopic_1_content}

### {subtopic_2}
{subtopic_2_content}

## Connections to Previous Learning
{previous_learning_connections}

## Preparation for Upcoming Content
{next_learning_preview}

## Summary
{summary_placeholder}

## Assessment
{assessment_placeholder}

{additional_sections}
</answer>
"""
    
    def _create_module_analysis_template(self) -> str:
        """
        Create template for module analysis tasks.
        
        Returns:
            Template string for module analysis
        """
        return """
<instructions>
As an expert instructional designer with years of experience in curriculum development and learning science, analyze the educational module on {topic} and provide a comprehensive analysis. Your analysis should:
- Evaluate alignment between objectives, content, and assessments using established instructional design frameworks
- Identify strengths and areas for improvement based on evidence-based learning principles
- Consider diverse learning styles, accessibility requirements, and universal design for learning
- Suggest practical, research-backed enhancements to improve learning outcomes and engagement
- Evaluate educational continuity between this module and adjacent modules
{additional_requirements}
</instructions>

<context>
Module content: {module_content}
Target audience: {target_audience}
Learning objectives: {learning_objectives}

Course structure context:
Previous module: {previous_module_title}
Next module: {next_module_title}
Module position: {module_position} of {total_modules}

{additional_context}
</context>

<example>
{example_analysis}
</example>

<thinking>
Let me analyze this module systematically as an instructional design professional:
1. First, I'll examine how well the content aligns with stated objectives using Bloom's taxonomy and constructive alignment principles
2. I'll evaluate the pedagogical approaches used and their effectiveness based on current learning science research
3. I'll identify potential knowledge gaps, misconceptions, or areas where students might struggle using cognitive load theory
4. I'll consider how well the module addresses diverse learning needs through universal design principles and differentiation strategies
5. I'll assess the assessment methods against best practices in authentic and formative assessment
6. I'll analyze how this module builds on previous modules and prepares for subsequent ones
7. I'll identify any gaps in educational continuity that might disrupt the learning experience

{additional_thinking}
</thinking>

<answer>
# Module Analysis: {module_title}

## Overview
{overview_placeholder}

## Alignment with Learning Objectives
{alignment_analysis}

## Content Analysis
{content_analysis}

## Educational Continuity
### How This Module Builds on Previous Learning
{builds_on_previous}

### How This Module Prepares for Upcoming Content
{prepares_for_upcoming}

## Assessment Strategy
{assessment_analysis}

## Recommendations for Improvement
1. {recommendation_1}
2. {recommendation_2}
3. {recommendation_3}

{additional_sections}
</answer>
"""
    
    def _create_course_outline_template(self) -> str:
        """
        Create template for course outline generation tasks.
        
        Returns:
            Template string for course outline generation
        """
        return """
<instructions>
As an expert in asynchronous online curriculum design with extensive experience developing self-paced educational content, create a comprehensive course outline for {subject}. Drawing on your expertise in digital learning environments where students work independently without real-time instructor guidance, the outline should:
- Provide a logical progression of topics that works effectively in a self-paced, asynchronous format
- Include clear, measurable learning objectives for each module that students can self-assess against
- Balance theoretical knowledge with practical application through varied digital activities that can be completed independently
- Consider appropriate content chunking and pacing for asynchronous learners who need to maintain motivation without regular live sessions
- Incorporate diverse assessment strategies suitable for automated feedback or self-evaluation
- Design for engagement and clarity knowing students must navigate the material without immediate instructor clarification
- Ensure strong educational continuity between modules to create a cohesive learning experience
{additional_requirements}
</instructions>

<context>
Course duration: {course_duration}
Target audience: {target_audience}
Prerequisites: {prerequisites}
{additional_context}
</context>

<example>
{example_outline}
</example>

<thinking>
Let me plan this course outline systematically as an asynchronous learning specialist:
1. First, I'll identify core concepts that can be effectively taught in a digital, self-paced environment
2. Then I'll organize these into logical, self-contained modules with clear entry and exit points for flexibility
3. I'll ensure content is appropriately chunked into digestible segments (10-15 minute learning objects) to maintain engagement
4. I'll incorporate multimedia elements and interactive components to compensate for the lack of live instruction
5. I'll design clear, unambiguous instructions that don't require clarification from an instructor
6. I'll include regular knowledge checks and automated feedback opportunities throughout each module
7. I'll build in scaffolded independent activities that provide sufficient guidance for learners working alone
8. I'll create strong transitions between modules to maintain educational continuity
9. I'll consider how to create a sense of presence and community despite the asynchronous nature of the course
10. I'll ensure accessibility considerations for diverse learners accessing content on different devices and in different contexts

{additional_thinking}
</thinking>

<answer>
# Course Outline: {course_title}

## Course Description
{course_description}

## Target Audience
{audience_description}

## Prerequisites
{prerequisites_list}

## Course Objectives
By the end of this course, students will be able to:
- {course_objective_1}
- {course_objective_2}
- {course_objective_3}

## Course Navigation and Structure
{navigation_guidance}

## Learning Progression
{learning_progression_overview}

## Module Structure

### Module 1: {module_1_title}
- Learning objectives:
  - {module_1_objective_1}
  - {module_1_objective_2}
- Topics covered:
  - {module_1_topic_1}
  - {module_1_topic_2}
- Independent learning activities:
  - {module_1_activity_1}
  - {module_1_activity_2}
- Self-assessment: {module_1_assessment}
- Estimated completion time: {module_1_time}
- Connects to next module by: {module_1_next_connection}

### Module 2: {module_2_title}
- Learning objectives:
  - {module_2_objective_1}
  - {module_2_objective_2}
- Topics covered:
  - {module_2_topic_1}
  - {module_2_topic_2}
- Independent learning activities:
  - {module_2_activity_1}
  - {module_2_activity_2}
- Self-assessment: {module_2_assessment}
- Estimated completion time: {module_2_time}
- Builds on previous module by: {module_2_previous_connection}
- Connects to next module by: {module_2_next_connection}

{additional_modules}

## Assessment Strategy
{assessment_strategy}

## Learning Resources and Technical Requirements
{learning_resources}

## Self-Paced Learning Strategies
{self_paced_strategies}

{additional_sections}
</answer>
"""
    
    def _create_educational_assessment_template(self) -> str:
        """
        Create template for educational assessment generation tasks.
        
        Returns:
            Template string for educational assessment generation
        """
        return """
<instructions>
As an expert in asynchronous online assessment design, create educational assessments for {topic} that effectively measure student understanding without requiring real-time instructor supervision. Drawing on your expertise in digital evaluation methods for self-paced environments, these assessments should:
- Precisely align with stated learning objectives to enable automated or self-evaluation
- Include a variety of question types that work effectively in an asynchronous digital environment (multiple choice, matching, drag-and-drop, automated-graded short answer)
- Assess different levels of cognitive understanding through carefully scaffolded questions that don't require immediate instructor clarification
- Provide exceptionally clear instructions and unambiguous scoring criteria for learners working independently
- Incorporate immediate automated feedback mechanisms that guide student learning
- Include built-in academic integrity measures appropriate for unsupervised assessment
- Consider technical limitations and accessibility requirements for diverse online learners
- Connect to prior and upcoming learning content to reinforce the learning progression
{additional_requirements}
</instructions>

<context>
Learning objectives: {learning_objectives}
Content covered: {content_covered}
Target audience: {target_audience}

Educational continuity:
Previous learning content: {previous_content}
Next learning content: {next_content}

{additional_context}
</context>

<example>
{example_assessment}
</example>

<thinking>
Let me design these assessments systematically as an asynchronous assessment specialist:
1. First, I'll identify which learning objectives can be effectively measured through automated digital assessment
2. Then I'll create assessment items that provide valid measurements without requiring instructor interpretation
3. I'll ensure question wording is completely unambiguous to prevent confusion during independent completion
4. I'll design a mix of formative (practice) and summative assessments with appropriate automated feedback
5. I'll incorporate knowledge checks that provide immediate guidance without instructor intervention
6. I'll consider how to maintain assessment security and validity in an unsupervised environment
7. I'll ensure the assessment functions properly across different devices and internet connectivity scenarios
8. I'll provide clear time expectations and completion guidance for self-paced learners
9. I'll include alternative assessment options where appropriate for learners with different needs
10. I'll reference previous learning and prepare students for upcoming content to reinforce educational continuity

{additional_thinking}
</thinking>

<answer>
# Assessment: {assessment_title}

## Introduction and Context
This assessment connects to your learning journey by:
- Building on your previous knowledge of: {builds_on_previous}
- Preparing you for upcoming learning about: {prepares_for_upcoming}

## Instructions for Students
{student_instructions}

## Part 1: Knowledge Check
1. {knowledge_question_1}
   a. {option_1a}
   b. {option_1b}
   c. {option_1c}
   d. {option_1d}

2. {knowledge_question_2}
   a. {option_2a}
   b. {option_2b}
   c. {option_2c}
   d. {option_2d}

## Part 2: Comprehension and Application
3. {comprehension_question}
   [Short answer response]

4. {application_question}
   [Extended response]

## Part 3: Analysis and Evaluation
5. {analysis_question}
   [Extended response]

6. {evaluation_question}
   [Extended response]

## Scoring Rubric
{scoring_rubric}

## Self-Review Questions
After completing this assessment, reflect on your learning by answering:
- How does this content connect to what you learned previously?
- What questions do you still have about this topic?
- How will you apply this knowledge in upcoming lessons?

## Answer Key
{answer_key}

{additional_sections}
</answer>
"""

    def _create_lesson_flow_template(self) -> str:
        """
        Create template for lesson flow generation tasks.
        
        Returns:
            Template string for lesson flow generation
        """
        return """
<instructions>
As an expert in instructional sequencing and learning design, create a detailed lesson flow for {topic} that provides a logical progression of learning experiences. Your lesson flow should:
- Present content in a sequence that builds understanding from foundational to advanced concepts
- Include a variety of learning activities that engage different learning styles
- Incorporate appropriate knowledge checks and assessment opportunities
- Balance direct instruction with active learning experiences
- Consider appropriate pacing and transitions between activities
- Include clear connections between lessons to create a cohesive learning experience
- Ensure strong educational continuity with previous and upcoming content
{additional_requirements}
</instructions>

<context>
Module focus: {module_focus}
Target audience: {target_audience}
Learning objectives: {learning_objectives}
Time constraints: {time_constraints}

Educational continuity:
Previous lesson content: {previous_lesson_content}
Next lesson content: {next_lesson_content}

{additional_context}
</context>

<example>
{example_flow}
</example>

<thinking>
Let me design this lesson flow systematically:
1. First, I'll identify the key concepts and skills that need to be developed
2. I'll determine the logical prerequisites and build a sequence that provides necessary scaffolding
3. I'll plan for variety in learning activities to maintain engagement and address different learning styles
4. I'll incorporate appropriate formative assessment points to check understanding
5. I'll consider the cognitive load throughout the sequence and ensure appropriate pacing
6. I'll identify potential points of confusion and plan additional support or clarification
7. I'll ensure clear transitions between lessons that reinforce connections between concepts
8. I'll explicitly connect to previous learning content to activate prior knowledge
9. I'll preview upcoming content to prepare students for future learning

{additional_thinking}
</thinking>

<answer>
# Lesson Flow: {module_title}

## Overview
{overview_description}

## Educational Continuity
### Builds on Previous Learning
{builds_on_previous}

### Prepares for Upcoming Content
{prepares_for_upcoming}

## Lesson Sequence

### Lesson 1: {lesson_1_title}
- Key concepts: {lesson_1_concepts}
- Learning activities: {lesson_1_activities}
- Estimated time: {lesson_1_time}
- Assessment approach: {lesson_1_assessment}
- Connection to previous content: {lesson_1_previous_connection}
- Connection to next lesson: {lesson_1_next_connection}

### Lesson 2: {lesson_2_title}
- Key concepts: {lesson_2_concepts}
- Learning activities: {lesson_2_activities}
- Estimated time: {lesson_2_time}
- Assessment approach: {lesson_2_assessment}
- Connection to previous lesson: {lesson_2_previous_connection}
- Connection to next lesson: {lesson_2_next_connection}

### Lesson 3: {lesson_3_title}
- Key concepts: {lesson_3_concepts}
- Learning activities: {lesson_3_activities}
- Estimated time: {lesson_3_time}
- Assessment approach: {lesson_3_assessment}
- Connection to previous lesson: {lesson_3_previous_connection}
- Connection to next lesson: {lesson_3_next_connection}

{additional_lessons}

## Learning Progression and Connections
{learning_progression}

## Differentiation Strategies
{differentiation_strategies}

{additional_sections}
</answer>
"""
    
    def create_prompt(self,
                     template_name: str,
                     variables: Dict[str, str],
                     role: Optional[str] = None,
                     examples: Optional[List[Dict[str, str]]] = None,
                     include_sections: Optional[List[str]] = None) -> str:
        """
        Create a prompt using a predefined template with variable substitution.
        
        Args:
            template_name: Name of the predefined template to use
            variables: Dictionary of variables to substitute in the template
            role: Optional role to add to the prompt
            examples: Optional list of examples to add for few-shot learning
            include_sections: Optional list of sections to include (instructions, context, thinking, answer)
                             If None, all sections are included
            
        Returns:
            Formatted prompt string
        """
        # Try to find the template
        if template_name not in self.templates:
            # Attempt to load custom template
            custom_template = self._load_custom_template(template_name)
            if custom_template:
                self.templates[template_name] = custom_template
                self.logger.info(f"Loaded custom template: {template_name}")
            else:
                self.logger.warning(f"Template '{template_name}' not found, using LessonContent as default")
                template_name = "LessonContent"
        
        # Get the template
        template = self.templates[template_name]
        
        # Add role if provided
        if role and role in self.role_prompts:
            role_prompt = self.role_prompts[role]
            self.logger.info(f"Adding {role} role to prompt")
            template = f"{role_prompt}\n\n{template}"
        
        # Add few-shot examples if provided
        if examples and len(examples) > 0:
            examples_text = "\n\n".join([self._format_example(example) for example in examples])
            
            # Check if there's an <example> tag to replace
            if "<example>" in template and "</example>" in template:
                # Replace the <example> section
                start = template.find("<example>")
                end = template.find("</example>", start) + len("</example>")
                template = template[:start] + f"<example>\n{examples_text}\n</example>" + template[end:]
            else:
                # Just append examples after the role but before the template
                self.logger.info(f"Adding {len(examples)} few-shot examples to prompt")
                role_end = template.find("\n\n") + 2 if role else 0
                template = template[:role_end] + f"Here are some examples for reference:\n\n{examples_text}\n\n" + template[role_end:]
        
        # Substitute variables in the template
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            if value:  # Only replace if value is not None or empty
                template = template.replace(placeholder, str(value))
        
        # Handle educational continuity placeholders with defaults if not provided
        educational_continuity_placeholders = [
            "previous_module_context", "next_module_context",
            "previous_lesson_context", "next_lesson_context", 
            "previous_step_context", "next_step_context",
            "builds_on_previous", "prepares_for_upcoming",
            "previous_content", "next_content",
            "module_1_next_connection", "module_2_previous_connection", 
            "module_2_next_connection", "lesson_1_previous_connection",
            "lesson_1_next_connection", "lesson_2_previous_connection",
            "lesson_2_next_connection", "lesson_3_previous_connection",
            "lesson_3_next_connection"
        ]
        
        for placeholder in educational_continuity_placeholders:
            placeholder_tag = "{" + placeholder + "}"
            if placeholder_tag in template:
                # Replace with empty string or default message
                template = template.replace(placeholder_tag, "[Not provided]")
        
        # Clean up any remaining placeholders
        template = re.sub(r'\{[a-zA-Z_]+\}', '', template)
        
        # Filter sections if requested
        if include_sections:
            template = self._filter_sections(template, include_sections)
        
        self.logger.info(f"Created prompt from template '{template_name}' with {len(variables)} variables")
        return template
    
    def _filter_sections(self, template: str, include_sections: List[str]) -> str:
        """
        Filter template to only include specified sections.
        
        Args:
            template: The template to filter
            include_sections: List of section names to include
            
        Returns:
            Filtered template
        """
        # Define all possible sections
        all_sections = ["instructions", "context", "example", "thinking", "answer"]
        
        # Normalize section names to lowercase
        include_sections = [s.lower() for s in include_sections]
        
        # Start with the parts before any section tags
        result = template.split("<" + all_sections[0])[0]
        
        # Process each section
        for section in all_sections:
            if section.lower() in include_sections:
                # Include this section if it exists in the template
                section_start = template.find(f"<{section}>")
                if section_start >= 0:
                    section_end = template.find(f"</{section}>", section_start) + len(f"</{section}>")
                    if section_end > section_start:
                        section_content = template[section_start:section_end]
                        result += "\n\n" + section_content
            
        return result
    
    def _load_custom_template(self, template_name: str) -> Optional[str]:
        """
        Load a custom template from the template directory.
        
        Args:
            template_name: Name of the template to load
            
        Returns:
            Template content if found, None otherwise
        """
        # Check if we have it in cache
        if template_name in self.template_cache:
            return self.template_cache[template_name]
            
        # Try different filename formats
        possible_filenames = [
            f"{template_name}.md",
            f"{template_name}.txt",
            f"{template_name}.template",
            f"{template_name.lower()}.md",
            f"{template_name.lower()}.txt",
            f"{template_name.lower()}.template",
            f"{'_'.join(re.findall('[A-Z][^A-Z]*', template_name)).lower()}.md"  # CamelCase to snake_case
        ]
        
        for filename in possible_filenames:
            file_path = os.path.join(self.template_dir, filename)
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Add to cache
                        self.template_cache[template_name] = content
                        self.logger.info(f"Loaded custom template: {filename}")
                        return content
            except Exception as e:
                self.logger.warning(f"Error loading template {filename}: {str(e)}")
                
        return None
    
    def _format_example(self, example: Dict[str, str]) -> str:
        """
        Format an example for few-shot learning.
        
        Args:
            example: Dictionary with example data
            
        Returns:
            Formatted example string
        """
        if "input" in example and "output" in example:
            return f"Input:\n{example['input']}\n\nOutput:\n{example['output']}"
        else:
            # Just join all key-value pairs
            return "\n\n".join([f"{k.capitalize()}:\n{v}" for k, v in example.items()])
    
    def create_custom_prompt(self,
                           instructions: str,
                           context: Optional[str] = None,
                           examples: Optional[List[Dict[str, str]]] = None,
                           thinking: Optional[str] = None,
                           answer_format: Optional[str] = None,
                           role: Optional[str] = None,
                           educational_continuity: Optional[str] = None) -> str:
        """
        Create a custom prompt with specified sections.
        
        Args:
            instructions: Main task instructions
            context: Optional background context
            examples: Optional examples for few-shot learning
            thinking: Optional thinking/reasoning guidance
            answer_format: Optional format for the answer
            role: Optional role to add to the prompt
            educational_continuity: Optional educational continuity information
            
        Returns:
            Formatted prompt string
        """
        # Start with role if provided
        prompt_parts = []
        
        if role and role in self.role_prompts:
            prompt_parts.append(self.role_prompts[role])
        
        # Add instructions section
        prompt_parts.append(f"<instructions>\n{instructions}\n</instructions>")
        
        # Add context section if provided, including educational continuity if available
        if context:
            context_content = context
            
            # Add educational continuity information if provided
            if educational_continuity:
                context_content = f"{context}\n\nEducational Continuity:\n{educational_continuity}"
                
            prompt_parts.append(f"<context>\n{context_content}\n</context>")
        elif educational_continuity:
            # Add educational continuity as its own context if no other context
            prompt_parts.append(f"<context>\nEducational Continuity:\n{educational_continuity}\n</context>")
        
        # Add examples section if provided
        if examples and len(examples) > 0:
            examples_text = "\n\n".join([self._format_example(example) for example in examples])
            prompt_parts.append(f"<example>\n{examples_text}\n</example>")
        
        # Add thinking section if provided
        if thinking:
            # Add educational continuity consideration to thinking process
            enhanced_thinking = thinking
            if "continuity" not in thinking.lower() and educational_continuity:
                enhanced_thinking += "\n8. I'll consider how this content connects to previous and upcoming learning to enhance educational continuity"
                
            prompt_parts.append(f"<thinking>\n{enhanced_thinking}\n</thinking>")
        
        # Add answer format section if provided
        if answer_format:
            # Check if answer format includes connections to other content
            if "previous" not in answer_format.lower() and "next" not in answer_format.lower() and educational_continuity:
                # Add educational continuity sections to answer format
                lines = answer_format.split("\n")
                # Insert educational continuity sections before Summary or similar ending sections
                insert_position = len(lines)
                for i, line in enumerate(lines):
                    if any(ending in line.lower() for ending in ["summary", "conclusion", "assessment", "additional"]):
                        insert_position = i
                        break
                
                # Insert educational continuity sections
                continuity_sections = [
                    "## Connections to Previous Learning",
                    "{previous_learning_connections}",
                    "",
                    "## Preparation for Upcoming Content",
                    "{next_learning_preview}",
                    ""
                ]
                
                enhanced_answer_format = "\n".join(lines[:insert_position] + continuity_sections + lines[insert_position:])
                prompt_parts.append(f"<answer>\n{enhanced_answer_format}\n</answer>")
            else:
                prompt_parts.append(f"<answer>\n{answer_format}\n</answer>")
        
        # Join all parts
        prompt = "\n\n".join(prompt_parts)
        
        components = ["role", "instructions", "context", "examples", "thinking", "answer", "educational_continuity"]
        values = [role, True, context, examples, thinking, answer_format, educational_continuity]
        included = [c for c, v in zip(components, values) if v]
        
        self.logger.info("Created custom prompt with sections: " + ", ".join(included))
        
        return prompt
        
    def create_standardized_prompt(self, 
                                 sections: Dict[str, str],
                                 role: Optional[str] = None) -> str:
        """
        Create a standardized prompt with consistent section formatting.
        
        Args:
            sections: Dictionary with section names as keys and content as values.
                     Supported sections: title, instructions, context, examples, thinking, answer, educational_continuity
            role: Optional role to add to the prompt
            
        Returns:
            Formatted prompt string with clear section headers
        """
        prompt_parts = []
        
        # Add role if provided
        if role and role in self.role_prompts:
            prompt_parts.append(self.role_prompts[role])
        
        # Add title if provided
        if "title" in sections and sections["title"]:
            prompt_parts.append(f"# {sections['title']}")
        
        # Add standard sections in preferred order
        section_order = ["instructions", "context", "educational_continuity", "examples", "thinking", "answer"]
        
        # Special handling for educational_continuity - incorporate into context if both exist
        if "educational_continuity" in sections and sections["educational_continuity"] and "context" in sections and sections["context"]:
            sections["context"] = sections["context"] + "\n\nEducational Continuity:\n" + sections["educational_continuity"]
            # Remove from sections dict to avoid duplication
            del sections["educational_continuity"]
        
        for section in section_order:
            if section in sections and sections[section]:
                # Convert examples to properly formatted text if it's a list
                if section == "examples" and isinstance(sections[section], list):
                    formatted_examples = "\n\n".join([self._format_example(example) for example in sections[section]])
                    prompt_parts.append(f"<{section}>\n{formatted_examples}\n</{section}>")
                else:
                    section_tag = "context" if section == "educational_continuity" else section
                    prompt_parts.append(f"<{section_tag}>\n{sections[section]}\n</{section_tag}>")
        
        # Join all parts with double newlines for clear separation
        standardized_prompt = "\n\n".join(prompt_parts)
        
        self.logger.info(f"Created standardized prompt with sections: {', '.join([s for s in sections.keys() if sections[s]])}")
        return standardized_prompt
        
    def convert_to_system_user_format(self, prompt: str) -> Tuple[str, str]:
        """
        Convert a structured prompt to system and user messages for API calls.
        
        Args:
            prompt: The structured prompt to convert
            
        Returns:
            Tuple of (system_message, user_message)
        """
        # Extract role if present at the beginning
        role_prompt = ""
        if prompt.startswith("You are "):
            end_of_role = prompt.find("\n\n")
            if end_of_role > 0:
                role_prompt = prompt[:end_of_role].strip()
                prompt = prompt[end_of_role:].strip()
        
        # Extract thinking section if present
        thinking_section = ""
        if "<thinking>" in prompt and "</thinking>" in template:
            start = prompt.find("<thinking>") + len("<thinking>")
            end = prompt.find("</thinking>")
            thinking_section = prompt[start:end].strip()
            # Remove thinking section from prompt
            prompt = prompt[:prompt.find("<thinking>")] + prompt[prompt.find("</thinking>") + len("</thinking>"):]
        
        # Determine what goes in system vs user message
        if role_prompt:
            # If role prompt exists, it becomes the system message
            system_message = role_prompt
            
            # Add thinking guidance to system message if present
            if thinking_section:
                system_message += f"\n\nWhen responding, use this thinking process to analyze the request:\n{thinking_section}"
                
            # The rest becomes the user message
            user_message = prompt.strip()
        else:
            # No role prompt, so make a generic system message
            if thinking_section:
                system_message = f"You are an AI assistant skilled in creating educational content. When responding, use this thinking process to analyze the request:\n{thinking_section}"
            else:
                system_message = "You are an AI assistant skilled in creating educational content."
            
            # The rest becomes the user message
            user_message = prompt.strip()
        
        # Ensure the section tags are removed from user message
        for tag in ["<instructions>", "</instructions>", "<context>", "</context>", 
                   "<example>", "</example>", "<answer>", "</answer>", 
                   "<educational_continuity>", "</educational_continuity>"]:
            user_message = user_message.replace(tag, "")
        
        # Clean up any empty lines from tag removal
        user_message = re.sub(r'\n{3,}', '\n\n', user_message)
        
        self.logger.info(f"Converted prompt to system ({len(system_message)} chars) and user ({len(user_message)} chars) messages")
        return system_message, user_message
        
    def get_template_names(self) -> List[str]:
        """
        Get a list of all available template names.
        
        Returns:
            List of template names
        """
        return list(self.templates.keys())
        
    def register_template(self, name: str, content: str) -> bool:
        """
        Register a new template or update an existing one.
        
        Args:
            name: Template name
            content: Template content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add to templates dict
            self.templates[name] = content
            # Add to cache
            self.template_cache[name] = content
            
            self.logger.info(f"Registered template: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to register template {name}: {str(e)}")
            return False
            
    def save_template(self, name: str, content: str) -> bool:
        """
        Save a template to the template directory.
        
        Args:
            name: Template name
            content: Template content
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert CamelCase to snake_case for filename
            filename = ''.join(['_' + c.lower() if c.isupper() else c for c in name]).lstrip('_')
            filename = f"{filename}.md"
            
            file_path = os.path.join(self.template_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Register the template
            self.register_template(name, content)
            
            self.logger.info(f"Saved template to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save template {name}: {str(e)}")
            return False

# Function for backward compatibility
def create_structured_prompt(instructions: str, context: str = "", examples: List[Dict[str, str]] = None, 
                           thinking: str = "", answer_format: str = "", role: str = None,
                           educational_continuity: str = "") -> str:
    """
    Create a structured prompt with specified sections.
    
    This is a convenience function for backward compatibility.
    
    Args:
        instructions: Main task instructions
        context: Optional background context
        examples: Optional examples for few-shot learning
        thinking: Optional thinking/reasoning guidance
        answer_format: Optional format for the answer
        role: Optional role to add to the prompt
        educational_continuity: Optional educational continuity information
        
    Returns:
        Formatted prompt string
    """
    try:
        template_system = PromptTemplateSystem()
        return template_system.create_custom_prompt(
            instructions=instructions,
            context=context,
            examples=examples,
            thinking=thinking,
            answer_format=answer_format,
            role=role,
            educational_continuity=educational_continuity
        )
    except Exception as e:
        logger.error(f"Error creating structured prompt: {str(e)}")
        
        # Fall back to manual creation
        prompt_parts = []
        
        # Define role messages
        role_prompts = {
            "educator": "You are an experienced educator who specializes in explaining technical concepts clearly. You break down complex ideas into understandable parts and provide helpful examples.",
            "expert": "You are a subject matter expert in this field with years of professional experience. You provide accurate, nuanced insights based on deep domain knowledge.",
            "editor": "You are a skilled educational editor who refines content to be clear, engaging, and accessible. You maintain the educational value while improving the presentation and flow.",
            "reviewer": "You are a thorough reviewer who carefully examines educational content for clarity, accuracy, and effectiveness. You provide specific, actionable feedback."
        }
        
        # Add role if provided
        if role and role in role_prompts:
            prompt_parts.append(role_prompts[role])
        
        # Add instructions section
        prompt_parts.append(f"<instructions>\n{instructions}\n</instructions>")
        
        # Add context section if provided
        if context:
            # Add educational continuity information if provided
            if educational_continuity:
                context = f"{context}\n\nEducational Continuity:\n{educational_continuity}"
            prompt_parts.append(f"<context>\n{context}\n</context>")
        elif educational_continuity:
            # Add educational continuity as its own context if no other context
            prompt_parts.append(f"<context>\nEducational Continuity:\n{educational_continuity}\n</context>")
        
        # Add examples section if provided
        if examples and len(examples) > 0:
            examples_text = "\n\n".join([f"Input:\n{e.get('input', '')}\n\nOutput:\n{e.get('output', '')}" 
                                       if 'input' in e and 'output' in e else 
                                       "\n\n".join([f"{k.capitalize()}:\n{v}" for k, v in e.items()])
                                       for e in examples])
            prompt_parts.append(f"<example>\n{examples_text}\n</example>")
        
        # Add thinking section if provided
        if thinking:
            prompt_parts.append(f"<thinking>\n{thinking}\n</thinking>")
        
        # Add answer format section if provided
        if answer_format:
            prompt_parts.append(f"<answer>\n{answer_format}\n</answer>")
        
        # Join all parts
        return "\n\n".join(prompt_parts)