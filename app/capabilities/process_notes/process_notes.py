import json
import hashlib
import logging
import shutil
import sys
from pathlib import Path

NEXUS_NAME = "Nexus"
PROCESSOR_VERSION = "1.1.1"

NEXUS_ROOT = Path(__file__).resolve().parents[3]
if str(NEXUS_ROOT) not in sys.path:
    sys.path.insert(0, str(NEXUS_ROOT))

from app.models import (
    DocumentInput,
    ErrorCategory,
    ImageInput,
    ModelError,
    ModelRequest,
)
from app.models.gateway import create_gateway
from app.provenance import (
    DuplicateClassification,
    ProcessingRecordStore,
    classify_source,
    calculate_processing_config_id,
    calculate_source_identity,
)


INBOX_DIR = NEXUS_ROOT / "data" / "inbox" / "register_photos"
SEMESTER_DIR = (
    NEXUS_ROOT
    / "data"
    / "knowledge"
    / "academic"
    / "Semester1"
)

LOGS_DIR = NEXUS_ROOT / "logs"
LOG_FILE = LOGS_DIR / "process_notes.log"
CONFIG_FILE = NEXUS_ROOT / "config" / "nexus_config.json"
PROCESSING_RECORD_FILE = NEXUS_ROOT / "data" / "provenance" / "processing_records.json"

SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf"
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
    "Pak-Study": "Ideology and Constitution of Pakistan"
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


LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("nexus.process_notes")


class ModelGatewayFailure(RuntimeError):
    def __init__(self, error):
        self.error = error
        super().__init__(error.category.value)


def load_configuration():
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            configuration = json.load(file)

        if not isinstance(configuration, dict):
            raise ValueError("Configuration must contain a JSON object.")

        return configuration

    except (OSError, json.JSONDecodeError, ValueError) as error:
        logger.warning(
            "Unable to load Nexus configuration for Model Gateway: %s",
            type(error).__name__,
        )
        return {}


def create_model_gateway(configuration=None, environ=None):
    if configuration is None:
        configuration = load_configuration()

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


def get_destination_directories(course_name):
    course_dir = SEMESTER_DIR / course_name
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
        file_path.name
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
):
    course_name = get_course_from_filename(
        file_path.name
    )

    if not course_name:
        logger.warning(
            "Skipping %s: filename prefix is not in COURSE_MAP.",
            file_path.name
        )

        print(
            f"[SKIP] Unknown course prefix: {file_path.name}"
        )

        return "skipped"

    raw_dir, notes_dir = get_destination_directories(
        course_name
    )

    notes_file = notes_dir / (
        file_path.stem + ".md"
    )

    raw_file = raw_dir / file_path.name

    identity_store = identity_store or ProcessingRecordStore(
        PROCESSING_RECORD_FILE
    )
    processing_config_id = processing_config_id or get_processing_config_id(
        gateway
    )

    source_identity, classification = classify_source(
        file_path,
        identity_store,
        processing_config_id,
        NEXUS_ROOT,
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

    if identity_store.is_completed(source_identity, processing_config_id):
        print("[SKIP] Exact source already processed with this configuration.")
        return "skipped"

    if classification.classification == DuplicateClassification.POSSIBLE_DUPLICATE:
        print("[REVIEW] Possible duplicate detected; source was not processed.")
        return "skipped"

    if notes_file.exists() and not (
        previous_record and previous_record.get("status") in {"failed", "partial"}
    ):
        logger.info(
            "Skipping existing Markdown output without a completed identity record: %s",
            notes_file,
        )
        print("[SKIP] Markdown output already exists; review required.")
        return "skipped"

    print()
    print(
        f"Processing: {file_path.name}"
    )

    print(
        f"Course:     {course_name}"
    )

    try:
        markdown_text = transcribe_file(
            gateway,
            file_path
        )

        raw_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        notes_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        notes_file.write_text(
            markdown_text + "\n",
            encoding="utf-8"
        )

        logger.info(
            "Markdown saved: %s",
            notes_file
        )

        if raw_file.exists():
            raise FileExistsError(
                "An archived original already exists at: "
                + str(raw_file)
            )

        shutil.move(
            str(file_path),
            str(raw_file)
        )

        logger.info(
            "Original moved to: %s",
            raw_file
        )

        identity_store.record(
            source_identity,
            processing_config_id,
            "completed",
            output_path=str(notes_file.relative_to(NEXUS_ROOT)),
        )

        print(
            "[SUCCESS] Notes created and original archived."
        )

        return "success"

    except Exception as error:
        try:
            identity_store.record(
                source_identity,
                processing_config_id,
                "failed",
                output_path=str(notes_file.relative_to(NEXUS_ROOT)),
            )
        except OSError:
            logger.error(
                "Unable to save processing failure record for %s.",
                file_path.name,
            )

        logger.exception(
            "Failed to process %s",
            file_path.name
        )

        print(
            "[ERROR] Failed to process "
            + file_path.name
            + ":"
        )

        print(
            "        " + str(error)
        )

        return "failed"


def process_register_photos():
    configuration = load_configuration()
    gateway = create_model_gateway(configuration)
    identity_store = ProcessingRecordStore(PROCESSING_RECORD_FILE)
    processing_config_id = get_processing_config_id(gateway)
    logger.info(
        "Starting %s process_notes v%s",
        NEXUS_NAME,
        PROCESSOR_VERSION
    )

    print()
    print("=" * 64)
    print("                 NEXUS REGISTER PROCESSOR")
    print("                         v" + PROCESSOR_VERSION)
    print("=" * 64)
    print(
        "Inbox:  " + str(INBOX_DIR)
    )
    print(
        "Output: " + str(SEMESTER_DIR)
    )
    print(
        "Provider: " + str(gateway.default_provider)
    )
    print(
        "Model:    " + str(gateway.default_model)
    )
    print("=" * 64)

    if not INBOX_DIR.exists():
        logger.warning(
            "Register Photos directory does not exist: %s",
            INBOX_DIR
        )

        print()
        print(
            "[WARNING] Register Photos folder does not exist."
        )

        print(
            "Nothing to process."
        )

        return

    try:
        files = sorted(
            [
                path
                for path in INBOX_DIR.iterdir()
                if path.is_file()
                and path.suffix.lower()
                in SUPPORTED_EXTENSIONS
            ],
            key=lambda path: path.name.lower()
        )

    except OSError as error:
        logger.exception(
            "Unable to read Inbox directory."
        )

        print()
        print(
            "[ERROR] Unable to read Inbox directory:"
        )

        print(
            str(error)
        )

        return

    if not files:
        print()
        print(
            "[INFO] No supported register files found."
        )

        logger.info(
            "No supported files found."
        )

        return

    print()
    print(
        "Found " + str(len(files)) + " file(s) to process."
    )

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
            )

            if result == "success":
                successful += 1

            elif result == "skipped":
                skipped += 1

            elif result == "failed":
                failed += 1

        except KeyboardInterrupt:
            print()
            print(
                "[INFO] Processing interrupted by user."
            )

            logger.info(
                "Processing interrupted by user."
            )

            break

    print()
    print("=" * 64)
    print("                    PROCESSING SUMMARY")
    print("=" * 64)
    print(
        "Successful: " + str(successful)
    )
    print(
        "Skipped:    " + str(skipped)
    )
    print(
        "Failed:     " + str(failed)
    )
    print("=" * 64)

    logger.info(
        "Processing complete | successful=%s skipped=%s failed=%s",
        successful,
        skipped,
        failed
    )


if __name__ == "__main__":
    try:
        process_register_photos()

    except KeyboardInterrupt:
        print()
        print(
            "[INFO] Nexus Register Processor stopped."
        )

        logger.info(
            "Processor interrupted by user."
        )

    except Exception as error:
        print()
        print(
            "[FATAL] Unexpected processor error:"
        )

        print(
            str(error)
        )

        logger.exception(
            "Unexpected processor failure."
        )