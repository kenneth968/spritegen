# Game Asset Generator Direction

## Current provider implications

- OpenAI's current image-generation guide centers GPT Image models, including
  `gpt-image-2`, and distinguishes the Image API for direct one-prompt image
  creation from the Responses API for conversational, multi-step, reference-based
  image workflows.
- OpenAI's guide also notes that Responses image generation can expose a revised
  prompt, which maps well to this tool's prompt-enhancement layer.
- OpenRouter image generation depends on model output modalities. The tool should
  discover or validate that the selected model can output images, then set image
  modalities and parse generated images from the assistant message.
- OpenRouter returns base64 data URLs in message images for compatible models, and
  some models can return multiple images in one response.

## Product shape

The project should evolve from a one-off prompt runner into a project workspace:

1. A user creates a game project with shared setting, style, palette, provider
   defaults, and negative prompt.
2. The project defines asset types such as towers, enemies, character portraits,
   props, tiles, or UI icons.
3. Each asset type can define evolution counts, common constraints, and a default
   output layout.
4. New assets inherit the project context and can include prior assets as context,
   so the next generated item belongs to the same universe.
5. Output layouts describe exact regions in generated atlases, so the tool can cut
   composite generations into files without the user manually measuring seams.

## First implementation slice

This branch adds the project and layout foundation while preserving the existing
generator:

- `spritegen.projects` stores project specs, asset specs, provider defaults, and
  prompt plans.
- `spritegen.layouts` defines named atlas layouts, including the character
  full-body plus eight emotion heads layout.
- `Slicer.slice_layout_image` cuts generated atlas images according to named
  layout regions and writes metadata.
- CLI commands let users create project specs, create prompt plans, inspect
  layouts, and slice layout images.

## Second implementation slice

The follow-up commit makes saved project assets executable:

- `spritegen.enhancement` enhances asset descriptions through mock,
  Pollinations, OpenAI Responses, or OpenRouter Chat Completions.
- `spritegen.project_generation` generates each prompt packet, saves raw images,
  slices layout regions, and writes a `generation_manifest.json`.
- `spritegen project enhance` updates a saved asset with provider-improved prompt
  text and rewrites its prompt plan.
- `spritegen project generate` runs a saved asset through the configured image
  provider. `--dry-run` updates and prints the plan without making image calls.
- OpenAI image generation now uses direct HTTPS with `OPENAI_API_KEY`, so the CLI
  no longer requires users to install the OpenAI Python package separately.

## Third implementation slice

The next usability layer separates prompt intelligence from image generation and
makes production color rules explicit:

- Projects already store separate image-provider/model and prompt-provider/model
  defaults; the desktop UI now labels those paths separately.
- Prompt enhancement now accepts Markdown-backed system guidance. Built-in guides
  live under `src/spritegen/prompt_guides/` for project context, asset families,
  individual assets, layouts, and color modes.
- OpenAI prompt enhancement passes those guides through the Responses API
  `instructions` field, and OpenRouter prompt enhancement sends them as a system
  message before the user's rough asset brief.
- Project specs now carry a color treatment: full color, limited palette,
  black/white, grayscale value map, or single-hue value map. The planner injects
  this into both the prompt-improvement brief and the final image prompt.
- The desktop provider area links to `https://models.dev/?search=minim` so users
  can find exact model IDs for providers such as OpenRouter.
- The desktop app can now refresh and load saved projects and saved assets from
  the selected project directory, making the workflow a reusable asset library
  instead of a single-entry form.

## Fourth implementation slice

Prompt improvement is now layered at the same levels the user thinks about the
project:

- `spritegen project enhance-project` rewrites the saved project summary, visual
  style, shared universe, palette, negative prompt, and color-mode notes from a
  strict JSON response.
- `spritegen project enhance-type` rewrites one asset type's reusable rules,
  evolution rules, and stage labels.
- The desktop app exposes the same levels as **Improve Project**, **Improve Type
  Rules**, and **Enhance Asset**, keeping the image-generation model separate
  from the prompt-improvement model.
- Structured prompt enhancement accepts fenced or plain JSON from providers and
  writes validated fields back to the existing project JSON.

## Fifth implementation slice

Post-processing is now explicit project configuration:

- Project JSON stores whether generated layout slices should remove simple
  backgrounds.
- The prompt planner tells image and prompt-improvement models whether the output
  will be background-removed, so generated assets can use removable backgrounds
  when transparency is desired.
- `spritegen project init` accepts `--remove-background` / `--no-remove-background`.
- `spritegen project generate` can override the saved setting for one run with
  the same boolean flag.
- The desktop app exposes the same setting as a project checkbox, and generated
  manifests record the effective background-removal choice.

## Sixth implementation slice

API keys are now session inputs instead of only environment variables:

- `SpriteConfig` can carry a session-only `api_key` for image generation.
- OpenAI and OpenRouter image calls use that key before falling back to
  `OPENAI_API_KEY` / `OPENROUTER_API_KEY`.
- `spritegen project generate --api-key ...` passes a one-run image key without
  writing it to project JSON.
- The desktop app labels the shared key field as **Session API Key** and passes
  it through project generation directly instead of mutating process environment
  variables.

## Seventh implementation slice

Layouts are no longer limited to built-in presets:

- Project JSON can store custom atlas layouts beside asset types.
- The prompt planner and project generator resolve custom layouts through the
  project before falling back to built-ins.
- `spritegen project layout add-grid` creates reusable project-specific grid
  atlases for contact sheets, tiles, multi-pose outputs, or any repeated cells.
- `spritegen project layout import/export/info/list/slice` lets users move layout
  JSON between projects and slice generated images with either built-in or custom
  layouts.
- The desktop layout picker includes project layouts after a project is loaded.

## Eighth implementation slice

Desktop output inspection now matches the files game users actually consume:

- Fresh generations show each raw atlas with its sliced sprite outputs beneath it.
- Saved assets reload `generation_manifest.json` and preview both raw and sliced
  images, including manifests that store relative paths.
- The preview panel clear path now resets all prior widgets before showing the
  empty-state message again.

## Ninth implementation slice

Provider setup is now closer to a normal desktop app:

- Desktop settings can remember the selected image provider/model, prompt
  provider/model, and provider API keys in a local user settings file.
- Image generation and prompt improvement have separate API key fields, so users
  can combine providers such as OpenRouter for images and OpenAI for prompt
  rewriting.
- **Check Setup** validates required model/key fields without making a network
  request.
- Saved API keys stay out of project JSON and can be cleared from the app.

## Tenth implementation slice

Custom layout creation moved into the desktop workflow:

- The Asset panel can create reusable equal-cell grid layouts with a project-local
  name, canvas size, row/column count, region prefix, and prompt instructions.
- New layouts are saved into project JSON, immediately selected in the Layout
  picker, and set as the current asset type's default layout.
- This closes the gap where users could define custom contact sheets from the CLI
  but not from the app they are expected to double-click and use.

## Eleventh implementation slice

Generated assets can now be exported as game-ready files:

- `spritegen.project_export` copies generated slice PNGs from
  `generation_manifest.json` into a clean `sprites/` folder and writes an
  `asset_export_manifest.json` with portable relative paths.
- `spritegen project export` exposes that flow for CLI users and can optionally
  copy raw generated atlases with `--include-raw`.
- The desktop **Export Sprites** button saves the current asset plan, exports the
  latest generated slices, and points **Open Folder** at the export directory.

## Twelfth implementation slice

Project coherence is now easier to inspect before generation:

- Prior saved assets are represented as structured prompt anchors with name,
  asset type, prompt summary, details, and layout.
- Prompt packet metadata records those known assets so saved prompt plans explain
  which existing assets influenced a generation.
- The desktop **Preview Prompts** button writes the current prompt plan and shows
  the exact prompts, including prior-asset anchors, before a user spends image
  generation tokens.

## Thirteenth implementation slice

Common game-asset workflows are now presets:

- `spritegen.workflow_presets` defines shared recipes for four-stage towers,
  character emotion atlases, four-variant atlases, single props, tiles, and UI
  icons.
- `spritegen project presets` lists available presets, and
  `spritegen project init --preset ...` applies one while still allowing explicit
  overrides.
- The desktop Asset panel exposes the same recipes through **Workflow** and
  **Apply Preset**, filling the asset type, reusable rules, evolution settings,
  stage labels, and default layout.

## Fourteenth implementation slice

Provider model setup now has shared suggestions without blocking custom IDs:

- `spritegen.provider_models` centralizes known image-generation and prompt-
  improvement model IDs for mock, Pollinations, OpenAI, and OpenRouter.
- `spritegen models --provider ... --role image|prompt` prints suggested model
  IDs and the reference pages users should check for current provider catalogs.
- The desktop provider panel shows image and prompt model suggestion pickers
  beside editable model fields, so users can start from current defaults while
  still pasting newer OpenRouter or models.dev IDs.
- OpenRouter image suggestions are aligned with the documented model discovery
  path: filter the Models API by `output_modalities=image` and use
  `image_config.image_size` values such as `1K`, `2K`, or `4K` during generation.

## Fifteenth implementation slice

Model discovery now reaches beyond the static fallback list:

- `spritegen.provider_models.discover_model_suggestions` can query OpenRouter's
  Models API with `output_modalities=image` or `output_modalities=text` and turn
  the response into the same suggestion objects used by the desktop app.
- `spritegen models --online --search ...` merges live OpenRouter results with
  the offline defaults, so users can find current model IDs without waiting for a
  package update.
- The desktop **Refresh Models** button fetches current OpenRouter image and
  prompt models into the suggestion pickers without overwriting any custom model
  text the user has typed.
- Offline defaults remain the fallback for no-network use and for providers that
  do not expose a model-list endpoint in this tool yet.
