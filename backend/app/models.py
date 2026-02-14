from __future__ import annotations

from uuid import uuid4
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


Zone = Literal["header", "sidebar", "content", "footer"]
WidgetKind = Literal["kpi", "table", "activity", "chart", "card", "list", "panel", "tabs", "form"]
ThemeProfile = Literal["default", "minimal", "liquid_glass"]
Density = Literal["comfortable", "compact"]
PatchStatus = Literal["draft", "committed", "rejected"]
DuiMode = Literal["safe", "extended", "experimental"]
EnvelopeVersion = Literal["a2ui.v0"]
A2UiMessageType = Literal[
    "intent.request",
    "intent.response",
    "commit.request",
    "commit.response",
    "revert.request",
    "revert.response",
    "manifest.current.request",
    "manifest.current.response",
    "manifest.revisions.request",
    "manifest.revisions.response",
    "dsl.current.request",
    "dsl.current.response",
    "dsl.intent.request",
    "dsl.intent.response",
    "dsl.parse.request",
    "dsl.parse.response",
    "dsl.revisions.request",
    "dsl.revisions.response",
    "dsl.validate.request",
    "dsl.validate.response",
    "dsl.commit.request",
    "dsl.commit.response",
    "error",
]

DEFAULT_SESSION_ID = "demo-session"
DEFAULT_SURFACE_ID = "math_lms.dashboard"
DEFAULT_CATALOG_VERSION = "math-lms-catalog-v1"


class ThemeConfig(BaseModel):
    profile: ThemeProfile = "default"
    density: Density = "comfortable"
    tokens: dict[str, str] = Field(default_factory=dict)


class WidgetConfig(BaseModel):
    id: str
    title: str
    kind: WidgetKind
    zone: Zone
    capability_id: str
    protected: bool = False
    template_id: str | None = None
    props: dict[str, Any] = Field(default_factory=dict)


class SectionConfig(BaseModel):
    id: str
    title: str
    zone: Zone
    child_widget_ids: list[str] = Field(default_factory=list)
    layout: dict[str, Any] = Field(default_factory=dict)


class UiManifest(BaseModel):
    schema_version: Literal[1] = 1
    manifest_id: str
    revision: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    theme: ThemeConfig
    widgets: list[WidgetConfig]
    sections: list[SectionConfig] = Field(default_factory=list)
    layout_constraints: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, str] = Field(default_factory=dict)


class PatchOperation(BaseModel):
    op: Literal[
        "set_theme_profile",
        "set_density",
        "set_theme_tokens",
        "set_layout_constraints",
        "move_widget",
        "remove_widget",
        "add_widget",
        "add_widget_from_template",
        "compose_section",
    ]
    profile: ThemeProfile | None = None
    density: Density | None = None
    tokens: dict[str, str] | None = None
    layout_constraints: dict[str, Any] | None = None

    widget_id: str | None = None
    zone: Zone | None = None
    widget: WidgetConfig | None = None

    template_id: str | None = None
    title: str | None = None
    capability_id: str | None = None
    props: dict[str, Any] | None = None

    section_id: str | None = None
    section_title: str | None = None
    child_widget_ids: list[str] | None = None
    section_layout: dict[str, Any] | None = None


class UiPatchPlan(BaseModel):
    patch_plan_id: str
    user_prompt: str
    session_id: str = DEFAULT_SESSION_ID
    surface_id: str = DEFAULT_SURFACE_ID
    turn_id: str | None = None
    mode: DuiMode = "extended"
    operations: list[PatchOperation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: PatchStatus = "draft"


class IntentRequest(BaseModel):
    user_prompt: str = Field(min_length=1, max_length=2000)
    current_manifest_id: str | None = None
    scope: str | None = None
    session_id: str | None = None
    surface_id: str | None = None
    turn_id: str | None = None


class IntentResponse(BaseModel):
    patch_plan: UiPatchPlan
    preview_manifest: UiManifest
    warnings: list[str] = Field(default_factory=list)


class CommitRequest(BaseModel):
    patch_plan_id: str
    approved_by: str | None = None
    session_id: str | None = None
    surface_id: str | None = None
    turn_id: str | None = None


class CommitResponse(BaseModel):
    manifest: UiManifest


class RevertRequest(BaseModel):
    target_revision: int
    approved_by: str | None = None
    session_id: str | None = None
    surface_id: str | None = None
    turn_id: str | None = None


class RevertResponse(BaseModel):
    manifest: UiManifest


class A2UiEnvelope(BaseModel):
    envelope_version: EnvelopeVersion = "a2ui.v0"
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str = DEFAULT_SESSION_ID
    surface_id: str = DEFAULT_SURFACE_ID
    turn_id: str = Field(default_factory=lambda: str(uuid4()))
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mode: DuiMode = "extended"
    catalog_version: str = DEFAULT_CATALOG_VERSION
    message_type: A2UiMessageType
    payload: dict[str, Any] = Field(default_factory=dict)
