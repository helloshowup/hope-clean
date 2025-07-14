import os
import json
from pathlib import Path


def get_project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parents[2]


def _load_settings() -> dict:
    settings_file = get_project_root() / "path_settings.json"
    if settings_file.exists():
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


_SETTINGS = _load_settings()


def reload_settings() -> None:
    """Reload path settings from disk."""
    global _SETTINGS
    _SETTINGS = _load_settings()


def get_log_base_dir() -> Path:
    """Return the base directory for log files."""
    env_path = os.getenv("SHOWUP_LOG_DIR")
    if env_path:
        return Path(env_path)
    if _SETTINGS.get("log_dir"):
        return Path(_SETTINGS["log_dir"])
    return get_project_root() / "showup_core" / "data" / "logs"


def get_template_base_dir() -> Path:
    """Return the base directory for templates."""
    env_path = os.getenv("SHOWUP_TEMPLATE_DIR")
    if env_path:
        return Path(env_path)
    if _SETTINGS.get("template_dir"):
        return Path(_SETTINGS["template_dir"])
    return get_project_root() / "templates"
