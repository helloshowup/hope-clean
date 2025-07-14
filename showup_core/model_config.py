"""Model configuration module for AI API models."""

import json
import pathlib
from .config import get_project_root
import logging

_CACHE = None


def load_user_model_settings() -> dict:
    """Return model-related settings from the root ``user_settings.json``."""
    settings_file = get_project_root() / "user_settings.json"
    if not settings_file.exists():
        return {}

    try:
        data = json.loads(settings_file.read_text())
    except Exception as exc:  # pragma: no cover - best effort
        logging.getLogger(__name__).warning(
            "Failed to load user model settings: %s", exc
        )
        return {}

    model_keys = {
        k
        for k in data.keys()
        if k.endswith("_model") or k in {"selected_model", "initial_generation_model"}
    }
    return {k: data[k] for k in model_keys}


def load_model_config() -> dict:
    """Load base model settings and overlay any user-specific selections."""
    global _CACHE
    if _CACHE is None:
        base_path = get_project_root() / "config" / "model_settings.json"
        try:
            config = json.loads(base_path.read_text())
        except Exception as exc:  # pragma: no cover - best effort
            logging.getLogger(__name__).warning(
                "Failed to load model_settings.json: %s", exc
            )
            config = {}

        user_cfg = load_user_model_settings()
        config.update(user_cfg)
        _CACHE = config

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
        "id": "gpt-4o-2024-05-13",
        "display_name": "GPT-4o (2024-05-13)",
        "description": "OpenAI GPT-4o release from May 2024",
    },
    {
        "id": "gpt-4o",
        "display_name": "GPT-4o",
        "description": "OpenAI's optimized model",
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
