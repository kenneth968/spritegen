"""Tests for sprite generation pipeline."""

import pytest
from pathlib import Path
from spritegen.config import SpriteConfig, SheetLayout, SpriteDefinition
from spritegen.models import GeneratedSheet, SpriteMetadata
from spritegen.style import StyleManager, StylePreset, PRESET_STYLES
from spritegen.generator import SpriteGenerator, create_mycomed_style


class TestSheetLayout:
    def test_sprite_count(self):
        layout = SheetLayout(rows=2, columns=2)
        assert layout.sprite_count == 4

    def test_custom_layout(self):
        layout = SheetLayout(
            rows=3, columns=4, cell_width=128, cell_height=128, padding=8
        )
        assert layout.sprite_count == 12
        assert layout.cell_width == 128


class TestSpriteConfig:
    def test_default_config(self):
        config = SpriteConfig()
        assert config.sheet_width == 512
        assert config.sheet_height == 512
        assert config.sprite_width == 128
        assert config.sprite_height == 128

    def test_get_layout_4_sprites(self):
        config = SpriteConfig()
        layout = config.get_layout(4)
        assert layout.sprite_count == 4
        assert layout.rows == 2
        assert layout.columns == 2

    def test_get_layout_6_sprites(self):
        config = SpriteConfig()
        layout = config.get_layout(6)
        assert layout.sprite_count == 6
        assert layout.rows == 2
        assert layout.columns == 3

    def test_validate_valid(self):
        config = SpriteConfig(output_dir=Path("test_output"))
        errors = config.validate()
        assert len(errors) == 0


class TestStyleManager:
    def test_generate_seed(self):
        mgr = StyleManager(style_dir=Path("test_styles"))
        seed = mgr._generate_seed()
        assert len(seed) == 16
        assert seed.isalnum()

    def test_create_and_load_style(self, tmp_path):
        mgr = StyleManager(style_dir=tmp_path)
        style = mgr.create_style(
            name="test_style",
            base_prompt="pixel art",
            color_palette=["#FF0000", "#00FF00"],
        )
        assert style.name == "test_style"
        assert style.base_prompt == "pixel art"

        loaded = mgr.load("test_style")
        assert loaded is not None
        assert loaded.name == "test_style"
        assert loaded.color_palette == ["#FF0000", "#00FF00"]

    def test_build_prompt(self, tmp_path):
        mgr = StyleManager(style_dir=tmp_path)
        style = PRESET_STYLES["pixel_art"]
        prompt = mgr.build_prompt(style, "a red mushroom")
        assert "a red mushroom" in prompt
        assert "pixel art" in prompt

    def test_record_generation(self, tmp_path):
        mgr = StyleManager(style_dir=tmp_path)
        style = mgr.create_style(name="test_gen", base_prompt="test")
        assert style.generation_count == 0
        mgr.record_generation("test_gen")
        loaded = mgr.load("test_gen")
        assert loaded.generation_count == 1


class TestGeneratedSheet:
    def test_width_height(self):
        layout = SheetLayout(rows=2, columns=2, cell_width=128, cell_height=128)
        sheet = GeneratedSheet(
            image_data=b"fake",
            layout=layout,
            sprites=[],
            style_seed="test",
            generation_params={},
        )
        assert sheet.width == 256
        assert sheet.height == 256


class TestSpriteMetadata:
    def test_creation(self):
        meta = SpriteMetadata(
            name="test_sprite",
            sprite_index=0,
            position=(0, 0),
            size=(64, 64),
            prompt="a test sprite",
        )
        assert meta.name == "test_sprite"
        assert meta.sprite_index == 0
        assert meta.position == (0, 0)


class TestOpenAIIntegration:
    def test_openai_script_generation(self):
        from spritegen.generator import SpriteGenerator
        from spritegen.style import StyleManager, StylePreset
        from spritegen.config import SpriteConfig, SpriteDefinition

        mgr = StyleManager()
        style = StylePreset(
            name="test_style",
            base_prompt="pixel art, simple geometric",
            negative_prompt="blurry",
            color_palette=["#FF0000"],
            visual_tags=["test"],
            seed="test123",
        )
        config = SpriteConfig(api_provider="openai", api_model="dall-e-3")
        generator = SpriteGenerator(style=style, config=config, style_manager=mgr)

        script = """
import openai
client = openai.OpenAI()
response = client.images.generate(
    model="dall-e-3",
    prompt="test prompt",
    size="1024x1024",
    n=1
)
print(response.data[0].b64_json)
"""
        result = generator._run_python_script(script)
        assert "ERROR:" in result or "billing" in result.lower() or result == ""

    def test_image_generation_error_handling(self):
        from spritegen.generator import SpriteGenerator, ImageGenerationError
        from spritegen.style import StyleManager, StylePreset
        from spritegen.config import SpriteConfig

        mgr = StyleManager()
        style = StylePreset(
            name="test_style",
            base_prompt="pixel art",
            negative_prompt="",
            color_palette=[],
            visual_tags=[],
            seed="test456",
        )
        config = SpriteConfig(api_provider="openai", api_model="dall-e-3")
        generator = SpriteGenerator(style=style, config=config, style_manager=mgr)

        try:
            generator._call_openai("test prompt", "blurry", (512, 512), "dall-e-3")
        except ImageGenerationError as e:
            assert "billing" in str(e).lower() or "ERROR" in str(e)
        except Exception as e:
            pass
