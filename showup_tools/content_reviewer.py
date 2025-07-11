"""
Content Reviewer Module for the Simplified Workflow.

This module handles reviewing content for the target learner.
"""

import logging
import re
import asyncio
from typing import Dict, List, Any, Optional, Tuple

# Import from core modules
from showup_core.api_client import generate_with_claude
from .constants import EXCEL_CLARIFICATION

# Set up logger
logger = logging.getLogger("simplified_workflow.content_reviewer")

async def review_content(content: str, target_learner_profile: str, instance_id: str = "default", ui_settings: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    """
    Review and improve content for the target learner.

    This function takes content and reviews it to ensure it's suitable for the target
    learner profile.

    Args:
        content: Content text to review and improve
        target_learner_profile: Description of the target learner to tailor content for
        instance_id: ID for tracking within the workflow system.
                    Note: No longer passed to API calls as batch processing has been removed.

    Returns:
        Tuple[str, str]: A tuple containing the edited content and the edit summary.
    """
    logger.info("Reviewing content for target learner")
    
    if not content:
        error_msg = "No content provided for review"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Prepare the review prompt
        prompt = _create_review_prompt(content, target_learner_profile)
        
        # Create a system prompt
        system_prompt = (
            "You are an experienced educational content editor with expertise in "
            "asynchronous learning design and educational best practices. You excel "
            "at analyzing content from a learner's perspective, identifying issues, "
            "suggesting improvements, and revising content to enhance the learning experience."
            f"\n\n{EXCEL_CLARIFICATION}"
            "\n\nIMPORTANT: Your response MUST use these exact tags:"
            "1. <edited_content>YOUR IMPROVED CONTENT HERE</edited_content>"
            "2. <edit_summary>YOUR SUMMARY OF CHANGES HERE</edit_summary>"
            "Failure to include these tags exactly as specified will cause system errors."
        )
        # Call Claude API with immediate execution
        logger.info(f"Calling Claude API for content review, content length: {len(content)}")

        try:
            # Call Claude API directly (batch processing has been removed from the workflow)
            # Use token limit from UI settings if provided, otherwise fall back to model default
            token_limit = ui_settings.get('token_limit', 4000) if ui_settings else 4000
            model = (
                ui_settings.get('model', 'claude-3-haiku-20240307')
                if ui_settings
                else 'claude-3-haiku-20240307'
            )
            
            logger.info(f"Using token limit from UI settings: {token_limit}")
            
            result = await generate_with_claude(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=token_limit,
                temperature=0.3,  # Lower temperature for more consistent results
                model=model,
                task_type="content_review"
                # Batch processing parameters have been removed
            )
        except Exception as api_e:
            logger.error(f"Error calling Claude API: {str(api_e)}")
            logger.exception("API call exception details:")
            # Re-raise to be handled by the outer exception handler
            raise
        
        # Process direct result
        logger.info(f"Successfully generated direct review result ({len(result)} characters), processing now")
        
        try:
            # Extract edited content and edit summary
            edited_content, edit_summary = _extract_review_results(result)
            
            logger.info(f"Extracted edited content ({len(edited_content)} characters) and edit summary")
            return edited_content, edit_summary
        except Exception as extract_e:
            logger.error(f"Error extracting review results: {str(extract_e)}")
            logger.exception("Extraction exception details:")
            
            # Create a simplified fallback from the raw result
            logger.warning("Using simplified extraction due to extraction error")
            try:
                # Try a simpler extraction approach
                if "<edited_content>" in result:
                    parts = result.split("<edited_content>")
                    if len(parts) > 1:
                        edited_part = parts[1].split("</edited_content>")[0].strip()
                        return edited_part, f"Error in normal extraction: {str(extract_e)}. Using simplified extraction."
                
                # If even simplified extraction fails, fall through to the outer exception handler
                raise ValueError(f"Failed to extract content after extraction error: {str(extract_e)}")
            except Exception as fallback_e:
                logger.error(f"Error in fallback extraction: {str(fallback_e)}")
                # In case of extraction failure, return the original content
                return content, f"Review failed (extraction error): {str(extract_e)}"
        
    except Exception as e:
        error_msg = f"Error reviewing content: {str(e)}"
        logger.error(error_msg)
        logger.exception("Review exception details:")
        
        # Enhanced error reporting and fallback behavior
        logger.warning("Returning original content due to review failure")
        return content, f"Review failed: {type(e).__name__}: {str(e)}"

def _create_review_prompt(content: str, target_learner_profile: str) -> str:
    """
    Create the prompt for reviewing content.
    
    Args:
        content: Content to review
        target_learner_profile: Description of the target learner
        
    Returns:
        Review prompt string
    """
    logger.info("Creating review prompt")
    
    try:
        # Try to load from template loader
        from .template_loader import get_content_review_template
        template = get_content_review_template()
        
        # Replace placeholders with actual values
        prompt = template.replace("{{content}}", content)
        prompt = prompt.replace("{{target_learner_profile}}", target_learner_profile)
        
        logger.info(f"Created review prompt from template loader ({len(prompt)} characters)")
        return prompt
    except ImportError:
        logger.warning("Template loader not available, using hardcoded template")
        
        # Create the prompt
        prompt = f"""
You are an experienced educational content editor tasked with reviewing and making minor edits to learning material to improve its accessibility for a specific target learner. Your goal is to remove barriers to learning without significantly altering the core content or going overboard with changes.

First, carefully review the target learner profile:

<target_learner_profile>
{target_learner_profile}
</target_learner_profile>

Now, review the content that needs to be edited:

<content>
{content}
</content>

Your task is to make minor edits to the content that will remove barriers to learning for the target learner profile. Follow these guidelines:

1. Identify potential barriers to learning based on the target learner profile.
2. Make small, targeted changes to address these barriers. This may include:
   - Simplifying complex language
   - Clarifying confusing concepts
   - Adding brief explanations for unfamiliar terms
   - Adjusting formatting for better readability
   - Removing or modifying culturally insensitive content
3. Maintain the original structure and core message of the content.
4. Do not add substantial new information or remove large portions of the existing content.
5. Ensure that your edits are minimal and focused on improving accessibility rather than rewriting the entire piece.

After reviewing and editing the content, provide your output in the following format:

<edited_content>
[Insert the edited content here, with your minor changes implemented]
</edited_content>

<edit_summary>
[Provide a brief summary of the changes you made and why they were necessary for the target learner profile. Limit this to 3-5 bullet points.]
</edit_summary>

Remember, the goal is to make the content more accessible to the target learner without drastically changing its substance or going overboard with edits.
"""
        
        logger.info(f"Created hardcoded review prompt ({len(prompt)} characters)")
        return prompt

def _extract_review_results(result: str) -> Tuple[str, str]:
    """
    Extract the edited content and edit summary from the review result.
    
    Args:
        result: Result string from the Claude API
        
    Returns:
        Tuple of (edited_content, edit_summary)
    """
    logger.info("Extracting review results")
    
    # Extract edited content
    edited_content_match = re.search(r'<edited_content>(.*?)</edited_content>', 
                                    result, re.DOTALL)
    
    # Extract edit summary
    edit_summary_match = re.search(r'<edit_summary>(.*?)</edit_summary>', 
                                  result, re.DOTALL)
    
    if edited_content_match:
        edited_content = edited_content_match.group(1).strip()
    else:
        logger.warning("Edited content tags not found in review result")
        edited_content = result
    
    if edit_summary_match:
        edit_summary = edit_summary_match.group(1).strip()
    else:
        logger.warning("Edit summary tags not found in review result")
        edit_summary = "No edit summary provided."
    
    return edited_content, edit_summary