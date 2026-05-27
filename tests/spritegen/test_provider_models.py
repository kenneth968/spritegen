from __future__ import annotations

import sys


def test_provider_model_catalog_exposes_defaults_and_sources():
    from spritegen.provider_models import (
        IMAGE_ROLE,
        PROMPT_ROLE,
        default_model,
        model_source_urls,
        model_suggestions,
    )

    assert default_model("openai", IMAGE_ROLE) == "gpt-image-2"
    assert default_model("openrouter", IMAGE_ROLE) == "google/gemini-3.1-flash-image-preview"
    assert default_model("openrouter", PROMPT_ROLE) == "openai/gpt-5.5"

    openrouter_image_models = {
        suggestion.model
        for suggestion in model_suggestions("openrouter", IMAGE_ROLE)
    }
    assert "google/gemini-3.1-flash-image-preview" in openrouter_image_models
    assert "openai/gpt-5.4-image-2" in openrouter_image_models

    sources = model_source_urls("openrouter")
    assert "https://openrouter.ai/docs/guides/overview/models" in sources
    assert "https://models.dev/?search=minim" in sources

    image_sources = model_source_urls("openrouter", IMAGE_ROLE)
    prompt_sources = model_source_urls("openrouter", PROMPT_ROLE)
    assert "https://openrouter.ai/docs/guides/overview/multimodal/image-generation" in image_sources
    assert "https://openrouter.ai/docs/guides/overview/multimodal/image-generation" not in prompt_sources


def test_openrouter_online_discovery_filters_by_role_and_search(monkeypatch):
    from spritegen import provider_models
    from spritegen.provider_models import (
        IMAGE_ROLE,
        PROMPT_ROLE,
        combined_model_suggestions,
        discover_model_suggestions,
    )

    payload = {
        "data": [
            {
                "id": "google/gemini-3.1-flash-image-preview",
                "name": "Google: Nano Banana 2",
                "description": "Image generation model",
                "context_length": 1000000,
                "architecture": {"output_modalities": ["image", "text"]},
            },
            {
                "id": "minimax/minimax-m2.7",
                "name": "MiniMax: MiniMax M2.7",
                "description": "Text generation model",
                "context_length": 200000,
                "architecture": {"output_modalities": ["text"]},
            },
            {
                "id": "image-only/example",
                "name": "Image Only Example",
                "description": "Unrelated image model",
                "architecture": {"output_modalities": ["image"]},
            },
        ]
    }

    captured_urls = []

    def fake_fetch_json(url, timeout):
        captured_urls.append(url)
        assert timeout == 7
        return payload

    monkeypatch.setattr(provider_models, "_fetch_json", fake_fetch_json)

    image_results = discover_model_suggestions(
        "openrouter",
        IMAGE_ROLE,
        search="banana",
        limit=10,
        timeout=7,
    )
    prompt_results = discover_model_suggestions(
        "openrouter",
        PROMPT_ROLE,
        search="minimax",
        limit=10,
        timeout=7,
    )

    assert [suggestion.model for suggestion in image_results] == [
        "google/gemini-3.1-flash-image-preview"
    ]
    assert image_results[0].label == "Google: Nano Banana 2"
    assert "image,text" in image_results[0].note
    assert [suggestion.model for suggestion in prompt_results] == [
        "minimax/minimax-m2.7"
    ]
    assert "output_modalities=image" in captured_urls[0]
    assert "output_modalities=text" in captured_urls[1]

    combined = combined_model_suggestions(
        "openrouter",
        IMAGE_ROLE,
        image_results,
    )
    models = [suggestion.model for suggestion in combined]
    assert models.count("google/gemini-3.1-flash-image-preview") == 1
    assert "openai/gpt-5.4-image-2" in models


def test_models_dev_discovery_uses_openrouter_model_ids(monkeypatch):
    from spritegen import provider_models
    from spritegen.provider_models import PROMPT_ROLE, discover_model_suggestions

    payload = {
        "openrouter": {
            "models": {
                "minimax/minimax-m2.7": {
                    "id": "minimax/minimax-m2.7",
                    "name": "MiniMax-M2.7",
                    "modalities": {"input": ["text"], "output": ["text"]},
                    "limit": {"context": 196608},
                    "release_date": "2026-03-18",
                },
                "google/gemini-3.1-flash-image-preview": {
                    "id": "google/gemini-3.1-flash-image-preview",
                    "name": "Nano Banana 2",
                    "modalities": {"input": ["text", "image"], "output": ["image", "text"]},
                },
            }
        }
    }

    def fake_fetch_json(url, timeout):
        assert url == "https://models.dev/api.json"
        assert timeout == 9
        return payload

    monkeypatch.setattr(provider_models, "_fetch_json", fake_fetch_json)

    results = discover_model_suggestions(
        "openrouter",
        PROMPT_ROLE,
        search="minimax",
        limit=10,
        timeout=9,
        source="models-dev",
    )

    assert [suggestion.model for suggestion in results] == ["minimax/minimax-m2.7"]
    assert results[0].label == "MiniMax-M2.7"
    assert "context: 196,608 tokens" in results[0].note
    assert results[0].source_url == "https://models.dev/?search=minimax"


def test_models_dev_discovery_can_return_openai_model_ids(monkeypatch):
    from spritegen import provider_models
    from spritegen.provider_models import IMAGE_ROLE, PROMPT_ROLE, discover_model_suggestions

    payload = {
        "openai": {
            "models": {
                "gpt-image-1.5": {
                    "id": "gpt-image-1.5",
                    "name": "gpt-image-1.5",
                    "modalities": {"input": ["text", "image"], "output": ["text", "image"]},
                    "limit": {"context": 32000},
                    "last_updated": "2025-11-25",
                },
                "gpt-5.5": {
                    "id": "gpt-5.5",
                    "name": "GPT-5.5",
                    "modalities": {"input": ["text", "image"], "output": ["text"]},
                    "limit": {"context": 400000},
                    "last_updated": "2026-04-23",
                },
            }
        }
    }

    monkeypatch.setattr(provider_models, "_fetch_json", lambda url, timeout: payload)

    image_results = discover_model_suggestions(
        "openai",
        IMAGE_ROLE,
        search="image",
        source="models-dev",
    )
    prompt_results = discover_model_suggestions(
        "openai",
        PROMPT_ROLE,
        search="gpt-5.5",
        source="auto",
    )

    assert [suggestion.model for suggestion in image_results] == ["gpt-image-1.5"]
    assert image_results[0].provider == "openai"
    assert image_results[0].source_url == "https://models.dev/?search=image"
    assert [suggestion.model for suggestion in prompt_results] == ["gpt-5.5"]
    assert "context: 400,000 tokens" in prompt_results[0].note


def test_cli_lists_suggested_models(monkeypatch, capsys):
    from spritegen.cli import main

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "spritegen",
            "models",
            "--provider",
            "openrouter",
            "--role",
            "image",
        ],
    )

    assert main() == 0

    output = capsys.readouterr().out
    assert "OpenRouter image model suggestions" in output
    assert "google/gemini-3.1-flash-image-preview" in output
    assert "openai/gpt-5.4-image-2" in output
    assert "https://openrouter.ai/docs/guides/overview/models" in output


def test_cli_lists_online_model_results(monkeypatch, capsys):
    from spritegen import cli
    from spritegen.cli import main
    from spritegen.provider_models import IMAGE_ROLE, ModelSuggestion

    def fake_discover(provider, role, search="", limit=20, timeout=15, source="auto"):
        assert provider == "openrouter"
        assert role == IMAGE_ROLE
        assert search == "banana"
        assert limit == 5
        assert source == "auto"
        return [
            ModelSuggestion(
                provider="openrouter",
                role=IMAGE_ROLE,
                model="live/banana-image",
                label="Live Banana Image",
                note="Live result",
                source_url="https://openrouter.ai/docs/guides/overview/models",
            )
        ]

    monkeypatch.setattr(cli, "discover_model_suggestions", fake_discover)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "spritegen",
            "models",
            "--provider",
            "openrouter",
            "--role",
            "image",
            "--online",
            "--search",
            "banana",
            "--limit",
            "5",
        ],
    )

    assert main() == 0

    output = capsys.readouterr().out
    assert "OpenRouter image model suggestions" in output
    assert "live/banana-image" in output
    assert "Live result" in output


def test_cli_can_use_models_dev_catalog_source(monkeypatch, capsys):
    from spritegen import cli
    from spritegen.cli import main
    from spritegen.provider_models import PROMPT_ROLE, ModelSuggestion

    def fake_discover(provider, role, search="", limit=20, timeout=15, source="auto"):
        assert provider == "openrouter"
        assert role == PROMPT_ROLE
        assert search == "minimax"
        assert source == "models-dev"
        return [
            ModelSuggestion(
                provider="openrouter",
                role=PROMPT_ROLE,
                model="minimax/minimax-m3",
                label="MiniMax-M2.7",
                note="models.dev result",
                source_url="https://models.dev/?search=minimax",
            )
        ]

    monkeypatch.setattr(cli, "discover_model_suggestions", fake_discover)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "spritegen",
            "models",
            "--provider",
            "openrouter",
            "--role",
            "prompt",
            "--online",
            "--catalog-source",
            "models-dev",
            "--search",
            "minimax",
        ],
    )

    assert main() == 0

    output = capsys.readouterr().out
    assert "minimax/minimax-m3" in output
    assert "models.dev result" in output
    assert "https://models.dev/?search=minimax" in output
