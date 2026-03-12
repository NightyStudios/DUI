from __future__ import annotations

from .dsl_models import (
    DuiDslDocument,
    DuiDslMeta,
    DuiDslPage,
    DuiDslSurface,
    DuiDslTheme,
    DuiDslWidget,
    DuiDslWidgetGroup,
)
from .models import DEFAULT_SURFACE_ID


LESSON_SURFACE_ID = "math_lms.lesson"


def build_seed_document_for_surface(surface_id: str) -> DuiDslDocument:
    if surface_id == LESSON_SURFACE_ID:
        return _lesson_seed_document()
    return _dashboard_seed_document(surface_id)


def _dashboard_seed_document(surface_id: str) -> DuiDslDocument:
    return DuiDslDocument(
        surface=DuiDslSurface(id=surface_id, title="Math Dashboard", route="/dashboard"),
        meta=DuiDslMeta(document_id="seed-dsl-dashboard-v2", revision=1, created_by="seed"),
        theme=DuiDslTheme(profile="default", density="comfortable", tokens={}),
        layout_constraints={"max_columns": 2, "sidebar_width": "normal", "content_density": "comfortable"},
        pages=[
            DuiDslPage(
                id="dashboard_page",
                title="Math Dashboard",
                route="/dashboard",
                group_ids=["main_header_group", "learning_overview", "main_sidebar_group"],
                is_default=True,
                layout={"max_columns": 2},
                style={},
                behavior={},
            )
        ],
        groups=[
            DuiDslWidgetGroup(
                id="main_header_group",
                title="Header",
                page_id="dashboard_page",
                zone="header",
                widget_ids=["course_progress"],
                visible=True,
                layout={"columns": 1},
                style={},
                behavior={},
            ),
            DuiDslWidgetGroup(
                id="learning_overview",
                title="Learning Overview",
                page_id="dashboard_page",
                zone="content",
                widget_ids=["learning_path", "mastery_trend"],
                visible=True,
                layout={"columns": 2},
                style={},
                behavior={},
            ),
            DuiDslWidgetGroup(
                id="main_sidebar_group",
                title="Sidebar",
                page_id="dashboard_page",
                zone="sidebar",
                widget_ids=["practice_queue"],
                visible=True,
                layout={"columns": 1},
                style={},
                behavior={},
            ),
        ],
        widgets=[
            DuiDslWidget(
                id="course_progress",
                kind="kpi",
                title="Course Progress",
                zone="header",
                group_id="main_header_group",
                capability_id="math.progress_overview",
                visible=True,
                props={"title": "Course Progress", "zone": "header", "capability_id": "math.progress_overview", "protected": True},
                behavior={"protected": True},
            ),
            DuiDslWidget(
                id="learning_path",
                kind="table",
                title="Learning Path",
                zone="content",
                group_id="learning_overview",
                capability_id="math.learning_path",
                visible=True,
                props={"title": "Learning Path", "zone": "content", "capability_id": "math.learning_path"},
            ),
            DuiDslWidget(
                id="mastery_trend",
                kind="chart",
                title="Mastery Trend",
                zone="content",
                group_id="learning_overview",
                capability_id="math.mastery_trend",
                visible=True,
                props={"title": "Mastery Trend", "zone": "content", "capability_id": "math.mastery_trend"},
            ),
            DuiDslWidget(
                id="practice_queue",
                kind="activity",
                title="Practice Queue",
                zone="sidebar",
                group_id="main_sidebar_group",
                capability_id="math.practice_queue",
                visible=True,
                props={"title": "Practice Queue", "zone": "sidebar", "capability_id": "math.practice_queue"},
            ),
        ],
    )


def _lesson_seed_document() -> DuiDslDocument:
    return DuiDslDocument(
        surface=DuiDslSurface(id=LESSON_SURFACE_ID, title="Lesson Surface", route="/lesson"),
        meta=DuiDslMeta(document_id="seed-dsl-lesson-v2", revision=1, created_by="seed"),
        theme=DuiDslTheme(profile="default", density="comfortable", tokens={}),
        layout_constraints={"max_columns": 1, "sidebar_width": "normal", "content_density": "comfortable"},
        pages=[
            DuiDslPage(
                id="lesson_page",
                title="Lesson Surface",
                route="/lesson",
                group_ids=["lesson_header_group", "lesson_section", "lesson_sidebar_group"],
                is_default=True,
                layout={"max_columns": 1},
                style={},
                behavior={},
            )
        ],
        groups=[
            DuiDslWidgetGroup(
                id="lesson_header_group",
                title="Lesson Header",
                page_id="lesson_page",
                zone="header",
                widget_ids=["lesson_progress"],
                visible=True,
                layout={"columns": 1},
                style={},
                behavior={},
            ),
            DuiDslWidgetGroup(
                id="lesson_section",
                title="Lesson Content",
                page_id="lesson_page",
                zone="content",
                widget_ids=["lesson_objectives", "lesson_theory"],
                visible=True,
                layout={"columns": 1},
                style={},
                behavior={},
            ),
            DuiDslWidgetGroup(
                id="lesson_sidebar_group",
                title="Lesson Sidebar",
                page_id="lesson_page",
                zone="sidebar",
                widget_ids=["lesson_exercises"],
                visible=True,
                layout={"columns": 1},
                style={},
                behavior={},
            ),
        ],
        widgets=[
            DuiDslWidget(
                id="lesson_progress",
                kind="kpi",
                title="Lesson Progress",
                zone="header",
                group_id="lesson_header_group",
                capability_id="math.lesson_progress",
                visible=True,
                props={"title": "Lesson Progress", "zone": "header", "capability_id": "math.lesson_progress", "protected": True},
                behavior={"protected": True},
            ),
            DuiDslWidget(
                id="lesson_objectives",
                kind="list",
                title="Objectives",
                zone="content",
                group_id="lesson_section",
                capability_id="math.lesson_objectives",
                visible=True,
                props={"title": "Objectives", "zone": "content", "capability_id": "math.lesson_objectives"},
            ),
            DuiDslWidget(
                id="lesson_theory",
                kind="card",
                title="Theory Points",
                zone="content",
                group_id="lesson_section",
                capability_id="math.lesson_theory",
                visible=True,
                props={"title": "Theory Points", "zone": "content", "capability_id": "math.lesson_theory"},
            ),
            DuiDslWidget(
                id="lesson_exercises",
                kind="activity",
                title="Exercises",
                zone="sidebar",
                group_id="lesson_sidebar_group",
                capability_id="math.lesson_exercises",
                visible=True,
                props={"title": "Exercises", "zone": "sidebar", "capability_id": "math.lesson_exercises"},
            ),
        ],
    )
