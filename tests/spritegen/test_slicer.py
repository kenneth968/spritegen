"""Tests for the Slicer module."""

import pytest
from io import BytesIO
from spritegen.config import SpriteConfig, SheetLayout
from spritegen.models import GeneratedSheet, SpriteMetadata
from spritegen.slicer import Slicer, SlicerError


class TestSlicerUnit:
    def test_slicer_requires_pil(self):
        slicer = Slicer(output_dir="test_output")
        assert slicer is not None


class TestSlicerEndToEnd:
    def _create_fake_sheet(self, rows=2, cols=2, cell_width=64, cell_height=64):
        """Create a fake sprite sheet image with distinct colored cells on white."""
        from PIL import Image

        padding = 0
        margin = 1
        sheet_w = cols * cell_width + 2 * margin
        sheet_h = rows * cell_height + 2 * margin

        img = Image.new("RGBA", (sheet_w, sheet_h), (255, 255, 255, 255))

        colors = [
            (255, 0, 0, 255),
            (0, 255, 0, 255),
            (0, 0, 255, 255),
            (255, 255, 0, 255),
        ]

        for idx in range(min(rows * cols, len(colors))):
            row = idx // cols
            col = idx % cols
            x = col * cell_width + margin
            y = row * cell_height + margin

            inner_pad = 4
            for py in range(inner_pad, cell_height - inner_pad):
                for px in range(inner_pad, cell_width - inner_pad):
                    img.putpixel((x + px, y + py), colors[idx])

        buf = BytesIO()
        img.save(buf, format="PNG")
        image_data = buf.getvalue()

        layout = SheetLayout(
            rows=rows,
            columns=cols,
            cell_width=cell_width,
            cell_height=cell_height,
            margin=margin,
            padding=padding,
        )

        sprites = []
        for idx in range(layout.sprite_count):
            row = idx // cols
            col = idx % cols
            x = col * cell_width + margin
            y = row * cell_height + margin
            sprites.append(
                SpriteMetadata(
                    name=f"sprite_{idx}",
                    sprite_index=idx,
                    position=(x, y),
                    size=(cell_width, cell_height),
                    prompt=f"test sprite {idx}",
                )
            )

        return GeneratedSheet(
            image_data=image_data,
            layout=layout,
            sprites=sprites,
            style_seed="test_seed",
            generation_params={},
        )

    def test_slice_and_save(self, tmp_path):
        """Test slicing a sheet into individual sprites."""
        sheet = self._create_fake_sheet()
        output_dir = tmp_path / "sprites"
        slicer = Slicer(output_dir=output_dir)

        paths = slicer.slice_and_save(sheet)

        assert len(paths) == 4
        assert all(p.suffix == ".png" for p in paths)
        for p in paths:
            assert p.exists()
            assert p.stat().st_size > 0

    def test_extract_sprite(self, tmp_path):
        """Test extracting a single sprite."""
        sheet = self._create_fake_sheet()
        slicer = Slicer(output_dir=tmp_path)

        sprite = slicer.extract_sprite(sheet, index=0)

        assert sprite is not None
        assert sprite.size == (64, 64)

    def test_slice_to_grid(self, tmp_path):
        """Test slicing to a grid of images."""
        sheet = self._create_fake_sheet(rows=2, cols=2)
        slicer = Slicer(output_dir=tmp_path)

        sprites = slicer.slice_to_grid(sheet)

        assert len(sprites) == 4
        assert all(s.size == (64, 64) for s in sprites)

    def test_transparent_bg_removes_white(self, tmp_path):
        """Test that white background becomes transparent."""
        sheet = self._create_fake_sheet()
        config = SpriteConfig(transparent_bg=True)
        slicer = Slicer(output_dir=tmp_path, config=config)

        sprite = slicer.extract_sprite(sheet, index=0)

        assert sprite is not None
        corners = [
            (0, 0),
            (sprite.size[0] - 1, 0),
            (0, sprite.size[1] - 1),
            (sprite.size[0] - 1, sprite.size[1] - 1),
        ]
        for x, y in corners:
            r, g, b, a = sprite.getpixel((x, y))
            assert a == 0, f"Corner ({x},{y}) should be transparent but got alpha={a}"

    def test_save_metadata(self, tmp_path):
        """Test saving sprite metadata."""
        sheet = self._create_fake_sheet()
        slicer = Slicer(output_dir=tmp_path)

        path = slicer.save_metadata(sheet)

        assert path.exists()
        import json

        data = json.loads(path.read_text())
        assert "sprites" in data
        assert len(data["sprites"]) == 4

    def test_slicer_error_when_pil_missing(self, monkeypatch):
        """Test that proper error is raised when PIL is not available."""
        import spritegen.slicer as slicer_module

        monkeypatch.setattr(slicer_module, "HAS_PIL", False)

        from spritegen.slicer import Slicer

        s = Slicer(output_dir="test")

        with pytest.raises(SlicerError, match="PIL"):
            s.extract_sprite(self._create_fake_sheet(), 0)
