import base64
import json
import os
import time
from typing import Any

from google import genai

from ..contracts import (
    ErrorCategory,
    ModelError,
    ModelRequest,
    ModelResult,
)


class GeminiProvider:
    provider_name = "gemini"

    def __init__(self, model="gemini-3.8-flash", api_key=None, client=None):
        self.model = model
        self._api_key = (
            api_key if api_key is not None else os.environ.get("GEMINI_API_KEY")
        )
        self._client = client

    def generate(self, request: ModelRequest) -> ModelResult:
        model = request.model or self.model
        started_at = time.perf_counter()

        if not self._api_key and self._client is None:
            return ModelResult.failure(
                provider=self.provider_name,
                model=model,
                error=ModelError(
                    category=ErrorCategory.MISSING_CREDENTIALS,
                    retryable=False,
                    detail="GEMINI_API_KEY",
                ),
                latency_ms=self._elapsed_ms(started_at),
            )

        try:
            client = self._client or genai.Client(api_key=self._api_key)
            interaction_kwargs: dict[str, Any] = {
                "model": model,
                "input": self._build_input(request),
            }

            if request.structured_output is not None:
                interaction_kwargs["response_format"] = {
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": request.structured_output.schema,
                }

            response = client.interactions.create(
                timeout=request.timeout_seconds,
                **interaction_kwargs,
            )
            text = getattr(response, "output_text", None)

            if not isinstance(text, str):
                return ModelResult.failure(
                    provider=self.provider_name,
                    model=model,
                    error=ModelError(
                        category=ErrorCategory.INVALID_RESPONSE,
                        retryable=False,
                        detail="missing_output_text",
                    ),
                    latency_ms=self._elapsed_ms(started_at),
                )

            data = None
            if request.structured_output is not None:
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    return ModelResult.failure(
                        provider=self.provider_name,
                        model=model,
                        error=ModelError(
                            category=ErrorCategory.INVALID_RESPONSE,
                            retryable=False,
                            detail="structured_output_not_json",
                        ),
                        latency_ms=self._elapsed_ms(started_at),
                    )

            return ModelResult(
                success=True,
                provider=self.provider_name,
                model=model,
                text=text,
                data=data,
                usage=self._usage_from_response(response),
                latency_ms=self._elapsed_ms(started_at),
            )

        except Exception as error:
            return ModelResult.failure(
                provider=self.provider_name,
                model=model,
                error=self._map_error(error),
                latency_ms=self._elapsed_ms(started_at),
            )

    @staticmethod
    def _build_input(request: ModelRequest):
        contents = []

        if request.text:
            contents.append({"type": "text", "text": request.text})

        for image in request.images:
            contents.append(
                {
                    "type": "image",
                    "data": base64.b64encode(image.data).decode("ascii"),
                    "mime_type": image.mime_type,
                }
            )

        for document in request.documents:
            contents.append(
                {
                    "type": "document",
                    "data": base64.b64encode(document.data).decode("ascii"),
                    "mime_type": document.mime_type,
                }
            )

        return contents

    @staticmethod
    def _usage_from_response(response):
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return {}

        values = {}
        for name in (
            "prompt_token_count",
            "candidates_token_count",
            "total_token_count",
        ):
            value = getattr(usage, name, None)
            if value is not None:
                values[name] = value
        return values

    @staticmethod
    def _elapsed_ms(started_at):
        return (time.perf_counter() - started_at) * 1000

    @staticmethod
    def _map_error(error):
        error_name = type(error).__name__.lower()
        error_text = str(error).lower()

        if "timeout" in error_name or "timeout" in error_text:
            category = ErrorCategory.TIMEOUT
            retryable = True
        elif "429" in error_text or "rate" in error_text or "quota" in error_text:
            category = ErrorCategory.RATE_LIMITED
            retryable = True
        elif "auth" in error_name or "permission" in error_text or "api key" in error_text:
            category = ErrorCategory.AUTHENTICATION_FAILED
            retryable = False
        elif "connection" in error_name or "unavailable" in error_text:
            category = ErrorCategory.PROVIDER_UNAVAILABLE
            retryable = True
        else:
            category = ErrorCategory.UNKNOWN_PROVIDER_ERROR
            retryable = False

        return ModelError(
            category=category,
            retryable=retryable,
            detail=type(error).__name__,
        )
