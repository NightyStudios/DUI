from __future__ import annotations

from .models import DEFAULT_SURFACE_ID, DuiMode
from .storage import ManifestStore


def resolve_mode(scope: str | None) -> DuiMode:
    if scope in {"safe", "extended", "experimental"}:
        return scope
    return "extended"


def resolve_surface_id(surface_id: str | None) -> str:
    if surface_id and surface_id.strip():
        return surface_id.strip()
    return DEFAULT_SURFACE_ID


def resolve_session_id(store: ManifestStore, *, surface_id: str, session_id: str | None) -> str:
    if session_id and session_id.strip():
        return session_id.strip()
    return store.get_surface_context(surface_id)["session_id"]
