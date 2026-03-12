from __future__ import annotations

from typing import Any

from .dsl_catalog import WIDGET_COMPILATION_MAP, ZONE_ALLOWLIST
from .dsl_models import DuiDslDocument, DuiDslPage, DuiDslWidget, DuiDslWidgetGroup

_ZONE_ORDER = ("header", "content", "sidebar", "footer")


def _normalize_zone(value: object) -> str:
    if isinstance(value, str) and value in ZONE_ALLOWLIST:
        return value
    return "content"


def _surface_page_id(surface_id: str) -> str:
    normalized = surface_id.replace("-", "_").replace(".", "_")
    return f"{normalized}_page"


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


def _contains_sidebar_collapsed_ref(value: object) -> bool:
    if isinstance(value, str):
        normalized = value.strip().replace("_", "").lower()
        return "sidebarcollapsed" in normalized
    if isinstance(value, dict):
        return any(_contains_sidebar_collapsed_ref(item) for item in value.items())
    if isinstance(value, tuple):
        return any(_contains_sidebar_collapsed_ref(item) for item in value)
    if isinstance(value, list):
        return any(_contains_sidebar_collapsed_ref(item) for item in value)
    return False


def derive_layout_constraints_from_legacy(
    *,
    document: DuiDslDocument,
) -> dict[str, Any]:
    sidebar_region = next(
        (
            node
            for node in document.legacy_nodes
            if node.type == "layout.region" and _normalize_zone(node.props.get("zone")) == "sidebar"
        ),
        None,
    )
    if sidebar_region is None:
        return {}

    prop_collapsible = _parse_bool(sidebar_region.props.get("collapsible"))
    if prop_collapsible is False:
        return {}

    has_toggle_action = any(
        action.type == "state.toggle" and _contains_sidebar_collapsed_ref(action.params)
        for action in document.actions
    )
    has_visibility_condition = _contains_sidebar_collapsed_ref(sidebar_region.visible_when)
    is_collapsible = prop_collapsible is True or has_toggle_action or has_visibility_condition
    if not is_collapsible:
        return {}

    collapsed_from_props = _parse_bool(sidebar_region.props.get("defaultCollapsed"))
    collapsed_initial = _parse_bool(document.state.locals.get("sidebarCollapsed"))
    if collapsed_initial is None:
        collapsed_initial = _parse_bool(document.state.locals.get("sidebar_collapsed"))
    if collapsed_initial is None:
        collapsed_initial = collapsed_from_props if collapsed_from_props is not None else False

    return {
        "sidebar_collapsible": True,
        "sidebar_collapsed_initial": collapsed_initial,
    }


def canonicalize_document(document: DuiDslDocument) -> DuiDslDocument:
    canonical = document.model_copy(deep=True)
    if canonical.pages or canonical.groups or canonical.widgets:
        canonical.legacy_nodes = []
        return canonical

    if not canonical.legacy_nodes:
        return canonical

    page_id = _surface_page_id(canonical.surface.id)
    legacy_layout_constraints = derive_layout_constraints_from_legacy(document=canonical)
    widget_map: dict[str, DuiDslWidget] = {}
    for node in canonical.legacy_nodes:
        mapping = WIDGET_COMPILATION_MAP.get(node.type)
        if not mapping:
            continue

        zone = _normalize_zone(node.props.get("zone"))
        widget_map[node.id] = DuiDslWidget(
            id=node.id,
            kind=mapping["kind"],
            title=str(node.props.get("title") or _title_from_id(node.id)),
            zone=zone,
            capability_id=str(node.props.get("capability_id") or mapping["capability_id"]),
            template_id=str(node.props.get("template_id")) if node.props.get("template_id") else None,
            visible=True,
            props=dict(node.props),
            style=dict(node.style) if isinstance(node.style, dict) else {},
            layout=dict(node.layout) if isinstance(node.layout, dict) else {},
            behavior={"protected": True} if bool(node.props.get("protected", False)) else {},
            a11y=dict(node.a11y) if isinstance(node.a11y, dict) else {},
        )

    groups: list[DuiDslWidgetGroup] = []
    assigned_widget_ids: set[str] = set()

    for node in canonical.legacy_nodes:
        if node.type != "layout.section":
            continue
        zone = _normalize_zone(node.props.get("zone"))
        widget_ids = [child_id for child_id in node.children if child_id in widget_map]
        for widget_id in widget_ids:
            widget_map[widget_id].group_id = node.id
        assigned_widget_ids.update(widget_ids)
        groups.append(
            DuiDslWidgetGroup(
                id=node.id,
                title=str(node.props.get("title") or _title_from_id(node.id)),
                page_id=page_id,
                zone=zone,
                widget_ids=widget_ids,
                visible=True,
                layout=dict(node.layout) if isinstance(node.layout, dict) else {},
                style=dict(node.style) if isinstance(node.style, dict) else {},
                behavior={},
            )
        )

    for zone in _ZONE_ORDER:
        region = next(
            (
                node
                for node in canonical.legacy_nodes
                if node.type == "layout.region" and _normalize_zone(node.props.get("zone")) == zone
            ),
            None,
        )
        if region is None:
            continue

        widget_ids = [
            child_id
            for child_id in region.children
            if child_id in widget_map and child_id not in assigned_widget_ids
        ]
        if not widget_ids:
            continue

        group_id = f"legacy_{zone}_group"
        for widget_id in widget_ids:
            widget_map[widget_id].group_id = group_id
        assigned_widget_ids.update(widget_ids)
        behavior: dict[str, Any] = {}
        if zone == "sidebar" and legacy_layout_constraints.get("sidebar_collapsible"):
            behavior["collapsible"] = True
            if legacy_layout_constraints.get("sidebar_collapsed_initial") is True:
                behavior["collapsed"] = True
        groups.append(
            DuiDslWidgetGroup(
                id=group_id,
                title=f"{zone.capitalize()} Group",
                page_id=page_id,
                zone=zone,
                widget_ids=widget_ids,
                visible=True,
                layout={"columns": 1},
                style={},
                behavior=behavior,
            )
        )

    remaining_by_zone: dict[str, list[str]] = {zone: [] for zone in _ZONE_ORDER}
    for widget_id, widget in widget_map.items():
        if widget_id in assigned_widget_ids:
            continue
        remaining_by_zone[_normalize_zone(widget.zone)].append(widget_id)

    for zone in _ZONE_ORDER:
        widget_ids = remaining_by_zone[zone]
        if not widget_ids:
            continue
        group_id = f"auto_{zone}_group"
        for widget_id in widget_ids:
            widget_map[widget_id].group_id = group_id
        groups.append(
            DuiDslWidgetGroup(
                id=group_id,
                title=f"{zone.capitalize()} Group",
                page_id=page_id,
                zone=zone,
                widget_ids=widget_ids,
                visible=True,
                layout={"columns": 1},
                style={},
                behavior={},
            )
        )

    canonical.pages = [
        DuiDslPage(
            id=page_id,
            title=canonical.surface.title,
            route=canonical.surface.route,
            group_ids=[group.id for group in groups],
            is_default=True,
            layout={"max_columns": canonical.layout_constraints.get("max_columns", 2)},
            style={},
            behavior={},
        )
    ]
    canonical.groups = groups
    canonical.widgets = list(widget_map.values())
    for key, value in legacy_layout_constraints.items():
        canonical.layout_constraints.setdefault(key, value)
    canonical.legacy_nodes = []
    return canonical
