import { useEffect, useMemo, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import {
  commitDslDocument,
  fetchCurrentDsl,
  fetchCurrentManifest,
  fetchDashboardData,
  fetchLessonData,
  fetchManifestRevisions,
  fetchSurfaces,
  generateDslIntent,
  parseDslSource,
  revertManifest,
} from './api';
import { starterDslSource } from './dslText';
import {
  DASHBOARD_SURFACE_ID,
  DEFAULT_LESSON_ID,
  FALLBACK_DASHBOARD,
  FALLBACK_LESSONS,
  FALLBACK_SURFACES,
  SESSION_ID,
} from './studioConfig';
import {
  describeError,
  normalizePathname,
  resolveRoute,
  routeForSurface,
  surfaceForRoute,
  type AppRoute,
  type BusyAction,
} from './studioRouting';
import type {
  DuiDslDocument,
  DuiMode,
  LmsDashboardData,
  LmsLessonData,
  UiManifest,
  UiSurfaceSummary,
} from './types';

function resolveDefaultTargetRevision(revisions: UiManifest[]): number | null {
  if (revisions.length < 2) {
    return null;
  }
  return revisions[revisions.length - 2]?.revision ?? null;
}

interface StudioControllerState {
  activeManifest: UiManifest | null;
  activeSurfaceId: string;
  busyAction: BusyAction;
  currentDsl: DuiDslDocument | null;
  currentRevision: number | string;
  currentRoute: AppRoute;
  dashboard: LmsDashboardData;
  draftDsl: DuiDslDocument | null;
  dslRevision: number | string;
  errorMessage: string;
  isGeneratorOpen: boolean;
  isMenuOpen: boolean;
  isSourceEditorOpen: boolean;
  lessonData: LmsLessonData | null;
  lessonLoading: boolean;
  manifest: UiManifest | null;
  mode: DuiMode;
  previewManifest: UiManifest | null;
  prompt: string;
  sidebarCollapsed: boolean;
  sortedRevisions: UiManifest[];
  sourceText: string;
  statusMessage: string;
  surfaceOptions: UiSurfaceSummary[];
  targetRevision: number | null;
}

interface StudioControllerActions {
  closeGeneratorEditor: () => void;
  closeSourceEditor: () => void;
  handleCommit: () => Promise<void>;
  handleGenerate: () => Promise<void>;
  handleParseSource: () => Promise<void>;
  handleRevert: () => Promise<void>;
  openDashboard: () => void;
  openLesson: (lessonId: string) => void;
  refreshCurrentSurface: () => Promise<void>;
  setMode: Dispatch<SetStateAction<DuiMode>>;
  setPrompt: Dispatch<SetStateAction<string>>;
  setSourceText: Dispatch<SetStateAction<string>>;
  setStarterSource: () => void;
  setTargetRevision: Dispatch<SetStateAction<number | null>>;
  switchSurface: (surfaceId: string) => void;
  toggleGeneratorEditor: () => void;
  toggleMenu: () => void;
  toggleSidebar: () => void;
  toggleSourceEditor: () => void;
}

interface StudioController {
  actions: StudioControllerActions;
  state: StudioControllerState;
}

export function useStudioController(): StudioController {
  const [currentPath, setCurrentPath] = useState<string>(() => normalizePathname(window.location.pathname));
  const [mode, setMode] = useState<DuiMode>('extended');
  const [prompt, setPrompt] = useState('Сделай интерфейс более контрастным, увеличь главный контент и добавь быстрые действия');
  const [sourceText, setSourceText] = useState(starterDslSource(DASHBOARD_SURFACE_ID));

  const [manifest, setManifest] = useState<UiManifest | null>(null);
  const [previewManifest, setPreviewManifest] = useState<UiManifest | null>(null);
  const [manifestRevisions, setManifestRevisions] = useState<UiManifest[]>([]);
  const [currentDsl, setCurrentDsl] = useState<DuiDslDocument | null>(null);
  const [draftDsl, setDraftDsl] = useState<DuiDslDocument | null>(null);
  const [availableSurfaces, setAvailableSurfaces] = useState<UiSurfaceSummary[]>(FALLBACK_SURFACES);

  const [dashboard, setDashboard] = useState<LmsDashboardData>(FALLBACK_DASHBOARD);
  const [lessonData, setLessonData] = useState<LmsLessonData | null>(null);
  const [lessonLoading, setLessonLoading] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const [busyAction, setBusyAction] = useState<BusyAction>(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const [isMenuOpen, setMenuOpen] = useState(false);
  const [isGeneratorOpen, setGeneratorOpen] = useState(false);
  const [isSourceEditorOpen, setSourceEditorOpen] = useState(false);
  const [targetRevision, setTargetRevision] = useState<number | null>(null);

  const activeManifest = previewManifest ?? manifest;
  const currentRoute = useMemo(() => resolveRoute(currentPath), [currentPath]);
  const activeSurfaceId = useMemo(() => surfaceForRoute(currentRoute), [currentRoute]);
  const currentRevision = manifest?.revision ?? '—';
  const dslRevision = currentDsl?.meta.revision ?? '—';

  const sortedRevisions = useMemo(
    () => [...manifestRevisions].sort((left, right) => right.revision - left.revision),
    [manifestRevisions],
  );
  const surfaceOptions = useMemo(() => {
    const raw = availableSurfaces.length > 0 ? availableSurfaces : FALLBACK_SURFACES;
    return [...raw].sort((left, right) => left.surface_id.localeCompare(right.surface_id));
  }, [availableSurfaces]);

  useEffect(() => {
    resetDraftState();
    setTargetRevision(null);
    void refreshAll(activeSurfaceId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSurfaceId]);

  useEffect(() => {
    const onPopState = (): void => {
      setCurrentPath(normalizePathname(window.location.pathname));
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  useEffect(() => {
    if (currentRoute.kind !== 'lesson') {
      setLessonData(null);
      setLessonLoading(false);
      return;
    }

    let cancelled = false;
    const fallback = FALLBACK_LESSONS[currentRoute.lessonId] ?? null;
    setLessonData(fallback);
    setLessonLoading(true);

    void fetchLessonData(currentRoute.lessonId)
      .then((payload) => {
        if (!cancelled) {
          setLessonData(payload);
        }
      })
      .catch(() => {
        if (!cancelled && !fallback) {
          setLessonData(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLessonLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [currentRoute]);

  async function refreshAll(surfaceId: string): Promise<void> {
    setBusyAction('refresh');
    setErrorMessage('');

    try {
      const [manifestResult, dslResult, revisionsResult, dashboardResult, surfacesResult] = await Promise.allSettled([
        fetchCurrentManifest(surfaceId),
        fetchCurrentDsl(surfaceId),
        fetchManifestRevisions(surfaceId),
        fetchDashboardData(),
        fetchSurfaces(),
      ]);

      if (manifestResult.status === 'fulfilled') {
        setManifest(manifestResult.value);
      }

      if (dslResult.status === 'fulfilled') {
        setCurrentDsl(dslResult.value);
      }

      if (revisionsResult.status === 'fulfilled') {
        applyRevisionData(revisionsResult.value, true);
      }

      if (dashboardResult.status === 'fulfilled') {
        setDashboard(dashboardResult.value);
      }

      if (surfacesResult.status === 'fulfilled' && surfacesResult.value.length > 0) {
        setAvailableSurfaces(surfacesResult.value);
      }

      const failures = [manifestResult, dslResult, revisionsResult, dashboardResult, surfacesResult].filter(
        (result) => result.status === 'rejected',
      );

      if (failures.length > 0) {
        setErrorMessage('Бэкенд частично недоступен. Включён локальный резервный режим для предпросмотра.');
      } else {
        setStatusMessage('Поверхность синхронизирована');
      }
    } catch (error) {
      setErrorMessage(describeError(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function refreshManifestAndDsl(surfaceId: string): Promise<void> {
    const [manifestValue, dslValue, revisionsValue] = await Promise.all([
      fetchCurrentManifest(surfaceId),
      fetchCurrentDsl(surfaceId),
      fetchManifestRevisions(surfaceId),
    ]);

    setManifest(manifestValue);
    setCurrentDsl(dslValue);
    applyRevisionData(revisionsValue, false);
  }

  function resetDraftState(): void {
    setDraftDsl(null);
    setPreviewManifest(null);
  }

  function applyRevisionData(revisions: UiManifest[], preserveSelectedTarget: boolean): void {
    const defaultTargetRevision = resolveDefaultTargetRevision(revisions);
    setManifestRevisions(revisions);
    setTargetRevision((current) => (preserveSelectedTarget && current !== null ? current : defaultTargetRevision));
  }

  async function handleGenerate(): Promise<void> {
    if (!prompt.trim()) {
      setErrorMessage('Введите запрос для генерации.');
      setMenuOpen(false);
      return;
    }

    setBusyAction('generate');
    setErrorMessage('');
    setStatusMessage('');

    try {
      const response = await generateDslIntent({
        prompt: prompt.trim(),
        mode,
        surfaceId: activeSurfaceId,
        sessionId: SESSION_ID,
      });

      setDraftDsl(response.document);
      setPreviewManifest(response.preview_manifest);
      setStatusMessage(
        response.validation_result.valid
          ? `Черновик сгенерирован. Предупреждений: ${response.warnings.length}`
          : 'Черновик сгенерирован, но есть ошибки валидации',
      );
    } catch (error) {
      setErrorMessage(describeError(error));
    } finally {
      setBusyAction(null);
      setMenuOpen(false);
    }
  }

  async function handleParseSource(): Promise<void> {
    if (!sourceText.trim()) {
      setErrorMessage('Вставьте DUI-исходник перед разбором.');
      return;
    }

    setBusyAction('parse');
    setErrorMessage('');
    setStatusMessage('');

    try {
      const response = await parseDslSource({ source: sourceText });
      setDraftDsl(response.document);
      setPreviewManifest(response.compiled_manifest);

      const parsedSurfaceId = response.document.surface.id.trim();
      if (parsedSurfaceId && parsedSurfaceId !== activeSurfaceId) {
        switchSurface(parsedSurfaceId);
      }

      if (response.validation_result.valid) {
        if (parsedSurfaceId && parsedSurfaceId !== activeSurfaceId) {
          setStatusMessage(`Исходник разобран. Активная поверхность переключена на ${parsedSurfaceId}.`);
        } else {
          setStatusMessage('Исходник разобран и готов к коммиту.');
        }
      } else {
        setErrorMessage('Исходник разобран, но есть ошибки валидации. Исправьте перед коммитом.');
      }
    } catch (error) {
      setErrorMessage(describeError(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleCommit(): Promise<void> {
    const documentToCommit = draftDsl ?? currentDsl;

    if (!documentToCommit) {
      setErrorMessage('Нет документа для коммита. Сначала сгенерируйте или вставьте исходник.');
      setMenuOpen(false);
      return;
    }

    setBusyAction('commit');
    setErrorMessage('');
    setStatusMessage('');

    try {
      const response = await commitDslDocument({
        document: documentToCommit,
        surfaceId: activeSurfaceId,
        expectedManifestRevision: manifest?.revision,
        expectedDslRevision: currentDsl?.meta.revision,
      });

      setManifest(response.manifest);
      setCurrentDsl(response.document);
      resetDraftState();
      setStatusMessage(`Коммит выполнен. Ревизия манифеста: ${response.manifest.revision}`);

      await refreshManifestAndDsl(activeSurfaceId);
    } catch (error) {
      setErrorMessage(describeError(error));
    } finally {
      setBusyAction(null);
      setMenuOpen(false);
    }
  }

  async function handleRevert(): Promise<void> {
    if (targetRevision === null) {
      setErrorMessage('Нет целевой ревизии для отката.');
      setMenuOpen(false);
      return;
    }

    setBusyAction('revert');
    setErrorMessage('');
    setStatusMessage('');

    try {
      const response = await revertManifest({ targetRevision, surfaceId: activeSurfaceId });
      setManifest(response.manifest);
      resetDraftState();
      setStatusMessage(`Откат выполнен до ревизии ${targetRevision}`);
      await refreshManifestAndDsl(activeSurfaceId);
    } catch (error) {
      setErrorMessage(describeError(error));
    } finally {
      setBusyAction(null);
      setMenuOpen(false);
    }
  }

  function navigateTo(path: string): void {
    const target = normalizePathname(path);
    if (target === currentPath) {
      return;
    }
    window.history.pushState({}, '', target);
    setCurrentPath(target);
    setMenuOpen(false);
  }

  function openLesson(lessonId: string): void {
    navigateTo(`/lesson/${encodeURIComponent(lessonId)}`);
  }

  function openDashboard(): void {
    navigateTo('/dashboard');
  }

  function switchSurface(surfaceId: string): void {
    const normalized = surfaceId.trim();
    if (!normalized || normalized === activeSurfaceId) {
      return;
    }

    const lessonId = currentRoute.kind === 'lesson' ? currentRoute.lessonId : dashboard.next_lesson_id || DEFAULT_LESSON_ID;
    navigateTo(routeForSurface(normalized, lessonId));
  }

  function toggleGeneratorEditor(): void {
    setSourceEditorOpen(false);
    setGeneratorOpen((previous) => !previous);
    setMenuOpen(false);
  }

  function toggleSourceEditor(): void {
    setGeneratorOpen(false);
    setSourceEditorOpen((previous) => !previous);
    setMenuOpen(false);
  }

  function setStarterSource(): void {
    setSourceText(starterDslSource(activeSurfaceId));
  }

  function closeSourceEditor(): void {
    setSourceEditorOpen(false);
  }

  function closeGeneratorEditor(): void {
    setGeneratorOpen(false);
  }

  function toggleMenu(): void {
    setMenuOpen((current) => !current);
  }

  function toggleSidebar(): void {
    setSidebarCollapsed((current) => !current);
  }

  async function refreshCurrentSurface(): Promise<void> {
    await refreshAll(activeSurfaceId);
  }

  return {
    actions: {
      closeGeneratorEditor,
      closeSourceEditor,
      handleCommit,
      handleGenerate,
      handleParseSource,
      handleRevert,
      openDashboard,
      openLesson,
      refreshCurrentSurface,
      setMode,
      setPrompt,
      setSourceText,
      setStarterSource,
      setTargetRevision,
      switchSurface,
      toggleGeneratorEditor,
      toggleMenu,
      toggleSidebar,
      toggleSourceEditor,
    },
    state: {
      activeManifest,
      activeSurfaceId,
      busyAction,
      currentDsl,
      currentRevision,
      currentRoute,
      dashboard,
      draftDsl,
      dslRevision,
      errorMessage,
      isGeneratorOpen,
      isMenuOpen,
      isSourceEditorOpen,
      lessonData,
      lessonLoading,
      manifest,
      mode,
      previewManifest,
      prompt,
      sidebarCollapsed,
      sortedRevisions,
      sourceText,
      statusMessage,
      surfaceOptions,
      targetRevision,
    },
  };
}
