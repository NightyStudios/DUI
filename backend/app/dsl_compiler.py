from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .dsl_catalog import WIDGET_COMPILATION_MAP, ZONE_ALLOWLIST
from .dsl_legacy_adapter import canonicalize_document
from .dsl_models import DuiDslDocument, DuiDslWidget, DuiDslWidgetGroup
from .manifest_service import tokens_for
from .models import SectionConfig, ThemeConfig, UiManifest, WidgetConfig
from .template_catalog import get_template

DEFAULT_LAYOUT_CONSTRAINTS = {
    "max_columns": 2,
    "sidebar_width": "normal",
    "content_density": "comfortable",
}

ALLOWED_WIDGET_KINDS = {"kpi", "table", "activity", "chart", "card", "list", "panel", "tabs", "form"}

_KIND_DEFAULT_CAPABILITY: dict[str, str] = {
    "kpi": "ui.static.kpi",
    "table": "ui.static.table",
    "activity": "ui.static.activity",
    "chart": "ui.static.chart",
    "card": "ui.static.card",
    "list": "ui.static.list",
    "panel": "ui.static.panel",
    "tabs": "ui.static.tabs",
    "form": "ui.form.generic",
}
for mapping in WIDGET_COMPILATION_MAP.values():
    _KIND_DEFAULT_CAPABILITY.setdefault(mapping["kind"], mapping["capability_id"])

_CAPABILITY_KIND_INDEX: dict[str, str] = {
    mapping["capability_id"]: mapping["kind"] for mapping in WIDGET_COMPILATION_MAP.values()
}


def _normalize_zone(value: object) -> str:
    if isinstance(value, str) and value in ZONE_ALLOWLIST:
        return value
    return "content"


def _title_from_id(identifier: str) -> str:
    return " ".join(chunk.capitalize() for chunk in identifier.replace("-", "_").split("_"))


def _parse_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "on"}:
            return True
        if normalized in {"false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
    return None


def _resolve_widget_kind(raw_kind: str | None, capability_id: str | None, template_id: str | None) -> str:
    if isinstance(raw_kind, str):
        normalized = raw_kind.strip().lower()
        if normalized in ALLOWED_WIDGET_KINDS:
            return normalized
        if normalized in WIDGET_COMPILATION_MAP:
            return WIDGET_COMPILATION_MAP[normalized]["kind"]
        if "kpi" in normalized:
            return "kpi"
        if "table" in normalized or "calendar" in normalized:
            return "table"
        if "activity" in normalized or "feed" in normalized or "queue" in normalized:
            return "activity"
        if "chart" in normalized or "trend" in normalized:
            return "chart"
        if "list" in normalized:
            return "list"
        if "panel" in normalized:
            return "panel"
        if "tab" in normalized:
            return "tabs"
        if "form" in normalized:
            return "form"

    if template_id:
        template = get_template(template_id)
        if template:
            return template.kind

    if capability_id and capability_id in _CAPABILITY_KIND_INDEX:
        return _CAPABILITY_KIND_INDEX[capability_id]

    return "card"


def _resolve_widget_capability(kind: str, capability_id: str | None, template_id: str | None, binding_id: str | None) -> str:
    if capability_id:
        return capability_id

    if template_id:
        template = get_template(template_id)
        if template:
            return template.capability_id

    if binding_id:
        return f"ui.binding.{binding_id}"

    return _KIND_DEFAULT_CAPABILITY.get(kind, "ui.static.card")


def _build_widget_props(widget: DuiDslWidget, *, title: str, zone: str, capability_id: str, template_id: str | None) -> dict[str, Any]:
    props = dict(widget.props)
    props.setdefault("title", title)
    props.setdefault("zone", zone)
    props.setdefault("capability_id", capability_id)
    if template_id:
        props.setdefault("template_id", template_id)
    if widget.binding_id:
        props.setdefault("binding_id", widget.binding_id)
    if widget.links:
        props.setdefault("links", [link.model_dump(mode="json") for link in widget.links])
    return props


def _derive_sidebar_layout_constraints_from_groups(groups: list[DuiDslWidgetGroup]) -> dict[str, bool]:
    sidebar_groups = [group for group in groups if _normalize_zone(group.zone) == "sidebar" and group.visible]
    if not sidebar_groups:
        return {}

    collapsible_flag = False
    collapsed_initial = False
    for group in sidebar_groups:
        behavior = group.behavior if isinstance(group.behavior, dict) else {}
        explicit_collapsible = _parse_bool(behavior.get("collapsible"))
        if explicit_collapsible is True:
            collapsible_flag = True
        explicit_collapsed = _parse_bool(behavior.get("collapsed"))
        if explicit_collapsed is None:
            explicit_collapsed = _parse_bool(behavior.get("defaultCollapsed"))
        if explicit_collapsed is True:
            collapsed_initial = True

    if not collapsible_flag:
        return {}

    return {
        "sidebar_collapsible": True,
        "sidebar_collapsed_initial": collapsed_initial,
    }


def _active_page(document: DuiDslDocument) -> tuple[str | None, set[str] | None]:
    if not document.pages:
        return None, None

    page = next((candidate for candidate in document.pages if candidate.is_default), document.pages[0])
    if page.group_ids:
        return page.id, set(page.group_ids)

    return page.id, None


def _compile_from_widget_graph(document: DuiDslDocument) -> tuple[list[WidgetConfig], list[SectionConfig], dict[str, str], dict[str, bool]]:
    active_page_id, active_page_groups = _active_page(document)

    all_groups = [group for group in document.groups if group.visible]
    if active_page_id is not None:
        scoped_groups: list[DuiDslWidgetGroup] = []
        for group in all_groups:
            if active_page_groups is not None:
                if group.id in active_page_groups:
                    scoped_groups.append(group)
            elif group.page_id is None or group.page_id == active_page_id:
                scoped_groups.append(group)
    else:
        scoped_groups = all_groups

    groups_by_id = {group.id: group for group in scoped_groups}

    visible_widgets = [widget for widget in document.widgets if widget.visible]
    widgets_by_id = {widget.id: widget for widget in visible_widgets}

    group_widget_ids: dict[str, list[str]] = {group.id: [] for group in scoped_groups}
    for group in scoped_groups:
        for widget_id in group.widget_ids:
            if widget_id in widgets_by_id and widget_id not in group_widget_ids[group.id]:
                group_widget_ids[group.id].append(widget_id)

    ungrouped_widget_ids: list[str] = []
    for widget in visible_widgets:
        if widget.group_id and widget.group_id in groups_by_id:
            if widget.id not in group_widget_ids[widget.group_id]:
                group_widget_ids[widget.group_id].append(widget.id)
            continue
        ungrouped_widget_ids.append(widget.id)

    compiled_widgets: dict[str, WidgetConfig] = {}

    def ensure_compiled_widget(widget_id: str, fallback_zone: str) -> WidgetConfig | None:
        if widget_id in compiled_widgets:
            return compiled_widgets[widget_id]
        widget = widgets_by_id.get(widget_id)
        if widget is None:
            return None

        zone = _normalize_zone(widget.zone) if widget.zone else fallback_zone
        template_id = widget.template_id if isinstance(widget.template_id, str) and widget.template_id.strip() else None
        capability_hint = widget.capability_id if isinstance(widget.capability_id, str) and widget.capability_id.strip() else None
        kind = _resolve_widget_kind(widget.kind, capability_hint, template_id)
        capability_id = _resolve_widget_capability(kind, capability_hint, template_id, widget.binding_id)
        title = widget.title.strip() if isinstance(widget.title, str) and widget.title.strip() else _title_from_id(widget.id)

        props = _build_widget_props(widget, title=title, zone=zone, capability_id=capability_id, template_id=template_id)
        protected = bool(widget.behavior.get("protected", props.get("protected", False)))

        compiled = WidgetConfig(
            id=widget.id,
            title=title,
            kind=kind,
            zone=zone,
            capability_id=capability_id,
            protected=protected,
            template_id=template_id,
            props=props,
            style=dict(widget.style) if isinstance(widget.style, dict) else {},
            layout=dict(widget.layout) if isinstance(widget.layout, dict) else {},
        )
        compiled_widgets[widget_id] = compiled
        return compiled

    sections: list[SectionConfig] = []
    for group in scoped_groups:
        zone = _normalize_zone(group.zone)
        child_ids: list[str] = []
        for widget_id in group_widget_ids.get(group.id, []):
            compiled = ensure_compiled_widget(widget_id, zone)
            if compiled is not None:
                child_ids.append(compiled.id)

        sections.append(
            SectionConfig(
                id=group.id,
                title=group.title,
                zone=zone,
                child_widget_ids=child_ids,
                layout=dict(group.layout) if isinstance(group.layout, dict) else {},
                style=dict(group.style) if isinstance(group.style, dict) else {},
            )
        )

    for widget_id in ungrouped_widget_ids:
        ensure_compiled_widget(widget_id, "content")

    widgets = list(compiled_widgets.values())

    if not sections and widgets:
        for zone in ("header", "content", "sidebar", "footer"):
            children = [widget.id for widget in widgets if widget.zone == zone]
            if children:
                sections.append(
                    SectionConfig(
                        id=f"auto_{zone}",
                        title=f"{zone.capitalize()} Section",
                        zone=zone,
                        child_widget_ids=children,
                        layout={"columns": 1},
                        style={},
                    )
                )

    metadata = {
        "dsl_model": "widget-graph-v2",
        "widget_count": str(len(document.widgets)),
        "group_count": str(len(document.groups)),
        "page_count": str(len(document.pages)),
    }
    if active_page_id:
        metadata["active_page_id"] = active_page_id

    derived_layout_constraints = _derive_sidebar_layout_constraints_from_groups(scoped_groups)
    return widgets, sections, metadata, derived_layout_constraints


def compile_dsl_document_to_manifest(
    document: DuiDslDocument,
    *,
    manifest_revision: int,
    manifest_id: str | None = None,
) -> UiManifest:
    canonical_document = canonicalize_document(document)
    widgets, sections, extra_metadata, derived_layout_constraints = _compile_from_widget_graph(canonical_document)

    tokens = tokens_for(canonical_document.theme.profile, canonical_document.theme.density)
    for key, value in canonical_document.theme.tokens.items():
        tokens[key] = value

    metadata = {
        "surface_id": canonical_document.surface.id,
        "dsl_document_id": canonical_document.meta.document_id,
        "dsl_version": canonical_document.dsl_version,
        "created_by": canonical_document.meta.created_by,
        **extra_metadata,
    }
    layout_constraints = {**DEFAULT_LAYOUT_CONSTRAINTS, **canonical_document.layout_constraints}
    for key, value in derived_layout_constraints.items():
        layout_constraints.setdefault(key, value)

    return UiManifest(
        manifest_id=manifest_id or str(uuid4()),
        revision=manifest_revision,
        created_at=datetime.now(timezone.utc),
        theme=ThemeConfig(
            profile=canonical_document.theme.profile,
            density=canonical_document.theme.density,
            tokens=tokens,
        ),
        widgets=widgets,
        sections=sections,
        layout_constraints=layout_constraints,
        metadata=metadata,
    )
