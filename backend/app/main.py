from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .dsl_models import (
    DuiDslCommitRequest,
    DuiDslCommitResponse,
    DuiDslDocument,
    DuiDslIntentRequest,
    DuiDslIntentResponse,
    DuiDslParseRequest,
    DuiDslParseResponse,
    DuiDslValidateRequest,
    DuiDslValidateResponse,
)
from .models import (
    A2UiEnvelope,
    CommitRequest,
    CommitResponse,
    DEFAULT_SESSION_ID,
    DEFAULT_SURFACE_ID,
    DuiMode,
    IntentRequest,
    IntentResponse,
    RevertRequest,
    RevertResponse,
)
from .services import DslService, EnvelopeService, UiService
from .storage import ManifestStore
from .telemetry import TELEMETRY

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent


def load_project_env(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        os.environ.setdefault(key, value)


load_project_env(PROJECT_ROOT / ".env")
STORE = ManifestStore(BASE_DIR / "data" / "state.json")
UI_SERVICE = UiService(STORE)
DSL_SERVICE = DslService(STORE)
ENVELOPE_SERVICE = EnvelopeService(STORE, UI_SERVICE, DSL_SERVICE)

app = FastAPI(title="Adaptive UI PoC API", version="0.2.0")


def resolve_cors_origins() -> list[str]:
    raw_origins = os.getenv("DUI_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    if not origins:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    return origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=resolve_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DASHBOARD_PAYLOAD = {
    "learner": {
        "name": "Amina",
        "track": "Algebra + Geometry",
        "streak_days": 12,
        "weekly_goal": 5,
        "lessons_done": 3,
        "mastery_percent": 68,
    },
    "learning_path": [
        {
            "id": "lesson-linear-equations",
            "title": "Linear Equations: One Variable",
            "topic": "Algebra",
            "difficulty": "Beginner",
            "duration_min": 30,
            "status": "in_progress",
        },
        {
            "id": "lesson-quadratic-intro",
            "title": "Quadratic Functions: Intuition",
            "topic": "Algebra",
            "difficulty": "Intermediate",
            "duration_min": 40,
            "status": "recommended",
        },
        {
            "id": "lesson-triangles-core",
            "title": "Triangles and Similarity",
            "topic": "Geometry",
            "difficulty": "Intermediate",
            "duration_min": 35,
            "status": "locked",
        },
    ],
    "practice_queue": [
        {
            "id": "set-linear-drill-01",
            "title": "Linear Drill #1",
            "focus": "Solving equations",
            "problems": 12,
            "due_date": "2026-02-10",
        },
        {
            "id": "set-geometry-angles-01",
            "title": "Angles in Triangles",
            "focus": "Geometry fundamentals",
            "problems": 10,
            "due_date": "2026-02-12",
        },
    ],
    "recent_activity": [
        "Finished quiz: Fractions warm-up",
        "Improved accuracy in linear equations to 86%",
        "Spent 28 min in focused practice mode",
    ],
    "mastery_trend": [61, 62, 64, 65, 67, 68],
    "weak_topics": ["Quadratic factoring", "Angle chasing", "Inequality transformations"],
    "quick_actions": [
        {"id": "resume_lesson", "label": "Resume Lesson"},
        {"id": "start_practice", "label": "Start Practice"},
        {"id": "review_mistakes", "label": "Review Mistakes"},
    ],
    "formulas": ["a^2 - b^2 = (a-b)(a+b)", "sin^2(x) + cos^2(x) = 1", "(a+b)^2 = a^2 + 2ab + b^2"],
    "next_lesson_id": "lesson-quadratic-intro",
    "assignments": [
        {"title": "Linear equations set B", "due_date": "2026-02-11"},
        {"title": "Triangles checkpoint", "due_date": "2026-02-13"},
    ],
}

LESSON_PAYLOADS = {
    "lesson-linear-equations": {
        "id": "lesson-linear-equations",
        "title": "Linear Equations: One Variable",
        "topic": "Algebra",
        "estimated_min": 30,
        "objectives": [
            "Isolate variables step by step",
            "Check solutions by substitution",
            "Translate word statements into equations",
        ],
        "theory_points": [
            "An equation stays balanced when applying the same operation on both sides.",
            "Combine like terms before isolating the variable.",
            "Always verify in the original equation.",
        ],
        "exercises": [
            {"id": "ex-1", "prompt": "Solve: 3x + 7 = 25", "type": "numeric"},
            {"id": "ex-2", "prompt": "Solve: 5(x - 2) = 20", "type": "numeric"},
            {
                "id": "ex-3",
                "prompt": "A number plus 9 equals 2 times the number minus 3. Find the number.",
                "type": "word_problem",
            },
        ],
    },
    "lesson-quadratic-intro": {
        "id": "lesson-quadratic-intro",
        "title": "Quadratic Functions: Intuition",
        "topic": "Algebra",
        "estimated_min": 40,
        "objectives": [
            "Identify parabola direction",
            "Estimate vertex from equation form",
            "Connect roots with x-axis intersections",
        ],
        "theory_points": [
            "Quadratic functions have the form ax^2 + bx + c.",
            "The sign of a controls whether the parabola opens up or down.",
            "Roots are x values where y becomes zero.",
        ],
        "exercises": [
            {"id": "ex-1", "prompt": "For y = x^2 - 4x + 3, list the roots", "type": "numeric"},
            {"id": "ex-2", "prompt": "Does y = -2x^2 + 1 open up or down?", "type": "single_choice"},
        ],
    },
}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ops/metrics")
def get_metrics() -> dict[str, object]:
    return TELEMETRY.snapshot()


@app.post("/dev/reset-seed")
def reset_seed() -> dict[str, str]:
    STORE.reset_to_seed()
    return {"status": "ok", "message": "seed manifest restored"}


@app.get("/lms/dashboard")
def get_lms_dashboard() -> dict:
    return DASHBOARD_PAYLOAD


@app.get("/lms/lesson/{lesson_id}")
def get_lesson(lesson_id: str) -> dict:
    payload = LESSON_PAYLOADS.get(lesson_id)
    if not payload:
        raise HTTPException(status_code=404, detail="lesson not found")
    return payload


@app.get("/ui/manifest/current")
def get_current_manifest(surface_id: str = DEFAULT_SURFACE_ID):
    return STORE.get_current_manifest(surface_id=surface_id)


@app.get("/ui/manifest/revisions")
def get_manifest_revisions(surface_id: str = DEFAULT_SURFACE_ID):
    return STORE.list_revisions(surface_id=surface_id)


@app.get("/ui/surfaces")
def get_surfaces() -> list[dict[str, str]]:
    return STORE.list_surfaces()


@app.get("/ui/dsl/current", response_model=DuiDslDocument)
def get_current_dsl(surface_id: str = DEFAULT_SURFACE_ID) -> DuiDslDocument:
    return STORE.get_current_dsl_document(surface_id=surface_id)


@app.get("/ui/dsl/revisions", response_model=list[DuiDslDocument])
def get_dsl_revisions(surface_id: str = DEFAULT_SURFACE_ID) -> list[DuiDslDocument]:
    return STORE.list_dsl_revisions(surface_id=surface_id)


def resolve_mode(scope: str | None) -> DuiMode:
    if scope in {"safe", "extended", "experimental"}:
        return scope
    return "extended"


def resolve_surface_id(surface_id: str | None) -> str:
    if surface_id and surface_id.strip():
        return surface_id.strip()
    return DEFAULT_SURFACE_ID


def resolve_session_id(surface_id: str, session_id: str | None) -> str:
    if session_id and session_id.strip():
        return session_id.strip()
    return STORE.get_surface_context(surface_id)["session_id"]


def build_intent(
    *,
    user_prompt: str,
    current_manifest_id: str | None,
    mode: DuiMode,
    surface_id: str,
    session_id: str,
    turn_id: str | None = None,
) -> IntentResponse:
    return UI_SERVICE.build_intent(
        user_prompt=user_prompt,
        current_manifest_id=current_manifest_id,
        mode=mode,
        surface_id=surface_id,
        session_id=session_id,
        turn_id=turn_id,
    )


def build_commit(
    *,
    patch_plan_id: str,
    surface_id: str,
    session_id: str,
    turn_id: str | None = None,
    expected_base_revision: int | None = None,
) -> CommitResponse:
    return UI_SERVICE.build_commit(
        patch_plan_id=patch_plan_id,
        surface_id=surface_id,
        session_id=session_id,
        turn_id=turn_id,
        expected_base_revision=expected_base_revision,
    )


def build_revert(*, target_revision: int, surface_id: str, approved_by: str | None = None) -> RevertResponse:
    return UI_SERVICE.build_revert(target_revision=target_revision, surface_id=surface_id, approved_by=approved_by)


def build_dsl_validate(*, document: DuiDslDocument, surface_id: str) -> DuiDslValidateResponse:
    return DSL_SERVICE.build_validate(document=document, surface_id=surface_id)


def build_dsl_parse(*, source_text: str, surface_id: str) -> DuiDslParseResponse:
    return DSL_SERVICE.build_parse(source_text=source_text, surface_id=surface_id)


def build_dsl_intent(
    *,
    user_prompt: str,
    surface_id: str,
    mode: DuiMode,
) -> DuiDslIntentResponse:
    return DSL_SERVICE.build_intent(user_prompt=user_prompt, surface_id=surface_id, mode=mode)


def build_dsl_commit(
    *,
    document: DuiDslDocument,
    surface_id: str,
    approved_by: str | None = None,
    expected_manifest_revision: int | None = None,
    expected_dsl_revision: int | None = None,
) -> DuiDslCommitResponse:
    return DSL_SERVICE.build_commit(
        document=document,
        surface_id=surface_id,
        approved_by=approved_by,
        expected_manifest_revision=expected_manifest_revision,
        expected_dsl_revision=expected_dsl_revision,
    )


@app.post("/ai/ui/intent", response_model=IntentResponse)
def ai_ui_intent(request: IntentRequest) -> IntentResponse:
    surface_id = resolve_surface_id(request.surface_id)
    mode = resolve_mode(request.scope)
    session_id = resolve_session_id(surface_id, request.session_id)
    return build_intent(
        user_prompt=request.user_prompt,
        current_manifest_id=request.current_manifest_id,
        mode=mode,
        surface_id=surface_id,
        session_id=session_id,
        turn_id=request.turn_id,
    )


@app.post("/ai/ui/commit", response_model=CommitResponse)
def ai_ui_commit(request: CommitRequest) -> CommitResponse:
    surface_id = resolve_surface_id(request.surface_id)
    session_id = resolve_session_id(surface_id, request.session_id)
    return build_commit(
        patch_plan_id=request.patch_plan_id,
        surface_id=surface_id,
        session_id=session_id,
        turn_id=request.turn_id,
        expected_base_revision=request.expected_base_revision,
    )


@app.post("/ai/ui/revert", response_model=RevertResponse)
def ai_ui_revert(request: RevertRequest) -> RevertResponse:
    surface_id = resolve_surface_id(request.surface_id)
    return build_revert(target_revision=request.target_revision, surface_id=surface_id, approved_by=request.approved_by)


@app.post("/ui/dsl/validate", response_model=DuiDslValidateResponse)
def ui_dsl_validate(request: DuiDslValidateRequest) -> DuiDslValidateResponse:
    surface_id = resolve_surface_id(request.surface_id or request.document.surface.id)
    return build_dsl_validate(document=request.document, surface_id=surface_id)


@app.post("/ui/dsl/parse", response_model=DuiDslParseResponse)
def ui_dsl_parse(request: DuiDslParseRequest) -> DuiDslParseResponse:
    surface_id = resolve_surface_id(request.surface_id)
    return build_dsl_parse(source_text=request.source_text, surface_id=surface_id)


@app.post("/ai/dsl/intent", response_model=DuiDslIntentResponse)
def ai_dsl_intent(request: DuiDslIntentRequest) -> DuiDslIntentResponse:
    surface_id = resolve_surface_id(request.surface_id)
    mode = resolve_mode(request.scope)
    return build_dsl_intent(user_prompt=request.user_prompt, surface_id=surface_id, mode=mode)


@app.post("/ui/dsl/commit", response_model=DuiDslCommitResponse)
def ui_dsl_commit(request: DuiDslCommitRequest) -> DuiDslCommitResponse:
    surface_id = resolve_surface_id(request.surface_id or request.document.surface.id)
    return build_dsl_commit(
        document=request.document,
        surface_id=surface_id,
        approved_by=request.approved_by,
        expected_manifest_revision=request.expected_manifest_revision,
        expected_dsl_revision=request.expected_dsl_revision,
    )


@app.post("/a2ui/envelope", response_model=A2UiEnvelope)
def a2ui_envelope(envelope: A2UiEnvelope) -> A2UiEnvelope:
    surface_id = resolve_surface_id(envelope.surface_id)
    session_id = resolve_session_id(surface_id, envelope.session_id)
    mode = resolve_mode(envelope.mode)
    return ENVELOPE_SERVICE.handle(
        envelope=envelope,
        surface_id=surface_id,
        session_id=session_id,
        mode=mode,
    )
