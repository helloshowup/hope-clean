#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Text processing utilities for fitness instruction voiceover generation.

Contains functions for processing text files, extracting fitness exercise content,
and preparing data for fitness script generation.
"""

import os
import logging
from typing import List

logger = logging.getLogger('fitness_instructor_voiceover')


def read_file_content(file_path: str) -> str:
    """Read content from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return ""


def prepare_fitness_content_for_prompt(file_paths: List[str]) -> str:
    """Process content files to extract key exercise details for fitness instruction script generation."""
    if not file_paths:
        logger.error("No files provided for fitness content preparation")
        return ""
    
    try:
        combined_content = ""
        
        for file_path in file_paths:
            logger.info(f"Processing fitness file: {file_path}")
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Extract only the text content, skipping metadata, code blocks, etc.
            combined_content += f"\n\n=== EXERCISE CONTENT FROM {os.path.basename(file_path)} ===\n\n"
            combined_content += file_content
        
        # Format prompt with instructions for fitness content
        formatted_prompt = (
            "Create a concise, user-friendly script that guides a learner through the exercise below, "
            "extracting only the cues necessary for correct form, reps, breathing, and modifications. "
            "Use the tone of an enthusiastic fitness instructor.\n\n"
            f"{combined_content}\n\n"
            "Important: Keep language audio-friendly and relevant to asynchronous learners. "
            "Focus on action-oriented cues and brief explanations (why it matters). "
            "Use clear, motivational wording suitable for adult learners at any fitness level."
        )
        
        return formatted_prompt
        
    except Exception as e:
        logger.error(f"Error preparing fitness content for prompt: {str(e)}")
        return ""
