from importlib import import_module

# Redirect to legacy package under showup_tools for backwards compatibility
module = import_module('showup_tools.showup_core')
for attr in getattr(module, '__all__', []):
    globals()[attr] = getattr(module, attr)
__all__ = getattr(module, '__all__', [])
from showup_tools.showup_core.api_client import generate_with_claude
