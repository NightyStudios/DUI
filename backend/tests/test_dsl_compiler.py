from __future__ import annotations

import unittest

from backend.app.dsl_compiler import compile_dsl_document_to_manifest
from backend.app.dsl_seed import LESSON_SURFACE_ID, build_seed_document_for_surface
from backend.app.models import DEFAULT_SURFACE_ID


class DuiDslCompilerTests(unittest.TestCase):
    def test_compile_dashboard_seed_document(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        manifest = compile_dsl_document_to_manifest(document, manifest_revision=5)

        self.assertEqual(manifest.revision, 5)
        self.assertGreaterEqual(len(manifest.widgets), 4)
        self.assertTrue(any(widget.id == "course_progress" for widget in manifest.widgets))
        self.assertTrue(any(section.id == "learning_overview" for section in manifest.sections))
        self.assertEqual(manifest.theme.profile, document.theme.profile)

    def test_compile_lesson_seed_document(self) -> None:
        document = build_seed_document_for_surface(LESSON_SURFACE_ID)
        manifest = compile_dsl_document_to_manifest(document, manifest_revision=2)

        self.assertEqual(manifest.revision, 2)
        self.assertEqual(manifest.metadata.get("surface_id"), LESSON_SURFACE_ID)
        self.assertTrue(any(widget.id == "lesson_progress" for widget in manifest.widgets))


if __name__ == "__main__":
    unittest.main()

