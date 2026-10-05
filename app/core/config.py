import json
import logging
from pathlib import Path

from app.core.feature_registry import FEATURE_REGISTRY


NEXUS_NAME = "Nexus"
NEXUS_VERSION = "1.1.1"

NEXUS_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = NEXUS_ROOT / "config" / "nexus_config.json"
PROCESS_NOTES_FILE = (
    NEXUS_ROOT
    / "app"
    / "capabilities"
    / "process_notes"
    / "process_notes.py"
)
DAEMON_FILE = NEXUS_ROOT / "nexus_daemon.py"


DEFAULT_CONFIG = {
    "config_version": 1,
    "nexus": {
        "name": NEXUS_NAME,
        "version": NEXUS_VERSION,
        "environment": "local"
    },
    "ai": {
        "provider": "gemini",
        "model": "gemini-3.8-flash"
    },
    "paths": {
        "inbox": "data/inbox",
        "academic": "data/knowledge/academic/Semester1",
        "modules": "app/capabilities",
        "logs": "logs",
        "backups": "backups"
    },
    "features": {
        feature_name: feature_data["default_enabled"]
        for feature_name, feature_data in FEATURE_REGISTRY.items()
    },
    "runtime": {
        "log_level": "INFO",
        "poll_interval_seconds": 5
    }
}


def merge_config(defaults, loaded):
    if not isinstance(loaded, dict):
        return defaults.copy()

    merged = {}

    for key, default_value in defaults.items():
        loaded_value = loaded.get(key)

        if isinstance(default_value, dict):
            if isinstance(loaded_value, dict):
                merged[key] = merge_config(default_value, loaded_value)
            else:
                merged[key] = default_value.copy()
        else:
            if loaded_value is not None:
                merged[key] = loaded_value
            else:
                merged[key] = default_value

    for key, value in loaded.items():
        if key not in merged:
            merged[key] = value

    return merged


def load_raw_config(config_path=None):
    target_path = Path(config_path) if config_path is not None else CONFIG_FILE

    if not target_path.exists():
        return {}

    try:
        with target_path.open("r", encoding="utf-8") as file:
            loaded_config = json.load(file)

        if not isinstance(loaded_config, dict):
            raise ValueError("Configuration must contain a JSON object.")

        return loaded_config

    except json.JSONDecodeError as error:
        print("[WARNING] Invalid JSON configuration:", error)

    except OSError as error:
        print("[WARNING] Unable to read configuration:", error)

    except ValueError as error:
        print("[WARNING] Invalid configuration structure:", error)

    return {}


def load_config(config_path=None):
    loaded_config = load_raw_config(config_path=config_path)

    if not loaded_config:
        target_path = Path(config_path) if config_path is not None else CONFIG_FILE
        if not target_path.exists():
            print("[WARNING] Configuration file not found:", target_path)
        else:
            print("[WARNING] Using safe default configuration.")

        return merge_config(DEFAULT_CONFIG, {})

    print("[INFO] Configuration loaded successfully.")
    return merge_config(DEFAULT_CONFIG, loaded_config)


def save_config(config_data, config_path=None):
    target_path = Path(config_path) if config_path is not None else CONFIG_FILE

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with target_path.open("w", encoding="utf-8") as file:
            json.dump(config_data, file, indent=4)

        return True

    except OSError as error:
        logging.getLogger("nexus.config").error("Unable to save configuration: %s", error)
        return False


def get_configured_path(name, default_name, configuration=None, root=None):
    active_config = configuration if configuration is not None else load_config()
    base_root = Path(root) if root is not None else NEXUS_ROOT
    paths = active_config.get("paths", {})
    configured_value = paths.get(name, default_name)

    if not isinstance(configured_value, str):
        configured_value = default_name

    path = Path(configured_value)

    if not path.is_absolute():
        path = base_root / path

    return path


def get_nexus_paths(configuration=None, root=None):
    active_config = configuration if configuration is not None else load_config()
    base_root = Path(root) if root is not None else NEXUS_ROOT

    inbox = get_configured_path("inbox", "data/inbox", active_config, base_root)
    academic = get_configured_path("academic", "data/knowledge/academic/Semester1", active_config, base_root)
    modules = get_configured_path("modules", "app/capabilities", active_config, base_root)
    logs = get_configured_path("logs", "logs", active_config, base_root)
    backups = get_configured_path("backups", "backups", active_config, base_root)

    return {
        "root": base_root,
        "config_file": CONFIG_FILE,
        "inbox": inbox,
        "academic": academic,
        "modules": modules,
        "logs": logs,
        "backups": backups,
        "provenance": base_root / "data" / "provenance" / "processing_records.json",
        "process_notes_file": PROCESS_NOTES_FILE,
        "daemon_file": DAEMON_FILE,
    }


def get_log_level(configuration=None):
    active_config = configuration if configuration is not None else load_config()
    runtime = active_config.get("runtime", {})
    configured_level = runtime.get("log_level", "INFO")

    if not isinstance(configured_level, str):
        return logging.INFO

    level = getattr(logging, configured_level.upper(), None)

    if not isinstance(level, int):
        print(
            "[WARNING] Invalid log level:",
            configured_level,
            "- using INFO."
        )
        return logging.INFO

    return level
