import type { DuiDslDocument } from './types';

const INDENT = '  ';
const IDENTIFIER_RE = /^[A-Za-z_][A-Za-z0-9_.-]*$/;
const RESERVED_WORDS = new Set(['true', 'false', 'null']);

function isIdentifier(value: string): boolean {
  return IDENTIFIER_RE.test(value) && !RESERVED_WORDS.has(value);
}

function formatIdentifier(value: string): string {
  if (isIdentifier(value)) {
    return value;
  }
  return JSON.stringify(value);
}

function formatKey(value: string): string {
  if (isIdentifier(value)) {
    return value;
  }
  return JSON.stringify(value);
}

function formatArray(values: unknown[], indentLevel: number): string {
  if (values.length === 0) {
    return '[]';
  }

  const inlineValues = values.map((value) => formatValue(value, indentLevel));
  const inline = `[${inlineValues.join(', ')}]`;
  if (inline.length <= 88 && values.every((value) => typeof value !== 'object' || value === null)) {
    return inline;
  }

  const indent = INDENT.repeat(indentLevel);
  const innerIndent = INDENT.repeat(indentLevel + 1);
  const rows = values.map((value) => `${innerIndent}${formatValue(value, indentLevel + 1)}`);
  return `[\n${rows.join(',\n')}\n${indent}]`;
}

function formatObject(input: Record<string, unknown>, indentLevel: number): string {
  const entries = Object.entries(input);
  if (entries.length === 0) {
    return '{}';
  }

  const inlineParts = entries.map(([key, value]) => `${formatKey(key)}: ${formatValue(value, indentLevel)}`);
  const inline = `{ ${inlineParts.join(', ')} }`;
  if (inline.length <= 100 && entries.every(([, value]) => typeof value !== 'object' || value === null)) {
    return inline;
  }

  const indent = INDENT.repeat(indentLevel);
  const innerIndent = INDENT.repeat(indentLevel + 1);
  const rows = entries.map(
    ([key, value]) => `${innerIndent}${formatKey(key)}: ${formatValue(value, indentLevel + 1)}`,
  );
  return `{\n${rows.join(',\n')}\n${indent}}`;
}

function formatValue(value: unknown, indentLevel: number): string {
  if (value === null) {
    return 'null';
  }
  if (typeof value === 'string') {
    if (isIdentifier(value)) {
      return value;
    }
    return JSON.stringify(value);
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  if (Array.isArray(value)) {
    return formatArray(value, indentLevel);
  }
  if (typeof value === 'object') {
    return formatObject(value as Record<string, unknown>, indentLevel);
  }
  return JSON.stringify(String(value));
}

function pushOptionalObjectBlock(
  lines: string[],
  label: string,
  value: Record<string, unknown>,
  indentLevel: number,
): void {
  if (Object.keys(value).length === 0) {
    return;
  }
  const indent = INDENT.repeat(indentLevel);
  lines.push(`${indent}${label} ${formatObject(value, indentLevel)}`);
}

export function serializeDuiDslDocument(document: DuiDslDocument): string {
  const lines: string[] = [];
  lines.push(`surface ${formatIdentifier(document.surface.id)} {`);
  lines.push(
    `${INDENT}surface_meta { title: ${formatValue(document.surface.title, 1)}, route: ${formatValue(document.surface.route, 1)} }`,
  );
  lines.push(
    `${INDENT}meta { document_id: ${formatValue(document.meta.document_id, 1)}, revision: ${document.meta.revision}, created_by: ${formatValue(document.meta.created_by, 1)} }`,
  );
  if (Object.keys(document.theme.tokens).length === 0) {
    lines.push(
      `${INDENT}theme { profile: ${formatValue(document.theme.profile, 1)} density: ${formatValue(document.theme.density, 1)} }`,
    );
  } else {
    lines.push(
      `${INDENT}theme { profile: ${formatValue(document.theme.profile, 1)} density: ${formatValue(document.theme.density, 1)} tokens ${formatObject(document.theme.tokens, 1)} }`,
    );
  }
  pushOptionalObjectBlock(lines, 'layout_constraints', document.layout_constraints, 1);
  pushOptionalObjectBlock(lines, 'state', document.state.locals, 1);

  for (const action of document.actions) {
    lines.push('');
    lines.push(`${INDENT}action ${formatIdentifier(action.id)} {`);
    lines.push(`${INDENT}${INDENT}type: ${formatValue(action.type, 2)}`);
    pushOptionalObjectBlock(lines, 'params', action.params, 2);
    lines.push(`${INDENT}}`);
  }

  for (const node of document.nodes) {
    lines.push('');
    lines.push(`${INDENT}node ${formatIdentifier(node.id)}: ${formatIdentifier(node.type)} {`);
    pushOptionalObjectBlock(lines, 'props', node.props, 2);
    pushOptionalObjectBlock(lines, 'style', node.style, 2);
    pushOptionalObjectBlock(lines, 'layout', node.layout, 2);
    pushOptionalObjectBlock(lines, 'a11y', node.a11y, 2);
    if (node.visible_when) {
      pushOptionalObjectBlock(lines, 'visible_when', node.visible_when, 2);
    }
    if (node.enabled_when) {
      pushOptionalObjectBlock(lines, 'enabled_when', node.enabled_when, 2);
    }
    if (node.children.length > 0) {
      lines.push(`${INDENT}${INDENT}children: ${formatArray(node.children, 2)}`);
    }
    if (Object.keys(node.slots).length > 0) {
      lines.push(`${INDENT}${INDENT}slots ${formatObject(node.slots, 2)}`);
    }
    if (Object.keys(node.on).length > 0) {
      lines.push(`${INDENT}${INDENT}on ${formatObject(node.on, 2)}`);
    }
    lines.push(`${INDENT}}`);
  }

  for (const binding of document.bindings) {
    lines.push('');
    lines.push(`${INDENT}binding ${formatIdentifier(binding.id)} {`);
    lines.push(`${INDENT}${INDENT}source: ${formatValue(binding.source, 2)}`);
    lines.push(`${INDENT}${INDENT}select: ${formatValue(binding.select, 2)}`);
    pushOptionalObjectBlock(lines, 'args', binding.args, 2);
    pushOptionalObjectBlock(lines, 'cache', binding.cache, 2);
    lines.push(`${INDENT}}`);
  }

  lines.push('}');
  return `${lines.join('\n')}\n`;
}
