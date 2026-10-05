import json
import tempfile
import unittest
from pathlib import Path

from app.provenance.source_identity import (
    CorruptedLedgerError,
    DuplicateClassification,
    ProcessingRecordStore,
    calculate_processing_config_id,
    calculate_source_identity,
    classify_source,
)


class SourceIdentityTests(unittest.TestCase):
    def test_identical_files_have_identical_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.txt"
            second = Path(directory) / "second.txt"
            first.write_bytes(b"same content")
            second.write_bytes(b"same content")

            first_identity = calculate_source_identity(first, Path(directory))
            second_identity = calculate_source_identity(second, Path(directory))

        self.assertEqual(first_identity.content_hash, second_identity.content_hash)

    def test_different_files_have_different_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.txt"
            second = Path(directory) / "second.txt"
            first.write_bytes(b"first")
            second.write_bytes(b"second")

            first_identity = calculate_source_identity(first)
            second_identity = calculate_source_identity(second)

        self.assertNotEqual(first_identity.content_hash, second_identity.content_hash)

    def test_renamed_identical_file_is_exact_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.jpg"
            renamed = Path(directory) / "renamed.jpg"
            source.write_bytes(b"image-bytes")
            renamed.write_bytes(source.read_bytes())
            store = ProcessingRecordStore(Path(directory) / "records.json")
            config_id = "config-a"
            store.record(calculate_source_identity(source), config_id, "completed")

            result = store.classify(calculate_source_identity(renamed), config_id)

        self.assertEqual(result.classification, DuplicateClassification.EXACT_DUPLICATE)

    def test_changed_file_is_modified_version(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "notes.jpg"
            source.write_bytes(b"old")
            store = ProcessingRecordStore(Path(directory) / "records.json")
            store.record(calculate_source_identity(source), "config-a", "completed")
            source.write_bytes(b"new content")

            result = store.classify(calculate_source_identity(source), "config-a")

        self.assertEqual(result.classification, DuplicateClassification.MODIFIED_VERSION)

    def test_possible_duplicate_is_classified_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "one.jpg"
            possible = Path(directory) / "two.jpg"
            source.write_bytes(b"12345")
            possible.write_bytes(b"abcde")
            store = ProcessingRecordStore(Path(directory) / "records.json")
            store.record(calculate_source_identity(source), "config-a", "completed")

            result = store.classify(calculate_source_identity(possible), "config-a")
            self.assertTrue(possible.exists())

        self.assertEqual(result.classification, DuplicateClassification.POSSIBLE_DUPLICATE)

    def test_processing_configuration_is_stable_and_changes_when_context_changes(self):
        first = calculate_processing_config_id("process_notes", "1", "1", "gemini", "model-a")
        same = calculate_processing_config_id("process_notes", "1", "1", "gemini", "model-a")
        changed = calculate_processing_config_id("process_notes", "1", "1", "gemini", "model-b")
        self.assertEqual(first, same)
        self.assertNotEqual(first, changed)

    def test_failed_processing_remains_retryable(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "notes.jpg"
            source.write_bytes(b"image")
            store = ProcessingRecordStore(Path(directory) / "records.json")
            identity = calculate_source_identity(source)
            store.record(identity, "config-a", "failed")

            self.assertFalse(store.is_completed(identity, "config-a"))
            store.record(identity, "config-a", "completed")
            self.assertTrue(store.is_completed(identity, "config-a"))

    def test_source_remains_untouched_by_identity_calculation(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            source.write_bytes(b"unchanged")
            before = source.read_bytes()
            calculate_source_identity(source)
            self.assertEqual(source.read_bytes(), before)
            self.assertTrue(source.exists())

    def test_unreadable_source_is_classified(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.jpg"
            store = ProcessingRecordStore(Path(directory) / "records.json")

            identity, result = classify_source(missing, store, "config-a")

        self.assertIsNone(identity)
        self.assertEqual(
            result.classification,
            DuplicateClassification.INVALID_UNREADABLE,
        )

    def test_corrupted_ledger_raises_error_and_creates_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger_path = Path(directory) / "records.json"
            ledger_path.write_text("{this is corrupted json", encoding="utf-8")

            store = ProcessingRecordStore(ledger_path)
            with self.assertRaises(CorruptedLedgerError):
                store.find_record("any-hash", "config-a")

            # Verify that a backup file was created preserving corrupt data
            bak_files = list(Path(directory).glob("*.bak"))
            self.assertGreaterEqual(len(bak_files), 1)
            self.assertEqual(bak_files[0].read_text(encoding="utf-8"), "{this is corrupted json")

    def test_malformed_ledger_without_records_key_raises_error(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger_path = Path(directory) / "records.json"
            ledger_path.write_text(json.dumps({"version": 1}), encoding="utf-8")

            store = ProcessingRecordStore(ledger_path)
            with self.assertRaises(CorruptedLedgerError):
                store.find_record("any-hash", "config-a")

    def test_ledger_append_preserves_historical_records(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger_path = Path(directory) / "records.json"
            store = ProcessingRecordStore(ledger_path)

            source1 = Path(directory) / "file1.txt"
            source2 = Path(directory) / "file2.txt"
            source1.write_bytes(b"first record")
            source2.write_bytes(b"second record")

            id1 = calculate_source_identity(source1)
            id2 = calculate_source_identity(source2)

            store.record(id1, "config-a", "completed", output_path="out1.md")
            store.record(id2, "config-a", "completed", output_path="out2.md")

            self.assertTrue(store.is_completed(id1, "config-a"))
            self.assertTrue(store.is_completed(id2, "config-a"))

            loaded = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(len(loaded["records"]), 2)
            self.assertEqual(loaded["records"][0]["source"]["content_hash"], id1.content_hash)
            self.assertEqual(loaded["records"][1]["source"]["content_hash"], id2.content_hash)


if __name__ == "__main__":
    unittest.main()
