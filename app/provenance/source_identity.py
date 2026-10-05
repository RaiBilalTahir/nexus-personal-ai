import hashlib
import json
import mimetypes
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class SourceIdentityError(ValueError):
    pass


class CorruptedLedgerError(RuntimeError):
    pass


class DuplicateClassification(str, Enum):
    NEW = "new"
    EXACT_DUPLICATE = "exact_duplicate"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    MODIFIED_VERSION = "modified_version"
    INVALID_UNREADABLE = "invalid_unreadable"


@dataclass(frozen=True)
class SourceIdentity:
    content_hash: str
    size_bytes: int
    extension: str
    mime_type: str
    filename: str
    relative_path: str
    modified_time_ns: int | None = None
    created_time_ns: int | None = None
    image_width: int | None = None
    image_height: int | None = None
    perceptual_hash: str | None = None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        return cls(**value)


@dataclass(frozen=True)
class ClassificationResult:
    classification: DuplicateClassification
    matching_record: dict[str, Any] | None = None
    reason: str = ""


@dataclass
class ProcessingRecordStore:
    path: Path

    def _load_records(self):
        if not self.path.exists():
            return []

        try:
            raw_text = self.path.read_text(encoding="utf-8")
        except OSError as error:
            raise CorruptedLedgerError(
                f"Unable to read processing ledger at {self.path}: {error}"
            ) from error

        try:
            value = json.loads(raw_text)
        except json.JSONDecodeError as error:
            # Preserve the corrupt evidence with a timestamped backup file
            backup_path = self.path.with_name(
                f"{self.path.stem}.corrupt.{int(time.time())}{self.path.suffix}.bak"
            )
            try:
                backup_path.write_text(raw_text, encoding="utf-8")
            except OSError:
                pass
            raise CorruptedLedgerError(
                f"Processing ledger at {self.path} is corrupted and cannot be parsed as JSON: {error}. "
                f"Original corrupted data preserved at {backup_path}."
            ) from error

        if not isinstance(value, dict) or "records" not in value:
            raise CorruptedLedgerError(
                f"Processing ledger at {self.path} has invalid format: expected dict with 'records' key."
            )

        records = value.get("records", [])
        if not isinstance(records, list):
            raise CorruptedLedgerError(
                f"Processing ledger at {self.path} has invalid format: 'records' must be a list."
            )

        return records

    def _save_records(self, records):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "records": records}

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.path.parent,
            prefix=self.path.name + ".",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            json.dump(payload, temporary, indent=2)
            temporary.write("\n")
            temporary_path = Path(temporary.name)

        os.replace(temporary_path, self.path)

    def classify(self, identity: SourceIdentity, processing_config_id: str):
        records = self._load_records()

        exact_matches = [
            record
            for record in records
            if record.get("source", {}).get("content_hash")
            == identity.content_hash
        ]
        if exact_matches:
            return ClassificationResult(
                classification=DuplicateClassification.EXACT_DUPLICATE,
                matching_record=exact_matches[-1],
                reason="content_hash_matches_existing_source",
            )

        same_name = [
            record
            for record in records
            if record.get("source", {}).get("filename", "").casefold()
            == identity.filename.casefold()
            and record.get("source", {}).get("mime_type") == identity.mime_type
        ]
        if same_name:
            return ClassificationResult(
                classification=DuplicateClassification.MODIFIED_VERSION,
                matching_record=same_name[-1],
                reason="filename_and_mime_match_but_content_hash_differs",
            )

        same_shape = [
            record
            for record in records
            if record.get("source", {}).get("mime_type") == identity.mime_type
            and record.get("source", {}).get("size_bytes") == identity.size_bytes
        ]
        if same_shape:
            return ClassificationResult(
                classification=DuplicateClassification.POSSIBLE_DUPLICATE,
                matching_record=same_shape[-1],
                reason="mime_type_and_size_match_but_content_hash_differs",
            )

        return ClassificationResult(
            classification=DuplicateClassification.NEW,
            reason="no_matching_source_record",
        )

    def find_record(self, content_hash: str, processing_config_id: str):
        matches = [
            record
            for record in self._load_records()
            if record.get("source", {}).get("content_hash") == content_hash
            and record.get("processing_config_id") == processing_config_id
        ]
        return matches[-1] if matches else None

    def record(
        self,
        identity: SourceIdentity,
        processing_config_id: str,
        status: str,
        output_path: str | None = None,
    ):
        records = self._load_records()
        records.append(
            {
                "source": identity.to_dict(),
                "processing_config_id": processing_config_id,
                "status": status,
                "output_path": output_path,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._save_records(records)

    def is_completed(self, identity: SourceIdentity, processing_config_id: str):
        record = self.find_record(identity.content_hash, processing_config_id)
        return bool(record and record.get("status") == "completed")


def calculate_source_identity(path: Path, root: Path | None = None):
    try:
        if not path.is_file():
            raise SourceIdentityError("source_is_not_a_file")

        stat = path.stat()
        digest = hashlib.sha256()
        with path.open("rb") as source_file:
            while chunk := source_file.read(1024 * 1024):
                digest.update(chunk)

        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        relative_path = str(path)
        if root is not None:
            try:
                relative_path = str(path.resolve().relative_to(root.resolve()))
            except ValueError:
                relative_path = str(path.resolve())

        width, height = _image_dimensions(path, mime_type)
        return SourceIdentity(
            content_hash=digest.hexdigest(),
            size_bytes=stat.st_size,
            extension=path.suffix.lower(),
            mime_type=mime_type,
            filename=path.name,
            relative_path=relative_path,
            modified_time_ns=getattr(stat, "st_mtime_ns", None),
            created_time_ns=getattr(stat, "st_ctime_ns", None),
            image_width=width,
            image_height=height,
        )
    except SourceIdentityError:
        raise
    except (OSError, ValueError) as error:
        raise SourceIdentityError(type(error).__name__) from error


def classify_source(path: Path, store: ProcessingRecordStore, processing_config_id: str, root: Path | None = None):
    try:
        identity = calculate_source_identity(path, root)
    except SourceIdentityError as error:
        return None, ClassificationResult(
            classification=DuplicateClassification.INVALID_UNREADABLE,
            reason=str(error),
        )

    return identity, store.classify(identity, processing_config_id)


def calculate_processing_config_id(
    capability: str,
    pipeline_version: str,
    schema_version: str,
    provider: str,
    model: str,
):
    value = {
        "capability": capability,
        "pipeline_version": pipeline_version,
        "schema_version": schema_version,
        "provider": provider,
        "model": model,
    }
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _image_dimensions(path: Path, mime_type: str):
    try:
        if mime_type == "image/png":
            with path.open("rb") as source_file:
                header = source_file.read(24)
            if header[:8] == b"\x89PNG\r\n\x1a\n":
                return int.from_bytes(header[16:20], "big"), int.from_bytes(
                    header[20:24], "big"
                )

        if mime_type == "image/jpeg":
            return _jpeg_dimensions(path)
    except (OSError, ValueError, IndexError):
        pass

    return None, None


def _jpeg_dimensions(path: Path):
    with path.open("rb") as source_file:
        data = source_file.read()

    if data[:2] != b"\xff\xd8":
        return None, None

    position = 2
    while position + 9 < len(data):
        if data[position] != 0xFF:
            position += 1
            continue

        marker = data[position + 1]
        position += 2
        if marker in (0xD8, 0xD9):
            continue
        if position + 2 > len(data):
            break

        segment_length = int.from_bytes(data[position:position + 2], "big")
        if segment_length < 2 or position + segment_length > len(data):
            break

        if marker in range(0xC0, 0xC4) or marker in range(0xC5, 0xC8):
            height = int.from_bytes(data[position + 3:position + 5], "big")
            width = int.from_bytes(data[position + 5:position + 7], "big")
            return width, height

        position += segment_length

    return None, None
