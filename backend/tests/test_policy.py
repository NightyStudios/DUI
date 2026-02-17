from __future__ import annotations

import unittest

from backend.app.main import STORE
from backend.app.models import PatchOperation
from backend.app.policy import PolicyEngine


class PolicyEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        STORE.reset_to_seed()

    def test_compose_section_rejects_children_removed_in_same_patch(self) -> None:
        manifest = STORE.get_current_manifest()
        operations = [
            PatchOperation(op="remove_widget", widget_id="practice_queue"),
            PatchOperation(
                op="compose_section",
                section_id="practice_focus",
                zone="content",
                child_widget_ids=["practice_queue", "mastery_trend"],
            ),
        ]

        result = PolicyEngine.validate_operations(manifest, operations, mode="extended")

        self.assertTrue(result.errors)
        self.assertTrue(
            any("unknown child widget ids" in error and "practice_queue" in error for error in result.errors),
            msg=f"Unexpected errors: {result.errors}",
        )


if __name__ == "__main__":
    unittest.main()
