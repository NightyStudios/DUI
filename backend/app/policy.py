from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import DuiMode, PatchOperation, UiManifest
from .policy_profiles import POLICY_PROFILES
from .template_catalog import template_ids


@dataclass
class PolicyResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class PolicyEngine:
    @staticmethod
    def validate_operations(
        manifest: UiManifest,
        operations: list[PatchOperation],
        mode: DuiMode = "extended",
    ) -> PolicyResult:
        result = PolicyResult()
        profile = POLICY_PROFILES[mode]

        widget_ids = {widget.id for widget in manifest.widgets}
        protected_ids = {widget.id for widget in manifest.widgets if widget.protected}
        removed_widget_ids = {
            operation.widget_id
            for operation in operations
            if operation.op == "remove_widget" and operation.widget_id in widget_ids
        }
        zone_counts = {"header": 0, "sidebar": 0, "content": 0, "footer": 0}
        for widget in manifest.widgets:
            if widget.id not in removed_widget_ids:
                zone_counts[widget.zone] += 1

        added_widget_ids = {
            operation.widget_id
            for operation in operations
            if operation.op == "add_widget_from_template" and operation.widget_id
        }
        added_widget_ids.update(
            operation.widget.id
            for operation in operations
            if operation.op == "add_widget" and operation.widget
        )
        planned_widget_ids = (set(widget_ids) - removed_widget_ids) | added_widget_ids

        for operation in operations:
            if operation.op not in profile.allowed_ops:
                result.errors.append(f"Operation '{operation.op}' is not allowed in mode '{mode}'")
                continue

            if operation.op == "remove_widget":
                if not operation.widget_id:
                    result.errors.append("remove_widget requires widget_id")
                    continue
                if operation.widget_id in protected_ids:
                    result.errors.append(f"Widget '{operation.widget_id}' is protected and cannot be removed")
                if operation.widget_id not in widget_ids:
                    result.warnings.append(f"Widget '{operation.widget_id}' does not exist in current manifest")

            elif operation.op == "move_widget":
                if not operation.widget_id or not operation.zone:
                    result.errors.append("move_widget requires widget_id and zone")
                elif operation.widget_id not in widget_ids:
                    result.errors.append(f"Cannot move unknown widget '{operation.widget_id}'")

            elif operation.op == "add_widget":
                if mode != "experimental":
                    result.errors.append("add_widget is allowed only in experimental mode")
                    continue
                if not operation.widget:
                    result.errors.append("add_widget requires widget payload")
                    continue
                if operation.widget.id in widget_ids:
                    result.errors.append(f"Widget '{operation.widget.id}' already exists")

            elif operation.op == "add_widget_from_template":
                if not operation.template_id or not operation.widget_id or not operation.zone:
                    result.errors.append("add_widget_from_template requires template_id, widget_id, zone")
                    continue
                if operation.template_id not in template_ids():
                    result.errors.append(f"Unknown template_id '{operation.template_id}'")
                if operation.widget_id in widget_ids:
                    result.errors.append(f"Widget '{operation.widget_id}' already exists")
                if zone_counts[operation.zone] >= profile.max_widgets_per_zone:
                    result.errors.append(f"Zone '{operation.zone}' has reached widget limit")
                else:
                    zone_counts[operation.zone] += 1

            elif operation.op == "compose_section":
                if not operation.section_id or not operation.zone:
                    result.errors.append("compose_section requires section_id and zone")
                    continue
                child_widget_ids = operation.child_widget_ids or []
                if len(child_widget_ids) == 0:
                    result.errors.append("compose_section requires non-empty child_widget_ids")
                if len(child_widget_ids) > profile.max_children_per_section:
                    result.errors.append(
                        f"compose_section supports up to {profile.max_children_per_section} child widgets"
                    )
                unknown_children = [wid for wid in child_widget_ids if wid not in planned_widget_ids]
                if unknown_children:
                    result.errors.append(
                        f"compose_section references unknown child widget ids: {', '.join(unknown_children)}"
                    )

            elif operation.op == "set_theme_profile":
                if not operation.profile:
                    result.errors.append("set_theme_profile requires profile")

            elif operation.op == "set_density":
                if not operation.density:
                    result.errors.append("set_density requires density")

            elif operation.op == "set_theme_tokens":
                if not operation.tokens:
                    result.errors.append("set_theme_tokens requires tokens")
                    continue
                PolicyEngine._validate_theme_tokens(operation.tokens, profile.theme_token_allowlist, result)

            elif operation.op == "set_layout_constraints":
                if not operation.layout_constraints:
                    result.errors.append("set_layout_constraints requires layout_constraints")
                    continue
                PolicyEngine._validate_layout_constraints(operation.layout_constraints, profile.layout_constraint_keys, result)

        return result

    @staticmethod
    def _validate_theme_tokens(tokens: dict[str, str], allowlist: frozenset[str], result: PolicyResult) -> None:
        for key, value in tokens.items():
            if key not in allowlist:
                result.errors.append(f"Theme token '{key}' is not allowed")
                continue
            if not isinstance(value, str) or len(value.strip()) == 0:
                result.errors.append(f"Theme token '{key}' must be a non-empty string")

    @staticmethod
    def _validate_layout_constraints(
        layout_constraints: dict[str, Any],
        allowlist: frozenset[str],
        result: PolicyResult,
    ) -> None:
        for key, value in layout_constraints.items():
            if key not in allowlist:
                result.errors.append(f"Layout constraint '{key}' is not allowed")
                continue

            if key == "max_columns":
                if not isinstance(value, int) or value < 1 or value > 4:
                    result.errors.append("layout max_columns must be an integer in range 1..4")

            elif key == "sidebar_width":
                if value not in {"narrow", "normal", "wide"}:
                    result.errors.append("layout sidebar_width must be one of narrow|normal|wide")

            elif key == "content_density":
                if value not in {"comfortable", "compact"}:
                    result.errors.append("layout content_density must be one of comfortable|compact")

            elif key == "emphasis_zone":
                if value not in {"header", "sidebar", "content", "footer"}:
                    result.errors.append("layout emphasis_zone must be one of header|sidebar|content|footer")
