"""
Simplified Workflow Package for ShowupSquaredV3.

This package implements a streamlined content generation workflow that processes
one content piece at a time through all steps, including content generation,
comparison, review, AI detection, and editing.

The workflow is designed to be simple, maintainable, and focused on personal utility.
"""

from .workflow import main as run_workflow

__all__ = ['run_workflow']