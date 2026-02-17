from __future__ import annotations

from dataclasses import dataclass

from .manifest_service import PROFILE_TOKENS
from .models import DuiMode


@dataclass(frozen=True)
class PolicyProfile:
    allowed_ops: frozenset[str]
    theme_token_allowlist: frozenset[str]
    layout_constraint_keys: frozenset[str]
    max_widgets_per_zone: int
    max_children_per_section: int


_BASE_THEME_TOKENS = frozenset(PROFILE_TOKENS["default"].keys()) | frozenset({"gap", "padding", "row_height"})
_LAYOUT_KEYS = frozenset({"max_columns", "sidebar_width", "content_density", "emphasis_zone"})

POLICY_PROFILES: dict[DuiMode, PolicyProfile] = {
    "safe": PolicyProfile(
        allowed_ops=frozenset(
            {
                "set_theme_profile",
                "set_density",
                "move_widget",
                "remove_widget",
            }
        ),
        theme_token_allowlist=_BASE_THEME_TOKENS,
        layout_constraint_keys=_LAYOUT_KEYS,
        max_widgets_per_zone=8,
        max_children_per_section=6,
    ),
    "extended": PolicyProfile(
        allowed_ops=frozenset(
            {
                "set_theme_profile",
                "set_density",
                "set_theme_tokens",
                "set_layout_constraints",
                "move_widget",
                "remove_widget",
                "add_widget_from_template",
                "compose_section",
            }
        ),
        theme_token_allowlist=_BASE_THEME_TOKENS,
        layout_constraint_keys=_LAYOUT_KEYS,
        max_widgets_per_zone=8,
        max_children_per_section=6,
    ),
    "experimental": PolicyProfile(
        allowed_ops=frozenset(
            {
                "set_theme_profile",
                "set_density",
                "set_theme_tokens",
                "set_layout_constraints",
                "move_widget",
                "remove_widget",
                "add_widget",
                "add_widget_from_template",
                "compose_section",
            }
        ),
        theme_token_allowlist=_BASE_THEME_TOKENS,
        layout_constraint_keys=_LAYOUT_KEYS,
        max_widgets_per_zone=8,
        max_children_per_section=6,
    ),
}
