from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .dsl_models import (
    DuiDslDocument,
    DuiDslMeta,
    DuiDslPage,
    DuiDslTheme,
    DuiDslWidget,
    DuiDslWidgetGroup,
    DuiDslWidgetLink,
)
from .manifest_service import tokens_for
from .models import UiManifest, WidgetConfig

_ZONE_ORDER = ["header", "content", "sidebar", "footer"]


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
        bindings=[binding.model_copy(deep=True) for binding in current_document.bindings],
        actions=[action.model_copy(deep=True) for action in current_document.actions],
        layout_constraints=dict(manifest.layout_constraints),
    )
