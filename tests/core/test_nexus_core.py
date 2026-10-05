import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

from app.core import config as nexus_config_module
from app.core import nexus_core


class NexusCoreTests(unittest.TestCase):
    def test_core_package_import(self):
        self.assertEqual(nexus_core.NEXUS_NAME, "Nexus")
        self.assertEqual(nexus_core.NEXUS_VERSION, "1.1.1")
        self.assertIsInstance(nexus_core.DEFAULT_CONFIG, dict)

    def test_core_does_not_import_tkinter(self):
        # Verify that importing app.core.nexus_core does NOT load tkinter into sys.modules
        self.assertNotIn("tkinter", sys.modules)

    def test_config_module_is_neutral_and_importable(self):
        self.assertEqual(nexus_config_module.NEXUS_NAME, "Nexus")
        self.assertEqual(nexus_config_module.NEXUS_VERSION, "1.1.1")
        self.assertNotIn("tkinter", sys.modules)

    def test_merge_config_defaults(self):
        defaults = {
            "nexus": {"name": "Nexus", "version": "1.0.0"},
            "runtime": {"log_level": "INFO"},
        }
        loaded = {
            "nexus": {"version": "1.1.1"},
            "extra_key": True,
        }
        merged = nexus_core.merge_config(defaults, loaded)
        self.assertEqual(merged["nexus"]["name"], "Nexus")
        self.assertEqual(merged["nexus"]["version"], "1.1.1")
        self.assertEqual(merged["runtime"]["log_level"], "INFO")
        self.assertTrue(merged["extra_key"])

    def test_merge_config_invalid_loaded_returns_copy_of_defaults(self):
        defaults = {"a": 1, "b": {"c": 2}}
        merged = nexus_core.merge_config(defaults, "not-a-dict")
        self.assertEqual(merged, defaults)
        self.assertIsNot(merged, defaults)

    def test_load_raw_config_handles_missing_file(self):
        missing_path = Path("/nonexistent/nexus_config_missing.json")
        result = nexus_core.load_raw_config(missing_path)
        self.assertEqual(result, {})

    def test_load_raw_config_handles_corrupt_json(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
            f.write("{invalid-json")
            temp_path = Path(f.name)
        try:
            result = nexus_core.load_raw_config(temp_path)
            self.assertEqual(result, {})
        finally:
            temp_path.unlink(missing_ok=True)

    def test_load_raw_config_handles_non_dict_json(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
            f.write("[\"a\", \"list\"]")
            temp_path = Path(f.name)
        try:
            result = nexus_core.load_raw_config(temp_path)
            self.assertEqual(result, {})
        finally:
            temp_path.unlink(missing_ok=True)

    def test_get_nexus_paths_returns_resolved_paths(self):
        custom_config = {
            "paths": {
                "inbox": "custom/inbox",
                "academic": "custom/academic",
                "logs": "custom/logs",
            }
        }
        with tempfile.TemporaryDirectory() as temp_root_str:
            temp_root = Path(temp_root_str)
            paths = nexus_core.get_nexus_paths(custom_config, root=temp_root)
            self.assertEqual(paths["inbox"], temp_root / "custom/inbox")
            self.assertEqual(paths["academic"], temp_root / "custom/academic")
            self.assertEqual(paths["logs"], temp_root / "custom/logs")

    def test_feature_enabled_honors_implemented_status(self):
        self.assertTrue(nexus_core.feature_enabled("process_notes"))
        fake_config = {"features": {"pc_control": True}}
        self.assertFalse(nexus_core.feature_enabled("pc_control", configuration=fake_config))

    def test_set_feature_refuses_to_enable_unimplemented_feature(self):
        result = nexus_core.set_feature("pc_control", True)
        self.assertFalse(result)

    def test_inspect_project_runs_without_exceptions(self):
        with tempfile.TemporaryDirectory() as temp_root_str:
            temp_root = Path(temp_root_str)
            core_dir = temp_root / "app" / "core"
            core_dir.mkdir(parents=True)
            (core_dir / "nexus_core.py").write_text("# core", encoding="utf-8")

            results = nexus_core.inspect_project(root=temp_root)
            self.assertIsInstance(results, dict)
            self.assertTrue(results["Core"])
            self.assertFalse(results["Nexus Daemon"])

    def test_gui_module_can_be_imported(self):
        tkinter_mocked = False
        if "tkinter" not in sys.modules:
            mock_tk = types.ModuleType("tkinter")
            mock_tk.Tk = lambda: None
            mock_tk.Frame = lambda *args, **kwargs: None
            mock_tk.Label = lambda *args, **kwargs: None
            mock_tk.Button = lambda *args, **kwargs: None
            mock_tk.Checkbutton = lambda *args, **kwargs: None
            mock_tk.BooleanVar = lambda *args, **kwargs: None
            mock_mb = types.ModuleType("tkinter.messagebox")
            sys.modules["tkinter"] = mock_tk
            sys.modules["tkinter.messagebox"] = mock_mb
            tkinter_mocked = True

        try:
            import app.ui.gui as gui_module
            self.assertTrue(hasattr(gui_module, "NexusGUI"))
            self.assertTrue(hasattr(gui_module, "start_gui"))
        finally:
            if tkinter_mocked:
                sys.modules.pop("tkinter.messagebox", None)
                sys.modules.pop("tkinter", None)


if __name__ == "__main__":
    unittest.main()
