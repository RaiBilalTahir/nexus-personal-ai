import ast
import io
import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.capabilities.process_notes import process_notes
from app.models import ErrorCategory, ModelError, ModelRequest, ModelResult
from app.provenance import (
    DuplicateClassification,
    ProcessingRecordStore,
    calculate_source_identity,
)


class FakeGateway:
    def __init__(self, result):
        self.result = result
        self.request = None
        self.default_provider = "gemini"
        self.default_model = "gemini-3.8-flash"

    def generate(self, request):
        self.request = request
        return self.result


class ProcessNotesGatewayTests(unittest.TestCase):
    def test_process_notes_does_not_import_gemini_sdk(self):
        source = Path(process_notes.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)

        self.assertNotIn("google", imported_modules)
        self.assertNotIn("google.genai", imported_modules)
        self.assertNotIn("GEMINI_API_KEY", source)
        self.assertNotIn("GEMINI_MODEL", source)
        self.assertNotIn("generate_content", source)

    def test_process_notes_does_not_import_nexus_core(self):
        source = Path(process_notes.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)

        self.assertNotIn("app.core.nexus_core", imported_modules)

    def test_image_model_request_construction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ICT_test.jpg"
            path.write_bytes(b"image-bytes")

            request = process_notes.build_model_request(path)

        self.assertIsInstance(request, ModelRequest)
        self.assertEqual(request.text, process_notes.TRANSCRIPTION_PROMPT)
        self.assertEqual(len(request.images), 1)
        self.assertEqual(request.images[0].mime_type, "image/jpeg")
        self.assertEqual(request.images[0].data, b"image-bytes")
        self.assertEqual(request.documents, ())

    def test_pdf_model_request_construction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ICT_test.pdf"
            path.write_bytes(b"pdf-bytes")

            request = process_notes.build_model_request(path)

        self.assertEqual(request.images, ())
        self.assertEqual(len(request.documents), 1)
        self.assertEqual(request.documents[0].mime_type, "application/pdf")
        self.assertEqual(request.documents[0].data, b"pdf-bytes")

    def test_successful_gateway_result_is_returned_as_text(self):
        gateway = FakeGateway(
            ModelResult(
                success=True,
                provider="gemini",
                model="gemini-3.8-flash",
                text="# Transcribed notes",
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ICT_test.jpg"
            path.write_bytes(b"image-bytes")
            text = process_notes.transcribe_file(gateway, path)

        self.assertEqual(text, "# Transcribed notes")
        self.assertEqual(gateway.request.metadata["capability"], "process_notes")

    def test_structured_gateway_error_is_handled_by_process_file(self):
        gateway = FakeGateway(
            ModelResult.failure(
                provider="gemini",
                model="gemini-3.8-flash",
                error=ModelError(
                    category=ErrorCategory.MISSING_CREDENTIALS,
                    retryable=False,
                    detail="GEMINI_API_KEY",
                ),
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ICT_test.jpg"
            path.write_bytes(b"image-bytes")
            result = process_notes.process_file(gateway, path)
            self.assertEqual(result, "failed")
            self.assertTrue(path.exists())

    def test_completed_exact_duplicate_is_not_sent_to_gateway(self):
        gateway = FakeGateway(
            ModelResult(
                success=True,
                provider="gemini",
                model="gemini-3.8-flash",
                text="should not be used",
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ICT_test.jpg"
            path.write_bytes(b"image-bytes")
            store = ProcessingRecordStore(Path(directory) / "records.json")
            identity = calculate_source_identity(path)
            store.record(identity, "config-a", "completed")

            result = process_notes.process_file(
                gateway,
                path,
                identity_store=store,
                processing_config_id="config-a",
            )

        self.assertEqual(result, "skipped")
        self.assertIsNone(gateway.request)

    def test_possible_duplicate_is_not_blocked_from_processing(self):
        gateway = FakeGateway(
            ModelResult(
                success=True,
                provider="gemini",
                model="gemini-3.8-flash",
                text="# Successful transcription of unique file",
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = root / "inbox"
            academic = root / "academic"
            inbox.mkdir()
            academic.mkdir()

            prior_file = inbox / "ICT_prior.jpg"
            prior_file.write_bytes(b"12345")
            store = ProcessingRecordStore(root / "records.json")
            store.record(calculate_source_identity(prior_file), "config-a", "completed")

            new_file = inbox / "ICT_new.jpg"
            new_file.write_bytes(b"abcde")

            paths = {
                "root": root,
                "inbox": inbox,
                "academic": academic,
                "provenance": root / "records.json",
            }

            result = process_notes.process_file(
                gateway,
                new_file,
                identity_store=store,
                processing_config_id="config-a",
                paths=paths,
            )

            self.assertEqual(result, "success")
            self.assertIsNotNone(gateway.request)
            expected_note = academic / "Introduction to Computing" / "notes" / "ICT_new.md"
            self.assertTrue(expected_note.exists())

    def test_transaction_safety_atomically_finalizes_output_and_archives_source(self):
        gateway = FakeGateway(
            ModelResult(
                success=True,
                provider="gemini",
                model="gemini-3.8-flash",
                text="# Transcribed lecture notes\n- Topic: Microprocessors",
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = root / "inbox"
            academic = root / "academic"
            inbox.mkdir()
            academic.mkdir()

            source_file = inbox / "ICT_lecture.jpg"
            source_file.write_bytes(b"sample-lecture-scan-content")
            store = ProcessingRecordStore(root / "records.json")

            paths = {
                "root": root,
                "inbox": inbox,
                "academic": academic,
                "provenance": root / "records.json",
            }

            result = process_notes.process_file(
                gateway,
                source_file,
                identity_store=store,
                processing_config_id="config-a",
                paths=paths,
            )

            self.assertEqual(result, "success")

            course_dir = academic / "Introduction to Computing"
            note_file = course_dir / "notes" / "ICT_lecture.md"
            temp_file = course_dir / "notes" / "ICT_lecture.md.tmp"
            raw_file = course_dir / "raw" / "ICT_lecture.jpg"

            self.assertTrue(note_file.exists())
            self.assertFalse(temp_file.exists())
            self.assertIn("Microprocessors", note_file.read_text(encoding="utf-8"))

            self.assertTrue(raw_file.exists())
            self.assertFalse(source_file.exists())

            self.assertTrue(store.is_completed(calculate_source_identity(raw_file), "config-a"))

    def test_source_move_succeeds_note_finalization_fails_rolls_back_source_to_inbox(self):
        gateway = FakeGateway(
            ModelResult(
                success=True,
                provider="gemini",
                model="gemini-3.8-flash",
                text="# Transcribed notes",
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = root / "inbox"
            academic = root / "academic"
            inbox.mkdir()
            academic.mkdir()

            source_file = inbox / "ICT_rollback.jpg"
            source_file.write_bytes(b"image-content-for-rollback")
            store = ProcessingRecordStore(root / "records.json")

            paths = {
                "root": root,
                "inbox": inbox,
                "academic": academic,
                "provenance": root / "records.json",
            }

            orig_replace = Path.replace

            def failing_replace(self, target):
                if str(self).endswith(".tmp"):
                    raise OSError("Simulated filesystem error during note finalization")
                return orig_replace(self, target)

            with patch.object(Path, "replace", failing_replace):
                result = process_notes.process_file(
                    gateway,
                    source_file,
                    identity_store=store,
                    processing_config_id="config-a",
                    paths=paths,
                )

            self.assertEqual(result, "failed")

            raw_file = academic / "Introduction to Computing" / "raw" / "ICT_rollback.jpg"
            note_file = academic / "Introduction to Computing" / "notes" / "ICT_rollback.md"
            temp_file = academic / "Introduction to Computing" / "notes" / "ICT_rollback.md.tmp"

            # Invariant: Source was rolled back to inbox!
            self.assertTrue(source_file.exists())
            self.assertEqual(source_file.read_bytes(), b"image-content-for-rollback")

            # Invariant: Source does NOT linger in raw archive
            self.assertFalse(raw_file.exists())

            # Invariant: Temp output was cleaned up
            self.assertFalse(temp_file.exists())

            # Invariant: Note was NOT finalized
            self.assertFalse(note_file.exists())

            # Invariant: A failed record is written in ledger
            record = store.find_record(calculate_source_identity(source_file).content_hash, "config-a")
            self.assertIsNotNone(record)
            self.assertEqual(record["status"], "failed")

            # Invariant: Immediate retry succeeds without collision!
            retry_result = process_notes.process_file(
                gateway,
                source_file,
                identity_store=store,
                processing_config_id="config-a",
                paths=paths,
            )
            self.assertEqual(retry_result, "success")
            self.assertTrue(note_file.exists())
            self.assertTrue(raw_file.exists())
            self.assertFalse(source_file.exists())

    def test_recovery_after_prior_partial_failure_with_stranded_raw_file(self):
        gateway = FakeGateway(
            ModelResult(
                success=True,
                provider="gemini",
                model="gemini-3.8-flash",
                text="# Recovered transcription from prior crash",
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = root / "inbox"
            academic = root / "academic"
            inbox.mkdir()
            academic.mkdir()

            source_file = inbox / "ICT_crash.jpg"
            source_file.write_bytes(b"crash-content")
            store = ProcessingRecordStore(root / "records.json")

            # Pre-seed a stranded raw file from an un-rolled-back previous crash with failed record
            raw_dir = academic / "Introduction to Computing" / "raw"
            raw_dir.mkdir(parents=True)
            stranded_raw = raw_dir / "ICT_crash.jpg"
            stranded_raw.write_bytes(b"crash-content")

            identity = calculate_source_identity(source_file)
            store.record(identity, "config-a", "failed", output_path="failed.md")

            paths = {
                "root": root,
                "inbox": inbox,
                "academic": academic,
                "provenance": root / "records.json",
            }

            # Should NOT deadlock with collision; should recover and complete!
            result = process_notes.process_file(
                gateway,
                source_file,
                identity_store=store,
                processing_config_id="config-a",
                paths=paths,
            )

            self.assertEqual(result, "success")
            note_file = academic / "Introduction to Computing" / "notes" / "ICT_crash.md"
            self.assertTrue(note_file.exists())
            self.assertIn("Recovered transcription", note_file.read_text(encoding="utf-8"))
            self.assertTrue(store.is_completed(identity, "config-a"))

    def test_no_duplicate_successful_ledger_record(self):
        gateway = FakeGateway(
            ModelResult(
                success=True,
                provider="gemini",
                model="gemini-3.8-flash",
                text="text",
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = root / "inbox"
            academic = root / "academic"
            inbox.mkdir()
            academic.mkdir()

            source_file = inbox / "ICT_dup.jpg"
            source_file.write_bytes(b"dup-content")
            store = ProcessingRecordStore(root / "records.json")

            identity = calculate_source_identity(source_file)
            store.record(identity, "config-a", "completed", output_path="dup.md")

            initial_records_count = len(store._load_records())

            paths = {
                "root": root,
                "inbox": inbox,
                "academic": academic,
                "provenance": root / "records.json",
            }

            result = process_notes.process_file(
                gateway,
                source_file,
                identity_store=store,
                processing_config_id="config-a",
                paths=paths,
            )

            self.assertEqual(result, "skipped")
            # Invariant: No duplicate record was appended
            self.assertEqual(len(store._load_records()), initial_records_count)

    def test_collision_safety_on_existing_target_note(self):
        gateway = FakeGateway(
            ModelResult(
                success=True,
                provider="gemini",
                model="gemini-3.8-flash",
                text="new transcription",
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = root / "inbox"
            academic = root / "academic"
            inbox.mkdir()
            academic.mkdir()

            source_file = inbox / "ICT_class.jpg"
            source_file.write_bytes(b"content")

            notes_dir = academic / "Introduction to Computing" / "notes"
            notes_dir.mkdir(parents=True)
            existing_note = notes_dir / "ICT_class.md"
            existing_note.write_text("# Original preserved note", encoding="utf-8")

            paths = {
                "root": root,
                "inbox": inbox,
                "academic": academic,
                "provenance": root / "records.json",
            }

            result = process_notes.process_file(
                gateway,
                source_file,
                paths=paths,
            )

            self.assertEqual(result, "failed")
            self.assertEqual(existing_note.read_text(encoding="utf-8"), "# Original preserved note")
            self.assertTrue(source_file.exists())

    def test_collision_safety_on_existing_archive_destination(self):
        gateway = FakeGateway(
            ModelResult(
                success=True,
                provider="gemini",
                model="gemini-3.8-flash",
                text="transcription",
            )
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = root / "inbox"
            academic = root / "academic"
            inbox.mkdir()
            academic.mkdir()

            source_file = inbox / "ICT_class.jpg"
            source_file.write_bytes(b"content")

            raw_dir = academic / "Introduction to Computing" / "raw"
            raw_dir.mkdir(parents=True)
            existing_raw = raw_dir / "ICT_class.jpg"
            existing_raw.write_bytes(b"existing-archived-file")

            paths = {
                "root": root,
                "inbox": inbox,
                "academic": academic,
                "provenance": root / "records.json",
            }

            result = process_notes.process_file(
                gateway,
                source_file,
                paths=paths,
            )

            self.assertEqual(result, "failed")
            self.assertEqual(existing_raw.read_bytes(), b"existing-archived-file")
            self.assertTrue(source_file.exists())

    def test_configuration_flows_through_gateway(self):
        config = json.loads(
            Path("config/nexus_config.json").read_text(encoding="utf-8")
        )
        gateway = process_notes.create_model_gateway(config, environ={})
        result = gateway.generate(ModelRequest(text="offline check"))

        self.assertFalse(result.success)
        self.assertEqual(result.provider, config["ai"]["provider"])
        self.assertEqual(result.model, config["ai"]["model"])
        self.assertEqual(result.error.category, ErrorCategory.MISSING_CREDENTIALS)
        self.assertEqual(gateway.default_provider, config["ai"]["provider"])
        self.assertEqual(gateway.default_model, config["ai"]["model"])

    def test_secret_is_not_written_to_logs(self):
        secret = "test-secret-that-must-not-appear"
        gateway = FakeGateway(
            ModelResult.failure(
                provider="gemini",
                model="gemini-3.8-flash",
                error=ModelError(
                    category=ErrorCategory.MISSING_CREDENTIALS,
                    retryable=False,
                    detail=secret,
                ),
            )
        )
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        process_notes.logger.addHandler(handler)

        try:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "ICT_test.jpg"
                path.write_bytes(b"image-bytes")
                process_notes.process_file(gateway, path)
        finally:
            process_notes.logger.removeHandler(handler)

        self.assertNotIn(secret, stream.getvalue())


if __name__ == "__main__":
    unittest.main()
