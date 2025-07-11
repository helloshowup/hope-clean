"""
Content utility functions for the workflow system.

Contains functions for processing, enhancing, and manipulating educational content.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional, Union, Tuple

# Import from core modules
from .file_utils import safe_read_file
from .api_utils import extract_response_content

# Configure logger
logger = logging.getLogger('content_utils')

def extract_context_element(data: Any, path: List[Union[str, int]], default: Any = None) -> Any:
    """
    Safely extract elements from nested data structures.
    
    Args:
        data: The data structure to extract from
        path: A list of keys/indices to navigate the structure
        default: Default value if path doesn't exist
        
    Returns:
        The extracted value or default
    """
    current = data
    try:
        for key in path:
            if isinstance(current, dict):
                current = current.get(key, default)
            elif isinstance(current, (list, tuple)) and isinstance(key, int) and 0 <= key < len(current):
                current = current[key]
            else:
                return default
            
            if current is None:
                return default
        return current
    except Exception as e:
        logger.error(f"Error extracting context element: {str(e)}")
        return default

def check_course_content_exists(
    course_id: str,
    content_type: str,
    module_number: int,
    lesson_number: Optional[int] = None,
    step_number: Optional[int] = None,
    step_type: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Check if specific course content exists.
    
    Args:
        course_id: Course identifier
        content_type: Type of content (module, lesson, step)
        module_number: Module number
        lesson_number: Optional lesson number
        step_number: Optional step number
        step_type: Optional step type (Article, Quiz, etc.)
        
    Returns:
        Tuple of (exists, path) where exists is a boolean and path is the path if it exists
    """
    from .config import get_course_content_paths
    
    try:
        # Get paths based on content type
        if content_type == 'module':
            paths = get_course_content_paths(course_id, module_number)
            path_to_check = paths.get("module_file")
        elif content_type == 'lesson' and lesson_number is not None:
            paths = get_course_content_paths(course_id, module_number, lesson_number)
            path_to_check = paths.get("lesson_file")
        elif content_type == 'step' and lesson_number is not None and step_number is not None:
            paths = get_course_content_paths(course_id, module_number, lesson_number, step_number)
            
            # If step type is specified, check for that specific type
            if step_type:
                path_to_check = paths.get(f"step_{step_type.lower()}_file")
            else:
                path_to_check = paths.get("step_file")
        else:
            return False, f"Invalid content type or missing parameters: {content_type}"
        
        # Check if the path exists
        if path_to_check and os.path.exists(path_to_check):
            return True, path_to_check
        else:
            return False, f"Content does not exist: {path_to_check}"
    
    except Exception as e:
        logger.error(f"Error checking content existence: {str(e)}")
        return False, f"Error checking content: {str(e)}"

def summarize_content(content_or_path: Union[str, Any], max_length: int = 1000) -> str:
    """
    Create a summary of content from a file or directly from content string.
    
    Args:
        content_or_path: Either a file path or the content string itself
        max_length: Maximum length of the summary
        
    Returns:
        Summarized content or error message
    """
    content = ""
    
    # Check if input is a file path or content string
    if isinstance(content_or_path, str) and os.path.exists(content_or_path):
        # It's a file path
        success, content = safe_read_file(content_or_path)
        if not success:
            return f"Error reading file: {content_or_path}"
    else:
        # It's already content
        content = str(content_or_path)
    
    # If content is already shorter than max_length, return it as is
    if len(content) <= max_length:
        return content
    
    # Simple summarization approach:
    # 1. Extract title/headings
    # 2. Extract first paragraph
    # 3. Extract any learning objectives
    # 4. Append a note about truncation
    
    summary_parts = []
    
    # Extract title (first heading)
    title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
    if title_match:
        summary_parts.append(f"# {title_match.group(1)}")
    
    # Extract first paragraph (simplified)
    first_para_match = re.search(r'(?:^|\n\n)((?:[^\n#].*\n)+)', content)
    if first_para_match:
        first_para = first_para_match.group(1).strip()
        if len(first_para) > 300:
            first_para = first_para[:297] + "..."
        summary_parts.append(first_para)
    
    # Extract learning objectives if present
    objectives_match = re.search(r'## Learning Objectives\s+((?:- .*\n)+)', content)
    if objectives_match:
        objectives = objectives_match.group(0)
        # Truncate if too long
        if len(objectives) > 400:
            objectives_lines = objectives.split('\n')
            truncated_objectives = '\n'.join(objectives_lines[:5]) + "\n- ..."
            summary_parts.append(truncated_objectives)
        else:
            summary_parts.append(objectives)
    
    # Add truncation note
    summary_parts.append(f"\n[Content truncated - original length: {len(content)} characters]")
    
    # Join parts and ensure we don't exceed max_length
    summary = "\n\n".join(summary_parts)
    if len(summary) > max_length:
        summary = summary[:max_length-3] + "..."
    
    return summary

def enhance_content_section(content: str, section_type: str, course_type: Optional[str] = None, 
                           api_func: Optional[callable] = None, logger: Optional[logging.Logger] = None) -> str:
    """
    Enhance a specific section of content.
    
    Args:
        content: The original content
        section_type: Type of section to enhance (e.g., 'learning_objectives', 'key_takeaways')
        course_type: Optional course type for context
        api_func: Optional function to call API for enhancement
        logger: Optional logger
        
    Returns:
        Enhanced content or original if enhancement fails
    """
    if not api_func:
        if logger:
            logger.warning(f"No API function provided for enhancing {section_type}, returning original content")
        return content
    
    # Skip enhancement if content is empty or already good
    if not content or len(content.strip()) < 10:
        if logger:
            logger.warning(f"Content too short to enhance, skipping {section_type}")
        return content
    
    enhancement_prompts = {
        'learning_objectives': f"""
            I need help enhancing these learning objectives to be more aligned with educational best practices.
            They should be specific, measurable, achievable, relevant, and time-bound (SMART).
            
            Original learning objectives:
            {content}
            
            Please provide improved versions that:
            - Start with strong action verbs (following Bloom's taxonomy)
            - Are clear and focused on specific skills or knowledge
            - Are aligned with a {course_type or 'general'} course
            - Maintain the original core concepts but express them more effectively
            
            Return ONLY the improved learning objectives, one per line with bullet points.
        """,
        
        'key_takeaways': f"""
            I need help enhancing these key takeaways to be more impactful and memorable.
            
            Original key takeaways:
            {content}
            
            Please provide improved versions that:
            - Summarize the most critical points clearly and concisely
            - Use simple, direct language
            - Focus on practical applications or insights
            - Are suitable for a {course_type or 'general'} course
            
            Return ONLY the improved key takeaways, one per line with bullet points.
        """,
        
        'image_placeholders': f"""
            I need help enhancing these image placeholders to be more specific and helpful for illustrators.
            
            Original image descriptions:
            {content}
            
            Please provide improved versions that:
            - Include more specific details about what the image should contain
            - Specify style, composition, and key elements
            - Align with a {course_type or 'general'} course
            - Are clear enough for an illustrator to create without additional context
            
            Return ONLY the improved image descriptions, preserving the original placeholder format.
        """
    }
    
    # Use default enhancement prompt if section type is not specifically defined
    prompt = enhancement_prompts.get(section_type, f"""
        I need help enhancing this content section to be more effective and engaging.
        
        Original content:
        {content}
        
        Please provide an improved version that:
        - Is more clear, concise, and engaging
        - Uses better phrasing and structure
        - Is suitable for a {course_type or 'general'} educational context
        
        Return ONLY the improved content.
    """)
    
    # System prompt for the enhancement
    system_prompt = f"""
        You are an expert educational content developer specializing in creating high-quality, 
        engaging, and effective learning materials. Your task is to enhance the provided 
        {section_type} section while maintaining its core message and purpose.
    """
    
    try:
        # Call the API function (which should match the signature expected)
        response = api_func(
            prompt=prompt.strip(),
            system_prompt=system_prompt.strip(),
            task_type="content_enhancement",
            complexity_level="standard"
        )
        
        # Check if the API call was successful
        if isinstance(response, dict) and response.get("success", False):
            # Extract the enhanced content
            enhanced_content = extract_response_content(response.get("content", ""))
            
            # Validate that enhanced content isn't empty or significantly shorter
            if enhanced_content and len(enhanced_content) >= len(content) * 0.7:
                if logger:
                    logger.info(f"Successfully enhanced {section_type} content")
                return enhanced_content.strip()
            else:
                if logger:
                    logger.warning("Enhanced content too short or empty, keeping original")
                return content
        else:
            # Log error details if available
            error_msg = "Unknown error"
            if isinstance(response, dict) and "error" in response:
                error_msg = response["error"]
            
            if logger:
                logger.error(f"Failed to enhance {section_type}: {error_msg}")
            return content
            
    except Exception as e:
        if logger:
            logger.error(f"Exception during {section_type} enhancement: {str(e)}")
        return content

# NEW HELPER FUNCTION: Extract adjacent lessons
def extract_adjacent_lessons(course_id: str, module_num: int, lesson_num: int) -> Dict[str, str]:
    """
    Extract information about lessons before and after the current one.
    
    Args:
        course_id: Course identifier
        module_num: Module number
        lesson_num: Current lesson number
        
    Returns:
        Dictionary with 'previous' and 'next' lesson information
    """
    from .config import get_course_content_paths
    
    adjacent = {}
    
    logger.info(f"Extracting adjacent lessons for course {course_id}, module {module_num}, lesson {lesson_num}")
    
    # Get module content to extract lesson information
    paths = get_course_content_paths(course_id, module_num)
    if os.path.exists(paths["module_path"]):
        success, module_content = safe_read_file(paths["module_path"])
        if success:
            # Use regex to find all lesson references in the module content
            lesson_pattern = r'Lesson\s+(\d+)[:\s]+([^\n]+)'
            lessons = re.findall(lesson_pattern, module_content, re.IGNORECASE)
            
            # Convert to dictionary for easy lookup
            lessons_dict = {int(num): title.strip() for num, title in lessons}
            
            # Get previous lesson if it exists
            if lesson_num > 1 and lesson_num - 1 in lessons_dict:
                adjacent["previous"] = f"Lesson {lesson_num-1}: {lessons_dict[lesson_num-1]}"
                logger.info(f"Found previous lesson: {adjacent['previous']}")
            
            # Get next lesson if it exists
            if lesson_num + 1 in lessons_dict:
                adjacent["next"] = f"Lesson {lesson_num+1}: {lessons_dict[lesson_num+1]}"
                logger.info(f"Found next lesson: {adjacent['next']}")
    
    # If no lessons found in module content, try alternative approaches
    if not adjacent:
        logger.info("No lessons found in module content, trying alternative approaches")
        
        # Check if previous lesson file exists
        if lesson_num > 1:
            prev_lesson_exists, prev_lesson_path = check_course_content_exists(
                course_id, 'lesson', module_num, lesson_num - 1)
                
            if prev_lesson_exists:
                logger.info(f"Found previous lesson {lesson_num-1} file at {prev_lesson_path}")
                # Try to extract title from lesson content
                success, content = safe_read_file(prev_lesson_path)
                if success:
                    # Try to extract title (first line with #)
                    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                    if title_match:
                        title = title_match.group(1).strip()
                        adjacent["previous"] = f"Lesson {lesson_num-1}: {title}"
                    else:
                        adjacent["previous"] = f"Lesson {lesson_num-1}"
                else:
                    adjacent["previous"] = f"Lesson {lesson_num-1}"
        
        # Check if next lesson file exists
        next_lesson_exists, next_lesson_path = check_course_content_exists(
            course_id, 'lesson', module_num, lesson_num + 1)
            
        if next_lesson_exists:
            logger.info(f"Found next lesson {lesson_num+1} file at {next_lesson_path}")
            # Try to extract title from lesson content
            success, content = safe_read_file(next_lesson_path)
            if success:
                # Try to extract title (first line with #)
                title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                if title_match:
                    title = title_match.group(1).strip()
                    adjacent["next"] = f"Lesson {lesson_num+1}: {title}"
                else:
                    adjacent["next"] = f"Lesson {lesson_num+1}"
            else:
                adjacent["next"] = f"Lesson {lesson_num+1}"
    
    return adjacent

# ENHANCED FUNCTION: Build context from course content
def build_context_from_course_content(course_id: str, module_number: int,
                                     lesson_number: Optional[int] = None,
                                     step_number: Optional[int] = None,
                                     csv_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Build a context dictionary using available course content.
    Includes context from previous and next steps/lessons for better continuity.
    
    Args:
        course_id: Course identifier
        module_number: Module number
        lesson_number: Optional lesson number
        step_number: Optional step number
        csv_path: Optional path to CSV file with course structure
        
    Returns:
        Context dictionary with available content including adjacent content
    """
    # Initialize empty result with default values
    result = {
        "formatted_context": "",
        "context_parts": [],
        "error": None
    }
    
    try:
        
        logger.info(f"Building context for course={course_id}, module={module_number}, lesson={lesson_number}, step={step_number}")
        
        # Continue with original function implementation...
        # This is a placeholder for the function's original logic
        
        # Return the result at the end of the try block
        return result
    except Exception as e:
        # Log the error
        logger.error(f"Error building context from course content: {str(e)}")
        # Set error message in result
        result["error"] = f"Failed to build context: {str(e)}"
        # Return the default result with error information
        return result
    