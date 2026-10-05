import tkinter as tk
from tkinter import messagebox

from app.core.feature_registry import FEATURE_REGISTRY
from app.core.nexus_core import (
    CONFIG_FILE,
    NEXUS_NAME,
    NEXUS_VERSION,
    feature_enabled,
    inspect_project,
    launch_process_notes,
    reload_configuration,
    set_feature,
)


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
