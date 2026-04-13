"""Style consistency analysis for sprite sheet generations.

Provides metrics to quantify how visually consistent sprite sheets are
across multiple generations. Used to validate that style presets produce
coherent outputs when applied repeatedly.

Usage:
    from spritegen.consistency import StyleConsistencyAnalyzer

    analyzer = StyleConsistencyAnalyzer()
    report = analyzer.analyze([path1, path2, path3])
    print(report.summary())
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SheetMetrics:
    """Metrics extracted from a single sprite sheet."""

    path: str
    width: int
    height: int
    mode: str
    dominant_colors: list[tuple[int, int, int]]
    color_histogram: list[float]
    mean_brightness: float
    mean_saturation: float
    transparency_ratio: float


@dataclass
class ConsistencyReport:
    """Results of style consistency analysis across multiple sheets."""

    sheet_count: int
    sheet_paths: list[str]
    dimension_consistent: bool
    dimension_details: dict[str, Any]
    color_consistency_score: float
    brightness_consistency_score: float
    saturation_consistency_score: float
    palette_adherence_scores: list[float]
    mean_palette_adherence: float
    pairwise_color_similarities: list[dict[str, Any]]
    overall_consistency_score: float
    pass_threshold: float
    passed: bool
    warnings: list[str]
    per_sheet_metrics: list[dict[str, Any]]

    def summary(self) -> str:
        lines = [
            f"Style Consistency Report",
            f"========================",
            f"Sheets analyzed: {self.sheet_count}",
            f"Dimension consistent: {self.dimension_consistent}",
            f"",
            f"Scores (0.0 = inconsistent, 1.0 = perfectly consistent):",
            f"  Color consistency:      {self.color_consistency_score:.3f}",
            f"  Brightness consistency: {self.brightness_consistency_score:.3f}",
            f"  Saturation consistency: {self.saturation_consistency_score:.3f}",
            f"  Palette adherence:      {self.mean_palette_adherence:.3f}",
            f"",
            f"Overall score: {self.overall_consistency_score:.3f}",
            f"Pass threshold: {self.pass_threshold:.3f}",
            f"Result: {'PASS' if self.passed else 'FAIL'}",
        ]
        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  - {w}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sheet_count": self.sheet_count,
            "sheet_paths": self.sheet_paths,
            "dimension_consistent": self.dimension_consistent,
            "dimension_details": self.dimension_details,
            "color_consistency_score": self.color_consistency_score,
            "brightness_consistency_score": self.brightness_consistency_score,
            "saturation_consistency_score": self.saturation_consistency_score,
            "palette_adherence_scores": self.palette_adherence_scores,
            "mean_palette_adherence": self.mean_palette_adherence,
            "pairwise_color_similarities": self.pairwise_color_similarities,
            "overall_consistency_score": self.overall_consistency_score,
            "pass_threshold": self.pass_threshold,
            "passed": self.passed,
            "warnings": self.warnings,
            "per_sheet_metrics": self.per_sheet_metrics,
        }


def _rgb_to_hsv(r: float, g: float, b: float) -> tuple[float, float, float]:
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    cmax = max(r, g, b)
    cmin = min(r, g, b)
    delta = cmax - cmin

    if delta == 0:
        h = 0.0
    elif cmax == r:
        h = 60 * (((g - b) / delta) % 6)
    elif cmax == g:
        h = 60 * (((b - r) / delta) + 2)
    else:
        h = 60 * (((r - g) / delta) + 4)

    s = 0.0 if cmax == 0 else delta / cmax
    v = cmax
    return h, s, v


def _color_distance(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


def _histogram_similarity(h1: list[float], h2: list[float]) -> float:
    if len(h1) != len(h2):
        return 0.0
    dot = sum(a * b for a, b in zip(h1, h2))
    mag1 = math.sqrt(sum(a * a for a in h1))
    mag2 = math.sqrt(sum(b * b for b in h2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


def _extract_metrics(path: Path) -> SheetMetrics:
    from PIL import Image

    img = Image.open(path).convert("RGBA")
    width, height = img.size

    pixels = list(img.getdata())

    opaque = [(r, g, b) for r, g, b, a in pixels if a > 128]
    transparent_count = sum(1 for _, _, _, a in pixels if a <= 128)
    transparency_ratio = transparent_count / max(len(pixels), 1)

    if not opaque:
        return SheetMetrics(
            path=str(path),
            width=width,
            height=height,
            mode="RGBA",
            dominant_colors=[],
            color_histogram=[0.0] * 256,
            mean_brightness=0.0,
            mean_saturation=0.0,
            transparency_ratio=1.0,
        )

    brightness_values = []
    saturation_values = []
    for r, g, b in opaque:
        _, s, v = _rgb_to_hsv(r, g, b)
        brightness_values.append(v)
        saturation_values.append(s)

    mean_brightness = sum(brightness_values) / len(brightness_values)
    mean_saturation = sum(saturation_values) / len(saturation_values)

    histogram = [0] * 256
    for r, g, b in opaque:
        gray = int(0.299 * r + 0.587 * g + 0.114 * b)
        histogram[gray] += 1
    total = sum(histogram)
    normalized_histogram = [v / max(total, 1) for v in histogram]

    quantize_img = img.convert("RGB").quantize(colors=8)
    palette = quantize_img.getpalette()
    dominant_colors: list[tuple[int, int, int]] = []
    if palette:
        for i in range(8):
            r, g, b = palette[i * 3], palette[i * 3 + 1], palette[i * 3 + 2]
            dominant_colors.append((r, g, b))

    return SheetMetrics(
        path=str(path),
        width=width,
        height=height,
        mode="RGBA",
        dominant_colors=dominant_colors,
        color_histogram=normalized_histogram,
        mean_brightness=mean_brightness,
        mean_saturation=mean_saturation,
        transparency_ratio=transparency_ratio,
    )


def _palette_adherence(
    sheet_colors: list[tuple[int, int, int]],
    style_palette: list[str],
) -> float:
    if not style_palette or not sheet_colors:
        return 1.0

    palette_rgb: list[tuple[int, int, int]] = []
    for hex_color in style_palette:
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        palette_rgb.append((r, g, b))

    total_min_dist = 0.0
    max_possible_dist = math.sqrt(3 * 255**2)
    for sc in sheet_colors:
        min_dist = min(_color_distance(sc, pc) for pc in palette_rgb)
        total_min_dist += min_dist

    mean_min_dist = total_min_dist / len(sheet_colors)
    adherence = 1.0 - (mean_min_dist / max_possible_dist)
    return max(0.0, min(1.0, adherence))


class StyleConsistencyAnalyzer:
    """Analyzes style consistency across multiple sprite sheet images."""

    def __init__(self, pass_threshold: float = 0.6) -> None:
        self.pass_threshold = pass_threshold

    def analyze(
        self,
        sheet_paths: list[Path],
        style_palette: list[str] | None = None,
    ) -> ConsistencyReport:
        if len(sheet_paths) < 2:
            raise ValueError("Need at least 2 sprite sheets to analyze consistency")

        warnings: list[str] = []
        all_metrics: list[SheetMetrics] = []

        for p in sheet_paths:
            if not p.exists():
                warnings.append(f"Sheet not found: {p}")
                continue
            try:
                metrics = _extract_metrics(p)
                all_metrics.append(metrics)
            except Exception as e:
                warnings.append(f"Failed to load {p}: {e}")

        if len(all_metrics) < 2:
            return ConsistencyReport(
                sheet_count=len(all_metrics),
                sheet_paths=[str(p) for p in sheet_paths],
                dimension_consistent=False,
                dimension_details={},
                color_consistency_score=0.0,
                brightness_consistency_score=0.0,
                saturation_consistency_score=0.0,
                palette_adherence_scores=[],
                mean_palette_adherence=0.0,
                pairwise_color_similarities=[],
                overall_consistency_score=0.0,
                pass_threshold=self.pass_threshold,
                passed=False,
                warnings=warnings + ["Insufficient sheets loaded for analysis"],
                per_sheet_metrics=[],
            )

        dims = [(m.width, m.height) for m in all_metrics]
        dimension_consistent = len(set(dims)) == 1
        if not dimension_consistent:
            warnings.append(f"Dimension mismatch: {set(dims)}")

        dim_details: dict[str, Any] = {
            "all_dimensions": [(m.width, m.height) for m in all_metrics],
            "consistent": dimension_consistent,
        }

        pairwise_sims: list[dict[str, Any]] = []
        color_sim_values: list[float] = []
        for i in range(len(all_metrics)):
            for j in range(i + 1, len(all_metrics)):
                sim = _histogram_similarity(
                    all_metrics[i].color_histogram,
                    all_metrics[j].color_histogram,
                )
                pairwise_sims.append(
                    {
                        "sheet_a": all_metrics[i].path,
                        "sheet_b": all_metrics[j].path,
                        "color_histogram_similarity": sim,
                    }
                )
                color_sim_values.append(sim)

        color_consistency = sum(color_sim_values) / max(len(color_sim_values), 1)

        brightness_values = [m.mean_brightness for m in all_metrics]
        brightness_mean = sum(brightness_values) / len(brightness_values)
        brightness_variance = sum(
            (v - brightness_mean) ** 2 for v in brightness_values
        ) / len(brightness_values)
        brightness_std = math.sqrt(brightness_variance)
        brightness_consistency = max(0.0, 1.0 - brightness_std * 2)

        saturation_values = [m.mean_saturation for m in all_metrics]
        saturation_mean = sum(saturation_values) / len(saturation_values)
        saturation_variance = sum(
            (v - saturation_mean) ** 2 for v in saturation_values
        ) / len(saturation_values)
        saturation_std = math.sqrt(saturation_variance)
        saturation_consistency = max(0.0, 1.0 - saturation_std * 2)

        palette_adherence_scores: list[float] = []
        if style_palette:
            for m in all_metrics:
                score = _palette_adherence(m.dominant_colors, style_palette)
                palette_adherence_scores.append(score)
        else:
            palette_adherence_scores = [1.0] * len(all_metrics)

        mean_palette_adherence = sum(palette_adherence_scores) / max(
            len(palette_adherence_scores), 1
        )

        weights = {
            "color": 0.20,
            "brightness": 0.30,
            "saturation": 0.30,
            "palette": 0.20,
        }
        overall = (
            weights["color"] * color_consistency
            + weights["brightness"] * brightness_consistency
            + weights["saturation"] * saturation_consistency
            + weights["palette"] * mean_palette_adherence
        )

        per_sheet: list[dict[str, Any]] = [
            {
                "path": m.path,
                "width": m.width,
                "height": m.height,
                "mean_brightness": m.mean_brightness,
                "mean_saturation": m.mean_saturation,
                "transparency_ratio": m.transparency_ratio,
                "dominant_colors": [list(c) for c in m.dominant_colors],
            }
            for m in all_metrics
        ]

        return ConsistencyReport(
            sheet_count=len(all_metrics),
            sheet_paths=[str(p) for p in sheet_paths],
            dimension_consistent=dimension_consistent,
            dimension_details=dim_details,
            color_consistency_score=color_consistency,
            brightness_consistency_score=brightness_consistency,
            saturation_consistency_score=saturation_consistency,
            palette_adherence_scores=palette_adherence_scores,
            mean_palette_adherence=mean_palette_adherence,
            pairwise_color_similarities=pairwise_sims,
            overall_consistency_score=overall,
            pass_threshold=self.pass_threshold,
            passed=overall >= self.pass_threshold,
            warnings=warnings,
            per_sheet_metrics=per_sheet,
        )
