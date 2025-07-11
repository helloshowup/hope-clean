#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fitness script generation module for fitness instructor voiceover generator.

Handles the creation of fitness instruction scripts using OpenAI API and script validation.
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

# Load .env file from the root directory
env_path = os.path.join(root_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    
logger = logging.getLogger('fitness_instructor_voiceover')

# Check for OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY not found in environment variables")


def _generate_fitness_script_internal(content: str, target_audience: str, word_limit: int = 500) -> str:
    """Internal script generation without validation - used by regeneration process."""
    if not OPENAI_API_KEY:
        return "Error: OpenAI API key not found. Please check your .env file."
    
    try:
        # Fitness instructor specialized system prompt
        system_prompt = (
            f"Generate a fitness instruction script (exactly {word_limit} words) with a single instructor voice for guiding ONE specific exercise:\n\n"
            "FITNESS INSTRUCTOR (Male VOICE1): An enthusiastic, motivating fitness coach (using the Andrew voice dragon) who clearly explains exercise techniques, benefits, and safety considerations. Uses an encouraging tone with clear instructions. Mixes technical knowledge with approachable explanations.\n\n"
            f"Script structure:\n"
            f"- Welcome & Setup ({int(word_limit*0.1)}-{int(word_limit*0.15)} words):\n"
            "  * Brief welcome and introduction to the specific exercise\n"
            "  * Explain benefits and target muscles\n"
            "  * Outline safety considerations\n"
            f"- Guided Repetition Segment ({int(word_limit*0.75)}-{int(word_limit*0.8)} words):\n"
            "  * Announce the exercise name clearly (e.g., 'Today we'll do Wall Push-ups')\n"
            "  * Describe starting position in detail\n"
            "  * Lead through 8-10 repetitions using a count + cue pattern\n"
            "  * Format repetitions as: 'One - [specific form cue] [pause] Two - [another cue] [pause]...'\n"
            "  * Include a longer pause after the final repetition\n"
            "  * Include a [emphasis]Success check[/emphasis] sentence after initial instructions\n"
            "  * Offer a modification option introduced with 'Too easy?...' or 'Need a challenge?...'\n"
            f"- Wrap-up & Success Check ({int(word_limit*0.1)}-{int(word_limit*0.15)} words):\n"
            "  * Summarize benefits of the exercise\n"
            "  * Provide encouragement on progress\n"
            "  * Suggest frequency or integration into routine\n\n"
            f"Technical level: Keep explanations at a level appropriate for general fitness enthusiasts, but still accurate.\n\n"
            "Important requirements:\n"
            "- Label the speaker as 'Instructor:' at the beginning of each new instruction block\n"
            "- Use natural instructional language that works well in audio format\n"
            "- Include [pause] markers (without specifying milliseconds) for exercise transitions and between repetitions\n"
            "- Use a longer [pause] (approximately 3 seconds) after the final repetition before wrap-up\n"
            "- Use [emphasis] markers for important form cues, safety points, and success checks\n"
            f"- Keep to about {word_limit} words total\n"
            "- Focus on clear, actionable instructions for a single exercise\n"
            "- Use encouraging language that motivates without being overly intense\n"
            "- Include specific form cues (e.g., 'Keep your core engaged' or 'Shoulders away from ears')\n"
            "- Address common form mistakes and how to correct them\n"
            "- Do NOT imply the instructor is physically present or watching the learner in real time (e.g., no 'I see you', 'nice form!')\n"
            "- Use simple, direct language\n"
            "- Avoid overused fitness clichés like 'No pain, no gain'\n"
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
            logger.info("Fitness instruction script generated successfully")
            return script
        else:
            error_msg = f"API Error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return f"Error generating fitness script: {error_msg}"
            
    except Exception as e:
        error_msg = f"Error generating fitness script: {str(e)}"
        logger.error(error_msg)
        return error_msg


def validate_fitness_script(script: str) -> tuple:
    """Validate the fitness instruction script."""
    # Count words for informational purposes
    words = re.findall(r'\b\w+\b', script)
    word_count = len(words)
    logger.info(f"Fitness script word count: {word_count}")
    
    # Check for instructor labels
    instructor_blocks = re.findall(r'Instructor:', script, re.IGNORECASE)
    if len(instructor_blocks) < 3:  # At least opening, main content, and closing
        return False, "Script needs more clearly labeled instruction blocks"
    
    # Check for exercise instructions
    exercise_cues = ['position', 'form', 'breathe', 'engage', 'hold', 'repeat', 'seconds', 'sets', 'reps']
    cues_found = sum(1 for cue in exercise_cues if cue.lower() in script.lower())
    if cues_found < 4:  # At least 4 different exercise cues
        return False, "Script needs more detailed exercise instructions and cues"
    
    return True, "Fitness script validation passed"


def _regenerate_fitness_script_if_needed(script: str, content: str, target_audience: str, word_limit: int = 500, max_attempts=3) -> str:
    """Regenerate fitness script if validation fails, with max attempts."""
    attempt = 1
    current_script = script
    
    while attempt <= max_attempts:
        valid, message = validate_fitness_script(current_script)
        if valid:
            logger.info(f"Fitness script validation passed after {attempt} attempts")
            return current_script
        
        logger.warning(f"Fitness script validation failed (attempt {attempt}/{max_attempts}): {message}")
        
        # Add additional feedback to the system prompt based on validation failure
        additional_feedback = ""
        if "more clearly labeled" in message.lower():
            additional_feedback = "Include more 'Instructor:' labels to clearly mark different sections of the workout."
        elif "more detailed exercise instructions" in message.lower():
            additional_feedback = "Include specific form cues, breathing instructions, and timing for each exercise."
        else:
            additional_feedback = message  # Use the full validation message
        
        # Generate new script with feedback using the internal method directly
        if attempt < max_attempts:
            modified_content = content + "\n\nIMPORTANT FEEDBACK: " + additional_feedback
            attempt += 1
            # Use internal method to avoid recursion
            current_script = _generate_fitness_script_internal(modified_content, target_audience, word_limit)
            
            # If generation failed, exit the loop
            if current_script.startswith("Error"):
                logger.error(f"Fitness script regeneration failed on attempt {attempt}: {current_script}")
                break
        else:
            logger.error(f"Failed to generate valid fitness script after {max_attempts} attempts")
            # Return the best script we have, with a warning prepended
            return f"// Note: This fitness script may not meet all quality guidelines. Please review carefully.\n\n{current_script}"
    
    return current_script


def generate_fitness_script(content: str, target_audience: str, word_limit: int = 500) -> str:
    """Generate fitness instruction script using OpenAI API with optimized prompt."""
    # Generate the script using the internal method
    script = _generate_fitness_script_internal(content, target_audience, word_limit)
    
    # Skip validation if there was an error
    if script.startswith("Error"):
        return script
    
    # Validate and regenerate if needed
    valid, message = validate_fitness_script(script)
    if not valid:
        logger.warning(f"Fitness script validation failed: {message}")
        # Use regeneration
        script = _regenerate_fitness_script_if_needed(script, content, target_audience, word_limit)
    
    return script
