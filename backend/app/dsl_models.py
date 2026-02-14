from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from .dsl_catalog import DSL_VERSION
from .models import Density, ThemeProfile, UiManifest


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


class DuiDslDocument(BaseModel):
    dsl_version: str = DSL_VERSION
    surface: DuiDslSurface
    meta: DuiDslMeta = Field(default_factory=DuiDslMeta)
    theme: DuiDslTheme = Field(default_factory=DuiDslTheme)
    state: DuiDslState = Field(default_factory=DuiDslState)
    nodes: list[DuiDslNode] = Field(default_factory=list)
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
    warnings: list[str] = Field(default_factory=list)
