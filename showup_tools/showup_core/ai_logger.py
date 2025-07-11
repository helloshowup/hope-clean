"""
AI logging utilities for ShowupSquared system.

This module provides utilities for enhanced logging of AI interactions,
making it easier to track and debug AI-related operations.
"""

import logging
import os
import datetime

class AILogEnhancer:
    """Helper class to enhance AI-related logging with consistent formatting"""
    
    @staticmethod
    def get_ai_logger(name="ai_interaction"):
        """Get a logger instance for AI interactions"""
        logger = logging.getLogger(name)
        return logger
    
    @staticmethod
    def log_ai_request(logger, model, task_type, complexity=None, use_cache=True):
        """Log the start of an AI request with proper formatting"""
        logger.info(f"[AI-REQUEST-START] Model: {model} | Task: {task_type} | Complexity: {complexity} | Cache: {'Enabled' if use_cache else 'Disabled'}")
    
    @staticmethod
    def log_ai_response(logger, model, status, duration, from_cache=False, token_count=None, cost=None):
        """Log the completion of an AI request with proper formatting"""
        cache_status = "CACHED" if from_cache else "LIVE"
        token_info = f"| Tokens: {token_count}" if token_count else ""
        cost_info = f"| Cost: ${cost:.4f}" if cost is not None else ""
        logger.info(f"[AI-RESPONSE-END] Model: {model} | Status: {status} | Source: {cache_status} | Duration: {duration:.2f}s {token_info} {cost_info}")
    
    @staticmethod 
    def log_ai_testing(logger, strategy, quality_score, selected=False):
        """Log A/B testing results with proper formatting"""
        logger.info(f"[AI-TESTING] Strategy: {strategy} | Quality: {quality_score:.1f}/100 | Selected: {'YES' if selected else 'no'}")
    
    @staticmethod
    def log_ai_detection(logger, content_type, ai_probability, improved=False):
        """Log AI detection results with proper formatting"""
        status = "IMPROVED" if improved else "UNCHANGED"
        logger.info(f"[AI-DETECTION] Type: {content_type} | AI Probability: {ai_probability:.2f} | Status: {status}")

    @staticmethod
    def log_cache_operation(logger, operation, cache_key, success=True):
        """Log cache operations with proper formatting"""
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"[AI-CACHE-{operation.upper()}] Key: {cache_key} | Status: {status}")

    @staticmethod
    def log_ab_testing_start(logger, task_type, complexity_level):
        """Log the start of A/B testing"""
        logger.info(f"[AI-AB-TESTING-START] Task: {task_type} | Complexity: {complexity_level}")
    
    @staticmethod
    def log_ab_strategy_start(logger, strategy_index, total_strategies, strategy_name, temperature):
        """Log the start of testing a specific A/B strategy"""
        logger.info(f"[AI-AB-STRATEGY-START] {strategy_index}/{total_strategies}: {strategy_name} (temp={temperature})")
    
    @staticmethod
    def log_ab_testing_end(logger, selected_strategy, score):
        """Log the end of A/B testing with results"""
        logger.info(f"[AI-AB-TESTING-END] Selected: {selected_strategy} | Score: {score:.1f}/100")
    
    @staticmethod
    def log_detection_start(logger, content_type, sensitivity):
        """Log the start of AI detection process"""
        logger.info(f"[AI-DETECTION-START] Type: {content_type} | Sensitivity: {sensitivity}")
    
    @staticmethod
    def log_detection_end(logger, initial_probability, final_probability=None):
        """Log the end of AI detection process"""
        if final_probability is not None:
            logger.info(f"[AI-DETECTION-END] Content improved: AI probability reduced from {initial_probability:.2f} to {final_probability:.2f}")
        else:
            logger.info(f"[AI-DETECTION-END] No improvement needed: AI probability {initial_probability:.2f}")
    
    @staticmethod
    def save_interaction_to_file(prompt, response, model, function_name, task_type=None, temperature=None,
                               calling_context=None, system_prompt=None):
        """
        Save AI interaction to a text file with limited character counts.
        
        Args:
            prompt: The prompt sent to the API
            response: The response received from the API
            model: The model used for the interaction
            function_name: Name of the function that called the API
            task_type: Type of task (optional)
            temperature: Temperature setting used (optional)
            calling_context: Context of the calling function (optional)
            system_prompt: System prompt used for the interaction (optional)
        """
        # Create directory if it doesn't exist
        log_dir = "C:/Users/User/Desktop/ShowupSquaredV4/data/logs/api_calls_responses"
        print(f"Saving AI interaction to directory: {log_dir}")
        
        # Create nested directories if they don't exist
        try:
            os.makedirs(log_dir, exist_ok=True)
            print(f"Ensured directory exists: {log_dir}")
        except Exception as e:
            print(f"Error creating directory {log_dir}: {str(e)}")
        os.makedirs(log_dir, exist_ok=True)
        
        # Generate timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create filename with context if available
        if calling_context:
            filename = f"{calling_context}_{function_name}_{timestamp}.txt"
        else:
            filename = f"{function_name}_{timestamp}.txt"
        filepath = os.path.join(log_dir, filename)
        
        # Keep full prompt but truncate response
        max_response_chars = 500
        
        # No truncation for prompt
        truncated_prompt = prompt
        
        # Truncate only the response
        truncated_response = response[:max_response_chars]
        if len(response) > max_response_chars:
            truncated_response += "... [truncated]"
        
        # Format content
        system_prompt_section = ""
        if system_prompt:
            system_prompt_section = f"--- SYSTEM PROMPT ---\n{system_prompt}\n\n"
            
        content = f"""TIMESTAMP: {timestamp}
MODEL: {model}
TASK TYPE: {task_type or 'Not specified'}
TEMPERATURE: {temperature or 'Not specified'}
CALLING FUNCTION: {function_name}
CONTEXT: {calling_context or 'Direct call'}

{system_prompt_section}--- PROMPT ---
{truncated_prompt}

--- RESPONSE ---
{truncated_response}
"""
        
        # Save to file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Successfully saved AI interaction to: {filepath}")
        except Exception as e:
            # Log error but don't interrupt normal operation
            print(f"Error saving AI interaction to file: {str(e)}")