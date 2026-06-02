"""Preflight checks for project asset generation runs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .provider_models import (
    IMAGE_ROLE,
    MODEL_VALIDATION_ERROR,
    MODEL_VALIDATION_WARNING,
    PROMPT_ROLE,
    ModelSuggestion,
    validate_model_choice,
)
from .projects import AssetSpec, ProjectSpec, PromptPlanner


PREFLIGHT_OK = "ready"
PREFLIGHT_WARNING = "warnings"
PREFLIGHT_ERROR = "errors"

PREFLIGHT_ISSUE_ERROR = "error"
PREFLIGHT_ISSUE_WARNING = "warning"

KEYED_PROVIDERS = {"openai", "openrouter"}


@dataclass(frozen=True)
class PreflightIssue:
    level: str
    message: str
    code: str = ""


@dataclass(frozen=True)
class ReferenceAssetSummary:
    name: str
    slug: str
    asset_type: str
    prompt: str
    details: str = ""
    layout: str = ""


@dataclass
class GenerationPreflightReport:
    project_name: str
    asset_name: str
    image_provider: str
    image_model: str
    prompt_provider: str
    prompt_model: str
    enhance_first: bool
    variants_per_packet: int
    image_count: int = 0
    slice_count: int = 0
    layout_summaries: dict[str, str] = field(default_factory=dict)
    reference_asset_count: int = 0
    reference_asset_summaries: list[ReferenceAssetSummary] = field(default_factory=list)
    issues: list[PreflightIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[PreflightIssue]:
        return [issue for issue in self.issues if issue.level == PREFLIGHT_ISSUE_ERROR]

    @property
    def warnings(self) -> list[PreflightIssue]:
        return [issue for issue in self.issues if issue.level == PREFLIGHT_ISSUE_WARNING]

    @property
    def status(self) -> str:
        if self.errors:
            return PREFLIGHT_ERROR
        if self.warnings:
            return PREFLIGHT_WARNING
        return PREFLIGHT_OK

    @property
    def ready(self) -> bool:
        return not self.errors


def build_generation_preflight(
    project: ProjectSpec,
    asset: AssetSpec,
    known_assets: list[AssetSpec] | None = None,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    prompt_provider: str | None = None,
    prompt_model: str | None = None,
    prompt_api_key: str | None = None,
    enhance_first: bool = False,
    variants_per_packet: int = 1,
    model_suggestions: dict[tuple[str, str], list[ModelSuggestion]] | None = None,
) -> GenerationPreflightReport:
    known_assets = known_assets or []
    suggestions = model_suggestions or {}
    image_provider = provider or project.provider_defaults.image_provider
    image_model = model or project.provider_defaults.image_model
    effective_prompt_provider = prompt_provider or project.provider_defaults.prompt_provider
    effective_prompt_model = prompt_model or project.provider_defaults.prompt_model
    report = GenerationPreflightReport(
        project_name=project.name,
        asset_name=asset.name,
        image_provider=image_provider,
        image_model=image_model,
        prompt_provider=effective_prompt_provider,
        prompt_model=effective_prompt_model,
        enhance_first=enhance_first,
        variants_per_packet=variants_per_packet,
    )

    if variants_per_packet < 1:
        report.issues.append(
            PreflightIssue(
                level=PREFLIGHT_ISSUE_ERROR,
                code="variants",
                message="Variants per packet must be at least 1",
            )
        )

    _add_model_validation_issue(
        report,
        provider=image_provider,
        role=IMAGE_ROLE,
        model=image_model,
        suggestions=suggestions,
    )
    _add_key_issue(report, provider=image_provider, api_key=api_key, purpose="image")

    if enhance_first:
        _add_model_validation_issue(
            report,
            provider=effective_prompt_provider,
            role=PROMPT_ROLE,
            model=effective_prompt_model,
            suggestions=suggestions,
        )
        _add_key_issue(
            report,
            provider=effective_prompt_provider,
            api_key=prompt_api_key,
            purpose="prompt",
        )

    try:
        packets = PromptPlanner().build_prompt_packets(
            project,
            asset,
            known_assets=known_assets,
        )
    except Exception as exc:
        report.issues.append(
            PreflightIssue(
                level=PREFLIGHT_ISSUE_ERROR,
                code="prompt-plan",
                message=f"Could not build prompt plan: {exc}",
            )
        )
        return report

    report.reference_asset_summaries = _reference_asset_summaries_from_packets(packets)
    report.reference_asset_count = len(report.reference_asset_summaries)
    report.image_count = len(packets) * max(variants_per_packet, 0)
    layout_counts = Counter(packet.layout_name for packet in packets)
    for layout_name, packet_count in sorted(layout_counts.items()):
        try:
            layout = project.get_layout(layout_name)
        except Exception as exc:
            report.issues.append(
                PreflightIssue(
                    level=PREFLIGHT_ISSUE_ERROR,
                    code="layout",
                    message=f"Could not resolve layout {layout_name}: {exc}",
                )
            )
            continue
        report.slice_count += len(layout.regions) * packet_count * max(variants_per_packet, 0)
        report.layout_summaries[layout_name] = (
            f"{layout.width}x{layout.height}, "
            f"{len(layout.regions)} region(s), {packet_count} packet(s)"
        )

    if not packets:
        report.issues.append(
            PreflightIssue(
                level=PREFLIGHT_ISSUE_ERROR,
                code="prompt-plan",
                message="Prompt plan did not produce any packets",
            )
        )

    return report


def _reference_asset_summaries_from_packets(packets) -> list[ReferenceAssetSummary]:
    if not packets:
        return []
    raw_summaries = packets[0].metadata.get("known_assets", [])
    summaries: list[ReferenceAssetSummary] = []
    for raw_summary in raw_summaries:
        if not isinstance(raw_summary, dict):
            continue
        name = str(raw_summary.get("name") or "").strip()
        slug = str(raw_summary.get("slug") or "").strip()
        asset_type = str(raw_summary.get("asset_type") or "").strip()
        prompt = str(raw_summary.get("prompt") or "").strip()
        if not name or not slug or not asset_type or not prompt:
            continue
        summaries.append(
            ReferenceAssetSummary(
                name=name,
                slug=slug,
                asset_type=asset_type,
                prompt=prompt,
                details=str(raw_summary.get("details") or "").strip(),
                layout=str(raw_summary.get("layout") or "").strip(),
            )
        )
    return summaries


def _add_model_validation_issue(
    report: GenerationPreflightReport,
    provider: str,
    role: str,
    model: str,
    suggestions: dict[tuple[str, str], list[ModelSuggestion]],
) -> None:
    other_role = PROMPT_ROLE if role == IMAGE_ROLE else IMAGE_ROLE
    result = validate_model_choice(
        provider,
        role,
        model,
        extra=suggestions.get((role, provider), []),
        other_extra=suggestions.get((other_role, provider), []),
    )
    if result.status == MODEL_VALIDATION_ERROR:
        report.issues.append(
            PreflightIssue(level=PREFLIGHT_ISSUE_ERROR, code=f"{role}-model", message=result.message)
        )
    elif result.status == MODEL_VALIDATION_WARNING:
        report.issues.append(
            PreflightIssue(
                level=PREFLIGHT_ISSUE_WARNING,
                code=f"{role}-model",
                message=result.message,
            )
        )


def _add_key_issue(
    report: GenerationPreflightReport,
    provider: str,
    api_key: str | None,
    purpose: str,
) -> None:
    if provider not in KEYED_PROVIDERS:
        return
    if api_key:
        return
    report.issues.append(
        PreflightIssue(
            level=PREFLIGHT_ISSUE_ERROR,
            code=f"{purpose}-api-key",
            message=f"{provider_label(provider)} {purpose} API key is required",
        )
    )


def provider_label(provider: str) -> str:
    labels = {
        "mock": "Mock",
        "pollinations": "Pollinations",
        "openai": "OpenAI",
        "openrouter": "OpenRouter",
    }
    return labels.get(provider, provider.title())
