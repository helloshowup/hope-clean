"""
Content Comparator Module for the Simplified Workflow.

This module handles comparing and combining multiple content versions.
"""

import logging
import re
import asyncio
from typing import Dict, List, Any, Optional, Tuple

# Import from core modules
from showup_core.api_client import generate_with_claude
from .constants import EXCEL_CLARIFICATION
from showup_core.utils import load_prompt

# Set up logger
logger = logging.getLogger("simplified_workflow.content_comparator")

async def compare_and_combine(generations: List[str],
                         target_learner: str,
                         context: Dict[str, str],
                         instance_id: str = "default",
                         ui_settings: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    """
    Compare and combine multiple content versions.

    This function takes multiple content versions and compares them to determine
    the best version for the target learner.

    Args:
        generations: List of generated content versions to compare and combine
        target_learner: Description of the target learner to tailor content for
        context: Dictionary with context information for the comparison
        instance_id: ID for tracking within the workflow system.
                    Note: No longer passed to API calls as batch processing has been removed.
        ui_settings: Optional dictionary with UI settings, including token limit and model
        
    Returns:
        Tuple[str, str]: A tuple containing the best version and the explanation.
    """
    logger.info(f"Comparing and combining {len(generations)} content versions")
    
    if not generations:
        error_msg = "No content versions provided for comparison"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # If only one version was generated, return it directly
    if len(generations) == 1:
        logger.info("Only one content version available, skipping comparison")
        logger.debug("DIAGNOSIS: Returning tuple directly without coroutine wrapping")
        return generations[0], "Only one version was generated, so it was used directly."
    
    try:
        # Prepare the comparison prompt
        prompt = _create_comparison_prompt(generations, target_learner, context)
        
        # Create a system prompt
        system_prompt = (
            "You are an expert educational content reviewer with deep knowledge of "
            "instructional design principles and learning science. You excel at "
            "analyzing educational content and creating optimized versions that "
            "best serve the needs of specific learner populations."
            f"\n\n{EXCEL_CLARIFICATION}"
            "\n\nIMPORTANT: Your response MUST use these exact tags:"
            "1. <best_version>YOUR SELECTED BEST VERSION HERE</best_version>"
            "2. <explanation>YOUR EXPLANATION HERE</explanation>"
            "Failure to include these tags exactly as specified will cause system errors."
        )
        
        # Call Claude API with immediate execution
        logger.info(f"Calling Claude API for {len(generations)} generations comparison")
        
        try:
            # Call Claude API directly (batch processing has been removed from the workflow)
            # Use token limit from UI settings if provided, otherwise use 8000 as default
            token_limit = ui_settings.get('token_limit', 8000) if ui_settings else 8000
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
                task_type="content_comparison"
                # Batch processing parameters have been removed
            )
        except Exception as api_e:
            logger.error(f"Error calling Claude API: {str(api_e)}")
            logger.exception("API call exception details:")
            # Re-raise to be handled by the outer exception handler
            raise
        
        
        # Process direct result
        logger.info(f"Successfully generated comparison result ({len(result)} characters), processing now")
        
        try:
            # Extract best version and explanation
            best_version, explanation = _extract_comparison_results(result)
            
            logger.info(f"Extracted best version ({len(best_version)} characters) and explanation")
            logger.debug(f"DIAGNOSIS: Return type of extracted results: {type((best_version, explanation))}")
            return best_version, explanation
        except Exception as extract_e:
            logger.error(f"Error extracting comparison results: {str(extract_e)}")
            logger.exception("Extraction exception details:")
            
            # Create a simplified fallback from the raw result
            logger.warning("Using simplified extraction due to extraction error")
            try:
                # Try a simpler extraction approach
                if "<best_version>" in result:
                    parts = result.split("<best_version>")
                    if len(parts) > 1:
                        best_part = parts[1].split("</best_version>")[0].strip()
                        return best_part, f"Error in normal extraction: {str(extract_e)}. Using simplified extraction."
                
                # If even simplified extraction fails, fall through to the outer exception handler
                raise ValueError(f"Failed to extract content after extraction error: {str(extract_e)}")
            except Exception as fallback_e:
                logger.error(f"Error in fallback extraction: {str(fallback_e)}")
                raise extract_e  # Re-raise the original extraction error
        
    except Exception as e:
        error_msg = f"Error comparing content versions: {str(e)}"
        logger.error(error_msg)
        logger.exception("Comparison exception details:")
        
        # Enhanced fallback strategy with more logging
        fallback_strategy = "longest version"
        logger.warning(f"Using fallback strategy: {fallback_strategy}")
        
        try:
            # First try to find the most complete version (heuristic approach)
            most_complete_version = None
            max_tags = 0
            
            # Look for the version that has the most structural elements (simple heuristic)
            for version in generations:
                tags_count = version.count('<') + version.count('>')
                paragraphs = version.count('\n\n')
                sentences = version.count('.')
                score = tags_count + paragraphs + sentences
                
                if most_complete_version is None or score > max_tags:
                    most_complete_version = version
                    max_tags = score
            
            if most_complete_version and max_tags > 0:
                logger.info(f"Found most structurally complete version with score {max_tags}")
                return most_complete_version, f"Error in comparison process: {str(e)}. Using most structurally complete version as fallback."
            
            # If the heuristic approach didn't find anything meaningful, fall back to longest
            logger.info("Structural analysis inconclusive, falling back to longest version")
            longest_version = max(generations, key=len)
            return longest_version, f"Error in comparison process: {str(e)}. Using longest version as fallback."
            
        except Exception as fallback_e:
            # Ultimate fallback if even our fallback logic fails
            logger.error(f"Error in fallback selection: {str(fallback_e)}")
            logger.exception("Fallback exception details:")
            
            # Just use the first version if everything else fails
            logger.warning("Using first version as ultimate fallback due to errors")
            return generations[0], f"Multiple errors in comparison process: {str(e)}, then: {str(fallback_e)}. Using first version as ultimate fallback."

def _create_comparison_prompt(generations: List[str],
                             target_learner: str,
                             context: Dict[str, str]) -> str:
    """
    Create the prompt for comparing content versions.
    
    Args:
        generations: List of generated content versions
        target_learner: Description of the target learner
        context: Dictionary with context information
        
    Returns:
        Comparison prompt string
    """
    logger.info("Creating comparison prompt")
    
    # Format generations for the prompt
    formatted_generations = ""
    for i, generation in enumerate(generations):
        formatted_generations += f"\n\n--- VERSION {i+1} ---\n\n{generation}"
    
    # Get context elements
    template_context = context.get("TEMPLATE", "")
    educational_context = context.get("CONTEXT", "")
    
    try:
        # Try to load from template loader
        from .template_loader import get_content_comparison_template
        template = get_content_comparison_template()
        
        # Replace placeholders with actual values
        prompt = template.replace("{{target_learner}}", target_learner)
        prompt = prompt.replace("{{educational_context}}", educational_context)
        prompt = prompt.replace("{{template_context}}", template_context)
        prompt = prompt.replace("{{formatted_generations}}", formatted_generations)
        
        logger.info(f"Created comparison prompt from template loader ({len(prompt)} characters)")
        return prompt
    except ImportError:
        logger.warning("Template loader not available, using default template")

        template = load_prompt('review/content_comparison_prompt')
        prompt = template.replace('{{target_learner}}', target_learner)
        prompt = prompt.replace('{{educational_context}}', educational_context)
        prompt = prompt.replace('{{template_context}}', template_context)
        prompt = prompt.replace('{{formatted_generations}}', formatted_generations)

        logger.info(f"Created comparison prompt from file ({len(prompt)} characters)")
        return prompt

def _extract_comparison_results(result: str) -> Tuple[str, str]:
    """
    Extract the best version and explanation from the comparison result.
    
    Args:
        result: Result string from the Claude API
        
    Returns:
        Tuple of (best_version, explanation)
    """
    logger.info("Extracting comparison results")
    
    pattern = re.compile(
        r'^\s*<best_version>(.*?)</best_version>\s*<explanation>(.*?)</explanation>\s*$',
        re.DOTALL,
    )
    match = pattern.fullmatch(result)

    if match:
        best_version = match.group(1).strip()
        explanation = match.group(2).strip()
        return best_version, explanation

    errors = []
    if not re.search(r'<best_version>.*?</best_version>', result, re.DOTALL):
        errors.append("Expected <best_version> not found.")
    if not re.search(r'<explanation>.*?</explanation>', result, re.DOTALL):
        errors.append("Expected <explanation> not found.")

    cleaned = re.sub(r'<best_version>.*?</best_version>', '', result, flags=re.DOTALL)
    cleaned = re.sub(r'<explanation>.*?</explanation>', '', cleaned, flags=re.DOTALL)
    if cleaned.strip():
        errors.append("Extraneous text detected outside expected tags.")

    error_msg = " ".join(errors) if errors else "Unexpected format in comparison result."
    logger.error(error_msg)
    raise ValueError(error_msg)