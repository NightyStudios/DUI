from __future__ import annotations

import unittest

from backend.app.dsl_seed import build_seed_document_for_surface
from backend.app.dsl_text_parser import parse_dui_lang
from backend.app.dsl_validator import DuiDslValidator
from backend.app.models import DEFAULT_SURFACE_ID


class DuiDslValidatorTests(unittest.TestCase):
    def test_seed_document_is_valid(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        result = DuiDslValidator.validate(document)
        self.assertTrue(result.valid, msg=f"Unexpected errors: {[issue.message for issue in result.errors]}")

    def test_duplicate_widget_id_is_rejected(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        document.widgets.append(document.widgets[0].model_copy(deep=True))
        result = DuiDslValidator.validate(document)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "widget.id_duplicate" for issue in result.errors))

    def test_unknown_group_widget_reference_is_rejected(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        document.groups[0].widget_ids.append("ghost_widget")
        result = DuiDslValidator.validate(document)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "group.widget_unknown" for issue in result.errors))

    def test_widget_graph_without_legacy_nodes_is_valid(self) -> None:
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
        result = DuiDslValidator.validate(document)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "widget.link_page_unknown" for issue in result.errors))


if __name__ == "__main__":
    unittest.main()
