from __future__ import annotations

from .dsl_legacy_adapter import canonicalize_document
from .dsl_models import DuiDslDocument, DuiDslPage, DuiDslWidget, DuiDslWidgetGroup
from .models import PatchOperation, Zone
from .template_catalog import get_template


def _surface_page_id(surface_id: str) -> str:
    normalized = surface_id.replace("-", "_").replace(".", "_")
    return f"{normalized}_page"


def _find_widget(document: DuiDslDocument, widget_id: str) -> DuiDslWidget | None:
    for widget in document.widgets:
        if widget.id == widget_id:
            return widget
    return None


def _find_group(document: DuiDslDocument, group_id: str) -> DuiDslWidgetGroup | None:
    for group in document.groups:
        if group.id == group_id:
            return group
    return None


def _default_page(document: DuiDslDocument) -> DuiDslPage:
    if document.pages:
        return next((page for page in document.pages if page.is_default), document.pages[0])

    page = DuiDslPage(
        id=_surface_page_id(document.surface.id),
        title=document.surface.title,
        route=document.surface.route,
        group_ids=[],
        is_default=True,
        layout={"max_columns": document.layout_constraints.get("max_columns", 2)},
        style={},
        behavior={},
    )
    document.pages.append(page)
    return page


def _visible_groups_for_default_page(document: DuiDslDocument) -> list[DuiDslWidgetGroup]:
    page = _default_page(document)
    if page.group_ids:
        ordered_groups: list[DuiDslWidgetGroup] = []
        for group_id in page.group_ids:
            group = _find_group(document, group_id)
            if group is not None and group.visible:
                ordered_groups.append(group)
        return ordered_groups

    return [group for group in document.groups if group.visible and (group.page_id is None or group.page_id == page.id)]


def _ensure_page_group_link(page: DuiDslPage, group_id: str) -> None:
    if group_id not in page.group_ids:
        page.group_ids.append(group_id)


def _next_available_id(existing_ids: set[str], preferred_id: str) -> str:
    if preferred_id not in existing_ids:
        return preferred_id

    stem = preferred_id
    if "_" in preferred_id:
        prefix, maybe_suffix = preferred_id.rsplit("_", 1)
        if maybe_suffix.isdigit():
            stem = prefix
    suffix = 2
    while f"{stem}_{suffix}" in existing_ids:
        suffix += 1
    return f"{stem}_{suffix}"


def _ensure_zone_group(document: DuiDslDocument, zone: Zone) -> DuiDslWidgetGroup:
    for group in _visible_groups_for_default_page(document):
        if group.zone == zone:
            return group

    page = _default_page(document)
    group_id = _next_available_id({group.id for group in document.groups}, f"auto_{zone}_group")
    group = DuiDslWidgetGroup(
        id=group_id,
        title=f"{zone.capitalize()} Group",
        page_id=page.id,
        zone=zone,
        widget_ids=[],
        visible=True,
        layout={"columns": 1},
        style={},
        behavior={},
    )
    document.groups.append(group)
    _ensure_page_group_link(page, group.id)
    return group


def _detach_widget_from_groups(document: DuiDslDocument, widget_id: str, *, skip_group_id: str | None = None) -> None:
    for group in document.groups:
        if group.id == skip_group_id:
            continue
        if widget_id in group.widget_ids:
            group.widget_ids = [candidate for candidate in group.widget_ids if candidate != widget_id]


def _move_widget_to_zone(document: DuiDslDocument, *, widget_id: str, zone: Zone) -> None:
    widget = _find_widget(document, widget_id)
    if widget is None:
        return

    target_group = _ensure_zone_group(document, zone)
    _detach_widget_from_groups(document, widget_id, skip_group_id=target_group.id)

    if widget.id not in target_group.widget_ids:
        target_group.widget_ids.append(widget.id)

    widget.group_id = target_group.id
    widget.zone = zone
    widget.props["zone"] = zone


def _remove_widget(document: DuiDslDocument, widget_id: str) -> None:
    if _find_widget(document, widget_id) is None:
        return
    document.widgets = [candidate for candidate in document.widgets if candidate.id != widget_id]
    _detach_widget_from_groups(document, widget_id)


def _upsert_group(
    document: DuiDslDocument,
    *,
    group_id: str,
    title: str,
    zone: Zone,
    widget_ids: list[str],
    layout: dict[str, object] | None = None,
) -> None:
    page = _default_page(document)
    children = [widget_id for widget_id in widget_ids if _find_widget(document, widget_id) is not None]
    if not children:
        return

    group = _find_group(document, group_id)
    if group is None:
        group = DuiDslWidgetGroup(
            id=group_id,
            title=title,
            page_id=page.id,
            zone=zone,
            widget_ids=list(children),
            visible=True,
            layout=dict(layout or {}),
            style={},
            behavior={},
        )
        document.groups.append(group)
    else:
        group.title = title
        group.page_id = page.id
        group.zone = zone
        group.visible = True
        group.widget_ids = list(children)
        group.layout = dict(layout or {})

    _ensure_page_group_link(page, group.id)
    for widget_id in children:
        widget = _find_widget(document, widget_id)
        if widget is None:
            continue
        _detach_widget_from_groups(document, widget_id, skip_group_id=group.id)
        widget.group_id = group.id
        widget.zone = zone
        widget.props["zone"] = zone


def _add_widget(document: DuiDslDocument, widget: DuiDslWidget) -> None:
    if _find_widget(document, widget.id) is not None:
        return

    next_widget = widget.model_copy(deep=True)
    target_zone = next_widget.zone or "content"
    target_group = _find_group(document, next_widget.group_id) if next_widget.group_id else None
    if target_group is None:
        target_group = _ensure_zone_group(document, target_zone)

    next_widget.group_id = target_group.id
    next_widget.zone = target_group.zone
    next_widget.props["zone"] = target_group.zone
    document.widgets.append(next_widget)
    if next_widget.id not in target_group.widget_ids:
        target_group.widget_ids.append(next_widget.id)


def _add_widget_from_template(document: DuiDslDocument, operation: PatchOperation) -> None:
    if not operation.template_id or not operation.widget_id or not operation.zone:
        return
    if _find_widget(document, operation.widget_id) is not None:
        return

    template = get_template(operation.template_id)
    if template is None:
        return

    target_group = _ensure_zone_group(document, operation.zone)
    title = operation.title or template.title
    capability_id = operation.capability_id or template.capability_id
    widget = DuiDslWidget(
        id=operation.widget_id,
        kind=template.kind,
        title=title,
        zone=operation.zone,
        group_id=target_group.id,
        capability_id=capability_id,
        template_id=template.template_id,
        visible=True,
        props={
            **template.default_props,
            **(operation.props or {}),
            "title": title,
            "zone": operation.zone,
            "template_id": template.template_id,
            "capability_id": capability_id,
        },
        style={},
        layout={},
        behavior={},
        a11y={},
        links=[],
    )
    document.widgets.append(widget)
    if widget.id not in target_group.widget_ids:
        target_group.widget_ids.append(widget.id)


def apply_patch_operations_to_document(document: DuiDslDocument, operations: list[PatchOperation]) -> DuiDslDocument:
    updated = canonicalize_document(document)

    for operation in operations:
        if operation.op == "set_theme_profile" and operation.profile:
            updated.theme.profile = operation.profile

        elif operation.op == "set_density" and operation.density:
            updated.theme.density = operation.density

        elif operation.op == "set_theme_tokens" and operation.tokens:
            updated.theme.tokens.update(operation.tokens)

        elif operation.op == "set_layout_constraints" and operation.layout_constraints:
            updated.layout_constraints.update(operation.layout_constraints)

        elif operation.op == "move_widget" and operation.widget_id and operation.zone:
            _move_widget_to_zone(updated, widget_id=operation.widget_id, zone=operation.zone)

        elif operation.op == "remove_widget" and operation.widget_id:
            _remove_widget(updated, operation.widget_id)

        elif operation.op == "add_widget" and operation.widget:
            _add_widget(
                updated,
                DuiDslWidget(
                    id=operation.widget.id,
                    kind=operation.widget.kind,
                    title=operation.widget.title,
                    zone=operation.widget.zone,
                    capability_id=operation.widget.capability_id,
                    template_id=operation.widget.template_id,
                    visible=not bool(operation.widget.props.get("hidden", False)),
                    props=dict(operation.widget.props),
                    style=dict(operation.widget.style),
                    layout=dict(operation.widget.layout),
                    behavior={"protected": operation.widget.protected} if operation.widget.protected else {},
                    a11y={},
                    links=[],
                ),
            )

        elif operation.op == "add_widget_from_template":
            _add_widget_from_template(updated, operation)

        elif operation.op == "compose_section" and operation.section_id and operation.zone:
            _upsert_group(
                updated,
                group_id=operation.section_id,
                title=operation.section_title or operation.section_id.replace("_", " ").title(),
                zone=operation.zone,
                widget_ids=operation.child_widget_ids or [],
                layout=operation.section_layout,
            )

    return updated
