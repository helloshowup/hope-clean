"""Markdown to HTML Converter Module for ClaudeAIPanel - Compatibility Layer"""

# Import the relocated MarkdownConverterPanel and utility functions
from .markdown_converter_panel import (
    LoggingHandler,
    markdown_to_html,
    apply_learning_objectives_styling,
    extract_special_sections,
    create_stop_reflect_html,
    create_key_takeaways_html,
    MarkdownConverterPanel
)

# Import the relocated FileRenamerPanel
from .file_renamer_panel import FileRenamerPanel

# This maintains compatibility with existing code that imports from this module
__all__ = [
    'LoggingHandler',
    'markdown_to_html',
    'apply_learning_objectives_styling',
    'extract_special_sections',
    'create_stop_reflect_html',
    'create_key_takeaways_html',
    'MarkdownConverterPanel',
    'FileRenamerPanel'
]
