"""CLI entry point for sprite generation pipeline.

Usage:
    python -m spritegen.cli generate --style mycomed_towers --sprites puffball_1 puffball_2 puffball_3 puffball_4
    python -m spritegen.cli slice --sheet output/sheets/spritesheet.png --output output/sprites
    python -m spritegen.cli style create --name my_style --base-prompt "pixel art, 64x64"
"""

import argparse
import sys
from pathlib import Path

from .layouts import PRESET_LAYOUTS, get_layout
from .projects import (
    AssetSpec,
    AssetTypeSpec,
    EvolutionPlan,
    ProjectSpec,
    ProjectStore,
    ProviderDefaults,
    PromptPlanner,
)
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


def cmd_project(args: argparse.Namespace) -> int:
    store = ProjectStore(root=args.project_root)
    planner = PromptPlanner()

    if args.project_command == "init":
        if args.evolutions < 1:
            print("--evolutions must be at least 1")
            return 1
        get_layout(args.layout)
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
        )
        project.add_asset_type(
            AssetTypeSpec(
                name=args.asset_type,
                shared_prompt=args.asset_type_context or "",
                evolution=EvolutionPlan(
                    count=args.evolutions,
                    shared_prompt=args.evolution_context or "",
                ),
                default_layout=args.layout,
            )
        )
        path = store.save_project(project)
        print(f"Created project: {project.name}")
        print(f"Project file: {path}")
        return 0

    if args.project_command == "asset":
        project = store.load_project(args.project)
        asset_type = project.get_asset_type(args.asset_type)
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

    project_init = project_subparsers.add_parser("init", help="Create a project spec")
    project_init.add_argument("--name", required=True)
    project_init.add_argument("--summary", default="")
    project_init.add_argument("--style", required=True, help="Shared visual style")
    project_init.add_argument("--context", required=True, help="Shared project universe")
    project_init.add_argument("--palette", default="", help="Comma-separated colors")
    project_init.add_argument("--negative-prompt", default="")
    project_init.add_argument("--provider", default="openai")
    project_init.add_argument("--image-model", default="gpt-image-2")
    project_init.add_argument("--prompt-provider", default="openai")
    project_init.add_argument("--prompt-model", default="gpt-5.5")
    project_init.add_argument("--asset-type", default="tower")
    project_init.add_argument("--asset-type-context", default="")
    project_init.add_argument("--evolutions", type=int, default=4)
    project_init.add_argument("--evolution-context", default="")
    project_init.add_argument("--layout", default="single_sprite")

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
    elif args.command == "project":
        return cmd_project(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
