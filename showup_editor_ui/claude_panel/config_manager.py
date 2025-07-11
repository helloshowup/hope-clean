#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration Manager for the Output Library Editor
Handles loading, saving, and accessing application settings
"""

import os
import json
import logging
from pathlib import Path
from .path_utils import get_project_root

# Get logger
logger = logging.getLogger("output_library_editor")

class ConfigManager:
    """Manages application configuration settings"""
    
    # Default configuration values
    showup_root = Path(
        os.environ.get("SHOWUP_ROOT", get_project_root())
    )

    DEFAULT_CONFIG = {
        "library_path": str(showup_root / "showup-library" / "library"),
        "recent_files": [],
        "recent_projects": [],
        "library_prompts_path": str(
            showup_root / "showup-library" / "prompts"
        ),
    }
    
    def __init__(self):
        # Path to the config file
        self.base_dir = str(get_project_root())
        self.config_file = os.path.join(self.base_dir, "settings.json")
        
        # Current configuration (loaded from file or defaults)
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file or create with defaults if missing."""
        try:
            config = self.load_settings()
        except FileNotFoundError:
            config = self.DEFAULT_CONFIG.copy()
            self._save_config(config)
        except Exception as e:  # noqa: BLE001 - log unexpected failures
            logger.error(f"Error loading config file: {str(e)}")
            config = self.DEFAULT_CONFIG.copy()

        for key, value in self.DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value

        return config

    def load_settings(self) -> dict:
        """Load settings while guarding against duplicate files."""
        root_file = os.path.join(self.base_dir, "settings.json")
        ui_file = os.path.join(self.base_dir, "showup-editor-ui", "settings.json")

        existing = [p for p in (root_file, ui_file) if os.path.exists(p)]
        if len(existing) > 1:
            raise ValueError(
                f"Duplicate settings.json files found: {existing[0]} and {existing[1]}"
            )
        if not existing:
            raise FileNotFoundError("settings.json not found")

        with open(existing[0], "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _save_config(self, config=None):
        """Save configuration to file"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error saving config file: {str(e)}")
            return False
    
    def get_setting(self, key):
        """Get a setting by key"""
        return self.config.get(key, self.DEFAULT_CONFIG.get(key))
    
    def set_setting(self, key, value):
        """Set a setting and save to file"""
        self.config[key] = value
        return self._save_config()
    
    def get_library_path(self):
        """Get the library path setting"""
        return self.get_setting("library_path")
    
    def set_library_path(self, path):
        """Set the library path setting"""
        return self.set_setting("library_path", path)

# Create a singleton instance
config_manager = ConfigManager()
