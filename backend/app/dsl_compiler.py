from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .dsl_catalog import WIDGET_COMPILATION_MAP, ZONE_ALLOWLIST
from .dsl_models import DuiDslDocument
from .manifest_service import tokens_for
from .models import SectionConfig, ThemeConfig, UiManifest, WidgetConfig

DEFAULT_LAYOUT_CONSTRAINTS = {
    "max_columns": 2,
    "sidebar_width": "normal",
    "content_density": "comfortable",
}


def _normalize_zone(value: object) -> str:
    if isinstance(value, str) and value in ZONE_ALLOWLIST:
        return value
    return "content"


def _title_from_node(node_id: str) -> str:
    return " ".join(chunk.capitalize() for chunk in node_id.replace("-", "_").split("_"))


def compile_dsl_document_to_manifest(
    document: DuiDslDocument,
    *,
    manifest_revision: int,
    manifest_id: str | None = None,
) -> UiManifest:
    widget_ids: set[str] = set()
    widgets: list[WidgetConfig] = []

    for node in document.nodes:
        mapping = WIDGET_COMPILATION_MAP.get(node.type)
        if not mapping:
            continue

        zone = _normalize_zone(node.props.get("zone"))
        widget_id = node.id
        widget_ids.add(widget_id)

        title = str(node.props.get("title") or _title_from_node(node.id))
        capability_id = str(node.props.get("capability_id") or mapping["capability_id"])
        template_id = node.props.get("template_id")
        protected = bool(node.props.get("protected", False))

        widgets.append(
            WidgetConfig(
                id=widget_id,
                title=title,
                kind=mapping["kind"],  # validated by WidgetConfig
                zone=zone,
                capability_id=capability_id,
                protected=protected,
                template_id=template_id if isinstance(template_id, str) else None,
                props=dict(node.props),
            )
        )

    sections: list[SectionConfig] = []
    for node in document.nodes:
        if node.type != "layout.section":
            continue
        zone = _normalize_zone(node.props.get("zone"))
        title = str(node.props.get("title") or _title_from_node(node.id))
        layout = node.layout if isinstance(node.layout, dict) else {}
        child_widget_ids = [child_id for child_id in node.children if child_id in widget_ids]

        sections.append(
            SectionConfig(
                id=node.id,
                title=title,
                zone=zone,
                child_widget_ids=child_widget_ids,
                layout=layout,
            )
        )

    if not sections and widgets:
        # Build simple auto-sections grouped by zone.
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
                    )
                )

    tokens = tokens_for(document.theme.profile, document.theme.density)
    for key, value in document.theme.tokens.items():
        tokens[key] = value

    metadata = {
        "surface_id": document.surface.id,
        "dsl_document_id": document.meta.document_id,
        "dsl_version": document.dsl_version,
        "created_by": document.meta.created_by,
    }

    return UiManifest(
        manifest_id=manifest_id or str(uuid4()),
        revision=manifest_revision,
        created_at=datetime.now(timezone.utc),
        theme=ThemeConfig(
            profile=document.theme.profile,
            density=document.theme.density,
            tokens=tokens,
        ),
        widgets=widgets,
        sections=sections,
        layout_constraints={**DEFAULT_LAYOUT_CONSTRAINTS, **document.layout_constraints},
        metadata=metadata,
    )

