import json
import os
import sys
import logging
import copy # Import deepcopy
from pathlib import Path
from PySide6.QtCore import QStandardPaths, QSettings


def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and PyInstaller."""
    if getattr(sys, 'frozen', False):
        # Running as packaged exe
        base_path = sys._MEIPASS
    else:
        # Running in dev - go up from app/core to project root
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)

# Define default settings structure (using the NEW nested format)
DEFAULT_CONFIG = {
    "api_keys": {
        "deepseek_api_key": "", # Use consistent key names here too
        "openrouter_api_key": "",
        "groq_api_key": "",
        "siliconflow_api_key": "",
        "google_api_key": "",
        "dashscope_api_key": "" # Add dashscope key here too
    },
    "api_urls": {
        "Google": "",
        "OpenAI": "",
        "DeepSeek": "",
        "OpenRouter": "",
        "Groq": "",
        "SiliconFlow": "",
        "DashScope": "",
        "MiniMax": ""
    },
    "default_models": {
         # Use the same structure as create_default_config for consistency
        "DeepSeek": {
            "default": "deepseek-chat",
            "available": ["deepseek-chat", "deepseek-coder", "deepseek-r1", "deepseek-r1-tapex"]
        },
        "OpenRouter": {
            "default": "mistralai/devstral-2512:free",
            "available": [
                "mistralai/devstral-2512:free",
                "x-ai/grok-3-mini-beta",
                "x-ai/grok-3-1212",
                "google/gemini-pro-1.5",
                "anthropic/claude-3-opus",
                "anthropic/claude-3-sonnet",
                "anthropic/claude-3-haiku",
                "openai/gpt-4o",
                "openai/gpt-4o-mini",
                "meta-llama/llama-3.1-405b-instruct",
                "meta-llama/llama-3.1-70b-instruct",
                "microsoft/wizardlm-2-8x22b"
            ]
        },
        "Groq": {
            "default": "moonshotai/kimi-k2-instruct",
            "available": [
                "moonshotai/kimi-k2-instruct",
                "moonshotai/kimi-k2-instruct-0905",
                "llama-3.1-70b-versatile",
                "llama-3.1-8b-instant",
                "llama3-70b-8192",
                "llama3-8b-8192",
                "mixtral-8x7b-32768",
                "gemma-7b-it",
                "gemma2-9b-it"
            ]
        },
        "SiliconFlow": {
            "default": "deepseek-ai/DeepSeek-V3.1-Terminus",
            "available": [
                "deepseek-ai/DeepSeek-V3.1-Terminus",
                "Qwen/Qwen2.5-72B-Instruct",
                "Qwen/Qwen2.5-7B-Instruct",
                "deepseek-ai/DeepSeek-V3",
                "THUDM/glm-4-9b-chat",
                "Qwen/Qwen2.5-Coder-32B-Instruct"
            ]
        },
        "Google": {
            "default": "gemini-2.5-flash-native-audio-preview-12-2025",
            "available": [
                "gemini-2.5-flash-native-audio-preview-12-2025",
                "gemini-2.5-flash-preview-09-2025",
                "gemini-2.0-flash-exp",
                "gemini-2.5-flash-002",
                "gemini-2.5-pro-002",
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gemini-1.5-pro-002",
                "gemini-1.5-flash-002",
                "gemini-1.5-pro",
                "gemini-1.5-flash"
            ]
        },
        "DashScope": {
            "default": "qwen3-omni-flash-realtime-2025-12-01",
            "available": [
                "qwen3-omni-flash-realtime-2025-12-01",
                "qwen3-omni-flash-realtime-2025-09-15",
                "qwen3-omni-realtime-flash",
                "qwen-omni-turbo-realtime",
                "qwen3-omni-flash-2025-12-01",
                "qwen3.5-72b-instruct",
                "qwen2.5-72b-instruct",
                "qwen-max",
                "qwen-plus",
                "qwen-turbo"
            ]
        },
        "MiniMax": {
            "default": "abab6.5s-chat",
            "available": ["abab6.5s-chat", "minimax-01-06"]
        }
    },
    "general_settings": {
        "display_language": "English",
        "history_retention": "Keep all history",
        "log_level": "INFO"
    },
    "memory_settings": {
        "enabled": False,
        "api_url": "https://api.evermind.ai",
        "api_key": "",
        "scope_id": "",
        "remember_chat": True,
        "remember_voice_chat": True,
        "remember_recordings": False,
        "remember_podcast": True,
        "remember_tts": True,
        "store_transcript_fulltext": False,
        "temporary_session": False
    },
    "output_directory": "", # Default output path
    "tts_settings": {
        "default_voice": "zh-CN-XiaoxiaoNeural",
        "auto_play_preview": True,
        "output_folder": "output/tts"
    },
    "qwen_tts_settings": {
        "voice_design_voices": [],
        "voice_clone_voices": [],
        "default_vd_model": "qwen3-tts-vd-realtime-2025-12-16",
        "default_vc_model": "qwen3-tts-vc-realtime-2025-11-27"
    },
    "minimax": {
        "api_key": "",
        "api_url": ""
    },
    "ui_settings": {
        "theme": "default",
        "window_size": [1000, 800]
    }
}

MEMORY_SETTINGS_ALIASES = {
    "url": "api_url",
    "key": "api_key",
    "scopeId": "scope_id",
    "tempSession": "temporary_session",
    "sceneChat": "remember_chat",
    "sceneVoiceChat": "remember_voice_chat",
    "sceneTranscription": "remember_recordings",
    "scenePodcast": "remember_podcast",
    "sceneTts": "remember_tts",
    "storeTranscriptFulltext": "store_transcript_fulltext",
}

class ConfigManager:
    """Manages loading and saving application configuration."""

    def __init__(self, config_file="config.json"):
        # Config file should be next to the exe (user-editable), not in _internal
        if getattr(sys, 'frozen', False):
            # Running as packaged exe - put config next to exe
            base_path = os.path.dirname(sys.executable)
        else:
            # Running in dev
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_file = Path(os.path.join(base_path, config_file))
        self.config = {}
        self.load_config()

    def _load_config(self):
        """Legacy method alias for load_config"""
        self.load_config()

    def _create_default_config(self):
        """创建默认配置"""
        self.config = copy.deepcopy(DEFAULT_CONFIG)
        self.save_config()

    def get_config_path(self):
        """Returns the full path to the config file."""
        return str(self.config_file)

    def load_config(self):
        """Load configuration from file, merging into the default structure."""
        if not self.config_file.exists():
            logging.warning(f"Config file '{self.config_file}' not found. Creating default configuration file.")
            # Make sure self.config IS the default before saving
            self.config = copy.deepcopy(DEFAULT_CONFIG)
            self.save_config()
            return # Start with defaults

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)

            self._normalize_memory_settings_payload(loaded_config)

            # Start with a fresh default config
            merged_config = copy.deepcopy(DEFAULT_CONFIG)
            # Merge the loaded config INTO the fresh default config structure
            self._merge_configs(merged_config, loaded_config)
            # Assign the correctly merged result back to self.config
            self.config = merged_config

            logging.info("Configuration loaded and merged successfully")
            # Optional: Save back the merged config immediately to fix the file structure on disk
            # self.save_config()

        except json.JSONDecodeError as e:
            logging.error(f"Error decoding config file '{self.config_file}': {e}. Using default config and attempting to overwrite.")
            self.config = copy.deepcopy(DEFAULT_CONFIG) # Reset to default on error
            self.save_config() # Overwrite corrupted file
        except Exception as e:
            logging.error(f"Error loading/merging configuration: {e}. Using default config.", exc_info=True)
            self.config = copy.deepcopy(DEFAULT_CONFIG) # Reset to default on other errors

    def _normalize_memory_settings_payload(self, payload):
        if not isinstance(payload, dict):
            return

        memory_settings = payload.get("memory_settings")
        if not isinstance(memory_settings, dict):
            return

        normalized = {}
        for key, value in memory_settings.items():
            canonical_key = MEMORY_SETTINGS_ALIASES.get(key, key)
            normalized[canonical_key] = value
        payload["memory_settings"] = normalized

    def _merge_configs(self, target, source, current_path=""): # Added path for logging
        """Recursively merge source dict into target dict.
        Prioritizes source value if key exists in both, unless both are dicts.
        Maintains the overall structure defined in DEFAULT_CONFIG.
        """
        if not isinstance(target, dict) or not isinstance(source, dict):
            logging.warning(f"Attempted to merge non-dictionary types at path '{current_path}'. Target: {type(target)}, Source: {type(source)}")
            return # Cannot merge non-dicts

        for key, source_value in source.items():
            full_key_path = f"{current_path}.{key}" if current_path else key

            if key in target:
                target_value = target[key]

                # If both are dictionaries, recurse into them
                if isinstance(target_value, dict) and isinstance(source_value, dict):
                    self._merge_configs(target_value, source_value, full_key_path)
                # Otherwise (different types OR both not dicts), the source value wins
                # This ensures loaded strings overwrite default dicts for default_models
                else:
                    # Optional: Log the overwrite for clarity
                    if type(target_value) != type(source_value):
                         logging.debug(f"Config merge: Overwriting key '{full_key_path}' with value from loaded config. Type mismatch (Default: {type(target_value)}, Loaded: {type(source_value)}). New value: {source_value}")
                    elif target_value != source_value:
                         logging.debug(f"Config merge: Updating key '{full_key_path}' with value from loaded config. Value: {source_value}")

                    target[key] = source_value # Source value takes precedence when key exists
            else:
                 # Key exists in source but not in target (DEFAULT_CONFIG structure)
                 # Ignore keys not present in the default structure to prevent adding arbitrary data
                 logging.debug(f"Config merge: Ignoring key '{full_key_path}' from loaded file as it's not in the default structure.")
                 pass # Keep ignoring unknown keys

    def save_config(self):
        """Save configuration to file."""
        try:
            # Ensure parent directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logging.info(f"Configuration saved successfully to {self.config_file}")
        except Exception as e:
            logging.error(f"Error saving configuration to {self.config_file}: {e}", exc_info=True)
            # Consider raising e or handling it depending on context

    def get(self, key, default=None):
        """获取配置值，支持点号分隔的键"""
        try:
            keys = key.split('.')
            value = self.config
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key, value):
        """设置配置值，支持点号分隔的键"""
        keys = key.split('.')
        current = self.config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def update_setting(self, key, value):
        """Updates a configuration value using dot notation."""
        try:
            keys = key.split('.')
            d = self.config
            for k in keys[:-1]: # Navigate to the parent dictionary
                # Ensure intermediate dictionaries exist
                if k not in d or not isinstance(d[k], dict):
                    d[k] = {}
                d = d[k]
            # Set the final key's value
            d[keys[-1]] = value
            logging.debug(f"Config updated: {key} = {value}")
            return True
        except Exception as e:
            logging.error(f"Failed to update config key '{key}': {e}", exc_info=True)
            return False
