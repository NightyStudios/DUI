from __future__ import annotations

from typing import Any


def normalize_prompt(prompt: str) -> str:
    return prompt.lower().replace("ё", "е").strip()


def infer_theme_token_overrides(prompt: str) -> dict[str, str]:
    normalized = normalize_prompt(prompt)
    tokens: dict[str, str] = {}

    if _has_any(normalized, "high contrast", "high-contrast", "контрастн"):
        tokens.update(
            {
                "bg": "#0b1020",
                "surface": "#111827",
                "surface_container": "#1f2937",
                "text": "#f9fafb",
                "muted": "#d1d5db",
                "outline": "#f8fafc",
                "accent": "#facc15",
                "accent_container": "#fde68a",
            }
        )

    if _has_any(normalized, "colorblind", "color blind", "дальто", "красно-зелен"):
        tokens.update(
            {
                "accent": "#2563eb",
                "accent_container": "#dbeafe",
                "outline": "#1d4ed8",
            }
        )

    if _has_any(normalized, "dyslex", "дислекс"):
        tokens.update(
            {
                "font": "'Verdana', sans-serif",
                "gap": "20px",
                "padding": "20px",
                "row_height": "52px",
                "outline": "#111827",
            }
        )

    if _has_any(normalized, "burnout", "anti-burnout", "спокойн", "paper mode", "paper режим", "матов"):
        tokens.update(
            {
                "bg": "#f7f4ef",
                "surface": "#fffdf8",
                "surface_container": "#f1ece4",
                "text": "#2f2a24",
                "muted": "#6b625a",
                "outline": "#b9aa98",
                "accent": "#8b5e34",
                "accent_container": "#eadbc8",
            }
        )

    if _has_any(normalized, "neon", "адреналин", "sprint", "спринт"):
        tokens.update(
            {
                "bg": "#09090b",
                "surface": "#111827",
                "surface_container": "#0f172a",
                "text": "#f8fafc",
                "muted": "#cbd5e1",
                "outline": "#22d3ee",
                "accent": "#22d3ee",
                "accent_container": "#164e63",
            }
        )

    return tokens


def infer_layout_constraint_overrides(prompt: str) -> dict[str, Any]:
    normalized = normalize_prompt(prompt)
    layout: dict[str, Any] = {}

    if _has_any(normalized, "projector", "проектор", "демонстрац"):
        layout.update(
            {
                "max_columns": 1,
                "content_density": "comfortable",
                "emphasis_zone": "header",
            }
        )

    if _has_any(normalized, "one hand", "одной рукой", "телефон", "mobile"):
        layout.update(
            {
                "content_density": "compact",
                "sidebar_width": "narrow",
                "emphasis_zone": "header",
            }
        )

    if wants_focus_only(prompt):
        layout.update(
            {
                "max_columns": 1,
                "emphasis_zone": "content",
            }
        )

    if _has_any(normalized, "lab mode", "lab-mode", "experimental", "эксперимент"):
        layout.update({"emphasis_zone": "content"})

    return layout


def wants_sidebar_to_top(prompt: str) -> bool:
    normalized = normalize_prompt(prompt)
    return ("сайдбар" in normalized or "sidebar" in normalized) and (
        "сверху" in normalized or "top" in normalized
    )


def wants_focus_only(prompt: str) -> bool:
    normalized = normalize_prompt(prompt)
    return _has_any(
        normalized,
        "deep focus",
        "глубокого фокуса",
        "только практик",
        "only practice",
        "5 минут",
        "first actionable",
        "первый actionable",
        "anti procrastination",
        "anti-procrastination",
    )


def wants_low_bandwidth(prompt: str) -> bool:
    normalized = normalize_prompt(prompt)
    return _has_any(normalized, "low bandwidth", "плохого интернета", "slow internet")


def _has_any(normalized: str, *tokens: str) -> bool:
    return any(token in normalized for token in tokens)

