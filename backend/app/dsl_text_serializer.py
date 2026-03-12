from __future__ import annotations

import json
import re
from typing import Any

from .dsl_legacy_adapter import canonicalize_document
from .dsl_models import DuiDslDocument, DuiDslWidget

INDENT = "  "
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


def _format_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        if IDENT_RE.match(value):
            return value
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def _format_inline_value(value: object) -> str:
    if isinstance(value, dict):
        items = ", ".join(f"{key}: {_format_inline_value(item)}" for key, item in value.items())
        return f"{{ {items} }}" if items else "{}"
    if isinstance(value, list):
        items = ", ".join(_format_inline_value(item) for item in value)
        return f"[ {items} ]" if items else "[]"
    return _format_scalar(value)


def _render_object_lines(payload: dict[str, Any], indent: str) -> list[str]:
    lines: list[str] = []
    for key, value in payload.items():
        if isinstance(value, dict):
            lines.append(f"{indent}{key} {{")
            lines.extend(_render_object_lines(value, indent + INDENT))
            lines.append(f"{indent}}}")
        else:
            lines.append(f"{indent}{key}: {_format_inline_value(value)}")
    return lines


def _append_object_block(lines: list[str], name: str, payload: dict[str, Any], indent: str) -> None:
    if not payload:
        return
    lines.append(f"{indent}{name} {{")
    lines.extend(_render_object_lines(payload, indent + INDENT))
    lines.append(f"{indent}}}")


def _widget_props_without_top_level(widget: DuiDslWidget) -> dict[str, Any]:
    props = dict(widget.props)
    duplicates = {
        "title": widget.title,
        "zone": widget.zone,
        "capability_id": widget.capability_id,
        "binding_id": widget.binding_id,
        "template_id": widget.template_id,
    }
    for key, value in duplicates.items():
        if value is not None and props.get(key) == value:
            props.pop(key, None)
    return props


def serialize_dui_lang(document: DuiDslDocument) -> str:
    canonical = canonicalize_document(document)
    lines = [f"surface {canonical.surface.id} {{"]

    lines.append(
        f"{INDENT}surface_meta {{ title: {_format_scalar(canonical.surface.title)} route: {_format_scalar(canonical.surface.route)} }}"
    )
    lines.append(
        f"{INDENT}meta {{ document_id: {_format_scalar(canonical.meta.document_id)} revision: {canonical.meta.revision} "
        f"created_at: {_format_scalar(canonical.meta.created_at.isoformat().replace('+00:00', 'Z'))} "
        f"created_by: {_format_scalar(canonical.meta.created_by)} }}"
    )

    lines.append(f"{INDENT}theme {{")
    lines.append(f"{INDENT * 2}profile: {_format_scalar(canonical.theme.profile)}")
    lines.append(f"{INDENT * 2}density: {_format_scalar(canonical.theme.density)}")
    _append_object_block(lines, "tokens", canonical.theme.tokens, INDENT * 2)
    lines.append(f"{INDENT}}}")

    _append_object_block(lines, "layout_constraints", canonical.layout_constraints, INDENT)
    _append_object_block(lines, "state", canonical.state.locals, INDENT)

    for action in canonical.actions:
        lines.append("")
        lines.append(f"{INDENT}action {action.id} {{")
        lines.append(f"{INDENT * 2}type: {_format_scalar(action.type)}")
        _append_object_block(lines, "params", action.params, INDENT * 2)
        lines.append(f"{INDENT}}}")

    for binding in canonical.bindings:
        lines.append("")
        lines.append(f"{INDENT}binding {binding.id} {{")
        lines.append(f"{INDENT * 2}source: {_format_scalar(binding.source)}")
        lines.append(f"{INDENT * 2}select: {_format_scalar(binding.select)}")
        _append_object_block(lines, "args", binding.args, INDENT * 2)
        _append_object_block(lines, "cache", binding.cache, INDENT * 2)
        lines.append(f"{INDENT}}}")

    for page in canonical.pages:
        lines.append("")
        lines.append(f"{INDENT}page {page.id} {{")
        lines.append(f"{INDENT * 2}title: {_format_scalar(page.title)}")
        lines.append(f"{INDENT * 2}route: {_format_scalar(page.route)}")
        lines.append(f"{INDENT * 2}groups: {_format_inline_value(page.group_ids)}")
        if page.is_default:
            lines.append(f"{INDENT * 2}default: true")
        _append_object_block(lines, "layout", page.layout, INDENT * 2)
        _append_object_block(lines, "style", page.style, INDENT * 2)
        _append_object_block(lines, "behavior", page.behavior, INDENT * 2)
        lines.append(f"{INDENT}}}")

    for group in canonical.groups:
        lines.append("")
        lines.append(f"{INDENT}group {group.id} {{")
        lines.append(f"{INDENT * 2}title: {_format_scalar(group.title)}")
        if group.page_id:
            lines.append(f"{INDENT * 2}page: {_format_scalar(group.page_id)}")
        lines.append(f"{INDENT * 2}zone: {_format_scalar(group.zone)}")
        lines.append(f"{INDENT * 2}widgets: {_format_inline_value(group.widget_ids)}")
        if not group.visible:
            lines.append(f"{INDENT * 2}visible: false")
        _append_object_block(lines, "layout", group.layout, INDENT * 2)
        _append_object_block(lines, "style", group.style, INDENT * 2)
        _append_object_block(lines, "behavior", group.behavior, INDENT * 2)
        lines.append(f"{INDENT}}}")

    for widget in canonical.widgets:
        lines.append("")
        lines.append(f"{INDENT}widget {widget.id}: {_format_scalar(widget.kind)} {{")
        if widget.title is not None:
            lines.append(f"{INDENT * 2}title: {_format_scalar(widget.title)}")
        if widget.group_id:
            lines.append(f"{INDENT * 2}group: {_format_scalar(widget.group_id)}")
        if widget.zone:
            lines.append(f"{INDENT * 2}zone: {_format_scalar(widget.zone)}")
        if widget.capability_id:
            lines.append(f"{INDENT * 2}capability_id: {_format_scalar(widget.capability_id)}")
        if widget.binding_id:
            lines.append(f"{INDENT * 2}binding_id: {_format_scalar(widget.binding_id)}")
        if widget.template_id:
            lines.append(f"{INDENT * 2}template_id: {_format_scalar(widget.template_id)}")
        if not widget.visible:
            lines.append(f"{INDENT * 2}visible: false")

        props = _widget_props_without_top_level(widget)
        _append_object_block(lines, "props", props, INDENT * 2)
        _append_object_block(lines, "style", widget.style, INDENT * 2)
        _append_object_block(lines, "layout", widget.layout, INDENT * 2)
        _append_object_block(lines, "behavior", widget.behavior, INDENT * 2)
        _append_object_block(lines, "a11y", widget.a11y, INDENT * 2)
        if widget.links:
            links_payload = [link.model_dump(mode="json") for link in widget.links]
            lines.append(f"{INDENT * 2}links {_format_inline_value(links_payload)}")
        lines.append(f"{INDENT}}}")

    lines.append("}")
    return "\n".join(lines)
