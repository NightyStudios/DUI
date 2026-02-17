from __future__ import annotations

import json
import os
import unittest
import urllib.error
import urllib.request

from backend.app.main import STORE, build_intent
from backend.app.models import DEFAULT_SURFACE_ID


def _tags_url_from_base(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        base = base[: -len("/v1")]
    return f"{base}/api/tags"


class LiveLlmPromptTests(unittest.TestCase):
    """Live tests for model-generated DUI intents.

    Opt-in only. Enable with DUI_LIVE_LLM_TESTS=1.
    """

    @classmethod
    def setUpClass(cls) -> None:
        if os.getenv("DUI_LIVE_LLM_TESTS", "0") != "1":
            raise unittest.SkipTest("Set DUI_LIVE_LLM_TESTS=1 to run live LLM prompt tests.")

        os.environ["DUI_LLM_PROVIDER"] = "local"
        os.environ.setdefault("DUI_LLM_BASE_URL", "http://127.0.0.1:11434/v1")
        os.environ.setdefault("DUI_LLM_MODEL", "qwen2.5:14b-instruct")

        model_name = os.environ["DUI_LLM_MODEL"]
        tags_url = _tags_url_from_base(os.environ["DUI_LLM_BASE_URL"])

        try:
            with urllib.request.urlopen(tags_url, timeout=5) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise unittest.SkipTest(f"Local Ollama API is unavailable: {type(error).__name__}") from error

        models = payload.get("models", [])
        if not isinstance(models, list):
            raise unittest.SkipTest("Unexpected /api/tags payload from Ollama")

        model_names = {item.get("name") for item in models if isinstance(item, dict)}
        if model_name not in model_names:
            raise unittest.SkipTest(f"Model '{model_name}' is not present in local Ollama tags")

    def setUp(self) -> None:
        STORE.reset_to_seed()

    def _assert_generated_by_model(self, warnings: list[str]) -> None:
        all_warnings = " ".join(warnings).lower()
        self.assertNotIn("fallback", all_warnings, msg=f"Expected model generation, got warnings: {warnings}")

    def test_prompt_glassmorphism_generates_theme_changes(self) -> None:
        response = build_intent(
            user_prompt="Сделай глассморфизм: стеклянные полупрозрачные поверхности и мягкий blur",
            current_manifest_id=None,
            mode="extended",
            surface_id=DEFAULT_SURFACE_ID,
            session_id="live-llm-tests",
            turn_id="turn-live-glass",
        )

        warnings = [*response.patch_plan.warnings, *response.warnings]
        self._assert_generated_by_model(warnings)

        operations = response.patch_plan.operations
        theme_ops = [operation for operation in operations if operation.op in {"set_theme_profile", "set_theme_tokens", "set_density"}]
        self.assertTrue(theme_ops, msg=f"Expected theme-changing ops, got: {[op.op for op in operations]}")

        has_liquid_glass = any(
            operation.op == "set_theme_profile" and operation.profile == "liquid_glass"
            for operation in operations
        )
        if not has_liquid_glass:
            token_values: list[str] = []
            for operation in operations:
                if operation.op == "set_theme_tokens" and operation.tokens:
                    token_values.extend(str(value).lower() for value in operation.tokens.values())
            token_text = " ".join(token_values)
            self.assertTrue(
                ("rgba" in token_text) or ("glass" in token_text) or ("blur" in token_text),
                msg=f"Expected glass-like theme output, operations: {operations}",
            )

    def test_prompt_sidebar_on_top_generates_layout_changes(self) -> None:
        response = build_intent(
            user_prompt=(
                "Поменяй лэйаут так, чтобы главный сайдбар был сверху: "
                "перемести главный блок из sidebar в header"
            ),
            current_manifest_id=None,
            mode="extended",
            surface_id=DEFAULT_SURFACE_ID,
            session_id="live-llm-tests",
            turn_id="turn-live-layout",
        )

        warnings = [*response.patch_plan.warnings, *response.warnings]
        self._assert_generated_by_model(warnings)

        operations = response.patch_plan.operations
        layout_ops = [
            operation
            for operation in operations
            if operation.op in {"move_widget", "set_layout_constraints", "compose_section"}
        ]
        self.assertTrue(layout_ops, msg=f"Expected layout-changing ops, got: {[op.op for op in operations]}")

        targets_header = any(operation.op == "move_widget" and operation.zone == "header" for operation in layout_ops) or any(
            operation.op == "set_layout_constraints"
            and operation.layout_constraints
            and operation.layout_constraints.get("emphasis_zone") == "header"
            for operation in layout_ops
        )
        self.assertTrue(
            targets_header,
            msg=f"Expected layout output targeting header/top, got operations: {operations}",
        )


if __name__ == "__main__":
    unittest.main()
