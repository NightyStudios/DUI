from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .dsl_catalog import WIDGET_COMPILATION_MAP
from .dsl_models import (
    DuiDslDocument,
    DuiDslMeta,
    DuiDslNode,
    DuiDslPage,
    DuiDslTheme,
    DuiDslWidget,
    DuiDslWidgetGroup,
    DuiDslWidgetLink,
)
from .manifest_service import tokens_for
from .models import UiManifest, WidgetConfig


_KIND_TO_NODE_TYPE: dict[str, str] = {
    "kpi": "data.kpi_card",
    "table": "data.data_table",
    "activity": "data.activity_feed",
    "chart": "chart.line",
    "card": "layout.card",
    "list": "layout.list",
    "panel": "layout.panel",
    "tabs": "layout.tabs",
    "form": "form.form",
}

_ZONE_ORDER = ["header", "content", "sidebar", "footer"]


def _resolve_node_type(widget: WidgetConfig) -> str:
    for node_type, mapping in WIDGET_COMPILATION_MAP.items():
        if mapping["capability_id"] == widget.capability_id:
            return node_type
    return _KIND_TO_NODE_TYPE.get(widget.kind, "layout.card")


def _filter_custom_theme_tokens(manifest: UiManifest) -> dict[str, str]:
    base_tokens = tokens_for(manifest.theme.profile, manifest.theme.density)
    custom: dict[str, str] = {}
    for key, value in manifest.theme.tokens.items():
        if base_tokens.get(key) != value:
            custom[key] = value
    return custom


def _surface_page_id(surface_id: str) -> str:
    normalized = surface_id.replace("-", "_").replace(".", "_")
    return f"{normalized}_page"


def _extract_links(widget: WidgetConfig) -> list[DuiDslWidgetLink]:
    raw_links = widget.props.get("links")
    links: list[DuiDslWidgetLink] = []
    if isinstance(raw_links, list):
        for item in raw_links:
            if isinstance(item, dict):
                try:
                    links.append(DuiDslWidgetLink.model_validate(item))
                except Exception:  # noqa: BLE001
                    continue
    elif isinstance(raw_links, dict):
        if any(key in raw_links for key in {"page", "widget", "route", "rel", "payload"}):
            try:
                links.append(DuiDslWidgetLink.model_validate(raw_links))
            except Exception:  # noqa: BLE001
                pass
    return links


def _build_widget_graph_from_manifest(manifest: UiManifest, *, surface_id: str, surface_title: str, surface_route: str) -> tuple[list[DuiDslPage], list[DuiDslWidgetGroup], list[DuiDslWidget]]:
    page_id = _surface_page_id(surface_id)

    widgets_by_id = {widget.id: widget for widget in manifest.widgets}
    group_by_widget_id: dict[str, str] = {}
    groups: list[DuiDslWidgetGroup] = []

    if manifest.sections:
        for section in manifest.sections:
            groups.append(
                DuiDslWidgetGroup(
                    id=section.id,
                    title=section.title,
                    page_id=page_id,
                    zone=section.zone,
                    widget_ids=[widget_id for widget_id in section.child_widget_ids if widget_id in widgets_by_id],
                    visible=True,
                    layout=dict(section.layout),
                    style=dict(section.style),
                    behavior={},
                )
            )
            for widget_id in section.child_widget_ids:
                if widget_id in widgets_by_id:
                    group_by_widget_id.setdefault(widget_id, section.id)
    else:
        for zone in _ZONE_ORDER:
            zone_widgets = [widget.id for widget in manifest.widgets if widget.zone == zone]
            if not zone_widgets:
                continue
            group_id = f"group_{zone}"
            groups.append(
                DuiDslWidgetGroup(
                    id=group_id,
                    title=f"{zone.capitalize()} Group",
                    page_id=page_id,
                    zone=zone,
                    widget_ids=zone_widgets,
                    visible=True,
                    layout={"columns": 1},
                    style={},
                    behavior={},
                )
            )
            for widget_id in zone_widgets:
                group_by_widget_id[widget_id] = group_id

    widgets: list[DuiDslWidget] = []
    for widget in manifest.widgets:
        group_id = group_by_widget_id.get(widget.id)
        binding_id = widget.props.get("binding_id")
        widgets.append(
            DuiDslWidget(
                id=widget.id,
                kind=widget.kind,
                title=widget.title,
                zone=widget.zone,
                group_id=group_id,
                capability_id=widget.capability_id,
                binding_id=binding_id if isinstance(binding_id, str) else None,
                template_id=widget.template_id,
                visible=not bool(widget.props.get("hidden", False)),
                props=dict(widget.props),
                style=dict(widget.style),
                layout=dict(widget.layout),
                behavior={"protected": widget.protected} if widget.protected else {},
                a11y={},
                links=_extract_links(widget),
            )
        )

    group_ids = [group.id for group in groups]
    page = DuiDslPage(
        id=page_id,
        title=surface_title,
        route=surface_route,
        group_ids=group_ids,
        is_default=True,
        layout={"max_columns": manifest.layout_constraints.get("max_columns", 2)},
        style={},
        behavior={},
    )
    return [page], groups, widgets


def _build_legacy_nodes(groups: list[DuiDslWidgetGroup], widgets: list[DuiDslWidget]) -> list[DuiDslNode]:
    zone_to_region = {
        "header": "main_header",
        "content": "main_content",
        "sidebar": "main_sidebar",
        "footer": "main_footer",
    }

    group_by_id = {group.id: group for group in groups}
    widgets_by_id = {widget.id: widget for widget in widgets}

    section_child_ids: set[str] = set()
    section_by_zone: dict[str, list[str]] = {zone: [] for zone in _ZONE_ORDER}
    section_nodes: list[DuiDslNode] = []
    for group in groups:
        if not group.visible:
            continue
        section_widget_ids = [widget_id for widget_id in group.widget_ids if widget_id in widgets_by_id and widgets_by_id[widget_id].visible]
        section_child_ids.update(section_widget_ids)
        section_by_zone[group.zone].append(group.id)
        section_nodes.append(
            DuiDslNode(
                id=group.id,
                type="layout.section",
                props={"title": group.title, "zone": group.zone},
                layout=dict(group.layout),
                style=dict(group.style),
                children=section_widget_ids,
            )
        )

    widgets_by_zone: dict[str, list[str]] = {zone: [] for zone in _ZONE_ORDER}
    widget_nodes: list[DuiDslNode] = []
    for widget in widgets:
        if not widget.visible:
            continue
        node_props = {
            "title": widget.title or "",
            "zone": widget.zone or (group_by_id[widget.group_id].zone if widget.group_id in group_by_id else "content"),
            "capability_id": widget.capability_id or "ui.static.card",
            "protected": bool(widget.behavior.get("protected", False)),
        }
        if widget.template_id:
            node_props["template_id"] = widget.template_id
        node_props.update(widget.props)
        widget_nodes.append(
            DuiDslNode(
                id=widget.id,
                type=_resolve_node_type(
                    WidgetConfig(
                        id=widget.id,
                        title=widget.title or widget.id,
                        kind=widget.kind if widget.kind in _KIND_TO_NODE_TYPE else "card",
                        zone=node_props["zone"],
                        capability_id=node_props["capability_id"],
                        protected=bool(node_props.get("protected", False)),
                        template_id=widget.template_id,
                        props=node_props,
                        style=dict(widget.style),
                        layout=dict(widget.layout),
                    )
                ),
                props=node_props,
                style=dict(widget.style),
                layout=dict(widget.layout),
                a11y=dict(widget.a11y),
            )
        )
        if widget.id not in section_child_ids:
            widgets_by_zone[node_props["zone"]].append(widget.id)

    region_nodes = [
        DuiDslNode(id=zone_to_region["header"], type="layout.region", props={"zone": "header"}, children=section_by_zone["header"] + widgets_by_zone["header"]),
        DuiDslNode(id=zone_to_region["content"], type="layout.region", props={"zone": "content"}, children=section_by_zone["content"] + widgets_by_zone["content"]),
        DuiDslNode(id=zone_to_region["sidebar"], type="layout.region", props={"zone": "sidebar"}, children=section_by_zone["sidebar"] + widgets_by_zone["sidebar"]),
        DuiDslNode(id=zone_to_region["footer"], type="layout.region", props={"zone": "footer"}, children=section_by_zone["footer"] + widgets_by_zone["footer"]),
    ]

    return [DuiDslNode(id="root", type="layout.page", children=[zone_to_region[zone] for zone in _ZONE_ORDER]), *region_nodes, *section_nodes, *widget_nodes]


def build_dsl_document_from_manifest(
    manifest: UiManifest,
    *,
    current_document: DuiDslDocument,
    created_by: str = "patch-sync",
) -> DuiDslDocument:
    surface = current_document.surface.model_copy(deep=True)
    pages, groups, widgets = _build_widget_graph_from_manifest(
        manifest,
        surface_id=surface.id,
        surface_title=surface.title,
        surface_route=surface.route,
    )

    legacy_nodes = _build_legacy_nodes(groups, widgets)

    return DuiDslDocument(
        dsl_version=current_document.dsl_version,
        surface=surface,
        meta=DuiDslMeta(
            document_id=f"doc_{uuid4().hex}",
            revision=current_document.meta.revision + 1,
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
        ),
        theme=DuiDslTheme(
            profile=manifest.theme.profile,
            density=manifest.theme.density,
            tokens=_filter_custom_theme_tokens(manifest),
        ),
        state=current_document.state.model_copy(deep=True),
        pages=pages,
        groups=groups,
        widgets=widgets,
        nodes=legacy_nodes,
        bindings=[binding.model_copy(deep=True) for binding in current_document.bindings],
        actions=[action.model_copy(deep=True) for action in current_document.actions],
        layout_constraints=dict(manifest.layout_constraints),
    )
