from pathlib import Path


def get_project_root() -> Path:
    """Return the project root directory as a Path object."""
    return Path(__file__).resolve().parents[2]
