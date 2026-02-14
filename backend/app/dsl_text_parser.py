from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .dsl_models import (
    DuiDslAction,
    DuiDslBinding,
    DuiDslDocument,
    DuiDslMeta,
    DuiDslNode,
    DuiDslState,
    DuiDslSurface,
    DuiDslTheme,
)


@dataclass(frozen=True)
class Token:
    type: str
    value: str
    line: int
    column: int


class DuiLangParseError(ValueError):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"{message} at line {line}, column {column}")
        self.line = line
        self.column = column


TOKEN_RE = re.compile(
    r"""
    (?P<WHITESPACE>\s+)
    |(?P<COMMENT>//[^\n]*|\#[^\n]*)
    |(?P<STRING>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')
    |(?P<NUMBER>-?\d+(?:\.\d+)?)
    |(?P<LBRACE>\{)
    |(?P<RBRACE>\})
    |(?P<LBRACKET>\[)
    |(?P<RBRACKET>\])
    |(?P<COLON>:)
    |(?P<COMMA>,)
    |(?P<IDENT>[A-Za-z_][A-Za-z0-9_.-]*)
    """,
    re.VERBOSE,
)


def _decode_string(raw: str) -> str:
    if raw.startswith('"'):
        return json.loads(raw)
    # Single-quoted string support.
    escaped = raw[1:-1].replace("\\'", "'")
    return bytes(escaped, "utf-8").decode("unicode_escape")


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    line = 1
    col = 1

    while pos < len(source):
        match = TOKEN_RE.match(source, pos)
        if not match:
            raise DuiLangParseError("Unexpected character", line, col)

        token_type = match.lastgroup
        assert token_type is not None
        value = match.group(0)

        if token_type not in {"WHITESPACE", "COMMENT"}:
            tokens.append(Token(token_type, value, line, col))

        line_breaks = value.count("\n")
        if line_breaks:
            line += line_breaks
            col = len(value.rsplit("\n", 1)[-1]) + 1
        else:
            col += len(value)

        pos = match.end()

    tokens.append(Token("EOF", "", line, col))
    return tokens


class Parser:
    def __init__(self, source: str):
        self.tokens = tokenize(source)
        self.index = 0

    def current(self) -> Token:
        return self.tokens[self.index]

    def advance(self) -> Token:
        token = self.current()
        self.index += 1
        return token

    def expect(self, token_type: str, value: str | None = None) -> Token:
        token = self.current()
        if token.type != token_type:
            raise DuiLangParseError(f"Expected {token_type}, got {token.type}", token.line, token.column)
        if value is not None and token.value != value:
            raise DuiLangParseError(f"Expected '{value}', got '{token.value}'", token.line, token.column)
        self.index += 1
        return token

    def expect_ident(self, value: str | None = None) -> Token:
        token = self.expect("IDENT")
        if value is not None and token.value != value:
            raise DuiLangParseError(f"Expected identifier '{value}', got '{token.value}'", token.line, token.column)
        return token

    def parse_identifier_like(self) -> str:
        token = self.current()
        if token.type == "IDENT":
            self.advance()
            return token.value
        if token.type == "STRING":
            self.advance()
            return _decode_string(token.value)
        raise DuiLangParseError("Expected identifier or string", token.line, token.column)

    def parse_scalar(self) -> Any:
        token = self.current()
        if token.type == "STRING":
            self.advance()
            return _decode_string(token.value)
        if token.type == "NUMBER":
            self.advance()
            return float(token.value) if "." in token.value else int(token.value)
        if token.type == "IDENT":
            self.advance()
            if token.value == "true":
                return True
            if token.value == "false":
                return False
            if token.value == "null":
                return None
            return token.value
        raise DuiLangParseError("Expected scalar value", token.line, token.column)

    def parse_value(self) -> Any:
        token = self.current()
        if token.type == "LBRACE":
            return self.parse_object()
        if token.type == "LBRACKET":
            return self.parse_array()
        return self.parse_scalar()

    def parse_array(self) -> list[Any]:
        values: list[Any] = []
        self.expect("LBRACKET")
        while self.current().type != "RBRACKET":
            values.append(self.parse_value())
            if self.current().type == "COMMA":
                self.advance()
        self.expect("RBRACKET")
        return values

    def parse_object(self) -> dict[str, Any]:
        obj: dict[str, Any] = {}
        self.expect("LBRACE")
        while self.current().type != "RBRACE":
            key = self.parse_identifier_like()
            if self.current().type == "COLON":
                self.advance()
                value = self.parse_value()
            elif self.current().type in {"LBRACE", "LBRACKET"}:
                value = self.parse_value()
            else:
                token = self.current()
                raise DuiLangParseError("Expected ':' or value block", token.line, token.column)
            obj[key] = value
            if self.current().type == "COMMA":
                self.advance()
        self.expect("RBRACE")
        return obj

    def parse_named_block(self) -> dict[str, Any]:
        # Expects current token to be LBRACE.
        return self.parse_object()

    def parse_node(self) -> DuiDslNode:
        self.expect_ident("node")
        node_id = self.parse_identifier_like()
        self.expect("COLON")
        node_type = self.parse_identifier_like()
        payload = self.parse_named_block()

        props = payload.get("props", {})
        style = payload.get("style", {})
        layout = payload.get("layout", {})
        a11y = payload.get("a11y", {})
        children = payload.get("children", [])
        slots = payload.get("slots", {})
        on = payload.get("on", {})
        visible_when = payload.get("visibleWhen", payload.get("visible_when"))
        enabled_when = payload.get("enabledWhen", payload.get("enabled_when"))

        # Any unknown top-level keys in node block fall back into props for flexibility.
        for key, value in payload.items():
            if key in {
                "props",
                "style",
                "layout",
                "a11y",
                "children",
                "slots",
                "on",
                "visibleWhen",
                "visible_when",
                "enabledWhen",
                "enabled_when",
            }:
                continue
            if key not in props:
                props[key] = value

        return DuiDslNode(
            id=node_id,
            type=node_type,
            props=props if isinstance(props, dict) else {},
            style=style if isinstance(style, dict) else {},
            layout=layout if isinstance(layout, dict) else {},
            a11y=a11y if isinstance(a11y, dict) else {},
            children=children if isinstance(children, list) else [],
            slots=slots if isinstance(slots, dict) else {},
            on=on if isinstance(on, dict) else {},
            visible_when=visible_when if isinstance(visible_when, dict) else None,
            enabled_when=enabled_when if isinstance(enabled_when, dict) else None,
        )

    def parse_binding(self) -> DuiDslBinding:
        self.expect_ident("binding")
        binding_id = self.parse_identifier_like()
        payload = self.parse_named_block()
        return DuiDslBinding(
            id=binding_id,
            source=str(payload.get("source", "")),
            select=str(payload.get("select", "$")),
            args=payload.get("args", {}) if isinstance(payload.get("args", {}), dict) else {},
            cache=payload.get("cache", {}) if isinstance(payload.get("cache", {}), dict) else {},
        )

    def parse_action(self) -> DuiDslAction:
        self.expect_ident("action")
        action_id = self.parse_identifier_like()
        payload = self.parse_named_block()
        return DuiDslAction(
            id=action_id,
            type=str(payload.get("type", "")),
            params=payload.get("params", {}) if isinstance(payload.get("params", {}), dict) else {},
        )

    def parse_theme(self) -> DuiDslTheme:
        self.expect_ident("theme")
        payload = self.parse_named_block()
        profile = payload.get("profile", "default")
        density = payload.get("density", "comfortable")
        tokens = payload.get("tokens", {})
        return DuiDslTheme(
            profile=str(profile),
            density=str(density),
            tokens=tokens if isinstance(tokens, dict) else {},
        )

    def parse_meta(self, previous: DuiDslMeta | None = None) -> DuiDslMeta:
        self.expect_ident("meta")
        payload = self.parse_named_block()
        if previous is None:
            previous = DuiDslMeta()
        if "document_id" in payload:
            previous.document_id = str(payload["document_id"])
        if "revision" in payload:
            previous.revision = int(payload["revision"])
        if "created_by" in payload:
            previous.created_by = str(payload["created_by"])
        return previous

    def parse_state(self) -> DuiDslState:
        self.expect_ident("state")
        payload = self.parse_named_block()
        return DuiDslState(locals=payload if isinstance(payload, dict) else {})

    def parse_document(self) -> DuiDslDocument:
        self.expect_ident("surface")
        surface_id = self.parse_identifier_like()
        self.expect("LBRACE")

        surface = DuiDslSurface(id=surface_id, title="Untitled Surface", route="/")
        meta = DuiDslMeta()
        theme = DuiDslTheme()
        state = DuiDslState()
        nodes: list[DuiDslNode] = []
        bindings: list[DuiDslBinding] = []
        actions: list[DuiDslAction] = []
        layout_constraints: dict[str, Any] = {}

        while self.current().type != "RBRACE":
            token = self.current()
            if token.type != "IDENT":
                raise DuiLangParseError("Expected section keyword", token.line, token.column)

            keyword = token.value
            if keyword == "meta":
                meta = self.parse_meta(meta)
            elif keyword == "theme":
                theme = self.parse_theme()
            elif keyword == "state":
                state = self.parse_state()
            elif keyword == "surface_meta":
                self.advance()
                payload = self.parse_named_block()
                title = payload.get("title")
                route = payload.get("route")
                if isinstance(title, str):
                    surface.title = title
                if isinstance(route, str):
                    surface.route = route
            elif keyword == "layout_constraints":
                self.advance()
                payload = self.parse_named_block()
                if isinstance(payload, dict):
                    layout_constraints = payload
            elif keyword == "node":
                nodes.append(self.parse_node())
            elif keyword == "binding":
                bindings.append(self.parse_binding())
            elif keyword == "action":
                actions.append(self.parse_action())
            else:
                raise DuiLangParseError(f"Unknown top-level section '{keyword}'", token.line, token.column)

        self.expect("RBRACE")
        self.expect("EOF")

        return DuiDslDocument(
            surface=surface,
            meta=meta,
            theme=theme,
            state=state,
            nodes=nodes,
            bindings=bindings,
            actions=actions,
            layout_constraints=layout_constraints,
        )


def parse_dui_lang(source: str) -> DuiDslDocument:
    parser = Parser(source)
    return parser.parse_document()
