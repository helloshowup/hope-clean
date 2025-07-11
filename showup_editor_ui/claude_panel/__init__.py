# Claude Panel Package
# This package contains modularized components of the ClaudeAIPanel class

# Import the main panel lazily so this package can be imported even if optional
# dependencies are missing when running lightweight tests.
try:
    from .main_panel import ClaudeAIPanel
except Exception:  # pragma: no cover - optional import for testing
    ClaudeAIPanel = None
