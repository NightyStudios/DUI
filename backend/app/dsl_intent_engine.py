from __future__ import annotations

import json

from .llm_gateway import LlmGateway
from .dsl_models import DuiDslDocument, DuiDslNode
from .dsl_seed import LESSON_SURFACE_ID
from .models import DuiMode


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
                "Preserve node/action/binding ids when possible.",
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
        normalized = prompt.lower().strip()
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

        if ("кнопк" in normalized or "button" in normalized) and any(
            token in normalized for token in ["красн", "red", "красный", "красные"]
        ):
            document.theme.tokens["accent"] = "#dc2626"
            document.theme.tokens["accent_container"] = "#fee2e2"
            changed = True

        if mode in {"extended", "experimental"}:
            if any(token in normalized for token in ["weak topics", "слаб", "слабые темы"]):
                changed = DuiDslIntentEngine._ensure_weak_topics_widget(document) or changed

            if any(token in normalized for token in ["practice section", "секция практика"]):
                changed = DuiDslIntentEngine._ensure_practice_section(document) or changed

            if any(token in normalized for token in ["фокус на практик", "practice focus", "больше практик"]):
                changed = DuiDslIntentEngine._move_practice_to_content(document) or changed

        if not changed:
            warnings.append(
                "DUI intent fallback did not detect known commands. Try: minimal, compact, weak topics, practice section."
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
    def _move_practice_to_content(document: DuiDslDocument) -> bool:
        node = DuiDslIntentEngine._find_node(document, "practice_queue")
        if node is None:
            return False

        changed = False
        if node.props.get("zone") != "content":
            node.props["zone"] = "content"
            changed = True

        sidebar = DuiDslIntentEngine._find_region(document, "sidebar")
        content = DuiDslIntentEngine._find_region(document, "content")
        if sidebar and "practice_queue" in sidebar.children:
            sidebar.children = [child for child in sidebar.children if child != "practice_queue"]
            changed = True
        if content and "practice_queue" not in content.children:
            content.children.append("practice_queue")
            changed = True
        return changed
