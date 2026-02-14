from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


TemplateKind = Literal["kpi", "table", "activity", "chart", "card", "list", "panel", "tabs", "form"]


@dataclass(frozen=True)
class TemplateSpec:
    template_id: str
    title: str
    kind: TemplateKind
    capability_id: str
    default_props: dict[str, str] = field(default_factory=dict)


TEMPLATE_CATALOG: dict[str, TemplateSpec] = {
    "weak_topics_list": TemplateSpec(
        template_id="weak_topics_list",
        title="Weak Topics",
        kind="list",
        capability_id="math.weak_topics",
    ),
    "next_lesson_card": TemplateSpec(
        template_id="next_lesson_card",
        title="Next Lesson",
        kind="card",
        capability_id="math.next_lesson",
    ),
    "study_streak_panel": TemplateSpec(
        template_id="study_streak_panel",
        title="Study Streak",
        kind="panel",
        capability_id="math.study_streak",
    ),
    "formula_cheatsheet": TemplateSpec(
        template_id="formula_cheatsheet",
        title="Formula Cheatsheet",
        kind="list",
        capability_id="math.formulas",
    ),
    "quick_actions": TemplateSpec(
        template_id="quick_actions",
        title="Quick Actions",
        kind="panel",
        capability_id="math.quick_actions",
    ),
    "assignment_calendar": TemplateSpec(
        template_id="assignment_calendar",
        title="Assignment Calendar",
        kind="table",
        capability_id="math.assignments",
    ),
    "focus_timer": TemplateSpec(
        template_id="focus_timer",
        title="Focus Timer",
        kind="card",
        capability_id="math.focus_timer",
    ),
}


def get_template(template_id: str) -> TemplateSpec | None:
    return TEMPLATE_CATALOG.get(template_id)


def template_ids() -> list[str]:
    return sorted(TEMPLATE_CATALOG.keys())
