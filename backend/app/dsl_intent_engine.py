from __future__ import annotations

import json

from .color_intent import infer_button_theme_tokens
from .dsl_models import DuiDslDocument, DuiDslNode
from .dsl_seed import LESSON_SURFACE_ID
from .llm_gateway import LlmGateway
from .models import DuiMode
from .prompt_rules import (
    infer_layout_constraint_overrides,
    infer_theme_token_overrides,
    normalize_prompt,
    wants_focus_only,
    wants_low_bandwidth,
    wants_sidebar_to_top,
)


class DuiDslIntentEngine:
    @staticmethod
    def build_next_document(
        prompt: str,
        current_document: DuiDslDocument,
        mode: DuiMode = "extended",
    ) -> tuple[DuiDslDocument, list[str]]:
        document, warnings = DuiDslIntentEngine._build_with_llm(prompt, current_document, mode)
        if document is not None:
            return document, warnings

        fallback_document, fallback_warnings = DuiDslIntentEngine._build_rule_based(prompt, current_document, mode)
        return fallback_document, warnings + fallback_warnings

    @staticmethod
    def _build_with_llm(
        prompt: str,
        current_document: DuiDslDocument,
        mode: DuiMode,
    ) -> tuple[DuiDslDocument | None, list[str]]:
        system_prompt = DuiDslIntentEngine._build_system_prompt(current_document, mode)
        user_prompt = (
            "Transform current DUI document according to user request.\n"
            f"User request:\n{prompt}\n\n"
            "Return JSON object with keys: document (full DUI document), warnings (array of strings)."
        )
        result = LlmGateway.completion_json(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=2200)
        if result.data is None:
            return None, result.warnings

        raw_document = result.data.get("document")
        if not isinstance(raw_document, dict):
            return None, ["LLM output does not include valid 'document'. Using DUI rule-based fallback."]

        warnings: list[str] = []
        raw_warnings = result.data.get("warnings")
        if isinstance(raw_warnings, list):
            warnings.extend(str(item) for item in raw_warnings)

        try:
            document = DuiDslDocument.model_validate(raw_document)
            return document, warnings
        except Exception:  # noqa: BLE001
            return None, ["LLM document validation failed. Using DUI rule-based fallback."]

    @staticmethod
    def _build_system_prompt(current_document: DuiDslDocument, mode: DuiMode) -> str:
        context = {
            "mode": mode,
            "surface_id": current_document.surface.id,
            "current_document": current_document.model_dump(mode="json"),
            "rules": [
                "Return JSON only.",
                "Do not include markdown fences.",
                "Keep document syntactically valid DUI document model.",
                "In safe mode, only change theme profile/density/tokens.",
                "Preserve widget/group/page ids when possible.",
                "Preserve node/action/binding ids when legacy node model is present.",
            ],
            "output_schema": {
                "document": "full DUI document object",
                "warnings": "array of strings",
            },
        }
        return (
            "You are an assistant that updates DUI documents based on user intent.\n"
            "Use this context:\n"
            f"{json.dumps(context, ensure_ascii=False)}"
        )

    @staticmethod
    def _build_rule_based(
        prompt: str,
        current_document: DuiDslDocument,
        mode: DuiMode,
    ) -> tuple[DuiDslDocument, list[str]]:
        normalized = normalize_prompt(prompt)
        document = current_document.model_copy(deep=True)
        warnings: list[str] = []
        changed = False

        if any(token in normalized for token in ["миним", "minimal", "минимализм"]):
            document.theme.profile = "minimal"
            changed = True

        if any(token in normalized for token in ["liquid", "glass", "стекл", "гласс"]):
            document.theme.profile = "liquid_glass"
            changed = True

        if any(token in normalized for token in ["default", "классич", "обыч"]):
            document.theme.profile = "default"
            changed = True

        if any(token in normalized for token in ["compact", "компакт", "плотн"]):
            document.theme.density = "compact"
            changed = True

        if any(token in normalized for token in ["comfortable", "простор", "воздух"]):
            document.theme.density = "comfortable"
            changed = True

        theme_tokens = infer_theme_token_overrides(prompt)
        button_theme_tokens = infer_button_theme_tokens(prompt)
        if button_theme_tokens:
            theme_tokens.update(button_theme_tokens)
        if theme_tokens:
            document.theme.tokens.update(theme_tokens)
            changed = True

        layout_overrides = infer_layout_constraint_overrides(prompt)
        if layout_overrides:
            document.layout_constraints.update(layout_overrides)
            changed = True

        if mode in {"extended", "experimental"}:
            if wants_sidebar_to_top(prompt):
                changed = DuiDslIntentEngine._move_node_to_zone(document, node_id="practice_queue", zone="header") or changed

            if any(token in normalized for token in ["убери сайдбар", "hide sidebar", "без сайдбара"]):
                changed = DuiDslIntentEngine._move_node_to_zone(document, node_id="practice_queue", zone="content") or changed
                document.layout_constraints["sidebar_width"] = "narrow"
                changed = True

            if any(token in normalized for token in ["weak topics", "слаб", "слабые темы"]):
                changed = DuiDslIntentEngine._ensure_weak_topics_widget(document) or changed

            if any(token in normalized for token in ["practice section", "секция практика", "секцию практика"]):
                changed = DuiDslIntentEngine._ensure_practice_section(document) or changed

            if any(token in normalized for token in ["фокус на практик", "practice focus", "больше практик"]):
                changed = DuiDslIntentEngine._move_practice_to_content(document) or changed

            if wants_focus_only(prompt):
                changed = DuiDslIntentEngine._move_practice_to_content(document) or changed
                changed = DuiDslIntentEngine._remove_node(document, "learning_path") or changed

            if wants_low_bandwidth(prompt):
                changed = DuiDslIntentEngine._remove_node(document, "mastery_trend") or changed

            if any(token in normalized for token in ["быстрые действия", "quick actions"]):
                changed = (
                    DuiDslIntentEngine._ensure_template_widget(
                        document,
                        node_id="quick_actions_1",
                        node_type="layout.panel",
                        title="Quick Actions",
                        zone="header",
                        template_id="quick_actions",
                        capability_id="math.quick_actions",
                    )
                    or changed
                )

            if any(token in normalized for token in ["формул", "formula"]):
                changed = (
                    DuiDslIntentEngine._ensure_template_widget(
                        document,
                        node_id="formula_cheatsheet_1",
                        node_type="layout.list",
                        title="Formula Cheatsheet",
                        zone="content",
                        template_id="formula_cheatsheet",
                        capability_id="math.formulas",
                    )
                    or changed
                )

            if any(token in normalized for token in ["next lesson", "следующ", "next step"]):
                changed = (
                    DuiDslIntentEngine._ensure_template_widget(
                        document,
                        node_id="next_lesson_card_1",
                        node_type="layout.card",
                        title="Next Lesson",
                        zone="content",
                        template_id="next_lesson_card",
                        capability_id="math.next_lesson",
                    )
                    or changed
                )

            if any(token in normalized for token in ["дедлайн", "deadline", "assignment calendar"]):
                changed = (
                    DuiDslIntentEngine._ensure_template_widget(
                        document,
                        node_id="assignment_calendar_1",
                        node_type="data.data_table",
                        title="Assignment Calendar",
                        zone="content",
                        template_id="assignment_calendar",
                        capability_id="math.assignments",
                    )
                    or changed
                )

            if any(token in normalized for token in ["focus timer", "таймер", "pomodoro"]):
                changed = (
                    DuiDslIntentEngine._ensure_template_widget(
                        document,
                        node_id="focus_timer_1",
                        node_type="layout.card",
                        title="Focus Timer",
                        zone="content",
                        template_id="focus_timer",
                        capability_id="math.focus_timer",
                    )
                    or changed
                )

            if any(token in normalized for token in ["streak", "геймифик", "gamif"]):
                changed = (
                    DuiDslIntentEngine._ensure_template_widget(
                        document,
                        node_id="study_streak_panel_1",
                        node_type="layout.panel",
                        title="Study Streak",
                        zone="header",
                        template_id="study_streak_panel",
                        capability_id="math.study_streak",
                    )
                    or changed
                )

            if any(token in normalized for token in ["mentor review", "менторск", "менторского ревью"]):
                changed = DuiDslIntentEngine._ensure_mentor_review_section(document) or changed

        if not changed:
            warnings.append(
                "DUI intent fallback did not detect known commands. Try: minimal, compact, make buttons #ccff00, weak topics, practice section."
            )

        if document.surface.id == LESSON_SURFACE_ID and mode == "safe":
            # Example safety nudge for lesson surface.
            warnings.append("Safe mode on lesson surface keeps structure unchanged.")

        return document, warnings

    @staticmethod
    def _find_node(document: DuiDslDocument, node_id: str) -> DuiDslNode | None:
        for node in document.nodes:
            if node.id == node_id:
                return node
        return None

    @staticmethod
    def _find_region(document: DuiDslDocument, zone: str) -> DuiDslNode | None:
        for node in document.nodes:
            if node.type == "layout.region" and node.props.get("zone") == zone:
                return node
        return None

    @staticmethod
    def _ensure_weak_topics_widget(document: DuiDslDocument) -> bool:
        if DuiDslIntentEngine._find_node(document, "weak_topics_list_1") is not None:
            return False

        document.nodes.append(
            DuiDslNode(
                id="weak_topics_list_1",
                type="lms.weak_topics_list",
                props={
                    "title": "Weak Topics",
                    "zone": "sidebar",
                    "capability_id": "math.weak_topics",
                },
            )
        )
        sidebar = DuiDslIntentEngine._find_region(document, "sidebar")
        if sidebar and "weak_topics_list_1" not in sidebar.children:
            sidebar.children.append("weak_topics_list_1")
        return True

    @staticmethod
    def _ensure_practice_section(document: DuiDslDocument) -> bool:
        if DuiDslIntentEngine._find_node(document, "practice_focus") is not None:
            return False

        if DuiDslIntentEngine._find_node(document, "practice_queue") is None:
            return False

        if DuiDslIntentEngine._find_node(document, "mastery_trend") is None:
            return False

        section = DuiDslNode(
            id="practice_focus",
            type="layout.section",
            props={"title": "Practice Focus", "zone": "content"},
            layout={"columns": 2},
            children=["practice_queue", "mastery_trend"],
        )
        document.nodes.append(section)

        content = DuiDslIntentEngine._find_region(document, "content")
        if content and "practice_focus" not in content.children:
            content.children.append("practice_focus")
        return True

    @staticmethod
    def _ensure_mentor_review_section(document: DuiDslDocument) -> bool:
        if DuiDslIntentEngine._find_node(document, "mentor_review") is not None:
            return False

        if DuiDslIntentEngine._find_node(document, "learning_path") is None:
            return False
        if DuiDslIntentEngine._find_node(document, "practice_queue") is None:
            return False

        changed = DuiDslIntentEngine._move_node_to_zone(document, node_id="practice_queue", zone="content")

        section = DuiDslNode(
            id="mentor_review",
            type="layout.section",
            props={"title": "Mentor Review", "zone": "content"},
            layout={"columns": 2},
            children=["learning_path", "practice_queue"],
        )
        document.nodes.append(section)
        changed = True
        content = DuiDslIntentEngine._find_region(document, "content")
        if content and "mentor_review" not in content.children:
            content.children.append("mentor_review")
            changed = True
        return changed

    @staticmethod
    def _move_practice_to_content(document: DuiDslDocument) -> bool:
        return DuiDslIntentEngine._move_node_to_zone(document, node_id="practice_queue", zone="content")

    @staticmethod
    def _move_node_to_zone(document: DuiDslDocument, *, node_id: str, zone: str) -> bool:
        node = DuiDslIntentEngine._find_node(document, node_id)
        if node is None:
            return False

        changed = False
        if node.props.get("zone") != zone:
            node.props["zone"] = zone
            changed = True

        for region in document.nodes:
            if region.type != "layout.region":
                continue
            if node_id in region.children and region.props.get("zone") != zone:
                region.children = [child for child in region.children if child != node_id]
                changed = True

        target_region = DuiDslIntentEngine._find_region(document, zone)
        if target_region and node_id not in target_region.children:
            target_region.children.append(node_id)
            changed = True

        return changed

    @staticmethod
    def _remove_node(document: DuiDslDocument, node_id: str) -> bool:
        if DuiDslIntentEngine._find_node(document, node_id) is None:
            return False

        changed = False
        next_nodes: list[DuiDslNode] = []
        for node in document.nodes:
            if node.id == node_id:
                changed = True
                continue

            if node_id in node.children:
                node.children = [child for child in node.children if child != node_id]
                changed = True

            for slot_name, slot_children in node.slots.items():
                if node_id in slot_children:
                    node.slots[slot_name] = [child for child in slot_children if child != node_id]
                    changed = True

            next_nodes.append(node)

        document.nodes = next_nodes
        return changed

    @staticmethod
    def _ensure_template_widget(
        document: DuiDslDocument,
        *,
        node_id: str,
        node_type: str,
        title: str,
        zone: str,
        template_id: str,
        capability_id: str,
    ) -> bool:
        existing = DuiDslIntentEngine._find_node(document, node_id)
        if existing is not None:
            return DuiDslIntentEngine._move_node_to_zone(document, node_id=node_id, zone=zone)

        document.nodes.append(
            DuiDslNode(
                id=node_id,
                type=node_type,
                props={
                    "title": title,
                    "zone": zone,
                    "template_id": template_id,
                    "capability_id": capability_id,
                },
            )
        )
        region = DuiDslIntentEngine._find_region(document, zone)
        if region and node_id not in region.children:
            region.children.append(node_id)
        return True
