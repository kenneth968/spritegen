# spritegen

AI-powered sprite sheet generator for tower defense games. Generates evolution chain sprites (Bloons TD style) using multiple AI image providers, with automatic background removal.

## Features

- **Multiple AI providers**: OpenAI (DALL-E), OpenRouter (Gemini Flash), Pollinations (free), HuggingFace, mock
- **Evolution chains**: Generate visually consistent upgrade sequences (like Bloons TD tower upgrades)
- **Automatic background removal**: Adaptive flood-fill handles white, black, and transparent backgrounds
- **Style consistency**: Style presets with seed tracking ensure visual coherence across generations
- **Sprite slicing**: Extract individual sprites from sheets with metadata export
- **Project-aware prompt planning**: Store a game project, shared style, palette, asset types, and prior assets so each new prompt carries the same universe context
- **Separate model choices**: Use one provider/model for final image generation and another provider/model for AI prompt improvement
- **Markdown prompt guides**: Bundled `.md` system prompts steer project, asset type, asset, layout, and color-mode prompt improvement
- **Color production modes**: Generate full color, limited palette, black/white, grayscale value-map, or single-hue value-map assets
- **Atlas layouts**: Define sliceable composite outputs, including a full-body character plus eight chibi emotion heads in one generated image

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

## Desktop App

On Windows, double-click `launch_spritegen.cmd` from the project folder. The launcher creates
a local `.venv`, installs the desktop dependencies, and opens the app.

The desktop app exposes separate provider/model fields for image generation and prompt
improvement. For OpenRouter model IDs, use [models.dev](https://models.dev/?search=minim)
or OpenRouter's model list, then paste the exact model name into the matching model field.
Saved projects and assets can be reopened from the Project and Asset selectors, so new
generations can reuse the same universe, style, palette, color mode, and prior assets.
Use **Improve Project**, **Improve Type Rules**, and **Enhance Asset** to run the
prompt-improvement model at the right level of the workflow before generating images.

For a distributable Windows executable:

```powershell
.\scripts\build_desktop_app.ps1 -Clean
```

The built app is written to `dist\spritegen.exe`.

## Project-Aware Workflow

Create a project once, then add assets inside that shared universe. The prompt planner saves
reusable JSON specs under `projects/<slug>/` and produces image prompts for every evolution stage.

```bash
spritegen project init \
  --name MyceliumTD \
  --summary "Fungal tower defense game" \
  --style "clean cartoon tower defense sprites, bold outlines, bright readable shapes" \
  --context "Friendly fungal towers defending a forest floor from tiny slime enemies" \
  --palette "#8B4513,#228B22,#9932CC,#00FA9A" \
  --color-mode limited_palette \
  --color-prompt "Keep values readable when recolored by tower upgrade tier" \
  --asset-type tower \
  --asset-type-context "Every tower has four upgrade stages and should read clearly at small game size" \
  --evolutions 4

spritegen project asset \
  --project myceliumtd \
  --asset-type tower \
  --name Puffball \
  --description "A mushroom tower that attacks by releasing spore clouds" \
  --details "Soft white cap, playful shape language, area damage identity" \
  --print-prompts

# Optional: have the prompt provider rewrite the rough asset idea.
# Use OPENAI_API_KEY or OPENROUTER_API_KEY in your environment for paid providers.
spritegen project enhance-project --project myceliumtd
spritegen project enhance-type --project myceliumtd --asset-type tower
spritegen project enhance --project myceliumtd --asset puffball

# Generate all prompt packets for the asset, save raw images, slice layout regions,
# and write a generation_manifest.json beside the output.
spritegen project generate --project myceliumtd --asset puffball
```

`spritegen project enhance` sends the user's rough asset idea as the user prompt and the
bundled Markdown guides in `src/spritegen/prompt_guides/` as system/developer guidance
where the selected provider supports it. The image model is only used by `project generate`.

For character atlases, ask the image model for the built-in layout, then slice the result:

```bash
spritegen layout info --name character_full_plus_8_emotions
spritegen layout slice \
  --image output/rogue_atlas.png \
  --layout character_full_plus_8_emotions \
  --output output/rogue \
  --prefix rogue_assassin
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
