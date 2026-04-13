# spritegen

AI-powered sprite sheet generator for tower defense games. Generates evolution chain sprites (Bloons TD style) using multiple AI image providers, with automatic background removal.

## Features

- **Multiple AI providers**: OpenAI (DALL-E), OpenRouter (Gemini Flash), Pollinations (free), HuggingFace, mock
- **Evolution chains**: Generate visually consistent upgrade sequences (like Bloons TD tower upgrades)
- **Automatic background removal**: Adaptive flood-fill handles white, black, and transparent backgrounds
- **Style consistency**: Style presets with seed tracking ensure visual coherence across generations
- **Sprite slicing**: Extract individual sprites from sheets with metadata export

## Quick Start

```bash
pip install -e .

# Generate with Pollinations (free, no API key)
python generate_pollinations.py --tower puffball

# Generate with OpenRouter + Gemini Flash
export OPENROUTER_API_KEY=sk-or-...
spritegen evolution-chain --tower puffball --provider openrouter --model google/gemini-3.1-flash-image-preview

# Generate a basic sprite sheet
spritegen generate --style pixel_art --sprites "red mushroom" "blue mushroom" --provider mock
```

## Tower Types

- **Puffball**: Spore cloud area damage (4 evolution stages)
- **Cordyceps**: Mind control / slow effect
- **Amanita**: Poison damage over time
- **Chanterelle**: Economy boost

## Architecture

```
src/spritegen/
  generator.py   - Core image generation (multi-provider)
  slicer.py      - Background removal & sprite extraction
  style.py       - Style presets & consistency management
  config.py      - Configuration dataclasses
  models.py      - Data models (GeneratedSheet, SpriteMetadata)
  mycomed.py     - Tower evolution chain definitions
  consistency.py - Style consistency analysis
  cli.py         - CLI entry point
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```
