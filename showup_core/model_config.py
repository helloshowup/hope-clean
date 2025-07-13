"""
Model configuration module for AI API models.
"""

# Available Claude models
CLAUDE_MODELS = [
    {
        "id": "claude-3-opus-20240229",
        "display_name": "Claude 3 Opus",
        "description": "Most powerful model for complex tasks"
    },
    {
        "id": "claude-3-7-sonnet-20250219",
        "display_name": "Claude 3.7 Sonnet",
        "description": "Latest Sonnet model with improved capabilities"
    },
    {
        "id": "claude-3-5-sonnet-20240620",
        "display_name": "Claude 3.5 Sonnet",
        "description": "Balanced model for most tasks"
    },
    {
        "id": "claude-3-haiku-20240307",
        "display_name": "Claude 3 Haiku",
        "description": "Fast, efficient model for simpler tasks"
    }
]

# Default model for general content generation
DEFAULT_MODEL = "claude-3-7-sonnet-20250219"

# Default model for building context or summaries
DEFAULT_CONTEXT_MODEL = "claude-3-haiku-20240307"

def get_model_display_name(model_id):
    """Get the display name for a model ID."""
    # Check Claude models
    for model in CLAUDE_MODELS:
        if model["id"] == model_id:
            return model["display_name"]
    
    # Check OpenAI models
    for model in OPENAI_MODELS:
        if model["id"] == model_id:
            return model["display_name"]
    
    return model_id

# Available OpenAI models
OPENAI_MODELS = [
    {
        "id": "gpt-4",
        "display_name": "GPT-4",
        "description": "OpenAI's most powerful model for complex tasks"
    }
]

def get_model_provider(model_id):
    """Determine the provider (Claude or OpenAI) for a given model ID."""
    if any(model["id"] == model_id for model in CLAUDE_MODELS):
        return "claude"
    elif any(model["id"] == model_id for model in OPENAI_MODELS):
        return "openai"
    return "unknown"

def get_available_models():
    """Get a list of all available models from both providers."""
    return CLAUDE_MODELS + OPENAI_MODELS