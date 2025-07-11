"""
API utility functions for the ShowupSquared workflow system.

This module provides utilities for interacting with AI APIs, including
parameter preparation, error handling, caching, and cost calculation.
"""

import os
import json
import time
import hashlib
import logging
import datetime
from typing import Dict, Any, List, Optional, Tuple, Callable
from .model_config import DEFAULT_CONTEXT_MODEL

logger = logging.getLogger("api_utils")

def prepare_api_params(model: str = DEFAULT_CONTEXT_MODEL,
                     temperature: float = 0.7,
                     max_tokens: int = 4000,
                     system_prompt: Optional[str] = None,
                     messages: Optional[List[Dict[str, str]]] = None,
                     prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Prepare parameters for API call based on model type.
    
    Args:
        model: Model identifier
        temperature: Temperature setting for response randomness
        max_tokens: Maximum tokens in the response
        system_prompt: Optional system prompt for chat models
        messages: Optional messages for chat models
        prompt: Optional prompt for completion models
        
    Returns:
        Dictionary of parameters for API call
    """
    params = {
        "model": model,
        "temperature": temperature,
        "max_tokens_to_sample": max_tokens
    }
    
    # If it's a Claude chat model
    if "claude" in model.lower() and (messages or system_prompt):
        # For Claude 3 models
        if "claude-3" in model.lower():
            if messages:
                params["messages"] = messages
            else:
                # Create a simple message structure
                params["messages"] = [
                    {"role": "user", "content": prompt or ""}
                ]
            
            # Add system prompt if provided
            if system_prompt:
                params["system"] = system_prompt
        
        # For older Claude models
        else:
            # Use the anthropic format
            prepared_prompt = ""
            
            if system_prompt:
                prepared_prompt += f"{system_prompt}\n\n"
            
            if messages:
                for message in messages:
                    role = message.get("role", "")
                    content = message.get("content", "")
                    
                    if role == "user":
                        prepared_prompt += f"\n\nHuman: {content}"
                    elif role == "assistant":
                        prepared_prompt += f"\n\nAssistant: {content}"
            elif prompt:
                prepared_prompt += f"\n\nHuman: {prompt}\n\nAssistant:"
            
            params["prompt"] = prepared_prompt
    
    # For standard completion models
    elif prompt:
        params["prompt"] = prompt
    
    return params

def test_api_connection(api_key: str, client_type: str = "claude") -> Tuple[bool, str]:
    """
    Test API connection with a specified key and client type.
    
    Args:
        api_key: API key to test
        client_type: Client type (claude, openai, etc.)
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Claude API
        if client_type.lower() == "claude":
            import anthropic
            client = anthropic.Client(api_key=api_key)
            
            # Create a simple message to test
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[
                    {"role": "user", "content": "Reply with 'Connection successful' only"}
                ]
            )
            
            if response and hasattr(response, 'content'):
                return True, "Connection successful"
            else:
                return False, "Unexpected response format"
        
        # OpenAI API
        elif client_type.lower() == "openai":
            import openai
            client = openai.OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Reply with 'Connection successful' only"}],
                max_tokens=10
            )
            
            if response and hasattr(response, 'choices'):
                return True, "Connection successful"
            else:
                return False, "Unexpected response format"
        
        else:
            return False, f"Unsupported client type: {client_type}"
            
    except Exception as e:
        logger.error(f"API connection test failed: {str(e)}")
        return False, f"Connection failed: {str(e)}"

def calculate_cost(model: str, 
                 prompt_tokens: int, 
                 completion_tokens: int,
                 pricing_data: Optional[Dict[str, Dict[str, float]]] = None) -> float:
    """
    Calculate cost based on model and token usage.
    
    Args:
        model: Model identifier
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        pricing_data: Optional custom pricing data
        
    Returns:
        Calculated cost in USD
    """
    # Default pricing data for common models
    default_pricing = {
        "claude-3-opus": {"prompt": 15.0, "completion": 75.0},  # $15/$75 per million tokens
        "claude-3-sonnet": {"prompt": 3.0, "completion": 15.0},  # $3/$15 per million tokens
        "claude-3-haiku": {"prompt": 0.25, "completion": 1.25},  # $0.25/$1.25 per million tokens
        "gpt-4": {"prompt": 30.0, "completion": 60.0},  # $30/$60 per million tokens
        "gpt-3.5-turbo": {"prompt": 0.5, "completion": 1.5}  # $0.5/$1.5 per million tokens
    }
    
    # Use provided pricing data or default
    pricing = pricing_data or default_pricing
    
    # Find the matching model pricing
    model_pricing = None
    for model_key, price in pricing.items():
        if model_key in model.lower():
            model_pricing = price
            break
    
    # If no specific pricing found, use a default
    if not model_pricing:
        # Default to a moderate pricing tier
        model_pricing = {"prompt": 3.0, "completion": 15.0}
        logger.warning(f"No specific pricing found for {model}, using default pricing")
    
    # Calculate cost (converting from per-million to per-token)
    prompt_cost = (prompt_tokens * model_pricing["prompt"]) / 1_000_000
    completion_cost = (completion_tokens * model_pricing["completion"]) / 1_000_000
    
    total_cost = prompt_cost + completion_cost
    
    return total_cost

def with_error_handling(func: Callable, 
                      max_retries: int = 3, 
                      retry_delay: float = 2.0,
                      *args, **kwargs) -> Tuple[bool, Any, Dict[str, Any]]:
    """
    Execute a function with retry and error handling.
    
    Args:
        func: Function to execute
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds
        *args, **kwargs: Arguments to pass to the function
        
    Returns:
        Tuple of (success, result, metadata)
    """
    metadata = {
        "attempts": 0,
        "success": False,
        "error": None,
        "start_time": time.time(),
        "end_time": None
    }
    
    for attempt in range(max_retries):
        metadata["attempts"] += 1
        
        try:
            result = func(*args, **kwargs)
            metadata["success"] = True
            metadata["end_time"] = time.time()
            metadata["duration"] = metadata["end_time"] - metadata["start_time"]
            return True, result, metadata
            
        except Exception as e:
            logger.warning(f"Attempt {attempt+1}/{max_retries} failed: {str(e)}")
            metadata["error"] = str(e)
            
            if attempt < max_retries - 1:
                # Exponential backoff
                sleep_time = retry_delay * (2 ** attempt)
                logger.info(f"Retrying in {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
    
    metadata["end_time"] = time.time()
    metadata["duration"] = metadata["end_time"] - metadata["start_time"]
    logger.error(f"All {max_retries} attempts failed: {metadata['error']}")
    
    return False, None, metadata

def extract_response_content(response: Any, client_type: str = "claude") -> str:
    """
    Extract text content from API response based on client type.
    
    Args:
        response: API response object
        client_type: Client type (claude, openai, etc.)
        
    Returns:
        Extracted text content
    """
    try:
        # Claude API
        if client_type.lower() == "claude":
            if hasattr(response, 'content'):
                if isinstance(response.content, list):
                    return response.content[0].text
                return response.content
            elif hasattr(response, 'completion'):
                return response.completion
            else:
                logger.warning(f"Unexpected Claude response format: {type(response)}")
                return str(response)
        
        # OpenAI API
        elif client_type.lower() == "openai":
            if hasattr(response, 'choices') and len(response.choices) > 0:
                if hasattr(response.choices[0], 'message'):
                    return response.choices[0].message.content
                elif hasattr(response.choices[0], 'text'):
                    return response.choices[0].text
                else:
                    logger.warning(f"Unexpected OpenAI response format: {type(response.choices[0])}")
                    return str(response)
            else:
                logger.warning(f"Unexpected OpenAI response format: {type(response)}")
                return str(response)
        
        # Unknown client
        else:
            logger.warning(f"Unsupported client type: {client_type}")
            return str(response)
    
    except Exception as e:
        logger.error(f"Error extracting response content: {str(e)}")
        return str(response)

def get_cached_or_generate(cache_key: str, 
                         generate_func: Callable, 
                         cache_dir: str,
                         force_refresh: bool = False,
                         max_cache_age: int = 30,  # days
                         *args, **kwargs) -> Tuple[bool, Any, bool]:
    """
    Get cached result or generate and cache new result.
    
    Args:
        cache_key: Unique key for cache entry
        generate_func: Function to generate result if cache miss
        cache_dir: Directory for cache files
        force_refresh: Whether to force regeneration
        max_cache_age: Maximum age of cache in days
        *args, **kwargs: Arguments to pass to generate function
        
    Returns:
        Tuple of (success, result, was_cached)
    """
    # Create cache directory if it doesn't exist
    os.makedirs(cache_dir, exist_ok=True)
    
    # Create a deterministic filename from cache key
    cache_key_hash = hashlib.md5(cache_key.encode()).hexdigest()
    cache_file = os.path.join(cache_dir, f"{cache_key_hash}.json")
    
    # Check if cache file exists and is not expired
    if os.path.exists(cache_file) and not force_refresh:
        file_age = (datetime.datetime.now() - 
                    datetime.datetime.fromtimestamp(os.path.getmtime(cache_file))).days
        
        if file_age <= max_cache_age:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                logger.info(f"Cache hit for key: {cache_key}")
                return True, cached_data, True
            except Exception as e:
                logger.warning(f"Error reading cache file: {str(e)}")
                # Fall through to regenerate
        else:
            logger.info(f"Cache expired for key: {cache_key} (age: {file_age} days)")
    
    # Cache miss or forced refresh, generate new result
    try:
        logger.info(f"Generating result for cache key: {cache_key}")
        result = generate_func(*args, **kwargs)
        
        # Save to cache
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved result to cache: {cache_file}")
        except Exception as e:
            logger.warning(f"Error writing to cache file: {str(e)}")
        
        return True, result, False
    
    except Exception as e:
        logger.error(f"Error generating result: {str(e)}")
        return False, str(e), False