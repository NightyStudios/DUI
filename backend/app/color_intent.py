from __future__ import annotations

import re

BUTTON_HINTS: tuple[str, ...] = (
    "кнопк",
    "button",
    "buttons",
    "btn",
    "cta",
)

COLOR_INTENT_HINTS: tuple[str, ...] = (
    "цвет",
    "color",
    "yellow",
    "red",
    "green",
    "blue",
    "pink",
    "orange",
    "purple",
    "lime",
    "chartreuse",
    "кислотн",
    "неон",
    "красн",
    "желт",
    "жёлт",
    "зелен",
    "син",
    "голуб",
    "оранж",
    "фиолет",
    "розов",
)

HEX_COLOR_RE = re.compile(r"(?<![\w-])#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})(?![\w-])")
COLOR_FUNCTION_RE = re.compile(r"\b(?:rgb|rgba|hsl|hsla)\s*\(\s*[^()]{1,80}\)", re.IGNORECASE)
ENGLISH_WORD_RE = re.compile(r"\b[a-z][a-z0-9_-]{2,31}\b")

ENGLISH_COLOR_ALIASES: tuple[tuple[str, str], ...] = (
    ("acid yellow", "#ccff00"),
    ("acid-yellow", "#ccff00"),
    ("neon yellow", "#ccff00"),
    ("neon-yellow", "#ccff00"),
    ("electric yellow", "#ccff00"),
    ("electric-yellow", "#ccff00"),
)

RUSSIAN_COLOR_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bкислотн[а-я-]*\s*[- ]?\s*желт[а-я-]*\b"), "#ccff00"),
    (re.compile(r"\bкрасн[а-я-]*\b"), "#dc2626"),
    (re.compile(r"\bжелт[а-я-]*\b"), "#facc15"),
    (re.compile(r"\bзелен[а-я-]*\b"), "#16a34a"),
    (re.compile(r"\bсин[а-я-]*\b"), "#2563eb"),
    (re.compile(r"\bголуб[а-я-]*\b"), "#0ea5e9"),
    (re.compile(r"\bоранж[а-я-]*\b"), "#f97316"),
    (re.compile(r"\bфиолет[а-я-]*\b"), "#7c3aed"),
    (re.compile(r"\bрозов[а-я-]*\b"), "#ec4899"),
)

# Common CSS color keywords (including popular aliases and grayscale tones).
CSS_NAMED_COLORS: frozenset[str] = frozenset(
    {
        "aqua",
        "aquamarine",
        "azure",
        "beige",
        "black",
        "blue",
        "brown",
        "chartreuse",
        "coral",
        "crimson",
        "cyan",
        "fuchsia",
        "gold",
        "goldenrod",
        "gray",
        "green",
        "grey",
        "hotpink",
        "indigo",
        "ivory",
        "khaki",
        "lavender",
        "lime",
        "linen",
        "magenta",
        "maroon",
        "navy",
        "olive",
        "orange",
        "orchid",
        "pink",
        "plum",
        "purple",
        "red",
        "salmon",
        "seagreen",
        "silver",
        "skyblue",
        "slateblue",
        "tan",
        "teal",
        "tomato",
        "turquoise",
        "violet",
        "white",
        "yellow",
        "yellowgreen",
    }
)


def infer_button_theme_tokens(prompt: str) -> dict[str, str] | None:
    normalized = _normalize(prompt)
    if not any(hint in normalized for hint in BUTTON_HINTS):
        return None

    accent = _extract_color(prompt, normalized)
    if accent is None:
        return None

    return {
        "accent": accent,
        # Keep tonal buttons in the same hue while softening saturation.
        "accent_container": f"color-mix(in srgb, {accent} 24%, white)",
    }


def _extract_color(prompt: str, normalized: str) -> str | None:
    hex_match = HEX_COLOR_RE.search(prompt)
    if hex_match:
        return hex_match.group(0).lower()

    color_function_match = COLOR_FUNCTION_RE.search(prompt)
    if color_function_match:
        return " ".join(color_function_match.group(0).split())

    if not any(hint in normalized for hint in COLOR_INTENT_HINTS):
        return None

    for phrase, color in ENGLISH_COLOR_ALIASES:
        if phrase in normalized:
            return color

    for pattern, color in RUSSIAN_COLOR_PATTERNS:
        if pattern.search(normalized):
            return color

    for word in ENGLISH_WORD_RE.findall(normalized):
        if word in CSS_NAMED_COLORS:
            return word

    return None


def _normalize(prompt: str) -> str:
    return prompt.lower().replace("ё", "е").strip()

