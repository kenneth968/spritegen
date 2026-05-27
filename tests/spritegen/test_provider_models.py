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
