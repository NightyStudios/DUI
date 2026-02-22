import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';

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
  MODE_LABELS,
  MODE_OPTIONS,
  SESSION_ID,
} from './studioConfig';
import { LessonPage, ManifestCanvas } from './studioRenderer';
import {
  describeError,
  getBusyActionLabel,
  normalizePathname,
  resolveRoute,
  routeForSurface,
  surfaceForRoute,
  type BusyAction,
} from './studioRouting';
import { resolveStudioTheme } from './theme';
import type {
  DuiDslDocument,
  DuiMode,
  LmsDashboardData,
  LmsLessonData,
  UiManifest,
  UiSurfaceSummary,
} from './types';

export default function App(): JSX.Element {
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
  const theme = useMemo(() => resolveStudioTheme(activeManifest), [activeManifest]);

  const appThemeStyle = {
    '--dui-bg': theme.bg,
    '--dui-bg-accent': theme.backgroundAccent,
    '--dui-surface': theme.surface,
    '--dui-surface-muted': theme.surfaceMuted,
    '--dui-border': theme.border,
    '--dui-text': theme.text,
    '--dui-muted': theme.muted,
    '--dui-accent': theme.accent,
    '--dui-accent-soft': theme.accentSoft,
    '--dui-success': theme.success,
    '--dui-warning': theme.warning,
    '--dui-danger': theme.danger,
    '--dui-shadow-soft': theme.shadow,
    '--dui-radius-lg': theme.radiusLg,
    '--dui-radius-md': theme.radiusMd,
    '--dui-radius-sm': theme.radiusSm,
  } as CSSProperties;

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
    setDraftDsl(null);
    setPreviewManifest(null);
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
        setManifestRevisions(revisionsResult.value);

        if (targetRevision === null && revisionsResult.value.length > 1) {
          setTargetRevision(revisionsResult.value[revisionsResult.value.length - 2]?.revision ?? null);
        }
      }

      if (dashboardResult.status === 'fulfilled') {
        setDashboard(dashboardResult.value);
      }

      if (surfacesResult.status === 'fulfilled') {
        if (surfacesResult.value.length > 0) {
          setAvailableSurfaces(surfacesResult.value);
        }
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
    setManifestRevisions(revisionsValue);

    if (revisionsValue.length > 1) {
      setTargetRevision(revisionsValue[revisionsValue.length - 2]?.revision ?? null);
    }
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
      setDraftDsl(null);
      setPreviewManifest(null);
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
      setPreviewManifest(null);
      setDraftDsl(null);
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

  function handleToggleGeneratorEditor(): void {
    setSourceEditorOpen(false);
    setGeneratorOpen((previous) => !previous);
    setMenuOpen(false);
  }

  function handleToggleSourceEditor(): void {
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

  return (
    <div className="studio-root" style={appThemeStyle}>
      <header className="studio-topbar">
        <div>
          <p className="eyebrow">DUI Студия</p>
          <h1>Конструктор адаптивного интерфейса</h1>
          <p className="subtle">
            поверхность: <code>{activeSurfaceId}</code> | ревизия манифеста: <strong>{currentRevision}</strong> | ревизия DSL:{' '}
            <strong>{dslRevision}</strong>
          </p>
        </div>

        <div className="topbar-actions">
          <label className="surface-picker" htmlFor="surface-select">
            <span>Surface</span>
            <select
              id="surface-select"
              className="surface-select"
              value={activeSurfaceId}
              onChange={(event) => switchSurface(event.target.value)}
              disabled={busyAction !== null}
            >
              {surfaceOptions.map((surface) => (
                <option key={surface.surface_id} value={surface.surface_id}>
                  {surface.surface_id}
                </option>
              ))}
            </select>
          </label>

          {currentRoute.kind === 'lesson' ? (
            <button
              type="button"
              className="secondary-button"
              onClick={openDashboard}
              disabled={busyAction !== null}
            >
              К панели
            </button>
          ) : null}

          <button
            type="button"
            className="secondary-button"
            onClick={() => void refreshAll(activeSurfaceId)}
            disabled={busyAction !== null}
          >
            Обновить
          </button>

          <button
            type="button"
            className="menu-button"
            onClick={() => setMenuOpen((current) => !current)}
            aria-expanded={isMenuOpen}
          >
            ☰ Действия DSL
          </button>

          {isMenuOpen ? (
            <div className="menu-popover">
              <button type="button" onClick={handleToggleGeneratorEditor} disabled={busyAction !== null}>
                Открыть генератор
              </button>
              <button type="button" onClick={() => void handleCommit()} disabled={busyAction !== null}>
                Закоммитить
              </button>
              <button type="button" onClick={() => void handleRevert()} disabled={busyAction !== null}>
                Откатить
              </button>
              <button type="button" onClick={handleToggleSourceEditor} disabled={busyAction !== null}>
                Вставить исходник
              </button>
            </div>
          ) : null}
        </div>
      </header>

      <main className="studio-main">
        {statusMessage ? <p className="status-message global-message">{statusMessage}</p> : null}
        {errorMessage ? <p className="error-message global-message">{errorMessage}</p> : null}

        {currentRoute.kind === 'lesson' ? (
          <LessonPage
            lesson={lessonData}
            manifest={activeManifest}
            loading={lessonLoading}
            onBack={openDashboard}
            onOpenLesson={openLesson}
          />
        ) : (
          <section className="panel preview-panel">
            <header className="panel-header">
              <h2>Предпросмотр поверхности</h2>
              <div className="preview-actions">
                <span className="status-dot">{previewManifest ? 'Черновой предпросмотр' : 'Текущий манифест'}</span>
                <span className="status-dot">{busyAction ? `В работе: ${getBusyActionLabel(busyAction)}` : 'Готово'}</span>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setSidebarCollapsed((current) => !current)}
                >
                  {sidebarCollapsed ? 'Показать сайдбар' : 'Скрыть сайдбар'}
                </button>
              </div>
            </header>

            {activeManifest ? (
              <ManifestCanvas
                manifest={activeManifest}
                dashboard={dashboard}
                sidebarCollapsed={sidebarCollapsed}
                onOpenLesson={openLesson}
              />
            ) : (
              <div className="empty-state">
                <p>Манифест не загружен. Нажмите «Обновить».</p>
              </div>
            )}
          </section>
        )}
      </main>

      {isGeneratorOpen ? (
        <div className="generator-floating-backdrop" onClick={closeGeneratorEditor}>
          <aside className="generator-floating-panel" onClick={(event) => event.stopPropagation()}>
            <div className="source-editor-header">
              <h3>Генератор DSL</h3>
              <div className="source-floating-actions">
                <button type="button" className="link-button" onClick={closeGeneratorEditor}>
                  Закрыть
                </button>
              </div>
            </div>

            <label className="field-label" htmlFor="intent-prompt">
              Запрос (интент)
            </label>
            <textarea
              id="intent-prompt"
              className="prompt-textarea generator-textarea"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              rows={6}
              placeholder="Опишите изменение интерфейса..."
            />

            <div className="control-grid">
              <label className="field-label" htmlFor="mode-select">
                Режим
              </label>
              <select id="mode-select" value={mode} onChange={(event) => setMode(event.target.value as DuiMode)}>
                {MODE_OPTIONS.map((item) => (
                  <option key={item} value={item}>
                    {MODE_LABELS[item]}
                  </option>
                ))}
              </select>

              <label className="field-label" htmlFor="revert-select">
                Цель отката
              </label>
              <select
                id="revert-select"
                value={targetRevision ?? ''}
                onChange={(event) => setTargetRevision(Number(event.target.value))}
                disabled={sortedRevisions.length === 0}
              >
                {sortedRevisions.length === 0 ? <option value="">нет</option> : null}
                {sortedRevisions.map((revision) => (
                  <option key={revision.manifest_id} value={revision.revision}>
                    ревизия {revision.revision}
                  </option>
                ))}
              </select>
            </div>

            <div className="source-actions generator-actions">
              <button type="button" className="secondary-button" onClick={() => void handleGenerate()} disabled={busyAction !== null}>
                Сгенерировать
              </button>
              <button type="button" className="secondary-button" onClick={() => void handleCommit()} disabled={busyAction !== null}>
                Закоммитить
              </button>
              <button type="button" className="secondary-button" onClick={() => void handleRevert()} disabled={busyAction !== null}>
                Откатить
              </button>
            </div>
          </aside>
        </div>
      ) : null}

      {isSourceEditorOpen ? (
        <div className="source-floating-backdrop" onClick={closeSourceEditor}>
          <aside className="source-floating-panel" onClick={(event) => event.stopPropagation()}>
            <div className="source-editor-header">
              <h3>DUI-исходник</h3>
              <div className="source-floating-actions">
                <button type="button" className="link-button" onClick={setStarterSource}>
                  Подставить шаблон
                </button>
                <button type="button" className="link-button" onClick={closeSourceEditor}>
                  Закрыть
                </button>
              </div>
            </div>
            <textarea
              className="source-textarea source-floating-textarea"
              value={sourceText}
              onChange={(event) => setSourceText(event.target.value)}
              rows={20}
              placeholder="Вставьте DUI-исходник..."
            />
            <div className="source-actions">
              <button type="button" className="secondary-button" onClick={() => void handleParseSource()} disabled={busyAction !== null}>
                Разобрать исходник
              </button>
            </div>
          </aside>
        </div>
      ) : null}
    </div>
  );
}
