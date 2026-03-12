from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .config import BASE_DIR, load_project_env
from .services import DslService, EnvelopeService, UiService
from .storage import ManifestStore


@dataclass(frozen=True)
class AppRuntime:
    store: ManifestStore
    ui_service: UiService
    dsl_service: DslService
    envelope_service: EnvelopeService


def create_runtime(store: ManifestStore | None = None) -> AppRuntime:
    load_project_env()
    runtime_store = store or ManifestStore(BASE_DIR / "data" / "state.json")
    ui_service = UiService(runtime_store)
    dsl_service = DslService(runtime_store)
    envelope_service = EnvelopeService(runtime_store, ui_service, dsl_service)
    return AppRuntime(
        store=runtime_store,
        ui_service=ui_service,
        dsl_service=dsl_service,
        envelope_service=envelope_service,
    )


@lru_cache(maxsize=1)
def get_default_runtime() -> AppRuntime:
    return create_runtime()


class StoreProxy:
    def __getattr__(self, name: str):
        return getattr(get_default_runtime().store, name)
