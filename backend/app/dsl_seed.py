from __future__ import annotations

from .dsl_models import DuiDslDocument, DuiDslMeta, DuiDslNode, DuiDslSurface, DuiDslTheme
from .models import DEFAULT_SURFACE_ID


LESSON_SURFACE_ID = "math_lms.lesson"


def build_seed_document_for_surface(surface_id: str) -> DuiDslDocument:
    if surface_id == LESSON_SURFACE_ID:
        return _lesson_seed_document()
    return _dashboard_seed_document(surface_id)


def _dashboard_seed_document(surface_id: str) -> DuiDslDocument:
    return DuiDslDocument(
        surface=DuiDslSurface(id=surface_id, title="Math Dashboard", route="/dashboard"),
        meta=DuiDslMeta(document_id="seed-dsl-dashboard-v1", revision=1, created_by="seed"),
        theme=DuiDslTheme(profile="default", density="comfortable", tokens={}),
        layout_constraints={"max_columns": 2, "sidebar_width": "normal", "content_density": "comfortable"},
        nodes=[
            DuiDslNode(id="root", type="layout.page", children=["main_header", "main_content", "main_sidebar"]),
            DuiDslNode(id="main_header", type="layout.region", props={"zone": "header"}, children=["course_progress"]),
            DuiDslNode(
                id="main_content",
                type="layout.region",
                props={"zone": "content"},
                children=["learning_overview", "learning_path", "mastery_trend"],
            ),
            DuiDslNode(id="main_sidebar", type="layout.region", props={"zone": "sidebar"}, children=["practice_queue"]),
            DuiDslNode(
                id="course_progress",
                type="data.kpi_card",
                props={
                    "title": "Course Progress",
                    "zone": "header",
                    "capability_id": "math.progress_overview",
                    "protected": True,
                },
            ),
            DuiDslNode(
                id="learning_path",
                type="data.data_table",
                props={"title": "Learning Path", "zone": "content", "capability_id": "math.learning_path"},
            ),
            DuiDslNode(
                id="mastery_trend",
                type="chart.line",
                props={"title": "Mastery Trend", "zone": "content", "capability_id": "math.mastery_trend"},
            ),
            DuiDslNode(
                id="practice_queue",
                type="data.activity_feed",
                props={"title": "Practice Queue", "zone": "sidebar", "capability_id": "math.practice_queue"},
            ),
            DuiDslNode(
                id="learning_overview",
                type="layout.section",
                props={"title": "Learning Overview", "zone": "content"},
                layout={"columns": 2},
                children=["learning_path", "mastery_trend"],
            ),
        ],
    )


def _lesson_seed_document() -> DuiDslDocument:
    return DuiDslDocument(
        surface=DuiDslSurface(id=LESSON_SURFACE_ID, title="Lesson Surface", route="/lesson"),
        meta=DuiDslMeta(document_id="seed-dsl-lesson-v1", revision=1, created_by="seed"),
        theme=DuiDslTheme(profile="default", density="comfortable", tokens={}),
        layout_constraints={"max_columns": 1, "sidebar_width": "normal", "content_density": "comfortable"},
        nodes=[
            DuiDslNode(id="root", type="layout.page", children=["lesson_header", "lesson_content", "lesson_sidebar"]),
            DuiDslNode(id="lesson_header", type="layout.region", props={"zone": "header"}, children=["lesson_progress"]),
            DuiDslNode(
                id="lesson_content",
                type="layout.region",
                props={"zone": "content"},
                children=["lesson_section", "lesson_objectives", "lesson_theory"],
            ),
            DuiDslNode(id="lesson_sidebar", type="layout.region", props={"zone": "sidebar"}, children=["lesson_exercises"]),
            DuiDslNode(
                id="lesson_progress",
                type="data.kpi_card",
                props={
                    "title": "Lesson Progress",
                    "zone": "header",
                    "capability_id": "math.lesson_progress",
                    "protected": True,
                },
            ),
            DuiDslNode(
                id="lesson_objectives",
                type="lms.lesson_objectives",
                props={"title": "Objectives", "zone": "content", "capability_id": "math.lesson_objectives"},
            ),
            DuiDslNode(
                id="lesson_theory",
                type="lms.theory_points",
                props={"title": "Theory Points", "zone": "content", "capability_id": "math.lesson_theory"},
            ),
            DuiDslNode(
                id="lesson_exercises",
                type="lms.exercise_list",
                props={"title": "Exercises", "zone": "sidebar", "capability_id": "math.lesson_exercises"},
            ),
            DuiDslNode(
                id="lesson_section",
                type="layout.section",
                props={"title": "Lesson Content", "zone": "content"},
                layout={"columns": 1},
                children=["lesson_objectives", "lesson_theory"],
            ),
        ],
    )

