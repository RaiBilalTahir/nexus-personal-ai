import json
import logging
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from feature_registry import FEATURE_REGISTRY


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


def load_raw_config():
    if not CONFIG_FILE.exists():
        return {}

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
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


def load_config():
    loaded_config = load_raw_config()

    if not loaded_config:
        if not CONFIG_FILE.exists():
            print("[WARNING] Configuration file not found:", CONFIG_FILE)
        else:
            print("[WARNING] Using safe default configuration.")

        return merge_config(DEFAULT_CONFIG, {})

    print("[INFO] Configuration loaded successfully.")
    return merge_config(DEFAULT_CONFIG, loaded_config)


config = load_config()


def save_config():
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

        with CONFIG_FILE.open("w", encoding="utf-8") as file:
            json.dump(config, file, indent=4)

        logger.info("Configuration saved successfully.")
        return True

    except OSError as error:
        logger.error("Unable to save configuration: %s", error)
        return False


def get_configured_path(name, default_name):
    paths = config.get("paths", {})
    configured_value = paths.get(name, default_name)

    if not isinstance(configured_value, str):
        configured_value = default_name

    path = Path(configured_value)

    if not path.is_absolute():
        path = NEXUS_ROOT / path

    return path


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

    INBOX_DIR = get_configured_path("inbox", "Inbox")
    SEMESTER1_DIR = get_configured_path("academic", "Semester1")
    BACKUPS_DIR = get_configured_path("backups", "Backups")
    MODULES_DIR = get_configured_path("modules", "modules")

    PC_CONTROL_DIR = MODULES_DIR / "pc_control"
    COMMUNICATIONS_DIR = MODULES_DIR / "communications"
    SCREEN_VISION_DIR = MODULES_DIR / "screen_vision"

    LOGS_DIR = get_configured_path("logs", "logs")
    LOG_FILE = LOGS_DIR / "nexus_core.log"


refresh_paths()


def get_log_level():
    runtime = config.get("runtime", {})
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


def feature_enabled(feature_name):
    feature = FEATURE_REGISTRY.get(feature_name)

    if feature is None or feature.get("status") != "implemented":
        return False

    features = config.get("features", {})
    return features.get(feature_name, False) is True


def set_feature(feature_name, enabled):
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

    if save_config():
        logger.info(
            "Feature '%s' changed to %s.",
            feature_name,
            bool(enabled)
        )
        return True

    return False


def inspect_project():
    paths = {
        "Core": NEXUS_ROOT / "nexus_core.py",
        "Config": CONFIG_FILE,
        "Process Notes": PROCESS_NOTES_FILE,
        "Nexus Daemon": DAEMON_FILE,
        "Inbox": INBOX_DIR,
        "Semester1": SEMESTER1_DIR,
        "Backups": BACKUPS_DIR,
        "Modules": MODULES_DIR,
        "PC Control": PC_CONTROL_DIR,
        "Communications": COMMUNICATIONS_DIR,
        "Screen Vision": SCREEN_VISION_DIR
    }

    results = {}

    for name, path in paths.items():
        results[name] = path.exists()

    return results


def launch_process_notes():
    reload_configuration()

    if not feature_enabled("process_notes"):
        logger.info("Process Notes is disabled by configuration.")
        return False

    if not PROCESS_NOTES_FILE.exists():
        logger.error("process_notes.py was not found.")
        return False

    logger.info("Launching process_notes.py")

    try:
        result = subprocess.run(
            [sys.executable, str(PROCESS_NOTES_FILE)],
            cwd=str(NEXUS_ROOT),
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


class NexusGUI:
    def __init__(self, root):
        self.root = root

        self.root.title("Nexus Control Center")
        self.root.geometry("760x620")
        self.root.minsize(700, 560)

        self.root.configure(bg="#101318")

        self.feature_vars = {}

        self.build_interface()
        self.refresh_interface()

    def create_label(
        self,
        parent,
        text,
        size=11,
        bold=False,
        fg="#E8EAED"
    ):
        font_style = "bold" if bold else "normal"

        return tk.Label(
            parent,
            text=text,
            font=("Segoe UI", size, font_style),
            fg=fg,
            bg=parent.cget("bg")
        )

    def build_interface(self):
        header = tk.Frame(
            self.root,
            bg="#171A21",
            height=100
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        title = tk.Label(
            header,
            text="NEXUS",
            font=("Segoe UI", 26, "bold"),
            fg="#FFFFFF",
            bg="#171A21"
        )
        title.pack(anchor="w", padx=28, pady=(18, 0))

        subtitle = tk.Label(
            header,
            text="Personal AI Operating Layer  •  Control Center",
            font=("Segoe UI", 10),
            fg="#9AA0AA",
            bg="#171A21"
        )
        subtitle.pack(anchor="w", padx=30)

        status_frame = tk.Frame(
            self.root,
            bg="#101318"
        )
        status_frame.pack(fill="x", padx=28, pady=(22, 8))

        self.status_label = self.create_label(
            status_frame,
            "Status",
            size=13,
            bold=True
        )
        self.status_label.pack(side="left")

        self.version_label = self.create_label(
            status_frame,
            "",
            size=10,
            fg="#9AA0AA"
        )
        self.version_label.pack(side="right")

        features_title = self.create_label(
            self.root,
            "FEATURES",
            size=10,
            bold=True,
            fg="#8E96A3"
        )
        features_title.pack(
            anchor="w",
            padx=30,
            pady=(18, 8)
        )

        features_frame = tk.Frame(
            self.root,
            bg="#171A21",
            bd=0
        )
        features_frame.pack(
            fill="x",
            padx=28
        )

        for feature_name, feature in FEATURE_REGISTRY.items():
            self.add_feature(
                features_frame,
                feature_name,
                feature
            )

        actions_title = self.create_label(
            self.root,
            "ACTIONS",
            size=10,
            bold=True,
            fg="#8E96A3"
        )
        actions_title.pack(
            anchor="w",
            padx=30,
            pady=(22, 8)
        )

        actions_frame = tk.Frame(
            self.root,
            bg="#101318"
        )
        actions_frame.pack(
            fill="x",
            padx=28
        )

        self.process_button = tk.Button(
            actions_frame,
            text="Run Process Notes",
            command=self.run_process_notes,
            font=("Segoe UI", 10, "bold"),
            fg="#FFFFFF",
            bg="#252A34",
            activebackground="#343B48",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=18,
            pady=10,
            cursor="hand2"
        )
        self.process_button.pack(side="left", padx=(0, 10))

        reload_button = tk.Button(
            actions_frame,
            text="Reload Configuration",
            command=self.reload,
            font=("Segoe UI", 10),
            fg="#FFFFFF",
            bg="#252A34",
            activebackground="#343B48",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=18,
            pady=10,
            cursor="hand2"
        )
        reload_button.pack(side="left", padx=(0, 10))

        inspect_button = tk.Button(
            actions_frame,
            text="System Check",
            command=self.system_check,
            font=("Segoe UI", 10),
            fg="#FFFFFF",
            bg="#252A34",
            activebackground="#343B48",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=18,
            pady=10,
            cursor="hand2"
        )
        inspect_button.pack(side="left")

        footer = tk.Frame(
            self.root,
            bg="#101318"
        )
        footer.pack(
            fill="x",
            side="bottom",
            padx=28,
            pady=20
        )

        self.footer_label = self.create_label(
            footer,
            "",
            size=9,
            fg="#707782"
        )
        self.footer_label.pack(anchor="w")

    def add_feature(
        self,
        parent,
        feature_name,
        feature
    ):
        row = tk.Frame(
            parent,
            bg="#171A21"
        )
        row.pack(
            fill="x",
            padx=18,
            pady=14
        )

        text_frame = tk.Frame(
            row,
            bg="#171A21"
        )
        text_frame.pack(
            side="left",
            fill="x",
            expand=True
        )

        name_label = tk.Label(
            text_frame,
            text=feature["display_name"],
            font=("Segoe UI", 11, "bold"),
            fg="#F2F3F5",
            bg="#171A21"
        )
        name_label.pack(anchor="w")

        description_label = tk.Label(
            text_frame,
            text=feature["description"],
            font=("Segoe UI", 9),
            fg="#8F96A1",
            bg="#171A21"
        )
        description_label.pack(
            anchor="w",
            pady=(3, 0)
        )

        if feature["status"] != "implemented":
            status_label = tk.Label(
                row,
                text=feature["status"].upper(),
                font=("Segoe UI", 9, "bold"),
                fg="#9AA0AA",
                bg="#252A34",
                padx=10,
                pady=5
            )
            status_label.pack(side="right", padx=(15, 0))
            return

        var = tk.BooleanVar(value=feature_enabled(feature_name))
        self.feature_vars[feature_name] = var

        toggle = tk.Checkbutton(
            row,
            variable=var,
            command=lambda name=feature_name, value=var:
                self.toggle_feature(name, value),
            text="ON",
            indicatoron=False,
            width=7,
            font=("Segoe UI", 9, "bold"),
            fg="#FFFFFF",
            bg="#252A34",
            activebackground="#343B48",
            activeforeground="#FFFFFF",
            selectcolor="#252A34",
            relief="flat",
            bd=0,
            cursor="hand2"
        )

        toggle.pack(side="right", padx=(15, 0))

    def toggle_feature(self, feature_name, variable):
        if feature_name not in FEATURE_REGISTRY:
            variable.set(False)
            return

        enabled = variable.get()

        if set_feature(feature_name, enabled):
            self.update_toggle_text(feature_name, enabled)

            readable_name = feature_name.replace(
                "_",
                " "
            ).title()

            if enabled:
                self.status_label.config(
                    text=readable_name + " enabled"
                )
            else:
                self.status_label.config(
                    text=readable_name + " disabled"
                )

            self.update_process_button()

        else:
            variable.set(
                feature_enabled(feature_name)
            )

            messagebox.showerror(
                "Nexus Configuration Error",
                "Nexus could not save the configuration."
            )

    def update_toggle_text(self, feature_name, enabled):
        for widget in self.root.winfo_children():
            self.update_toggle_widgets(
                widget,
                feature_name,
                enabled
            )

    def update_toggle_widgets(
        self,
        widget,
        feature_name,
        enabled
    ):
        for child in widget.winfo_children():
            if isinstance(child, tk.Checkbutton):
                try:
                    variable_name = str(
                        child.cget("variable")
                    )

                    current_variable = self.feature_vars.get(
                        feature_name
                    )

                    if current_variable is not None:
                        expected_name = str(
                            current_variable
                        )

                        if variable_name == expected_name:
                            child.config(
                                text="ON" if enabled else "OFF"
                            )
                except tk.TclError:
                    pass

            self.update_toggle_widgets(
                child,
                feature_name,
                enabled
            )

    def refresh_interface(self):
        reload_configuration()

        for feature_name, variable in self.feature_vars.items():
            variable.set(
                feature_enabled(feature_name)
            )
            self.update_toggle_text(
                feature_name,
                variable.get()
            )

        self.update_process_button()

        self.version_label.config(
            text="Core v" + NEXUS_VERSION
        )

        self.footer_label.config(
            text="Config: " + str(CONFIG_FILE)
        )

        self.status_label.config(
            text="Nexus ready"
        )

    def update_process_button(self):
        if feature_enabled("process_notes"):
            self.process_button.config(
                state="normal",
                text="Run Process Notes"
            )
        else:
            self.process_button.config(
                state="disabled",
                text="Process Notes Disabled"
            )

    def run_process_notes(self):
        if not feature_enabled("process_notes"):
            messagebox.showinfo(
                "Process Notes Disabled",
                "Process Notes is currently disabled."
            )
            return

        self.status_label.config(
            text="Running Process Notes..."
        )

        self.root.update_idletasks()

        success = launch_process_notes()

        if success:
            self.status_label.config(
                text="Process Notes completed"
            )
        else:
            self.status_label.config(
                text="Process Notes failed"
            )

            messagebox.showerror(
                "Process Notes",
                "Process Notes did not complete successfully.\n\n"
                "Check the Nexus log for details."
            )

    def reload(self):
        self.refresh_interface()

    def system_check(self):
        results = inspect_project()

        lines = []

        for name, exists in results.items():
            symbol = "OK" if exists else "MISSING"
            lines.append(
                "{:<20} {}".format(
                    name + ":",
                    symbol
                )
            )

        messagebox.showinfo(
            "Nexus System Check",
            "\n".join(lines)
        )


def start_gui():
    root = tk.Tk()

    app = NexusGUI(root)

    root.protocol(
        "WM_DELETE_WINDOW",
        root.destroy
    )

    root.mainloop()


if __name__ == "__main__":
    start_gui()