from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .dsl_compiler import compile_dsl_document_to_manifest
from .dsl_intent_engine import DuiDslIntentEngine
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
from .dsl_text_parser import DuiLangParseError, parse_dui_lang
from .dsl_validator import DuiDslValidator
from .intent_engine import IntentEngine
from .manifest_service import apply_patch_operations, clone_with_revision
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
from .policy import PolicyEngine
from .storage import ManifestStore

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

app = FastAPI(title="Adaptive UI PoC API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
    current_manifest = STORE.get_current_manifest(surface_id=surface_id)
    if current_manifest_id and current_manifest_id != current_manifest.manifest_id:
        raise HTTPException(status_code=409, detail="current_manifest_id is stale")

    patch_plan = IntentEngine.build_patch_plan(user_prompt, current_manifest, mode=mode)
    patch_plan.surface_id = surface_id
    patch_plan.session_id = session_id
    patch_plan.turn_id = turn_id
    policy_result = PolicyEngine.validate_operations(current_manifest, patch_plan.operations, mode=mode)

    if policy_result.errors:
        patch_plan.status = "rejected"
        patch_plan.warnings.extend(policy_result.errors)
        STORE.save_patch_plan(patch_plan, surface_id=surface_id)
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Patch plan rejected by policy",
                "errors": policy_result.errors,
                "patch_plan_id": patch_plan.patch_plan_id,
            },
        )

    patch_plan.warnings.extend(policy_result.warnings)
    preview = apply_patch_operations(current_manifest, patch_plan.operations)
    # Preview should not mutate persisted revision numbers.
    preview.revision = current_manifest.revision
    preview.manifest_id = current_manifest.manifest_id

    STORE.save_patch_plan(patch_plan, surface_id=surface_id)

    return IntentResponse(
        patch_plan=patch_plan,
        preview_manifest=preview,
        warnings=patch_plan.warnings,
    )


def build_commit(
    *,
    patch_plan_id: str,
    surface_id: str,
    session_id: str,
    turn_id: str | None = None,
) -> CommitResponse:
    patch_plan = STORE.get_patch_plan(patch_plan_id, surface_id=surface_id)
    if not patch_plan:
        # Legacy compatibility: try global lookup for plans created before surfaces existed.
        patch_plan = STORE.get_patch_plan(patch_plan_id, surface_id=None)
    if not patch_plan:
        raise HTTPException(status_code=404, detail="patch_plan_id not found")

    if patch_plan.surface_id and patch_plan.surface_id != surface_id:
        raise HTTPException(status_code=409, detail="patch_plan belongs to another surface")

    current_manifest = STORE.get_current_manifest(surface_id=surface_id)
    policy_result = PolicyEngine.validate_operations(current_manifest, patch_plan.operations, mode=patch_plan.mode)
    if policy_result.errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Patch plan failed policy on commit", "errors": policy_result.errors},
        )

    next_manifest = apply_patch_operations(current_manifest, patch_plan.operations)
    patch_plan.surface_id = surface_id
    patch_plan.session_id = session_id or DEFAULT_SESSION_ID
    patch_plan.turn_id = turn_id or patch_plan.turn_id
    patch_plan.status = "committed"
    STORE.update_patch_plan(patch_plan, surface_id=surface_id)
    STORE.append_manifest_revision(next_manifest, surface_id=surface_id)

    return CommitResponse(manifest=next_manifest)


def build_revert(*, target_revision: int, surface_id: str) -> RevertResponse:
    current_manifest = STORE.get_current_manifest(surface_id=surface_id)
    target_manifest = STORE.get_revision(target_revision, surface_id=surface_id)
    if not target_manifest:
        raise HTTPException(status_code=404, detail="target revision not found")

    reverted = clone_with_revision(target_manifest, current_manifest.revision + 1)
    reverted.metadata["reverted_from"] = str(current_manifest.revision)
    reverted.metadata["reverted_to"] = str(target_revision)
    reverted.metadata["surface_id"] = surface_id

    STORE.append_manifest_revision(reverted, surface_id=surface_id)

    return RevertResponse(manifest=reverted)


def build_dsl_validate(*, document: DuiDslDocument, surface_id: str) -> DuiDslValidateResponse:
    validation_result = DuiDslValidator.validate(document)
    if not validation_result.valid:
        return DuiDslValidateResponse(result=validation_result, compiled_manifest=None)

    current_manifest = STORE.get_current_manifest(surface_id=surface_id)
    preview_manifest = compile_dsl_document_to_manifest(
        document,
        manifest_revision=current_manifest.revision,
        manifest_id=current_manifest.manifest_id,
    )
    return DuiDslValidateResponse(result=validation_result, compiled_manifest=preview_manifest)


def build_dsl_parse(*, source_text: str, surface_id: str) -> DuiDslParseResponse:
    try:
        document = parse_dui_lang(source_text)
    except DuiLangParseError as error:
        raise HTTPException(status_code=400, detail={"message": str(error), "line": error.line, "column": error.column}) from error
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to parse DSL source: {type(error).__name__}") from error

    # Force document surface to resolved context.
    document.surface.id = surface_id

    validation_result = DuiDslValidator.validate(document)
    compiled_manifest = None
    if validation_result.valid:
        current_manifest = STORE.get_current_manifest(surface_id=surface_id)
        compiled_manifest = compile_dsl_document_to_manifest(
            document,
            manifest_revision=current_manifest.revision,
            manifest_id=current_manifest.manifest_id,
        )
    return DuiDslParseResponse(
        document=document,
        validation_result=validation_result,
        compiled_manifest=compiled_manifest,
    )


def _enforce_dsl_mode(
    *,
    current_document: DuiDslDocument,
    next_document: DuiDslDocument,
    mode: DuiMode,
) -> list[str]:
    errors: list[str] = []
    if mode == "safe":
        # Safe mode only permits theme changes.
        if current_document.nodes != next_document.nodes:
            errors.append("safe mode allows only theme updates (nodes cannot change)")
        if current_document.bindings != next_document.bindings:
            errors.append("safe mode allows only theme updates (bindings cannot change)")
        if current_document.actions != next_document.actions:
            errors.append("safe mode allows only theme updates (actions cannot change)")
        if current_document.layout_constraints != next_document.layout_constraints:
            errors.append("safe mode allows only theme updates (layout_constraints cannot change)")
    return errors


def build_dsl_intent(
    *,
    user_prompt: str,
    surface_id: str,
    mode: DuiMode,
) -> DuiDslIntentResponse:
    current_document = STORE.get_current_dsl_document(surface_id=surface_id)
    next_document, intent_warnings = DuiDslIntentEngine.build_next_document(
        user_prompt,
        current_document,
        mode=mode,
    )
    next_document.surface.id = surface_id

    mode_errors = _enforce_dsl_mode(current_document=current_document, next_document=next_document, mode=mode)
    if mode_errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "DSL intent rejected by mode policy", "errors": mode_errors},
        )

    validation_result = DuiDslValidator.validate(next_document)
    if not validation_result.valid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "DSL intent produced invalid document",
                "errors": [issue.model_dump(mode="json") for issue in validation_result.errors],
                "warnings": intent_warnings,
            },
        )

    current_manifest = STORE.get_current_manifest(surface_id=surface_id)
    preview_manifest = compile_dsl_document_to_manifest(
        next_document,
        manifest_revision=current_manifest.revision,
        manifest_id=current_manifest.manifest_id,
    )
    return DuiDslIntentResponse(
        document=next_document,
        validation_result=validation_result,
        preview_manifest=preview_manifest,
        warnings=intent_warnings,
    )


def build_dsl_commit(*, document: DuiDslDocument, surface_id: str, approved_by: str | None = None) -> DuiDslCommitResponse:
    validation_result = DuiDslValidator.validate(document)
    if not validation_result.valid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "DSL document failed validation",
                "errors": [issue.model_dump(mode="json") for issue in validation_result.errors],
            },
        )

    current_manifest = STORE.get_current_manifest(surface_id=surface_id)
    current_document = STORE.get_current_dsl_document(surface_id=surface_id)

    next_document = document.model_copy(deep=True)
    next_document.surface.id = surface_id
    next_document.meta.revision = current_document.meta.revision + 1
    next_document.meta.created_at = datetime.now(timezone.utc)
    if approved_by:
        next_document.meta.created_by = approved_by

    next_manifest = compile_dsl_document_to_manifest(
        next_document,
        manifest_revision=current_manifest.revision + 1,
    )
    next_manifest.metadata["surface_id"] = surface_id

    STORE.append_dsl_revision(next_document, surface_id=surface_id)
    STORE.append_manifest_revision(next_manifest, surface_id=surface_id)

    return DuiDslCommitResponse(document=next_document, manifest=next_manifest)


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
    )


@app.post("/ai/ui/revert", response_model=RevertResponse)
def ai_ui_revert(request: RevertRequest) -> RevertResponse:
    surface_id = resolve_surface_id(request.surface_id)
    return build_revert(target_revision=request.target_revision, surface_id=surface_id)


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
    return build_dsl_commit(document=request.document, surface_id=surface_id, approved_by=request.approved_by)


@app.post("/a2ui/envelope", response_model=A2UiEnvelope)
def a2ui_envelope(envelope: A2UiEnvelope) -> A2UiEnvelope:
    surface_id = resolve_surface_id(envelope.surface_id)
    session_id = resolve_session_id(surface_id, envelope.session_id)
    surface_context = STORE.get_surface_context(surface_id)
    mode = resolve_mode(envelope.mode)

    if envelope.message_type == "manifest.current.request":
        manifest = STORE.get_current_manifest(surface_id=surface_id)
        payload = {"manifest": manifest.model_dump(mode="json")}
        return A2UiEnvelope(
            session_id=session_id,
            surface_id=surface_id,
            turn_id=envelope.turn_id,
            mode=mode,
            catalog_version=surface_context["catalog_version"],
            message_type="manifest.current.response",
            payload=payload,
        )

    if envelope.message_type == "manifest.revisions.request":
        revisions = STORE.list_revisions(surface_id=surface_id)
        payload = {"revisions": [revision.model_dump(mode="json") for revision in revisions]}
        return A2UiEnvelope(
            session_id=session_id,
            surface_id=surface_id,
            turn_id=envelope.turn_id,
            mode=mode,
            catalog_version=surface_context["catalog_version"],
            message_type="manifest.revisions.response",
            payload=payload,
        )

    if envelope.message_type == "dsl.current.request":
        document = STORE.get_current_dsl_document(surface_id=surface_id)
        payload = {"document": document.model_dump(mode="json")}
        return A2UiEnvelope(
            session_id=session_id,
            surface_id=surface_id,
            turn_id=envelope.turn_id,
            mode=mode,
            catalog_version=surface_context["catalog_version"],
            message_type="dsl.current.response",
            payload=payload,
        )

    if envelope.message_type == "dsl.intent.request":
        prompt = str(envelope.payload.get("user_prompt", "")).strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="dsl.intent.request requires payload.user_prompt")
        response = build_dsl_intent(user_prompt=prompt, surface_id=surface_id, mode=mode)
        payload = response.model_dump(mode="json")
        return A2UiEnvelope(
            session_id=session_id,
            surface_id=surface_id,
            turn_id=envelope.turn_id,
            mode=mode,
            catalog_version=surface_context["catalog_version"],
            message_type="dsl.intent.response",
            payload=payload,
        )

    if envelope.message_type == "dsl.parse.request":
        source_text_raw = envelope.payload.get("source_text")
        if not isinstance(source_text_raw, str) or not source_text_raw.strip():
            raise HTTPException(status_code=400, detail="dsl.parse.request requires non-empty payload.source_text")
        response = build_dsl_parse(source_text=source_text_raw, surface_id=surface_id)
        payload = response.model_dump(mode="json")
        return A2UiEnvelope(
            session_id=session_id,
            surface_id=surface_id,
            turn_id=envelope.turn_id,
            mode=mode,
            catalog_version=surface_context["catalog_version"],
            message_type="dsl.parse.response",
            payload=payload,
        )

    if envelope.message_type == "dsl.revisions.request":
        revisions = STORE.list_dsl_revisions(surface_id=surface_id)
        payload = {"documents": [revision.model_dump(mode="json") for revision in revisions]}
        return A2UiEnvelope(
            session_id=session_id,
            surface_id=surface_id,
            turn_id=envelope.turn_id,
            mode=mode,
            catalog_version=surface_context["catalog_version"],
            message_type="dsl.revisions.response",
            payload=payload,
        )

    if envelope.message_type == "dsl.validate.request":
        document_raw = envelope.payload.get("document")
        if not isinstance(document_raw, dict):
            raise HTTPException(status_code=400, detail="dsl.validate.request requires payload.document object")
        document = DuiDslDocument.model_validate(document_raw)
        response = build_dsl_validate(document=document, surface_id=surface_id)
        payload = response.model_dump(mode="json")
        return A2UiEnvelope(
            session_id=session_id,
            surface_id=surface_id,
            turn_id=envelope.turn_id,
            mode=mode,
            catalog_version=surface_context["catalog_version"],
            message_type="dsl.validate.response",
            payload=payload,
        )

    if envelope.message_type == "dsl.commit.request":
        document_raw = envelope.payload.get("document")
        if not isinstance(document_raw, dict):
            raise HTTPException(status_code=400, detail="dsl.commit.request requires payload.document object")
        approved_by_raw = envelope.payload.get("approved_by")
        approved_by = str(approved_by_raw) if isinstance(approved_by_raw, str) else None
        document = DuiDslDocument.model_validate(document_raw)
        response = build_dsl_commit(document=document, surface_id=surface_id, approved_by=approved_by)
        payload = response.model_dump(mode="json")
        return A2UiEnvelope(
            session_id=session_id,
            surface_id=surface_id,
            turn_id=envelope.turn_id,
            mode=mode,
            catalog_version=surface_context["catalog_version"],
            message_type="dsl.commit.response",
            payload=payload,
        )

    if envelope.message_type == "intent.request":
        prompt = str(envelope.payload.get("user_prompt", "")).strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="intent.request requires payload.user_prompt")
        current_manifest_id = envelope.payload.get("current_manifest_id")
        if current_manifest_id is not None:
            current_manifest_id = str(current_manifest_id)
        intent_response = build_intent(
            user_prompt=prompt,
            current_manifest_id=current_manifest_id,
            mode=mode,
            surface_id=surface_id,
            session_id=session_id,
            turn_id=envelope.turn_id,
        )
        payload = intent_response.model_dump(mode="json")
        return A2UiEnvelope(
            session_id=session_id,
            surface_id=surface_id,
            turn_id=envelope.turn_id,
            mode=mode,
            catalog_version=surface_context["catalog_version"],
            message_type="intent.response",
            payload=payload,
        )

    if envelope.message_type == "commit.request":
        patch_plan_id = str(envelope.payload.get("patch_plan_id", "")).strip()
        if not patch_plan_id:
            raise HTTPException(status_code=400, detail="commit.request requires payload.patch_plan_id")
        commit_response = build_commit(
            patch_plan_id=patch_plan_id,
            surface_id=surface_id,
            session_id=session_id,
            turn_id=envelope.turn_id,
        )
        payload = commit_response.model_dump(mode="json")
        return A2UiEnvelope(
            session_id=session_id,
            surface_id=surface_id,
            turn_id=envelope.turn_id,
            mode=mode,
            catalog_version=surface_context["catalog_version"],
            message_type="commit.response",
            payload=payload,
        )

    if envelope.message_type == "revert.request":
        target_revision_raw = envelope.payload.get("target_revision")
        if not isinstance(target_revision_raw, int):
            raise HTTPException(status_code=400, detail="revert.request requires integer payload.target_revision")
        revert_response = build_revert(target_revision=target_revision_raw, surface_id=surface_id)
        payload = revert_response.model_dump(mode="json")
        return A2UiEnvelope(
            session_id=session_id,
            surface_id=surface_id,
            turn_id=envelope.turn_id,
            mode=mode,
            catalog_version=surface_context["catalog_version"],
            message_type="revert.response",
            payload=payload,
        )

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported message_type '{envelope.message_type}' for /a2ui/envelope",
    )
