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


if __name__ == "__main__":
    unittest.main()

