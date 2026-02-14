from __future__ import annotations

import re
from collections import defaultdict

from .dsl_catalog import (
    ACTION_TYPE_ALLOWLIST,
    DSL_VERSION,
    MAX_ACTIONS_PER_NODE,
    MAX_BINDINGS_PER_DOCUMENT,
    MAX_CHILDREN_PER_NODE,
    MAX_DEPTH_PER_DOCUMENT,
    MAX_NODES_PER_DOCUMENT,
    NODE_TYPE_ALLOWLIST,
    THEME_TOKEN_ALLOWLIST,
    ZONE_ALLOWLIST,
)
from .dsl_models import DuiDslDocument, DuiDslValidationIssue, DuiDslValidationResult

NODE_ID_RE = re.compile(r"^[a-z][a-z0-9_\-.]{2,63}$")
CAPABILITY_SOURCE_PREFIX = "capability:"


class DuiDslValidator:
    @staticmethod
    def validate(document: DuiDslDocument) -> DuiDslValidationResult:
        errors: list[DuiDslValidationIssue] = []
        warnings: list[DuiDslValidationIssue] = []

        if document.dsl_version != DSL_VERSION:
            errors.append(
                DuiDslValidationIssue(
                    severity="error",
                    code="dsl.version_unsupported",
                    message=f"Unsupported dsl_version '{document.dsl_version}'",
                    path="dsl_version",
                )
            )

        if len(document.nodes) > MAX_NODES_PER_DOCUMENT:
            errors.append(
                DuiDslValidationIssue(
                    severity="error",
                    code="dsl.too_many_nodes",
                    message=f"Document has {len(document.nodes)} nodes, maximum is {MAX_NODES_PER_DOCUMENT}",
                    path="nodes",
                )
            )

        if len(document.bindings) > MAX_BINDINGS_PER_DOCUMENT:
            errors.append(
                DuiDslValidationIssue(
                    severity="error",
                    code="dsl.too_many_bindings",
                    message=f"Document has {len(document.bindings)} bindings, maximum is {MAX_BINDINGS_PER_DOCUMENT}",
                    path="bindings",
                )
            )

        node_ids: dict[str, int] = {}
        for index, node in enumerate(document.nodes):
            node_path = f"nodes[{index}]"
            if node.id in node_ids:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="node.id_duplicate",
                        message=f"Node id '{node.id}' is duplicated",
                        path=f"{node_path}.id",
                    )
                )
            else:
                node_ids[node.id] = index

            if not NODE_ID_RE.match(node.id):
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="node.id_invalid",
                        message=f"Node id '{node.id}' does not match allowed pattern",
                        path=f"{node_path}.id",
                    )
                )

            if node.type not in NODE_TYPE_ALLOWLIST:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="node.type_unknown",
                        message=f"Node type '{node.type}' is not in allowlist",
                        path=f"{node_path}.type",
                    )
                )

            if len(node.children) > MAX_CHILDREN_PER_NODE:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="node.too_many_children",
                        message=f"Node '{node.id}' has too many children",
                        path=f"{node_path}.children",
                    )
                )

            if len(node.on) > MAX_ACTIONS_PER_NODE:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="node.too_many_actions",
                        message=f"Node '{node.id}' has too many event handlers",
                        path=f"{node_path}.on",
                    )
                )

            maybe_zone = node.props.get("zone")
            if maybe_zone is not None and maybe_zone not in ZONE_ALLOWLIST:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="node.zone_invalid",
                        message=f"Zone '{maybe_zone}' is not allowed",
                        path=f"{node_path}.props.zone",
                    )
                )

            maybe_capability = node.props.get("capability_id")
            if maybe_capability is not None and not isinstance(maybe_capability, str):
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="node.capability_invalid",
                        message="capability_id must be a string when provided",
                        path=f"{node_path}.props.capability_id",
                    )
                )

        node_id_set = set(node_ids.keys())
        for index, node in enumerate(document.nodes):
            node_path = f"nodes[{index}]"
            for child_idx, child_id in enumerate(node.children):
                if child_id not in node_id_set:
                    errors.append(
                        DuiDslValidationIssue(
                            severity="error",
                            code="node.child_unknown",
                            message=f"Unknown child node id '{child_id}'",
                            path=f"{node_path}.children[{child_idx}]",
                        )
                    )
            for slot_name, slot_children in node.slots.items():
                for child_idx, child_id in enumerate(slot_children):
                    if child_id not in node_id_set:
                        errors.append(
                            DuiDslValidationIssue(
                                severity="error",
                                code="node.slot_child_unknown",
                                message=f"Unknown child node id '{child_id}' in slot '{slot_name}'",
                                path=f"{node_path}.slots.{slot_name}[{child_idx}]",
                            )
                        )

        action_ids: dict[str, int] = {}
        for index, action in enumerate(document.actions):
            action_path = f"actions[{index}]"
            if action.id in action_ids:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="action.id_duplicate",
                        message=f"Action id '{action.id}' is duplicated",
                        path=f"{action_path}.id",
                    )
                )
            else:
                action_ids[action.id] = index

            if action.type not in ACTION_TYPE_ALLOWLIST:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="action.type_unknown",
                        message=f"Action type '{action.type}' is not in allowlist",
                        path=f"{action_path}.type",
                    )
                )

        for index, node in enumerate(document.nodes):
            node_path = f"nodes[{index}]"
            for event_name, action_ref in node.on.items():
                if action_ref not in action_ids:
                    errors.append(
                        DuiDslValidationIssue(
                            severity="error",
                            code="node.action_ref_unknown",
                            message=f"Unknown action reference '{action_ref}' for event '{event_name}'",
                            path=f"{node_path}.on.{event_name}",
                        )
                    )

        binding_ids: dict[str, int] = {}
        for index, binding in enumerate(document.bindings):
            binding_path = f"bindings[{index}]"
            if binding.id in binding_ids:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="binding.id_duplicate",
                        message=f"Binding id '{binding.id}' is duplicated",
                        path=f"{binding_path}.id",
                    )
                )
            else:
                binding_ids[binding.id] = index

            if not binding.source.startswith(CAPABILITY_SOURCE_PREFIX):
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="binding.source_invalid",
                        message="Binding source must start with 'capability:'",
                        path=f"{binding_path}.source",
                    )
                )

        for key, value in document.theme.tokens.items():
            if key not in THEME_TOKEN_ALLOWLIST:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="theme.token_unknown",
                        message=f"Theme token '{key}' is not allowed",
                        path=f"theme.tokens.{key}",
                    )
                )
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="theme.token_invalid",
                        message=f"Theme token '{key}' must be a non-empty string",
                        path=f"theme.tokens.{key}",
                    )
                )

        DuiDslValidator._validate_graph(document, errors)

        stats = {
            "node_count": len(document.nodes),
            "action_count": len(document.actions),
            "binding_count": len(document.bindings),
            "error_count": len(errors),
            "warning_count": len(warnings),
        }
        return DuiDslValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings, stats=stats)

    @staticmethod
    def _validate_graph(document: DuiDslDocument, errors: list[DuiDslValidationIssue]) -> None:
        if not document.nodes:
            errors.append(
                DuiDslValidationIssue(
                    severity="error",
                    code="graph.empty",
                    message="Document must contain at least one node",
                    path="nodes",
                )
            )
            return

        adjacency: dict[str, list[str]] = defaultdict(list)
        indegree: dict[str, int] = defaultdict(int)
        node_ids = {node.id for node in document.nodes}

        for node in document.nodes:
            for child in node.children:
                if child in node_ids:
                    adjacency[node.id].append(child)
                    indegree[child] += 1
            for slot_children in node.slots.values():
                for child in slot_children:
                    if child in node_ids:
                        adjacency[node.id].append(child)
                        indegree[child] += 1

        roots = [node.id for node in document.nodes if indegree[node.id] == 0]
        if not roots:
            errors.append(
                DuiDslValidationIssue(
                    severity="error",
                    code="graph.no_root",
                    message="Document graph has no root node",
                    path="nodes",
                )
            )
            return

        visited: set[str] = set()
        in_stack: set[str] = set()
        max_depth_found = 0

        def dfs(node_id: str, depth: int) -> None:
            nonlocal max_depth_found
            max_depth_found = max(max_depth_found, depth)
            if node_id in in_stack:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="graph.cycle",
                        message=f"Cycle detected at node '{node_id}'",
                        path=f"nodes[{node_id}]",
                    )
                )
                return
            if node_id in visited:
                return
            visited.add(node_id)
            in_stack.add(node_id)
            for child in adjacency.get(node_id, []):
                dfs(child, depth + 1)
            in_stack.remove(node_id)

        for root in roots:
            dfs(root, 1)

        if max_depth_found > MAX_DEPTH_PER_DOCUMENT:
            errors.append(
                DuiDslValidationIssue(
                    severity="error",
                    code="graph.depth_exceeded",
                    message=f"Graph depth {max_depth_found} exceeds limit {MAX_DEPTH_PER_DOCUMENT}",
                    path="nodes",
                )
            )

