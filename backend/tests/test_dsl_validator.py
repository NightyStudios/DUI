from __future__ import annotations

import unittest

from backend.app.dsl_models import DuiDslNode
from backend.app.dsl_seed import build_seed_document_for_surface
from backend.app.dsl_validator import DuiDslValidator
from backend.app.models import DEFAULT_SURFACE_ID


class DuiDslValidatorTests(unittest.TestCase):
    def test_seed_document_is_valid(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        result = DuiDslValidator.validate(document)
        self.assertTrue(result.valid, msg=f"Unexpected errors: {[issue.message for issue in result.errors]}")

    def test_unknown_node_type_is_rejected(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        document.nodes.append(DuiDslNode(id="bad_node", type="evil.custom_component"))
        result = DuiDslValidator.validate(document)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "node.type_unknown" for issue in result.errors))

    def test_duplicate_node_id_is_rejected(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        first = document.nodes[0]
        document.nodes.append(DuiDslNode(id=first.id, type="layout.container"))
        result = DuiDslValidator.validate(document)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "node.id_duplicate" for issue in result.errors))

    def test_unknown_child_reference_is_rejected(self) -> None:
        document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        document.nodes[0].children.append("ghost_node")
        result = DuiDslValidator.validate(document)
        self.assertFalse(result.valid)
        self.assertTrue(any(issue.code == "node.child_unknown" for issue in result.errors))


if __name__ == "__main__":
    unittest.main()

