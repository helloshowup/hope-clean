"""
Configuration module for the workflow system.

Contains directory structures, course definitions, and other configuration constants
used throughout the application.
"""

import os
import logging
from showup_editor_ui.claude_panel.path_utils import get_project_root

# Calculate BASE_DIR relative to this module's location
# Since this file is in ShowupSquaredV3/core, we need to go up one level to reach the project root
BASE_DIR = os.path.join(str(get_project_root()), "showup-core")

# Templates directories used throughout the configuration
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
INPUT_TEMPLATES_DIR = os.path.join(BASE_DIR, "data", "input", "templates")

# Central location for learner profiles
LEARNER_PROFILES_DIR = "data/input/learner_profiles"

# Define available courses
AVAILABLE_COURSES = {
    'photography': {
        'name': 'Photography Foundation Unit',
        'client': 'Further Learning',
        'level': 'Pearsons Higher National Certificate'
    },
    'prompt_engineering': {
        'name': 'Prompt Engineering',
        'client': 'Excel Education',
        'level': 'k-12 High School'
    },
    'interior_design': {
        'name': 'Interior Design Foundation Unit',
        'client': 'Further Learning',
        'level': 'Pearsons Higher National Certificate'
    },
    'graphic_design': {
        'name': 'Graphic Design Diploma',
        'client': 'Further Learning',
        'level': 'Pearsons Higher National Diploma'
    },
    'robotics': {
        'name': 'Intro to Robotics',
        'client': 'Excel Education',
        'level': 'k-12 Middle School'
    },
    'physical_education': {
        'name': 'Physical Education',
        'client': 'Excel Education',
        'level': 'k-12 Middle School'
    }
}

# Directory structure - defined only once
DIRS = {
    'input': {
        'csv': os.path.join(BASE_DIR, 'data/input/csv'),
        'learner_profiles': os.path.join(BASE_DIR, LEARNER_PROFILES_DIR),  # Use central constant
        'templates': TEMPLATES_DIR,  # Use absolute path
    },
    'temp': {
        'outlines': os.path.join(BASE_DIR, 'data/temp/outlines'),
    },
    'library': {  # New top-level directory for the library
        'root': os.path.join(BASE_DIR, 'library'),
    },
    'output': {  # Maintain this for backward compatibility
        'lessons': os.path.join(BASE_DIR, 'data/output/lessons'),
        'steps': os.path.join(BASE_DIR, 'data/output/steps'),
        'modules': os.path.join(BASE_DIR, 'data/output/modules'),
        'html': os.path.join(BASE_DIR, 'data/output/html'),  # New directory for HTML output
    },
    'logs': {
        'root': os.path.join(BASE_DIR, 'data/logs'),  # Add root key for logs directory
        'workflow': os.path.join(BASE_DIR, 'data/logs/workflow2'),
    },
    'templates': {
        'steps': os.path.join(BASE_DIR, 'config/templates/steps'),  # Preserve existing entry
        'root': TEMPLATES_DIR,          # Main templates directory
        'input': INPUT_TEMPLATES_DIR,   # Input templates directory
        'robotics': os.path.join(INPUT_TEMPLATES_DIR, 'excel-lesson-template.md'),
        'article': os.path.join(INPUT_TEMPLATES_DIR, 'article_template.md'),
        'workshop': os.path.join(INPUT_TEMPLATES_DIR, 'workshop_template.md'),
        'video': os.path.join(INPUT_TEMPLATES_DIR, 'video_script_template.md'),
        'quiz': os.path.join(INPUT_TEMPLATES_DIR, 'Quiz.md'),
        'downloadable': os.path.join(INPUT_TEMPLATES_DIR, 'Downloadable.md'),
        'content': os.path.join(INPUT_TEMPLATES_DIR, 'Content.md'),
        'activity': os.path.join(INPUT_TEMPLATES_DIR, 'Activity.md'),
        'resource_collection': os.path.join(INPUT_TEMPLATES_DIR, 'resource_collection_template.md'),
        'case_study': os.path.join(INPUT_TEMPLATES_DIR, 'case_study_template.md'),
        'Excel_lesson': os.path.join(INPUT_TEMPLATES_DIR, 'excel-lesson-template.md'),
        'infographic': os.path.join(INPUT_TEMPLATES_DIR, 'infographic-content-template.md'),
        'game_design': os.path.join(INPUT_TEMPLATES_DIR, 'game-template.md'),
    },
    'cache': {
        'root': os.path.join(BASE_DIR, 'data/cache'),  # Add root key for cache directory
        'summaries': os.path.join(BASE_DIR, 'data/cache/summaries'),
        'examples': os.path.join(BASE_DIR, 'data/cache/examples'),  # Add this line
    },
    'archive': {  # Explicit directory for archived content
        'root': os.path.join(BASE_DIR, 'data/archive'),
    },
    'settings': {  # New directory for user settings
        'root': os.path.join(BASE_DIR, 'data/settings'),
    },
    'data': {  # Add missing data key for PromptManager
        'root': os.path.join(BASE_DIR, 'data'),
        'settings': os.path.join(BASE_DIR, 'data/settings'),
    }
}

def validate_dirs_structure():
    """
    Validate the DIRS structure to ensure all expected 'root' keys exist.
    Logs warnings for missing keys but doesn't halt execution.
    """
    logger = logging.getLogger("config")
    
    # Define directories that should have a 'root' key
    root_required_dirs = ['library', 'templates', 'cache', 'archive', 'settings']
    
    for dir_name in root_required_dirs:
        if dir_name not in DIRS:
            logger.warning(f"Missing '{dir_name}' in DIRS configuration")
        elif not isinstance(DIRS[dir_name], dict):
            logger.warning(f"DIRS['{dir_name}'] is not a dictionary as expected")
        elif 'root' not in DIRS[dir_name]:
            logger.warning(f"Directory '{dir_name}' missing 'root' key in DIRS")

def ensure_directories():
    """Create all required directories defined in DIRS."""
    # Get a logger for this function
    config_logger = logging.getLogger("config")
    
    # Ensure learner profiles directory exists
    learner_profiles_path = os.path.join(BASE_DIR, LEARNER_PROFILES_DIR)
    if not os.path.exists(learner_profiles_path):
        os.makedirs(learner_profiles_path, exist_ok=True)
        config_logger.info(f"Created learner profiles directory at {learner_profiles_path}")
    else:
        config_logger.debug(f"Learner profiles directory exists at {learner_profiles_path}")
    
    for category, paths in DIRS.items():
        for name, path in paths.items():
            # Only create directories for paths that don't have file extensions
            if not os.path.splitext(path)[1]:  # Check if path has no extension
                os.makedirs(path, exist_ok=True)
                config_logger.debug(f"Created directory: {path}")
            else:
                # For file paths, just make sure the parent directory exists
                os.makedirs(os.path.dirname(path), exist_ok=True)
                config_logger.debug(f"Ensured parent directory exists for: {path}")

def setup_logging(name="workflow", log_to_console=True):
    """Set up logging to file with optional console output."""
    # Create logs directory if needed
    os.makedirs(DIRS['logs']['workflow'], exist_ok=True)
    
    # Configure logging
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Check if logger already has handlers to prevent duplicates
    if not logger.handlers:
        # Add file handler
        file_handler = logging.FileHandler(os.path.join(DIRS['logs']['workflow'], f"{name}.log"))
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Add console handler if requested
        if log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(file_formatter)
            logger.addHandler(console_handler)
        
        # Disable propagation to prevent duplicate logging from parent loggers
        logger.propagate = False
        
        logger.info(f"Logging initialized with file output to: {DIRS['logs']['workflow']}/{name}.log")
    
    return logger

def load_user_settings():
    """Load user settings from the settings file."""
    # Get a logger for this function
    config_logger = logging.getLogger("config")
    
    settings_path = os.path.join(DIRS['data']['settings'], "user_preferences.json")
    settings = {}
    
    if os.path.exists(settings_path):
        try:
            import json
            with open(settings_path, "r") as f:
                settings = json.load(f)
            config_logger.info(f"Loading saved settings from: {settings_path}")
        except Exception as e:
            config_logger.error(f"Error loading settings: {str(e)}")
    else:
        config_logger.info(f"No settings file found at {settings_path}, using defaults")
    
    return settings

def get_course_directory(course_id, base_dir=None):
    """
    Get the directory path for a course.
    
    Args:
        course_id: Course identifier
        base_dir: Optional base directory (default: BASE_DIR)
        
    Returns:
        Path to the course directory
    """
    if course_id not in AVAILABLE_COURSES:
        print(f"Error: Unknown course ID: {course_id}")
        raise ValueError(f"Unknown course ID: {course_id}")
    
    # Use provided base directory or default
    library_root = DIRS['library']['root'] if base_dir is None else os.path.join(base_dir, 'library')
    
    course_name = AVAILABLE_COURSES[course_id]['name']
    course_dir = os.path.join(library_root, course_name)
    
    # Ensure directory exists
    os.makedirs(course_dir, exist_ok=True)
    
    return course_dir

def get_course_content_paths(course_id, module_num, lesson_num=None, step_num=None, base_dir=None):
    """
    Get paths for course content (module, lesson, step).
    
    Args:
        course_id: Course identifier
        module_num: Module number
        lesson_num: Optional lesson number
        step_num: Optional step number
        base_dir: Optional base directory (default: BASE_DIR)
        
    Returns:
        Dictionary of paths for course content
    """
    # Get course directory
    course_dir = get_course_directory(course_id, base_dir)
    
    # Standardize module directory name
    module_dir = os.path.join(course_dir, f"Module_{module_num}")
    
    # Create result dictionary
    paths = {
        'course_dir': course_dir,
        'module_dir': module_dir,
        'module_path': os.path.join(module_dir, "module_content.md"),
    }
    
    # Add lesson-specific paths if lesson_num is provided
    if lesson_num is not None:
        lesson_dir = os.path.join(module_dir, f"Lesson_{lesson_num}")
        lesson_path = os.path.join(lesson_dir, "lesson_content.md")
        
        paths.update({
            'lesson_dir': lesson_dir,
            'lesson_path': lesson_path,
        })
        
        # Add step-specific paths if step_num is provided
        if step_num is not None:
            step_path = os.path.join(lesson_dir, f"step_{step_num}.md")
            
            paths.update({
                'step_path': step_path,
            })
    
    return paths

# Run validation on module load
validate_dirs_structure()