"""
Claude Text Editor Integration

This module provides integration with Claude's text editor tool capability,
allowing AI-assisted document editing.
"""

import os
import logging
import shutil
from datetime import datetime
from .file_utils import create_timestamped_backup

# Set up logging
logger = logging.getLogger('claude_editor')

class ClaudeEditor:
    """A class that implements the Claude Text Editor tool functionality."""
    
    def __init__(self, base_dir=None, backup_dir=None):
        """Initialize the editor with base directory and backup directory."""
        self.base_dir = base_dir or os.getcwd()
        self.backup_dir = backup_dir or os.path.join(self.base_dir, "_backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        self.operations = {}
        
    def view(self, path, view_range=None):
        """
        View the contents of a file or list a directory.
        
        Args:
            path: Path to the file or directory to view
            view_range: Optional tuple of (start_line, end_line) to view only a portion of the file
            
        Returns:
            File content as string or directory listing as list
        """
        full_path = os.path.join(self.base_dir, path)
        
        # Check if path exists
        if not os.path.exists(full_path):
            logger.error(f"Path does not exist: {full_path}")
            return f"Error: Path does not exist: {path}"
        
        # If it's a directory, list its contents
        if os.path.isdir(full_path):
            try:
                items = os.listdir(full_path)
                return {
                    "type": "directory",
                    "path": path,
                    "items": items
                }
            except Exception as e:
                logger.error(f"Error listing directory {path}: {str(e)}")
                return f"Error listing directory: {str(e)}"
        
        # If it's a file, read its contents
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # If view_range is specified, extract only those lines
            if view_range and isinstance(view_range, tuple) and len(view_range) == 2:
                start_line, end_line = view_range
                lines = content.split('\n')
                
                # Adjust for 0-based indexing
                start_idx = max(0, start_line - 1)
                end_idx = min(len(lines), end_line)
                
                content = '\n'.join(lines[start_idx:end_idx])
            
            return {
                "type": "file",
                "path": path,
                "content": content
            }
        except Exception as e:
            logger.error(f"Error reading file {path}: {str(e)}")
            return f"Error reading file: {str(e)}"
        
    def str_replace(self, path, old_str, new_str):
        """
        Replace a specific string in a file with a new string.
        
        Args:
            path: Path to the file to modify
            old_str: String to replace
            new_str: Replacement string
            
        Returns:
            Dictionary with operation result
        """
        full_path = os.path.join(self.base_dir, path)
        
        # Check if file exists
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            logger.error(f"File does not exist: {full_path}")
            return {
                "success": False,
                "error": f"File does not exist: {path}"
            }
        
        try:
            # Create backup
            backup_path = self._create_backup(full_path)
            
            # Read file content
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace string
            new_content = content.replace(old_str, new_str)
            
            # Count replacements
            replacement_count = content.count(old_str)
            
            # Write updated content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"Replaced {replacement_count} occurrences in {path}")
            
            return {
                "success": True,
                "path": path,
                "replacements": replacement_count,
                "backup_path": backup_path
            }
        except Exception as e:
            logger.error(f"Error replacing string in {path}: {str(e)}")
            return {
                "success": False,
                "error": f"Error replacing string: {str(e)}"
            }
    
    def edit_file(self, path, new_content):
        """
        Edit a file by replacing its entire content.
        
        Args:
            path: Path to the file to edit
            new_content: New content for the file
            
        Returns:
            Dictionary with operation result
        """
        full_path = os.path.join(self.base_dir, path)
        
        # Check if file exists
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            logger.error(f"File does not exist: {full_path}")
            return {
                "success": False,
                "error": f"File does not exist: {path}"
            }
        
        try:
            # Create backup
            backup_path = self._create_backup(full_path)
            
            # Write new content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"Edited file: {path}")
            
            return {
                "success": True,
                "path": path,
                "backup_path": backup_path
            }
        except Exception as e:
            logger.error(f"Error editing file {path}: {str(e)}")
            return {
                "success": False,
                "error": f"Error editing file: {str(e)}"
            }
    
    def _create_backup(self, file_path):
        """Create a backup of a file before modifying it."""
        try:
            # Get relative path to maintain directory structure inside backup_dir
            rel_path = os.path.relpath(file_path, self.base_dir)

            backup_dir = os.path.join(self.backup_dir, os.path.dirname(rel_path))
            os.makedirs(backup_dir, exist_ok=True)

            backup_path = create_timestamped_backup(file_path, backup_dir)
            return backup_path
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return None

def enhance_document(file_path, template_path=None, custom_prompt=None, learner_profile=None):
    """
    Enhance a document by comparing it to a template and making improvements.
    
    Args:
        file_path: Path to the document to enhance
        template_path: Optional path to a template document
        custom_prompt: Optional custom prompt for enhancement
        learner_profile: Optional learner profile for context
        
    Returns:
        Enhanced document content
    """
    try:
        # Import here to avoid circular imports
        from .api_client import generate_with_claude
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Read template content if provided
        template_content = ""
        if template_path and os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        
        # Create system prompt
        system_prompt = """
        You are an expert educational content editor. Your task is to enhance the provided document
        while maintaining its educational integrity and structure.
        
        If a template is provided, use it as a reference for style, structure, and formatting.
        If a custom prompt is provided, follow its specific instructions for enhancement.
        If a learner profile is provided, tailor the content to meet the needs of that learner.
        
        Important guidelines:
        1. Preserve any YAML frontmatter at the beginning of the document (between --- delimiters)
        2. Maintain the overall structure and educational integrity of the content
        3. Improve clarity, readability, and engagement
        4. Ensure the content is appropriate for the target learner
        5. Return the complete enhanced document
        """
        
        # Create user prompt
        user_prompt = f"""
        # Document to Enhance
        
        {file_content}
        """
        
        # Add template if available
        if template_content:
            user_prompt += f"""
            
            # Template Reference
            
            {template_content}
            """
        
        # Add custom prompt if available
        if custom_prompt:
            user_prompt += f"""
            
            # Custom Enhancement Instructions
            
            {custom_prompt}
            """
        
        # Add learner profile if available
        if learner_profile:
            user_prompt += f"""
            
            # Target Learner Profile
            
            {learner_profile}
            """
        
        # Call Claude API
        enhanced_content = generate_with_claude(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model="claude-3-7-sonnet-20250219",
            max_tokens=4000,
            temperature=0.2,
            task_type="document_enhancement"
        )
        
        logger.info(f"Enhanced document: {file_path}")
        return enhanced_content
        
    except Exception as e:
        logger.error(f"Error enhancing document: {str(e)}")
        return f"Error enhancing document: {str(e)}"
