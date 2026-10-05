import ast
import io
import json
import logging
import tempfile
import unittest
from pathlib import Path

from app.models import ErrorCategory, ModelError, ModelRequest, ModelResult
from app.capabilities.process_notes import process_notes


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
        from app.provenance import ProcessingRecordStore, calculate_source_identity

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
