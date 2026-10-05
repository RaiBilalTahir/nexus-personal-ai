import os
from typing import Mapping, Protocol

from .contracts import ErrorCategory, ModelError, ModelRequest, ModelResult


class ModelProvider(Protocol):
    provider_name: str

    def generate(self, request: ModelRequest) -> ModelResult:
        ...


class ModelGateway:
    def __init__(
        self,
        providers: Mapping[str, ModelProvider],
        default_provider: str,
        default_model: str | None = None,
    ):
        self._providers = dict(providers)
        self._default_provider = default_provider
        self._default_model = default_model

    def generate(self, request: ModelRequest) -> ModelResult:
        provider_name = request.provider or self._default_provider
        provider = self._providers.get(provider_name)

        if provider is None:
            return ModelResult.failure(
                provider=provider_name,
                model=request.model,
                error=ModelError(
                    category=ErrorCategory.UNSUPPORTED_CAPABILITY,
                    retryable=False,
                    detail="provider_not_registered",
                ),
            )

        return provider.generate(request)

    def provider_names(self):
        return tuple(self._providers)

    @property
    def default_provider(self):
        return self._default_provider

    @property
    def default_model(self):
        return self._default_model


def create_gateway(config, environ=None):
    from .providers.gemini import GeminiProvider

    environment = os.environ if environ is None else environ
    ai_config = config.get("ai", {})
    provider_name = ai_config.get("provider", "gemini")
    model_name = ai_config.get("model", "gemini-3.8-flash")

    providers = {
        "gemini": GeminiProvider(
            model=model_name,
            api_key=environment.get("GEMINI_API_KEY"),
        )
    }

    return ModelGateway(
        providers=providers,
        default_provider=provider_name,
        default_model=model_name,
    )
