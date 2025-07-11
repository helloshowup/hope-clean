"""
Content Generator Module for the Simplified Workflow.

This module handles generating content using the Claude API.
"""

import logging
import os
import time
import concurrent.futures
import asyncio
import json
from typing import Dict, List, Any, Optional

# Import from core modules
from showup_core.api_client import generate_with_claude
# Import RAG system
from showup_tools.simplified_app.rag_system import enhanced_generate_content
from .constants import EXCEL_CLARIFICATION

# Set up logger
logger = logging.getLogger("simplified_workflow.content_generator")

async def generate_content(variables: Dict[str, str], template: str, settings: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate content using Claude API.

    Args:
        variables: Dictionary with variables for template substitution
        template: Template string with placeholders for variables
        settings: Dictionary with generation settings

    Returns:
        Generated content as a string
    """
    logger.info(f"Generating content for {variables.get('step_title', 'unknown step')}")

    # Get settings or use defaults
    if settings is None:
        settings = {}

    # Get generation settings
    gen_settings = settings.get("generation_settings", {})
    
    # Get token limit from UI settings with fallback
    max_tokens = int(settings.get("token_limit", gen_settings.get("max_tokens", 4000)))
    
    # Other settings
    temperature = gen_settings.get("temperature", 0.5)
    word_count = gen_settings.get("character_limit", 500)   # Default to 500 words, using character_limit field for backward compatibility
    
    # Get model from settings - prioritize initial_generation_model if available
    model = settings.get(
        "initial_generation_model",
        settings.get("selected_model", "claude-3-haiku-20240307"),
    )

    # Get template-specific settings if available
    template_type = variables.get("template_type", "").lower()
    template_settings = settings.get("template_settings", {}).get(template_type, {})

    # Override with template-specific settings if available
    if template_settings:
        max_tokens = template_settings.get("max_tokens", max_tokens)
        temperature = template_settings.get("temperature", temperature)
        word_count = template_settings.get("character_limit", word_count)   # Using character_limit field for backward compatibility
        word_count = template_settings.get("word_count", word_count)   # Also check for word_count field
        model = template_settings.get("model", model)

    logger.info(f"Using settings: max_tokens={max_tokens}, temperature={temperature}, "
                f"word_count={word_count}, model={model}")

    # Substitute variables in template
    prompt = template
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        # Convert non-string values to strings to avoid "replace() argument 2 must be str, not dict" error
        if not isinstance(value, str):
            logger.debug(f"Converting non-string value for key '{key}' from {type(value)} to string")
            value = str(value)
        prompt = prompt.replace(placeholder, value)

    # Add word count instruction to the prompt
    if word_count > 0:
        word_count_instruction = (
            f"\n\nIMPORTANT: Your response should be approximately {word_count} words "
            f"in length. This is a target, not a strict limit, but aim to keep your content "
            f"around this word count for consistency."
        )
        prompt += word_count_instruction

    # Log prompt length for debugging
    logger.debug(f"Prompt length: {len(prompt)} characters")

    try:
        # Create a system prompt that complements the structured prompt
        # Extract critical variables for the system prompt
        step_title = variables.get('step_title', 'Unknown Topic')
        content_outline = variables.get('content_outline', '')
        rationale = variables.get('rationale', '')
        topic = variables.get('topic', '')
        
        # Create a clearly labeled rationale section if available
        rationale_section = ""
        if rationale:
            rationale_section = f"\n\nThe educational rationale for this content is: '{rationale}'"
        
        system_prompt = (
            "You are an expert educational content creator specializing in curriculum development for Excel High School. "
            "You excel at crafting clear, engaging, and instructionally sound content for learners of all levels. "
            f"Your specific task is to create content for: '{step_title}'. "
            f"Stay EXACTLY on topic and follow this content outline precisely: '{content_outline}'. "
            f"{rationale_section}"
            "\n\nDo NOT create content about science topics unless specifically instructed to do so in the outline. "
            "Do NOT create content about photosynthesis, water cycles, or other random science topics unless specifically mentioned in the outline. "
            f"\n\n{EXCEL_CLARIFICATION}"
            "\n\nIMPORTANT: Your content must directly address the specific '{step_title}' topic and follow the content outline exactly as provided."
            "\n\nIMPORTANT FORMATTING REQUIREMENT: You MUST wrap your entire content with <educational_content> tags like this:"
            "<educational_content>"
            "All your actual content goes here"
            "</educational_content>"
            "Failure to include these tags exactly as specified will cause system errors."
        )

        # Check if handbook_path is provided to use RAG-enhanced generation
        handbook_path = variables.get('handbook_path', None)
        
        if handbook_path and os.path.exists(handbook_path):
            logger.info(f"Using RAG system with handbook: {handbook_path}")
            # Use the RAG-enhanced content generation
            content = await enhanced_generate_content(
                variables=variables,
                template=prompt,  # We've already done the variable substitution
                settings={
                    "system_prompt": system_prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "model": model
                }
            )
        else:
            # Call Claude API directly if no handbook is provided
            logger.info("Using direct Claude API call (no RAG)")
            content = await generate_with_claude(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                model=model,
                task_type="content_generation"
            )

        logger.info(f"Successfully generated content ({len(content)} characters)")
        return content

    except Exception as e:
        error_msg = f"Error generating content: {str(e)}"
        logger.error(error_msg)
        if isinstance(e, RuntimeError):
            raise
        else:
            raise RuntimeError(f"Error during asynchronous operation: {error_msg}")

async def generate_three_versions_from_plan(final_plan: Dict[str, Any], ui_settings: Optional[Dict[str, Any]] = None) -> List[str]:
    """Generate three script versions from a finalized plan."""

    if ui_settings is None:
        ui_settings = {}

    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "generation_prompt.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error(f"Generation prompt not found: {prompt_path}")
        raise

    prompt = prompt_template.replace("{{final_plan}}", json.dumps(final_plan, ensure_ascii=False))

    max_tokens = ui_settings.get("generation_settings", {}).get("max_tokens", 4000)
    freq_pen = ui_settings.get("generation_settings", {}).get("frequency_penalty", 0.0)
    pres_pen = ui_settings.get("generation_settings", {}).get("presence_penalty", 0.0)
    model = ui_settings.get("initial_generation_model", ui_settings.get("selected_model", "claude-3-haiku-20240307"))

    temperatures = [0.3, 0.5, 1.0]
    versions = []

    for idx, temp in enumerate(temperatures):
        logger.info(f"Generating version {idx+1} with temperature {temp} using model {model}")
        content = await generate_with_claude(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temp,
            model=model,
            frequency_penalty=freq_pen,
            presence_penalty=pres_pen,
            task_type="content_generation",
        )
        versions.append(content)
        # Encourage diversity for the next version
        prompt += "\n\nNOTE: Provide a distinctly different take for the next version."

    logger.info("Completed generation of all three versions from plan")
    return versions


def extract_educational_content(content: str) -> str:
    """
    Extract content from between <educational_content> tags.
    
    Args:
        content: Generated content that may contain tags
        
    Returns:
        Extracted content without tags
    """
    logger.info("Extracting educational content from generated text")
    
    start_tag = "<educational_content>"
    end_tag = "</educational_content>"
    
    start_index = content.find(start_tag)
    end_index = content.find(end_tag)
    
    if start_index != -1 and end_index != -1:
        # Extract content between tags
        extracted_content = content[start_index + len(start_tag):end_index].strip()
        logger.info(f"Successfully extracted content between tags ({len(extracted_content)} characters)")
        return extracted_content
    else:
        # If tags not found, return the original content
        logger.warning("Educational content tags not found, returning original content")
        return content

def load_content_generation_template() -> str:
    """
    Load the content generation template.
    
    Returns:
        Template string for content generation
    """
    # IMPORTANT NOTES: 
    # 1. All content generation will now use high-school-lesson-template structure regardless of
    #    whether the CSV specifies "Article", "Video", or any other template type
    # 2. When adding more templates to this directory, extend this code to select between them
    #    based on template_type or other variables
    # 3. The system maintains a fallback mechanism below to prevent workflow failures
    #    if templates are missing
    
    # Path to templates directory specified by user
    template_dir = r"C:\Users\User\Desktop\ShowupSquaredV4 (2)\ShowupSquaredV4\ShowupSquaredV4\showup_tools\simplified_app\templates"
    template_path = os.path.join(template_dir, "high-school-lesson-template.md")
    
    logger.info(f"Loading content generation template from {template_path}")
    
    # TODO: Future enhancement - implement template selection logic like this:
    # variables["template_type"].lower() could be used to select appropriate template
    # e.g., if template_type.lower() == "article":
    #     template_path = os.path.join(template_dir, "article-template.md")
    # elif template_type.lower() == "video":
    #     template_path = os.path.join(template_dir, "video-template.md")
    # etc.
    
    # Try to load the template from file
    try:
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as file:
                template = file.read()
                logger.info("Successfully loaded template from file")
                return template
        else:
            logger.warning(f"Template file not found: {template_path}")
    except Exception as e:
        logger.error(f"Error loading template file: {str(e)}")
    
    # Fallback template if file loading fails
    logger.warning("Using fallback hardcoded template")
    template = """
    You are a professional physical education curriculum developer creating NEW original educational content for a physical education course.
        
    YOUR TASK:
    Create a COMPLETE, ORIGINAL LESSON about {{topic}} for {{target_learner}} in {{course_name}}.
    This lesson should teach {{objective}} through practical, engaging activities and clear explanations.
    
    CONTENT OUTLINE TO COVER:
    {{content_outline}}
    
    CRITICAL INSTRUCTIONS:
    1. Generate COMPLETELY NEW, original educational content (do not ask for text to edit)
    2. Write as a complete, ready-to-use lesson (not template placeholders)
    3. Include clear explanations, examples, and activities relevant to physical education
    4. Use age-appropriate language for {{target_learner}}
    5. Make content practical and actionable for physical education classes
    6. Do not include placeholder text or template instructions in your final output
    7. Format with proper markdown headings, lists, and structure
    8. Focus on creating substantive, instructionally sound content
    
    Your response should be 600-800 words in length. Create high-quality educational content that could be used immediately in a physical education classroom.
    Do not reference this prompt or include meta-commentary - just provide the finished lesson content.
    """
    
    logger.info(f"Using default content generation template ({len(template)} characters)")
    return template