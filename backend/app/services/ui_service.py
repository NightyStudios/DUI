from __future__ import annotations

from fastapi import HTTPException

from ..consistency import enforce_cross_surface_theme_consistency
from ..dsl_projection import build_dsl_document_from_manifest
from ..intent_engine import IntentEngine
from ..manifest_service import apply_patch_operations, clone_with_revision
from ..models import (
    DEFAULT_SESSION_ID,
    DuiMode,
    IntentResponse,
    RevertResponse,
    CommitResponse,
)
from ..policy import PolicyEngine
from ..storage import ManifestStore
from ..telemetry import TELEMETRY


class UiService:
    def __init__(self, store: ManifestStore):
        self.store = store

    def build_intent(
        self,
        *,
        user_prompt: str,
        current_manifest_id: str | None,
        mode: DuiMode,
        surface_id: str,
        session_id: str,
        turn_id: str | None = None,
    ) -> IntentResponse:
        with TELEMETRY.track("ui.intent"):
            current_manifest = self.store.get_current_manifest(surface_id=surface_id)
            if current_manifest_id and current_manifest_id != current_manifest.manifest_id:
                raise HTTPException(status_code=409, detail="current_manifest_id is stale")

            patch_plan = IntentEngine.build_patch_plan(user_prompt, current_manifest, mode=mode)
            patch_plan.surface_id = surface_id
            patch_plan.session_id = session_id
            patch_plan.turn_id = turn_id
            patch_plan.base_manifest_id = current_manifest.manifest_id
            patch_plan.base_revision = current_manifest.revision

            policy_result = PolicyEngine.validate_operations(current_manifest, patch_plan.operations, mode=mode)
            if policy_result.errors:
                patch_plan.status = "rejected"
                patch_plan.warnings.extend(policy_result.errors)
                self.store.save_patch_plan(patch_plan, surface_id=surface_id)
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
            preview.revision = current_manifest.revision
            preview.manifest_id = current_manifest.manifest_id

            self.store.save_patch_plan(patch_plan, surface_id=surface_id)
            return IntentResponse(
                patch_plan=patch_plan,
                preview_manifest=preview,
                warnings=patch_plan.warnings,
            )

    def build_commit(
        self,
        *,
        patch_plan_id: str,
        surface_id: str,
        session_id: str,
        turn_id: str | None = None,
        expected_base_revision: int | None = None,
    ) -> CommitResponse:
        with TELEMETRY.track("ui.commit"):
            patch_plan = self.store.get_patch_plan(patch_plan_id, surface_id=surface_id)
            if not patch_plan:
                patch_plan = self.store.get_patch_plan(patch_plan_id, surface_id=None)
            if not patch_plan:
                raise HTTPException(status_code=404, detail="patch_plan_id not found")

            if patch_plan.surface_id and patch_plan.surface_id != surface_id:
                raise HTTPException(status_code=409, detail="patch_plan belongs to another surface")
            if patch_plan.status != "draft":
                raise HTTPException(status_code=409, detail=f"patch_plan is already {patch_plan.status}")

            current_manifest = self.store.get_current_manifest(surface_id=surface_id)
            current_document = self.store.get_current_dsl_document(surface_id=surface_id)

            if patch_plan.base_revision is not None and current_manifest.revision != patch_plan.base_revision:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Patch plan base revision is stale",
                        "current_revision": current_manifest.revision,
                        "expected_revision": patch_plan.base_revision,
                    },
                )
            if expected_base_revision is not None and current_manifest.revision != expected_base_revision:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Commit request uses stale base revision",
                        "current_revision": current_manifest.revision,
                        "expected_revision": expected_base_revision,
                    },
                )

            policy_result = PolicyEngine.validate_operations(current_manifest, patch_plan.operations, mode=patch_plan.mode)
            if policy_result.errors:
                raise HTTPException(
                    status_code=400,
                    detail={"message": "Patch plan failed policy on commit", "errors": policy_result.errors},
                )

            next_manifest = apply_patch_operations(current_manifest, patch_plan.operations)
            next_manifest.metadata["surface_id"] = surface_id
            next_manifest.metadata["write_source"] = "patch_plan"
            next_manifest.metadata["patch_plan_id"] = patch_plan.patch_plan_id

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

            next_document = build_dsl_document_from_manifest(
                next_manifest,
                current_document=current_document,
                created_by=session_id or DEFAULT_SESSION_ID,
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
                        "message": "state changed during commit; retry intent",
                        "current_manifest_revision": current_manifest_revision,
                        "current_dsl_revision": current_dsl_revision,
                    },
                )

            patch_plan.surface_id = surface_id
            patch_plan.session_id = session_id or DEFAULT_SESSION_ID
            patch_plan.turn_id = turn_id or patch_plan.turn_id
            patch_plan.status = "committed"
            self.store.update_patch_plan(patch_plan, surface_id=surface_id)

            return CommitResponse(manifest=next_manifest)

    def build_revert(self, *, target_revision: int, surface_id: str, approved_by: str | None = None) -> RevertResponse:
        with TELEMETRY.track("ui.revert"):
            current_manifest = self.store.get_current_manifest(surface_id=surface_id)
            current_document = self.store.get_current_dsl_document(surface_id=surface_id)
            target_manifest = self.store.get_revision(target_revision, surface_id=surface_id)
            if not target_manifest:
                raise HTTPException(status_code=404, detail="target revision not found")

            reverted = clone_with_revision(target_manifest, current_manifest.revision + 1)
            reverted.metadata["reverted_from"] = str(current_manifest.revision)
            reverted.metadata["reverted_to"] = str(target_revision)
            reverted.metadata["surface_id"] = surface_id
            reverted.metadata["write_source"] = "revert"

            next_document = build_dsl_document_from_manifest(
                reverted,
                current_document=current_document,
                created_by=approved_by or DEFAULT_SESSION_ID,
            )
            ok, current_manifest_revision, current_dsl_revision = self.store.append_manifest_and_dsl_revision(
                manifest=reverted,
                document=next_document,
                surface_id=surface_id,
                expected_manifest_revision=current_manifest.revision,
                expected_dsl_revision=current_document.meta.revision,
            )
            if not ok:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "state changed during revert; retry",
                        "current_manifest_revision": current_manifest_revision,
                        "current_dsl_revision": current_dsl_revision,
                    },
                )

            return RevertResponse(manifest=reverted)
