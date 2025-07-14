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
from simplified_workflow.rag_system import enhanced_generate_content
from .constants import EXCEL_CLARIFICATION
from showup_core.utils import load_prompt

# Set up logger
logger = logging.getLogger("simplified_workflow.content_generator")

# Simple block-specific instructions used when generating content
BLOCK_INSTRUCTIONS = {
    "lesson_metadata": "Write a header using the title and optional subtitle.",
    "learning_objectives": "Present the objectives as a bulleted list.",
    "introduction": "Compose an engaging introduction based on the content_summary and optional hook_suggestion.",
    "section_heading": "Output an H{level} heading titled '{title}'.",
    "explanatory_text": "Explain the topic covering the key_points. Apply tone_suggestion if provided.",
    "list_block": "Create a {list_type} list titled '{heading}' expanding each item in items_summary.",
    "example_analysis": "Describe the example, initial_statement, improved_version_summary and explanation_points.",
    "process_steps": "Outline the process with the given steps, using introductory_text if present.",
    "reflection_prompt": "Provide the questions as a reflection exercise with the prompt_heading.",
    "key_takeaways": "Summarize the key points as bullet list.",
    "diagram_placeholder": "Give a detailed textual description for the diagram concept_to_illustrate.",
    "flowchart_placeholder": "Give a detailed textual description for the flowchart process_name.",
}

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

        # Check if reference_handbook_path is provided to use RAG-enhanced generation
        handbook_path = variables.get('reference_handbook_path', None)

        if handbook_path and os.path.exists(handbook_path):
            logger.info(f"Using RAG system with handbook: {handbook_path}")
            # Use the RAG-enhanced content generation
            variables['handbook_path'] = handbook_path
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
        verify_educational_content_tags(content)
        return content

    except Exception as e:
        error_msg = f"Error generating content: {str(e)}"
        logger.error(error_msg)
        if isinstance(e, RuntimeError):
            raise
        else:
            raise RuntimeError(f"Error during asynchronous operation: {error_msg}")

async def generate_three_versions_from_plan(
    final_plan: Dict[str, Any], template: str, ui_settings: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Generate three content versions from a finalized plan using a Markdown template."""

    if ui_settings is None:
        ui_settings = {}

    use_dynamic = ui_settings.get("use_dynamic_blocks", True) and not template
    system_prompt = load_prompt("system/ai_editor_system_message")

    try:
        prompt_template = load_prompt("generation/generation_prompt")
    except FileNotFoundError:
        logger.error("Generation prompt not found")
        raise

    max_tokens = ui_settings.get("generation_settings", {}).get("max_tokens", 4000)
    freq_pen = ui_settings.get("generation_settings", {}).get("frequency_penalty", 0.0)
    pres_pen = ui_settings.get("generation_settings", {}).get("presence_penalty", 0.0)
    model = ui_settings.get("initial_generation_model", ui_settings.get("selected_model", "claude-3-haiku-20240307"))
    total_words = ui_settings.get("generation_settings", {}).get("word_count", 500)

    if use_dynamic:
        content_blocks = final_plan.get("content_blocks", [])
        if not isinstance(content_blocks, list):
            raise ValueError("final_plan must contain content_blocks list")

        per_block_words = max(1, total_words // max(len(content_blocks), 1))

        async def generate_version(temp: float) -> str:
            parts = []
            for block in content_blocks:
                instruction = BLOCK_INSTRUCTIONS.get(block.get("block_type", ""), "Expand this block into lesson content.")
                prompt = (
                    prompt_template.replace("{{block}}", json.dumps(block, ensure_ascii=False))
                    .replace("{{instruction}}", instruction.format(**block))
                    .replace("{{word_count}}", str(per_block_words))
                )
                result = await generate_with_claude(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temp,
                    model=model,
                    frequency_penalty=freq_pen,
                    presence_penalty=pres_pen,
                    system_prompt=system_prompt,
                    task_type="content_generation",
                )
                verify_educational_content_tags(result)
                parts.append(result.strip())
            return "\n\n".join(parts)
    else:
        prompt = prompt_template.replace("{{final_plan}}", json.dumps(final_plan, ensure_ascii=False))
        prompt = prompt.replace("{{block}}", "").replace("{{instruction}}", "")
        if template:
            prompt += "\n\nUse this Markdown template to structure the lesson:\n" + template

        async def generate_version(temp: float) -> str:
            version_prompt = prompt + ("\n\nNOTE: Provide a distinctly different take for the next version." if temp != 0.3 else "")
            result = await generate_with_claude(
                prompt=version_prompt,
                max_tokens=max_tokens,
                temperature=temp,
                model=model,
                frequency_penalty=freq_pen,
                presence_penalty=pres_pen,
                system_prompt=system_prompt,
                task_type="content_generation",
            )
            verify_educational_content_tags(result)
            return result.strip()

    temperatures = [0.3, 0.5, 1.0]
    tasks = [asyncio.create_task(generate_version(t)) for t in temperatures]
    versions = await asyncio.gather(*tasks)

    for v in versions:
        verify_educational_content_tags(v)

    logger.info("Completed generation of all three versions from plan")
    return list(versions)


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

def verify_educational_content_tags(content: str) -> bool:
    """Check that the generated content includes <educational_content> tags."""
    start_tag = "<educational_content>"
    end_tag = "</educational_content>"
    if start_tag in content and end_tag in content:
        return True
    logger.warning("<educational_content> tags missing from generated output")
    return False

from pathlib import Path

def load_content_generation_template(ui_settings: Optional[Dict[str, Any]] = None) -> str:
    """Load the content generation template.

    Args:
        ui_settings: Optional settings dict. If it contains a
            ``template_directory`` key, templates will be loaded from this
            directory. Otherwise the default ``templates`` folder in the
            repository root is used.

    Returns:
        Template string for content generation.
    """
    # IMPORTANT NOTES: 
    # 1. All content generation will now use high-school-lesson-template structure regardless of
    #    whether the CSV specifies "Article", "Video", or any other template type
    # 2. When adding more templates to this directory, extend this code to select between them
    #    based on template_type or other variables
    # 3. The system maintains a fallback mechanism below to prevent workflow failures
    #    if templates are missing
    
    if ui_settings is None:
        ui_settings = {}

    template_dir_setting = ui_settings.get("template_directory")
    if template_dir_setting:
        template_dir = Path(template_dir_setting)
    else:
        template_dir = Path(__file__).resolve().parents[1] / "templates"

    template_path = template_dir / "high-school-lesson-template.md"
    
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
        if template_path.exists():
            with template_path.open('r', encoding='utf-8') as file:
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
