from __future__ import annotations

import unittest

from backend.app.dsl_compiler import compile_dsl_document_to_manifest
from backend.app.dsl_patch_service import apply_patch_operations_to_document
from backend.app.dsl_seed import build_seed_document_for_surface
from backend.app.manifest_service import apply_patch_operations
from backend.app.models import DEFAULT_SURFACE_ID, PatchOperation


class DuiDslPatchServiceTests(unittest.TestCase):
    def test_apply_move_widget_updates_canonical_group_and_manifest(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        operations = [PatchOperation(op="move_widget", widget_id="practice_queue", zone="header")]

        updated_document = apply_patch_operations_to_document(document, operations)
        practice_queue = next(widget for widget in updated_document.widgets if widget.id == "practice_queue")
        header_group = next(group for group in updated_document.groups if group.zone == "header")
        compiled_manifest = compile_dsl_document_to_manifest(updated_document, manifest_revision=1)

        self.assertEqual(practice_queue.zone, "header")
        self.assertEqual(practice_queue.group_id, header_group.id)
        self.assertIn("practice_queue", header_group.widget_ids)
        self.assertEqual(
            next(widget for widget in compiled_manifest.widgets if widget.id == "practice_queue").zone,
            "header",
        )

    def test_apply_compose_section_matches_manifest_patch_shape(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        manifest = compile_dsl_document_to_manifest(document, manifest_revision=1)
        operations = [
            PatchOperation(op="move_widget", widget_id="practice_queue", zone="content"),
            PatchOperation(
                op="compose_section",
                section_id="mentor_review",
                section_title="Mentor Review",
                zone="content",
                child_widget_ids=["learning_path", "practice_queue"],
                section_layout={"columns": 2},
            ),
        ]

        updated_document = apply_patch_operations_to_document(document, operations)
        updated_manifest = compile_dsl_document_to_manifest(updated_document, manifest_revision=1)
        patched_manifest = apply_patch_operations(manifest, operations)

        mentor_group = next(group for group in updated_document.groups if group.id == "mentor_review")
        self.assertEqual(mentor_group.widget_ids, ["learning_path", "practice_queue"])

        updated_section = next(section for section in updated_manifest.sections if section.id == "mentor_review")
        patched_section = next(section for section in patched_manifest.sections if section.id == "mentor_review")
        self.assertEqual(updated_section.zone, patched_section.zone)
        self.assertEqual(updated_section.child_widget_ids, patched_section.child_widget_ids)
        self.assertEqual(updated_section.layout, patched_section.layout)

    def test_apply_add_widget_from_template_creates_widget_and_membership(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        operations = [
            PatchOperation(
                op="add_widget_from_template",
                template_id="quick_actions",
                widget_id="quick_actions_1",
                zone="header",
            )
        ]

        updated_document = apply_patch_operations_to_document(document, operations)
        widget = next(widget for widget in updated_document.widgets if widget.id == "quick_actions_1")
        header_group = next(group for group in updated_document.groups if group.zone == "header")

        self.assertEqual(widget.template_id, "quick_actions")
        self.assertEqual(widget.group_id, header_group.id)
        self.assertIn("quick_actions_1", header_group.widget_ids)


if __name__ == "__main__":
    unittest.main()
