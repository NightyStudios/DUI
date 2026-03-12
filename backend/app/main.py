from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .app_runtime import AppRuntime, StoreProxy, create_runtime, get_default_runtime
from .config import load_project_env, resolve_cors_origins
from .dsl_models import (
    DuiDslCommitRequest,
    DuiDslCommitResponse,
    DuiDslDocument,
    DuiDslIntentRequest,
    DuiDslIntentResponse,
    DuiDslParseRequest,
    DuiDslParseResponse,
    DuiDslTransformRequest,
    DuiDslTransformResponse,
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
from .storage import ManifestStore
from .telemetry import TELEMETRY

router = APIRouter()
STORE = StoreProxy()


def _resolve_runtime(request: Request | None = None) -> AppRuntime:
    if request is not None:
        runtime = getattr(request.app.state, "runtime", None)
        if isinstance(runtime, AppRuntime):
            return runtime
    return get_default_runtime()


def _build_lifespan(provided_runtime: AppRuntime | None, provided_store: ManifestStore | None):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.runtime = provided_runtime or create_runtime(provided_store)
        yield

    return lifespan


def create_app(*, runtime: AppRuntime | None = None, store: ManifestStore | None = None) -> FastAPI:
    load_project_env()
    app = FastAPI(
        title="Adaptive UI PoC API",
        version="0.2.0",
        lifespan=_build_lifespan(runtime, store),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolve_cors_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ops/metrics")
def get_metrics() -> dict[str, object]:
    return TELEMETRY.snapshot()


@router.post("/dev/reset-seed")
def reset_seed(http_request: Request) -> dict[str, str]:
    _resolve_runtime(http_request).store.reset_to_seed()
    return {"status": "ok", "message": "seed manifest restored"}


@router.get("/lms/dashboard")
def get_lms_dashboard() -> dict:
    return get_dashboard_payload()


@router.get("/lms/lesson/{lesson_id}")
def get_lesson(lesson_id: str) -> dict:
    return get_lesson_payload_or_404(lesson_id)


@router.get("/ui/manifest/current")
def get_current_manifest(http_request: Request, surface_id: str = DEFAULT_SURFACE_ID):
    return _resolve_runtime(http_request).store.get_current_manifest(surface_id=surface_id)


@router.get("/ui/manifest/revisions")
def get_manifest_revisions(http_request: Request, surface_id: str = DEFAULT_SURFACE_ID):
    return _resolve_runtime(http_request).store.list_revisions(surface_id=surface_id)


@router.get("/ui/surfaces")
def get_surfaces(http_request: Request) -> list[dict[str, str]]:
    return _resolve_runtime(http_request).store.list_surfaces()


@router.get("/ui/dsl/current", response_model=DuiDslDocument)
def get_current_dsl(http_request: Request, surface_id: str = DEFAULT_SURFACE_ID) -> DuiDslDocument:
    return _resolve_runtime(http_request).store.get_current_dsl_document(surface_id=surface_id)


@router.get("/ui/dsl/revisions", response_model=list[DuiDslDocument])
def get_dsl_revisions(http_request: Request, surface_id: str = DEFAULT_SURFACE_ID) -> list[DuiDslDocument]:
    return _resolve_runtime(http_request).store.list_dsl_revisions(surface_id=surface_id)


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
    return get_default_runtime().ui_service.build_intent(
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
    approved_by: str | None = None,
    turn_id: str | None = None,
    expected_base_revision: int | None = None,
) -> CommitResponse:
    return get_default_runtime().ui_service.build_commit(
        patch_plan_id=patch_plan_id,
        surface_id=surface_id,
        session_id=session_id,
        approved_by=approved_by,
        turn_id=turn_id,
        expected_base_revision=expected_base_revision,
    )


def build_revert(*, target_revision: int, surface_id: str, approved_by: str | None = None) -> RevertResponse:
    return get_default_runtime().ui_service.build_revert(
        target_revision=target_revision,
        surface_id=surface_id,
        approved_by=approved_by,
    )


def build_dsl_validate(*, document: DuiDslDocument, surface_id: str) -> DuiDslValidateResponse:
    return get_default_runtime().dsl_service.build_validate(document=document, surface_id=surface_id)


def build_dsl_parse(*, source_text: str, surface_id: str | None = None) -> DuiDslParseResponse:
    return get_default_runtime().dsl_service.build_parse(source_text=source_text, surface_id=surface_id)


def build_dsl_intent(*, user_prompt: str, surface_id: str, mode: DuiMode) -> DuiDslIntentResponse:
    return get_default_runtime().dsl_service.build_intent(user_prompt=user_prompt, surface_id=surface_id, mode=mode)


def build_dsl_transform(
    *,
    source_text: str,
    user_prompt: str,
    surface_id: str | None,
    mode: DuiMode,
) -> DuiDslTransformResponse:
    return get_default_runtime().dsl_service.build_transform(
        source_text=source_text,
        user_prompt=user_prompt,
        surface_id=surface_id,
        mode=mode,
    )


def build_dsl_commit(
    *,
    document: DuiDslDocument,
    surface_id: str,
    approved_by: str | None = None,
    expected_manifest_revision: int | None = None,
    expected_dsl_revision: int | None = None,
) -> DuiDslCommitResponse:
    return get_default_runtime().dsl_service.build_commit(
        document=document,
        surface_id=surface_id,
        approved_by=approved_by,
        expected_manifest_revision=expected_manifest_revision,
        expected_dsl_revision=expected_dsl_revision,
    )


@router.post("/ai/ui/intent", response_model=IntentResponse)
def ai_ui_intent(payload: IntentRequest, http_request: Request) -> IntentResponse:
    runtime = _resolve_runtime(http_request)
    surface_id = resolve_surface_id(payload.surface_id)
    mode = resolve_mode(payload.scope)
    session_id = resolve_session_id(runtime.store, surface_id=surface_id, session_id=payload.session_id)
    return runtime.ui_service.build_intent(
        user_prompt=payload.user_prompt,
        current_manifest_id=payload.current_manifest_id,
        mode=mode,
        surface_id=surface_id,
        session_id=session_id,
        turn_id=payload.turn_id,
    )


@router.post("/ai/ui/commit", response_model=CommitResponse)
def ai_ui_commit(payload: CommitRequest, http_request: Request) -> CommitResponse:
    runtime = _resolve_runtime(http_request)
    surface_id = resolve_surface_id(payload.surface_id)
    session_id = resolve_session_id(runtime.store, surface_id=surface_id, session_id=payload.session_id)
    return runtime.ui_service.build_commit(
        patch_plan_id=payload.patch_plan_id,
        surface_id=surface_id,
        session_id=session_id,
        approved_by=payload.approved_by,
        turn_id=payload.turn_id,
        expected_base_revision=payload.expected_base_revision,
    )


@router.post("/ai/ui/revert", response_model=RevertResponse)
def ai_ui_revert(payload: RevertRequest, http_request: Request) -> RevertResponse:
    runtime = _resolve_runtime(http_request)
    surface_id = resolve_surface_id(payload.surface_id)
    return runtime.ui_service.build_revert(
        target_revision=payload.target_revision,
        surface_id=surface_id,
        approved_by=payload.approved_by,
    )


@router.post("/ui/dsl/validate", response_model=DuiDslValidateResponse)
def ui_dsl_validate(payload: DuiDslValidateRequest, http_request: Request) -> DuiDslValidateResponse:
    runtime = _resolve_runtime(http_request)
    surface_id = resolve_surface_id(payload.surface_id or payload.document.surface.id)
    return runtime.dsl_service.build_validate(document=payload.document, surface_id=surface_id)


@router.post("/ui/dsl/parse", response_model=DuiDslParseResponse)
def ui_dsl_parse(payload: DuiDslParseRequest, http_request: Request) -> DuiDslParseResponse:
    runtime = _resolve_runtime(http_request)
    surface_id = payload.surface_id.strip() if payload.surface_id and payload.surface_id.strip() else None
    return runtime.dsl_service.build_parse(source_text=payload.source_text, surface_id=surface_id)


@router.post("/ai/dsl/intent", response_model=DuiDslIntentResponse)
def ai_dsl_intent(payload: DuiDslIntentRequest, http_request: Request) -> DuiDslIntentResponse:
    runtime = _resolve_runtime(http_request)
    surface_id = resolve_surface_id(payload.surface_id)
    mode = resolve_mode(payload.scope)
    return runtime.dsl_service.build_intent(user_prompt=payload.user_prompt, surface_id=surface_id, mode=mode)


@router.post("/ai/dsl/transform", response_model=DuiDslTransformResponse)
def ai_dsl_transform(payload: DuiDslTransformRequest, http_request: Request) -> DuiDslTransformResponse:
    runtime = _resolve_runtime(http_request)
    resolved_surface_id = payload.surface_id.strip() if payload.surface_id and payload.surface_id.strip() else None
    mode = resolve_mode(payload.scope)
    return runtime.dsl_service.build_transform(
        source_text=payload.source_text,
        user_prompt=payload.user_prompt,
        surface_id=resolved_surface_id,
        mode=mode,
    )


@router.post("/ui/dsl/commit", response_model=DuiDslCommitResponse)
def ui_dsl_commit(payload: DuiDslCommitRequest, http_request: Request) -> DuiDslCommitResponse:
    runtime = _resolve_runtime(http_request)
    surface_id = resolve_surface_id(payload.surface_id or payload.document.surface.id)
    return runtime.dsl_service.build_commit(
        document=payload.document,
        surface_id=surface_id,
        approved_by=payload.approved_by,
        expected_manifest_revision=payload.expected_manifest_revision,
        expected_dsl_revision=payload.expected_dsl_revision,
    )


def a2ui_envelope(envelope: A2UiEnvelope, runtime: AppRuntime | None = None) -> A2UiEnvelope:
    resolved_runtime = runtime or get_default_runtime()
    surface_id = resolve_surface_id(envelope.surface_id)
    session_id = resolve_session_id(resolved_runtime.store, surface_id=surface_id, session_id=envelope.session_id)
    mode = resolve_mode(envelope.mode)
    return resolved_runtime.envelope_service.handle(
        envelope=envelope,
        surface_id=surface_id,
        session_id=session_id,
        mode=mode,
    )


@router.post("/a2ui/envelope", response_model=A2UiEnvelope)
def a2ui_envelope_route(envelope: A2UiEnvelope, http_request: Request) -> A2UiEnvelope:
    return a2ui_envelope(envelope, runtime=_resolve_runtime(http_request))


app = create_app()
