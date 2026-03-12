from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from ..consistency import enforce_cross_surface_theme_consistency
from ..dsl_compiler import compile_dsl_document_to_manifest
from ..dsl_legacy_adapter import canonicalize_document
from ..dsl_models import (
    DuiDslCommitResponse,
    DuiDslDocument,
    DuiDslIntentResponse,
    DuiDslParseResponse,
    DuiDslTransformResponse,
    DuiDslValidateResponse,
)
from ..dsl_patch_service import apply_patch_operations_to_document
from ..dsl_text_parser import DuiLangParseError, parse_dui_lang
from ..dsl_text_serializer import serialize_dui_lang
from ..dsl_validator import DuiDslValidator
from ..intent_engine import IntentEngine
from ..models import DEFAULT_SURFACE_ID, DuiMode
from ..policy import PolicyEngine
from ..storage import ManifestStore
from ..telemetry import TELEMETRY


class DslService:
    def __init__(self, store: ManifestStore):
        self.store = store

    def build_validate(self, *, document: DuiDslDocument, surface_id: str) -> DuiDslValidateResponse:
        with TELEMETRY.track("dui.validate"):
            normalized_document = canonicalize_document(document)
            normalized_document.surface.id = surface_id
            validation_result = DuiDslValidator.validate(normalized_document)
            if not validation_result.valid:
                return DuiDslValidateResponse(result=validation_result, compiled_manifest=None)

            current_manifest = self.store.get_current_manifest(surface_id=surface_id)
            preview_manifest = compile_dsl_document_to_manifest(
                normalized_document,
                manifest_revision=current_manifest.revision,
                manifest_id=current_manifest.manifest_id,
            )
            return DuiDslValidateResponse(result=validation_result, compiled_manifest=preview_manifest)

    def build_parse(self, *, source_text: str, surface_id: str | None = None) -> DuiDslParseResponse:
        with TELEMETRY.track("dui.parse"):
            try:
                document = parse_dui_lang(source_text)
            except DuiLangParseError as error:
                raise HTTPException(
                    status_code=400,
                    detail={"message": str(error), "line": error.line, "column": error.column},
                ) from error
            except Exception as error:  # noqa: BLE001
                raise HTTPException(status_code=400, detail=f"Failed to parse DUI source: {type(error).__name__}") from error

            resolved_surface_id = (surface_id or "").strip()
            if not resolved_surface_id:
                resolved_surface_id = document.surface.id.strip() if document.surface.id.strip() else DEFAULT_SURFACE_ID

            document.surface.id = resolved_surface_id
            document = canonicalize_document(document)
            validation_result = DuiDslValidator.validate(document)
            compiled_manifest = None
            if validation_result.valid:
                current_manifest = self.store.get_current_manifest(surface_id=resolved_surface_id)
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

    def build_transform(
        self,
        *,
        source_text: str,
        user_prompt: str,
        surface_id: str | None,
        mode: DuiMode,
    ) -> DuiDslTransformResponse:
        with TELEMETRY.track("dui.transform"):
            try:
                current_document = parse_dui_lang(source_text)
            except DuiLangParseError as error:
                raise HTTPException(
                    status_code=400,
                    detail={"message": str(error), "line": error.line, "column": error.column},
                ) from error
            except Exception as error:  # noqa: BLE001
                raise HTTPException(status_code=400, detail=f"Failed to parse DUI source: {type(error).__name__}") from error

            resolved_surface_id = (surface_id or "").strip()
            if not resolved_surface_id:
                resolved_surface_id = current_document.surface.id.strip() if current_document.surface.id.strip() else DEFAULT_SURFACE_ID

            current_document = canonicalize_document(current_document)
            current_document.surface.id = resolved_surface_id
            current_manifest = compile_dsl_document_to_manifest(
                current_document,
                manifest_revision=max(current_document.meta.revision, 1),
            )

            patch_plan = IntentEngine.build_patch_plan(user_prompt, current_manifest, mode=mode)
            patch_plan.surface_id = resolved_surface_id
            policy_result = PolicyEngine.validate_operations(current_manifest, patch_plan.operations, mode=mode)
            if policy_result.errors:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "DUI transform rejected by operation policy",
                        "errors": policy_result.errors,
                        "warnings": [*patch_plan.warnings, *policy_result.warnings],
                        "operations": [operation.model_dump(mode="json") for operation in patch_plan.operations],
                    },
                )

            patch_plan.warnings.extend(policy_result.warnings)
            next_document = apply_patch_operations_to_document(current_document, patch_plan.operations)
            next_document.surface.id = resolved_surface_id

            mode_errors = self._enforce_mode(current_document=current_document, next_document=next_document, mode=mode)
            if mode_errors:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "DUI transform rejected by mode policy",
                        "errors": mode_errors,
                        "warnings": patch_plan.warnings,
                        "operations": [operation.model_dump(mode="json") for operation in patch_plan.operations],
                    },
                )

            validation_result = DuiDslValidator.validate(next_document)
            if not validation_result.valid:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "DUI transform produced invalid document",
                        "errors": [issue.model_dump(mode="json") for issue in validation_result.errors],
                        "warnings": patch_plan.warnings,
                        "operations": [operation.model_dump(mode="json") for operation in patch_plan.operations],
                    },
                )

            preview_manifest = compile_dsl_document_to_manifest(
                next_document,
                manifest_revision=current_manifest.revision,
                manifest_id=current_manifest.manifest_id,
            )
            return DuiDslTransformResponse(
                source_text=serialize_dui_lang(next_document),
                document=next_document,
                validation_result=validation_result,
                preview_manifest=preview_manifest,
                operations=patch_plan.operations,
                warnings=patch_plan.warnings,
            )

    def build_intent(
        self,
        *,
        user_prompt: str,
        surface_id: str,
        mode: DuiMode,
    ) -> DuiDslIntentResponse:
        with TELEMETRY.track("dui.intent"):
            current_document = canonicalize_document(self.store.get_current_dsl_document(surface_id=surface_id))
            current_manifest = self.store.get_current_manifest(surface_id=surface_id)
            patch_plan = IntentEngine.build_patch_plan(user_prompt, current_manifest, mode=mode)
            patch_plan.surface_id = surface_id
            policy_result = PolicyEngine.validate_operations(current_manifest, patch_plan.operations, mode=mode)
            if policy_result.errors:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "DUI intent rejected by operation policy",
                        "errors": policy_result.errors,
                        "warnings": [*patch_plan.warnings, *policy_result.warnings],
                        "operations": [operation.model_dump(mode="json") for operation in patch_plan.operations],
                    },
                )

            patch_plan.warnings.extend(policy_result.warnings)
            next_document = apply_patch_operations_to_document(current_document, patch_plan.operations)
            next_document.surface.id = surface_id

            mode_errors = self._enforce_mode(current_document=current_document, next_document=next_document, mode=mode)
            if mode_errors:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "DUI intent rejected by mode policy",
                        "errors": mode_errors,
                        "warnings": patch_plan.warnings,
                        "operations": [operation.model_dump(mode="json") for operation in patch_plan.operations],
                    },
                )

            validation_result = DuiDslValidator.validate(next_document)
            if not validation_result.valid:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "DUI intent produced invalid document",
                        "errors": [issue.model_dump(mode="json") for issue in validation_result.errors],
                        "warnings": patch_plan.warnings,
                        "operations": [operation.model_dump(mode="json") for operation in patch_plan.operations],
                    },
                )

            preview_manifest = compile_dsl_document_to_manifest(
                next_document,
                manifest_revision=current_manifest.revision,
                manifest_id=current_manifest.manifest_id,
            )
            return DuiDslIntentResponse(
                document=next_document,
                validation_result=validation_result,
                preview_manifest=preview_manifest,
                operations=patch_plan.operations,
                warnings=patch_plan.warnings,
            )

    def build_commit(
        self,
        *,
        document: DuiDslDocument,
        surface_id: str,
        approved_by: str | None = None,
        expected_manifest_revision: int | None = None,
        expected_dsl_revision: int | None = None,
    ) -> DuiDslCommitResponse:
        with TELEMETRY.track("dui.commit"):
            normalized_document = canonicalize_document(document)
            normalized_document.surface.id = surface_id
            validation_result = DuiDslValidator.validate(normalized_document)
            if not validation_result.valid:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "DUI document failed validation",
                        "errors": [issue.model_dump(mode="json") for issue in validation_result.errors],
                    },
                )

            current_manifest = self.store.get_current_manifest(surface_id=surface_id)
            current_document = canonicalize_document(self.store.get_current_dsl_document(surface_id=surface_id))
            if expected_manifest_revision is not None and current_manifest.revision != expected_manifest_revision:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "stale manifest revision for DUI commit",
                        "current_revision": current_manifest.revision,
                        "expected_revision": expected_manifest_revision,
                    },
                )
            if expected_dsl_revision is not None and current_document.meta.revision != expected_dsl_revision:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "stale DUI revision for commit",
                        "current_revision": current_document.meta.revision,
                        "expected_revision": expected_dsl_revision,
                    },
                )

            next_document = normalized_document.model_copy(deep=True)
            next_document.meta.revision = current_document.meta.revision + 1
            next_document.meta.created_at = datetime.now(timezone.utc)
            if approved_by:
                next_document.meta.created_by = approved_by

            next_manifest = compile_dsl_document_to_manifest(
                next_document,
                manifest_revision=current_manifest.revision + 1,
            )
            next_manifest.metadata["surface_id"] = surface_id
            next_manifest.metadata["write_source"] = "dui"

            consistency_errors = enforce_cross_surface_theme_consistency(
                self.store,
                surface_id=surface_id,
                candidate_manifest=next_manifest,
            )
            if consistency_errors:
                raise HTTPException(
                    status_code=409,
                    detail={"message": "Cross-surface consistency check failed", "errors": consistency_errors},
                )

            ok, current_manifest_revision, current_dsl_revision = self.store.append_manifest_and_dsl_revision(
                manifest=next_manifest,
                document=next_document,
                surface_id=surface_id,
                expected_manifest_revision=current_manifest.revision,
                expected_dsl_revision=current_document.meta.revision,
            )
            if not ok:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "state changed during DUI commit; retry",
                        "current_manifest_revision": current_manifest_revision,
                        "current_dsl_revision": current_dsl_revision,
                    },
                )

            return DuiDslCommitResponse(document=next_document, manifest=next_manifest)

    @staticmethod
    def _enforce_mode(
        *,
        current_document: DuiDslDocument,
        next_document: DuiDslDocument,
        mode: DuiMode,
    ) -> list[str]:
        errors: list[str] = []
        if mode == "safe":
            guarded_fields = (
                ("pages", current_document.pages, next_document.pages),
                ("groups", current_document.groups, next_document.groups),
                ("widgets", current_document.widgets, next_document.widgets),
                ("bindings", current_document.bindings, next_document.bindings),
                ("actions", current_document.actions, next_document.actions),
                ("layout_constraints", current_document.layout_constraints, next_document.layout_constraints),
            )
            for field_name, current_value, next_value in guarded_fields:
                if current_value != next_value:
                    errors.append(f"safe mode allows only theme updates ({field_name} cannot change)")
        return errors
