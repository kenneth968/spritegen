"""Core sprite sheet generator using AI image generation APIs.

Usage:
    from spritegen import SpriteGenerator, StyleManager, SpriteConfig

    style_mgr = StyleManager()
    style = style_mgr.load("my_style")
    config = SpriteConfig()

    generator = SpriteGenerator(style=style, config=config)
    sheet = generator.generate_sheet(
        name="my_sprites",
        sprites=[
            SpriteDefinition("sprite1", "a red mushroom"),
            SpriteDefinition("sprite2", "a blue mushroom"),
        ]
    )
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from .config import SpriteConfig, SpriteDefinition, SheetLayout
from .models import GeneratedSheet, SpriteMetadata
from .style import StylePreset, StyleManager


API_TIMEOUT_SECONDS = 120


class ImageGenerationError(Exception):
    pass


class SpriteGenerator:
    def __init__(
        self,
        style: StylePreset,
        config: SpriteConfig | None = None,
        style_manager: StyleManager | None = None,
    ) -> None:
        self.style = style
        self.config = config or SpriteConfig()
        self.style_manager = style_manager or StyleManager()

    def _call_image_api(
        self,
        prompt: str,
        negative_prompt: str,
        size: tuple[int, int],
        reference_images: list[Path | str] | None = None,
    ) -> bytes:
        provider = self.config.api_provider
        model = self.config.api_model

        if provider == "openai":
            return self._call_openai(prompt, negative_prompt, size, model)
        elif provider == "anthropic":
            return self._call_anthropic(prompt, negative_prompt, size)
        elif provider == "replicate":
            return self._call_replicate(prompt, negative_prompt, size, model)
        elif provider == "mock":
            return self._call_mock(prompt, size)
        elif provider == "huggingface":
            return self._call_huggingface(prompt, negative_prompt, size, model)
        elif provider == "pollinations":
            return self._call_pollinations(prompt, size)
        elif provider == "openrouter":
            return self._call_openrouter(
                prompt,
                negative_prompt,
                size,
                model,
                reference_images=reference_images,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _call_openai(
        self,
        prompt: str,
        negative_prompt: str,
        size: tuple[int, int],
        model: str,
    ) -> bytes:
        size_str = f"{size[0]}x{size[1]}"
        if model == "dall-e-3":
            size_str = "1024x1024"

        api_key = self.config.api_key or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ImageGenerationError("OPENAI_API_KEY is required for OpenAI image generation")

        full_prompt = prompt
        if negative_prompt:
            full_prompt = f"{prompt}\n\nAvoid: {negative_prompt}"

        payload = {
            "model": model,
            "prompt": full_prompt,
            "size": size_str,
            "n": 1,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/images/generations",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=API_TIMEOUT_SECONDS) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise ImageGenerationError(f"OpenAI image generation failed: {exc}") from exc

        try:
            return self._b64_to_png(result["data"][0]["b64_json"])
        except (KeyError, IndexError, TypeError) as exc:
            raise ImageGenerationError("OpenAI response did not include b64 image data") from exc

    def _call_mock(self, prompt: str, size: tuple[int, int]) -> bytes:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            raise ImageGenerationError(
                "PIL/Pillow is required for mock generation. Install with: pip install pillow"
            )

        width, height = size
        margin = 1
        inner_pad = 4

        # Parse grid layout from prompt (e.g. "3x3 grid") instead of hardcoding 2x2
        import re
        grid_match = re.search(r"(\d+)x(\d+)\s*grid", prompt)
        if grid_match:
            cols = int(grid_match.group(1))
            rows = int(grid_match.group(2))
        else:
            # Fallback: use config layout based on frame count in prompt
            frame_count = len(re.findall(r"Frame \d+:", prompt))
            layout = self.config.get_layout(max(frame_count, 1))
            rows = layout.rows
            cols = layout.columns

        cell_w = width // cols
        cell_h = height // rows
        sprite_count = rows * cols

        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except Exception:
            font = ImageFont.load_default()

        sprite_colors = [
            (255, 200, 200, 255),
            (200, 255, 200, 255),
            (200, 200, 255, 255),
            (255, 255, 200, 255),
            (255, 220, 180, 255),
            (180, 255, 220, 255),
            (220, 180, 255, 255),
            (255, 180, 220, 255),
            (180, 220, 255, 255),
            (220, 255, 180, 255),
            (255, 240, 200, 255),
            (200, 240, 255, 255),
            (240, 200, 255, 255),
            (200, 255, 240, 255),
            (255, 200, 240, 255),
            (240, 255, 200, 255),
        ]

        for idx in range(sprite_count):
            row = idx // cols
            col = idx % cols
            x = col * cell_w + margin
            y = row * cell_h + margin
            w = cell_w - margin * 2
            h = cell_h - margin * 2

            color = sprite_colors[idx % len(sprite_colors)]

            draw.rectangle([x, y, x + w, y + h], fill=(255, 255, 255, 255))
            inner_x = x + inner_pad
            inner_y = y + inner_pad
            inner_w = w - inner_pad * 2
            inner_h = h - inner_pad * 2
            draw.ellipse(
                [inner_x, inner_y, inner_x + inner_w, inner_y + inner_h],
                fill=color,
            )

            text = f"S{idx + 1}"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            text_x = x + (w - text_w) // 2
            text_y = y + (h - text_h) // 2
            draw.text((text_x, text_y), text, fill=(0, 0, 0, 255), font=font)

        import io

        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()

    def _call_huggingface(
        self,
        prompt: str,
        negative_prompt: str,
        size: tuple[int, int],
        model: str,
    ) -> bytes:
        import json

        prompt_json = json.dumps(prompt)
        neg_json = json.dumps(negative_prompt)

        script = f"""
import requests
import sys
import base64
from io import BytesIO

API_URL = "https://api-inference.huggingface.co/models/{model}"
headers = {{"Authorization": "Bearer " + (open(".hf_token").read().strip() if __import__("os").path.exists(".hf_token") else "")}}

payload = {{
    "inputs": {prompt_json},
    "negative_prompt": {neg_json},
}}

try:
    response = requests.post(API_URL, json=payload, timeout=120)
    if response.status_code == 200:
        b64 = base64.b64encode(response.content).decode()
        print(b64)
    else:
        print(f"ERROR:HTTP:" + str(response.status_code) + ":" + response.text[:200])
        sys.exit(1)
except Exception as e:
    print(f"ERROR:UNEXPECTED:" + type(e).__name__ + ":" + str(e)[:200])
    sys.exit(1)
"""
        result = self._run_python_script(script)
        if result.startswith("ERROR:"):
            raise ImageGenerationError(result)
        return self._b64_to_png(result)

    def _call_pollinations(
        self,
        prompt: str,
        size: tuple[int, int],
    ) -> bytes:
        import json

        prompt_json = json.dumps(prompt)
        w, h = size

        script = f"""
import urllib.request
import urllib.parse
import base64
import sys

prompt = {prompt_json}
# Truncate prompt to avoid URL length limits (Pollinations uses GET)
if len(prompt) > 800:
    prompt = prompt[:800]
encoded = urllib.parse.quote(prompt)
url = f"https://image.pollinations.ai/prompt/{{encoded}}?width={w}&height={h}&nologo=true&model=flux"

try:
    req = urllib.request.Request(url, headers={{"User-Agent": "spritegen/1.0"}})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    b64 = base64.b64encode(data).decode()
    print(b64)
except Exception as e:
    print(f"ERROR:UNEXPECTED:" + type(e).__name__ + ":" + str(e)[:200])
    sys.exit(1)
"""
        result = self._run_python_script(script)
        if result.startswith("ERROR:"):
            raise ImageGenerationError(result)
        return self._b64_to_png(result)

    def _call_openrouter(
        self,
        prompt: str,
        negative_prompt: str,
        size: tuple[int, int],
        model: str,
        reference_images: list[Path | str] | None = None,
    ) -> bytes:
        """Generate image via OpenRouter (Gemini Flash image generation)."""
        import json as _json

        image_config_json = _json.dumps(self._openrouter_image_config(size))
        reference_paths_json = _json.dumps([str(path) for path in reference_images or []])
        full_prompt = (
            f"Generate a game sprite image: {prompt}. "
            f"Avoid: {negative_prompt}. "
            f"The image should be {size[0]}x{size[1]} pixels, "
            f"centered on white background, single sprite."
        )
        prompt_json = _json.dumps(full_prompt)
        model_json = _json.dumps(model)

        script = f"""
import urllib.request
import json
import base64
import sys
import os

reference_image_paths = {reference_paths_json}

api_key = (
    os.environ.get("SPRITEGEN_SESSION_API_KEY", "")
    or os.environ.get("OPENROUTER_API_KEY", "")
    or os.environ.get("OPENAI_API_KEY", "")
)
if not api_key:
    print("ERROR:AUTH:No OPENROUTER_API_KEY or OPENAI_API_KEY found in environment")
    sys.exit(1)

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {{
    "Authorization": f"Bearer {{api_key}}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/spritegen",
}}

content = [{{"type": "text", "text": {prompt_json}}}]
for reference_path in reference_image_paths:
    try:
        with open(reference_path, "rb") as reference_file:
            reference_b64 = base64.b64encode(reference_file.read()).decode()
    except OSError:
        continue
    content.append({{
        "type": "image_url",
        "image_url": {{"url": "data:image/png;base64," + reference_b64}},
    }})

payload = json.dumps({{
    "model": {model_json},
    "messages": [
        {{
            "role": "user",
            "content": content if reference_image_paths else {prompt_json}
        }}
    ],
    "modalities": ["image", "text"],
    "image_config": {image_config_json},
}}).encode()

try:
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode())

    # Extract image from response
    msg = result.get("choices", [{{}}])[0].get("message", {{}})

    # Gemini returns images in msg.images array
    images = msg.get("images", [])
    if images:
        for img_part in images:
            if isinstance(img_part, dict):
                img_url = img_part.get("image_url", {{}}).get("url", "")
                if img_url.startswith("data:"):
                    b64 = img_url.split(",", 1)[1]
                    print(b64)
                    sys.exit(0)

    # Fallback: check content for image parts
    content = msg.get("content", "")
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                img_url = part.get("image_url", {{}}).get("url", "")
                if img_url.startswith("data:"):
                    b64 = img_url.split(",", 1)[1]
                    print(b64)
                    sys.exit(0)

    print("ERROR:NOIMAGE:No image found in OpenRouter response: " + json.dumps(result)[:300])
    sys.exit(1)

except Exception as e:
    print(f"ERROR:UNEXPECTED:" + type(e).__name__ + ":" + str(e)[:200])
    sys.exit(1)
"""
        env = (
            {"SPRITEGEN_SESSION_API_KEY": self.config.api_key}
            if self.config.api_key
            else None
        )
        result = self._run_python_script(script, env=env)
        if result.startswith("ERROR:"):
            raise ImageGenerationError(result)
        return self._b64_to_png(result)

    def _openrouter_image_config(self, size: tuple[int, int]) -> dict[str, str]:
        width, height = size
        return {
            "aspect_ratio": self._aspect_ratio(width, height),
            "image_size": self._openrouter_image_size(width, height),
        }

    def _aspect_ratio(self, width: int, height: int) -> str:
        supported = {
            "1:1": 1 / 1,
            "2:3": 2 / 3,
            "3:2": 3 / 2,
            "3:4": 3 / 4,
            "4:3": 4 / 3,
            "4:5": 4 / 5,
            "5:4": 5 / 4,
            "9:16": 9 / 16,
            "16:9": 16 / 9,
            "21:9": 21 / 9,
        }
        target = width / height
        return min(supported, key=lambda ratio: abs(supported[ratio] - target))

    def _openrouter_image_size(self, width: int, height: int) -> str:
        longest_edge = max(width, height)
        if longest_edge <= 1024:
            return "1K"
        if longest_edge <= 2048:
            return "2K"
        return "4K"

    def _call_anthropic(
        self,
        prompt: str,
        negative_prompt: str,
        size: tuple[int, int],
    ) -> bytes:
        raise ImageGenerationError("Anthropic image generation not yet implemented")

    def _call_replicate(
        self,
        prompt: str,
        negative_prompt: str,
        size: tuple[int, int],
        model: str,
    ) -> bytes:
        raise ImageGenerationError("Replicate image generation not yet implemented")

    def _run_python_script(self, script: str, env: dict[str, str] | None = None) -> str:
        try:
            run_env = None
            if env:
                run_env = os.environ.copy()
                run_env.update(env)
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                timeout=API_TIMEOUT_SECONDS,
                env=run_env,
            )
            if result.returncode != 0:
                error_msg = (
                    result.stdout.strip()
                    if result.stdout.strip()
                    else result.stderr.strip()
                )
                return f"ERROR: {error_msg[:500]}"
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return f"ERROR: Timeout after {API_TIMEOUT_SECONDS}s"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _b64_to_png(self, b64_data: str) -> bytes:
        import base64

        return base64.b64decode(b64_data)

    def generate_sheet(
        self,
        name: str,
        sprites: list[SpriteDefinition],
    ) -> GeneratedSheet:
        layout = self.config.get_layout(len(sprites))

        negative_prompt = self.style_manager.build_negative_prompt(self.style)

        sprite_prompts = []
        for sprite in sprites:
            full_prompt = self.style_manager.build_prompt(
                self.style,
                sprite.prompt,
            )
            sprite_prompts.append(full_prompt)

        combined_prompt = " | ".join(
            [f"Frame {i + 1}: {p}" for i, p in enumerate(sprite_prompts)]
        )

        combined_prompt += f" | sheet layout: {layout.columns}x{layout.rows} grid"

        image_data = self._call_image_api(
            combined_prompt,
            negative_prompt,
            (self.config.sheet_width, self.config.sheet_height),
        )

        sprite_metadata = []
        for i, sprite_def in enumerate(sprites):
            row = i // layout.columns
            col = i % layout.columns
            x = col * layout.cell_width + layout.margin
            y = row * layout.cell_height + layout.margin

            sprite_metadata.append(
                SpriteMetadata(
                    name=sprite_def.name,
                    sprite_index=i,
                    position=(x, y),
                    size=(
                        layout.cell_width - layout.padding,
                        layout.cell_height - layout.padding,
                    ),
                    prompt=sprite_def.prompt,
                    style_seed=self.style.seed,
                )
            )

        self.style_manager.record_generation(self.style.name)

        return GeneratedSheet(
            image_data=image_data,
            layout=layout,
            sprites=sprite_metadata,
            style_seed=self.style.seed,
            generation_params={
                "provider": self.config.api_provider,
                "model": self.config.api_model,
                "sheet_size": (self.config.sheet_width, self.config.sheet_height),
            },
        )

    def generate_single_sprite(
        self,
        name: str,
        prompt: str,
        width: int | None = None,
        height: int | None = None,
    ) -> GeneratedSheet:
        """Generate a single sprite image (one API call, no grid splitting).

        Ideal for evolution chains where each stage should be one coherent image
        that visually evolves from the previous stage (like Bloons TD upgrades).
        """
        w = width or self.config.sprite_width or 512
        h = height or self.config.sprite_height or 512

        full_prompt = self.style_manager.build_prompt(self.style, prompt)
        negative_prompt = self.style_manager.build_negative_prompt(self.style)

        image_data = self._call_image_api(
            full_prompt,
            negative_prompt,
            (w, h),
        )

        # Detect actual image size (API may return different dimensions)
        try:
            from PIL import Image
            actual_img = Image.open(io.BytesIO(image_data))
            actual_w, actual_h = actual_img.size
        except Exception:
            actual_w, actual_h = w, h

        # Single sprite occupies the entire image
        sprite_meta = SpriteMetadata(
            name=name,
            sprite_index=0,
            position=(0, 0),
            size=(actual_w, actual_h),
            prompt=prompt,
            style_seed=self.style.seed,
        )

        self.style_manager.record_generation(self.style.name)

        return GeneratedSheet(
            image_data=image_data,
            layout=SheetLayout(rows=1, columns=1, cell_width=actual_w, cell_height=actual_h),
            sprites=[sprite_meta],
            style_seed=self.style.seed,
            generation_params={
                "provider": self.config.api_provider,
                "model": self.config.api_model,
                "sheet_size": (w, h),
            },
        )

    def generate_raw_image(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        reference_images: list[Path | str] | None = None,
    ) -> bytes:
        """Generate one image without adding style-manager prompt text."""
        return self._call_image_api(
            prompt,
            negative_prompt,
            (width, height),
            reference_images=reference_images,
        )

    def generate_evolution_chain(
        self,
        chain_name: str,
        species: str,
        stages: list[dict[str, str]],
    ) -> list[GeneratedSheet]:
        """Generate an evolution chain — one sprite per stage.

        Each stage produces a single coherent sprite image that visually
        evolves from the previous stage, maintaining character identity
        across upgrade levels (like tower upgrades in Bloons TD).
        """
        sheets = []
        for i, stage in enumerate(stages):
            stage_name = stage.get("name", f"stage{i + 1}")
            stage_prompt = stage["prompt"]

            # Keep prompts concise for URL-based APIs like Pollinations
            if i > 0:
                stage_prompt = (
                    f"same {species} character upgraded: {stage_prompt}, "
                    f"single centered sprite, consistent style"
                )
            else:
                stage_prompt = (
                    f"{stage_prompt}, single centered {species} sprite, base form"
                )

            sheet = self.generate_single_sprite(
                name=f"{chain_name}_{stage_name}",
                prompt=stage_prompt,
            )
            sheets.append(sheet)
        return sheets


def create_mycomed_style(manager: StyleManager) -> StylePreset:
    return manager.create_style(
        name="mycomed_towers",
        base_prompt="""tower defense game sprite, mushroom tower character,
            Bloons TD art style, clean bold outlines, bright saturated colors,
            cartoony, vector-like, smooth shading, white background,
            single centered character, fun and expressive""",
        negative_prompt="""pixel art, pixelated, blurry, low quality, distorted,
            photographic, realistic, photorealistic, 3D render, watermark,
            signature, text, letters, numbers, UI elements, dark background,
            black background, gritty, horror, multiple characters""",
        color_palette=[
            "#8B4513",
            "#228B22",
            "#9932CC",
            "#00FA9A",
            "#FF6B6B",
            "#4ECDC4",
            "#45B7D1",
            "#96CEB4",
        ],
        visual_tags=[
            "mushroom",
            "fungal",
            "tower-defense",
            "game-sprite",
            "bioluminescent",
            "organic",
            "fantasy",
        ],
    )
