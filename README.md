# spritegen

AI-powered sprite sheet generator for tower defense games. Generates evolution chain sprites (Bloons TD style) using multiple AI image providers, with automatic background removal.

## Features

- **Multiple AI providers**: OpenAI (DALL-E), OpenRouter (Gemini Flash), Pollinations (free), HuggingFace, mock
- **Evolution chains**: Generate visually consistent upgrade sequences (like Bloons TD tower upgrades)
- **Automatic background removal**: Adaptive flood-fill handles white, black, and transparent backgrounds
- **Style consistency**: Style presets with seed tracking ensure visual coherence across generations
- **Sprite slicing**: Extract individual sprites from sheets with metadata export
- **Project-aware prompt planning**: Store a game project, shared style, palette, asset types, and prior assets so each new prompt carries the same universe context
- **Visual reference reuse**: OpenRouter generations can include prior generated atlases as reference images for stronger project coherence
- **Separate model choices**: Use one provider/model for final image generation and another provider/model for AI prompt improvement
- **Markdown prompt guides**: Bundled `.md` system prompts steer project, asset type, asset, layout, and color-mode prompt improvement
- **Color production modes**: Generate full color, limited palette, black/white, grayscale value-map, or single-hue value-map assets
- **Post-processing control**: Save whether layout slices should remove simple backgrounds or keep the generated frame/background
- **Atlas layouts**: Define sliceable composite outputs, including a full-body character plus eight chibi emotion heads in one generated image
- **Project custom layouts**: Save reusable project-specific atlas grids and slice generated images with them

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
improvement. Each provider has suggested model IDs in a picker beside the editable
model field, so a user can choose a known-good default or paste a newer/custom model.
For OpenRouter model IDs, use [models.dev](https://models.dev/?search=minim) or
OpenRouter's model list, then paste the exact model name into the matching model field.
Use **Refresh Models** to pull the current OpenRouter model list into those pickers;
the built-in suggestions remain available when offline.
Paste provider keys into **Image API Key** and **Prompt API Key**. Use **Check Setup**
to confirm the selected providers have models and keys, or **Save Local Setup** to
remember provider defaults and keys on this computer. Keys are never written to project
JSON; they live in the local user settings file or in `OPENAI_API_KEY` /
`OPENROUTER_API_KEY` environment variables.
Saved projects and assets can be reopened from the Project and Asset selectors, so new
generations can reuse the same universe, style, palette, color mode, and prior assets.
Use **Improve Project**, **Improve Type Rules**, and **Enhance Asset** to run the
prompt-improvement model at the right level of the workflow before generating images.
Use **Preview Prompts** to inspect the exact image prompts, including prior saved
assets that will be used as style and universe anchors, before spending image tokens.
When using OpenRouter for image generation, saved raw atlases from prior project
assets are also sent as visual reference images when available; other providers
currently keep using the text anchors.
Use **Workflow / Apply Preset** to fill common asset-type settings such as four-stage
towers or a full-body character plus eight emotion heads.
Use **Custom Layout** to add reusable equal-cell atlases, contact sheets, tile grids,
pose sheets, or a large hero region plus a grid of smaller related cells to the
current project without leaving the app.
The output panel previews both the raw generated atlas and the sliced sprite files from
`generation_manifest.json`, so desktop users can inspect the game-ready files directly.
Use **Export Sprites** after generation to copy the sliced files and a compact export
manifest into `projects/<project>/exports/<asset>/`.

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
  --preset tower_4_stage \
  --summary "Fungal tower defense game" \
  --style "clean cartoon tower defense sprites, bold outlines, bright readable shapes" \
  --context "Friendly fungal towers defending a forest floor from tiny slime enemies" \
  --palette "#8B4513,#228B22,#9932CC,#00FA9A" \
  --color-mode limited_palette \
  --color-prompt "Keep values readable when recolored by tower upgrade tier" \
  --remove-background

# See available presets, such as tower_4_stage and character_emotion_atlas.
spritegen project presets

# See suggested provider model IDs for image generation or prompt improvement.
spritegen models --provider openrouter --role image
spritegen models --provider openrouter --role prompt
spritegen models --provider openrouter --role prompt --online --search minimax

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

# Copy the sliced, game-ready PNGs into a clean export folder for an engine.
spritegen project export --project myceliumtd --asset puffball
```

For one-off CLI runs without environment variables, pass a session-only key:

```bash
spritegen project generate --project myceliumtd --asset puffball --api-key sk-or-...
```

Use `--no-remove-background` on `project init` for assets where the generated
background is intentional, or pass `--remove-background` / `--no-remove-background`
to `project generate` to override the project setting for one run.
Use `spritegen project export --include-raw` when you also want the original generated
atlases copied beside the sliced sprites.

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

For project-specific atlas shapes, save a custom layout on the project and reuse it
for future assets. In the desktop app, use **Custom Layout** for equal-cell grids
or hero-plus-grid character sheets; the same layouts can also be managed from the CLI:

```bash
spritegen project layout --project myceliumtd add-grid \
  --name tower_contact_sheet \
  --width 1536 \
  --height 1024 \
  --rows 2 \
  --columns 3 \
  --region-prefix tower_pose \
  --prompt-instructions "Create six clean tower pose cells with hard seams."

spritegen project asset \
  --project myceliumtd \
  --asset-type tower \
  --name PuffballContact \
  --description "Puffball tower shown in six readable pose variants" \
  --layout tower_contact_sheet \
  --print-prompts

spritegen project layout --project myceliumtd add-hero-grid \
  --name rogue_character_sheet \
  --width 1024 \
  --height 1024 \
  --hero-width 512 \
  --grid-rows 4 \
  --grid-columns 2 \
  --hero-region-name full_body \
  --grid-region-prefix head
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
