"""Generate tower sprites using pollinations.ai (free, no API key required).

Usage:
    python generate_pollinations.py --tower puffball
    python generate_pollinations.py --tower puffball --stages 1 2  (only stages 1 and 2)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from spritegen import (
    SpriteConfig,
    SpriteGenerator,
    StyleManager,
    Slicer,
    create_mycomed_style,
)
from spritegen.mycomed import EVOLUTION_STAGES


def main():
    parser = argparse.ArgumentParser(
        description="Generate sprites via pollinations.ai (free, no auth)"
    )
    parser.add_argument(
        "--tower",
        required=True,
        choices=["puffball", "cordyceps", "amanita", "slime_enemy"],
    )
    parser.add_argument("--output-dir", default="output/sprites/pollinations")
    parser.add_argument("--sheet-dir", default="output/sheets/pollinations")
    parser.add_argument(
        "--stages", nargs="*", type=int, help="Which stages to generate (1-4)"
    )
    args = parser.parse_args()

    config = SpriteConfig(
        output_dir=Path(args.output_dir),
        sheet_dir=Path(args.sheet_dir),
        api_provider="pollinations",
        sheet_width=512,
        sheet_height=512,
    )

    style_mgr = StyleManager()
    style = style_mgr.load("mycomed_towers") or create_mycomed_style(style_mgr)

    generator = SpriteGenerator(style=style, config=config, style_manager=style_mgr)

    stages = EVOLUTION_STAGES[args.tower]
    selected = args.stages or list(range(1, len(stages) + 1))

    print(f"Generating {args.tower} via pollinations.ai (stages: {selected})...")
    print("Mode: one sprite per evolution stage (Bloons TD style upgrades)")

    for stage_idx, stage in enumerate(stages):
        stage_num = stage_idx + 1
        if stage_num not in selected:
            continue

        stage_name = stage["name"]
        stage_prompt = stage["prompt"]

        print(f"\n--- Stage {stage_num}/{len(stages)}: {stage_name} ---")
        print(f"Prompt: {stage_prompt[:80]}...")

        # Keep prompts concise — Pollinations has URL length limits
        if stage_idx > 0:
            full_prompt = (
                f"same {args.tower} character upgraded: {stage_prompt}, "
                f"single centered sprite, consistent style"
            )
        else:
            full_prompt = (
                f"{stage_prompt}, single centered {args.tower} sprite, base form"
            )

        try:
            sheet = generator.generate_single_sprite(
                name=f"{args.tower}_lvl{stage_num}",
                prompt=full_prompt,
            )

            # Save the raw image
            sprite_path = config.output_dir / f"{args.tower}_lvl{stage_num}.png"
            sprite_path.parent.mkdir(parents=True, exist_ok=True)
            sprite_path.write_bytes(sheet.image_data)
            size = sprite_path.stat().st_size
            print(f"  Raw sprite: {sprite_path} ({size:,} bytes)")

            # Save with background removed
            stage_slicer = Slicer(output_dir=config.output_dir, config=config)
            transparent_path = stage_slicer.save_sprite(sheet, 0)
            print(f"  Transparent: {transparent_path.name}")

        except Exception as e:
            print(f"  Error generating stage {stage_num}: {e}")
            continue

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
