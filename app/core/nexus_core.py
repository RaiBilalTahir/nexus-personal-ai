import json
import logging
import subprocess
import sys
from pathlib import Path

from app.core.config import (
    CONFIG_FILE,
    DAEMON_FILE,
    DEFAULT_CONFIG,
    NEXUS_NAME,
    NEXUS_ROOT,
    NEXUS_VERSION,
    PROCESS_NOTES_FILE,
    get_configured_path,
    get_log_level,
    get_nexus_paths,
    load_config,
    load_raw_config,
    merge_config,
    save_config as config_save,
)
from app.core.feature_registry import FEATURE_REGISTRY


config = load_config()


def save_config(config_data=None, config_path=None):
    global config
    data_to_save = config_data if config_data is not None else config
    success = config_save(data_to_save, config_path=config_path)

    if success:
        if config_data is not None and config_path is None:
            config = data_to_save
        logger.info("Configuration saved successfully.")
        return True
    else:
        logger.error("Unable to save configuration.")
        return False


def refresh_paths():
    global INBOX_DIR
    global SEMESTER1_DIR
    global BACKUPS_DIR
    global MODULES_DIR
    global PC_CONTROL_DIR
    global COMMUNICATIONS_DIR
    global SCREEN_VISION_DIR
    global LOGS_DIR
    global LOG_FILE

    paths = get_nexus_paths()
    INBOX_DIR = paths["inbox"]
    SEMESTER1_DIR = paths["academic"]
    BACKUPS_DIR = paths["backups"]
    MODULES_DIR = paths["modules"]

    PC_CONTROL_DIR = MODULES_DIR / "pc_control"
    COMMUNICATIONS_DIR = MODULES_DIR / "communications"
    SCREEN_VISION_DIR = MODULES_DIR / "screen_vision"

    LOGS_DIR = paths["logs"]
    LOG_FILE = LOGS_DIR / "nexus_core.log"


refresh_paths()

LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=get_log_level(),
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("nexus.core")


def reload_configuration():
    global config

    config = load_config()
    refresh_paths()

    new_log_level = get_log_level()
    logger.setLevel(new_log_level)

    for handler in logger.handlers:
        handler.setLevel(new_log_level)

    logger.info("Configuration reloaded.")
    return config


def feature_enabled(feature_name, configuration=None):
    feature = FEATURE_REGISTRY.get(feature_name)

    if feature is None or feature.get("status") != "implemented":
        return False

    active_config = configuration if configuration is not None else config
    features = active_config.get("features", {})
    return features.get(feature_name, False) is True


def set_feature(feature_name, enabled, config_path=None):
    global config
    feature = FEATURE_REGISTRY.get(feature_name)

    if feature is None or feature.get("status") != "implemented":
        logger.warning(
            "Cannot change unavailable feature '%s'.",
            feature_name
        )
        return False

    if "features" not in config:
        config["features"] = {}

    config["features"][feature_name] = bool(enabled)

    if save_config(config_data=config, config_path=config_path):
        logger.info(
            "Feature '%s' changed to %s.",
            feature_name,
            bool(enabled)
        )
        return True

    return False


def inspect_project(configuration=None, root=None):
    base_root = Path(root) if root is not None else NEXUS_ROOT
    paths = get_nexus_paths(configuration=configuration, root=base_root)

    core_file = base_root / "app" / "core" / "nexus_core.py"
    pc_control_dir = paths["modules"] / "pc_control"
    communications_dir = paths["modules"] / "communications"
    screen_vision_dir = paths["modules"] / "screen_vision"

    checked_paths = {
        "Core": core_file,
        "Config": paths["config_file"],
        "Process Notes": paths["process_notes_file"],
        "Nexus Daemon": paths["daemon_file"],
        "Inbox": paths["inbox"],
        "Semester1": paths["academic"],
        "Backups": paths["backups"],
        "Modules": paths["modules"],
        "PC Control": pc_control_dir,
        "Communications": communications_dir,
        "Screen Vision": screen_vision_dir
    }

    results = {}
    for name, path in checked_paths.items():
        results[name] = path.exists()

    return results


def launch_process_notes(configuration=None, root=None):
    active_config = configuration if configuration is not None else reload_configuration()

    if not feature_enabled("process_notes", active_config):
        logger.info("Process Notes is disabled by configuration.")
        return False

    paths = get_nexus_paths(active_config, root=root)
    process_notes_path = paths["process_notes_file"]

    if not process_notes_path.exists():
        logger.error("process_notes.py was not found at %s", process_notes_path)
        return False

    logger.info("Launching process_notes.py")

    try:
        result = subprocess.run(
            [sys.executable, str(process_notes_path)],
            cwd=str(paths["root"]),
            check=False
        )

        if result.returncode == 0:
            logger.info("Process Notes finished successfully.")
            return True

        logger.error(
            "Process Notes exited with code %s.",
            result.returncode
        )
        return False

    except OSError as error:
        logger.error(
            "Unable to launch Process Notes: %s",
            error
        )
        return False


# Conversation & Command Core Coordination
_conversation_engine = None


def get_conversation_engine(
    gateway=None,
    session_store=None,
    retry_policy=None,
    reload=False,
):
    global _conversation_engine

    if _conversation_engine is None or reload:
        from app.conversation.engine import ConversationEngine, RetryPolicy
        from app.conversation.session import SessionStore
        from app.models.gateway import create_gateway

        active_gateway = gateway if gateway is not None else create_gateway(config)
        active_store = session_store if session_store is not None else SessionStore()
        active_policy = retry_policy if retry_policy is not None else RetryPolicy()

        _conversation_engine = ConversationEngine(
            gateway=active_gateway,
            session_store=active_store,
            retry_policy=active_policy,
        )

    return _conversation_engine


def execute_command(command, engine=None):
    active_engine = engine if engine is not None else get_conversation_engine()
    return active_engine.execute_command(command)


def send_chat_message(
    text,
    session_id=None,
    preferences=None,
    constraints=None,
    evidence=None,
    engine=None,
):
    from app.conversation.commands import CommandIntent, NexusCommand

    command = NexusCommand(
        text=text,
        session_id=session_id,
        intent=CommandIntent.CONVERSATION,
        preferences=preferences or {},
        constraints=tuple(constraints or ()),
        evidence=tuple(evidence or ()),
    )
    return execute_command(command, engine=engine)


def get_session_store(engine=None):
    active_engine = engine if engine is not None else get_conversation_engine()
    return active_engine.session_store


def reset_session(session_id, engine=None):
    store = get_session_store(engine=engine)
    session = store.reset_session(session_id)
    return session is not None