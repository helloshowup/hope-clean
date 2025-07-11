"""
HTML utility functions for the workflow system.

Contains functions for converting markdown to HTML, applying themes,
and generating responsive educational content.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import json
from pathlib import Path

# Import from core modules
from .file_utils import safe_read_file, safe_write_file

# Configure logger
logger = logging.getLogger('html_utils')

class TemplateManager:
    """
    Manages HTML templates for educational content.
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the TemplateManager.
        
        Args:
            templates_dir: Optional directory path containing templates
        """
        self.logger = logger
        self.templates = {}
        self.templates_dir = templates_dir or os.path.join(os.getcwd(), "templates", "html")
        
        # Ensure templates directory exists
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Load default templates
        self._load_default_templates()
        
        # Load custom templates if template directory exists
        if os.path.exists(self.templates_dir):
            self._load_templates_from_directory()
    
    def _load_default_templates(self):
        """Load default built-in templates."""
        # Default lesson template
        self.templates["lesson"] = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{title}}</title>
            <style>
                {{css}}
            </style>
        </head>
        <body class="{{theme}}">
            <div class="container">
                <header>
                    <h1>{{title}}</h1>
                    <div class="metadata">
                        <span class="module">Module {{module_number}}</span>
                        <span class="lesson">Lesson {{lesson_number}}</span>
                    </div>
                </header>
                
                <main>
                    <div class="content">
                        {{content}}
                    </div>
                </main>
                
                <footer>
                    <div class="navigation">
                        {{#prev_lesson}}
                        <a href="{{prev_lesson}}" class="prev">← Previous Lesson</a>
                        {{/prev_lesson}}
                        
                        {{#next_lesson}}
                        <a href="{{next_lesson}}" class="next">Next Lesson →</a>
                        {{/next_lesson}}
                    </div>
                </footer>
            </div>
        </body>
        </html>
        """
        
        # Default module template
        self.templates["module"] = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{title}}</title>
            <style>
                {{css}}
            </style>
        </head>
        <body class="{{theme}}">
            <div class="container">
                <header>
                    <h1>{{title}}</h1>
                    <div class="metadata">
                        <span class="course">{{course_name}}</span>
                        <span class="module">Module {{module_number}}</span>
                    </div>
                </header>
                
                <main>
                    <div class="module-overview">
                        {{content}}
                    </div>
                    
                    <div class="lessons-list">
                        <h2>Lessons</h2>
                        <ul>
                            {{#lessons}}
                            <li><a href="{{url}}">{{title}}</a></li>
                            {{/lessons}}
                        </ul>
                    </div>
                </main>
                
                <footer>
                    <div class="navigation">
                        {{#prev_module}}
                        <a href="{{prev_module}}" class="prev">← Previous Module</a>
                        {{/prev_module}}
                        
                        {{#next_module}}
                        <a href="{{next_module}}" class="next">Next Module →</a>
                        {{/next_module}}
                    </div>
                </footer>
            </div>
        </body>
        </html>
        """
        
        # Default step template
        self.templates["step"] = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{title}}</title>
            <style>
                {{css}}
            </style>
        </head>
        <body class="{{theme}}">
            <div class="container">
                <header>
                    <h1>{{title}}</h1>
                    <div class="metadata">
                        <span class="module">Module {{module_number}}</span>
                        <span class="lesson">Lesson {{lesson_number}}</span>
                        <span class="step">Step {{step_number}}</span>
                    </div>
                </header>
                
                <main>
                    <div class="content">
                        {{content}}
                    </div>
                </main>
                
                <footer>
                    <div class="navigation">
                        {{#prev_step}}
                        <a href="{{prev_step}}" class="prev">← Previous Step</a>
                        {{/prev_step}}
                        
                        {{#next_step}}
                        <a href="{{next_step}}" class="next">Next Step →</a>
                        {{/next_step}}
                        
                        <a href="{{lesson_url}}" class="up">↑ Back to Lesson</a>
                    </div>
                </footer>
            </div>
        </body>
        </html>
        """
        
        self.logger.info("Loaded default templates")
    
    def _load_templates_from_directory(self):
        """Load templates from the templates directory."""
        try:
            # Find all HTML files in the templates directory
            template_files = [f for f in os.listdir(self.templates_dir) if f.endswith('.html')]
            
            for file_name in template_files:
                # Extract template name from filename (remove extension)
                template_name = os.path.splitext(file_name)[0]
                
                # Read template file
                file_path = os.path.join(self.templates_dir, file_name)
                success, content = safe_read_file(file_path)
                
                if success and content:
                    self.templates[template_name] = content
                    self.logger.info(f"Loaded template '{template_name}' from {file_path}")
                else:
                    self.logger.warning(f"Failed to load template from {file_path}")
            
            self.logger.info(f"Loaded {len(template_files)} templates from {self.templates_dir}")
        except Exception as e:
            self.logger.error(f"Error loading templates from directory: {e}")
    
    def get_template(self, template_name: str) -> Optional[str]:
        """
        Get a template by name.
        
        Args:
            template_name: Name of the template to retrieve
            
        Returns:
            Template string or None if not found
        """
        return self.templates.get(template_name)
    
    def register_template(self, template_name: str, template_content: str, save_to_disk: bool = False) -> bool:
        """
        Register a new template.
        
        Args:
            template_name: Name for the template
            template_content: HTML template content
            save_to_disk: Whether to save the template to disk
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.templates[template_name] = template_content
            
            if save_to_disk:
                # Save template to disk
                file_path = os.path.join(self.templates_dir, f"{template_name}.html")
                success = safe_write_file(file_path, template_content)
                
                if not success:
                    self.logger.warning(f"Failed to save template '{template_name}' to disk")
                    return False
                
                self.logger.info(f"Saved template '{template_name}' to {file_path}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error registering template '{template_name}': {e}")
            return False
    
    def list_templates(self) -> List[str]:
        """
        List all available templates.
        
        Returns:
            List of template names
        """
        return list(self.templates.keys())
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Render a template with the provided context.
        
        Args:
            template_name: Name of the template to render
            context: Dictionary of variables to inject into the template
            
        Returns:
            Rendered HTML or None if template not found
        """
        template = self.get_template(template_name)
        
        if not template:
            self.logger.warning(f"Template '{template_name}' not found")
            return None
        
        try:
            # Simple template rendering with placeholders
            rendered = template
            
            # Replace simple variables: {{variable}}
            for key, value in context.items():
                if isinstance(value, (str, int, float)):
                    placeholder = "{{" + key + "}}"
                    rendered = rendered.replace(placeholder, str(value))
            
            # Handle conditional sections: {{#variable}}content{{/variable}}
            for key, value in context.items():
                # If value is truthy, keep the content inside the conditional
                if value:
                    pattern = r'{{#' + re.escape(key) + r'}}(.*?){{/' + re.escape(key) + r'}}'
                    rendered = re.sub(pattern, r'\1', rendered, flags=re.DOTALL)
                else:
                    # If value is falsy, remove the content inside the conditional
                    pattern = r'{{#' + re.escape(key) + r'}}(.*?){{/' + re.escape(key) + r'}}'
                    rendered = re.sub(pattern, '', rendered, flags=re.DOTALL)
            
            # Handle loop sections: {{#items}}{{item}}{{/items}}
            for key, value in context.items():
                if isinstance(value, list):
                    loop_pattern = r'{{#' + re.escape(key) + r'}}(.*?){{/' + re.escape(key) + r'}}'
                    loop_match = re.search(loop_pattern, rendered, re.DOTALL)
                    
                    if loop_match:
                        loop_template = loop_match.group(1)
                        loop_result = ""
                        
                        for item in value:
                            if isinstance(item, dict):
                                item_content = loop_template
                                for item_key, item_value in item.items():
                                    if isinstance(item_value, (str, int, float)):
                                        item_content = item_content.replace(
                                            "{{" + item_key + "}}", str(item_value)
                                        )
                                loop_result += item_content
                            else:
                                # If items are not dictionaries, use them directly
                                loop_result += loop_template.replace("{{item}}", str(item))
                        
                        rendered = re.sub(loop_pattern, loop_result, rendered, flags=re.DOTALL)
            
            return rendered
        except Exception as e:
            self.logger.error(f"Error rendering template '{template_name}': {e}")
            return None


class ThemeManager:
    """
    Manages CSS themes for HTML content.
    """
    
    def __init__(self, themes_dir: Optional[str] = None):
        """
        Initialize the ThemeManager.
        
        Args:
            themes_dir: Optional directory path containing theme CSS files
        """
        self.logger = logger
        self.themes = {}
        self.themes_dir = themes_dir or os.path.join(os.getcwd(), "templates", "themes")
        
        # Ensure themes directory exists
        os.makedirs(self.themes_dir, exist_ok=True)
        
        # Load default themes
        self._load_default_themes()
        
        # Load custom themes if themes directory exists
        if os.path.exists(self.themes_dir):
            self._load_themes_from_directory()
    
    def _load_default_themes(self):
        """Load default built-in themes."""
        # Default light theme
        self.themes["light"] = """
        :root {
            --primary-color: #4a6da7;
            --secondary-color: #f8f9fa;
            --text-color: #333;
            --link-color: #0066cc;
            --heading-color: #2c3e50;
            --border-color: #dee2e6;
            --code-bg: #f5f5f5;
            --blockquote-bg: #f9f9f9;
            --blockquote-border: #e3e3e3;
            --font-sans: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            --font-serif: Georgia, 'Times New Roman', serif;
            --font-mono: 'Courier New', Courier, monospace;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: var(--font-sans);
            line-height: 1.6;
            color: var(--text-color);
            background-color: #fff;
            max-width: 100%;
            overflow-x: hidden;
        }
        
        .container {
            max-width: 850px;
            margin: 0 auto;
            padding: 1rem;
        }
        
        header {
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        header h1 {
            color: var(--heading-color);
            margin-bottom: 0.5rem;
        }
        
        .metadata {
            font-size: 0.9rem;
            color: #666;
        }
        
        .metadata span {
            margin-right: 1rem;
        }
        
        main {
            margin-bottom: 2rem;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: var(--heading-color);
            margin: 1.5rem 0 1rem 0;
            line-height: 1.2;
        }
        
        h1 { font-size: 2.2rem; }
        h2 { font-size: 1.8rem; }
        h3 { font-size: 1.5rem; }
        h4 { font-size: 1.3rem; }
        h5 { font-size: 1.1rem; }
        h6 { font-size: 1rem; }
        
        p {
            margin-bottom: 1.2rem;
        }
        
        a {
            color: var(--link-color);
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        ul, ol {
            margin-bottom: 1.2rem;
            padding-left: 2rem;
        }
        
        li {
            margin-bottom: 0.5rem;
        }
        
        blockquote {
            border-left: 4px solid var(--blockquote-border);
            background-color: var(--blockquote-bg);
            padding: 1rem;
            margin-bottom: 1.2rem;
            font-style: italic;
        }
        
        code {
            font-family: var(--font-mono);
            background-color: var(--code-bg);
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-size: 0.9rem;
        }
        
        pre {
            background-color: var(--code-bg);
            padding: 1rem;
            border-radius: 5px;
            overflow-x: auto;
            margin-bottom: 1.2rem;
        }
        
        pre code {
            padding: 0;
            background-color: transparent;
        }
        
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1.2rem auto;
        }
        
        .lessons-list {
            margin-top: 2rem;
        }
        
        footer {
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
        }
        
        .navigation {
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
        }
        
        .navigation a {
            margin: 0.5rem;
            padding: 0.5rem 1rem;
            background-color: var(--secondary-color);
            border-radius: 4px;
            text-decoration: none;
            transition: background-color 0.2s;
        }
        
        .navigation a:hover {
            background-color: var(--border-color);
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .container {
                padding: 0.5rem;
            }
            
            h1 { font-size: 1.8rem; }
            h2 { font-size: 1.5rem; }
            h3 { font-size: 1.3rem; }
            
            .navigation {
                flex-direction: column;
            }
            
            .navigation a {
                margin: 0.3rem 0;
                text-align: center;
        }
        """

        # Default dark theme
        self.themes["dark"] = """
        :root {
            --primary-color: #6c8ecc;
            --secondary-color: #2c3844;
            --text-color: #e0e0e0;
            --link-color: #8cb4ff;
            --heading-color: #ffffff;
            --border-color: #4a5a6a;
            --code-bg: #282c34;
            --blockquote-bg: #2c3440;
            --blockquote-border: #4a5a6a;
            --font-sans: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            --font-serif: Georgia, 'Times New Roman', serif;
            --font-mono: 'Courier New', Courier, monospace;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: var(--font-sans);
            line-height: 1.6;
            color: var(--text-color);
            background-color: #1a1f2b;
            max-width: 100%;
            overflow-x: hidden;
        }
        
        .container {
            max-width: 850px;
            margin: 0 auto;
            padding: 1rem;
        }
        
        header {
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        header h1 {
            color: var(--heading-color);
            margin-bottom: 0.5rem;
        }
        
        .metadata {
            font-size: 0.9rem;
            color: #aaa;
        }
        
        .metadata span {
            margin-right: 1rem;
        }
        
        main {
            margin-bottom: 2rem;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: var(--heading-color);
            margin: 1.5rem 0 1rem 0;
            line-height: 1.2;
        }
        
        h1 { font-size: 2.2rem; }
        h2 { font-size: 1.8rem; }
        h3 { font-size: 1.5rem; }
        h4 { font-size: 1.3rem; }
        h5 { font-size: 1.1rem; }
        h6 { font-size: 1rem; }
        
        p {
            margin-bottom: 1.2rem;
        }
        
        a {
            color: var(--link-color);
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        ul, ol {
            margin-bottom: 1.2rem;
            padding-left: 2rem;
        }
        
        li {
            margin-bottom: 0.5rem;
        }
        
        blockquote {
            border-left: 4px solid var(--blockquote-border);
            background-color: var(--blockquote-bg);
            padding: 1rem;
            margin-bottom: 1.2rem;
            font-style: italic;
        }
        
        code {
            font-family: var(--font-mono);
            background-color: var(--code-bg);
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-size: 0.9rem;
        }
        
        pre {
            background-color: var(--code-bg);
            padding: 1rem;
            border-radius: 5px;
            overflow-x: auto;
            margin-bottom: 1.2rem;
        }
        
        pre code {
            padding: 0;
            background-color: transparent;
        }
        
        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1.2rem auto;
        }
        
        .lessons-list {
            margin-top: 2rem;
        }
        
        footer {
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
        }
        
        .navigation {
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
        }
        
        .navigation a {
            margin: 0.5rem;
            padding: 0.5rem 1rem;
            background-color: var(--secondary-color);
            border-radius: 4px;
            text-decoration: none;
            transition: background-color 0.2s;
        }
        
        .navigation a:hover {
            background-color: #3a4857;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .container {
                padding: 0.5rem;
            }
            
            h1 { font-size: 1.8rem; }
            h2 { font-size: 1.5rem; }
            h3 { font-size: 1.3rem; }
            
            .navigation {
                flex-direction: column;
            }
            
            .navigation a {
                margin: 0.3rem 0;
                text-align: center;
            }
        }
        """

