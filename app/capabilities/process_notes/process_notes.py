import hashlib
import json
import logging
import os
import shutil
import sys
from pathlib import Path

NEXUS_NAME = "Nexus"
PROCESSOR_VERSION = "1.1.1"

NEXUS_ROOT = Path(__file__).resolve().parents[3]
if str(NEXUS_ROOT) not in sys.path:
    sys.path.insert(0, str(NEXUS_ROOT))

from app.core.config import get_nexus_paths, load_config
from app.models import (
    DocumentInput,
    ErrorCategory,
    ImageInput,
    ModelError,
    ModelRequest,
)
from app.models.gateway import create_gateway
from app.provenance import (
    CorruptedLedgerError,
    DuplicateClassification,
    ProcessingRecordStore,
    calculate_processing_config_id,
    calculate_source_identity,
    classify_source,
)

SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
}

IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

COURSE_MAP = {
    "Electronics": "Basic Electronics",
    "Electronics-Lab": "Basic Electronics - Lab",
    "English": "Functional English",
    "Logic": "Logic Thinking",
    "Financial-Account": "Financial Account",
    "ICT": "Introduction to Computing",
    "ICT-Lab": "Introduction to Computing - Lab",
    "Ideology": "Ideology and Constitution of Pakistan",
    "Pak-Study": "Ideology and Constitution of Pakistan",
}

TRANSCRIPTION_PROMPT = """
You are Nexus's academic notes transcription engine.

Accurately transcribe the supplied handwritten class notes
or academic document into clean Markdown.

Rules:

1. Preserve the original meaning.
2. Do not invent missing information.
3. Do not silently correct the student's content.
4. Preserve headings and subheadings.
5. Preserve bullet points and numbered lists.
6. Preserve formulas, equations, symbols, and technical terms.
7. Preserve examples and definitions.
8. If handwriting is genuinely unclear, write [unclear].
9. If there is a diagram, flowchart, circuit, table, graph,
   or other visual structure, describe it clearly in Markdown.
10. Preserve the logical order of the original document.
11. Do not add an introduction or conclusion.
12. Return ONLY the Markdown transcription.

Accuracy is more important than creativity.
"""

logger = logging.getLogger("nexus.process_notes")


class ModelGatewayFailure(RuntimeError):
    def __init__(self, error):
        self.error = error
        super().__init__(error.category.value)


def create_model_gateway(configuration=None, environ=None):
    if configuration is None:
        configuration = load_config()

    return create_gateway(configuration, environ=environ)


def get_processing_config_id(gateway):
    prompt_version = hashlib.sha256(
        TRANSCRIPTION_PROMPT.encode("utf-8")
    ).hexdigest()
    return calculate_processing_config_id(
        capability="process_notes",
        pipeline_version=PROCESSOR_VERSION,
        schema_version=prompt_version,
        provider=gateway.default_provider,
        model=gateway.default_model or "provider-default",
    )


def get_course_from_filename(filename):
    prefix = filename.split("_", 1)[0]
    return COURSE_MAP.get(prefix)


def get_destination_directories(course_name, semester_dir=None):
    base_semester = Path(semester_dir) if semester_dir is not None else (
        NEXUS_ROOT / "data" / "knowledge" / "academic" / "Semester1"
    )
    course_dir = base_semester / course_name
    raw_dir = course_dir / "raw"
    notes_dir = course_dir / "notes"

    return raw_dir, notes_dir


def build_model_request(file_path):
    source_data = file_path.read_bytes()

    if file_path.suffix.lower() == ".pdf":
        documents = (
            DocumentInput(
                data=source_data,
                mime_type="application/pdf",
                name=file_path.name,
            ),
        )
        images = ()
    else:
        images = (
            ImageInput(
                data=source_data,
                mime_type=IMAGE_MIME_TYPES[file_path.suffix.lower()],
                name=file_path.name,
            ),
        )
        documents = ()

    return ModelRequest(
        text=TRANSCRIPTION_PROMPT,
        images=images,
        documents=documents,
        metadata={
            "capability": "process_notes",
            "source_name": file_path.name,
        },
    )


def transcribe_file(gateway, file_path):
    logger.info(
        "Submitting file to Model Gateway: %s",
        file_path.name,
    )

    result = gateway.generate(build_model_request(file_path))

    if not result.success:
        logger.error(
            "Model Gateway request failed | category=%s retryable=%s",
            result.error.category.value,
            result.error.retryable,
        )
        raise ModelGatewayFailure(result.error)

    text = result.text

    if not text or not text.strip():
        raise ModelGatewayFailure(
            ModelError(
                category=ErrorCategory.INVALID_RESPONSE,
                retryable=False,
                detail="empty_text",
            )
        )

    return text.strip()


def process_file(
    gateway,
    file_path,
    identity_store=None,
    processing_config_id=None,
    configuration=None,
    paths=None,
):
    course_name = get_course_from_filename(file_path.name)

    if not course_name:
        logger.warning(
            "Skipping %s: filename prefix is not in COURSE_MAP.",
            file_path.name,
        )
        print(f"[SKIP] Unknown course prefix: {file_path.name}")
        return "skipped"

    active_config = configuration or load_config()
    resolved_paths = paths or get_nexus_paths(active_config, root=NEXUS_ROOT)
    semester_dir = resolved_paths["academic"]

    raw_dir, notes_dir = get_destination_directories(
        course_name,
        semester_dir=semester_dir,
    )

    notes_file = notes_dir / (file_path.stem + ".md")
    temp_notes_file = notes_dir / (file_path.stem + ".md.tmp")
    raw_file = raw_dir / file_path.name

    identity_store = identity_store or ProcessingRecordStore(
        resolved_paths["provenance"]
    )
    processing_config_id = processing_config_id or get_processing_config_id(
        gateway
    )

    source_identity, classification = classify_source(
        file_path,
        identity_store,
        processing_config_id,
        resolved_paths["root"],
    )
    if source_identity is None:
        logger.error(
            "Unable to classify source %s: %s",
            file_path.name,
            classification.reason,
        )
        print("[ERROR] Source file could not be read safely.")
        return "failed"

    previous_record = identity_store.find_record(
        source_identity.content_hash,
        processing_config_id,
    )

    logger.info(
        "Source classification | file=%s classification=%s",
        file_path.name,
        classification.classification.value,
    )

    # 1. Exact duplicate check
    if classification.classification == DuplicateClassification.EXACT_DUPLICATE:
        if identity_store.is_completed(source_identity, processing_config_id):
            print("[SKIP] Exact source already processed with this configuration.")
            return "skipped"

    # 2. Advisory possible duplicate notice - do NOT skip valid files
    if classification.classification == DuplicateClassification.POSSIBLE_DUPLICATE:
        logger.info(
            "Advisory: %s shares size and MIME with existing record, but differs in content hash. Proceeding.",
            file_path.name,
        )
        print(f"[ADVISORY] Note: {file_path.name} has same size as an earlier file but unique content. Processing.")

    # 3. Destination collision safety: target markdown
    if notes_file.exists() and not (
        previous_record and previous_record.get("status") in {"failed", "partial"}
    ):
        logger.info(
            "Skipping existing Markdown output without a retryable identity record: %s",
            notes_file,
        )
        print("[COLLISION] Target markdown file already exists; review required.")
        return "failed"

    # 4. Destination collision safety: archive destination
    # Check if raw_file exists from an incomplete prior failure that can be recovered
    is_recoverable_partial = (
        raw_file.exists()
        and previous_record is not None
        and previous_record.get("status") in {"failed", "partial"}
        and not notes_file.exists()
    )

    if raw_file.exists() and not is_recoverable_partial:
        logger.warning(
            "Archived original already exists at destination: %s",
            raw_file,
        )
        print(f"[COLLISION] An archived original already exists at: {raw_file.name}. Source left intact in inbox.")
        return "failed"

    print()
    print(f"Processing: {file_path.name}")
    print(f"Course:     {course_name}")

    source_moved = False
    note_finalized = False

    try:
        markdown_text = transcribe_file(gateway, file_path)

        raw_dir.mkdir(parents=True, exist_ok=True)
        notes_dir.mkdir(parents=True, exist_ok=True)

        # 5. Write through temporary file to guarantee atomic output
        temp_notes_file.write_text(markdown_text + "\n", encoding="utf-8")

        if not temp_notes_file.exists() or temp_notes_file.stat().st_size == 0:
            raise IOError("Temporary markdown output could not be verified.")

        logger.info("Temporary markdown saved: %s", temp_notes_file)

        # 6. Re-verify raw archive collision right before moving
        if raw_file.exists() and not is_recoverable_partial:
            raise FileExistsError(
                f"Destination archive file {raw_file} already exists."
            )

        # 7. Move original source file to archive
        if file_path.resolve() != raw_file.resolve() and file_path.exists():
            shutil.move(str(file_path), str(raw_file))
            source_moved = True
            logger.info("Original moved to: %s", raw_file)

        # 8. Atomically finalize output note
        temp_notes_file.replace(notes_file)
        note_finalized = True
        logger.info("Markdown finalized: %s", notes_file)

        # 9. Record completion in provenance ledger
        try:
            relative_output = str(notes_file.relative_to(resolved_paths["root"]))
        except ValueError:
            relative_output = str(notes_file)

        identity_store.record(
            source_identity,
            processing_config_id,
            "completed",
            output_path=relative_output,
        )

        print("[SUCCESS] Notes created and original archived.")
        return "success"

    except Exception as error:
        # Transaction rollback:
        # A. If source was moved to raw archive, but note finalization failed, roll source back to inbox!
        if source_moved and not note_finalized and raw_file.exists():
            try:
                shutil.move(str(raw_file), str(file_path))
                logger.info("Transaction rollback: restored source from %s back to %s", raw_file, file_path)
            except OSError as rollback_err:
                logger.error("Rollback failed to restore source to inbox: %s", rollback_err)

        # B. If note was finalized, but subsequent step failed, remove note to avoid orphan
        if note_finalized and not source_moved and notes_file.exists():
            try:
                notes_file.unlink()
                logger.info("Transaction rollback: removed uncompleted note %s", notes_file)
            except OSError:
                pass

        # C. Always clean up temporary file
        if temp_notes_file.exists():
            try:
                temp_notes_file.unlink()
            except OSError:
                pass

        try:
            try:
                relative_output = str(notes_file.relative_to(resolved_paths["root"]))
            except ValueError:
                relative_output = str(notes_file)

            identity_store.record(
                source_identity,
                processing_config_id,
                "failed",
                output_path=relative_output,
            )
        except (OSError, CorruptedLedgerError):
            logger.error(
                "Unable to save processing failure record for %s.",
                file_path.name,
            )

        logger.exception("Failed to process %s", file_path.name)
        print(f"[ERROR] Failed to process {file_path.name}: {error}")
        return "failed"


def process_register_photos(configuration=None, root=None):
    active_config = configuration or load_config()
    resolved_paths = get_nexus_paths(active_config, root=root)

    gateway = create_model_gateway(active_config)
    identity_store = ProcessingRecordStore(resolved_paths["provenance"])
    processing_config_id = get_processing_config_id(gateway)

    inbox_dir = resolved_paths["inbox"]
    if (inbox_dir / "register_photos").exists():
        inbox_dir = inbox_dir / "register_photos"

    semester_dir = resolved_paths["academic"]

    logger.info(
        "Starting %s process_notes v%s",
        NEXUS_NAME,
        PROCESSOR_VERSION,
    )

    print()
    print("=" * 64)
    print("                 NEXUS REGISTER PROCESSOR")
    print("                         v" + PROCESSOR_VERSION)
    print("=" * 64)
    print("Inbox:    " + str(inbox_dir))
    print("Output:   " + str(semester_dir))
    print("Provider: " + str(gateway.default_provider))
    print("Model:    " + str(gateway.default_model))
    print("=" * 64)

    if not inbox_dir.exists():
        logger.warning(
            "Inbox directory does not exist: %s",
            inbox_dir,
        )
        print()
        print("[WARNING] Inbox folder does not exist.")
        print("Nothing to process.")
        return

    try:
        files = sorted(
            [
                path
                for path in inbox_dir.iterdir()
                if path.is_file()
                and path.suffix.lower() in SUPPORTED_EXTENSIONS
            ],
            key=lambda path: path.name.lower(),
        )
    except OSError as error:
        logger.exception("Unable to read Inbox directory.")
        print()
        print(f"[ERROR] Unable to read Inbox directory: {error}")
        return

    if not files:
        print()
        print("[INFO] No supported register files found.")
        logger.info("No supported files found.")
        return

    print()
    print(f"Found {len(files)} file(s) to process.")

    successful = 0
    skipped = 0
    failed = 0

    for file_path in files:
        try:
            result = process_file(
                gateway,
                file_path,
                identity_store=identity_store,
                processing_config_id=processing_config_id,
                configuration=active_config,
                paths=resolved_paths,
            )

            if result == "success":
                successful += 1
            elif result == "skipped":
                skipped += 1
            elif result == "failed":
                failed += 1

        except KeyboardInterrupt:
            print()
            print("[INFO] Processing interrupted by user.")
            logger.info("Processing interrupted by user.")
            break

    print()
    print("=" * 64)
    print("                    PROCESSING SUMMARY")
    print("=" * 64)
    print(f"Successful: {successful}")
    print(f"Skipped:    {skipped}")
    print(f"Failed:     {failed}")
    print("=" * 64)

    logger.info(
        "Processing complete | successful=%s skipped=%s failed=%s",
        successful,
        skipped,
        failed,
    )


if __name__ == "__main__":
    try:
        process_register_photos()
    except KeyboardInterrupt:
        print()
        print("[INFO] Nexus Register Processor stopped.")
        logger.info("Processor interrupted by user.")
    except Exception as error:
        print()
        print(f"[FATAL] Unexpected processor error: {error}")
        logger.exception("Unexpected processor failure.")