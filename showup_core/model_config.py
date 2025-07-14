"""Model configuration module for AI API models."""

import json
import pathlib

_CACHE = None


def load_model_config():
    """Load model configuration from JSON file (cached)."""
    global _CACHE
    if _CACHE is None:
        path = pathlib.Path(__file__).parent.parent / "config" / "model_settings.json"
        _CACHE = json.loads(path.read_text())
    return _CACHE


# Available Claude models
CLAUDE_MODELS = [
    {
        "id": "claude-3-7-sonnet-20250219",
        "display_name": "Claude 3.7 Sonnet",
        "description": "Latest Sonnet model with improved capabilities",
    },
    {
        "id": "claude-3-5-sonnet-20240620",
        "display_name": "Claude 3.5 Sonnet",
        "description": "Balanced model for most tasks",
    },
]

# Default model for general content generation
DEFAULT_MODEL = "claude-3-7-sonnet-20250219"

# Default model for building context or summaries
DEFAULT_CONTEXT_MODEL = "claude-3-5-sonnet-20240620"

# Default model specifically for planning tasks
DEFAULT_PLANNING_MODEL = DEFAULT_CONTEXT_MODEL


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
        "description": "OpenAI's most powerful model for complex tasks",
    },
    {
        "id": "openai/o3-2025-04-16",
        "display_name": "OpenAI O3",
        "description": "Next generation OpenAI model",
    },
    {
        "id": "openai/o3-mini-2025-01-31",
        "display_name": "OpenAI O3 Mini",
        "description": "Smaller O3 variant",
    },
]


def get_model_provider(model_id):
    """Determine the provider (Claude or OpenAI) for a given model ID."""
    if any(model["id"] == model_id for model in CLAUDE_MODELS):
        return "claude"
    elif (
        any(model["id"] == model_id for model in OPENAI_MODELS)
        or model_id.startswith("openai/")
        or model_id.startswith("gpt-")
    ):
        return "openai"
    return "unknown"


def get_available_models():
    """Get a list of all available models from both providers."""
    return CLAUDE_MODELS + OPENAI_MODELS
