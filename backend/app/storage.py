from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .dsl_models import DuiDslDocument
from .dsl_seed import LESSON_SURFACE_ID, build_seed_document_for_surface
from .manifest_service import tokens_for
from .models import (
    DEFAULT_CATALOG_VERSION,
    DEFAULT_SESSION_ID,
    DEFAULT_SURFACE_ID,
    SectionConfig,
    ThemeConfig,
    UiManifest,
    UiPatchPlan,
    WidgetConfig,
)


SURFACE_STORE_VERSION = 1


class ManifestStore:
    @staticmethod
    def _normalize_surface_id(surface_id: str | None) -> str:
        if surface_id and surface_id.strip():
            return surface_id.strip()
        return DEFAULT_SURFACE_ID

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self._init_state()
            return

        normalized = self._normalize_state(self._read_state())
        self._write_state(normalized)

    def _build_dashboard_seed_manifest(self, manifest_id: str = "seed-manifest-v1") -> UiManifest:
        return UiManifest(
            manifest_id=manifest_id,
            revision=1,
            theme=ThemeConfig(
                profile="default",
                density="comfortable",
                tokens=tokens_for("default", "comfortable"),
            ),
            widgets=[
                WidgetConfig(
                    id="course_progress",
                    title="Course Progress",
                    kind="kpi",
                    zone="header",
                    capability_id="math.progress_overview",
                    protected=True,
                ),
                WidgetConfig(
                    id="learning_path",
                    title="Learning Path",
                    kind="table",
                    zone="content",
                    capability_id="math.learning_path",
                ),
                WidgetConfig(
                    id="practice_queue",
                    title="Practice Queue",
                    kind="activity",
                    zone="sidebar",
                    capability_id="math.practice_queue",
                ),
                WidgetConfig(
                    id="mastery_trend",
                    title="Mastery Trend",
                    kind="chart",
                    zone="content",
                    capability_id="math.mastery_trend",
                ),
            ],
            sections=[
                SectionConfig(
                    id="learning_overview",
                    title="Learning Overview",
                    zone="content",
                    child_widget_ids=["learning_path", "mastery_trend"],
                    layout={"columns": 2},
                )
            ],
            layout_constraints={"max_columns": 2, "sidebar_width": "normal", "content_density": "comfortable"},
            metadata={"seed": "true", "domain": "math-lms", "surface_id": DEFAULT_SURFACE_ID},
        )

    def _build_lesson_seed_manifest(self, manifest_id: str = "seed-lesson-manifest-v1") -> UiManifest:
        return UiManifest(
            manifest_id=manifest_id,
            revision=1,
            theme=ThemeConfig(
                profile="default",
                density="comfortable",
                tokens=tokens_for("default", "comfortable"),
            ),
            widgets=[
                WidgetConfig(
                    id="lesson_progress",
                    title="Lesson Progress",
                    kind="kpi",
                    zone="header",
                    capability_id="math.lesson_progress",
                    protected=True,
                ),
                WidgetConfig(
                    id="lesson_objectives",
                    title="Objectives",
                    kind="list",
                    zone="content",
                    capability_id="math.lesson_objectives",
                ),
                WidgetConfig(
                    id="lesson_theory",
                    title="Theory Points",
                    kind="card",
                    zone="content",
                    capability_id="math.lesson_theory",
                ),
                WidgetConfig(
                    id="lesson_exercises",
                    title="Exercises",
                    kind="activity",
                    zone="sidebar",
                    capability_id="math.lesson_exercises",
                ),
            ],
            sections=[
                SectionConfig(
                    id="lesson_content",
                    title="Lesson Content",
                    zone="content",
                    child_widget_ids=["lesson_objectives", "lesson_theory"],
                    layout={"columns": 1},
                )
            ],
            layout_constraints={"max_columns": 1, "sidebar_width": "normal", "content_density": "comfortable"},
            metadata={"seed": "true", "domain": "math-lms", "surface_id": LESSON_SURFACE_ID},
        )

    def _build_seed_manifest_for_surface(self, surface_id: str) -> UiManifest:
        if surface_id == LESSON_SURFACE_ID:
            return self._build_lesson_seed_manifest()
        manifest = self._build_dashboard_seed_manifest()
        manifest.metadata["surface_id"] = surface_id
        return manifest

    def _new_surface_state(
        self,
        surface_id: str,
        manifest: UiManifest,
        dsl_document: DuiDslDocument | None = None,
        *,
        session_id: str = DEFAULT_SESSION_ID,
        catalog_version: str = DEFAULT_CATALOG_VERSION,
    ) -> dict[str, Any]:
        if dsl_document is None:
            dsl_document = build_seed_document_for_surface(surface_id)
        return {
            "surface_id": surface_id,
            "session_id": session_id,
            "catalog_version": catalog_version,
            "metadata": {
                "domain": manifest.metadata.get("domain", "math-lms"),
                "seed": manifest.metadata.get("seed", "true"),
            },
            "revisions": [manifest.model_dump(mode="json")],
            "dsl_revisions": [dsl_document.model_dump(mode="json")],
            "patch_plans": {},
        }

    def _normalize_surface_state(self, surface_id: str, raw_surface: Any) -> dict[str, Any]:
        if not isinstance(raw_surface, dict):
            seed_manifest = self._build_seed_manifest_for_surface(surface_id)
            return self._new_surface_state(surface_id, seed_manifest)

        revisions = raw_surface.get("revisions")
        if not isinstance(revisions, list) or not revisions:
            seed_manifest = self._build_seed_manifest_for_surface(surface_id)
            revisions = [seed_manifest.model_dump(mode="json")]

        patch_plans = raw_surface.get("patch_plans")
        if not isinstance(patch_plans, dict):
            patch_plans = {}

        dsl_revisions = raw_surface.get("dsl_revisions")
        if not isinstance(dsl_revisions, list) or not dsl_revisions:
            dsl_revisions = [build_seed_document_for_surface(surface_id).model_dump(mode="json")]

        metadata = raw_surface.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        return {
            "surface_id": surface_id,
            "session_id": str(raw_surface.get("session_id") or DEFAULT_SESSION_ID),
            "catalog_version": str(raw_surface.get("catalog_version") or DEFAULT_CATALOG_VERSION),
            "metadata": metadata,
            "revisions": revisions,
            "dsl_revisions": dsl_revisions,
            "patch_plans": patch_plans,
        }

    def _normalize_state(self, raw_state: Any) -> dict[str, Any]:
        if isinstance(raw_state, dict) and isinstance(raw_state.get("surfaces"), dict):
            surfaces: dict[str, Any] = {}
            for surface_id, raw_surface in raw_state["surfaces"].items():
                surfaces[str(surface_id)] = self._normalize_surface_state(str(surface_id), raw_surface)

            if DEFAULT_SURFACE_ID not in surfaces:
                surfaces[DEFAULT_SURFACE_ID] = self._new_surface_state(
                    DEFAULT_SURFACE_ID,
                    self._build_seed_manifest_for_surface(DEFAULT_SURFACE_ID),
                )
            if LESSON_SURFACE_ID not in surfaces:
                surfaces[LESSON_SURFACE_ID] = self._new_surface_state(
                    LESSON_SURFACE_ID,
                    self._build_seed_manifest_for_surface(LESSON_SURFACE_ID),
                )

            return {"surface_store_version": SURFACE_STORE_VERSION, "surfaces": surfaces}

        # Legacy format migration.
        legacy_revisions = []
        legacy_patch_plans: dict[str, Any] = {}
        if isinstance(raw_state, dict):
            raw_revisions = raw_state.get("revisions")
            raw_patch_plans = raw_state.get("patch_plans")
            if isinstance(raw_revisions, list):
                legacy_revisions = raw_revisions
            if isinstance(raw_patch_plans, dict):
                legacy_patch_plans = raw_patch_plans

        if not legacy_revisions:
            legacy_revisions = [self._build_seed_manifest_for_surface(DEFAULT_SURFACE_ID).model_dump(mode="json")]

        migrated_surfaces = {
            DEFAULT_SURFACE_ID: {
                "surface_id": DEFAULT_SURFACE_ID,
                "session_id": DEFAULT_SESSION_ID,
                "catalog_version": DEFAULT_CATALOG_VERSION,
                "metadata": {"domain": "math-lms", "seed": "migrated"},
                "revisions": legacy_revisions,
                "dsl_revisions": [build_seed_document_for_surface(DEFAULT_SURFACE_ID).model_dump(mode="json")],
                "patch_plans": legacy_patch_plans,
            },
            LESSON_SURFACE_ID: self._new_surface_state(
                LESSON_SURFACE_ID,
                self._build_seed_manifest_for_surface(LESSON_SURFACE_ID),
                build_seed_document_for_surface(LESSON_SURFACE_ID),
            ),
        }
        return {"surface_store_version": SURFACE_STORE_VERSION, "surfaces": migrated_surfaces}

    def _init_state(self) -> None:
        dashboard_manifest = self._build_seed_manifest_for_surface(DEFAULT_SURFACE_ID)
        lesson_manifest = self._build_seed_manifest_for_surface(LESSON_SURFACE_ID)
        dashboard_document = build_seed_document_for_surface(DEFAULT_SURFACE_ID)
        lesson_document = build_seed_document_for_surface(LESSON_SURFACE_ID)
        self._write_state(
            {
                "surface_store_version": SURFACE_STORE_VERSION,
                "surfaces": {
                    DEFAULT_SURFACE_ID: self._new_surface_state(
                        DEFAULT_SURFACE_ID,
                        dashboard_manifest,
                        dashboard_document,
                    ),
                    LESSON_SURFACE_ID: self._new_surface_state(
                        LESSON_SURFACE_ID,
                        lesson_manifest,
                        lesson_document,
                    ),
                },
            }
        )

    def reset_to_seed(self) -> None:
        self._init_state()

    def _read_state(self) -> dict[str, Any]:
        if not self.state_file.exists():
            self._init_state()

        raw = self.state_file.read_text(encoding="utf-8")
        if not raw.strip():
            self._init_state()
            raw = self.state_file.read_text(encoding="utf-8")

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Self-heal corrupted state files (for example interrupted writes).
            self._init_state()
            raw = self.state_file.read_text(encoding="utf-8")
            return json.loads(raw)

    def _write_state(self, state: dict[str, Any]) -> None:
        payload = json.dumps(state, indent=2, ensure_ascii=False)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.state_file.parent,
                delete=False,
                prefix=f"{self.state_file.name}.",
                suffix=".tmp",
            ) as tmp_file:
                tmp_file.write(payload)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
                tmp_path = Path(tmp_file.name)

            os.replace(tmp_path, self.state_file)
        finally:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def _ensure_surface(self, state: dict[str, Any], surface_id: str) -> dict[str, Any]:
        surface_id = self._normalize_surface_id(surface_id)
        surfaces = state.setdefault("surfaces", {})
        if surface_id not in surfaces:
            seed_manifest = self._build_seed_manifest_for_surface(surface_id)
            seed_document = build_seed_document_for_surface(surface_id)
            surfaces[surface_id] = self._new_surface_state(surface_id, seed_manifest, seed_document)
        return surfaces[surface_id]

    def _get_surface(self, state: dict[str, Any], surface_id: str) -> dict[str, Any]:
        surface_id = self._normalize_surface_id(surface_id)
        surface = self._ensure_surface(state, surface_id)
        return self._normalize_surface_state(surface_id, surface)

    def list_surfaces(self) -> list[dict[str, str]]:
        state = self._read_state()
        normalized = self._normalize_state(state)
        self._write_state(normalized)
        output: list[dict[str, str]] = []
        for surface_id, surface in normalized["surfaces"].items():
            output.append(
                {
                    "surface_id": surface_id,
                    "session_id": str(surface.get("session_id") or DEFAULT_SESSION_ID),
                    "catalog_version": str(surface.get("catalog_version") or DEFAULT_CATALOG_VERSION),
                    "manifest_revision_count": str(len(surface.get("revisions", []))),
                    "dsl_revision_count": str(len(surface.get("dsl_revisions", []))),
                }
            )
        return output

    def get_current_manifest(self, surface_id: str = DEFAULT_SURFACE_ID) -> UiManifest:
        surface_id = self._normalize_surface_id(surface_id)
        state = self._read_state()
        normalized = self._normalize_state(state)
        surface = self._get_surface(normalized, surface_id)
        self._ensure_surface(normalized, surface_id)
        normalized["surfaces"][surface_id] = surface
        self._write_state(normalized)
        raw = surface["revisions"][-1]
        return UiManifest.model_validate(raw)

    def list_revisions(self, surface_id: str = DEFAULT_SURFACE_ID) -> list[UiManifest]:
        surface_id = self._normalize_surface_id(surface_id)
        state = self._read_state()
        normalized = self._normalize_state(state)
        surface = self._get_surface(normalized, surface_id)
        self._ensure_surface(normalized, surface_id)
        normalized["surfaces"][surface_id] = surface
        self._write_state(normalized)
        return [UiManifest.model_validate(raw) for raw in surface["revisions"]]

    def get_current_dsl_document(self, surface_id: str = DEFAULT_SURFACE_ID) -> DuiDslDocument:
        surface_id = self._normalize_surface_id(surface_id)
        state = self._read_state()
        normalized = self._normalize_state(state)
        surface = self._get_surface(normalized, surface_id)
        self._ensure_surface(normalized, surface_id)
        normalized["surfaces"][surface_id] = surface
        self._write_state(normalized)
        raw = surface["dsl_revisions"][-1]
        return DuiDslDocument.model_validate(raw)

    def list_dsl_revisions(self, surface_id: str = DEFAULT_SURFACE_ID) -> list[DuiDslDocument]:
        surface_id = self._normalize_surface_id(surface_id)
        state = self._read_state()
        normalized = self._normalize_state(state)
        surface = self._get_surface(normalized, surface_id)
        self._ensure_surface(normalized, surface_id)
        normalized["surfaces"][surface_id] = surface
        self._write_state(normalized)
        return [DuiDslDocument.model_validate(raw) for raw in surface["dsl_revisions"]]

    def get_surface_context(self, surface_id: str = DEFAULT_SURFACE_ID) -> dict[str, str]:
        surface_id = self._normalize_surface_id(surface_id)
        state = self._read_state()
        normalized = self._normalize_state(state)
        surface = self._get_surface(normalized, surface_id)
        self._ensure_surface(normalized, surface_id)
        normalized["surfaces"][surface_id] = surface
        self._write_state(normalized)
        return {
            "surface_id": surface_id,
            "session_id": str(surface.get("session_id") or DEFAULT_SESSION_ID),
            "catalog_version": str(surface.get("catalog_version") or DEFAULT_CATALOG_VERSION),
        }

    def save_patch_plan(self, patch_plan: UiPatchPlan, surface_id: str | None = None) -> None:
        resolved_surface_id = self._normalize_surface_id(surface_id or patch_plan.surface_id)
        patch_plan.surface_id = resolved_surface_id
        state = self._read_state()
        normalized = self._normalize_state(state)
        surface = self._ensure_surface(normalized, resolved_surface_id)
        surface["patch_plans"][patch_plan.patch_plan_id] = patch_plan.model_dump(mode="json")
        self._write_state(normalized)

    def get_patch_plan(self, patch_plan_id: str, surface_id: str | None = None) -> UiPatchPlan | None:
        state = self._read_state()
        normalized = self._normalize_state(state)

        if surface_id:
            surface = self._ensure_surface(normalized, self._normalize_surface_id(surface_id))
            raw = surface["patch_plans"].get(patch_plan_id)
            self._write_state(normalized)
            if raw:
                return UiPatchPlan.model_validate(raw)
            return None

        for resolved_surface_id in normalized["surfaces"].keys():
            surface = self._ensure_surface(normalized, resolved_surface_id)
            raw = surface["patch_plans"].get(patch_plan_id)
            if raw:
                self._write_state(normalized)
                return UiPatchPlan.model_validate(raw)
        self._write_state(normalized)
        return None

    def update_patch_plan(self, patch_plan: UiPatchPlan, surface_id: str | None = None) -> None:
        resolved_surface_id = self._normalize_surface_id(surface_id or patch_plan.surface_id)
        patch_plan.surface_id = resolved_surface_id
        state = self._read_state()
        normalized = self._normalize_state(state)
        surface = self._ensure_surface(normalized, resolved_surface_id)
        surface["patch_plans"][patch_plan.patch_plan_id] = patch_plan.model_dump(mode="json")
        self._write_state(normalized)

    def append_manifest_revision(self, manifest: UiManifest, surface_id: str = DEFAULT_SURFACE_ID) -> None:
        surface_id = self._normalize_surface_id(surface_id)
        state = self._read_state()
        normalized = self._normalize_state(state)
        surface = self._ensure_surface(normalized, surface_id)
        surface["revisions"].append(manifest.model_dump(mode="json"))
        self._write_state(normalized)

    def append_dsl_revision(self, document: DuiDslDocument, surface_id: str = DEFAULT_SURFACE_ID) -> None:
        surface_id = self._normalize_surface_id(surface_id)
        state = self._read_state()
        normalized = self._normalize_state(state)
        surface = self._ensure_surface(normalized, surface_id)
        surface["dsl_revisions"].append(document.model_dump(mode="json"))
        self._write_state(normalized)

    def append_manifest_and_dsl_revision(
        self,
        *,
        manifest: UiManifest,
        document: DuiDslDocument,
        surface_id: str = DEFAULT_SURFACE_ID,
        expected_manifest_revision: int | None = None,
        expected_dsl_revision: int | None = None,
    ) -> tuple[bool, int, int]:
        surface_id = self._normalize_surface_id(surface_id)
        state = self._read_state()
        normalized = self._normalize_state(state)
        surface = self._ensure_surface(normalized, surface_id)

        current_manifest_revision = int(surface["revisions"][-1]["revision"])
        current_dsl_revision = int(surface["dsl_revisions"][-1]["meta"]["revision"])
        if expected_manifest_revision is not None and current_manifest_revision != expected_manifest_revision:
            return False, current_manifest_revision, current_dsl_revision
        if expected_dsl_revision is not None and current_dsl_revision != expected_dsl_revision:
            return False, current_manifest_revision, current_dsl_revision

        surface["revisions"].append(manifest.model_dump(mode="json"))
        surface["dsl_revisions"].append(document.model_dump(mode="json"))
        self._write_state(normalized)
        return True, current_manifest_revision, current_dsl_revision

    def get_revision(self, revision: int, surface_id: str = DEFAULT_SURFACE_ID) -> UiManifest | None:
        surface_id = self._normalize_surface_id(surface_id)
        state = self._read_state()
        normalized = self._normalize_state(state)
        surface = self._ensure_surface(normalized, surface_id)
        self._write_state(normalized)
        for raw in surface["revisions"]:
            if raw.get("revision") == revision:
                return UiManifest.model_validate(raw)
        return None
