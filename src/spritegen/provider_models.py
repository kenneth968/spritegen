"""Provider model suggestions for image generation and prompt improvement."""

from __future__ import annotations

from dataclasses import dataclass


IMAGE_ROLE = "image"
PROMPT_ROLE = "prompt"
MODEL_ROLES = (IMAGE_ROLE, PROMPT_ROLE)

OPENAI_IMAGE_MODELS_URL = "https://developers.openai.com/api/docs/models/gpt-image-2"
OPENAI_MODELS_URL = "https://developers.openai.com/api/docs/models"
OPENROUTER_IMAGE_DOCS_URL = (
    "https://openrouter.ai/docs/guides/overview/multimodal/image-generation"
)
OPENROUTER_MODELS_URL = "https://openrouter.ai/docs/guides/overview/models"
MODELS_DEV_OPENROUTER_SEARCH_URL = "https://models.dev/?search=minim"


@dataclass(frozen=True)
class ModelSuggestion:
    provider: str
    role: str
    model: str
    label: str
    note: str = ""
    source_url: str = ""


MODEL_SUGGESTIONS: tuple[ModelSuggestion, ...] = (
    ModelSuggestion(
        provider="mock",
        role=IMAGE_ROLE,
        model="mock",
        label="Mock image generator",
        note="Local deterministic image output for testing.",
    ),
    ModelSuggestion(
        provider="mock",
        role=PROMPT_ROLE,
        model="mock",
        label="Mock prompt improver",
        note="Local deterministic prompt improvement for testing.",
    ),
    ModelSuggestion(
        provider="pollinations",
        role=IMAGE_ROLE,
        model="flux",
        label="Pollinations Flux",
        note="Simple no-key image generation path.",
    ),
    ModelSuggestion(
        provider="pollinations",
        role=PROMPT_ROLE,
        model="openai",
        label="Pollinations OpenAI-compatible text",
        note="Simple no-key prompt improvement path.",
    ),
    ModelSuggestion(
        provider="openai",
        role=IMAGE_ROLE,
        model="gpt-image-2",
        label="GPT Image 2",
        note="OpenAI state-of-the-art image generation model.",
        source_url=OPENAI_IMAGE_MODELS_URL,
    ),
    ModelSuggestion(
        provider="openai",
        role=PROMPT_ROLE,
        model="gpt-5.5",
        label="GPT-5.5",
        note="OpenAI frontier model for complex prompt improvement.",
        source_url=OPENAI_MODELS_URL,
    ),
    ModelSuggestion(
        provider="openai",
        role=PROMPT_ROLE,
        model="gpt-5.4",
        label="GPT-5.4",
        note="More affordable OpenAI model for prompt improvement.",
        source_url=OPENAI_MODELS_URL,
    ),
    ModelSuggestion(
        provider="openrouter",
        role=IMAGE_ROLE,
        model="google/gemini-3.1-flash-image-preview",
        label="Gemini 3.1 Flash Image Preview",
        note="OpenRouter image-output model with extended aspect-ratio support.",
        source_url=OPENROUTER_IMAGE_DOCS_URL,
    ),
    ModelSuggestion(
        provider="openrouter",
        role=IMAGE_ROLE,
        model="openai/gpt-5.4-image-2",
        label="GPT-5.4 Image 2 via OpenRouter",
        note="OpenRouter image-output model discovered through output_modalities=image.",
        source_url=OPENROUTER_MODELS_URL,
    ),
    ModelSuggestion(
        provider="openrouter",
        role=IMAGE_ROLE,
        model="recraft/recraft-v4.1",
        label="Recraft V4.1",
        note="OpenRouter image-output model for direct image generation.",
        source_url=OPENROUTER_MODELS_URL,
    ),
    ModelSuggestion(
        provider="openrouter",
        role=IMAGE_ROLE,
        model="black-forest-labs/flux.2-klein-4b",
        label="FLUX.2 Klein 4B",
        note="OpenRouter image-output model.",
        source_url=OPENROUTER_MODELS_URL,
    ),
    ModelSuggestion(
        provider="openrouter",
        role=PROMPT_ROLE,
        model="openai/gpt-5.5",
        label="OpenAI GPT-5.5 via OpenRouter",
        note="Strong prompt rewriting model when available in your OpenRouter account.",
        source_url=OPENROUTER_MODELS_URL,
    ),
    ModelSuggestion(
        provider="openrouter",
        role=PROMPT_ROLE,
        model="minimax/minimax-m2.7",
        label="MiniMax M2.7 via OpenRouter",
        note="Useful OpenRouter text model candidate for prompt rewriting.",
        source_url=MODELS_DEV_OPENROUTER_SEARCH_URL,
    ),
)


def model_suggestions(provider: str, role: str) -> list[ModelSuggestion]:
    return [
        suggestion
        for suggestion in MODEL_SUGGESTIONS
        if suggestion.provider == provider and suggestion.role == role
    ]


def default_model(provider: str, role: str) -> str:
    suggestions = model_suggestions(provider, role)
    return suggestions[0].model if suggestions else ""


def model_source_urls(
    provider: str | None = None,
    role: str | None = None,
) -> list[str]:
    urls = []
    for suggestion in MODEL_SUGGESTIONS:
        if provider and suggestion.provider != provider:
            continue
        if role and suggestion.role != role:
            continue
        if suggestion.source_url and suggestion.source_url not in urls:
            urls.append(suggestion.source_url)
    return urls
