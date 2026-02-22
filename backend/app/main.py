from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import BASE_DIR, load_project_env, resolve_cors_origins
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
from .mock_lms_data import get_dashboard_payload, get_lesson_payload_or_404
from .models import (
    A2UiEnvelope,
    CommitRequest,
    CommitResponse,
    DEFAULT_SURFACE_ID,
    DuiMode,
    IntentRequest,
    IntentResponse,
    RevertRequest,
    RevertResponse,
)
from .runtime_context import resolve_mode, resolve_session_id, resolve_surface_id
from .services import DslService, EnvelopeService, UiService
from .storage import ManifestStore
from .telemetry import TELEMETRY

load_project_env()
STORE = ManifestStore(BASE_DIR / "data" / "state.json")
UI_SERVICE = UiService(STORE)
DSL_SERVICE = DslService(STORE)
ENVELOPE_SERVICE = EnvelopeService(STORE, UI_SERVICE, DSL_SERVICE)

app = FastAPI(title="Adaptive UI PoC API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=resolve_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return get_dashboard_payload()


@app.get("/lms/lesson/{lesson_id}")
def get_lesson(lesson_id: str) -> dict:
    return get_lesson_payload_or_404(lesson_id)


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


# Kept for tests and scripts that call service helpers directly.
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


def build_dsl_parse(*, source_text: str, surface_id: str | None = None) -> DuiDslParseResponse:
    return DSL_SERVICE.build_parse(source_text=source_text, surface_id=surface_id)


def build_dsl_intent(*, user_prompt: str, surface_id: str, mode: DuiMode) -> DuiDslIntentResponse:
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
    session_id = resolve_session_id(STORE, surface_id=surface_id, session_id=request.session_id)
    return UI_SERVICE.build_intent(
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
    session_id = resolve_session_id(STORE, surface_id=surface_id, session_id=request.session_id)
    return UI_SERVICE.build_commit(
        patch_plan_id=request.patch_plan_id,
        surface_id=surface_id,
        session_id=session_id,
        turn_id=request.turn_id,
        expected_base_revision=request.expected_base_revision,
    )


@app.post("/ai/ui/revert", response_model=RevertResponse)
def ai_ui_revert(request: RevertRequest) -> RevertResponse:
    surface_id = resolve_surface_id(request.surface_id)
    return UI_SERVICE.build_revert(target_revision=request.target_revision, surface_id=surface_id, approved_by=request.approved_by)


@app.post("/ui/dsl/validate", response_model=DuiDslValidateResponse)
def ui_dsl_validate(request: DuiDslValidateRequest) -> DuiDslValidateResponse:
    surface_id = resolve_surface_id(request.surface_id or request.document.surface.id)
    return DSL_SERVICE.build_validate(document=request.document, surface_id=surface_id)


@app.post("/ui/dsl/parse", response_model=DuiDslParseResponse)
def ui_dsl_parse(request: DuiDslParseRequest) -> DuiDslParseResponse:
    surface_id = request.surface_id.strip() if request.surface_id and request.surface_id.strip() else None
    return DSL_SERVICE.build_parse(source_text=request.source_text, surface_id=surface_id)


@app.post("/ai/dsl/intent", response_model=DuiDslIntentResponse)
def ai_dsl_intent(request: DuiDslIntentRequest) -> DuiDslIntentResponse:
    surface_id = resolve_surface_id(request.surface_id)
    mode = resolve_mode(request.scope)
    return DSL_SERVICE.build_intent(user_prompt=request.user_prompt, surface_id=surface_id, mode=mode)


@app.post("/ui/dsl/commit", response_model=DuiDslCommitResponse)
def ui_dsl_commit(request: DuiDslCommitRequest) -> DuiDslCommitResponse:
    surface_id = resolve_surface_id(request.surface_id or request.document.surface.id)
    return DSL_SERVICE.build_commit(
        document=request.document,
        surface_id=surface_id,
        approved_by=request.approved_by,
        expected_manifest_revision=request.expected_manifest_revision,
        expected_dsl_revision=request.expected_dsl_revision,
    )


@app.post("/a2ui/envelope", response_model=A2UiEnvelope)
def a2ui_envelope(envelope: A2UiEnvelope) -> A2UiEnvelope:
    surface_id = resolve_surface_id(envelope.surface_id)
    session_id = resolve_session_id(STORE, surface_id=surface_id, session_id=envelope.session_id)
    mode = resolve_mode(envelope.mode)
    return ENVELOPE_SERVICE.handle(
        envelope=envelope,
        surface_id=surface_id,
        session_id=session_id,
        mode=mode,
    )
