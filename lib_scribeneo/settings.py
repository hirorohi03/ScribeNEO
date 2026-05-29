"""
Settings manager for ScribeNEO.
Handles loading, saving, and migrating user settings between local JSON storage
and the WebUI options system.
"""
import os
import json
from modules import shared

EXT_ROOT = os.path.dirname(os.path.realpath(__file__))
CONFIG_PATH = os.path.normpath(os.path.join(EXT_ROOT, "config.json"))

def load_config():
    """
    Load configuration from local config.json file.
    If the file does not exist, attempts to migrate settings from legacy options.
    
    Returns:
        dict: The configuration dictionary.
    """
    default_config = {
        "timeout": 30,
        "max_tokens": 512,
        "openrouter": {
            "key": "",
            "endpoint": "https://openrouter.ai/api/v1"
        },
        "huggingface": {
            "key": "",
            "endpoint": "https://router.huggingface.co/v1"
        },
        "ollama": {
            "endpoint": "http://localhost:11434",
            "keep_alive": 60
        },
        "lmstudio": {
            "endpoint": "http://localhost:1234/v1",
            "key": ""
        }
    }
    
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                # Deep merge top-level dictionaries
                for k, v in saved.items():
                    if k == "provider":
                        continue
                    if isinstance(v, dict) and k in default_config:
                        default_config[k].update(v)
                    else:
                        default_config[k] = v
                return default_config
        except Exception as e:
            print(f"[ScribeNEO] Error loading config: {e}")

    # Migration logic for legacy settings
    migration_done = False
    legacy_prefixes = ["promptscribe_", "scribeneo_"]
    
    mapping = {
        "openrouter_key": ("openrouter", "key"),
        "openrouter_endpoint": ("openrouter", "endpoint"),
        "hf_token": ("huggingface", "key"),
        "hf_key": ("huggingface", "key"),
        "hf_endpoint": ("huggingface", "endpoint"),
        "ollama_endpoint": ("ollama", "endpoint")
    }

    for prefix in legacy_prefixes:
        for suffix, target in mapping.items():
            opt_key = f"{prefix}{suffix}"
            val = getattr(shared.opts, opt_key, None)
            if val is not None and val != "":
                if isinstance(target, tuple):
                    default_config[target[0]][target[1]] = val
                else:
                    default_config[target] = val
                migration_done = True
    
    if migration_done:
        save_config(default_config)
    else:
        save_config(default_config)
    
    return default_config

def save_config(data):
    """
    Persist configuration to the local config.json file.
    
    Args:
        data (dict): The configuration data to save.
    """
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[ScribeNEO] Error saving config: {e}")
