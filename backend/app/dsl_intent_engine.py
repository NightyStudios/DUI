from __future__ import annotations

import json
import os

import httpx

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
        api_key = os.getenv("APIFREE_API_KEY")
        if not api_key:
            return None, ["APIFREE_API_KEY is not set. Using DSL rule-based fallback."]

        base_url = os.getenv("APIFREE_BASE_URL", "https://api.apifree.ai/v1").rstrip("/")
        model = os.getenv("APIFREE_MODEL", "deepseek-ai/deepseek-r1-0528")
        timeout_seconds = float(os.getenv("APIFREE_TIMEOUT_SEC", "60"))

        system_prompt = DuiDslIntentEngine._build_system_prompt(current_document, mode)
        user_prompt = (
            "Transform current DUI-Lang document according to user request.\n"
            f"User request:\n{prompt}\n\n"
            "Return JSON object with keys: document (full DUI-Lang document), warnings (array of strings)."
        )
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2200,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                if response.status_code >= 400:
                    fallback_payload = dict(payload)
                    fallback_payload.pop("response_format", None)
                    response = client.post(f"{base_url}/chat/completions", headers=headers, json=fallback_payload)
                response.raise_for_status()

            body = response.json()
            content = DuiDslIntentEngine._extract_assistant_content(body)
            if not content:
                return None, ["APIFree returned empty content. Using DSL rule-based fallback."]

            parsed = DuiDslIntentEngine._parse_json(content)
            if parsed is None or not isinstance(parsed, dict):
                return None, ["Failed to parse LLM JSON output. Using DSL rule-based fallback."]

            raw_document = parsed.get("document")
            if not isinstance(raw_document, dict):
                return None, ["LLM output does not include valid 'document'. Using DSL rule-based fallback."]

            warnings: list[str] = []
            raw_warnings = parsed.get("warnings")
            if isinstance(raw_warnings, list):
                warnings.extend(str(item) for item in raw_warnings)

            try:
                document = DuiDslDocument.model_validate(raw_document)
                return document, warnings
            except Exception:  # noqa: BLE001
                return None, ["LLM document validation failed. Using DSL rule-based fallback."]
        except Exception as error:  # noqa: BLE001
            return None, [f"APIFree DSL intent failed ({type(error).__name__}). Using rule-based fallback."]

    @staticmethod
    def _extract_assistant_content(body: dict) -> str | None:
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            return None

        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
            return "\n".join(chunks) if chunks else None
        return None

    @staticmethod
    def _parse_json(content: str) -> dict | None:
        stripped = content.strip()
        if stripped.startswith("```"):
            stripped = stripped.removeprefix("```json").removeprefix("```")
            if stripped.endswith("```"):
                stripped = stripped[:-3]
            stripped = stripped.strip()
        try:
            parsed = json.loads(stripped)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _build_system_prompt(current_document: DuiDslDocument, mode: DuiMode) -> str:
        context = {
            "mode": mode,
            "surface_id": current_document.surface.id,
            "current_document": current_document.model_dump(mode="json"),
            "rules": [
                "Return JSON only.",
                "Do not include markdown fences.",
                "Keep document syntactically valid DUI-Lang document model.",
                "In safe mode, only change theme profile/density/tokens.",
                "Preserve node/action/binding ids when possible.",
            ],
            "output_schema": {
                "document": "full DUI-Lang document object",
                "warnings": "array of strings",
            },
        }
        return (
            "You are an assistant that updates DUI-Lang documents based on user intent.\n"
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

        if mode in {"extended", "experimental"}:
            if any(token in normalized for token in ["weak topics", "слаб", "слабые темы"]):
                changed = DuiDslIntentEngine._ensure_weak_topics_widget(document) or changed

            if any(token in normalized for token in ["practice section", "секция практика"]):
                changed = DuiDslIntentEngine._ensure_practice_section(document) or changed

            if any(token in normalized for token in ["фокус на практик", "practice focus", "больше практик"]):
                changed = DuiDslIntentEngine._move_practice_to_content(document) or changed

        if not changed:
            warnings.append(
                "DSL intent fallback did not detect known commands. Try: minimal, compact, weak topics, practice section."
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

