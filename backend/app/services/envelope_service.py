from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException

from ..dsl_models import DuiDslDocument
from ..models import A2UiEnvelope
from ..storage import ManifestStore
from .dsl_service import DslService
from .ui_service import UiService


class EnvelopeService:
    def __init__(self, store: ManifestStore, ui_service: UiService, dsl_service: DslService):
        self.store = store
        self.ui_service = ui_service
        self.dsl_service = dsl_service

    def handle(self, *, envelope: A2UiEnvelope, surface_id: str, session_id: str, mode: str) -> A2UiEnvelope:
        surface_context = self.store.get_surface_context(surface_id)
        payload = self._dispatch(
            envelope=envelope,
            surface_id=surface_id,
            session_id=session_id,
            mode=mode,
        )
        return self._response(
            envelope,
            session_id,
            surface_id,
            mode,
            surface_context["catalog_version"],
            self._response_message_type(envelope.message_type),
            payload,
        )

    def _dispatch(self, *, envelope: A2UiEnvelope, surface_id: str, session_id: str, mode: str) -> dict[str, object]:
        handlers: dict[str, Callable[[], dict[str, object]]] = {
            "manifest.current.request": lambda: self._handle_manifest_current(surface_id=surface_id),
            "manifest.revisions.request": lambda: self._handle_manifest_revisions(surface_id=surface_id),
            "dsl.current.request": lambda: self._handle_dsl_current(surface_id=surface_id),
            "dsl.intent.request": lambda: self._handle_dsl_intent(envelope=envelope, surface_id=surface_id, mode=mode),
            "dsl.parse.request": lambda: self._handle_dsl_parse(envelope=envelope, surface_id=surface_id),
            "dsl.revisions.request": lambda: self._handle_dsl_revisions(surface_id=surface_id),
            "dsl.validate.request": lambda: self._handle_dsl_validate(envelope=envelope, surface_id=surface_id),
            "dsl.commit.request": lambda: self._handle_dsl_commit(envelope=envelope, surface_id=surface_id),
            "intent.request": lambda: self._handle_intent(
                envelope=envelope,
                surface_id=surface_id,
                session_id=session_id,
                mode=mode,
            ),
            "commit.request": lambda: self._handle_commit(
                envelope=envelope,
                surface_id=surface_id,
                session_id=session_id,
            ),
            "revert.request": lambda: self._handle_revert(envelope=envelope, surface_id=surface_id),
        }
        handler = handlers.get(envelope.message_type)
        if handler is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported message_type '{envelope.message_type}' for /a2ui/envelope",
            )
        return handler()

    def _handle_manifest_current(self, *, surface_id: str) -> dict[str, object]:
        manifest = self.store.get_current_manifest(surface_id=surface_id)
        return {"manifest": manifest.model_dump(mode="json")}

    def _handle_manifest_revisions(self, *, surface_id: str) -> dict[str, object]:
        revisions = self.store.list_revisions(surface_id=surface_id)
        return {"revisions": [revision.model_dump(mode="json") for revision in revisions]}

    def _handle_dsl_current(self, *, surface_id: str) -> dict[str, object]:
        document = self.store.get_current_dsl_document(surface_id=surface_id)
        return {"document": document.model_dump(mode="json")}

    def _handle_dsl_intent(self, *, envelope: A2UiEnvelope, surface_id: str, mode: str) -> dict[str, object]:
        prompt = self._read_required_str(envelope.payload, "user_prompt", message_type=envelope.message_type)
        response = self.dsl_service.build_intent(user_prompt=prompt, surface_id=surface_id, mode=mode)
        return response.model_dump(mode="json")

    def _handle_dsl_parse(self, *, envelope: A2UiEnvelope, surface_id: str) -> dict[str, object]:
        source_text = self._read_required_str(envelope.payload, "source_text", message_type=envelope.message_type)
        response = self.dsl_service.build_parse(source_text=source_text, surface_id=surface_id)
        return response.model_dump(mode="json")

    def _handle_dsl_revisions(self, *, surface_id: str) -> dict[str, object]:
        revisions = self.store.list_dsl_revisions(surface_id=surface_id)
        return {"documents": [revision.model_dump(mode="json") for revision in revisions]}

    def _handle_dsl_validate(self, *, envelope: A2UiEnvelope, surface_id: str) -> dict[str, object]:
        document = self._read_document(envelope.payload, message_type=envelope.message_type)
        response = self.dsl_service.build_validate(document=document, surface_id=surface_id)
        return response.model_dump(mode="json")

    def _handle_dsl_commit(self, *, envelope: A2UiEnvelope, surface_id: str) -> dict[str, object]:
        document = self._read_document(envelope.payload, message_type=envelope.message_type)
        approved_by = self._read_optional_str(envelope.payload, "approved_by")
        response = self.dsl_service.build_commit(
            document=document,
            surface_id=surface_id,
            approved_by=approved_by,
            expected_manifest_revision=self._read_optional_int(envelope.payload, "expected_manifest_revision"),
            expected_dsl_revision=self._read_optional_int(envelope.payload, "expected_dsl_revision"),
        )
        return response.model_dump(mode="json")

    def _handle_intent(
        self,
        *,
        envelope: A2UiEnvelope,
        surface_id: str,
        session_id: str,
        mode: str,
    ) -> dict[str, object]:
        prompt = self._read_required_str(envelope.payload, "user_prompt", message_type=envelope.message_type)
        current_manifest_id = self._read_optional_str(envelope.payload, "current_manifest_id")
        response = self.ui_service.build_intent(
            user_prompt=prompt,
            current_manifest_id=current_manifest_id,
            mode=mode,
            surface_id=surface_id,
            session_id=session_id,
            turn_id=envelope.turn_id,
        )
        return response.model_dump(mode="json")

    def _handle_commit(self, *, envelope: A2UiEnvelope, surface_id: str, session_id: str) -> dict[str, object]:
        patch_plan_id = self._read_required_str(envelope.payload, "patch_plan_id", message_type=envelope.message_type)
        response = self.ui_service.build_commit(
            patch_plan_id=patch_plan_id,
            surface_id=surface_id,
            session_id=session_id,
            approved_by=self._read_optional_str(envelope.payload, "approved_by"),
            turn_id=envelope.turn_id,
            expected_base_revision=self._read_optional_int(envelope.payload, "expected_base_revision"),
        )
        return response.model_dump(mode="json")

    def _handle_revert(self, *, envelope: A2UiEnvelope, surface_id: str) -> dict[str, object]:
        target_revision = self._read_optional_int(envelope.payload, "target_revision")
        if target_revision is None:
            raise HTTPException(status_code=400, detail=f"{envelope.message_type} requires integer payload.target_revision")
        response = self.ui_service.build_revert(
            target_revision=target_revision,
            surface_id=surface_id,
            approved_by=self._read_optional_str(envelope.payload, "approved_by"),
        )
        return response.model_dump(mode="json")

    @staticmethod
    def _response_message_type(message_type: str) -> str:
        if not message_type.endswith(".request"):
            raise HTTPException(status_code=400, detail=f"Unsupported message_type '{message_type}' for /a2ui/envelope")
        return f"{message_type[:-len('.request')]}.response"

    @staticmethod
    def _read_required_str(payload: dict[str, object], key: str, *, message_type: str) -> str:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        raise HTTPException(status_code=400, detail=f"{message_type} requires non-empty payload.{key}")

    @staticmethod
    def _read_optional_str(payload: dict[str, object], key: str) -> str | None:
        value = payload.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return None

    @staticmethod
    def _read_document(payload: dict[str, object], *, message_type: str) -> DuiDslDocument:
        document_raw = payload.get("document")
        if not isinstance(document_raw, dict):
            raise HTTPException(status_code=400, detail=f"{message_type} requires payload.document object")
        return DuiDslDocument.model_validate(document_raw)

    @staticmethod
    def _read_optional_int(payload: dict[str, object], key: str) -> int | None:
        value = payload.get(key)
        if value is None:
            return None
        if not isinstance(value, int):
            raise HTTPException(status_code=400, detail=f"{key} must be integer when provided")
        return value

    @staticmethod
    def _response(
        request_envelope: A2UiEnvelope,
        session_id: str,
        surface_id: str,
        mode: str,
        catalog_version: str,
        message_type: str,
        payload: dict[str, object],
    ) -> A2UiEnvelope:
        return A2UiEnvelope(
            session_id=session_id,
            surface_id=surface_id,
            turn_id=request_envelope.turn_id,
            mode=mode,
            catalog_version=catalog_version,
            message_type=message_type,
            payload=payload,
        )
