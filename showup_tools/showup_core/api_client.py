"""
API client for interacting with AI services.

This module provides a unified interface for accessing various
AI models and services, with built-in error handling, caching, cost tracking,
and cost tracking capabilities.
"""

import os
import time
import json
import logging
import hashlib
import datetime
from typing import Dict, Optional
from showup_editor_ui.claude_panel.path_utils import get_project_root
from .model_config import DEFAULT_MODEL, DEFAULT_CONTEXT_MODEL

try:
    from .api_utils import (
        prepare_api_params,
        extract_response_content,
        calculate_cost,
        with_error_handling,
        get_cached_or_generate
    )
    # Import PromptTemplateSystem from prompt_templates module
    from .prompt_templates import PromptTemplateSystem
except ImportError:
    # Fallback for direct imports
    pass

logger = logging.getLogger("api_client")

class SmartModelSelector:
    """
    Intelligently selects AI models based on task requirements.
    
    This class helps choose the most appropriate model based on factors like
    task complexity, required capabilities, and cost constraints.
    """
    
    # Default model tiers with capabilities and costs
    DEFAULT_TIERS = {
        "basic": {
            "models": ["claude-3-haiku-20240307", "gpt-3.5-turbo"],
            "capabilities": ["simple_text", "classification", "summarization"],
            "max_tokens": 4000,
            "cost_per_1k": 0.25  # Approximate cost per 1K tokens
        },
        "standard": {
            "models": ["claude-3-7-sonnet-20250219", "gpt-3.5-turbo-16k"],
            "capabilities": ["simple_text", "classification", "summarization", 
                           "analysis", "coding", "content_creation"],
            "max_tokens": 8000,
            "cost_per_1k": 3.00  # Approximate cost per 1K tokens
        },
        "advanced": {
            "models": ["claude-3-opus-20240229", "gpt-4"],
            "capabilities": ["simple_text", "classification", "summarization", 
                           "analysis", "coding", "content_creation",
                           "complex_reasoning", "creative_work", "research"],
            "max_tokens": 16000,
            "cost_per_1k": 15.00  # Approximate cost per 1K tokens
        }
    }
    
    def __init__(self, preferred_provider: str = "claude", custom_tiers: Optional[Dict] = None):
        """
        Initialize the SmartModelSelector.
        
        Args:
            preferred_provider: Preferred AI provider (claude, openai)
            custom_tiers: Optional custom model tiers configuration
        """
        self.preferred_provider = preferred_provider.lower()
        self.tiers = custom_tiers or self.DEFAULT_TIERS
        self.logger = logging.getLogger("api_client.model_selector")
    
    def select_model(self, task_type: str, 
                   complexity: str = "standard", 
                   budget_sensitive: bool = False) -> str:
        """
        Select the most appropriate model for a given task.
        
        Args:
            task_type: Type of task (e.g., summarization, coding)
            complexity: Task complexity level (basic, standard, advanced)
            budget_sensitive: Whether to prioritize lower cost
            
        Returns:
            Selected model identifier
        """
        # Determine minimum required tier based on task type
        required_tier = "basic"
        
        for tier_name, tier_data in self.tiers.items():
            if task_type in tier_data["capabilities"]:
                required_tier = tier_name
                break
        
        # Override tier based on complexity if needed
        if complexity == "basic" and required_tier == "standard":
            # Downgrade if task allows
            if budget_sensitive:
                required_tier = "basic"
                self.logger.info("Downgrading to basic tier due to budget sensitivity")
        elif complexity == "advanced":
            # Upgrade if advanced complexity
            required_tier = "advanced"
            self.logger.info("Upgrading to advanced tier due to task complexity")
            
        # Select model based on preferred provider
        tier_data = self.tiers[required_tier]
        for model in tier_data["models"]:
            if self.preferred_provider in model.lower():
                return model
                
        # Fallback to first model in tier if preferred provider not found
        return tier_data["models"][0]


class ApiClient:
    """
    API client for interacting with LLM services.
    
    This class provides a unified interface for accessing AI model APIs,
    with built-in caching, error handling, and model selection.
    """
    
    def __init__(self, api_key: str = None, preferred_provider: str = "claude"):
        """
        Initialize the API client.
        
        Args:
            api_key: API key for the preferred provider (optional if set in config)
            preferred_provider: Preferred AI provider (claude, openai)
        """
        self.api_key = api_key
        self.preferred_provider = preferred_provider.lower()
        self.model_selector = SmartModelSelector(preferred_provider=preferred_provider)
        self.logger = logging.getLogger("api_client")
        
        # Try to load API keys from config if not provided
        if not self.api_key:
            # First, try to load from environment or .env file
            try:
                import os
                from dotenv import load_dotenv
                
                # Try to load from the ShowupSquared directory .env file
                dotenv_path = os.path.join(str(get_project_root()), '.env')
                load_dotenv(dotenv_path)
                
                if self.preferred_provider == "claude":
                    self.api_key = os.getenv("ANTHROPIC_API_KEY")
                elif self.preferred_provider == "openai":
                    self.api_key = os.getenv("OPENAI_API_KEY")
                    
                if self.api_key:
                    self.logger.info(f"Loaded {preferred_provider} API key from .env file")
            except ImportError:
                self.logger.warning("Could not import dotenv, falling back to config")
            except Exception as e:
                self.logger.warning(f"Error loading from .env: {str(e)}")
            
            # If still no API key, try from config file
            if not self.api_key:
                try:
                    from config.api_keys import ANTHROPIC_API_KEY, OPENAI_API_KEY
                    if self.preferred_provider == "claude" and ANTHROPIC_API_KEY:
                        self.api_key = ANTHROPIC_API_KEY
                    elif self.preferred_provider == "openai" and OPENAI_API_KEY:
                        self.api_key = OPENAI_API_KEY
                except ImportError:
                    self.logger.warning("Could not load API keys from config")
        
        # Check if API key is set
        if not self.api_key:
            self.logger.warning(f"No API key provided for {preferred_provider}")
    
    async def generate(self, prompt: str, task_type: str = "content_creation",
                 complexity: str = "standard", max_tokens: int = 4000,
                 temperature: float = 0.7, use_cache: bool = True) -> str:
        """
        Generate content using the selected LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            task_type: Type of task (summarization, coding, content_creation, etc.)
            complexity: Task complexity (basic, standard, advanced)
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature setting (0.0-1.0)
            use_cache: Whether to cache responses
            
        Returns:
            Generated content as a string
        """
        # Select appropriate model
        model = self.model_selector.select_model(task_type, complexity)
        
        # Use the selected model's API
        if "claude" in model.lower():
            return await generate_with_claude(prompt, max_tokens, temperature, model, use_cache)
        else:
            # Fallback to Claude if OpenAI integration not implemented yet
            self.logger.warning(f"Selected model {model} not fully supported, falling back to Claude")
            return await generate_with_claude(prompt, max_tokens, temperature, DEFAULT_MODEL, use_cache)


def get_api_client(api_key: str = None, preferred_provider: str = "claude") -> ApiClient:
    """
    Get an API client instance.
    
    Args:
        api_key: API key to use (optional if set in config)
        preferred_provider: Preferred AI provider (claude, openai)
        
    Returns:
        ApiClient instance
    """
    return ApiClient(api_key, preferred_provider)



def get_model_max_tokens(model: str) -> int:
    """
    Get the maximum allowed output tokens for a specific Claude model.
    
    Args:
        model: Claude model name
        
    Returns:
        Maximum allowed output tokens for the model
    """
    # Define maximum token limits for each model
    model_limits = {
        # Claude 3 models
        "claude-3-opus-20240229": 4096,  # Claude 3 Opus
        "claude-3-sonnet-20240229": 4096,  # Claude 3 Sonnet
        "claude-3-haiku-20240307": 4096,  # Claude 3 Haiku
        "claude-3-5-sonnet-20240620": 8192,  # Claude 3.5 Sonnet
        "claude-3-7-sonnet-20250219": 8192,  # Claude 3.7 Sonnet
        
        # Default for any unspecified model
        "default": 4000
    }
    
    # Return the limit for the specified model, or the default if not found
    return model_limits.get(model, model_limits["default"])

async def generate_with_claude(prompt: str, max_tokens: int = 4000, temperature: float = 0.7,
                           model: Optional[str] = None, use_cache: bool = True,
                           task_type: str = "content_generation", system_prompt: str = "",
                           module_number: int = None, lesson_number: int = None,
                           step_number: int = None, frequency_penalty: float = 0.0,
                           presence_penalty: float = 0.0) -> str:
    """
    Generate content using Anthropic's Claude API.
    
    Args:
        prompt: The prompt to send to Claude
        max_tokens: Maximum number of tokens to generate
        temperature: Temperature for response (0.0-1.0)
        model: Claude model to use
        use_cache: Whether to cache responses
        task_type: Type of task for logging purposes
        system_prompt: Optional system prompt to guide Claude's behavior
        module_number: Module number if available (for logging purposes)
        lesson_number: Lesson number if available (for logging purposes)
        step_number: Step number if available (for logging purposes)
        
    Returns:
        The generated response content as a string
    """
    # Import timing and logging utilities
    import inspect
    import os
    from .ai_logger import AILogEnhancer
    
    # Get the name of the calling function and its caller
    calling_function = "unknown_function"
    calling_context = ""
    
    # Get the call stack
    frame = inspect.currentframe()
    try:
        # Go back one frame to get the immediate caller
        if frame and frame.f_back:
            calling_function = frame.f_back.f_code.co_name
            
            # Go back one more frame to get the higher-level context
            if frame.f_back.f_back:
                context_frame = frame.f_back.f_back
                context_function = context_frame.f_code.co_name
                context_file = os.path.basename(context_frame.f_code.co_filename)
                
                # If the call is from an A/B testing or other special context, include it
                if context_function in ["_call_anthropic_with_ab_testing", "generate_lesson_content",
                                       "generate_step_content", "process_workflow"]:
                    calling_context = f"{context_file}:{context_function}"
    finally:
        # Clean up to prevent reference cycles
        del frame
    
    # Get AI-specific logger and start timing
    ai_logger = AILogEnhancer.get_ai_logger()
    start_time = time.time()
    from_cache = False

    # Log the start of the AI request
    # Determine default model if not provided
    if not model:
        if task_type and ("context" in task_type or "summary" in task_type):
            model = DEFAULT_CONTEXT_MODEL
        else:
            model = DEFAULT_MODEL

    AILogEnhancer.log_ai_request(ai_logger, model, task_type, None, use_cache)
    
    # Get API key from environment or config
    api_key = None
    
    # Try to get from environment variables
    try:
        import os
        from dotenv import load_dotenv
        
        # Try to load from the ShowupSquared directory .env file
        dotenv_path = os.path.join(str(get_project_root()), '.env')
        load_dotenv(dotenv_path)
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            logger.info("Using Claude API key from environment variables")
    except ImportError:
        logger.warning("Could not import dotenv, falling back to config")
    except Exception as e:
        logger.warning(f"Error loading from .env: {str(e)}")
    
    # If not found in environment, try config file
    if not api_key:
        try:
            from config.api_keys import ANTHROPIC_API_KEY
            api_key = ANTHROPIC_API_KEY
            if api_key:
                logger.info("Using Claude API key from config file")
        except ImportError:
            logger.error("Could not import ANTHROPIC_API_KEY from config.api_keys")
    
    # Check if we have an API key
    if not api_key:
        error_msg = "No Claude API key found in environment or config"
        logger.error(error_msg)
        
        # Log the failed API request
        end_time = time.time()
        AILogEnhancer.log_ai_response(
            ai_logger,
            model,
            "FAILED",
            end_time - start_time,
            False,
            None,
            None
        )
        # Save the failed interaction to a file
        error_response = "Error: ANTHROPIC_API_KEY not configured. Please add it to .env or config/api_keys.py"
        AILogEnhancer.save_interaction_to_file(
            prompt=prompt,
            response=error_response,
            model=model,
            function_name=calling_function,
            task_type=task_type,
            temperature=temperature,
            calling_context=calling_context,
            system_prompt=system_prompt
        )
        
        return error_response
        
    # Direct API call implementation, no batch processing

    # Re-enabled caching for cost efficiency
    # Check if we should use the cache
    use_cache_flag = True
    if not use_cache:
        logger.info("Caching explicitly disabled for this request")
        use_cache_flag = False

    # Make API request
    headers = {
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "x-api-key": api_key,
    }
    
    # Update API version for Claude 3 models
    if model.startswith("claude-3"):
        # Claude 3 models require the newer API version
        headers["anthropic-version"] = "2023-06-01"
    
    # Validate and adjust max_tokens based on model limits
    model_max_tokens = get_model_max_tokens(model)
    if max_tokens > model_max_tokens:
        logger.warning(f"Requested max_tokens ({max_tokens}) exceeds model limit for {model}. Adjusting to {model_max_tokens}.")
        max_tokens = model_max_tokens
    
    # Log API request (excluding API key)
    log_headers = headers.copy()
    log_headers["x-api-key"] = "********"  # Mask the API key in logs
    logger.info(f"Calling Claude API: model={model}, max_tokens={max_tokens}, temperature={temperature}")
    
    # Construct the request payload according to Claude API specifications
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    # Add system prompt if provided - Claude API expects it at the top level
    if system_prompt:
        data["system"] = system_prompt
        
    # Log the request structure (without sensitive data)
    logger.debug(f"Claude API request structure: {json.dumps({k: ('...' if k in ['messages', 'system'] else v) for k, v in data.items()})}")
    # Log the first 1000 characters of the prompt for debugging
    logger.debug(f"Prompt first 1000 chars: {prompt[:1000]}")
    # Log the first 1000 characters of the system prompt for debugging
    if system_prompt:
        logger.debug(f"System prompt first 1000 chars: {system_prompt[:1000]}")
    api_start_time = time.time()
    try:
        # Use aiohttp for async HTTP requests
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=120  # 2-minute timeout
            ) as response:
                response_text = await response.text()
                
                # Check for errors
                if response.status >= 400:
                    error_msg = f"Claude API error: {response.status}, message='{response_text}', url='{response.url}'"
                    logger.error(error_msg)
                    logger.error(f"Request payload causing error (excluding sensitive data): {json.dumps({k: ('...' if k in ['messages', 'system'] else v) for k, v in data.items()})}")
                    
                    # Calculate token count approximation
                    prompt_tokens = len(prompt.split()) // 3 * 4  # Very rough estimate
                    logger.error(f"Approximate prompt token count: {prompt_tokens}")
                    
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status,
                        message=response_text,
                        headers=response.headers
                    )
                    
                result = await response.json()
                
                # Extract content from response
                content = result.get("content", [{}])[0].get("text", "")
                
                # Implement proper caching to reduce API costs
                # Generate a cache key for this request
                cache_key = f"claude_{model}_{hashlib.md5((prompt + (system_prompt or '')).encode()).hexdigest()}"
                
                # Save to cache if caching is enabled
                if use_cache_flag:
                    try:
                        # Import the cache module from rag_system if available
                        from Step_generator.simplified_app.rag_system.cache_manager import cache
                        cache.set(cache_key, content)
                        logger.info(f"Saved response to cache with key: {cache_key}")
                    except ImportError:
                        # Fallback if rag_system is not available
                        logger.warning("Could not import cache module, response not cached")
                
                # Calculate token estimates for logging
                prompt_tokens = len(prompt.split()) // 3 * 4  # Rough estimate
                completion_tokens = len(content.split()) // 3 * 4 if content else 0
                
                # Calculate cost using utility function
                from .api_utils import calculate_cost
                cost = calculate_cost(model, prompt_tokens, completion_tokens)
                
                # Log the successful API response
                end_time = time.time()
                AILogEnhancer.log_ai_response(
                    ai_logger,
                    model,
                    "SUCCESS",
                    end_time - start_time,
                    False,
                    prompt_tokens + completion_tokens,
                    cost
                )
                
                # Save the interaction to a file
                AILogEnhancer.save_interaction_to_file(
                    prompt=prompt,
                    response=content,
                    model=model,
                    function_name=calling_function,
                    task_type=task_type,
                    temperature=temperature,
                    calling_context=calling_context,
                    system_prompt=system_prompt
                )
                
                # Save request and response as separate files for prompt engineering review
                save_api_logs_to_files(
                    prompt=prompt,
                    response=content,
                    module_number=module_number,
                    lesson_number=lesson_number,
                    step_number=step_number,
                    function_type=task_type
                )
                    
                return content
                
    except aiohttp.ClientResponseError as e:
        error_msg = f"Claude API error: {e.status}, message='{e.message}', url='{e.request_info.url}'"
        logger.error(error_msg)
        logger.error(f"Request payload causing error (excluding sensitive data): {json.dumps({k: ('...' if k in ['messages', 'system'] else v) for k, v in data.items()})}")
        
        # Calculate token count approximation
        prompt_tokens = len(prompt.split()) // 3 * 4  # Very rough estimate
        logger.error(f"Approximate prompt token count: {prompt_tokens}")
        
        # Log the failed API response
        end_time = time.time()
        AILogEnhancer.log_ai_response(
            ai_logger,
            model,
            "FAILED",
            end_time - start_time,
            False,
            None,
            None
        )
        
        # Save the failed interaction to a file
        error_response = f"Error generating content with Claude API: {error_msg}"
        AILogEnhancer.save_interaction_to_file(
            prompt=prompt,
            response=error_response,
            model=model,
            function_name=calling_function,
            task_type=task_type,
            temperature=temperature,
            calling_context=calling_context,
            system_prompt=system_prompt
        )
        
        logger.error(error_msg)
        return error_response
    except Exception as e:
        error_msg = f"Unexpected error calling Claude API: {str(e)}"
        
        # Log the failed API response
        end_time = time.time()
        AILogEnhancer.log_ai_response(
            ai_logger,
            model,
            "FAILED",
            end_time - start_time,
            False,
            None,
            None
        )
        
        # Save the failed interaction to a file
        error_response = f"Error generating content with Claude API: {error_msg}"
        AILogEnhancer.save_interaction_to_file(
            prompt=prompt,
            response=error_response,
            model=model,
            function_name=calling_function,
            task_type=task_type,
            temperature=temperature,
            calling_context=calling_context,
            system_prompt=system_prompt
        )
        
        logger.error(error_msg)
        return error_response


def save_api_logs_to_files(prompt: str, response: str, module_number=None, lesson_number=None,
                           step_number=None, function_type="general"):
    """
    Save API request and response as separate text files.
    
    Args:
        prompt: The prompt sent to the API
        response: The response received from the API
        module_number: Module number if available
        lesson_number: Lesson number if available
        step_number: Step number if available
        function_type: Type of function (review, ai-detection, etc.)
    """
    # Import necessary modules
    
    # Get logger
    global logger
    if not logger:
        logger = logging.getLogger("api_client")
    
    # Log that we're saving files
    logger.info(f"=== SAVING API LOGS: function_type={function_type}, prompt_length={len(prompt)}, response_length={len(response)} ===")
    
    # Create logs directory if it doesn't exist
    log_dir = "C:/Users/User/Desktop/ShowupSquaredV4/logs"
    logger.info(f"Saving API logs to directory: {log_dir}")
    
    # Create directory if it doesn't exist
    try:
        os.makedirs(log_dir, exist_ok=True)
        logger.info(f"Ensured directory exists: {log_dir}")
    except Exception as e:
        logger.error(f"Error creating directory {log_dir}: {str(e)}")
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Build file name prefix with available context
    file_prefix = ""
    if module_number is not None:
        file_prefix += f"module-{module_number}_"
    if lesson_number is not None:
        file_prefix += f"lesson-{lesson_number}_"
    if step_number is not None:
        file_prefix += f"step-{step_number}_"
    file_prefix += f"{function_type}"
    
    # Create file paths
    request_file = os.path.join(log_dir, f"{file_prefix}_request_{timestamp}.txt")
    response_file = os.path.join(log_dir, f"{file_prefix}_response_{timestamp}.txt")
    
    # Save request to file
    try:
        with open(request_file, 'w', encoding='utf-8') as f:
            f.write(prompt)
        logger.info(f"Successfully saved API request to: {request_file}")
    except Exception as e:
        logger.error(f"Error saving API request to file: {str(e)}")
    
    # Save response to file
    try:
        with open(response_file, 'w', encoding='utf-8') as f:
            f.write(response)
        logger.info(f"Successfully saved API response to: {response_file}")
    except Exception as e:
        logger.error(f"Error saving API response to file: {str(e)}")
    
    # Log completion
    logger.info(f"=== COMPLETED SAVING API LOGS: {function_type} ===")


async def generate_with_llm(prompt: str, task_type: str = "content_creation",
                      complexity: str = "standard", max_tokens: int = 4000,
                      temperature: float = 0.7, use_cache: bool = True) -> str:
    """
    Generate content using the best available LLM based on the task requirements.
    
    This function automatically selects the appropriate model based on task complexity.
    
    Args:
        prompt: The prompt to send to the LLM
        task_type: Type of task (summarization, coding, content_creation, etc.)
        complexity: Task complexity (basic, standard, advanced)
        max_tokens: Maximum number of tokens to generate
        temperature: Temperature setting (0.0-1.0)
        use_cache: Whether to cache responses
        
    Returns:
        Generated content as a string
    """
    # Create a default API client and use it for generation
    client = get_api_client()
    return await client.generate(prompt, task_type, complexity, max_tokens, temperature, use_cache)

# Define __all__ to explicitly control what's exported
__all__ = [
    'SmartModelSelector',
    'ApiClient',
    'get_api_client',
    'generate_with_claude',
    'generate_with_llm',
    'PromptTemplateSystem'
]