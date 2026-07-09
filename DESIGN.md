# Design

## Source of truth
- Status: Active
- Last refreshed: 2026-06-06
- Primary product surfaces: Windows desktop app, project-aware CLI, generated HTML galleries.
- Evidence reviewed: `README.md`, `docs/game-asset-generator-research.md`, `src/spritegen/ui/main_window.py`, `tests/spritegen/test_desktop_ui.py`.

## Brand
- Personality: practical, clear, craft-focused, and production-minded.
- Trust signals: local project files, visible preflight checks, explicit provider/model choices, readable prompt previews, and clear export paths.
- Avoid: toy-like novelty, marketing-page composition, dense ungrouped forms, hidden API cost risks, decorative visuals that compete with asset inspection.

## Product goals
- Goals: let game creators define a reusable art direction, generate coherent AI game assets, inspect prompts before spending image calls, slice atlases correctly, and export engine-ready files.
- Non-goals: replace a full art tool, manage game-engine projects directly, or hide provider/model details from users who need control.
- Success signals: a new user can create or open a project, choose providers, preview prompts, generate assets, and find exported sprites without editing JSON or reading CLI docs.

## Personas and jobs
- Primary personas: solo game developers, technical artists, small indie teams, and prototype builders.
- User jobs: keep a project universe coherent, improve rough asset ideas, generate several atlas variants, validate slicing/output, and export selected sprites.
- Key contexts of use: desktop iteration sessions, provider/API-key setup, pre-generation checks, and post-generation asset review.

## Information architecture
- Primary navigation: left-side setup tabs for Project, Asset, and Providers; right-side workspace for prompt plan and generated output.
- Core routes/screens: desktop main window, project gallery HTML, asset gallery HTML, CLI project workflow.
- Content hierarchy: project context first, asset definition second, provider setup third, prompt/output evidence always visible on the right.

## Design Principles
- Principle 1: Keep the main workflow visible. The user should not lose Save, Enhance, Generate, progress, or status while editing deeper settings.
- Principle 2: Make spend-risk explicit. Preflight, prompt preview, provider setup, and model validation should be prominent before generation.
- Tradeoffs: prefer dense but legible desktop controls over spacious marketing layouts; prefer explicit model/configuration fields over wizard-style hiding.

## Visual language
- Color: neutral light workspace, white input surfaces, teal primary action, amber enhancement accent, red destructive/clearing action, green success.
- Typography: Segoe UI/Arial-compatible desktop sans-serif, 13 px base UI text, larger bold section labels.
- Spacing/layout rhythm: 8 px grid, 16 px panel padding, focused tab pages, stable split-pane widths.
- Shape/radius/elevation: 6-8 px radius, thin borders, no nested decorative cards beyond functional grouped controls.
- Motion: none required; avoid animation that distracts from generated asset inspection.
- Imagery/iconography: generated assets are the primary imagery; UI chrome should stay quiet and not use decorative illustrations.

## Components
- Existing components to reuse: PySide `QTabWidget`, `QGroupBox`, `QFormLayout`, `QSplitter`, `PreviewPanel`, provider/model controls, prompt preview text area.
- New/changed components: repo-owned Qt design tokens, role-based button styling, app/sidebar/workspace/action-footer object names, styled empty/output labels.
- Variants and states: primary Generate, accent Enhance, secondary utility actions, danger Clear Saved Keys, disabled provider-key fields, empty generated-output state.
- Token/component ownership: `src/spritegen/ui/theme.py` owns desktop tokens and QSS; `src/spritegen/ui/main_window.py` assigns semantic object names and button roles.

## Accessibility
- Target standard: practical WCAG AA contrast for text and controls where Qt styling allows.
- Keyboard/focus behavior: native Qt tab order and focus rings should remain visible; do not remove focus outlines.
- Contrast/readability: controls must be readable on light backgrounds; placeholder and metadata text should remain secondary but legible.
- Screen-reader semantics: keep native labels, form rows, and button text explicit.
- Reduced motion and sensory considerations: no essential motion or flashing states.

## Responsive behavior
- Supported breakpoints/devices: Windows desktop/laptop screens at 1400 px minimum width and above.
- Layout adaptations: splitter permits wider output review while preserving a usable setup pane; tab pages scroll vertically.
- Touch/hover differences: mouse/keyboard desktop is primary; touch is not a target for this PySide surface.

## Interaction states
- Loading: progress bar and status label report generation/enhancement work.
- Empty: generated output shows a quiet centered empty state until assets exist.
- Error: warning dialogs for blocking failures, status text for recoverable workflow states.
- Success: status label names saved/loaded/generated/exported results and points to paths when useful.
- Disabled: API key fields disable when the selected provider does not need a key.
- Offline/slow network, if applicable: model refresh falls back to offline suggestions; provider setup should make missing keys/models visible before generation.

## Content voice
- Tone: direct, concrete, tool-like.
- Terminology: project, asset, provider, model, prompt plan, generated output, variant, export.
- Microcopy rules: labels should name the data or command directly; avoid instructional paragraphs in the app chrome.

## Implementation constraints
- Framework/styling system: PySide6 desktop UI with Qt stylesheets.
- Design-token constraints: keep tokens in Python/QSS, no new runtime dependency for design.
- Performance constraints: UI styling must not slow app launch, generation threads, slicing, or gallery rendering.
- Compatibility constraints: Windows launcher remains the primary easy-use path; offscreen Qt tests may not have system fonts.
- Test/screenshot expectations: add regression tests for semantic roles/tokens and capture native screenshots for visual changes when practical.

## Open questions
- [ ] Whether to add icons for high-frequency commands / owner: product / impact: may improve scan speed once icon assets or an icon library are chosen.
- [ ] Whether to offer compact and comfortable density modes / owner: product / impact: could help both laptop and large-monitor users.
