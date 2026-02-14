from __future__ import annotations

import unittest

from backend.app.dsl_seed import build_seed_document_for_surface
from backend.app.main import STORE, a2ui_envelope, build_dsl_commit, build_dsl_intent, build_dsl_parse, build_dsl_validate
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


if __name__ == "__main__":
    unittest.main()
