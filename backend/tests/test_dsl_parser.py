from __future__ import annotations

import unittest

from backend.app.dsl_text_parser import DuiLangParseError, parse_dui_lang


SAMPLE_DSL = """
surface math_lms.dashboard {
  surface_meta { title: "Math Dashboard", route: "/dashboard" }
  meta { document_id: "doc_sample", revision: 1, created_by: "seed" }
  theme { profile: minimal density: compact tokens { accent: "#111111" } }
  layout_constraints { max_columns: 2, sidebar_width: normal, content_density: compact }
  state { selectedLessonId: "lesson-linear-equations" }

  action act_open { type: nav.open_route params { route: "/lesson" } }

  node root: layout.page {
    children: [header_region, content_region]
  }

  node header_region: layout.region {
    props { zone: header }
    children: [course_progress]
  }

  node content_region: layout.region {
    props { zone: content }
    children: [learning_path]
  }

  node course_progress: data.kpi_card {
    props { title: "Progress", zone: header, capability_id: math.progress_overview, protected: true }
    on { click: act_open }
  }

  node learning_path: data.data_table {
    props { title: "Learning Path", zone: content, capability_id: math.learning_path }
  }

  binding bind_progress {
    source: "capability:math.progress_overview"
    select: "$"
  }
}
"""

SAMPLE_WIDGET_DSL = """
surface math_lms.dashboard {
  surface_meta { title: "Math Dashboard", route: "/dashboard" }
  meta { document_id: "doc_widget_sample", revision: 2, created_by: "seed" }
  theme { profile: default density: comfortable }
  layout_constraints { max_columns: 2, sidebar_width: normal }

  page dashboard_page {
    title: "Dashboard"
    route: "/dashboard"
    default: true
    groups: [header_group, content_group]
  }

  group header_group {
    title: "Header Group"
    page: dashboard_page
    zone: header
    widgets: [course_progress]
  }

  group content_group {
    title: "Content Group"
    page: dashboard_page
    zone: content
    widgets: [learning_path]
  }

  widget course_progress: kpi {
    title: "Course Progress"
    group: header_group
    capability_id: math.progress_overview
    style { background: "#0f172a" }
    layout { min_height: 240 }
  }

  widget learning_path: table {
    title: "Learning Path"
    group: content_group
    capability_id: math.learning_path
    visible: true
    links [ { page: dashboard_page, rel: open } ]
  }
}
"""


class DuiDslParserTests(unittest.TestCase):
    def test_parse_valid_dsl_text(self) -> None:
        document = parse_dui_lang(SAMPLE_DSL)
        self.assertEqual(document.surface.id, "math_lms.dashboard")
        self.assertEqual(document.theme.profile, "minimal")
        self.assertEqual(document.theme.density, "compact")
        self.assertEqual(len(document.nodes), 5)
        self.assertEqual(len(document.actions), 1)
        self.assertEqual(len(document.bindings), 1)
        self.assertEqual(document.nodes[0].id, "root")

    def test_parse_invalid_dsl_text_raises(self) -> None:
        bad_text = "surface demo { node root: layout.page { children: [x] "
        with self.assertRaises(DuiLangParseError):
            parse_dui_lang(bad_text)

    def test_parse_widget_graph_dsl_text(self) -> None:
        document = parse_dui_lang(SAMPLE_WIDGET_DSL)
        self.assertEqual(document.surface.id, "math_lms.dashboard")
        self.assertEqual(len(document.pages), 1)
        self.assertEqual(len(document.groups), 2)
        self.assertEqual(len(document.widgets), 2)
        self.assertEqual(document.pages[0].id, "dashboard_page")
        self.assertTrue(document.pages[0].is_default)
        self.assertEqual(document.widgets[0].id, "course_progress")
        self.assertEqual(document.widgets[0].capability_id, "math.progress_overview")


if __name__ == "__main__":
    unittest.main()
