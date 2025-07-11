#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script generation module for podcast generator.

Handles the creation of podcast scripts using OpenAI API and script validation.
"""

import os
import re
import logging
import requests
from dotenv import load_dotenv
import sys
from showup_editor_ui.claude_panel.path_utils import get_project_root

# Ensure we can find the root directory to load the .env file
root_dir = str(get_project_root())
# Add the root directory to sys.path if it's not already there
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Load .env file from the root directory
env_path = os.path.join(root_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    
logger = logging.getLogger('podcast_generator')

# Check for OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY not found in environment variables")


def _generate_script_internal(content: str, target_learner: str, word_limit: int = 500) -> str:
    """Internal script generation without validation - used by regeneration process."""
    if not OPENAI_API_KEY:
        return "Error: OpenAI API key not found. Please check your .env file."
    
    try:
        # Improved system prompt that avoids AI writing patterns while ensuring natural conversation
        system_prompt = (
            f"Generate a robotics-focused discussion (exactly {word_limit} words) between two specialists with clear, different voices:\n\n"
            "SPECIALIST 1 (Male VOICE1): Systems expert who explains how robots work using clear, step-by-step explanations. Focuses on basic principles and how parts work together. Uses simple words and short sentences.\n\n"
            "SPECIALIST 2 (Male VOICE2): Applications expert who asks questions and shows how robots are used in real life. Gives examples that middle school students (ages 11-14) would understand and find interesting.\n\n"
            "Conversation structure:\n"
            f"- Start with a short greeting and topic introduction ({int(word_limit*0.1)}-{int(word_limit*0.12)} words)\n"
            f"- Explore 2-3 main ideas about robots through back-and-forth talking ({int(word_limit*0.76)}-{int(word_limit*0.84)} words):\n"
            "  * Show both experts adding to each other's ideas\n"
            "  * Include one small disagreement where one gently corrects the other\n"
            "  * Mix different types of questions (asking for clearer explanations, challenging ideas, connecting topics)\n"
            "  * Sometimes use short 1-2 sentence responses before going deeper\n"
            f"- End with both sharing final thoughts ({int(word_limit*0.1)}-{int(word_limit*0.12)} words)\n\n"
            f"Technical level: Keep explanations at 5th-6th grade reading level but still accurate.\n\n"
            "Important requirements:\n"
            "- Label speakers as 'Specialist 1:' and 'Specialist 2:' every time they speak\n"
            "- Change how they talk to each other throughout the conversation:\n"
            "  * Sometimes have Specialist 2 build on an idea instead of questioning it\n"
            "  * Let either specialist sometimes show surprise or take time to think\n"
            "  * Include natural talk elements like quick agreements (\"Exactly.\") or thinking moments (\"Hmm, that's interesting...\")\n"
            "- Use [pause] and [emphasis] markers only when really needed\n"
            f"- Keep to about {word_limit} words total\n"
            "- Don't use podcast intros/outros or mention social media\n"
            "- Use examples that connect to what middle school students know\n"
            "- Focus on clear explanations with simple words\n"
            "- DO use helpful comparisons (\"A robot sensor works like your eyes\")\n"
            "- Avoid words like \"powerful,\" \"advanced,\" \"master,\" \"revolutionize\"\n"
            "- Don't use phrases like \"in today's digital age\"\n"
            "- Skip formal transitions like \"furthermore\" or \"moreover\"\n"
            "- Use simple language throughout"
        )
        
        # Call OpenAI API
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4.1",  # Using the latest model
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                "temperature": 0.7,
                "max_tokens": 4000
            }
        )
        
        if response.status_code == 200:
            script = response.json()["choices"][0]["message"]["content"]
            logger.info("Script generated successfully")
            return script
        else:
            error_msg = f"API Error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return f"Error generating script: {error_msg}"
            
    except Exception as e:
        error_msg = f"Error generating script: {str(e)}"
        logger.error(error_msg)
        return error_msg


def validate_script(script: str) -> tuple:
    """Validate the script for AI pattern detection (removed word count validation)."""
    # Count words for informational purposes only
    words = re.findall(r'\b\w+\b', script)
    word_count = len(words)
    logger.info(f"Script word count: {word_count} (word count validation disabled)")
    
    # Check dialogue variety
    specialist1_lines = re.findall(r'Specialist 1:[^\n]+', script, re.IGNORECASE)
    specialist2_lines = re.findall(r'Specialist 2:[^\n]+', script, re.IGNORECASE)
    
    # Check for variety in specialist 2's contributions (not just questions)
    if len(specialist2_lines) > 3:
        question_count = sum(1 for line in specialist2_lines if '?' in line)
        if question_count / len(specialist2_lines) > 0.8:  # 80% or more are questions
            return False, "Specialist 2 relies too heavily on questions; needs more varied contributions"
    
    # AI pattern detection has been disabled per user request
    return True, "Script validation passed"


def _regenerate_if_needed(script: str, content: str, target_learner: str, word_limit: int = 500, max_attempts=3) -> str:
    """Regenerate script if validation fails, with max attempts."""
    attempt = 1
    current_script = script
    
    while attempt <= max_attempts:
        valid, message = validate_script(current_script)
        if valid:
            logger.info(f"Script validation passed after {attempt} attempts")
            return current_script
        
        logger.warning(f"Script validation failed (attempt {attempt}/{max_attempts}): {message}")
        
        # Add additional feedback to the system prompt based on validation failure
        additional_feedback = ""
        if "relies too heavily on questions" in message.lower():
            additional_feedback = "Have Specialist 2 make more statements and observations, not just questions. They should contribute expertise, not just prompt Specialist 1."
        elif "AI pattern" in message:
            additional_feedback = "Strictly avoid AI writing clichés mentioned in language restrictions: avoid power terms, digital framing, academic inflation, and filler transitions."
        else:
            additional_feedback = message  # Use the full validation message
        
        # Generate new script with feedback using the internal method directly
        if attempt < max_attempts:
            modified_content = content + "\n\nIMPORTANT FEEDBACK: " + additional_feedback
            attempt += 1
            # Use internal method to avoid recursion
            current_script = _generate_script_internal(modified_content, target_learner, word_limit)
            
            # If generation failed, exit the loop
            if current_script.startswith("Error"):
                logger.error(f"Script regeneration failed on attempt {attempt}: {current_script}")
                break
        else:
            logger.error(f"Failed to generate valid script after {max_attempts} attempts")
            # Return the best script we have, with a warning prepended
            return f"// Note: This script may not meet all quality guidelines. Please review carefully.\n\n{current_script}"
    
    return current_script


def generate_script(content: str, target_learner: str, word_limit: int = 500) -> str:
    """Generate podcast script using OpenAI API with optimized prompt."""
    # Generate the script using the internal method
    script = _generate_script_internal(content, target_learner, word_limit)
    
    # Skip validation if there was an error
    if script.startswith("Error"):
        return script
    
    # Validate and regenerate if needed
    valid, message = validate_script(script)
    if not valid:
        logger.warning(f"Script validation failed: {message}")
        # Use regeneration
        script = _regenerate_if_needed(script, content, target_learner, word_limit)
    
    return script
