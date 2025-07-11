"""
Core module for the ShowupSquared system.

This package contains essential utilities, configuration, and helper functions
that form the foundation of the ShowupSquared workflow system.
"""
# Set up basic logging first - we'll configure it properly later
import logging
from showup_editor_ui.claude_panel.path_utils import get_project_root
core_logger = logging.getLogger("core")
core_logger.setLevel(logging.INFO)

# Define the public API
# Define the public API
__all__ = []

# First, import basic configuration with no dependencies
from .config import (
    BASE_DIR,
    DIRS,
    AVAILABLE_COURSES,
    ensure_directories,
    setup_logging,
    load_user_settings,
    get_course_directory,
    get_course_content_paths
)

# Add to public API
__all__.extend([
    'BASE_DIR',
    'DIRS',
    'AVAILABLE_COURSES',
    'ensure_directories',
    'setup_logging',
    'load_user_settings',
    'get_course_directory',
    'get_course_content_paths',
])

# Import file utilities from file_utils (the dedicated module)
from .file_utils import (
    safe_read_file,
    safe_write_file,
    ensure_directory_exists,
    ensure_directory,  # Alias for compatibility
    archive_file,
    load_json_file,
    save_json_file,
    read_json_file,
    write_json_file,
    validate_csv_basics,
    check_course_content_exists,
    list_files,
    file_exists,
    directory_exists
)

# Add to public API
__all__.extend([
    'safe_read_file',
    'safe_write_file',
    'ensure_directory_exists',
    'ensure_directory',  # Alias for compatibility
    'archive_file',
    'load_json_file',
    'save_json_file',
    'read_json_file',
    'write_json_file',
    'validate_csv_basics',
    'check_course_content_exists',
    'list_files',
    'file_exists',
    'directory_exists'
])

# Import API utilities and client functions
from .api_utils import (
    prepare_api_params,
    test_api_connection,
    with_error_handling,
    calculate_cost,
    extract_response_content,
    get_cached_or_generate
)

# Add to public API
__all__.extend([
    'prepare_api_params',
    'test_api_connection',
    'with_error_handling',
    'calculate_cost',
    'extract_response_content',
    'get_cached_or_generate'
])

# Import API client functions
try:
    from .api_client import (
        SmartModelSelector,
        ApiClient,
        get_api_client,
        generate_with_claude,
        generate_with_llm
    )
    
    # Add to public API
    __all__.extend([
        'SmartModelSelector',
        'ApiClient',
        'get_api_client',
        'generate_with_claude',
        'generate_with_llm'
    ])
except ImportError as e:
    core_logger.warning(f"Could not import API client functions: {e}")

# Try to import HTML utilities
try:
    from showup_core.html_converter import (
        process_html_metadata,
        create_html_base,
        process_html_section,
        convert_markdown_to_html,
        convert_lesson_to_html,
        convert_module_to_html,
        generate_content_html,
        generate_enhancement_comparison_report,
        HTMLConverter
    )
    
    # Add to public API
    __all__.extend([
        'process_html_metadata',
        'create_html_base',
        'process_html_section',
        'convert_markdown_to_html',
        'convert_lesson_to_html',
        'convert_module_to_html',
        'generate_content_html',
        'generate_enhancement_comparison_report',
        'HTMLConverter'
    ])
except ImportError as e:
    core_logger.warning(f"Could not import HTML converter modules: {e}")

# Try to import content enhancer modules
try:
    from .content_enhancer import (
        QualityAnalyzer,
        AIDetector,
        ContentEnhancer,
        extract_context_element,
        summarize_content,
        enhance_content_section,
        build_context_from_course_content,
        analyze_content_quality
    )
    
    # Add to public API
    __all__.extend([
        'QualityAnalyzer',
        'AIDetector',
        'ContentEnhancer',
        'extract_context_element',
        'summarize_content',
        'enhance_content_section',
        'build_context_from_course_content',
        'analyze_content_quality'
    ])
except ImportError as e:
    core_logger.warning(f"Could not import content enhancer modules: {e}")

# Import state manager
try:
    from .state_manager import (
        get_work_state,
        save_work_state,
        update_module_state,
        update_lesson_state,
        is_work_needed,
        format_timestamp,
        calculate_file_hash
    )
    
    # Add to public API
    __all__.extend([
        'get_work_state',
        'save_work_state',
        'update_module_state',
        'update_lesson_state',
        'is_work_needed',
        'format_timestamp',
        'calculate_file_hash'
    ])
except ImportError as e:
    core_logger.warning(f"Could not import state manager modules: {e}")

# Import utility functions
try:
    from .utils import (
        check_dependencies,
        safe_convert_to_int
    )
    
    # Add to public API
    __all__.extend([
        'check_dependencies',
        'safe_convert_to_int'
    ])
except ImportError as e:
    core_logger.warning(f"Could not import utility functions: {e}")

# Import CSV parser utilities
try:
    from .csv_parser import (
        extract_lessons_and_steps_from_csv,
        extract_lessons_from_csv,
        ensure_ai_phrases_file
    )
    
    # Add to public API
    __all__.extend([
        'extract_lessons_and_steps_from_csv',
        'extract_lessons_from_csv',
        'ensure_ai_phrases_file'
    ])
except ImportError as e:
    core_logger.warning(f"Could not import CSV parser utilities: {e}")

# Try to import ApiClient and related classes
try:
    from .api_client import ApiClient, SmartModelSelector, PromptTemplateSystem, get_api_client
    
    # Add to public API
    __all__.extend([
        'ApiClient',
        'SmartModelSelector',
        'PromptTemplateSystem',
        'get_api_client'
    ])
except ImportError as e:
    core_logger.warning(f"Could not import ApiClient and related classes: {e}")

# Initialize the core module
# Add a handler if not already present
if not core_logger.handlers:
    # Create file handler
    import os
    logs_dir = os.path.join(str(get_project_root()), 'showup-core', 'data', 'logs', 'workflow2')
    os.makedirs(logs_dir, exist_ok=True)
    
    file_handler = logging.FileHandler(os.path.join(logs_dir, "core.log"))
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    core_logger.addHandler(file_handler)
    
    # Prevent propagation to avoid duplicate logging
    core_logger.propagate = False

core_logger.info("Initializing ShowupSquared core module")

# Run initial directory setup
ensure_directories()