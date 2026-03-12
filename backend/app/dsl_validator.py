from __future__ import annotations

import re

from .dsl_catalog import (
    ACTION_TYPE_ALLOWLIST,
    DSL_VERSION,
    MAX_BINDINGS_PER_DOCUMENT,
    MAX_NODES_PER_DOCUMENT,
    THEME_TOKEN_ALLOWLIST,
    ZONE_ALLOWLIST,
)
from .dsl_legacy_adapter import canonicalize_document
from .dsl_models import DuiDslDocument, DuiDslValidationIssue, DuiDslValidationResult

NODE_ID_RE = re.compile(r"^[a-z][a-z0-9_\-.]{2,63}$")
CAPABILITY_SOURCE_PREFIX = "capability:"


class DuiDslValidator:
    @staticmethod
    def validate(document: DuiDslDocument) -> DuiDslValidationResult:
        legacy_node_count = len(document.legacy_nodes)
        canonical_document = canonicalize_document(document)

        errors: list[DuiDslValidationIssue] = []
        warnings: list[DuiDslValidationIssue] = []

        if canonical_document.dsl_version != DSL_VERSION:
            errors.append(
                DuiDslValidationIssue(
                    severity="error",
                    code="dsl.version_unsupported",
                    message=f"Unsupported dsl_version '{canonical_document.dsl_version}'",
                    path="dsl_version",
                )
            )

        if legacy_node_count > MAX_NODES_PER_DOCUMENT:
            errors.append(
                DuiDslValidationIssue(
                    severity="error",
                    code="dsl.too_many_nodes",
                    message=f"Document has {legacy_node_count} legacy nodes, maximum is {MAX_NODES_PER_DOCUMENT}",
                    path="nodes",
                )
            )

        if len(canonical_document.bindings) > MAX_BINDINGS_PER_DOCUMENT:
            errors.append(
                DuiDslValidationIssue(
                    severity="error",
                    code="dsl.too_many_bindings",
                    message=(
                        f"Document has {len(canonical_document.bindings)} bindings, "
                        f"maximum is {MAX_BINDINGS_PER_DOCUMENT}"
                    ),
                    path="bindings",
                )
            )

        action_ids: dict[str, int] = {}
        for index, action in enumerate(canonical_document.actions):
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

        binding_ids: dict[str, int] = {}
        for index, binding in enumerate(canonical_document.bindings):
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

        DuiDslValidator._validate_widget_graph(
            document=canonical_document,
            errors=errors,
            warnings=warnings,
            binding_ids=set(binding_ids.keys()),
        )

        for key, value in canonical_document.theme.tokens.items():
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

        if not (canonical_document.pages or canonical_document.groups or canonical_document.widgets):
            errors.append(
                DuiDslValidationIssue(
                    severity="error",
                    code="graph.empty",
                    message="Document must contain at least one page, group, or widget",
                    path="widgets",
                )
            )

        stats = {
            "legacy_node_count": legacy_node_count,
            "page_count": len(canonical_document.pages),
            "group_count": len(canonical_document.groups),
            "widget_count": len(canonical_document.widgets),
            "action_count": len(canonical_document.actions),
            "binding_count": len(canonical_document.bindings),
            "error_count": len(errors),
            "warning_count": len(warnings),
        }
        return DuiDslValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings, stats=stats)

    @staticmethod
    def _validate_widget_graph(
        *,
        document: DuiDslDocument,
        errors: list[DuiDslValidationIssue],
        warnings: list[DuiDslValidationIssue],
        binding_ids: set[str],
    ) -> None:
        if not (document.pages or document.groups or document.widgets):
            return

        page_ids: dict[str, int] = {}
        group_ids: dict[str, int] = {}
        widget_ids: dict[str, int] = {}

        for index, page in enumerate(document.pages):
            page_path = f"pages[{index}]"
            if page.id in page_ids:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="page.id_duplicate",
                        message=f"Page id '{page.id}' is duplicated",
                        path=f"{page_path}.id",
                    )
                )
            else:
                page_ids[page.id] = index

            if not NODE_ID_RE.match(page.id):
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="page.id_invalid",
                        message=f"Page id '{page.id}' does not match allowed pattern",
                        path=f"{page_path}.id",
                    )
                )

        default_page_count = sum(1 for page in document.pages if page.is_default)
        if document.pages and default_page_count == 0:
            warnings.append(
                DuiDslValidationIssue(
                    severity="warning",
                    code="page.default_missing",
                    message="No default page is set; first page will be treated as active",
                    path="pages",
                )
            )
        if default_page_count > 1:
            warnings.append(
                DuiDslValidationIssue(
                    severity="warning",
                    code="page.default_multiple",
                    message="Multiple default pages set; first match will be treated as active",
                    path="pages",
                )
            )

        for index, group in enumerate(document.groups):
            group_path = f"groups[{index}]"
            if group.id in group_ids:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="group.id_duplicate",
                        message=f"Group id '{group.id}' is duplicated",
                        path=f"{group_path}.id",
                    )
                )
            else:
                group_ids[group.id] = index

            if not NODE_ID_RE.match(group.id):
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="group.id_invalid",
                        message=f"Group id '{group.id}' does not match allowed pattern",
                        path=f"{group_path}.id",
                    )
                )

            if group.page_id and group.page_id not in page_ids:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="group.page_unknown",
                        message=f"Group '{group.id}' references unknown page '{group.page_id}'",
                        path=f"{group_path}.page_id",
                    )
                )

            if group.zone not in ZONE_ALLOWLIST:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="group.zone_invalid",
                        message=f"Zone '{group.zone}' is not allowed",
                        path=f"{group_path}.zone",
                    )
                )

        for index, widget in enumerate(document.widgets):
            widget_path = f"widgets[{index}]"
            if widget.id in widget_ids:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="widget.id_duplicate",
                        message=f"Widget id '{widget.id}' is duplicated",
                        path=f"{widget_path}.id",
                    )
                )
            else:
                widget_ids[widget.id] = index

            if not NODE_ID_RE.match(widget.id):
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="widget.id_invalid",
                        message=f"Widget id '{widget.id}' does not match allowed pattern",
                        path=f"{widget_path}.id",
                    )
                )

            if widget.zone and widget.zone not in ZONE_ALLOWLIST:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="widget.zone_invalid",
                        message=f"Zone '{widget.zone}' is not allowed",
                        path=f"{widget_path}.zone",
                    )
                )

            if widget.group_id and widget.group_id not in group_ids:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="widget.group_unknown",
                        message=f"Widget '{widget.id}' references unknown group '{widget.group_id}'",
                        path=f"{widget_path}.group_id",
                    )
                )

            if widget.binding_id and widget.binding_id not in binding_ids:
                errors.append(
                    DuiDslValidationIssue(
                        severity="error",
                        code="widget.binding_unknown",
                        message=f"Widget '{widget.id}' references unknown binding '{widget.binding_id}'",
                        path=f"{widget_path}.binding_id",
                    )
                )

        widget_id_set = set(widget_ids.keys())
        group_id_set = set(group_ids.keys())
        page_id_set = set(page_ids.keys())

        for index, page in enumerate(document.pages):
            page_path = f"pages[{index}]"
            for idx, group_id in enumerate(page.group_ids):
                if group_id not in group_id_set:
                    errors.append(
                        DuiDslValidationIssue(
                            severity="error",
                            code="page.group_unknown",
                            message=f"Page '{page.id}' references unknown group '{group_id}'",
                            path=f"{page_path}.group_ids[{idx}]",
                        )
                    )

        for index, group in enumerate(document.groups):
            group_path = f"groups[{index}]"
            for idx, widget_id in enumerate(group.widget_ids):
                if widget_id not in widget_id_set:
                    errors.append(
                        DuiDslValidationIssue(
                            severity="error",
                            code="group.widget_unknown",
                            message=f"Group '{group.id}' references unknown widget '{widget_id}'",
                            path=f"{group_path}.widget_ids[{idx}]",
                        )
                    )

        for index, widget in enumerate(document.widgets):
            widget_path = f"widgets[{index}]"
            for link_idx, link in enumerate(widget.links):
                if link.page and link.page not in page_id_set:
                    errors.append(
                        DuiDslValidationIssue(
                            severity="error",
                            code="widget.link_page_unknown",
                            message=f"Widget '{widget.id}' links to unknown page '{link.page}'",
                            path=f"{widget_path}.links[{link_idx}].page",
                        )
                    )
                if link.widget and link.widget not in widget_id_set:
                    errors.append(
                        DuiDslValidationIssue(
                            severity="error",
                            code="widget.link_widget_unknown",
                            message=f"Widget '{widget.id}' links to unknown widget '{link.widget}'",
                            path=f"{widget_path}.links[{link_idx}].widget",
                        )
                    )

            if (
                widget.visible
                and not widget.capability_id
                and not widget.template_id
                and not widget.binding_id
                and not widget.props
            ):
                warnings.append(
                    DuiDslValidationIssue(
                        severity="warning",
                        code="widget.data_source_missing",
                        message=f"Widget '{widget.id}' has no capability/template/binding and no props",
                        path=f"{widget_path}.capability_id",
                    )
                )
