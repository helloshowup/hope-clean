#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Claude API Client - Handles communication with Claude API for enhanced RAG capabilities

This module provides a clean interface for making calls to Claude API,
specifically optimized for query construction and content analysis tasks.
"""

import os
import json
import logging
import time
import hashlib
from typing import Dict, Any, Optional, List, Union

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests library not available. Claude API client will not work.")

# Configure logging
logger = logging.getLogger(__name__)

def load_env_file(env_path: str) -> Dict[str, str]:
    """Load environment variables from a .env file."""
    env_vars = {}
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip('"\'')
                        env_vars[key.strip()] = value
            logger.info(f"Loaded {len(env_vars)} variables from {env_path}")
        except Exception as e:
            logger.error(f"Error loading .env file {env_path}: {e}")
    return env_vars

class ClaudeAPIClient:
    """Client for interacting with Claude API"""
    
    def __init__(self, 
                 api_key: Optional[str] = None, 
                 model: str = "claude-3-haiku-20240307",
                 cache_dir: str = "./claude_cache",
                 env_path: Optional[str] = None):
        """Initialize Claude API client
        
        Args:
            api_key: Claude API key (if None, will look for CLAUDE_API_KEY or ANTHROPIC_API_KEY env var or .env file)
            model: Claude model to use
            cache_dir: Directory to cache Claude API responses
            env_path: Path to .env file (if None, will look in common locations)
        """
        # Try environment variables first (both possible names)
        self.api_key = api_key or os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            # Try to find .env file in common locations
            env_paths_to_try = []
            if env_path:
                env_paths_to_try.append(env_path)
            
            # Look for .env in project root (relative to this file)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.join(current_dir, "..", "..", "..", ".env")
            env_paths_to_try.append(os.path.normpath(project_root))
            
            # Also try current working directory
            env_paths_to_try.append(".env")
            
            for env_file_path in env_paths_to_try:
                if os.path.exists(env_file_path):
                    env_vars = load_env_file(env_file_path)
                    # Check for both possible key names
                    self.api_key = env_vars.get("CLAUDE_API_KEY") or env_vars.get("ANTHROPIC_API_KEY")
                    if self.api_key:
                        logger.info(f"Loaded Claude API key from {env_file_path}")
                        break
            
            if not self.api_key:
                logger.warning("No Claude API key found. Checked CLAUDE_API_KEY and ANTHROPIC_API_KEY in environment variables and .env files.")
        
        self.model = model
        self.cache_dir = cache_dir
        self.base_url = "https://api.anthropic.com/v1/messages"
        
        # Create cache directory
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            logger.info(f"Created Claude cache directory: {cache_dir}")
    
    def _get_cache_key(self, prompt: str, model: str) -> str:
        """Generate cache key for a prompt"""
        content = f"{model}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> str:
        """Get path to cached response"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def _load_from_cache(self, cache_key: str) -> Optional[str]:
        """Load response from cache if available"""
        cache_path = self._get_cache_path(cache_key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Check if cache is less than 24 hours old
                    if time.time() - data.get('timestamp', 0) < 86400:
                        logger.debug(f"Using cached response for key: {cache_key}")
                        return data.get('response')
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        return None
    
    def _save_to_cache(self, cache_key: str, response: str):
        """Save response to cache"""
        cache_path = self._get_cache_path(cache_key)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'response': response,
                    'timestamp': time.time()
                }, f, ensure_ascii=False, indent=2)
            logger.debug(f"Cached response for key: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def call_claude(self, prompt: str, max_tokens: int = 1000, 
                   temperature: float = 0.3, use_cache: bool = True) -> Optional[str]:
        """Make a call to Claude API
        
        Args:
            prompt: The prompt to send to Claude
            max_tokens: Maximum tokens in response
            temperature: Temperature for response generation
            use_cache: Whether to use cached responses
            
        Returns:
            Claude's response text or None if failed
        """
        if not self.api_key:
            logger.error("No Claude API key available")
            return None
        
        if not REQUESTS_AVAILABLE:
            logger.error("requests library not available")
            return None
        
        # Check cache first
        cache_key = self._get_cache_key(prompt, self.model)
        if use_cache:
            cached_response = self._load_from_cache(cache_key)
            if cached_response:
                return cached_response
        
        # Prepare API request
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        try:
            logger.debug(f"Making Claude API call with {len(prompt)} character prompt")
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            response_data = response.json()
            content = response_data.get('content', [])
            
            if content and len(content) > 0:
                result = content[0].get('text', '')
                
                # Cache the response
                if use_cache:
                    self._save_to_cache(cache_key, result)
                
                logger.debug(f"Claude API call successful, response length: {len(result)}")
                return result
            else:
                logger.error("No content in Claude API response")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Claude API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Claude API call: {e}")
            return None
    
    def generate_search_queries(self, lesson_content: str) -> Dict[str, List[str]]:
        """Generate enhanced search queries from lesson content
        
        Args:
            lesson_content: The lesson content to analyze
            
        Returns:
            Dictionary with concepts as keys and related search terms as values
        """
        # Extract key parts of lesson to save tokens
        lesson_summary = self._extract_lesson_summary(lesson_content)
        
        prompt = f"""Analyze this lesson content and extract the 3-5 most important concepts, topics, or questions that would be relevant to search for in a reference handbook.

For each concept, provide 2-3 alternative phrasings or related terms that might appear in a handbook.

Format your response as a JSON object with concepts as keys and arrays of related terms as values.

Example format:
{{
    "grid systems": ["grid layout", "layout grid", "design grid"],
    "typography": ["font selection", "typeface", "text styling"],
    "color theory": ["color palette", "color schemes", "color harmony"]
}}

LESSON CONTENT:
{lesson_summary}

Respond with only the JSON object, no additional text."""
        
        response = self.call_claude(prompt, max_tokens=500, temperature=0.2)
        
        if response:
            try:
                # Clean up response to ensure it's valid JSON
                response = response.strip()
                if response.startswith('```json'):
                    response = response[7:]
                if response.endswith('```'):
                    response = response[:-3]
                response = response.strip()
                
                query_data = json.loads(response)
                logger.info(f"Generated {len(query_data)} search concepts from lesson")
                return query_data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Claude response as JSON: {e}")
                logger.debug(f"Raw response: {response}")
        
        # Fallback to basic keyword extraction
        return self._fallback_keyword_extraction(lesson_content)
    
    def _extract_lesson_summary(self, lesson_content: str, max_chars: int = 2000) -> str:
        """Extract a summary of the lesson to save tokens
        
        Args:
            lesson_content: Full lesson content
            max_chars: Maximum characters to include
            
        Returns:
            Summarized lesson content
        """
        # Extract headings first
        import re
        headings = re.findall(r'^#+\s+(.+?)$', lesson_content, re.MULTILINE)
        
        # Start with headings
        summary_parts = []
        if headings:
            summary_parts.append("HEADINGS: " + " | ".join(headings))
        
        # Add first few paragraphs
        paragraphs = [p.strip() for p in lesson_content.split('\n\n') if p.strip()]
        
        current_length = len('\n'.join(summary_parts))
        for para in paragraphs[:5]:  # Limit to first 5 paragraphs
            if current_length + len(para) > max_chars:
                break
            summary_parts.append(para)
            current_length += len(para)
        
        return '\n\n'.join(summary_parts)
    
    def _fallback_keyword_extraction(self, lesson_content: str) -> Dict[str, List[str]]:
        """Fallback keyword extraction when Claude API fails
        
        Args:
            lesson_content: The lesson content
            
        Returns:
            Basic keyword extraction results
        """
        import re
        
        # Extract headings as main concepts
        headings = re.findall(r'^#+\s+(.+?)$', lesson_content, re.MULTILINE)
        
        # Extract common design/educational terms
        common_terms = [
            'design', 'layout', 'grid', 'typography', 'color', 'brand',
            'visual', 'pattern', 'structure', 'hierarchy', 'balance',
            'contrast', 'alignment', 'proximity', 'repetition'
        ]
        
        found_terms = []
        content_lower = lesson_content.lower()
        for term in common_terms:
            if term in content_lower:
                found_terms.append(term)
        
        # Create basic query structure
        result = {}
        
        # Add headings as concepts
        for heading in headings[:3]:  # Limit to first 3 headings
            clean_heading = re.sub(r'[^\w\s]', '', heading).strip()
            if clean_heading:
                result[clean_heading.lower()] = [clean_heading, clean_heading.replace(' ', '_')]
        
        # Add found terms
        if found_terms:
            result['key_concepts'] = found_terms
        
        logger.info(f"Fallback extraction found {len(result)} concepts")
        return result


# Create a singleton instance
claude_client = ClaudeAPIClient()
