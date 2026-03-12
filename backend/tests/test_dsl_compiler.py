from __future__ import annotations

import unittest

from backend.app.dsl_compiler import compile_dsl_document_to_manifest
from backend.app.dsl_seed import LESSON_SURFACE_ID, build_seed_document_for_surface
from backend.app.dsl_text_parser import parse_dui_lang
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

    def test_compile_derives_sidebar_collapse_hints_from_dsl(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        sidebar_group = next(group for group in document.groups if group.zone == "sidebar")
        sidebar_group.behavior["collapsible"] = True
        sidebar_group.behavior["collapsed"] = True

        manifest = compile_dsl_document_to_manifest(document, manifest_revision=3)
        self.assertEqual(manifest.layout_constraints.get("sidebar_collapsible"), True)
        self.assertEqual(manifest.layout_constraints.get("sidebar_collapsed_initial"), True)

    def test_compile_keeps_explicit_sidebar_collapse_override(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        sidebar_group = next(group for group in document.groups if group.zone == "sidebar")
        sidebar_group.behavior["collapsible"] = True
        sidebar_group.behavior["collapsed"] = True
        document.layout_constraints["sidebar_collapsible"] = False

        manifest = compile_dsl_document_to_manifest(document, manifest_revision=4)
        self.assertEqual(manifest.layout_constraints.get("sidebar_collapsible"), False)

    def test_compile_preserves_widget_and_section_style_layout(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        learning_overview = next(group for group in document.groups if group.id == "learning_overview")
        learning_overview.layout = {"columns": 3, "gap": "20px"}
        learning_overview.style = {"padding": "24px", "background": "#111111"}

        learning_path = next(widget for widget in document.widgets if widget.id == "learning_path")
        learning_path.layout = {"col_span": 2, "min_height": "260px"}
        learning_path.style = {"borderRadius": "20px", "opacity": 0.9}

        manifest = compile_dsl_document_to_manifest(document, manifest_revision=6)
        compiled_section = next(section for section in manifest.sections if section.id == "learning_overview")
        compiled_widget = next(widget for widget in manifest.widgets if widget.id == "learning_path")

        self.assertEqual(compiled_section.layout.get("columns"), 3)
        self.assertEqual(compiled_section.style.get("padding"), "24px")
        self.assertEqual(compiled_widget.layout.get("col_span"), 2)
        self.assertEqual(compiled_widget.layout.get("min_height"), "260px")
        self.assertEqual(compiled_widget.style.get("borderRadius"), "20px")
        self.assertEqual(compiled_widget.style.get("opacity"), 0.9)

    def test_compile_widget_graph_without_nodes(self) -> None:
        source_text = """
        surface math_lms.dashboard {
          page dashboard_page { title: "Dashboard", route: "/dashboard", default: true, groups: [header_group] }
          group header_group { title: "Header", page: dashboard_page, zone: header, widgets: [course_progress] }
          widget course_progress: kpi {
            title: "Course Progress"
            capability_id: math.progress_overview
            group: header_group
            layout { min_height: 280 }
            style { border: "2px solid #22d3ee" }
          }
        }
        """
        document = parse_dui_lang(source_text)
        manifest = compile_dsl_document_to_manifest(document, manifest_revision=7)

        self.assertEqual(manifest.revision, 7)
        self.assertEqual(len(manifest.widgets), 1)
        self.assertEqual(manifest.widgets[0].id, "course_progress")
        self.assertEqual(manifest.widgets[0].layout.get("min_height"), 280)
        self.assertEqual(manifest.widgets[0].style.get("border"), "2px solid #22d3ee")
        self.assertEqual(len(manifest.sections), 1)
        self.assertEqual(manifest.sections[0].id, "header_group")
        self.assertEqual(manifest.metadata.get("dsl_model"), "widget-graph-v2")


if __name__ == "__main__":
    unittest.main()
