import toml
from pathlib import Path

REQUIRED = [
    "anthropic",
    "claude_api",
    "openai",
    "markdown",
    "python-docx",
    "Pillow",
    "aiohttp",
    "azure-cognitiveservices-speech",
]

def test_required_packages_present():
    data = toml.loads(Path('pyproject.toml').read_text())
    deps = set(data.get('project', {}).get('dependencies', []))
    missing = [pkg for pkg in REQUIRED if pkg not in deps]
    assert not missing, f"Missing packages: {missing}"
