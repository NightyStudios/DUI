from __future__ import annotations

import unittest

from backend.app.dsl_models import DuiDslNode
from backend.app.dsl_seed import build_seed_document_for_surface
from backend.app.dsl_text_parser import parse_dui_lang
from backend.app.dsl_validator import DuiDslValidator
from backend.app.models import DEFAULT_SURFACE_ID


class DuiDslValidatorTests(unittest.TestCase):
    def test_seed_document_is_valid(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        result = DuiDslValidator.validate(document)
        self.assertTrue(result.valid, msg=f"Unexpected errors: {[issue.message for issue in result.errors]}")

    def test_unknown_node_type_is_rejected(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        document.nodes.append(DuiDslNode(id="bad_node", type="evil.custom_component"))
        result = DuiDslValidator.validate(document)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "node.type_unknown" for issue in result.errors))

    def test_duplicate_node_id_is_rejected(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        first = document.nodes[0]
        document.nodes.append(DuiDslNode(id=first.id, type="layout.container"))
        result = DuiDslValidator.validate(document)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "node.id_duplicate" for issue in result.errors))

    def test_unknown_child_reference_is_rejected(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        document.nodes[0].children.append("ghost_node")
        result = DuiDslValidator.validate(document)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "node.child_unknown" for issue in result.errors))

    def test_widget_graph_without_nodes_is_valid(self) -> None:
        source_text = """
        surface math_lms.dashboard {
          page dashboard_page { title: "Dashboard", route: "/dashboard", default: true, groups: [main_group] }
          group main_group { title: "Main", page: dashboard_page, zone: content, widgets: [course_progress] }
          widget course_progress: kpi {
            title: "Course Progress"
            group: main_group
            capability_id: math.progress_overview
          }
        }
        """
        document = parse_dui_lang(source_text)
        document.nodes = []
        result = DuiDslValidator.validate(document)
        self.assertTrue(result.valid, msg=f"Unexpected errors: {[issue.message for issue in result.errors]}")

    def test_widget_graph_unknown_page_link_is_rejected(self) -> None:
        source_text = """
        surface math_lms.dashboard {
          page dashboard_page { title: "Dashboard", route: "/dashboard", default: true, groups: [main_group] }
          group main_group { title: "Main", page: dashboard_page, zone: content, widgets: [next_step] }
          widget next_step: card {
            title: "Next"
            group: main_group
            links [ { page: ghost_page } ]
          }
        }
        """
        document = parse_dui_lang(source_text)
        document.nodes = []
        result = DuiDslValidator.validate(document)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "widget.link_page_unknown" for issue in result.errors))


if __name__ == "__main__":
    unittest.main()
