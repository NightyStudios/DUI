import type {
  A2UiEnvelope,
  DuiDslCommitResponse,
  DuiDslDocument,
  DuiDslIntentResponse,
  DuiDslParseResponse,
  DuiDslValidateResponse,
  DuiMode,
  IntentResponse,
  LmsDashboardData,
  LmsLessonData,
  UiManifest,
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
const DEFAULT_SESSION_ID = 'demo-session';
const DEFAULT_SURFACE_ID = 'math_lms.dashboard';
const DEFAULT_CATALOG_VERSION = 'math-lms-catalog-v1';

export interface SurfaceContext {
  sessionId?: string;
  surfaceId?: string;
  turnId?: string;
  mode?: DuiMode;
}

async function parseJsonOrThrow<T>(response: Response, message: string): Promise<T> {
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`${message}: ${response.status} ${errorBody}`);
  }
  return response.json() as Promise<T>;
}

function randomId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function buildEnvelope(
  messageType: A2UiEnvelope['message_type'],
  payload: Record<string, unknown>,
  context?: SurfaceContext,
): A2UiEnvelope {
  return {
    envelope_version: 'a2ui.v0',
    message_id: randomId(),
    session_id: context?.sessionId ?? DEFAULT_SESSION_ID,
    surface_id: context?.surfaceId ?? DEFAULT_SURFACE_ID,
    turn_id: context?.turnId ?? randomId(),
    sent_at: new Date().toISOString(),
    mode: context?.mode ?? 'extended',
    catalog_version: DEFAULT_CATALOG_VERSION,
    message_type: messageType,
    payload,
  };
}

async function sendEnvelope(
  messageType: A2UiEnvelope['message_type'],
  expectedResponseType: A2UiEnvelope['message_type'],
  payload: Record<string, unknown>,
  context?: SurfaceContext,
): Promise<Record<string, unknown>> {
  const envelope = buildEnvelope(messageType, payload, context);
  const response = await fetch(`${API_BASE}/a2ui/envelope`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(envelope),
  });

  const parsed = await parseJsonOrThrow<A2UiEnvelope>(response, 'A2UI envelope request failed');
  if (parsed.message_type !== expectedResponseType) {
    throw new Error(`Unexpected envelope response type: ${parsed.message_type}`);
  }
  return parsed.payload;
}

export async function fetchCurrentManifest(context?: SurfaceContext): Promise<UiManifest> {
  const payload = await sendEnvelope(
    'manifest.current.request',
    'manifest.current.response',
    {},
    context,
  );
  return payload.manifest as UiManifest;
}

export async function fetchRevisions(context?: SurfaceContext): Promise<UiManifest[]> {
  const payload = await sendEnvelope(
    'manifest.revisions.request',
    'manifest.revisions.response',
    {},
    context,
  );
  return payload.revisions as UiManifest[];
}

export async function fetchCurrentDslDocument(context?: SurfaceContext): Promise<DuiDslDocument> {
  const payload = await sendEnvelope(
    'dsl.current.request',
    'dsl.current.response',
    {},
    context,
  );
  return payload.document as DuiDslDocument;
}

export async function fetchDslRevisions(context?: SurfaceContext): Promise<DuiDslDocument[]> {
  const payload = await sendEnvelope(
    'dsl.revisions.request',
    'dsl.revisions.response',
    {},
    context,
  );
  return payload.documents as DuiDslDocument[];
}

export async function fetchDashboardData(): Promise<LmsDashboardData> {
  const response = await fetch(`${API_BASE}/lms/dashboard`);
  return parseJsonOrThrow<LmsDashboardData>(response, 'Failed to load dashboard');
}

export async function fetchLesson(lessonId: string): Promise<LmsLessonData> {
  const response = await fetch(`${API_BASE}/lms/lesson/${lessonId}`);
  return parseJsonOrThrow<LmsLessonData>(response, 'Failed to load lesson');
}

export async function requestIntent(
  userPrompt: string,
  currentManifestId?: string,
  mode: DuiMode = 'extended',
  context?: SurfaceContext,
): Promise<IntentResponse> {
  const payload = await sendEnvelope(
    'intent.request',
    'intent.response',
    { user_prompt: userPrompt, current_manifest_id: currentManifestId },
    { ...context, mode },
  );
  return payload as unknown as IntentResponse;
}

export async function requestDslIntent(
  userPrompt: string,
  mode: DuiMode = 'extended',
  context?: SurfaceContext,
): Promise<DuiDslIntentResponse> {
  const payload = await sendEnvelope(
    'dsl.intent.request',
    'dsl.intent.response',
    { user_prompt: userPrompt },
    { ...context, mode },
  );
  return payload as unknown as DuiDslIntentResponse;
}

export async function parseDslSource(
  sourceText: string,
  context?: SurfaceContext,
): Promise<DuiDslParseResponse> {
  const payload = await sendEnvelope(
    'dsl.parse.request',
    'dsl.parse.response',
    { source_text: sourceText },
    context,
  );
  return payload as unknown as DuiDslParseResponse;
}

export async function validateDslDocument(
  document: DuiDslDocument,
  context?: SurfaceContext,
): Promise<DuiDslValidateResponse> {
  const payload = await sendEnvelope(
    'dsl.validate.request',
    'dsl.validate.response',
    { document },
    context,
  );
  return payload as unknown as DuiDslValidateResponse;
}

export async function commitDslDocument(
  document: DuiDslDocument,
  approvedBy = 'poc-user',
  context?: SurfaceContext,
): Promise<DuiDslCommitResponse> {
  const payload = await sendEnvelope(
    'dsl.commit.request',
    'dsl.commit.response',
    { document, approved_by: approvedBy },
    context,
  );
  return payload as unknown as DuiDslCommitResponse;
}

export async function commitPatchPlan(patchPlanId: string, context?: SurfaceContext): Promise<UiManifest> {
  const payload = await sendEnvelope(
    'commit.request',
    'commit.response',
    { patch_plan_id: patchPlanId, approved_by: 'poc-user' },
    context,
  );
  const data = payload as { manifest: UiManifest };
  return data.manifest;
}

export async function revertRevision(targetRevision: number, context?: SurfaceContext): Promise<UiManifest> {
  const payload = await sendEnvelope(
    'revert.request',
    'revert.response',
    { target_revision: targetRevision, approved_by: 'poc-user' },
    context,
  );
  const data = payload as { manifest: UiManifest };
  return data.manifest;
}
