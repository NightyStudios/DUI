from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend.app.dsl_seed import build_seed_document_for_surface
from backend.app.main import (
    STORE,
    a2ui_envelope,
    build_commit,
    build_dsl_commit,
    build_dsl_intent,
    build_dsl_parse,
    build_dsl_validate,
    build_intent,
)
from backend.app.models import A2UiEnvelope, DEFAULT_SURFACE_ID


class DuiDslServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        STORE.reset_to_seed()

    def test_store_has_seed_dsl_document(self) -> None:
        document = STORE.get_current_dsl_document(DEFAULT_SURFACE_ID)
        self.assertEqual(document.dsl_version, "dui-lang/1.0")
        self.assertEqual(document.surface.id, DEFAULT_SURFACE_ID)

    def test_build_dsl_validate_returns_preview_manifest(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        response = build_dsl_validate(document=document, surface_id=DEFAULT_SURFACE_ID)
        self.assertTrue(response.result.valid)
        self.assertIsNotNone(response.compiled_manifest)

    def test_build_dsl_validate_forces_surface_context(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        document.surface.id = "another.surface"
        response = build_dsl_validate(document=document, surface_id=DEFAULT_SURFACE_ID)
        self.assertIsNotNone(response.compiled_manifest)
        self.assertEqual(response.compiled_manifest.metadata["surface_id"], DEFAULT_SURFACE_ID)

    def test_build_dsl_commit_appends_revisions(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        response = build_dsl_commit(document=document, surface_id=DEFAULT_SURFACE_ID, approved_by="test-user")
        self.assertEqual(response.document.meta.revision, 2)
        self.assertEqual(response.manifest.revision, 2)

        dsl_revisions = STORE.list_dsl_revisions(DEFAULT_SURFACE_ID)
        manifest_revisions = STORE.list_revisions(DEFAULT_SURFACE_ID)
        self.assertEqual(len(dsl_revisions), 2)
        self.assertEqual(len(manifest_revisions), 2)

    def test_a2ui_envelope_dsl_validate(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        envelope = A2UiEnvelope(
            message_type="dsl.validate.request",
            surface_id=DEFAULT_SURFACE_ID,
            session_id="test-session",
            turn_id="turn-1",
            payload={"document": document.model_dump(mode="json")},
        )
        response = a2ui_envelope(envelope)
        self.assertEqual(response.message_type, "dsl.validate.response")
        self.assertTrue(bool(response.payload["result"]["valid"]))

    def test_build_dsl_parse_from_text(self) -> None:
        source_text = """
        surface math_lms.dashboard {
          theme { profile: default density: comfortable }
          node root: layout.page { children: [header] }
          node header: layout.region { props { zone: header } children: [course_progress] }
          node course_progress: data.kpi_card {
            props { title: "Progress", zone: header, capability_id: math.progress_overview, protected: true }
          }
        }
        """
        response = build_dsl_parse(source_text=source_text, surface_id=DEFAULT_SURFACE_ID)
        self.assertTrue(response.validation_result.valid)
        self.assertEqual(response.document.surface.id, DEFAULT_SURFACE_ID)
        self.assertIsNotNone(response.compiled_manifest)

    def test_a2ui_envelope_dsl_parse(self) -> None:
        source_text = """
        surface math_lms.dashboard {
          node root: layout.page { children: [header] }
          node header: layout.region { props { zone: header } children: [course_progress] }
          node course_progress: data.kpi_card { props { zone: header, capability_id: math.progress_overview } }
        }
        """
        envelope = A2UiEnvelope(
            message_type="dsl.parse.request",
            surface_id=DEFAULT_SURFACE_ID,
            session_id="test-session",
            turn_id="turn-2",
            payload={"source_text": source_text},
        )
        response = a2ui_envelope(envelope)
        self.assertEqual(response.message_type, "dsl.parse.response")
        self.assertTrue(bool(response.payload["validation_result"]["valid"]))

    def test_build_dsl_intent_theme_change(self) -> None:
        response = build_dsl_intent(
            user_prompt="Сделай стиль минимализм и compact",
            surface_id=DEFAULT_SURFACE_ID,
            mode="safe",
        )
        self.assertEqual(response.document.theme.profile, "minimal")
        self.assertEqual(response.document.theme.density, "compact")
        self.assertTrue(response.validation_result.valid)
        self.assertIsNotNone(response.preview_manifest)

    def test_a2ui_envelope_dsl_intent(self) -> None:
        envelope = A2UiEnvelope(
            message_type="dsl.intent.request",
            surface_id=DEFAULT_SURFACE_ID,
            session_id="test-session",
            turn_id="turn-3",
            mode="safe",
            payload={"user_prompt": "Сделай стиль минимализм"},
        )
        response = a2ui_envelope(envelope)
        self.assertEqual(response.message_type, "dsl.intent.response")
        payload = response.payload
        self.assertEqual(payload["document"]["theme"]["profile"], "minimal")
        self.assertTrue(bool(payload["validation_result"]["valid"]))

    def test_build_commit_rejects_repeated_commit_for_same_patch_plan(self) -> None:
        intent_response = build_intent(
            user_prompt="Сделай стиль minimal",
            current_manifest_id=None,
            mode="extended",
            surface_id=DEFAULT_SURFACE_ID,
            session_id="test-session",
            turn_id="turn-commit-1",
        )
        patch_plan_id = intent_response.patch_plan.patch_plan_id

        first_commit = build_commit(
            patch_plan_id=patch_plan_id,
            surface_id=DEFAULT_SURFACE_ID,
            session_id="test-session",
            turn_id="turn-commit-2",
        )
        self.assertGreaterEqual(first_commit.manifest.revision, 2)

        with self.assertRaises(HTTPException) as error_ctx:
            build_commit(
                patch_plan_id=patch_plan_id,
                surface_id=DEFAULT_SURFACE_ID,
                session_id="test-session",
                turn_id="turn-commit-3",
            )
        self.assertEqual(error_ctx.exception.status_code, 409)

    def test_build_intent_tracks_base_revision(self) -> None:
        intent_response = build_intent(
            user_prompt="Сделай стиль minimal",
            current_manifest_id=None,
            mode="extended",
            surface_id=DEFAULT_SURFACE_ID,
            session_id="test-session",
            turn_id="turn-base-1",
        )
        self.assertIsNotNone(intent_response.patch_plan.base_revision)
        self.assertEqual(intent_response.patch_plan.base_revision, 1)
        self.assertEqual(intent_response.patch_plan.base_manifest_id, intent_response.preview_manifest.manifest_id)

    def test_manifest_patch_commit_keeps_dui_synced(self) -> None:
        intent_response = build_intent(
            user_prompt="Сделай стиль minimal",
            current_manifest_id=None,
            mode="extended",
            surface_id=DEFAULT_SURFACE_ID,
            session_id="test-session",
            turn_id="turn-sync-1",
        )
        build_commit(
            patch_plan_id=intent_response.patch_plan.patch_plan_id,
            surface_id=DEFAULT_SURFACE_ID,
            session_id="test-session",
            turn_id="turn-sync-2",
            expected_base_revision=1,
        )
        current_document = STORE.get_current_dsl_document(DEFAULT_SURFACE_ID)
        self.assertEqual(current_document.meta.revision, 2)
        self.assertEqual(current_document.theme.profile, "minimal")

    def test_build_dsl_commit_rejects_stale_revision_expectation(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        with self.assertRaises(HTTPException) as error_ctx:
            build_dsl_commit(
                document=document,
                surface_id=DEFAULT_SURFACE_ID,
                expected_manifest_revision=999,
                expected_dsl_revision=999,
            )
        self.assertEqual(error_ctx.exception.status_code, 409)

    def test_build_intent_fallback_supports_red_buttons_prompt(self) -> None:
        with patch.dict(os.environ, {"DUI_LLM_PROVIDER": "disabled"}, clear=False):
            response = build_intent(
                user_prompt="Сделай все кнопки красными",
                current_manifest_id=None,
                mode="extended",
                surface_id=DEFAULT_SURFACE_ID,
                session_id="test-session",
                turn_id="turn-red-buttons-ui",
            )

        set_theme_ops = [operation for operation in response.patch_plan.operations if operation.op == "set_theme_tokens"]
        self.assertTrue(set_theme_ops)
        accent_values = [operation.tokens.get("accent") for operation in set_theme_ops if operation.tokens]
        self.assertIn("#dc2626", accent_values)

    def test_build_dui_intent_fallback_supports_red_buttons_prompt(self) -> None:
        with patch.dict(os.environ, {"DUI_LLM_PROVIDER": "disabled"}, clear=False):
            response = build_dsl_intent(
                user_prompt="Сделай все кнопки красными",
                surface_id=DEFAULT_SURFACE_ID,
                mode="extended",
            )

        self.assertEqual(response.document.theme.tokens.get("accent"), "#dc2626")
        self.assertTrue(response.validation_result.valid)


if __name__ == "__main__":
    unittest.main()
