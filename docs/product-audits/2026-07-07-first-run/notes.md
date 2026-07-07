# Spritegen First-Run Product Audit

Date: 2026-07-07

## Audit Scope

Surface audited: Windows desktop app.

User goal: start from a fresh app state, choose the no-key provider, create/use the starter project, check whether a run is ready, generate output, and export sprites.

Destination: local folder.

Capture method: direct PySide window capture on Windows. Browser and Chrome capture were not applicable because the product surface is a native Qt desktop app, not a web page. Mock generation was used for the generated-output and export screenshots to avoid calling external providers or spending image credits.

## Captured Steps

1. `01-welcome.png` - First-run welcome state.
   Health: poor. The welcome overlay is not clearly above the main app. Background app controls and welcome cards overlap, making the first decision feel broken.

2. `02-starter-main.png` - Main app after choosing Pollinations and applying the starter.
   Health: mixed. The starter path works and the provider status is reassuring, but key form content is clipped and the status area shows a long local path.

3. `03-providers-drawer.png` - Provider settings drawer.
   Health: mixed. Provider setup is understandable, but the drawer compresses the workspace and hides some tabs behind arrows.

4. `04-run-check.png` - Run check with preflight details visible.
   Health: good concept, mixed execution. The user gets a clear ready state before generation, but the detailed preflight appears below a large empty output region.

5. `05-generated-output.png` - Mock generation result after the run check.
   Health: weak. Generation completed, but the visible output area only shows a filename strip. The generated image is not visible because the preflight panel remains open.

6. `06-export-status.png` - Exported sprite status.
   Health: mixed. Export succeeds and confirms sprite count, but the long path wraps across the status area and the run summary still reads like generation is in progress.

## Strengths

- The product has a real first-run path: the user can choose a free no-key provider, apply a starter project, check readiness, generate, and export.
- Provider status is visible in the top bar and uses plain, trust-building copy like "No key needed" and "Key missing".
- The run check is valuable. It tells users image count, slice count, provider/model, prompt enhancement state, and layout before spending calls.
- The app keeps core project and asset context visible while working, which is right for a creator tool.
- Export and gallery actions are discoverable near generated output.

## UX Risks

1. Welcome overlay layering breaks the first impression.
   Evidence: `01-welcome.png`. The welcome cards appear behind or mixed with the main app. The user is asked to choose a provider while the underlying project, output, and footer controls remain visually active.

2. The default main screen looks crowded before the user has done anything.
   Evidence: `02-starter-main.png`. The project form, asset form, run controls, output controls, footer controls, and long status message are all visible at once. This is powerful, but it makes the first session feel like a control panel instead of a guided path.

3. Important form content is clipped.
   Evidence: `02-starter-main.png`, `03-providers-drawer.png`, `04-run-check.png`. The art style field scrolls internally, the palette text and swatches overlap visually, and the asset layout row is cramped.

4. Settings drawer tab navigation is hard to scan.
   Evidence: `03-providers-drawer.png`. Only "Providers" and "Advanced" are visible, with arrows for hidden tabs. A new user may not realize project, asset, and layout settings are also in the drawer.

5. Check Run competes with output instead of becoming the current task.
   Evidence: `04-run-check.png`. The preflight text is useful, but it is pushed below an empty generated-output box.

6. Generated output is not visually rewarded after generation.
   Evidence: `05-generated-output.png`. The status says generation completed, but the visible output shows only "base (single_sprite)" and a raw-atlas filename. The generated image is off-screen or hidden by the still-open preflight panel.

7. Status copy exposes long implementation paths.
   Evidence: `02-starter-main.png`, `06-export-status.png`. Long file paths wrap and dominate the footer. The product should show a short success message plus an open-folder action.

8. Run summary can become stale.
   Evidence: `06-export-status.png`. The upper run summary still reads "Generating asset..." after export succeeded.

## Accessibility Risks

- Keyboard and screen-reader semantics need testing in a real interactive session. Screenshots confirm visible labels, but not tab order, focus recovery, or assistive technology names.
- Some controls may be below comfortable target size when the layout is compressed, especially drawer tabs, spinbox arrows, and the small gear/settings button.
- Internal scrolling inside form fields can hide content from users who rely on zoom or large text.
- The first-run overlay issue creates a likely focus-management risk: users may be able to interact with background controls while the overlay is visible.
- Status messages that rely on long paths are hard to scan and may be verbose for screen-reader users.

## Recommended Improvement Direction

Recommended: a first-run usability pass, not a full feature expansion.

1. Make first run a true guided start.
   Fix the welcome overlay layering and focus behavior. Show one clear entry decision: start free, connect provider, or open existing project. Background controls should be visually and interactively inactive while the overlay is shown.

2. Promote the active workflow state.
   Treat Check Run, Generate, and Export as distinct states. When Check Run is active, show the preflight where the output preview normally sits. When generation finishes, collapse or hide preflight and scroll/focus to the generated images.

3. Tighten the main screen for readability.
   Prevent field and swatch overlap, give the layout row more room, shorten footer paths, and make stale status states update in both the run summary and footer.

Alternative paths:

- Visual polish pass: improve spacing, icons, and labels while leaving flow behavior mostly intact. Lower risk, but it would not fix the biggest first-run friction.
- Power-user pass: improve provider model management, galleries, and export controls. Useful later, but it adds capability before the current first-session path feels easy.

## Evidence Limits

- This audit used screenshot evidence and direct UI state changes. It did not test a live Pollinations/OpenRouter/OpenAI image call.
- Mock generation was used for output and export screenshots.
- This audit did not verify keyboard-only operation, screen-reader output, high-contrast mode, or text scaling behavior.
- The app was captured at 1925x1080 on Windows. Smaller laptop behavior should be tested before shipping layout changes.
