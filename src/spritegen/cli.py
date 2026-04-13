"""CLI entry point for sprite generation pipeline.

Usage:
    python -m spritegen.cli generate --style mycomed_towers --sprites puffball_1 puffball_2 puffball_3 puffball_4
    python -m spritegen.cli slice --sheet output/sheets/spritesheet.png --output output/sprites
    python -m spritegen.cli style create --name my_style --base-prompt "pixel art, 64x64"
"""

import argparse
import sys
from pathlib import Path

from . import (
    SpriteConfig,
    SpriteDefinition,
    SpriteGenerator,
    StyleManager,
    Slicer,
    create_mycomed_style,
)
from .mycomed import EVOLUTION_STAGES, get_evolution_chain


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
    from .config import SheetLayout

    layout = config.get_layout(args.count or 4)
    sheet = GeneratedSheet(
        image_data=sheet_data,
        layout=layout,
        sprites=[],
        style_seed="unknown",
        generation_params={},
    )

    for i in range(len(sheet.sprites)):
        path = slicer.save_sprite(sheet, i)
        print(f"Saved: {path}")

    return 0


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
    slicer = Slicer(output_dir=config.output_dir, config=config)

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
    style_list = style_subparsers.add_parser("list", help="List styles")
    style_info = style_subparsers.add_parser("info", help="Show style info")
    style_info.add_argument("--name", required=True)

    args = parser.parse_args()

    if args.command == "generate":
        return cmd_generate(args)
    elif args.command == "slice":
        return cmd_slice(args)
    elif args.command == "evolution-chain":
        return cmd_evolution_chain(args)
    elif args.command == "style":
        return cmd_style(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
