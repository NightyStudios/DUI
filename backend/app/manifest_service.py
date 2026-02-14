from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .models import Density, PatchOperation, SectionConfig, ThemeProfile, UiManifest, WidgetConfig
from .template_catalog import get_template


PROFILE_TOKENS: dict[ThemeProfile, dict[str, str]] = {
    "default": {
        "bg": "#f3edf7",
        "surface": "#fffbfe",
        "surface_container": "#f7f2fa",
        "text": "#1d1b20",
        "muted": "#49454f",
        "accent": "#6750a4",
        "accent_container": "#eaddff",
        "outline": "#79747e",
        "radius": "16px",
        "shadow": "0 1px 2px rgba(0, 0, 0, 0.3), 0 2px 6px rgba(0, 0, 0, 0.14)",
        "font": "'Roboto', sans-serif",
    },
    "minimal": {
        "bg": "#f8fafc",
        "surface": "#ffffff",
        "surface_container": "#f1f5f9",
        "text": "#0f172a",
        "muted": "#475569",
        "accent": "#0f172a",
        "accent_container": "#e2e8f0",
        "outline": "#94a3b8",
        "radius": "12px",
        "shadow": "0 1px 2px rgba(15, 23, 42, 0.08)",
        "font": "'Roboto', sans-serif",
    },
    "liquid_glass": {
        "bg": "#dbeafe",
        "surface": "rgba(255, 255, 255, 0.66)",
        "surface_container": "rgba(255, 255, 255, 0.5)",
        "text": "#0f172a",
        "muted": "#334155",
        "accent": "#0369a1",
        "accent_container": "rgba(186, 230, 253, 0.65)",
        "outline": "rgba(255, 255, 255, 0.6)",
        "radius": "20px",
        "shadow": "0 10px 32px rgba(15, 23, 42, 0.22)",
        "font": "'Roboto', sans-serif",
    },
}

DENSITY_TOKENS: dict[Density, dict[str, str]] = {
    "comfortable": {
        "gap": "16px",
        "padding": "16px",
        "row_height": "44px",
    },
    "compact": {
        "gap": "10px",
        "padding": "10px",
        "row_height": "36px",
    },
}


def tokens_for(profile: ThemeProfile, density: Density) -> dict[str, str]:
    tokens = dict(PROFILE_TOKENS[profile])
    tokens.update(DENSITY_TOKENS[density])
    return tokens


def _remove_widget_from_sections(manifest: UiManifest, widget_id: str) -> None:
    for section in manifest.sections:
        section.child_widget_ids = [value for value in section.child_widget_ids if value != widget_id]


def _get_widget(manifest: UiManifest, widget_id: str) -> WidgetConfig | None:
    for widget in manifest.widgets:
        if widget.id == widget_id:
            return widget
    return None


def _upsert_section(manifest: UiManifest, section: SectionConfig) -> None:
    for index, existing in enumerate(manifest.sections):
        if existing.id == section.id:
            manifest.sections[index] = section
            return
    manifest.sections.append(section)


def apply_patch_operations(manifest: UiManifest, operations: list[PatchOperation]) -> UiManifest:
    updated = manifest.model_copy(deep=True)

    for operation in operations:
        if operation.op == "set_theme_profile" and operation.profile:
            updated.theme.profile = operation.profile
            updated.theme.tokens = tokens_for(updated.theme.profile, updated.theme.density)

        elif operation.op == "set_density" and operation.density:
            updated.theme.density = operation.density
            updated.theme.tokens = tokens_for(updated.theme.profile, updated.theme.density)

        elif operation.op == "set_theme_tokens" and operation.tokens:
            for key, value in operation.tokens.items():
                updated.theme.tokens[key] = value

        elif operation.op == "set_layout_constraints" and operation.layout_constraints:
            updated.layout_constraints.update(operation.layout_constraints)

        elif operation.op == "move_widget" and operation.widget_id and operation.zone:
            widget = _get_widget(updated, operation.widget_id)
            if widget:
                widget.zone = operation.zone
                _remove_widget_from_sections(updated, widget.id)

        elif operation.op == "remove_widget" and operation.widget_id:
            updated.widgets = [w for w in updated.widgets if w.id != operation.widget_id]
            _remove_widget_from_sections(updated, operation.widget_id)

        elif operation.op == "add_widget" and operation.widget:
            exists = any(w.id == operation.widget.id for w in updated.widgets)
            if not exists:
                updated.widgets.append(operation.widget)

        elif operation.op == "add_widget_from_template" and operation.template_id and operation.widget_id and operation.zone:
            template = get_template(operation.template_id)
            exists = any(w.id == operation.widget_id for w in updated.widgets)
            if template and not exists:
                widget = WidgetConfig(
                    id=operation.widget_id,
                    title=operation.title or template.title,
                    kind=template.kind,
                    zone=operation.zone,
                    capability_id=operation.capability_id or template.capability_id,
                    protected=False,
                    template_id=template.template_id,
                    props={**template.default_props, **(operation.props or {})},
                )
                updated.widgets.append(widget)

        elif operation.op == "compose_section" and operation.section_id and operation.zone:
            section = SectionConfig(
                id=operation.section_id,
                title=operation.section_title or operation.section_id.replace("_", " ").title(),
                zone=operation.zone,
                child_widget_ids=operation.child_widget_ids or [],
                layout=operation.section_layout or {},
            )
            _upsert_section(updated, section)

    updated.manifest_id = str(uuid4())
    updated.revision = manifest.revision + 1
    updated.created_at = datetime.now(timezone.utc)
    return updated


def clone_with_revision(manifest: UiManifest, revision: int) -> UiManifest:
    cloned = manifest.model_copy(deep=True)
    cloned.manifest_id = str(uuid4())
    cloned.revision = revision
    cloned.created_at = datetime.now(timezone.utc)
    return cloned
