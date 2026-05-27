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
