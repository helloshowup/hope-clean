#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Text processing utilities for podcast generation.

Contains functions for processing text files, extracting educational content,
and preparing data for script generation.
"""

import os
import re
import glob
import logging
from typing import Dict, List
from showup_editor_ui.claude_panel.path_utils import get_project_root

logger = logging.getLogger('podcast_generator')


def load_learner_profiles() -> Dict[str, str]:
    """Load available learner profiles from the profiles directory."""
    learner_profiles: Dict[str, str] = {}
    
    profiles_dir = os.path.join(
        str(get_project_root()),
        "showup-core",
        "data",
        "input",
        "learner_profiles",
    )
    if not os.path.exists(profiles_dir):
        logger.warning(f"Learner profiles directory not found: {profiles_dir}")
        return learner_profiles
    
    # Default robotics podcast profile path
    default_profile_path = os.path.join(profiles_dir, "Robotics_Podcast.md")
    default_profile_content = ""
    
    # Only add these generic profiles if the Robotics_Podcast.md isn't found
    if not os.path.exists(default_profile_path):
        # Add default options
        learner_profiles["Beginner"] = "beginners with no prior knowledge"
        learner_profiles["Intermediate"] = "intermediates with some background knowledge"
        learner_profiles["Advanced"] = "advanced learners with strong domain knowledge"
    
    # Find all markdown and text files in the profiles directory
    profile_files = []
    # Process markdown files first (priority over .txt files with same name)
    for ext in [".md", ".txt"]:
        profile_files.extend(glob.glob(os.path.join(profiles_dir, f"*{ext}")))
    
    # Track processed profiles to avoid duplicates (prefer .md over .txt)
    processed_names = set()
    
    # Load profile content
    for profile_path in profile_files:
        try:
            filename = os.path.basename(profile_path)
            base_name = os.path.splitext(filename)[0]
            
            # Skip if we've already processed a file with this name
            # (this ensures .md files are used over .txt files with the same name)
            if base_name in processed_names:
                continue
            
            # Skip empty files
            if os.path.getsize(profile_path) == 0:
                logger.warning(f"Skipping empty profile file: {filename}")
                continue
            
            # Read profile content
            with open(profile_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Skip if content is empty after stripping
            if not content:
                logger.warning(f"Skipping profile with empty content: {filename}")
                continue
                
            # Use the first line as the display name if it's a heading
            display_name = base_name
            lines = content.split('\n')
            if lines and lines[0].startswith('#'):
                heading_name = lines[0].lstrip('#').strip()
                if heading_name:
                    display_name = heading_name
            
            # Save the default profile content if this is our target file
            if profile_path == default_profile_path:
                default_profile_content = content
            
            # Add to profiles dict and mark as processed
            learner_profiles[display_name] = content
            processed_names.add(base_name)
            logger.info(f"Loaded learner profile: {display_name} (from {filename}) with {len(content)} characters")
        except Exception as e:
            logger.error(f"Error loading learner profile {profile_path}: {str(e)}")
    
    return learner_profiles


def read_file_content(file_path: str) -> str:
    """Read content from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return ""


def prepare_content_for_prompt(file_paths: List[str]) -> str:
    """Process content files to extract key educational concepts for script generation."""
    combined_content = ""
    
    for file_path in file_paths:
        filename = os.path.basename(file_path)
        file_content = read_file_content(file_path)
        
        if not file_content:
            continue
            
        # Extract core educational components from markdown
        # Prioritize headings, learning objectives, and key definitions
        content_sections = []
        
        # Extract learning objectives if present
        learning_objectives = re.search(r'#+\s*Learning Objectives(.*?)(?=#+|$)', 
                                       file_content, re.DOTALL | re.IGNORECASE)
        if learning_objectives:
            content_sections.append(f"LEARNING OBJECTIVES:\n{learning_objectives.group(1).strip()}")
        
        # Extract key concepts and definitions (look for H2/H3 headings and subsequent paragraphs)
        key_concepts = re.findall(r'#{2,3}\s*(.*?)\n(.*?)(?=#{2,}|$)', 
                                 file_content, re.DOTALL)
        for concept in key_concepts:
            heading = concept[0].strip()
            content = concept[1].strip()
            if heading.lower() not in ['learning objectives']:  # Skip already processed sections
                content_sections.append(f"KEY CONCEPT - {heading}:\n{content}")
        
        # Ensure we're capturing key takeaways if present
        takeaways = re.search(r'#+\s*Key Takeaways(.*?)(?=#+|$)', 
                             file_content, re.DOTALL | re.IGNORECASE)
        if takeaways:
            content_sections.append(f"KEY TAKEAWAYS:\n{takeaways.group(1).strip()}")
            
        # Add the processed file content to combined content
        if content_sections:
            combined_content += f"\n\n--- EDUCATIONAL CONTENT FROM: {filename} ---\n\n"
            combined_content += "\n\n".join(content_sections)
        else:
            # Fallback: if structured extraction fails, include the raw content
            combined_content += f"\n\n--- CONTENT FROM: {filename} ---\n\n{file_content}"
    
    return combined_content
