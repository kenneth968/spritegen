"""Provider model suggestions for image generation and prompt improvement."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen


IMAGE_ROLE = "image"
PROMPT_ROLE = "prompt"
MODEL_ROLES = (IMAGE_ROLE, PROMPT_ROLE)
MODEL_VALIDATION_OK = "ok"
MODEL_VALIDATION_WARNING = "warning"
MODEL_VALIDATION_ERROR = "error"

OPENAI_IMAGE_MODELS_URL = "https://developers.openai.com/api/docs/models/gpt-image-2"
OPENAI_MODELS_URL = "https://developers.openai.com/api/docs/models"
OPENROUTER_IMAGE_DOCS_URL = (
    "https://openrouter.ai/docs/guides/overview/multimodal/image-generation"
)
OPENROUTER_MODELS_URL = "https://openrouter.ai/docs/guides/overview/models"
MODELS_DEV_API_URL = "https://models.dev/api.json"
MODELS_DEV_SEARCH_URL = "https://models.dev/?search=minim"
MODELS_DEV_OPENROUTER_SEARCH_URL = MODELS_DEV_SEARCH_URL
MODEL_DISCOVERY_SOURCES = ("auto", "openrouter", "models-dev")

PROVIDER_LABELS = {
    "mock": "Mock",
    "pollinations": "Pollinations",
    "openai": "OpenAI",
    "openrouter": "OpenRouter",
}


def provider_label(provider: str) -> str:
    return PROVIDER_LABELS.get(provider, provider.title())


@dataclass(frozen=True)
class ModelSuggestion:
    provider: str
    role: str
    model: str
    label: str
    note: str = ""
    source_url: str = ""


@dataclass(frozen=True)
class ModelValidationResult:
    provider: str
    role: str
    model: str
    status: str
    message: str
    suggestion: ModelSuggestion | None = None
    source_urls: tuple[str, ...] = ()


class ModelDiscoveryError(Exception):
    pass


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
        model="google/gemini-3.1-flash-image",
        label="Gemini 3.1 Flash Image",
        note="OpenRouter image-output model currently listed first for image generation.",
        source_url=OPENROUTER_IMAGE_DOCS_URL,
    ),
    ModelSuggestion(
        provider="openrouter",
        role=IMAGE_ROLE,
        model="google/gemini-3.1-flash-image-preview",
        label="Gemini 3.1 Flash Image Preview",
        note="OpenRouter image-output preview model retained for existing saved projects.",
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
        source_url=MODELS_DEV_SEARCH_URL,
    ),
)


def _fetch_json(url: str, timeout: int) -> dict:
    request = Request(url, headers={"User-Agent": "spritegen/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def model_suggestions(provider: str, role: str) -> list[ModelSuggestion]:
    return [
        suggestion
        for suggestion in MODEL_SUGGESTIONS
        if suggestion.provider == provider and suggestion.role == role
    ]


def default_model(provider: str, role: str) -> str:
    suggestions = model_suggestions(provider, role)
    return suggestions[0].model if suggestions else ""


def discover_model_suggestions(
    provider: str,
    role: str,
    search: str = "",
    limit: int = 20,
    timeout: int = 15,
    source: str = "auto",
) -> list[ModelSuggestion]:
    if role not in MODEL_ROLES:
        raise ValueError(f"Unknown model role: {role}")
    if source not in MODEL_DISCOVERY_SOURCES:
        raise ValueError(f"Unknown model discovery source: {source}")
    if source == "openrouter" and provider == "openrouter":
        return _discover_openrouter_models(role=role, search=search, limit=limit, timeout=timeout)
    if source == "openrouter":
        return []
    if source == "models-dev":
        return _discover_models_dev_models(
            provider=provider,
            role=role,
            search=search,
            limit=limit,
            timeout=timeout,
        )

    if provider != "openrouter":
        return _discover_models_dev_models(
            provider=provider,
            role=role,
            search=search,
            limit=limit,
            timeout=timeout,
        )

    openrouter_error: ModelDiscoveryError | None = None
    try:
        openrouter_results = _discover_openrouter_models(
            role=role,
            search=search,
            limit=limit,
            timeout=timeout,
        )
    except ModelDiscoveryError as exc:
        openrouter_error = exc
    else:
        if openrouter_results:
            return openrouter_results

    try:
        return _discover_models_dev_models(
            provider=provider,
            role=role,
            search=search,
            limit=limit,
            timeout=timeout,
        )
    except ModelDiscoveryError:
        if openrouter_error:
            raise openrouter_error
        raise


def combined_model_suggestions(
    provider: str,
    role: str,
    extra: list[ModelSuggestion] | tuple[ModelSuggestion, ...] = (),
) -> list[ModelSuggestion]:
    suggestions: list[ModelSuggestion] = []
    seen: set[str] = set()
    for suggestion in [*model_suggestions(provider, role), *extra]:
        if suggestion.model in seen:
            continue
        seen.add(suggestion.model)
        suggestions.append(suggestion)
    return suggestions


def validate_model_choice(
    provider: str,
    role: str,
    model: str,
    extra: list[ModelSuggestion] | tuple[ModelSuggestion, ...] = (),
    other_extra: list[ModelSuggestion] | tuple[ModelSuggestion, ...] = (),
) -> ModelValidationResult:
    if role not in MODEL_ROLES:
        raise ValueError(f"Unknown model role: {role}")

    model_id = model.strip()
    role_label = _role_label(role)
    provider_label = _provider_label(provider)
    if not model_id:
        return ModelValidationResult(
            provider=provider,
            role=role,
            model=model_id,
            status=MODEL_VALIDATION_ERROR,
            message=f"No {role_label} model selected",
            source_urls=tuple(model_source_urls(provider, role)),
        )

    suggestions = _suggestions_for_validation(provider, role, extra)
    suggestion = _find_model_suggestion(suggestions, model_id)
    if suggestion:
        return ModelValidationResult(
            provider=provider,
            role=role,
            model=model_id,
            status=MODEL_VALIDATION_OK,
            message=f"{model_id} is a known {provider_label} {role_label} model",
            suggestion=suggestion,
            source_urls=tuple(_validation_source_urls(provider, role, suggestion)),
        )

    other_role = PROMPT_ROLE if role == IMAGE_ROLE else IMAGE_ROLE
    other_suggestions = _suggestions_for_validation(provider, other_role, other_extra)
    other_suggestion = _find_model_suggestion(other_suggestions, model_id)
    if other_suggestion:
        other_role_label = _role_label(other_role)
        return ModelValidationResult(
            provider=provider,
            role=role,
            model=model_id,
            status=MODEL_VALIDATION_ERROR,
            message=(
                f"{model_id} is a known {provider_label} {other_role_label} model, "
                f"not {_role_article_label(role)}"
            ),
            suggestion=other_suggestion,
            source_urls=tuple(_validation_source_urls(provider, other_role, other_suggestion)),
        )

    other_provider_suggestion = _find_other_provider_suggestion(provider, role, model_id)
    if other_provider_suggestion:
        other_provider_label = _provider_label(other_provider_suggestion.provider)
        return ModelValidationResult(
            provider=provider,
            role=role,
            model=model_id,
            status=MODEL_VALIDATION_ERROR,
            message=(
                f"{model_id} is a known {other_provider_label} {role_label} model, "
                f"not {_provider_article_label(provider)} model"
            ),
            suggestion=other_provider_suggestion,
            source_urls=tuple(
                _validation_source_urls(
                    other_provider_suggestion.provider,
                    role,
                    other_provider_suggestion,
                )
            ),
        )

    return ModelValidationResult(
        provider=provider,
        role=role,
        model=model_id,
        status=MODEL_VALIDATION_WARNING,
        message=(
            f"Custom {provider_label} {role_label} model: {model_id}. "
            "This ID is not in the built-in or refreshed suggestions; use "
            "Refresh Models or models.dev to confirm it supports the selected role."
        ),
        source_urls=tuple(_custom_model_source_urls(provider, role)),
    )


def _suggestions_for_validation(
    provider: str,
    role: str,
    extra: list[ModelSuggestion] | tuple[ModelSuggestion, ...] = (),
) -> list[ModelSuggestion]:
    return [
        suggestion
        for suggestion in combined_model_suggestions(provider, role, extra)
        if suggestion.provider == provider and suggestion.role == role
    ]


def _find_model_suggestion(
    suggestions: list[ModelSuggestion],
    model: str,
) -> ModelSuggestion | None:
    for suggestion in suggestions:
        if suggestion.model == model:
            return suggestion
    return None


def _find_other_provider_suggestion(
    provider: str,
    role: str,
    model: str,
) -> ModelSuggestion | None:
    return _find_model_suggestion(
        [
            suggestion
            for suggestion in MODEL_SUGGESTIONS
            if suggestion.provider != provider and suggestion.role == role
        ],
        model,
    )


def _provider_label(provider: str) -> str:
    labels = {
        "mock": "Mock",
        "pollinations": "Pollinations",
        "openai": "OpenAI",
        "openrouter": "OpenRouter",
    }
    return labels.get(provider, provider.title())


def _provider_article_label(provider: str) -> str:
    article = "an" if provider in {"openai", "openrouter"} else "a"
    return f"{article} {_provider_label(provider)}"


def _role_label(role: str) -> str:
    return "image" if role == IMAGE_ROLE else "prompt"


def _role_article_label(role: str) -> str:
    return "an image model" if role == IMAGE_ROLE else "a prompt model"


def _validation_source_urls(
    provider: str,
    role: str,
    suggestion: ModelSuggestion | None = None,
) -> list[str]:
    urls = model_source_urls(provider, role)
    if suggestion and suggestion.source_url and suggestion.source_url not in urls:
        urls.append(suggestion.source_url)
    return urls


def _custom_model_source_urls(provider: str, role: str) -> list[str]:
    urls = model_source_urls(provider, role)
    for url in model_source_urls(provider):
        if url not in urls:
            urls.append(url)
    if provider == "openrouter" and MODELS_DEV_OPENROUTER_SEARCH_URL not in urls:
        urls.append(MODELS_DEV_OPENROUTER_SEARCH_URL)
    if not urls:
        urls.append("https://models.dev/")
    return urls


def _discover_openrouter_models(
    role: str,
    search: str = "",
    limit: int = 20,
    timeout: int = 15,
) -> list[ModelSuggestion]:
    output_modality = "image" if role == IMAGE_ROLE else "text"
    query = urlencode({"output_modalities": output_modality})
    url = f"https://openrouter.ai/api/v1/models?{query}"
    try:
        payload = _fetch_json(url, timeout)
    except Exception as exc:
        raise ModelDiscoveryError(f"Could not fetch OpenRouter models: {exc}") from exc

    data = payload.get("data", [])
    if not isinstance(data, list):
        raise ModelDiscoveryError("OpenRouter models response did not include a data list")

    results: list[ModelSuggestion] = []
    search_text = search.strip().lower()
    for item in data:
        if not isinstance(item, dict):
            continue
        suggestion = _openrouter_model_to_suggestion(item, role, output_modality)
        if suggestion is None:
            continue
        if search_text and search_text not in _suggestion_search_text(suggestion):
            continue
        results.append(suggestion)
        if len(results) >= limit:
            break
    return results


def _openrouter_model_to_suggestion(
    item: dict,
    role: str,
    output_modality: str,
) -> ModelSuggestion | None:
    model_id = str(item.get("id") or "").strip()
    if not model_id:
        return None
    architecture = item.get("architecture")
    if not isinstance(architecture, dict):
        return None
    outputs = [
        str(value)
        for value in architecture.get("output_modalities", [])
        if isinstance(value, str)
    ]
    if output_modality not in outputs:
        return None
    label = str(item.get("name") or model_id)
    description = str(item.get("description") or "").strip()
    note_parts = [f"Outputs: {','.join(outputs)}"]
    context_length = item.get("context_length")
    if isinstance(context_length, int) and context_length > 0:
        note_parts.append(f"context: {context_length:,} tokens")
    if description:
        note_parts.append(description[:160])
    return ModelSuggestion(
        provider="openrouter",
        role=role,
        model=model_id,
        label=label,
        note="; ".join(note_parts),
        source_url=OPENROUTER_MODELS_URL,
    )


def _discover_models_dev_models(
    provider: str,
    role: str,
    search: str = "",
    limit: int = 20,
    timeout: int = 15,
) -> list[ModelSuggestion]:
    output_modality = "image" if role == IMAGE_ROLE else "text"
    try:
        payload = _fetch_json(MODELS_DEV_API_URL, timeout)
    except Exception as exc:
        raise ModelDiscoveryError(f"Could not fetch models.dev catalog: {exc}") from exc

    catalog = payload.get(provider)
    if not isinstance(catalog, dict):
        return []
    models = catalog.get("models")
    if not isinstance(models, dict):
        raise ModelDiscoveryError(f"models.dev {provider} catalog did not include models")

    results: list[ModelSuggestion] = []
    search_text = search.strip().lower()
    for key, item in models.items():
        if not isinstance(item, dict):
            continue
        suggestion = _models_dev_model_to_suggestion(
            provider,
            key,
            item,
            role,
            output_modality,
            search=search,
        )
        if suggestion is None:
            continue
        if search_text and search_text not in _suggestion_search_text(suggestion):
            continue
        results.append(suggestion)
        if len(results) >= limit:
            break
    return results


def _models_dev_model_to_suggestion(
    provider: str,
    key: str,
    item: dict,
    role: str,
    output_modality: str,
    search: str = "",
) -> ModelSuggestion | None:
    model_id = str(item.get("id") or key).strip()
    if not model_id:
        return None
    modalities = item.get("modalities")
    if not isinstance(modalities, dict):
        return None
    outputs = [
        str(value)
        for value in modalities.get("output", [])
        if isinstance(value, str)
    ]
    if output_modality not in outputs:
        return None
    label = str(item.get("name") or model_id)
    note_parts = [f"Outputs: {','.join(outputs)}"]
    limits = item.get("limit")
    context = limits.get("context") if isinstance(limits, dict) else None
    if isinstance(context, int) and context > 0:
        note_parts.append(f"context: {context:,} tokens")
    release_date = str(item.get("release_date") or "").strip()
    if release_date:
        note_parts.append(f"released: {release_date}")
    last_updated = str(item.get("last_updated") or "").strip()
    if last_updated and last_updated != release_date:
        note_parts.append(f"updated: {last_updated}")
    return ModelSuggestion(
        provider=provider,
        role=role,
        model=model_id,
        label=label,
        note="; ".join(note_parts),
        source_url=_models_dev_search_url(search),
    )


def _models_dev_search_url(search: str = "") -> str:
    search_text = search.strip()
    if not search_text:
        return "https://models.dev/"
    return f"https://models.dev/?{urlencode({'search': search_text})}"


def _suggestion_search_text(suggestion: ModelSuggestion) -> str:
    return " ".join(
        [
            suggestion.provider,
            suggestion.role,
            suggestion.model,
            suggestion.label,
            suggestion.note,
        ]
    ).lower()


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
