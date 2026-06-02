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
  can find exact model IDs for providers such as OpenRouter and OpenAI.
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
- `spritegen models --online --catalog-source models-dev --search ...` can query
  models.dev provider catalogs directly when users find newer model names there
  first, including OpenRouter and OpenAI IDs.
- The desktop **Refresh Models** button fetches current OpenRouter and OpenAI
  image and prompt models into the suggestion pickers without overwriting any
  custom model text the user has typed.
- Offline defaults remain the fallback for no-network use and for providers that
  do not expose a model-list endpoint in this tool yet.

## Sixteenth implementation slice

Custom atlas layout creation now covers character-sheet composites:

- `AssetLayout.hero_plus_grid` creates one large hero/full-body region plus a
  same-identity grid of smaller supporting cells, matching the requested
  512x1024 character plus eight 256x256 expression-head layout shape while
  allowing custom dimensions.
- `spritegen project layout add-hero-grid` saves that layout into project JSON,
  so it can drive prompt planning, generation, slicing, and export like any
  built-in layout.
- The desktop **Custom Layout** panel now has an **Add Hero + Grid** action and
  hero-region controls, so users can define this composite shape without editing
  JSON by hand.
- The layout prompt instructions explicitly call out hard seams, same identity,
  shared palette/materials/style, and exact slice boundaries.

## Seventeenth implementation slice

Project coherence now uses visual references where the provider supports them:

- Project generation scans known prior assets for `generation_manifest.json` and
  collects existing raw generated atlases as reference images.
- OpenRouter image generation sends those references as `image_url` data-url
  content parts alongside the text prompt, using the same Chat Completions path
  as image generation.
- OpenAI image generation keeps using the Images API for simple text-only runs,
  then switches to the Responses image-generation tool when prior raw atlases are
  available as `input_image` references.
- Generation manifests now record the reference images used at the run and output
  levels, making style-reference influence auditable after generation.
- Providers without implemented multimodal image input continue using the
  existing text anchors from prior assets rather than guessing unsupported API
  payloads.

## Eighteenth implementation slice

First-run project setup now has executable examples:

- `spritegen.project_starters` defines starter projects that produce the same
  `ProjectSpec`, `AssetSpec`, and prompt packets as hand-authored projects.
- `spritegen project starters` lists available starter projects, and
  `spritegen project starter --starter mycelium_td` creates a saved project,
  first asset, and prompt plan in one command.
- The desktop Project panel exposes the same flow through **Starter** and
  **Create Starter**, so a double-click user can begin from a coherent MyceliumTD
  or rogue-character example without editing JSON or learning the CLI first.

## Nineteenth implementation slice

Generation now supports candidate variants:

- `ProjectAssetGenerator.generate(..., variants_per_packet=N)` creates multiple
  raw atlases and sliced outputs for each prompt packet without changing the
  saved project or asset spec.
- `generation_manifest.json` records `variants_per_packet`, `variant_index`, and
  `variant_count` so later preview/export steps know which files belong to each
  candidate.
- `spritegen project generate --variants N` exposes the same workflow for CLI
  users, including dry-run image counts.
- The desktop provider panel includes **Image Variants**, and preview titles mark
  variant outputs so users can compare candidates before exporting.

## Twentieth implementation slice

Variant runs can now be narrowed at export time:

- `ProjectAssetExporter` accepts a selected variant and filters
  `generation_manifest.json` outputs without mutating the saved project, asset, or
  generation manifest.
- `asset_export_manifest.json` records `selected_variant`, while each exported
  sprite still carries its `variant_index` and `variant_count`.
- `spritegen project export --variant N` lets CLI users export only the chosen
  candidate from a variant generation run.
- The desktop output toolbar adds a **Variant** selector with **All** as the
  default, so users can compare generated candidates and export only the one they
  want to bring into their game.

## Twenty-first implementation slice

Chosen variants now feed future project coherence:

- The OpenRouter and OpenAI visual-reference path checks each prior asset's
  `asset_export_manifest.json` before falling back to the first generated atlas.
- When an export records `selected_variant`, the matching raw atlas in
  `generation_manifest.json` becomes the preferred reference image for later
  assets in the same project.
- This keeps the user's chosen candidate, rather than an arbitrary first variant,
  as the visual style anchor for subsequent generations.

## Twenty-second implementation slice

Generation runs now produce a browser-review artifact:

- `ProjectAssetGenerator` writes `asset_gallery.html` beside
  `generation_manifest.json` for every generation run.
- The gallery links the manifest, raw atlases, sliced sprites, prompt text,
  variants, and reference images using relative file paths.
- `spritegen project generate` prints the gallery path, and the desktop output
  toolbar adds **Open Gallery** so users can inspect and compare candidates in a
  browser without digging through folders.

## Twenty-third implementation slice

Provider discovery and visual references now cover the main paid paths more
evenly:

- models.dev discovery is generic per provider, so OpenAI and OpenRouter can both
  return current image and prompt model IDs through the CLI and desktop refresh.
- OpenAI reference-image generation uses Responses image generation with
  `input_image` parts only when references exist, preserving the simpler Images
  API path for normal text-only calls.
- Project manifests now reflect the same prior-asset reference list for OpenAI
  and OpenRouter runs, including the user's exported variant preference.

## Twenty-fourth implementation slice

Project organization now has a browser-level home page:

- `spritegen.project_gallery.ProjectGalleryWriter` writes `project_gallery.html`
  in the project folder, linking project JSON, asset JSON, prompt plans,
  generation manifests, per-asset run galleries, export manifests, and preview
  thumbnails.
- `spritegen project gallery --project ...` lets CLI users refresh that index on
  demand, while `project generate` and `project export` print the project gallery
  path after writing generation or export artifacts.
- The desktop app adds **Project Gallery** so a double-click user can open the
  whole project in a browser without digging through generated folders.

## Twenty-fifth implementation slice

Project output can now be handed off as one pack:

- `ProjectAssetExporter.export_project` walks the saved assets in a project and
  copies generated slices into `exports/_project_pack/assets/<type>/<asset>/`.
- The project pack writes `project_export_manifest.json`, records skipped assets
  that have not been generated yet, and respects each asset's selected variant
  from `asset_export_manifest.json` unless the caller asks for all variants.
- `spritegen project export-project` / `export-all` exposes the pack flow for
  CLI users, and the desktop app adds **Export Project** for the same operation.

## Twenty-sixth implementation slice

Generation can now include prompt improvement in the same flow:

- `spritegen project generate --enhance-first` runs the asset-level prompt
  enhancer, saves the improved prompt on the asset JSON, rebuilds the prompt plan,
  and then generates images from the improved prompt.
- The flag uses the project's prompt provider/model by default, while
  `--prompt-provider`, `--prompt-model`, and `--prompt-api-key` allow one-run
  overrides without changing the image-generation provider.
- The desktop app adds **Improve prompt before Generate**, so a user can keep the
  separate prompt model but still run enhancement and image generation with one
  Generate action.

## Twenty-seventh implementation slice

Provider setup now catches common model-role mistakes without blocking current
catalog IDs:

- `spritegen.provider_models.validate_model_choice` checks selected image and
  prompt models against built-in suggestions plus refreshed OpenRouter/models.dev
  catalog results.
- Known prompt-only IDs such as `minimax/minimax-m2.7` are reported as the wrong
  role when pasted into the image model field, while newer custom IDs remain
  allowed with a setup warning.
- `spritegen models --validate ...` exposes the same check for CLI users.
- Desktop **Check Setup** now combines key checks with model-role validation, so
  a double-click user can catch swapped image/prompt models before spending API
  calls.

## Twenty-eighth implementation slice

Generation now has a reusable preflight step:

- `spritegen.preflight.build_generation_preflight` builds the same prompt-packet
  and layout summary a generation will use, then reports provider key, model-role,
  variant-count, atlas-size, and expected slice-count issues before any image API
  call.
- `spritegen project preflight --project ... --asset ...` exposes that report to
  CLI users and exits non-zero only when the run has blocking errors.
- Desktop **Generate** now runs the same preflight and stops before starting the
  background generation worker when a known wrong-role model or required key is
  missing.

## Twenty-ninth implementation slice

Desktop preflight is now visible before generation:

- The Prompt Plan toolbar has **Check Run**, which writes the shared preflight
  report into the same read-only panel used for prompt previews.
- The report lists readiness status, provider/model choices, whether prompt
  improvement will run, atlas image count, expected slice count, variants,
  layouts, reference assets, and any blocking or warning issues.
- This lets a desktop user inspect the actual run shape before pressing
  **Generate**, while **Generate** still repeats the preflight guard.

## Thirtieth implementation slice

Preflight now shows which saved project assets will steer coherence:

- `GenerationPreflightReport` carries structured reference-asset summaries
  derived from the same prompt-packet metadata used by image prompts.
- CLI `spritegen project preflight` and desktop **Check Run** list each prior
  asset by name, type, prompt, details, and layout instead of showing only a
  count.
- The current asset is excluded from those summaries, so users can see the
  actual already-saved assets that will shape the next generation.

## Thirty-first implementation slice

Desktop model discovery is now searchable and source-selectable:

- The provider setup panel has a **Model Catalog** selector for `auto`,
  OpenRouter, or models.dev plus a search box for terms like `minimax`.
- Desktop **Refresh Models** passes the selected catalog and search text into the
  shared discovery worker, so users can pull current models.dev IDs into the
  image and prompt model pickers without using the CLI.
- This keeps the easy desktop path aligned with the documented models.dev
  workflow for finding current OpenRouter and OpenAI model names.
