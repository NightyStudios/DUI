from __future__ import annotations

import json
from uuid import uuid4

from .color_intent import infer_button_theme_tokens
from .llm_gateway import LlmGateway
from .models import DuiMode, PatchOperation, UiManifest, UiPatchPlan
from .prompt_rules import (
    infer_layout_constraint_overrides,
    infer_theme_token_overrides,
    normalize_prompt,
    wants_focus_only,
    wants_low_bandwidth,
    wants_sidebar_to_top,
)
from .template_catalog import template_ids


class IntentEngine:
    """Hybrid intent parser for v1 PoC.

    - Primary path: APIFree OpenAI-compatible chat completions.
    - Fallback path: deterministic rule-based parser.
    """

    @staticmethod
    def build_patch_plan(prompt: str, manifest: UiManifest, mode: DuiMode = "extended") -> UiPatchPlan:
        operations, warnings = IntentEngine._build_patch_plan_with_llm(prompt, manifest, mode)
        if operations is None:
            fallback_operations, fallback_warnings = IntentEngine._build_patch_plan_rule_based(prompt, manifest, mode)
            merged_warnings = warnings + fallback_warnings
            return UiPatchPlan(
                patch_plan_id=str(uuid4()),
                user_prompt=prompt,
                mode=mode,
                operations=fallback_operations,
                warnings=merged_warnings,
            )

        if not operations:
            fallback_operations, fallback_warnings = IntentEngine._build_patch_plan_rule_based(prompt, manifest, mode)
            merged_warnings = warnings + ["LLM produced no operations. Applied rule-based fallback."] + fallback_warnings
            return UiPatchPlan(
                patch_plan_id=str(uuid4()),
                user_prompt=prompt,
                mode=mode,
                operations=fallback_operations,
                warnings=merged_warnings,
            )

        return UiPatchPlan(
            patch_plan_id=str(uuid4()),
            user_prompt=prompt,
            mode=mode,
            operations=operations,
            warnings=warnings,
        )

    @staticmethod
    def _build_patch_plan_with_llm(
        prompt: str,
        manifest: UiManifest,
        mode: DuiMode,
    ) -> tuple[list[PatchOperation] | None, list[str]]:
        system_prompt = IntentEngine._build_system_prompt(manifest, mode)
        user_prompt = (
            "User request for DUI changes:\n"
            f"{prompt}\n\n"
            "Return a JSON object with keys: operations (array), warnings (array)."
        )
        result = LlmGateway.completion_json(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=1000)
        if result.data is None:
            return None, result.warnings

        raw_operations = result.data.get("operations", [])
        raw_warnings = result.data.get("warnings", [])
        operations, parse_warnings = IntentEngine._coerce_operations(raw_operations)

        warnings: list[str] = []
        if isinstance(raw_warnings, list):
            warnings.extend(str(item) for item in raw_warnings)
        warnings.extend(parse_warnings)

        if not operations:
            warnings.append("LLM returned no valid operations.")

        return operations, warnings

    @staticmethod
    def _coerce_operations(raw_operations: object) -> tuple[list[PatchOperation], list[str]]:
        if not isinstance(raw_operations, list):
            return [], ["LLM operations field is not an array."]

        operations: list[PatchOperation] = []
        warnings: list[str] = []

        for index, raw_operation in enumerate(raw_operations):
            if not isinstance(raw_operation, dict):
                warnings.append(f"Operation {index} ignored: expected object.")
                continue

            try:
                operation = PatchOperation.model_validate(raw_operation)
                operations.append(operation)
            except Exception:  # noqa: BLE001
                warnings.append(f"Operation {index} ignored: schema validation failed.")

        return operations, warnings

    @staticmethod
    def _allowed_ops(mode: DuiMode) -> list[dict[str, object]]:
        safe_ops: list[dict[str, object]] = [
            {
                "op": "set_theme_profile",
                "profile": ["default", "minimal", "liquid_glass"],
            },
            {
                "op": "set_density",
                "density": ["comfortable", "compact"],
            },
            {
                "op": "move_widget",
                "widget_id": "existing widget id",
                "zone": ["header", "sidebar", "content", "footer"],
            },
            {
                "op": "remove_widget",
                "widget_id": "existing widget id that is not protected",
            },
        ]

        if mode == "safe":
            return safe_ops

        extended_ops = safe_ops + [
            {
                "op": "set_theme_tokens",
                "tokens": {
                    "surface": "string color",
                    "accent": "string color",
                    "radius": "string with px",
                },
            },
            {
                "op": "set_layout_constraints",
                "layout_constraints": {
                    "max_columns": "int 1..4",
                    "sidebar_width": "narrow|normal|wide",
                    "content_density": "comfortable|compact",
                    "emphasis_zone": "header|sidebar|content|footer",
                },
            },
            {
                "op": "add_widget_from_template",
                "template_id": template_ids(),
                "widget_id": "new unique id",
                "title": "optional title",
                "zone": ["header", "sidebar", "content", "footer"],
                "capability_id": "optional capability override",
                "props": "optional object",
            },
            {
                "op": "compose_section",
                "section_id": "new or existing section id",
                "section_title": "optional title",
                "zone": ["header", "sidebar", "content", "footer"],
                "child_widget_ids": "array of widget ids",
                "section_layout": "optional layout object",
            },
        ]

        if mode == "experimental":
            return extended_ops + [
                {
                    "op": "add_widget",
                    "widget": "full WidgetConfig object",
                }
            ]

        return extended_ops

    @staticmethod
    def _build_system_prompt(manifest: UiManifest, mode: DuiMode) -> str:
        widgets = [
            {
                "id": widget.id,
                "title": widget.title,
                "zone": widget.zone,
                "protected": widget.protected,
                "template_id": widget.template_id,
            }
            for widget in manifest.widgets
        ]
        sections = [
            {
                "id": section.id,
                "zone": section.zone,
                "child_widget_ids": section.child_widget_ids,
            }
            for section in manifest.sections
        ]

        context = {
            "mode": mode,
            "theme": {
                "profile": manifest.theme.profile,
                "density": manifest.theme.density,
            },
            "widgets": widgets,
            "sections": sections,
            "layout_constraints": manifest.layout_constraints,
            "allowed_ops": IntentEngine._allowed_ops(mode),
            "rules": [
                "Return JSON only.",
                "Do not include markdown fences.",
                "Do not use unknown operations.",
                "Never remove protected widgets.",
                "Only use widget ids that exist or are created in this patch.",
            ],
            "output_schema": {
                "operations": "array of operation objects",
                "warnings": "array of strings",
            },
        }

        return (
            "You are an assistant that converts natural language UI requests into safe DUI patch operations.\n"
            "Use this context:\n"
            f"{json.dumps(context, ensure_ascii=False)}"
        )

    @staticmethod
    def _build_patch_plan_rule_based(
        prompt: str,
        manifest: UiManifest,
        mode: DuiMode,
    ) -> tuple[list[PatchOperation], list[str]]:
        normalized = normalize_prompt(prompt)
        operations: list[PatchOperation] = []
        warnings: list[str] = []
        existing_widget_ids = {widget.id for widget in manifest.widgets}

        if any(token in normalized for token in ["миним", "minimal", "минимализм"]):
            operations.append(PatchOperation(op="set_theme_profile", profile="minimal"))

        if any(token in normalized for token in ["liquid", "glass", "стекл", "гласс"]):
            operations.append(PatchOperation(op="set_theme_profile", profile="liquid_glass"))

        if any(token in normalized for token in ["default", "обыч", "классич"]):
            operations.append(PatchOperation(op="set_theme_profile", profile="default"))

        if any(token in normalized for token in ["compact", "компакт", "плотн"]):
            operations.append(PatchOperation(op="set_density", density="compact"))

        if any(token in normalized for token in ["простор", "comfortable", "воздух"]):
            operations.append(PatchOperation(op="set_density", density="comfortable"))

        hide_sidebar_requested = any(token in normalized for token in ["убери сайдбар", "hide sidebar", "без сайдбара"])
        if hide_sidebar_requested:
            sidebar_widget_ids = [widget.id for widget in manifest.widgets if widget.zone == "sidebar"]
            for widget_id in sidebar_widget_ids:
                operations.append(PatchOperation(op="move_widget", widget_id=widget_id, zone="content"))

        if any(token in normalized for token in ["фокус на практик", "practice focus", "больше практик"]):
            operations.append(PatchOperation(op="move_widget", widget_id="practice_queue", zone="content"))
            operations.append(PatchOperation(op="move_widget", widget_id="learning_path", zone="sidebar"))

        if mode in {"extended", "experimental"}:
            theme_tokens = infer_theme_token_overrides(prompt)
            button_theme_tokens = infer_button_theme_tokens(prompt)
            if button_theme_tokens:
                theme_tokens.update(button_theme_tokens)
            if theme_tokens:
                operations.append(PatchOperation(op="set_theme_tokens", tokens=theme_tokens))

            layout_constraints = infer_layout_constraint_overrides(prompt)
            if layout_constraints:
                operations.append(PatchOperation(op="set_layout_constraints", layout_constraints=layout_constraints))

            if hide_sidebar_requested:
                operations.append(
                    PatchOperation(op="set_layout_constraints", layout_constraints={"sidebar_width": "narrow"})
                )

            if wants_sidebar_to_top(prompt):
                operations.append(PatchOperation(op="move_widget", widget_id="practice_queue", zone="header"))

            if wants_focus_only(prompt):
                operations.append(PatchOperation(op="move_widget", widget_id="practice_queue", zone="content"))

            if wants_low_bandwidth(prompt):
                operations.append(PatchOperation(op="remove_widget", widget_id="mastery_trend"))

            if any(token in normalized for token in ["добавь слаб", "weak topic", "weak topics", "слабые темы"]):
                widget_id = IntentEngine._next_available_widget_id(existing_widget_ids, "weak_topics_list_1")
                existing_widget_ids.add(widget_id)
                operations.append(
                    PatchOperation(
                        op="add_widget_from_template",
                        template_id="weak_topics_list",
                        widget_id=widget_id,
                        zone="sidebar",
                        title="Weak Topics",
                    )
                )

            if any(token in normalized for token in ["быстрые действия", "quick actions"]):
                widget_id = IntentEngine._next_available_widget_id(existing_widget_ids, "quick_actions_1")
                existing_widget_ids.add(widget_id)
                operations.append(
                    PatchOperation(
                        op="add_widget_from_template",
                        template_id="quick_actions",
                        widget_id=widget_id,
                        zone="header",
                    )
                )

            if any(token in normalized for token in ["формул", "formula"]):
                formula_widget_id = IntentEngine._next_available_widget_id(existing_widget_ids, "formula_cheatsheet_1")
                existing_widget_ids.add(formula_widget_id)
                operations.append(
                    PatchOperation(
                        op="add_widget_from_template",
                        template_id="formula_cheatsheet",
                        widget_id=formula_widget_id,
                        zone="content",
                    )
                )

            if any(token in normalized for token in ["next lesson", "следующ", "next step"]):
                lesson_widget_id = IntentEngine._next_available_widget_id(existing_widget_ids, "next_lesson_card_1")
                existing_widget_ids.add(lesson_widget_id)
                operations.append(
                    PatchOperation(
                        op="add_widget_from_template",
                        template_id="next_lesson_card",
                        widget_id=lesson_widget_id,
                        zone="content",
                    )
                )

            if any(token in normalized for token in ["дедлайн", "deadline", "assignment calendar"]):
                assignment_widget_id = IntentEngine._next_available_widget_id(existing_widget_ids, "assignment_calendar_1")
                existing_widget_ids.add(assignment_widget_id)
                operations.append(
                    PatchOperation(
                        op="add_widget_from_template",
                        template_id="assignment_calendar",
                        widget_id=assignment_widget_id,
                        zone="content",
                    )
                )

            if any(token in normalized for token in ["focus timer", "таймер", "pomodoro"]):
                focus_widget_id = IntentEngine._next_available_widget_id(existing_widget_ids, "focus_timer_1")
                existing_widget_ids.add(focus_widget_id)
                operations.append(
                    PatchOperation(
                        op="add_widget_from_template",
                        template_id="focus_timer",
                        widget_id=focus_widget_id,
                        zone="content",
                    )
                )

            if any(token in normalized for token in ["streak", "геймифик", "gamif"]):
                streak_widget_id = IntentEngine._next_available_widget_id(existing_widget_ids, "study_streak_panel_1")
                existing_widget_ids.add(streak_widget_id)
                operations.append(
                    PatchOperation(
                        op="add_widget_from_template",
                        template_id="study_streak_panel",
                        widget_id=streak_widget_id,
                        zone="header",
                    )
                )

            if any(token in normalized for token in ["секция практика", "секцию практика", "practice section"]):
                operations.append(
                    PatchOperation(
                        op="compose_section",
                        section_id="practice_focus",
                        section_title="Practice Focus",
                        zone="content",
                        child_widget_ids=["practice_queue", "mastery_trend"],
                        section_layout={"columns": 2},
                    )
                )

            if any(token in normalized for token in ["mentor review", "менторск", "менторского ревью"]):
                operations.append(PatchOperation(op="move_widget", widget_id="practice_queue", zone="content"))
                operations.append(
                    PatchOperation(
                        op="compose_section",
                        section_id="mentor_review",
                        section_title="Mentor Review",
                        zone="content",
                        child_widget_ids=["learning_path", "practice_queue"],
                        section_layout={"columns": 2},
                    )
                )

        if not operations:
            warnings.append(
                "Intent parser fallback did not detect commands. Try: minimal, compact, make buttons #ccff00, hide sidebar, weak topics, practice section."
            )

        return operations, warnings

    @staticmethod
    def _next_available_widget_id(existing_widget_ids: set[str], preferred_id: str) -> str:
        if preferred_id not in existing_widget_ids:
            return preferred_id

        stem = preferred_id
        if "_" in preferred_id:
            prefix, maybe_suffix = preferred_id.rsplit("_", 1)
            if maybe_suffix.isdigit():
                stem = prefix
        suffix = 2
        while f"{stem}_{suffix}" in existing_widget_ids:
            suffix += 1
        return f"{stem}_{suffix}"
