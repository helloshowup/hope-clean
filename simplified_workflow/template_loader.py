"""
Template Loader Module for the Simplified Workflow.

This module handles loading templates from the JSON file or falling back to hardcoded templates.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

# Set up logger
logger = logging.getLogger("simplified_workflow.template_loader")

# Path to the templates JSON file
TEMPLATES_JSON_PATH = "C:\\Users\\User\\Desktop\\ShowupSquaredV4 (2)\\ShowupSquaredV4\\ShowupSquaredV4\\ShowupSquaredV4\\simplified_workflow_templates.json"

# Cache for loaded templates
_templates_cache = None

def load_templates() -> Dict[str, Any]:
    """
    Load templates from the JSON file.
    
    Returns:
        Dictionary with templates
    """
    global _templates_cache
    
    # Return cached templates if available
    if _templates_cache is not None:
        return _templates_cache
    
    logger.info(f"Loading templates from {TEMPLATES_JSON_PATH}")
    
    try:
        # Check if the file exists
        if not os.path.exists(TEMPLATES_JSON_PATH):
            logger.warning(f"Templates file not found: {TEMPLATES_JSON_PATH}")
            return {"templates": {}}
        
        # Load the templates
        with open(TEMPLATES_JSON_PATH, "r", encoding="utf-8") as f:
            templates = json.load(f)
        
        # Cache the templates
        _templates_cache = templates
        
        logger.info(f"Successfully loaded {len(templates.get('templates', {}))} templates")
        return templates
    
    except Exception as e:
        logger.error(f"Error loading templates: {str(e)}")
        return {"templates": {}}

def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a template by ID.
    
    Args:
        template_id: ID of the template
        
    Returns:
        Template dictionary or None if not found
    """
    templates = load_templates()
    
    if template_id in templates.get("templates", {}):
        logger.info(f"Found template: {template_id}")
        return templates["templates"][template_id]
    
    logger.warning(f"Template not found: {template_id}")
    return None

def get_template_content(template_id: str) -> Optional[str]:
    """
    Get the content of a template by ID.
    
    Args:
        template_id: ID of the template
        
    Returns:
        Template content or None if not found
    """
    template = get_template(template_id)
    
    if template is not None:
        return template.get("content")
    
    return None

def get_template_variables(template_id: str) -> List[str]:
    """
    Get the variables of a template by ID.
    
    Args:
        template_id: ID of the template
        
    Returns:
        List of variable names
    """
    template = get_template(template_id)
    
    if template is not None:
        return template.get("variables", [])
    
    return []

def get_content_generation_template() -> str:
    """
    Get the content generation template.
    
    Returns:
        Content generation template string
    """
    # Always use the specified high school lesson template file
    excel_template_path = "C:\\Users\\User\\Desktop\\ShowupSquaredV4 (2)\\ShowupSquaredV4\\ShowupSquaredV4\\showup_tools\\simplified_app\\templates\\high-school-lesson-template.md"
    logger.info(f"Loading content generation template from: {excel_template_path}")
    
    try:
        # Load the template file directly
        with open(excel_template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Create a cleaner structured prompt that avoids API formatting issues
        enhanced_prompt = f"""
        You are a professional physical education curriculum developer creating NEW original educational content for a physical education course.
        
        YOUR TASK:
        Create a COMPLETE, ORIGINAL LESSON about "{{{topic}}}" for {{{target_learner}}} in {{{course_name}}}.
        This lesson should teach {{{objective}}} through practical, engaging activities and clear explanations.
        
        CONTENT OUTLINE TO COVER:
        {{{content_outline}}}
        
        CRITICAL INSTRUCTIONS:
        1. Generate COMPLETELY NEW, original educational content (do not ask for text to edit)
        2. Write as a complete, ready-to-use lesson (not template placeholders)
        3. Include clear explanations, examples, and activities relevant to physical education
        4. Use age-appropriate language for {{{target_learner}}}
        5. Make content practical and actionable for physical education classes
        6. Do not include placeholder text or template instructions in your final output
        7. Format with proper markdown headings, lists, and structure
        8. Focus on creating substantive, instructionally sound content
        
        REQUIRED LESSON STRUCTURE:
        
        {template_content}
        
        Your response should be 600-800 words in length. Create high-quality educational content that could be used immediately in a physical education classroom.
        Do not reference this prompt or include meta-commentary - just provide the finished lesson content.
        """
        
        logger.info(f"Successfully prepared enhanced template ({len(enhanced_prompt)} characters)")
        return enhanced_prompt
    except Exception as e:
        # If there's an error loading the template file, log it and fall back to default
        logger.error(f"Error loading high school lesson template file: {str(e)}")
        logger.warning("Falling back to hardcoded content generation template")
        
        # Create a default template instead of recursive import
        default_template = f"""
        You are a professional physical education curriculum developer creating NEW original educational content for a physical education course.
        
        YOUR TASK:
        Create a COMPLETE, ORIGINAL LESSON about "{{{{topic}}}}" for {{{{target_learner}}}} in {{{{course_name}}}}.
        This lesson should teach {{{{objective}}}} through practical, engaging activities and clear explanations.
        
        CONTENT OUTLINE TO COVER:
        {{{{content_outline}}}}
        
        CRITICAL INSTRUCTIONS:
        1. Generate COMPLETELY NEW, original educational content (do not ask for text to edit)
        2. Write as a complete, ready-to-use lesson (not template placeholders)
        3. Include clear explanations, examples, and activities relevant to physical education
        4. Use age-appropriate language for {{{{target_learner}}}}
        5. Make content practical and actionable for physical education classes
        6. Do not include placeholder text or template instructions in your final output
        7. Format with proper markdown headings, lists, and structure
        8. Focus on creating substantive, instructionally sound content
        
        Your response should be 600-800 words in length. Create high-quality educational content that could be used immediately in a physical education classroom.
        Do not reference this prompt or include meta-commentary - just provide the finished lesson content.
        """
        return default_template

def get_content_review_template() -> str:
    """
    Get the content review template.
    
    Returns:
        Content review template string
    """
    template_content = get_template_content("content_review")
    
    if template_content is not None:
        return template_content
    
    # Fall back to hardcoded template
    logger.warning("Falling back to hardcoded content review template")
    
    # Define the review template directly to avoid circular imports
    hardcoded_template = """
    You are an educational content reviewer with expertise in curriculum design and pedagogy. Your task is to review educational content and provide feedback on its quality, clarity, and educational effectiveness.
    
    Below is the content to review:
    
    <content>
    {{content}}
    </content>
    
    This content is intended for the following target learner profile:
    
    <target_learner_profile>
    {{target_learner_profile}}
    </target_learner_profile>
    
    Please review the content according to the following criteria:
    1. **Accuracy**: Is the information factually correct and up-to-date?
    2. **Clarity**: Is the content clear, well-organized, and appropriate for the target learner?
    3. **Engagement**: Does the content effectively engage the intended audience?
    4. **Educational Value**: Does the content effectively support the learning objectives?
    5. **Inclusivity**: Is the content accessible and inclusive for diverse learners?
    
    For each criterion, provide a rating (Excellent, Good, Satisfactory, Needs Improvement) and specific feedback explaining your assessment.
    
    Conclude with:
    1. Overall rating (Excellent, Good, Satisfactory, Needs Improvement)
    2. A summary of strengths
    3. Up to three specific recommendations for improvement
    4. A revised version of any sections that need significant improvement
    
    Present your review in the following format:
    <review>
    [Your detailed review here, organized by criteria]
    </review>
    """
    
    return hardcoded_template

def get_content_comparison_template() -> str:
    """
    Get the content comparison template.
    
    Returns:
        Content comparison template string
    """
    template_content = get_template_content("content_comparison")
    
    if template_content is not None:
        return template_content
    
    # Fall back to hardcoded template
    logger.warning("Falling back to hardcoded content comparison template")
    
    # Import here to avoid circular imports
    from .content_comparator import _create_comparison_prompt
    
    # Create a dummy prompt with placeholders
    dummy_generations = ["{{formatted_generations}}"]
    dummy_target_learner = "{{target_learner}}"
    dummy_context = {
        "TEMPLATE": "{{template_context}}",
        "CONTEXT": "{{educational_context}}"
    }
    
    # Get the template with placeholders
    template = _create_comparison_prompt(dummy_generations, dummy_target_learner, dummy_context)
    
    # Replace the actual values with placeholders
    template = template.replace("{{formatted_generations}}", "{{formatted_generations}}")
    template = template.replace("{{target_learner}}", "{{target_learner}}")
    template = template.replace("{{template_context}}", "{{template_context}}")
    template = template.replace("{{educational_context}}", "{{educational_context}}")
    
    return template

def get_ai_detection_editing_template() -> str:
    """
    Get the AI detection editing template.
    
    Returns:
        AI detection editing template string
    """
    template_content = get_template_content("ai_detection_editing")
    
    if template_content is not None:
        return template_content
    
    # Fall back to hardcoded template
    logger.warning("Falling back to hardcoded AI detection editing template")
    
    # Import here to avoid circular imports
    from .ai_detector import _create_editing_prompt
    
    # Create a dummy prompt with placeholders
    dummy_content = "{{content}}"
    dummy_detected_patterns = {"patterns": [], "count": 0}
    dummy_target_learner = "{{target_learner}}"
    
    # Get the template with placeholders
    template = _create_editing_prompt(dummy_content, dummy_detected_patterns, dummy_target_learner)
    
    # Replace the actual values with placeholders
    template = template.replace(dummy_content, "{{content}}")
    template = template.replace("No specific patterns provided, but the text has AI-like characteristics.", "{{patterns_info}}")
    template = template.replace(dummy_target_learner, "{{target_learner}}")
    
    return template