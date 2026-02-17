from __future__ import annotations

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

        if envelope.message_type == "manifest.current.request":
            manifest = self.store.get_current_manifest(surface_id=surface_id)
            payload = {"manifest": manifest.model_dump(mode="json")}
            return self._response(envelope, session_id, surface_id, mode, surface_context["catalog_version"], "manifest.current.response", payload)

        if envelope.message_type == "manifest.revisions.request":
            revisions = self.store.list_revisions(surface_id=surface_id)
            payload = {"revisions": [revision.model_dump(mode="json") for revision in revisions]}
            return self._response(envelope, session_id, surface_id, mode, surface_context["catalog_version"], "manifest.revisions.response", payload)

        if envelope.message_type == "dsl.current.request":
            document = self.store.get_current_dsl_document(surface_id=surface_id)
            payload = {"document": document.model_dump(mode="json")}
            return self._response(envelope, session_id, surface_id, mode, surface_context["catalog_version"], "dsl.current.response", payload)

        if envelope.message_type == "dsl.intent.request":
            prompt = str(envelope.payload.get("user_prompt", "")).strip()
            if not prompt:
                raise HTTPException(status_code=400, detail="dsl.intent.request requires payload.user_prompt")
            response = self.dsl_service.build_intent(user_prompt=prompt, surface_id=surface_id, mode=mode)
            return self._response(envelope, session_id, surface_id, mode, surface_context["catalog_version"], "dsl.intent.response", response.model_dump(mode="json"))

        if envelope.message_type == "dsl.parse.request":
            source_text_raw = envelope.payload.get("source_text")
            if not isinstance(source_text_raw, str) or not source_text_raw.strip():
                raise HTTPException(status_code=400, detail="dsl.parse.request requires non-empty payload.source_text")
            response = self.dsl_service.build_parse(source_text=source_text_raw, surface_id=surface_id)
            return self._response(envelope, session_id, surface_id, mode, surface_context["catalog_version"], "dsl.parse.response", response.model_dump(mode="json"))

        if envelope.message_type == "dsl.revisions.request":
            revisions = self.store.list_dsl_revisions(surface_id=surface_id)
            payload = {"documents": [revision.model_dump(mode="json") for revision in revisions]}
            return self._response(envelope, session_id, surface_id, mode, surface_context["catalog_version"], "dsl.revisions.response", payload)

        if envelope.message_type == "dsl.validate.request":
            document_raw = envelope.payload.get("document")
            if not isinstance(document_raw, dict):
                raise HTTPException(status_code=400, detail="dsl.validate.request requires payload.document object")
            document = DuiDslDocument.model_validate(document_raw)
            response = self.dsl_service.build_validate(document=document, surface_id=surface_id)
            return self._response(envelope, session_id, surface_id, mode, surface_context["catalog_version"], "dsl.validate.response", response.model_dump(mode="json"))

        if envelope.message_type == "dsl.commit.request":
            document_raw = envelope.payload.get("document")
            if not isinstance(document_raw, dict):
                raise HTTPException(status_code=400, detail="dsl.commit.request requires payload.document object")
            approved_by_raw = envelope.payload.get("approved_by")
            approved_by = str(approved_by_raw) if isinstance(approved_by_raw, str) else None
            expected_manifest_revision = self._read_optional_int(envelope.payload, "expected_manifest_revision")
            expected_dsl_revision = self._read_optional_int(envelope.payload, "expected_dsl_revision")
            document = DuiDslDocument.model_validate(document_raw)
            response = self.dsl_service.build_commit(
                document=document,
                surface_id=surface_id,
                approved_by=approved_by,
                expected_manifest_revision=expected_manifest_revision,
                expected_dsl_revision=expected_dsl_revision,
            )
            return self._response(envelope, session_id, surface_id, mode, surface_context["catalog_version"], "dsl.commit.response", response.model_dump(mode="json"))

        if envelope.message_type == "intent.request":
            prompt = str(envelope.payload.get("user_prompt", "")).strip()
            if not prompt:
                raise HTTPException(status_code=400, detail="intent.request requires payload.user_prompt")
            current_manifest_id = envelope.payload.get("current_manifest_id")
            if current_manifest_id is not None:
                current_manifest_id = str(current_manifest_id)
            intent_response = self.ui_service.build_intent(
                user_prompt=prompt,
                current_manifest_id=current_manifest_id,
                mode=mode,
                surface_id=surface_id,
                session_id=session_id,
                turn_id=envelope.turn_id,
            )
            return self._response(envelope, session_id, surface_id, mode, surface_context["catalog_version"], "intent.response", intent_response.model_dump(mode="json"))

        if envelope.message_type == "commit.request":
            patch_plan_id = str(envelope.payload.get("patch_plan_id", "")).strip()
            if not patch_plan_id:
                raise HTTPException(status_code=400, detail="commit.request requires payload.patch_plan_id")
            expected_base_revision = self._read_optional_int(envelope.payload, "expected_base_revision")
            commit_response = self.ui_service.build_commit(
                patch_plan_id=patch_plan_id,
                surface_id=surface_id,
                session_id=session_id,
                turn_id=envelope.turn_id,
                expected_base_revision=expected_base_revision,
            )
            return self._response(envelope, session_id, surface_id, mode, surface_context["catalog_version"], "commit.response", commit_response.model_dump(mode="json"))

        if envelope.message_type == "revert.request":
            target_revision_raw = envelope.payload.get("target_revision")
            if not isinstance(target_revision_raw, int):
                raise HTTPException(status_code=400, detail="revert.request requires integer payload.target_revision")
            approved_by_raw = envelope.payload.get("approved_by")
            approved_by = str(approved_by_raw) if isinstance(approved_by_raw, str) else None
            revert_response = self.ui_service.build_revert(
                target_revision=target_revision_raw,
                surface_id=surface_id,
                approved_by=approved_by,
            )
            return self._response(envelope, session_id, surface_id, mode, surface_context["catalog_version"], "revert.response", revert_response.model_dump(mode="json"))

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported message_type '{envelope.message_type}' for /a2ui/envelope",
        )

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
