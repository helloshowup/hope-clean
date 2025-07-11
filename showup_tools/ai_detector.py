"""
AI Detector Module for the Simplified Workflow.

This module handles AI pattern detection and editing to make content more human-like.
"""

import logging
import re
import json
import os
from typing import Dict, List, Any, Optional, Tuple

# Import from core modules
from showup_core.api_client import generate_with_claude
from .constants import EXCEL_CLARIFICATION

# Set up logger
logger = logging.getLogger("simplified_workflow.ai_detector")

def detect_ai_patterns(content: str) -> Dict[str, Any]:
    """
    Detect AI-generated patterns using regex.
    
    Args:
        content: Content to analyze
        
    Returns:
        Dictionary with detected patterns and their locations
    """
    logger.info("Detecting AI patterns in content")
    
    if not content:
        logger.warning("No content provided for AI detection")
        return {"detected": False, "patterns": [], "text": ""}
    
    try:
        # Load AI phrases from JSON file
        ai_phrases_data = _load_ai_phrases()
        
        # Initialize results
        detected_patterns = []
        
        # Check for each pattern in the patterns array
        if "patterns" in ai_phrases_data:
            for category_data in ai_phrases_data["patterns"]:
                category = category_data.get("category", "Unknown")
                patterns = category_data.get("patterns", [])
                
                for pattern in patterns:
                    try:
                        regex = re.compile(pattern, re.IGNORECASE | re.DOTALL)
                        matches = list(regex.finditer(content))
                        
                        if matches:
                            for match in matches:
                                detected_patterns.append({
                                    "pattern": pattern,
                                    "description": f"AI pattern from category: {category}",
                                    "match": match.group(0),
                                    "start": match.start(),
                                    "end": match.end(),
                                    "category": category
                                })
                    except Exception as e:
                        logger.error(f"Error with regex pattern '{pattern}': {str(e)}")
        
        # Also check for simple phrases
        if "phrases" in ai_phrases_data:
            for phrase in ai_phrases_data["phrases"]:
                if isinstance(phrase, str) and phrase.strip():
                    try:
                        # Create a regex that matches the phrase as a whole word
                        regex = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
                        matches = list(regex.finditer(content))
                        
                        if matches:
                            for match in matches:
                                detected_patterns.append({
                                    "pattern": phrase,
                                    "description": "Common AI phrase",
                                    "match": match.group(0),
                                    "start": match.start(),
                                    "end": match.end(),
                                    "category": "Common Phrases"
                                })
                    except Exception as e:
                        logger.error(f"Error with phrase '{phrase}': {str(e)}")
        
        # Sort patterns by position in text
        detected_patterns.sort(key=lambda x: x["start"])
        
        # Prepare result
        result = {
            "detected": len(detected_patterns) > 0,
            "patterns": detected_patterns,
            "count": len(detected_patterns)
        }
        
        if detected_patterns:
            # Extract a portion of the text with detected patterns
            # Find the first and last pattern positions
            first_pos = detected_patterns[0]["start"]
            last_pos = detected_patterns[-1]["end"]
            
            # Extract text with some context
            context_size = 100  # characters before and after
            start_pos = max(0, first_pos - context_size)
            end_pos = min(len(content), last_pos + context_size)
            
            # Extract text with detected patterns
            result["text"] = content[start_pos:end_pos]
            
            logger.info(f"Detected {len(detected_patterns)} AI patterns")
        else:
            logger.info("No AI patterns detected")
        
        return result
        
    except Exception as e:
        error_msg = f"Error detecting AI patterns: {str(e)}"
        logger.error(error_msg)
        return {"detected": False, "patterns": [], "error": str(e)}

async def edit_content(content: str, detected_patterns: Dict[str, Any], target_learner: str, ui_settings: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
    """
    Edit content to make it more human-like.
    
    Args:
        content: Content to edit
        detected_patterns: Dictionary with detected AI patterns
        target_learner: Description of the target learner
        ui_settings: Dictionary with UI settings including token limit
        
    Returns:
        Tuple of (edited_content, explanation)
    """
    logger.info("Editing content to make it more human-like")
    
    if not content:
        error_msg = "No content provided for editing"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Check if content appears to be an AI assistant's response rather than educational content
    # Look for common phrases that might indicate confusion in the AI response
    error_indicators = [
        "I notice there's a misunderstanding",
        "You've asked me to edit AI-generated text",
        "what you've provided is actually",
        "I'll need you to provide the specific text"
    ]
    
    for indicator in error_indicators:
        if indicator.lower() in content.lower():
            logger.warning(f"Content appears to be an AI response rather than educational content: '{indicator}'")
            return content, "Content appears to be an AI response rather than educational content. No edits performed."
    
    # If no patterns detected, return original content
    if not detected_patterns.get("detected", False):
        logger.info("No AI patterns detected, returning original content")
        return content, "No AI patterns detected, no edits needed."
    
    try:
        # Prepare the editing prompt
        prompt = _create_editing_prompt(content, detected_patterns, target_learner)
        
        # Create a system prompt
        system_prompt = (
            "You are an expert editor specializing in making AI-generated content "
            "more human-like and natural. You excel at identifying patterns typical "
            "of AI writing and transforming them into authentic, engaging content "
            "that resonates with specific target audiences."
            f"\n\n{EXCEL_CLARIFICATION}"
        )
        
        # Call Claude API
        # Get token limit from ui_settings if available, otherwise use default
        token_limit = int(ui_settings.get("token_limit", 4000)) if ui_settings else 4000
        logger.info(f"Using token limit: {token_limit}")
        
        result = await generate_with_claude(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=token_limit,
            temperature=0.4,  # Moderate temperature for creativity but consistency
            task_type="content_editing"
            # Batch processing has been removed from the workflow
        )
        
        logger.info(f"Successfully generated editing result ({len(result)} characters)")
        
        # Extract edited content and explanation
        edited_content, explanation = _extract_editing_results(result)
        
        logger.info(f"Extracted edited content ({len(edited_content)} characters) and explanation")
        return edited_content, explanation
        
    except Exception as e:
        error_msg = f"Error editing content: {str(e)}"
        logger.error(error_msg)
        
        # Return original content if editing fails
        return content, f"Editing failed: {str(e)}"

def _load_ai_phrases() -> Dict[str, Any]:
    """
    Load AI phrases from JSON file.
    
    Returns:
        Dictionary with AI phrases data including patterns and phrases
    """
    logger.info("Loading AI phrases")
    
    try:
        # Path to AI phrases JSON file
        file_path = "C:\\Users\\User\\Desktop\\ShowupSquaredV4 (2)\\ShowupSquaredV4\\ShowupSquaredV4\\data\\ai_phrases.json"
        
        if not os.path.exists(file_path):
            logger.warning(f"AI phrases file not found: {file_path}")
            return {"phrases": [], "patterns": []}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            phrases_data = json.load(f)
            
        # Log the number of patterns and phrases
        pattern_count = len(phrases_data.get("patterns", []))
        phrase_count = len(phrases_data.get("phrases", []))
        logger.info(f"Loaded AI phrases data: {pattern_count} pattern categories, {phrase_count} individual phrases")
        
        return phrases_data
        
    except Exception as e:
        logger.error(f"Error loading AI phrases: {str(e)}")
        return {"phrases": [], "patterns": []}

def _create_editing_prompt(content: str, detected_patterns: Dict[str, Any], target_learner: str) -> str:
    """
    Create the prompt for editing content.
    
    Args:
        content: Content to edit
        detected_patterns: Dictionary with detected AI patterns
        target_learner: Description of the target learner
        
    Returns:
        Editing prompt string
    """
    logger.info("Creating editing prompt")
    
    # Format detected patterns for the prompt
    patterns_info = ""
    for i, pattern in enumerate(detected_patterns.get("patterns", [])):
        patterns_info += f"\n{i+1}. Pattern: '{pattern.get('match', '')}'\n   Description: {pattern.get('description', '')}"
    
    if not patterns_info:
        patterns_info = "No specific patterns provided, but the text has AI-like characteristics."
    
    try:
        # Try to load from template loader
        from .template_loader import get_ai_detection_editing_template
        template = get_ai_detection_editing_template()
        
        # Replace placeholders with actual values
        prompt = template.replace("{{content}}", content)
        prompt = prompt.replace("{{patterns_info}}", patterns_info)
        prompt = prompt.replace("{{target_learner}}", target_learner)
        
        logger.info(f"Created editing prompt from template loader ({len(prompt)} characters)")
        return prompt
    except ImportError:
        logger.warning("Template loader not available, using hardcoded template")
        
        # Create the prompt
        prompt = f"""
You are tasked with editing a piece of writing that has been detected as AI-generated to make it more human-like and suitable for a specific target learner. Your goal is to analyze the text, identify AI-like characteristics, and make appropriate edits using the Claude edit tool.

Here is the detected AI-written text:

<detected_ai_text>
{content}
</detected_ai_text>

The following AI patterns were detected:
{patterns_info}

The target learner for this text is:

<target_learner>
{target_learner}
</target_learner>

To complete this task, follow these steps:

1. Analyze the text:
   - Look for patterns typical of AI-generated content, such as overly formal language, repetitive structures, or lack of personal voice.
   - Identify any content that may not be suitable or engaging for the target learner.

2. Plan your edits:
   - Consider how to make the language more natural and conversational.
   - Think about ways to adapt the content to better suit the target learner's needs and interests.
   - Plan to vary sentence structures and vocabulary to create a more human-like flow.

3. Make edits using the Claude edit tool:
   - Use the edit tool to make changes that will make the text more human-like and appropriate for the target learner.
   - Focus on:
     a. Simplifying complex sentences if needed for the target learner
     b. Adding personal anecdotes or examples where appropriate
     c. Varying sentence length and structure
     d. Incorporating more natural transitions between ideas
     e. Adjusting vocabulary to match the target learner's level
     f. Adding rhetorical questions or conversational elements if suitable

4. Review and refine:
   - After making your initial edits, review the text again to ensure it reads naturally and meets the needs of the target learner.
   - Make any final adjustments to improve flow, coherence, and suitability.

5. Provide the edited version:
   - Present the final edited version of the text, ensuring it is more human-like and appropriate for the target learner.

Please output your edited version of the text within <edited_text> tags. Before the edited text, briefly explain the main changes you made and why they are appropriate for the target learner, enclosing this explanation in <explanation> tags.
"""
        
        logger.info(f"Created hardcoded editing prompt ({len(prompt)} characters)")
        return prompt

def _extract_editing_results(result: str) -> Tuple[str, str]:
    """
    Extract the edited content and explanation from the editing result.
    
    Args:
        result: Result string from the Claude API
        
    Returns:
        Tuple of (edited_content, explanation)
    """
    logger.info("Extracting editing results")
    
    # Extract edited text
    edited_text_match = re.search(r'<edited_text>(.*?)</edited_text>', 
                                 result, re.DOTALL)
    
    # Extract explanation
    explanation_match = re.search(r'<explanation>(.*?)</explanation>', 
                                 result, re.DOTALL)
    
    if edited_text_match:
        edited_text = edited_text_match.group(1).strip()
    else:
        logger.warning("Edited text tags not found in editing result")
        edited_text = result
    
    if explanation_match:
        explanation = explanation_match.group(1).strip()
    else:
        logger.warning("Explanation tags not found in editing result")
        explanation = "No explanation provided."
    
    return edited_text, explanation