from __future__ import annotations

import os

from .models import UiManifest
from .storage import ManifestStore


def enforce_cross_surface_theme_consistency(
    store: ManifestStore,
    *,
    surface_id: str,
    candidate_manifest: UiManifest,
) -> list[str]:
    """Returns policy errors when global theme consistency is violated."""
    strict = os.getenv("DUI_ENFORCE_CROSS_SURFACE_THEME", "0") == "1"
    if not strict:
        return []

    errors: list[str] = []
    for entry in store.list_surfaces():
        other_surface_id = entry["surface_id"]
        if other_surface_id == surface_id:
            continue
        other_manifest = store.get_current_manifest(surface_id=other_surface_id)
        if other_manifest.theme.profile != candidate_manifest.theme.profile:
            errors.append(
                "cross-surface consistency violation: "
                f"theme profile '{candidate_manifest.theme.profile}' on {surface_id} differs "
                f"from '{other_manifest.theme.profile}' on {other_surface_id}"
            )
            continue
        if other_manifest.theme.density != candidate_manifest.theme.density:
            errors.append(
                "cross-surface consistency violation: "
                f"theme density '{candidate_manifest.theme.density}' on {surface_id} differs "
                f"from '{other_manifest.theme.density}' on {other_surface_id}"
            )
    return errors
