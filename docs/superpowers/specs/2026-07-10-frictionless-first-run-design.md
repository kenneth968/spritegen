# Frictionless First Run and Instant Generation

## Context

The desktop app contains capable project, prompt, layout, provider, gallery, and export
tools, but it exposes too many of them before a new user has generated anything. A live
inspection also reproduced a blocking storage bug: `Path("projects").absolute()` resolves
relative to the process working directory. When the app is launched from a protected
directory, even **Check Run** fails with an access-denied error before provider validation
or generation begins.

The current provider indicator can also claim that a key is loaded while the selected
provider and image model are incompatible. The no-cost sample action exists, but it is
buried inside the Project tab of the settings drawer.

## Goal

A new user can launch the desktop app, describe one asset, and start a real image
generation without configuring projects, model IDs, prompt providers, output paths, or
API keys.

The first successful result should teach the product. Advanced project and provider
controls remain available after the user has a reason to need them.

## Success Criteria

1. Launching from any working directory uses a stable, writable project location and never
   attempts to write beneath the launcher or executable directory.
2. With no saved API key, a user can enter an asset idea and click **Generate** to start a
   real Pollinations generation.
3. With a valid saved provider setup, the same action uses that provider without asking for
   the key again.
4. Selecting a keyed provider without a key reveals one inline key field and a single
   **Connect and generate** action.
5. Known provider/model mismatches are repaired before preflight; intentional unknown
   custom models remain usable with the existing warning behavior.
6. Predictable setup, storage, and provider failures are shown inline with a specific
   recovery action rather than a generic modal dialog.
7. The generated atlas and sliced output appear in the main workspace, and export actions
   become prominent only when output exists.
8. Existing advanced project workflows, layouts, prompt improvement, galleries, variants,
   and exports continue to work.

## Non-Goals

- Replacing the existing project-aware generation engine.
- Adding a new provider or model-catalog dependency.
- Moving API keys into an operating-system credential manager in this change.
- Redesigning the generated HTML galleries or CLI.
- Silently substituting mock output when a real provider fails.

## Chosen Approach

Use an instant composer as the default desktop surface. A wizard was rejected because it
still makes the user complete setup steps before seeing value. Keeping the full project
editor as the default was rejected because it preserves the present information overload.

The instant composer is a thin entry point over the existing project and generation
services. It creates the minimum project and asset specifications automatically, then uses
the same preflight, generation thread, slicing, preview, and export paths as advanced mode.

## Default Experience

The main window opens with:

- a prominent multi-line **Describe your asset** field;
- an output-type selector with **Single sprite** selected by default;
- optional **Evolution chain** and **Character sheet** presets;
- a compact provider status control such as **Free provider** or **OpenAI connected**;
- one primary **Generate** button; and
- the existing output workspace in an intentional empty state.

Project art direction, palette, model selection, prompt-provider configuration, layout
editing, and storage location move behind **Advanced project setup**. Opening advanced mode
reveals the existing project panel and settings drawer; it does not navigate to a separate
application or discard the quick-start prompt.

Before output exists, gallery and export commands remain secondary or hidden. After a run
succeeds, the output preview becomes the visual focus and the relevant export and folder
actions become available beside it.

## Automatic Project and Asset Creation

Quick generation uses a stable project named `Quick Start` with slug `quick-start`. Each
idea becomes a new asset inside that project. The asset name is derived from the first
meaningful words of the description, and slug collisions receive a numeric suffix. The
user can rename or enrich the generated project and asset later in advanced mode.

Output types map to existing layouts and presets:

- **Single sprite** uses `single_sprite`.
- **Evolution chain** uses the existing four-stage tower/evolution preset.
- **Character sheet** uses `character_full_plus_8_emotions`.

No parallel quick-generation data model is introduced. The generated project and asset are
ordinary `ProjectSpec` and `AssetSpec` records saved by `ProjectStore`.

## Stable Project Storage

Introduce one application-path resolver responsible for the default writable location.
On desktop it resolves the base directory from Qt's writable Documents location and uses:

`<Documents>/Spritegen/projects`

If the platform does not report a Documents location, the fallback is:

`<home>/Spritegen/projects`

The resolver returns an absolute path and validates that the directory can be created and
written before any project is saved. The current `Path("projects").absolute()` defaults are
removed from the desktop startup path. A user-selected custom project folder remains
supported and takes precedence after it has been saved.

Storage validation runs before quick-project creation. A failure produces an inline message
with **Choose another folder**; it never falls through to a later access-denied traceback.

## Provider and API-Key Behavior

Provider selection follows this order:

1. Load the last saved provider and repair any known provider/role model mismatch by
   selecting that provider's recommended defaults.
2. Reuse the repaired saved provider when its required key is available.
3. Otherwise select Pollinations with the repository's recommended image model.
4. If the user explicitly selects OpenAI or OpenRouter without a key, reveal the inline
   key field instead of opening the full settings drawer.

The advanced provider panel remains available from the compact provider status control.
Model IDs, catalogs, prompt-provider separation, and manual key clearing stay there.

When a provider is changed, its recommended image and prompt models are selected
automatically. On startup, a saved model that produces a known provider/role error is
replaced by the recommended default and the status reports that the setup was repaired.
A model that only produces the existing unknown/custom warning is preserved.

**Connect and generate** stores the key through the existing `UserSettingsStore`, refreshes
the provider status, reruns preflight, and continues the interrupted generation. Users do
not need to click a separate save or setup-check command.

## Generation Data Flow

1. The user enters an asset description and chooses an output type.
2. The controller resolves and validates the project root.
3. It selects or repairs the provider setup.
4. If a required key is missing, the inline connection state is shown and the flow pauses.
5. The controller creates or loads `Quick Start`, derives a unique asset, and maps the
   output type to an existing layout.
6. Existing preflight runs with the resolved key and models.
7. Blocking preflight issues appear inline with focused recovery actions.
8. The existing generation thread runs and streams progress into the composer/output area.
9. Existing manifest loading renders raw and sliced images in the workspace.
10. The completed asset becomes available in advanced project mode and existing galleries.

## Components and Ownership

### Application path resolver

Owns default path selection, absolute normalization, and writable-directory validation. It
does not know about projects, providers, or UI widgets.

### Quick composer

Owns the description field, output-type selector, compact provider state, inline recovery
area, progress, and primary action. It emits user intent and renders state; it does not call
providers directly.

### Main-window controller

Coordinates the quick-generation flow, creates ordinary project/asset specifications, and
delegates to existing preflight and generation services. Shared provider and error-formatting
logic remains reusable by advanced mode.

### Advanced project setup

Reuses the existing project panel and settings drawer. Its visibility changes, but its saved
data and generation semantics do not.

## Error Handling

Expected failures render in the quick composer:

- missing key: **Paste key** and **Connect and generate**;
- provider unavailable or rate limited: **Retry**, **Use free provider**, or
  **Change provider**, as applicable;
- invalid known model: automatically select the recommended model and explain the repair;
- unwritable project location: **Choose another folder**;
- invalid or empty description: focus the description field with concise guidance.

Unexpected exceptions show a short inline summary with a **Show details** affordance. Modal
dialogs remain acceptable only for destructive confirmations or operating-system file
pickers. Provider errors continue to use the repository's centralized provider-error
translation.

## Testing

### Automated regression tests

- Default project-root resolution is independent of the process working directory.
- The resolver returns an absolute Documents-based path and handles the home fallback.
- An unwritable root is detected before `ProjectStore` writes.
- A fresh no-key window selects Pollinations and a compatible recommended model.
- A valid saved keyed provider is restored without another key prompt.
- Changing providers selects compatible defaults.
- A known saved provider/model mismatch is repaired; an unknown custom model is preserved.
- Quick generation creates `Quick Start` and a uniquely named ordinary asset.
- Each output type maps to the intended existing layout or preset.
- Missing-key generation enters inline connection state and resumes after key entry.
- Preflight failures are rendered inline and do not start the generation thread.
- Advanced mode still exposes existing project and provider controls.

### Manual desktop QA

1. Launch the desktop entry point from a directory outside the repository.
2. With fresh settings and no API keys, generate a simple single sprite through
   Pollinations and inspect the rendered output.
3. Repeat with a keyed provider, including first-time inline key entry.
4. Start with an intentionally mismatched known provider/model setting and confirm automatic
   repair before generation.
5. Exercise all three output types.
6. Open advanced mode, load the quick project and generated asset, then verify prompt preview,
   gallery, folder, and export actions.
7. Verify the main window at its minimum size and at the normal desktop size.

## Compatibility and Migration

Existing saved projects and custom project directories remain valid and can be selected
without moving their contents. Existing user settings are loaded as before. Only settings
with a blocking, known provider/model mismatch are repaired; custom warning-only model IDs
are not overwritten. User settings gain an optional absolute project-root field so a chosen
custom directory persists across launches; settings without that field use the new default.

The current main project editor remains available, so this change does not require a data
migration or remove expert workflows. It changes the default presentation and the path used
when no custom project root has been chosen.

## Acceptance Gate

The work is complete only when a fresh desktop session can produce and display one real
no-key image from an arbitrary launch directory, keyed-provider generation can be completed
without entering the full settings drawer, all targeted automated tests pass, and the
advanced project workflow remains usable.
