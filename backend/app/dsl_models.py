from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .dsl_catalog import DSL_VERSION
from .models import Density, PatchOperation, ThemeProfile, UiManifest, Zone


DuiIssueSeverity = Literal["error", "warning"]


class DuiDslSurface(BaseModel):
    id: str
    title: str
    route: str


class DuiDslMeta(BaseModel):
    document_id: str = Field(default_factory=lambda: f"doc_{uuid4().hex}")
    revision: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"


class DuiDslTheme(BaseModel):
    profile: ThemeProfile = "default"
    density: Density = "comfortable"
    tokens: dict[str, str] = Field(default_factory=dict)


class DuiDslState(BaseModel):
    locals: dict[str, Any] = Field(default_factory=dict)


class DuiDslNode(BaseModel):
    id: str
    type: str
    props: dict[str, Any] = Field(default_factory=dict)
    style: dict[str, Any] = Field(default_factory=dict)
    layout: dict[str, Any] = Field(default_factory=dict)
    a11y: dict[str, Any] = Field(default_factory=dict)
    visible_when: dict[str, Any] | None = None
    enabled_when: dict[str, Any] | None = None
    children: list[str] = Field(default_factory=list)
    slots: dict[str, list[str]] = Field(default_factory=dict)
    on: dict[str, str] = Field(default_factory=dict)


class DuiDslBinding(BaseModel):
    id: str
    source: str
    select: str = "$"
    args: dict[str, Any] = Field(default_factory=dict)
    cache: dict[str, Any] = Field(default_factory=dict)


class DuiDslAction(BaseModel):
    id: str
    type: str
    params: dict[str, Any] = Field(default_factory=dict)


class DuiDslWidgetLink(BaseModel):
    page: str | None = None
    widget: str | None = None
    route: str | None = None
    rel: str = "navigate"
    payload: dict[str, Any] = Field(default_factory=dict)


class DuiDslWidget(BaseModel):
    id: str
    kind: str = "card"
    title: str | None = None
    zone: Zone | None = None
    group_id: str | None = None
    capability_id: str | None = None
    binding_id: str | None = None
    template_id: str | None = None
    visible: bool = True
    props: dict[str, Any] = Field(default_factory=dict)
    style: dict[str, Any] = Field(default_factory=dict)
    layout: dict[str, Any] = Field(default_factory=dict)
    behavior: dict[str, Any] = Field(default_factory=dict)
    a11y: dict[str, Any] = Field(default_factory=dict)
    links: list[DuiDslWidgetLink] = Field(default_factory=list)


class DuiDslWidgetGroup(BaseModel):
    id: str
    title: str
    page_id: str | None = None
    zone: Zone = "content"
    widget_ids: list[str] = Field(default_factory=list)
    visible: bool = True
    layout: dict[str, Any] = Field(default_factory=dict)
    style: dict[str, Any] = Field(default_factory=dict)
    behavior: dict[str, Any] = Field(default_factory=dict)


class DuiDslPage(BaseModel):
    id: str
    title: str
    route: str
    group_ids: list[str] = Field(default_factory=list)
    is_default: bool = False
    layout: dict[str, Any] = Field(default_factory=dict)
    style: dict[str, Any] = Field(default_factory=dict)
    behavior: dict[str, Any] = Field(default_factory=dict)


class DuiDslDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dsl_version: str = DSL_VERSION
    surface: DuiDslSurface
    meta: DuiDslMeta = Field(default_factory=DuiDslMeta)
    theme: DuiDslTheme = Field(default_factory=DuiDslTheme)
    state: DuiDslState = Field(default_factory=DuiDslState)
    pages: list[DuiDslPage] = Field(default_factory=list)
    groups: list[DuiDslWidgetGroup] = Field(default_factory=list)
    widgets: list[DuiDslWidget] = Field(default_factory=list)
    legacy_nodes: list[DuiDslNode] = Field(default_factory=list, validation_alias="nodes", exclude=True)
    bindings: list[DuiDslBinding] = Field(default_factory=list)
    actions: list[DuiDslAction] = Field(default_factory=list)
    layout_constraints: dict[str, Any] = Field(default_factory=dict)


class DuiDslValidationIssue(BaseModel):
    severity: DuiIssueSeverity
    code: str
    message: str
    path: str


class DuiDslValidationResult(BaseModel):
    valid: bool
    errors: list[DuiDslValidationIssue] = Field(default_factory=list)
    warnings: list[DuiDslValidationIssue] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)


class DuiDslValidateRequest(BaseModel):
    document: DuiDslDocument
    surface_id: str | None = None


class DuiDslValidateResponse(BaseModel):
    result: DuiDslValidationResult
    compiled_manifest: UiManifest | None = None


class DuiDslCommitRequest(BaseModel):
    document: DuiDslDocument
    surface_id: str | None = None
    approved_by: str | None = None
    expected_manifest_revision: int | None = None
    expected_dsl_revision: int | None = None


class DuiDslCommitResponse(BaseModel):
    document: DuiDslDocument
    manifest: UiManifest


class DuiDslParseRequest(BaseModel):
    source_text: str = Field(min_length=1, max_length=100_000)
    surface_id: str | None = None


class DuiDslParseResponse(BaseModel):
    document: DuiDslDocument
    validation_result: DuiDslValidationResult
    compiled_manifest: UiManifest | None = None


class DuiDslIntentRequest(BaseModel):
    user_prompt: str = Field(min_length=1, max_length=2000)
    surface_id: str | None = None
    scope: str | None = None
    session_id: str | None = None
    turn_id: str | None = None


class DuiDslIntentResponse(BaseModel):
    document: DuiDslDocument
    validation_result: DuiDslValidationResult
    preview_manifest: UiManifest | None = None
    operations: list[PatchOperation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DuiDslTransformRequest(BaseModel):
    source_text: str = Field(min_length=1, max_length=100_000)
    user_prompt: str = Field(min_length=1, max_length=2000)
    surface_id: str | None = None
    scope: str | None = None
    session_id: str | None = None
    turn_id: str | None = None


class DuiDslTransformResponse(BaseModel):
    source_text: str
    document: DuiDslDocument
    validation_result: DuiDslValidationResult
    preview_manifest: UiManifest | None = None
    operations: list[PatchOperation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
