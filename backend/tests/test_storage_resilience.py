from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.app.models import DEFAULT_SURFACE_ID
from backend.app.storage import ManifestStore


class ManifestStoreResilienceTests(unittest.TestCase):
    def test_init_recovers_from_empty_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            state_file.write_text("", encoding="utf-8")

            store = ManifestStore(state_file)
            manifest = store.get_current_manifest(DEFAULT_SURFACE_ID)

            self.assertEqual(manifest.revision, 1)
            parsed = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertIn("surfaces", parsed)

    def test_init_recovers_from_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state.json"
            state_file.write_text("{broken-json", encoding="utf-8")

            store = ManifestStore(state_file)
            dsl_document = store.get_current_dsl_document(DEFAULT_SURFACE_ID)

            self.assertEqual(dsl_document.surface.id, DEFAULT_SURFACE_ID)
            parsed = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertIn("surface_store_version", parsed)


if __name__ == "__main__":
    unittest.main()
