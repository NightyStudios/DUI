import type {
  DuiDslCommitResponse,
  DuiDslDocument,
  DuiDslIntentResponse,
  DuiDslParseResponse,
  LmsLessonData,
  DuiMode,
  LmsDashboardData,
  UiManifest,
  UiSurfaceSummary,
} from './types';

export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000';

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

interface ErrorLikePayload {
  detail?: string | { message?: string };
  message?: string;
}

function extractErrorMessage(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  const typed = payload as ErrorLikePayload;
  if (typeof typed.message === 'string' && typed.message.trim()) {
    return typed.message;
  }
  if (typeof typed.detail === 'string' && typed.detail.trim()) {
    return typed.detail;
  }
  if (typed.detail && typeof typed.detail === 'object' && typeof typed.detail.message === 'string' && typed.detail.message.trim()) {
    return typed.detail.message;
  }
  return null;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...(init?.headers ?? {}),
    },
  });

  const text = await response.text();
  const payload = text ? (JSON.parse(text) as unknown) : null;

  if (!response.ok) {
    const message = extractErrorMessage(payload) ?? `Ошибка запроса: ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return payload as T;
}

export function fetchCurrentManifest(surfaceId: string): Promise<UiManifest> {
  return requestJson<UiManifest>(`/ui/manifest/current?surface_id=${encodeURIComponent(surfaceId)}`);
}

export function fetchManifestRevisions(surfaceId: string): Promise<UiManifest[]> {
  return requestJson<UiManifest[]>(`/ui/manifest/revisions?surface_id=${encodeURIComponent(surfaceId)}`);
}

export function fetchSurfaces(): Promise<UiSurfaceSummary[]> {
  return requestJson<UiSurfaceSummary[]>('/ui/surfaces');
}

export function fetchCurrentDsl(surfaceId: string): Promise<DuiDslDocument> {
  return requestJson<DuiDslDocument>(`/ui/dsl/current?surface_id=${encodeURIComponent(surfaceId)}`);
}

export function fetchDashboardData(): Promise<LmsDashboardData> {
  return requestJson<LmsDashboardData>('/lms/dashboard');
}

export function fetchLessonData(lessonId: string): Promise<LmsLessonData> {
  return requestJson<LmsLessonData>(`/lms/lesson/${encodeURIComponent(lessonId)}`);
}

export function generateDslIntent(params: {
  prompt: string;
  surfaceId: string;
  mode: DuiMode;
  sessionId: string;
}): Promise<DuiDslIntentResponse> {
  return requestJson<DuiDslIntentResponse>('/ai/dsl/intent', {
    method: 'POST',
    body: JSON.stringify({
      user_prompt: params.prompt,
      scope: params.mode,
      surface_id: params.surfaceId,
      session_id: params.sessionId,
    }),
  });
}

export function parseDslSource(params: { source: string; surfaceId?: string }): Promise<DuiDslParseResponse> {
  const payload: Record<string, unknown> = {
    source_text: params.source,
  };

  if (typeof params.surfaceId === 'string' && params.surfaceId.trim().length > 0) {
    payload.surface_id = params.surfaceId;
  }

  return requestJson<DuiDslParseResponse>('/ui/dsl/parse', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function commitDslDocument(params: {
  document: DuiDslDocument;
  surfaceId: string;
  expectedManifestRevision?: number;
  expectedDslRevision?: number;
}): Promise<DuiDslCommitResponse> {
  return requestJson<DuiDslCommitResponse>('/ui/dsl/commit', {
    method: 'POST',
    body: JSON.stringify({
      document: params.document,
      surface_id: params.surfaceId,
      approved_by: 'dui-studio-ui',
      expected_manifest_revision: params.expectedManifestRevision,
      expected_dsl_revision: params.expectedDslRevision,
    }),
  });
}

export function revertManifest(params: { targetRevision: number; surfaceId: string }): Promise<{ manifest: UiManifest }> {
  return requestJson<{ manifest: UiManifest }>('/ai/ui/revert', {
    method: 'POST',
    body: JSON.stringify({
      target_revision: params.targetRevision,
      surface_id: params.surfaceId,
      approved_by: 'dui-studio-ui',
    }),
  });
}
