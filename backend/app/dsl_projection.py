from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .dsl_catalog import WIDGET_COMPILATION_MAP
from .dsl_models import DuiDslDocument, DuiDslMeta, DuiDslNode, DuiDslTheme
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


def build_dsl_document_from_manifest(
    manifest: UiManifest,
    *,
    current_document: DuiDslDocument,
    created_by: str = "patch-sync",
) -> DuiDslDocument:
    zone_to_region = {
        "header": "main_header",
        "content": "main_content",
        "sidebar": "main_sidebar",
        "footer": "main_footer",
    }
    root_children = [zone_to_region[zone] for zone in ("header", "content", "sidebar", "footer")]

    section_child_ids: set[str] = set()
    section_by_zone: dict[str, list[str]] = {"header": [], "content": [], "sidebar": [], "footer": []}
    section_nodes: list[DuiDslNode] = []
    for section in manifest.sections:
        section_child_ids.update(section.child_widget_ids)
        section_by_zone[section.zone].append(section.id)
        section_nodes.append(
            DuiDslNode(
                id=section.id,
                type="layout.section",
                props={"title": section.title, "zone": section.zone},
                layout=dict(section.layout),
                children=list(section.child_widget_ids),
            )
        )

    widgets_by_zone: dict[str, list[str]] = {"header": [], "content": [], "sidebar": [], "footer": []}
    widget_nodes: list[DuiDslNode] = []
    for widget in manifest.widgets:
        node_props = {
            "title": widget.title,
            "zone": widget.zone,
            "capability_id": widget.capability_id,
            "protected": widget.protected,
        }
        if widget.template_id:
            node_props["template_id"] = widget.template_id
        node_props.update(widget.props)
        widget_nodes.append(
            DuiDslNode(
                id=widget.id,
                type=_resolve_node_type(widget),
                props=node_props,
            )
        )
        if widget.id not in section_child_ids:
            widgets_by_zone[widget.zone].append(widget.id)

    region_nodes = [
        DuiDslNode(id=zone_to_region["header"], type="layout.region", props={"zone": "header"}, children=section_by_zone["header"] + widgets_by_zone["header"]),
        DuiDslNode(id=zone_to_region["content"], type="layout.region", props={"zone": "content"}, children=section_by_zone["content"] + widgets_by_zone["content"]),
        DuiDslNode(id=zone_to_region["sidebar"], type="layout.region", props={"zone": "sidebar"}, children=section_by_zone["sidebar"] + widgets_by_zone["sidebar"]),
        DuiDslNode(id=zone_to_region["footer"], type="layout.region", props={"zone": "footer"}, children=section_by_zone["footer"] + widgets_by_zone["footer"]),
    ]

    return DuiDslDocument(
        dsl_version=current_document.dsl_version,
        surface=current_document.surface.model_copy(deep=True),
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
        nodes=[DuiDslNode(id="root", type="layout.page", children=root_children), *region_nodes, *section_nodes, *widget_nodes],
        bindings=[binding.model_copy(deep=True) for binding in current_document.bindings],
        actions=[action.model_copy(deep=True) for action in current_document.actions],
        layout_constraints=dict(manifest.layout_constraints),
    )
