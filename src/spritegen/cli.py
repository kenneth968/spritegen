"""CLI entry point for sprite generation pipeline.

Usage:
    python -m spritegen.cli generate --style mycomed_towers --sprites puffball_1 puffball_2 puffball_3 puffball_4
    python -m spritegen.cli slice --sheet output/sheets/spritesheet.png --output output/sprites
    python -m spritegen.cli style create --name my_style --base-prompt "pixel art, 64x64"
"""

import argparse
import json
import sys
from pathlib import Path

from .layouts import PRESET_LAYOUTS, AssetLayout, get_layout
from .enhancement import PromptEnhancer
from .provider_models import (
    IMAGE_ROLE,
    MODEL_ROLES,
    PROMPT_ROLE,
    ModelDiscoveryError,
    combined_model_suggestions,
    default_model,
    discover_model_suggestions,
    model_source_urls,
)
from .project_export import ProjectAssetExporter
from .project_generation import ProjectAssetGenerator
from .projects import (
    AssetSpec,
    AssetTypeSpec,
    COLOR_TREATMENT_MODES,
    ColorTreatment,
    EvolutionPlan,
    ProjectSpec,
    ProjectStore,
    PostProcessSettings,
    ProviderDefaults,
    PromptPlanner,
    apply_asset_type_enhancement,
    apply_project_enhancement,
    slugify,
)
from .workflow_presets import get_workflow_preset, list_workflow_presets
from . import (
    SpriteConfig,
    SpriteDefinition,
    SpriteGenerator,
    StyleManager,
    Slicer,
    create_mycomed_style,
)
from .models import SpriteMetadata
from .mycomed import EVOLUTION_STAGES


def cmd_generate(args: argparse.Namespace) -> int:
    config = SpriteConfig(
        output_dir=Path(args.output_dir),
        sheet_dir=Path(args.sheet_dir),
        api_provider=args.provider or "openai",
        api_model=args.model or "dall-e-3",
    )

    if args.dry_run:
        print("Dry run mode — would generate with:")
        print(f"  provider: {config.api_provider}")
        print(f"  model: {config.api_model}")
        print(f"  style: {args.style}")
        print(f"  sprites: {args.sprites}")
        return 0

    errors = config.validate()
    if errors:
        print("Configuration errors:")
        for e in errors:
            print(f"  - {e}")
        return 1

    style_mgr = StyleManager()

    if args.create_style:
        style = create_mycomed_style(style_mgr)
        print(f"Created style: {style.name}")
        return 0

    style = style_mgr.load(args.style)
    if not style:
        print(f"Style '{args.style}' not found. Use --create-style to create it.")
        return 1

    generator = SpriteGenerator(style=style, config=config, style_manager=style_mgr)

    sprites = [
        SpriteDefinition(name=args.sprites[i], prompt=p, index=i)
        for i, p in enumerate(args.sprites)
    ]

    print(f"Generating sprite sheet with {len(sprites)} sprites...")
    sheet = generator.generate_sheet(name=args.name or "sprites", sprites=sprites)

    sheet_path = config.sheet_dir / f"{args.name or 'sprites'}.png"
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save_sheet(sheet_path)
    print(f"Saved sheet to: {sheet_path}")

    return 0


def cmd_slice(args: argparse.Namespace) -> int:
    config = SpriteConfig(output_dir=Path(args.output))

    slicer = Slicer(output_dir=config.output_dir, config=config)

    sheet_data = Path(args.sheet).read_bytes()
    from .models import GeneratedSheet

    layout = config.get_layout(args.count or 4)
    sprites = []
    for i in range(args.count or layout.sprite_count):
        sprites.append(
            SpriteDefinition(
                name=f"sprite_{i + 1}",
                prompt="manual slice",
                index=i,
            )
        )

    sheet = GeneratedSheet(
        image_data=sheet_data,
        layout=layout,
        sprites=[
            SpriteMetadata(
                name=sprite.name,
                sprite_index=sprite.index,
                position=(
                    (sprite.index % layout.columns) * layout.cell_width + layout.margin,
                    (sprite.index // layout.columns) * layout.cell_height + layout.margin,
                ),
                size=(layout.cell_width - layout.padding, layout.cell_height - layout.padding),
                prompt=sprite.prompt,
            )
            for sprite in sprites
        ],
        style_seed="unknown",
        generation_params={},
    )

    for i in range(len(sheet.sprites)):
        path = slicer.save_sprite(sheet, i)
        print(f"Saved: {path}")

    return 0


def cmd_layout(args: argparse.Namespace) -> int:
    if args.layout_command == "list":
        print("Available layouts:")
        for name, layout in sorted(PRESET_LAYOUTS.items()):
            print(f"  - {name}: {layout.width}x{layout.height}, {len(layout.regions)} regions")
        return 0

    if args.layout_command == "info":
        layout = get_layout(args.name)
        print(f"Layout: {layout.name}")
        print(f"Canvas: {layout.width}x{layout.height}")
        print(layout.prompt_instructions)
        for region in layout.regions:
            print(
                f"  - {region.name}: ({region.x},{region.y}) "
                f"{region.width}x{region.height} - {region.prompt_role}"
            )
        return 0

    if args.layout_command == "slice":
        layout = get_layout(args.layout)
        image_data = Path(args.image).read_bytes()
        slicer = Slicer(output_dir=Path(args.output))
        paths = slicer.slice_layout_image(image_data, layout, prefix=args.prefix)
        for path in paths:
            print(f"Saved: {path}")
        return 0

    return 1


def cmd_models(args: argparse.Namespace) -> int:
    role_label = "image" if args.role == IMAGE_ROLE else "prompt"
    provider_label = args.provider.title() if args.provider != "openai" else "OpenAI"
    if args.provider == "openrouter":
        provider_label = "OpenRouter"
    elif args.provider == "pollinations":
        provider_label = "Pollinations"

    online_suggestions = []
    if args.online:
        try:
            online_suggestions = discover_model_suggestions(
                args.provider,
                args.role,
                search=args.search,
                limit=args.limit,
            )
        except ModelDiscoveryError as exc:
            print(f"Online model discovery failed: {exc}")

    suggestions = combined_model_suggestions(
        args.provider,
        args.role,
        online_suggestions,
    )
    if args.search and not args.online:
        search_text = args.search.lower()
        suggestions = [
            suggestion
            for suggestion in suggestions
            if search_text
            in " ".join(
                [
                    suggestion.model,
                    suggestion.label,
                    suggestion.note,
                ]
            ).lower()
        ]
    print(f"{provider_label} {role_label} model suggestions:")
    if not suggestions:
        print("  - none")
    for suggestion in suggestions:
        default_marker = " (default)" if suggestion.model == default_model(args.provider, args.role) else ""
        print(f"  - {suggestion.model}{default_marker}")
        print(f"    {suggestion.label}")
        if suggestion.note:
            print(f"    {suggestion.note}")

    sources = model_source_urls(args.provider, args.role)
    if sources:
        print("Sources:")
        for url in sources:
            print(f"  - {url}")
    return 0


def print_layout(layout: AssetLayout) -> None:
    print(f"Layout: {layout.name}")
    print(f"Canvas: {layout.width}x{layout.height}")
    print(layout.prompt_instructions)
    for region in layout.regions:
        print(
            f"  - {region.name}: ({region.x},{region.y}) "
            f"{region.width}x{region.height} - {region.prompt_role}"
        )


def cmd_project(args: argparse.Namespace) -> int:
    store = ProjectStore(root=args.project_root)
    planner = PromptPlanner()

    if args.project_command == "presets":
        print("Available workflow presets:")
        for preset in list_workflow_presets():
            print(f"  - {preset.key}: {preset.label}")
            print(f"    {preset.description}")
            print(
                f"    asset_type={preset.asset_type}, "
                f"evolutions={preset.evolution_count}, layout={preset.default_layout}"
            )
        return 0

    if args.project_command == "layout":
        project = store.load_project(args.project)

        if args.layout_action == "list":
            print("Built-in layouts:")
            for name, layout in sorted(PRESET_LAYOUTS.items()):
                print(f"  - {name}: {layout.width}x{layout.height}, {len(layout.regions)} regions")
            print("Project layouts:")
            if not project.custom_layouts:
                print("  - none")
            for name, layout in sorted(project.custom_layouts.items()):
                print(f"  - {name}: {layout.width}x{layout.height}, {len(layout.regions)} regions")
            return 0

        if args.layout_action == "info":
            print_layout(project.get_layout(args.name))
            return 0

        if args.layout_action == "add-grid":
            layout = AssetLayout.grid(
                name=args.name,
                width=args.width,
                height=args.height,
                rows=args.rows,
                columns=args.columns,
                region_prefix=args.region_prefix,
            )
            if args.prompt_instructions:
                layout.prompt_instructions = args.prompt_instructions
            project.add_layout(layout)
            path = store.save_project(project)
            print(f"Saved layout: {layout.name}")
            print(f"Project file: {path}")
            return 0

        if args.layout_action == "add-hero-grid":
            layout = AssetLayout.hero_plus_grid(
                name=slugify(args.name).replace("-", "_"),
                width=args.width,
                height=args.height,
                hero_width=args.hero_width,
                grid_rows=args.grid_rows,
                grid_columns=args.grid_columns,
                hero_region_name=args.hero_region_name,
                grid_region_prefix=args.grid_region_prefix,
                hero_side=args.hero_side,
            )
            if args.prompt_instructions:
                layout.prompt_instructions = args.prompt_instructions
            project.add_layout(layout)
            path = store.save_project(project)
            print(f"Saved layout: {layout.name}")
            print(f"Project file: {path}")
            return 0

        if args.layout_action == "import":
            data = json.loads(Path(args.file).read_text(encoding="utf-8"))
            layout = AssetLayout.from_dict(data)
            project.add_layout(layout)
            path = store.save_project(project)
            print(f"Imported layout: {layout.name}")
            print(f"Project file: {path}")
            return 0

        if args.layout_action == "export":
            layout = project.get_layout(args.name)
            data = json.dumps(layout.to_dict(), indent=2)
            if args.output:
                output = Path(args.output)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(data, encoding="utf-8")
                print(f"Exported layout: {output}")
            else:
                print(data)
            return 0

        if args.layout_action == "slice":
            layout = project.get_layout(args.name)
            image_data = Path(args.image).read_bytes()
            slicer = Slicer(output_dir=Path(args.output))
            paths = slicer.slice_layout_image(image_data, layout, prefix=args.prefix)
            for path in paths:
                print(f"Saved: {path}")
            return 0

        return 1

    if args.project_command == "init":
        preset = get_workflow_preset(args.preset) if args.preset else None
        asset_type_name = args.asset_type or (preset.asset_type if preset else "tower")
        asset_type_context = args.asset_type_context
        if asset_type_context is None and preset:
            asset_type_context = preset.shared_prompt
        evolutions = args.evolutions
        if evolutions is None:
            evolutions = preset.evolution_count if preset else 4
        evolution_context = args.evolution_context
        if evolution_context is None and preset:
            evolution_context = preset.evolution_prompt
        evolution_labels = list(preset.evolution_labels) if preset else []
        layout_name = args.layout or (preset.default_layout if preset else "single_sprite")

        if evolutions < 1:
            print("--evolutions must be at least 1")
            return 1
        get_layout(layout_name)
        palette = [c.strip() for c in args.palette.split(",") if c.strip()]
        project = ProjectSpec(
            name=args.name,
            summary=args.summary or "",
            visual_style=args.style,
            shared_context=args.context,
            palette=palette,
            negative_prompt=args.negative_prompt or "",
            provider_defaults=ProviderDefaults(
                image_provider=args.provider,
                image_model=args.image_model,
                prompt_provider=args.prompt_provider,
                prompt_model=args.prompt_model,
            ),
            color_treatment=ColorTreatment(
                mode=args.color_mode,
                custom_prompt=args.color_prompt or "",
            ),
            postprocess=PostProcessSettings(remove_background=args.remove_background),
        )
        project.add_asset_type(
            AssetTypeSpec(
                name=asset_type_name,
                shared_prompt=asset_type_context or "",
                evolution=EvolutionPlan(
                    count=evolutions,
                    labels=evolution_labels,
                    shared_prompt=evolution_context or "",
                ),
                default_layout=layout_name,
            )
        )
        path = store.save_project(project)
        print(f"Created project: {project.name}")
        print(f"Project file: {path}")
        return 0

    if args.project_command == "asset":
        project = store.load_project(args.project)
        asset_type = project.get_asset_type(args.asset_type)
        project.get_layout(args.layout or asset_type.default_layout)
        asset = AssetSpec(
            name=args.name,
            asset_type=args.asset_type,
            description=args.description,
            details=args.details or "",
            enhanced_prompt=args.enhanced_prompt or "",
            layout=args.layout,
        )
        known_assets = store.load_assets(project)
        asset_path = store.save_asset(project, asset)
        packets = planner.build_prompt_packets(project, asset, known_assets=known_assets)
        plan_path = store.save_prompt_plan(project, asset, packets)

        print(f"Saved asset: {asset_path}")
        print(f"Saved prompt plan: {plan_path}")
        print(f"Enhancement brief model: {project.provider_defaults.prompt_model}")
        print(planner.build_enhancement_brief(project, asset_type, asset, known_assets))
        if args.print_prompts:
            for packet in packets:
                label = packet.stage_label or "single"
                print(f"\n--- {asset.name} / {label} ---")
                print(packet.prompt)
        else:
            print(f"Prompt packets: {len(packets)}")
        return 0

    if args.project_command == "enhance":
        project = store.load_project(args.project)
        asset = store.load_asset(project, args.asset)
        asset_type = project.get_asset_type(asset.asset_type)
        known_assets = store.load_assets(project)
        brief = planner.build_enhancement_brief(project, asset_type, asset, known_assets)
        provider = args.provider or project.provider_defaults.prompt_provider
        model = args.model or project.provider_defaults.prompt_model

        enhanced = PromptEnhancer().enhance(
            brief,
            provider=provider,
            model=model,
            api_key=args.api_key,
            system_prompt=planner.build_enhancement_system_prompt(
                project,
                asset_type,
                asset,
            ),
        )
        asset.enhanced_prompt = enhanced
        asset_path = store.save_asset(project, asset)
        packets = planner.build_prompt_packets(project, asset, known_assets=known_assets)
        plan_path = store.save_prompt_plan(project, asset, packets)

        print(f"Enhanced asset prompt: {asset_path}")
        print(f"Updated prompt plan: {plan_path}")
        print(enhanced)
        return 0

    if args.project_command == "enhance-project":
        project = store.load_project(args.project)
        provider = args.provider or project.provider_defaults.prompt_provider
        model = args.model or project.provider_defaults.prompt_model
        data = PromptEnhancer().enhance_json(
            planner.build_project_enhancement_brief(project),
            provider=provider,
            model=model,
            api_key=args.api_key,
            system_prompt=planner.build_project_enhancement_system_prompt(),
            fallback=planner.project_enhancement_fallback(project),
        )
        apply_project_enhancement(project, data)
        path = store.save_project(project)

        print(f"Enhanced project: {path}")
        print(f"Summary: {project.summary}")
        print(f"Style: {project.visual_style}")
        print(f"Universe: {project.shared_context}")
        if project.palette:
            print(f"Palette: {', '.join(project.palette)}")
        return 0

    if args.project_command == "enhance-type":
        project = store.load_project(args.project)
        asset_type = project.get_asset_type(args.asset_type)
        provider = args.provider or project.provider_defaults.prompt_provider
        model = args.model or project.provider_defaults.prompt_model
        data = PromptEnhancer().enhance_json(
            planner.build_asset_type_enhancement_brief(project, asset_type),
            provider=provider,
            model=model,
            api_key=args.api_key,
            system_prompt=planner.build_asset_type_enhancement_system_prompt(),
            fallback=planner.asset_type_enhancement_fallback(asset_type),
        )
        apply_asset_type_enhancement(asset_type, data)
        project.add_asset_type(asset_type)
        path = store.save_project(project)

        print(f"Enhanced asset type: {asset_type.name}")
        print(f"Project file: {path}")
        print(f"Rules: {asset_type.shared_prompt}")
        if asset_type.evolution.shared_prompt:
            print(f"Evolution: {asset_type.evolution.shared_prompt}")
        if asset_type.evolution.labels:
            print(f"Labels: {', '.join(asset_type.evolution.labels)}")
        return 0

    if args.project_command == "generate":
        project = store.load_project(args.project)
        asset = store.load_asset(project, args.asset)
        known_assets = store.load_assets(project)
        packets = planner.build_prompt_packets(project, asset, known_assets=known_assets)
        plan_path = store.save_prompt_plan(project, asset, packets)

        if args.dry_run:
            print(f"Dry run: would generate {len(packets)} image(s)")
            print(f"Prompt plan: {plan_path}")
            for packet in packets:
                label = packet.stage_label or "single"
                print(f"  - {asset.name} / {label}: {packet.layout_name}")
            return 0

        result = ProjectAssetGenerator(store=store).generate_packets(
            project=project,
            asset=asset,
            packets=packets,
            provider=args.provider,
            model=args.model,
            api_key=args.api_key,
            output_root=args.output_root,
            remove_background=args.remove_background,
        )
        print(f"Generated asset: {result.output_dir}")
        print(f"Manifest: {result.manifest_path}")
        for output in result.outputs:
            label = output.stage_label or "single"
            print(f"  - {label}: {output.raw_image} ({len(output.slices)} slices)")
        return 0

    if args.project_command == "export":
        project = store.load_project(args.project)
        asset = store.load_asset(project, args.asset)
        result = ProjectAssetExporter(store=store).export_saved_asset(
            project=project,
            asset=asset,
            output_dir=args.output,
            manifest_path=args.manifest,
            include_raw=args.include_raw,
        )
        print(f"Exported sprites: {result.output_dir}")
        print(f"Export manifest: {result.manifest_path}")
        print(f"Sprites: {len(result.sprites)}")
        if result.raw_images:
            print(f"Raw images: {len(result.raw_images)}")
        return 0

    return 1


def cmd_evolution_chain(args: argparse.Namespace) -> int:
    config = SpriteConfig(
        output_dir=Path(args.output_dir),
        sheet_dir=Path(args.sheet_dir),
        api_provider=args.provider or "openai",
        api_model=args.model or "dall-e-2",
    )

    if args.dry_run:
        print("Dry run mode — would generate evolution chain:")
        print(f"  tower: {args.tower}")
        print(f"  provider: {config.api_provider}")
        print(f"  model: {config.api_model}")
        return 0

    errors = config.validate()
    if errors:
        print("Configuration errors:")
        for e in errors:
            print(f"  - {e}")
        return 1

    style_mgr = StyleManager()

    if args.create_style:
        style = create_mycomed_style(style_mgr)
        print(f"Created style: {style.name}")
    else:
        style = style_mgr.load(args.style or "mycomed_towers")
        if not style:
            print(f"Style '{args.style}' not found. Use --create-style to create it.")
            return 1

    if args.tower not in EVOLUTION_STAGES:
        print(f"Tower '{args.tower}' not found. Available towers:")
        for tower_id in EVOLUTION_STAGES:
            print(f"  - {tower_id}")
        return 1

    generator = SpriteGenerator(style=style, config=config, style_manager=style_mgr)
    stages = EVOLUTION_STAGES[args.tower]
    print(f"Generating {args.tower} evolution chain ({len(stages)} stages)...")

    for stage_idx, stage in enumerate(stages):
        stage_num = stage_idx + 1
        stage_name = stage["name"]
        stage_prompt = stage["prompt"]
        sprite_count = stage.get("count", 4)

        print(f"\n--- Stage {stage_num}/4: {stage_name} ---")

        sprites = [
            SpriteDefinition(
                name=f"{args.tower}_s{stage_num}_v{v}",
                prompt=stage_prompt,
                index=v,
            )
            for v in range(sprite_count)
        ]

        try:
            sheet = generator.generate_sheet(
                name=f"{args.tower}_stage{stage_num}",
                sprites=sprites,
            )

            sheet_path = config.sheet_dir / f"{args.tower}_stage{stage_num}.png"
            sheet_path.parent.mkdir(parents=True, exist_ok=True)
            sheet.save_sheet(sheet_path)
            print(f"  Sheet saved: {sheet_path}")

            stage_output_dir = config.output_dir / f"{args.tower}_stage{stage_num}"
            stage_slicer = Slicer(output_dir=stage_output_dir, config=config)

            for i in range(len(sheet.sprites)):
                path = stage_slicer.save_sprite(sheet, i)
                print(f"  Sprite saved: {path.name}")

            metadata_path = stage_slicer.save_metadata(sheet)
            print(f"  Metadata saved: {metadata_path.name}")

        except Exception as e:
            print(f"  Error: {e}")
            if "billing" in str(e).lower():
                print("  Billing limit reached - stopping generation")
                break
            continue

    print("\nEvolution chain generation complete!")
    return 0


def cmd_style(args: argparse.Namespace) -> int:
    style_mgr = StyleManager()

    if args.style_command == "create":
        style = style_mgr.create_style(
            name=args.name,
            base_prompt=args.base_prompt,
            negative_prompt=args.negative_prompt or "",
            color_palette=args.colors.split(",") if args.colors else None,
            visual_tags=args.tags.split(",") if args.tags else None,
        )
        print(f"Created style '{style.name}' with seed: {style.seed}")
        return 0

    elif args.style_command == "list":
        from .style import PRESET_STYLES

        print("Available styles:")
        for name in sorted(set(list(PRESET_STYLES.keys()) + ["mycomed_towers"])):
            style = style_mgr.load(name)
            if style:
                print(f"  - {name} ({style.generation_count} generations)")
        return 0

    elif args.style_command == "info":
        style = style_mgr.load(args.name)
        if not style:
            print(f"Style '{args.name}' not found")
            return 1
        print(f"Style: {style.name}")
        print(f"Seed: {style.seed}")
        print(f"Base prompt: {style.base_prompt}")
        print(f"Color palette: {style.color_palette}")
        print(f"Visual tags: {style.visual_tags}")
        print(f"Generation count: {style.generation_count}")
        return 0

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprite sheet generation pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen_parser = subparsers.add_parser("generate", help="Generate a sprite sheet")
    gen_parser.add_argument("--style", default="pixel_art", help="Style name to use")
    gen_parser.add_argument("--name", help="Name for the sprite sheet")
    gen_parser.add_argument(
        "--sprites", nargs="+", required=True, help="Sprite prompts"
    )
    gen_parser.add_argument(
        "--output-dir", default="output/sprites", help="Output directory"
    )
    gen_parser.add_argument(
        "--sheet-dir", default="output/sheets", help="Sheet output directory"
    )
    gen_parser.add_argument("--provider", default="openai", help="API provider")
    gen_parser.add_argument(
        "--model", default="dall-e-3", help="API model (dall-e-3 or dall-e-2)"
    )
    gen_parser.add_argument(
        "--create-style", action="store_true", help="Create the style first"
    )
    gen_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without calling API",
    )

    slice_parser = subparsers.add_parser("slice", help="Slice a sprite sheet")
    slice_parser.add_argument("--sheet", required=True, help="Path to sprite sheet")
    slice_parser.add_argument(
        "--output", default="output/sprites", help="Output directory"
    )
    slice_parser.add_argument("--count", type=int, help="Number of sprites")

    layout_parser = subparsers.add_parser("layout", help="Manage and slice atlas layouts")
    layout_subparsers = layout_parser.add_subparsers(
        dest="layout_command",
        required=True,
    )
    layout_subparsers.add_parser("list", help="List built-in atlas layouts")
    layout_info = layout_subparsers.add_parser("info", help="Show a layout")
    layout_info.add_argument("--name", required=True)
    layout_slice = layout_subparsers.add_parser("slice", help="Slice an image by layout")
    layout_slice.add_argument("--image", required=True, help="Generated atlas image")
    layout_slice.add_argument("--layout", required=True, help="Layout preset name")
    layout_slice.add_argument("--output", default="output/sprites", help="Output directory")
    layout_slice.add_argument("--prefix", help="Filename prefix")

    models_parser = subparsers.add_parser(
        "models",
        help="List suggested provider model IDs",
    )
    models_parser.add_argument(
        "--provider",
        default="openrouter",
        choices=["mock", "pollinations", "openai", "openrouter"],
        help="Provider to list model suggestions for",
    )
    models_parser.add_argument(
        "--role",
        default=IMAGE_ROLE,
        choices=MODEL_ROLES,
        help="Model role: image generation or prompt improvement",
    )
    models_parser.add_argument(
        "--online",
        action="store_true",
        help="Fetch provider model lists when supported, then merge with offline suggestions",
    )
    models_parser.add_argument(
        "--search",
        default="",
        help="Filter model suggestions by text, such as minimax or image",
    )
    models_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum online model suggestions to fetch",
    )

    evo_parser = subparsers.add_parser(
        "evolution-chain", help="Generate a tower evolution chain"
    )
    evo_parser.add_argument(
        "--tower",
        required=True,
        choices=["puffball", "cordyceps", "amanita"],
        help="Tower type to generate",
    )
    evo_parser.add_argument(
        "--style", default="mycomed_towers", help="Style name to use"
    )
    evo_parser.add_argument(
        "--output-dir", default="output/sprites", help="Sprite output directory"
    )
    evo_parser.add_argument(
        "--sheet-dir", default="output/sheets", help="Sheet output directory"
    )
    evo_parser.add_argument("--provider", default="openai", help="API provider")
    evo_parser.add_argument(
        "--model", default="dall-e-2", help="API model (dall-e-3 or dall-e-2)"
    )
    evo_parser.add_argument(
        "--create-style", action="store_true", help="Create the style first"
    )
    evo_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without calling API",
    )

    style_parser = subparsers.add_parser("style", help="Manage styles")
    style_subparsers = style_parser.add_subparsers(dest="style_command", required=True)
    style_create = style_subparsers.add_parser("create", help="Create a new style")
    style_create.add_argument("--name", required=True)
    style_create.add_argument("--base-prompt", required=True)
    style_create.add_argument("--negative-prompt", default="")
    style_create.add_argument("--colors")
    style_create.add_argument("--tags")
    style_subparsers.add_parser("list", help="List styles")
    style_info = style_subparsers.add_parser("info", help="Show style info")
    style_info.add_argument("--name", required=True)

    project_parser = subparsers.add_parser(
        "project",
        help="Create project-aware prompt plans",
    )
    project_parser.add_argument(
        "--project-root",
        default="projects",
        help="Directory where project specs are stored",
    )
    project_subparsers = project_parser.add_subparsers(
        dest="project_command",
        required=True,
    )

    project_subparsers.add_parser(
        "presets",
        help="List built-in workflow presets for common game-asset shapes",
    )

    project_layout = project_subparsers.add_parser(
        "layout",
        help="Manage project-specific atlas layouts",
    )
    project_layout.add_argument("--project", required=True, help="Project slug or JSON path")
    project_layout_subparsers = project_layout.add_subparsers(
        dest="layout_action",
        required=True,
    )
    project_layout_subparsers.add_parser("list", help="List built-in and project layouts")
    project_layout_info = project_layout_subparsers.add_parser("info", help="Show a layout")
    project_layout_info.add_argument("--name", required=True)
    project_layout_add_grid = project_layout_subparsers.add_parser(
        "add-grid",
        help="Add a reusable grid atlas layout to the project",
    )
    project_layout_add_grid.add_argument("--name", required=True)
    project_layout_add_grid.add_argument("--width", type=int, default=1024)
    project_layout_add_grid.add_argument("--height", type=int, default=1024)
    project_layout_add_grid.add_argument("--rows", type=int, required=True)
    project_layout_add_grid.add_argument("--columns", type=int, required=True)
    project_layout_add_grid.add_argument("--region-prefix", default="cell")
    project_layout_add_grid.add_argument("--prompt-instructions", default="")
    project_layout_add_hero_grid = project_layout_subparsers.add_parser(
        "add-hero-grid",
        help="Add a large hero region plus a grid of smaller related cells",
    )
    project_layout_add_hero_grid.add_argument("--name", required=True)
    project_layout_add_hero_grid.add_argument("--width", type=int, default=1024)
    project_layout_add_hero_grid.add_argument("--height", type=int, default=1024)
    project_layout_add_hero_grid.add_argument("--hero-width", type=int, default=512)
    project_layout_add_hero_grid.add_argument("--grid-rows", type=int, required=True)
    project_layout_add_hero_grid.add_argument("--grid-columns", type=int, required=True)
    project_layout_add_hero_grid.add_argument("--hero-region-name", default="full_body")
    project_layout_add_hero_grid.add_argument("--grid-region-prefix", default="head")
    project_layout_add_hero_grid.add_argument(
        "--hero-side",
        choices=["left", "right"],
        default="left",
    )
    project_layout_add_hero_grid.add_argument("--prompt-instructions", default="")
    project_layout_import = project_layout_subparsers.add_parser(
        "import",
        help="Import a layout JSON file into the project",
    )
    project_layout_import.add_argument("--file", required=True)
    project_layout_export = project_layout_subparsers.add_parser(
        "export",
        help="Export a built-in or project layout as JSON",
    )
    project_layout_export.add_argument("--name", required=True)
    project_layout_export.add_argument("--output")
    project_layout_slice = project_layout_subparsers.add_parser(
        "slice",
        help="Slice an image with a built-in or project layout",
    )
    project_layout_slice.add_argument("--name", required=True, help="Layout name")
    project_layout_slice.add_argument("--image", required=True, help="Generated atlas image")
    project_layout_slice.add_argument("--output", default="output/sprites")
    project_layout_slice.add_argument("--prefix")

    project_init = project_subparsers.add_parser("init", help="Create a project spec")
    project_init.add_argument("--name", required=True)
    project_init.add_argument("--summary", default="")
    project_init.add_argument("--style", required=True, help="Shared visual style")
    project_init.add_argument("--context", required=True, help="Shared project universe")
    project_init.add_argument("--palette", default="", help="Comma-separated colors")
    project_init.add_argument("--negative-prompt", default="")
    project_init.add_argument("--provider", default="openai")
    project_init.add_argument("--image-model", default=default_model("openai", IMAGE_ROLE))
    project_init.add_argument("--prompt-provider", default="openai")
    project_init.add_argument("--prompt-model", default=default_model("openai", PROMPT_ROLE))
    project_init.add_argument(
        "--preset",
        choices=sorted(preset.key for preset in list_workflow_presets()),
        help="Apply a common asset workflow preset",
    )
    project_init.add_argument(
        "--color-mode",
        default="full_color",
        choices=sorted(COLOR_TREATMENT_MODES),
        help="Color treatment carried into prompt enhancement and image generation",
    )
    project_init.add_argument(
        "--color-prompt",
        default="",
        help="Extra color-mode instructions, such as value bands or palette rules",
    )
    project_init.add_argument(
        "--remove-background",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether generated layout slices should have simple backgrounds removed",
    )
    project_init.add_argument("--asset-type")
    project_init.add_argument("--asset-type-context")
    project_init.add_argument("--evolutions", type=int)
    project_init.add_argument("--evolution-context")
    project_init.add_argument("--layout")

    project_asset = project_subparsers.add_parser(
        "asset",
        help="Create an asset spec and prompt plan",
    )
    project_asset.add_argument("--project", required=True, help="Project slug or JSON path")
    project_asset.add_argument("--asset-type", default="tower")
    project_asset.add_argument("--name", required=True)
    project_asset.add_argument("--description", required=True)
    project_asset.add_argument("--details", default="")
    project_asset.add_argument("--enhanced-prompt", default="")
    project_asset.add_argument("--layout")
    project_asset.add_argument(
        "--print-prompts",
        action="store_true",
        help="Print full image prompts for every packet",
    )

    project_enhance = project_subparsers.add_parser(
        "enhance",
        help="Improve a saved asset prompt using the project's prompt provider",
    )
    project_enhance.add_argument("--project", required=True, help="Project slug or JSON path")
    project_enhance.add_argument("--asset", required=True, help="Asset slug or JSON path")
    project_enhance.add_argument("--provider")
    project_enhance.add_argument("--model")
    project_enhance.add_argument("--api-key", help="Session-only API key override")

    project_enhance_project = project_subparsers.add_parser(
        "enhance-project",
        help="Improve the saved project style, universe, palette, and negative prompt",
    )
    project_enhance_project.add_argument(
        "--project",
        required=True,
        help="Project slug or JSON path",
    )
    project_enhance_project.add_argument("--provider")
    project_enhance_project.add_argument("--model")
    project_enhance_project.add_argument("--api-key", help="Session-only API key override")

    project_enhance_type = project_subparsers.add_parser(
        "enhance-type",
        help="Improve reusable rules for one saved project asset type",
    )
    project_enhance_type.add_argument("--project", required=True, help="Project slug or JSON path")
    project_enhance_type.add_argument("--asset-type", required=True)
    project_enhance_type.add_argument("--provider")
    project_enhance_type.add_argument("--model")
    project_enhance_type.add_argument("--api-key", help="Session-only API key override")

    project_generate = project_subparsers.add_parser(
        "generate",
        help="Generate a saved asset from its project prompt plan",
    )
    project_generate.add_argument("--project", required=True, help="Project slug or JSON path")
    project_generate.add_argument("--asset", required=True, help="Asset slug or JSON path")
    project_generate.add_argument("--provider")
    project_generate.add_argument("--model")
    project_generate.add_argument("--api-key", help="Session-only image API key override")
    project_generate.add_argument("--output-root")
    project_generate.add_argument(
        "--remove-background",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Override the saved project background-removal setting for this run",
    )
    project_generate.add_argument(
        "--dry-run",
        action="store_true",
        help="Write/update the prompt plan without calling an image API",
    )

    project_export = project_subparsers.add_parser(
        "export",
        help="Copy generated slices into a game-ready export folder",
    )
    project_export.add_argument("--project", required=True, help="Project slug or JSON path")
    project_export.add_argument("--asset", required=True, help="Asset slug or JSON path")
    project_export.add_argument("--output", help="Export directory")
    project_export.add_argument("--manifest", help="Generation manifest path override")
    project_export.add_argument(
        "--include-raw",
        action="store_true",
        help="Also copy raw generated atlases into the export folder",
    )

    args = parser.parse_args()

    if args.command == "generate":
        return cmd_generate(args)
    elif args.command == "slice":
        return cmd_slice(args)
    elif args.command == "evolution-chain":
        return cmd_evolution_chain(args)
    elif args.command == "style":
        return cmd_style(args)
    elif args.command == "layout":
        return cmd_layout(args)
    elif args.command == "models":
        return cmd_models(args)
    elif args.command == "project":
        return cmd_project(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
