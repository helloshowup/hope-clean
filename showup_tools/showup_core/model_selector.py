"""
Smart Model Selector module for optimizing model selection.

This module provides a tiered model selection system that chooses
the most appropriate model based on task complexity, token usage estimates,
and budget constraints.
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple

from .config import setup_logging

# Initialize logger
logger = logging.getLogger("model_selector")
setup_logging()  # Configure the root logger

class SmartModelSelector:
    """
    A system for selecting the optimal model based on task complexity.
    
    This class implements a tiered model selection system that:
    - Uses smaller models for simple tasks (claude-3-haiku for formatting, snippets)
    - Uses medium models for standard tasks (claude-3-5-sonnet for documentation, functions)
    - Uses larger models for complex tasks (claude-3-7-sonnet for algorithms, refactoring)
    - Estimates token usage and API costs before making API calls
    - Respects token budget constraints
    """
    
    def __init__(self, cost_optimization_enabled: bool = True):
        """
        Initialize the SmartModelSelector.
        
        Args:
            cost_optimization_enabled: Whether to optimize for cost (default: True)
        """
        self.logger = logger
        self.cost_optimization_enabled = cost_optimization_enabled
        
        # Define available models and their capabilities
        self.models = {
            "claude-3-haiku-20240307": {
                "description": "Small, fast model for simple tasks",
                "complexity_tier": 1,
                "cost_per_1k_input_tokens": 0.25,
                "cost_per_1k_output_tokens": 1.25,
                "context_window": 200000,
                "strengths": ["formatting", "simple snippets", "quick responses"],
                "ideal_for": ["short summaries", "basic Q&A", "simple text formatting"]
            },
            "claude-3-5-sonnet-20240620": {
                "description": "Balanced model for medium complexity tasks",
                "complexity_tier": 2,
                "cost_per_1k_input_tokens": 3.0,
                "cost_per_1k_output_tokens": 15.0,
                "context_window": 200000,
                "strengths": ["standard functions", "documentation", "detailed responses"],
                "ideal_for": ["code review", "documentation", "standard programming tasks"]
            },
            "claude-3-7-sonnet-20250219": {
                "description": "Large model for complex tasks",
                "complexity_tier": 3,
                "cost_per_1k_input_tokens": 15.0,
                "cost_per_1k_output_tokens": 75.0, 
                "context_window": 200000,
                "strengths": ["complex reasoning", "algorithms", "sophisticated code"],
                "ideal_for": ["algorithm design", "refactoring", "complex problem solving"]
            }
        }
        
        # Default model for when complexity is unclear
        self.default_model = "claude-3-haiku-20240307"
        
        # Token budget constraints
        self.token_budget = None  # No budget constraints by default
        
        # Token usage tracking
        self.token_usage = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "requests": []
        }
        
        logger.info("SmartModelSelector initialized with cost optimization " + 
                  ("enabled" if cost_optimization_enabled else "disabled"))
    
    def select_model(
        self,
        prompt: str,
        task_type: Optional[str] = None,
        force_model: Optional[str] = None,
        max_expected_tokens: int = 1000
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Select the optimal model for a given prompt and task.
        
        Args:
            prompt: The prompt text to analyze
            task_type: Optional task type for better selection
            force_model: Optional model to force selection of
            max_expected_tokens: Maximum expected response tokens
            
        Returns:
            Tuple of (selected_model_name, model_info)
        """
        # If a model is forced, use it if valid
        if force_model and force_model in self.models:
            logger.info(f"Using forced model selection: {force_model}")
            return force_model, self.models[force_model]
        
        # If cost optimization is disabled, use the default high-quality model
        if not self.cost_optimization_enabled:
            logger.info("Cost optimization disabled, using default high-quality model: claude-3-7-sonnet-20250219")
            return "claude-3-7-sonnet-20250219", self.models["claude-3-7-sonnet-20250219"]
        
        # Estimate task complexity
        complexity_score = self._estimate_complexity(prompt, task_type)
        
        # Estimate token usage and cost
        input_tokens = self._estimate_tokens(prompt)
        estimated_cost = self._estimate_cost(input_tokens, max_expected_tokens, "claude-3-5-sonnet-20240620")
        
        # Select model based on complexity score and hints
        selected_model = self._select_by_complexity(
            complexity_score, task_type, max_expected_tokens
        )
        
        # Check if the selected model fits within budget constraints
        if self.token_budget is not None:
            model_cost = self._estimate_cost(input_tokens, max_expected_tokens, selected_model)
            if model_cost > self.token_budget:
                logger.info(f"Selected model {selected_model} exceeds budget, downgrading model")
                # Downgrade model if needed to fit budget
                selected_model = self._downgrade_model(selected_model, input_tokens, max_expected_tokens)
        
        # Log the selection decision
        selection_reason = f"Task complexity score: {complexity_score}/10"
        if task_type:
            selection_reason += f", Task type: {task_type}"
        selection_reason += f", Input tokens: ~{input_tokens}"
        
        logger.info(f"Selected model {selected_model} ({selection_reason})")
        
        return selected_model, self.models[selected_model]
    
    def _estimate_complexity(self, prompt: str, task_type: Optional[str] = None) -> int:
        """
        Estimate the complexity of a task on a scale of 1-10.
        
        Args:
            prompt: The prompt text to analyze
            task_type: Optional task type for better estimation
            
        Returns:
            Complexity score from 1-10
        """
        # Start with a base complexity score
        complexity = 5  # Medium complexity by default
        
        # Task type-based adjustments
        task_complexity = {
            "formatting": 1,
            "simple_snippet": 2,
            "documentation": 4,
            "function_implementation": 5,
            "code_review": 6,
            "refactoring": 7,
            "algorithm_design": 8,
            "debugging": 8,
            "system_design": 9,
            "optimization": 9
        }
        
        if task_type and task_type in task_complexity:
            complexity = task_complexity[task_type]
            logger.info(f"Task type '{task_type}' has base complexity score: {complexity}")
        
        # Adjust based on prompt length
        prompt_length = len(prompt)
        if prompt_length > 10000:
            complexity += 2
        elif prompt_length > 5000:
            complexity += 1
        elif prompt_length < 1000:
            complexity -= 1
        
        # Adjust based on code block count
        code_blocks = len(re.findall(r'```', prompt)) // 2  # Each block has opening and closing
        if code_blocks > 5:
            complexity += 1
        elif code_blocks > 10:
            complexity += 2
        
        # Check for algorithm-related keywords
        algorithm_keywords = [
            "algorithm", "complexity", "optimization", "efficient", 
            "performance", "big o", "time complexity", "space complexity"
        ]
        if any(keyword in prompt.lower() for keyword in algorithm_keywords):
            complexity += 1
            logger.info("Complexity increased due to algorithm-related keywords")
        
        # Check for specialized terminology
        specialized_terms = [
            "concurrency", "multithreading", "parallelism", 
            "distributed", "recursion", "dynamic programming",
            "machine learning", "neural network", "blockchain"
        ]
        if any(term in prompt.lower() for term in specialized_terms):
            complexity += 1
            logger.info("Complexity increased due to specialized terminology")
        
        # Cap complexity between 1-10
        complexity = max(1, min(10, complexity))
        
        logger.info(f"Estimated task complexity: {complexity}/10")
        return complexity
    
    def _select_by_complexity(
        self,
        complexity_score: int,
        task_type: Optional[str] = None,
        token_budget: Optional[int] = None,
    ) -> str:
        """Select model based on complexity score and additional hints."""
        if task_type in {"context_generation", "summary"}:
            return "claude-3-haiku-20240307"

        if token_budget is not None and token_budget <= 4000:
            return "claude-3-haiku-20240307"

        if complexity_score <= 3:
            # Simple tasks use the smallest model
            return "claude-3-haiku-20240307"
        if complexity_score >= 8:
            # Complex tasks use the largest model
            return "claude-3-7-sonnet-20250219"
        # Medium complexity tasks use the balanced model
        return "claude-3-5-sonnet-20240620"
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for a given text.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Simple estimate: ~4 characters per token for English text
        # This is a rough approximation, actual tokenization varies by model
        char_count = len(text)
        estimated_tokens = char_count // 4
        
        # Add 10% buffer for safety
        estimated_tokens = int(estimated_tokens * 1.1)
        
        logger.info(f"Estimated token count for text: {estimated_tokens} (chars: {char_count})")
        return estimated_tokens
    
    def _estimate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """
        Estimate cost for a given model and token usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name
            
        Returns:
            Estimated cost in USD
        """
        if model not in self.models:
            logger.warning(f"Unknown model: {model}, using default for cost estimation")
            model = self.default_model
        
        model_info = self.models[model]
        input_cost = (input_tokens / 1000) * model_info["cost_per_1k_input_tokens"]
        output_cost = (output_tokens / 1000) * model_info["cost_per_1k_output_tokens"]
        total_cost = input_cost + output_cost
        
        logger.info(f"Estimated cost for {model}: ${total_cost:.4f} "
                   f"(input: ${input_cost:.4f}, output: ${output_cost:.4f})")
        
        return total_cost
    
    def _downgrade_model(self, current_model: str, input_tokens: int, output_tokens: int) -> str:
        """
        Downgrade to a cheaper model to fit budget constraints.
        
        Args:
            current_model: Currently selected model
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Downgraded model name
        """
        if current_model == "claude-3-7-sonnet-20250219":
            return "claude-3-5-sonnet-20240620"
        elif current_model == "claude-3-5-sonnet-20240620":
            return "claude-3-haiku-20240307"
        
        # If already using the cheapest model, just return it
        return "claude-3-haiku-20240307"
    
    def set_token_budget(self, budget: Optional[float]) -> None:
        """
        Set token budget constraint.
        
        Args:
            budget: Maximum cost allowed per request in USD, or None for no constraint
        """
        self.token_budget = budget
        logger.info(f"Set token budget constraint: ${budget if budget is not None else 'None'}")
    
    def track_usage(self, input_tokens: int, output_tokens: int, model: str) -> None:
        """
        Track token usage and costs for a request.
        
        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            model: Model used for the request
        """
        # Calculate cost
        cost = self._estimate_cost(input_tokens, output_tokens, model)
        
        # Update tracking
        self.token_usage["total_input_tokens"] += input_tokens
        self.token_usage["total_output_tokens"] += output_tokens
        self.token_usage["total_cost"] += cost
        
        # Add request details
        self.token_usage["requests"].append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost
        })
        
        logger.info(f"Tracked usage: {input_tokens} input, {output_tokens} output tokens "
                   f"(${cost:.4f}) using {model}")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get current token usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            "total_input_tokens": self.token_usage["total_input_tokens"],
            "total_output_tokens": self.token_usage["total_output_tokens"],
            "total_cost": self.token_usage["total_cost"],
            "request_count": len(self.token_usage["requests"]),
            "average_request_cost": (
                self.token_usage["total_cost"] / len(self.token_usage["requests"])
                if self.token_usage["requests"] else 0
            )
        }
    
    def reset_usage_tracking(self) -> None:
        """Reset usage tracking statistics."""
        self.token_usage = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "requests": []
        }
        logger.info("Reset usage tracking statistics")