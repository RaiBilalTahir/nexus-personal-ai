from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class ErrorCategory(str, Enum):
    MISSING_CREDENTIALS = "missing_credentials"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    INVALID_REQUEST = "invalid_request"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    AUTHENTICATION_FAILED = "authentication_failed"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    INVALID_RESPONSE = "invalid_response"
    UNKNOWN_PROVIDER_ERROR = "unknown_provider_error"


@dataclass(frozen=True)
class ImageInput:
    data: bytes
    mime_type: str
    name: str | None = None

    def __post_init__(self):
        if not isinstance(self.data, bytes) or not self.data:
            raise ValueError("Image data must be non-empty bytes.")
        if not isinstance(self.mime_type, str) or not self.mime_type.startswith("image/"):
            raise ValueError("Image MIME type must start with 'image/'.")


@dataclass(frozen=True)
class DocumentInput:
    data: bytes
    mime_type: str
    name: str | None = None

    def __post_init__(self):
        if not isinstance(self.data, bytes) or not self.data:
            raise ValueError("Document data must be non-empty bytes.")
        if not isinstance(self.mime_type, str) or not self.mime_type:
            raise ValueError("Document MIME type must be non-empty text.")


@dataclass(frozen=True)
class StructuredOutput:
    schema: Mapping[str, Any]
    name: str = "response"

    def __post_init__(self):
        if not isinstance(self.schema, Mapping) or not self.schema:
            raise ValueError("Structured output schema must be a non-empty mapping.")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Structured output name must be non-empty text.")


@dataclass(frozen=True)
class ModelRequest:
    text: str | None = None
    images: tuple[ImageInput, ...] = ()
    documents: tuple[DocumentInput, ...] = ()
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    timeout_seconds: float = 60.0
    structured_output: StructuredOutput | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self):
        images = tuple(self.images)
        object.__setattr__(self, "images", images)
        documents = tuple(self.documents)
        object.__setattr__(self, "documents", documents)

        if self.text is not None and not isinstance(self.text, str):
            raise ValueError("Model text must be text or None.")
        if not self.text and not images and not documents:
            raise ValueError(
                "A model request must contain text, an image, or a document."
            )
        if self.provider is not None and not self.provider.strip():
            raise ValueError("Provider must be non-empty text when provided.")
        if self.model is not None and not self.model.strip():
            raise ValueError("Model must be non-empty text when provided.")
        if self.temperature is not None and not 0 <= self.temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2.")
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be greater than zero.")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("Request metadata must be a mapping.")


@dataclass(frozen=True)
class ModelError:
    category: ErrorCategory
    retryable: bool
    detail: str | None = None


@dataclass(frozen=True)
class ModelResult:
    success: bool
    provider: str
    model: str | None
    text: str | None = None
    data: Any = None
    usage: Mapping[str, Any] = field(default_factory=dict)
    latency_ms: float | None = None
    error: ModelError | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.success and self.error is not None:
            raise ValueError("Successful results cannot contain an error.")
        if not self.success and self.error is None:
            raise ValueError("Failed results must contain an error.")

    @classmethod
    def failure(
        cls,
        provider: str,
        model: str | None,
        error: ModelError,
        latency_ms: float | None = None,
    ):
        return cls(
            success=False,
            provider=provider,
            model=model,
            error=error,
            latency_ms=latency_ms,
        )
