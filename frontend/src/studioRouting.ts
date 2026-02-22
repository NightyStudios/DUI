import { ApiError } from './api';
import {
  DASHBOARD_SURFACE_ID,
  LESSON_SURFACE_ID,
} from './studioConfig';

export type BusyAction = 'refresh' | 'generate' | 'parse' | 'commit' | 'revert' | null;
export type AppRoute = { kind: 'dashboard' } | { kind: 'lesson'; lessonId: string };

export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.message} (HTTP ${error.status})`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Непредвиденная ошибка';
}

export function getBusyActionLabel(action: BusyAction): string {
  if (action === 'refresh') {
    return 'обновление';
  }
  if (action === 'generate') {
    return 'генерация';
  }
  if (action === 'parse') {
    return 'разбор';
  }
  if (action === 'commit') {
    return 'коммит';
  }
  if (action === 'revert') {
    return 'откат';
  }
  return 'готово';
}

export function normalizePathname(pathname: string): string {
  if (!pathname || pathname === '/') {
    return '/dashboard';
  }
  return pathname;
}

export function resolveRoute(pathname: string): AppRoute {
  const normalized = normalizePathname(pathname);
  if (normalized.startsWith('/lesson/')) {
    const lessonId = decodeURIComponent(normalized.replace('/lesson/', '').trim());
    if (lessonId) {
      return { kind: 'lesson', lessonId };
    }
  }
  return { kind: 'dashboard' };
}

export function isLessonSurfaceId(surfaceId: string): boolean {
  const normalized = surfaceId.trim().toLowerCase();
  return normalized === LESSON_SURFACE_ID || normalized.startsWith('math_lms.lesson');
}

export function routeForSurface(surfaceId: string, lessonId: string): string {
  if (isLessonSurfaceId(surfaceId)) {
    return `/lesson/${encodeURIComponent(lessonId)}`;
  }
  return '/dashboard';
}

export function surfaceForRoute(route: AppRoute): string {
  if (route.kind === 'lesson') {
    return LESSON_SURFACE_ID;
  }
  return DASHBOARD_SURFACE_ID;
}
