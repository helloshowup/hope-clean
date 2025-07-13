#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ShowupSquared RAG System

A lightweight, local vector database and retrieval system for reducing token usage
when generating content with Claude API.
"""

import logging
from .token_counter import count_tokens, tokenizer
from .cache_manager import cache
from .textbook_vector_db import vector_db
from .rag_integration import enhanced_generate_content, generate_with_claude_rag

# Configure package-level logger
logger = logging.getLogger(__name__)

__all__ = [
    'count_tokens',
    'tokenizer',
    'cache',
    'vector_db',
    'enhanced_generate_content',
    'generate_with_claude_rag'
]
