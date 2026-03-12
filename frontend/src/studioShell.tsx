import type { JSX } from 'react';

import { MODE_LABELS, MODE_OPTIONS } from './studioConfig';
import { ManifestCanvas } from './studioRenderer';
import { getBusyActionLabel, type AppRoute, type BusyAction } from './studioRouting';
import type { DuiMode, LmsDashboardData, UiManifest, UiSurfaceSummary } from './types';

interface StudioTopbarProps {
  activeSurfaceId: string;
  busyAction: BusyAction;
  currentRevision: number | string;
  currentRoute: AppRoute;
  dslRevision: number | string;
  isMenuOpen: boolean;
  onCommit: () => void;
  onOpenDashboard: () => void;
  onRefresh: () => void;
  onRevert: () => void;
  onSwitchSurface: (surfaceId: string) => void;
  onToggleGenerator: () => void;
  onToggleMenu: () => void;
  onToggleSourceEditor: () => void;
  surfaceOptions: UiSurfaceSummary[];
}

export function StudioTopbar(props: StudioTopbarProps): JSX.Element {
  const {
    activeSurfaceId,
    busyAction,
    currentRevision,
    currentRoute,
    dslRevision,
    isMenuOpen,
    onCommit,
    onOpenDashboard,
    onRefresh,
    onRevert,
    onSwitchSurface,
    onToggleGenerator,
    onToggleMenu,
    onToggleSourceEditor,
    surfaceOptions,
  } = props;

  return (
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
            onChange={(event) => onSwitchSurface(event.target.value)}
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
          <button type="button" className="secondary-button" onClick={onOpenDashboard} disabled={busyAction !== null}>
            К панели
          </button>
        ) : null}

        <button type="button" className="secondary-button" onClick={onRefresh} disabled={busyAction !== null}>
          Обновить
        </button>

        <button type="button" className="menu-button" onClick={onToggleMenu} aria-expanded={isMenuOpen}>
          ☰ Действия DSL
        </button>

        {isMenuOpen ? (
          <div className="menu-popover">
            <button type="button" onClick={onToggleGenerator} disabled={busyAction !== null}>
              Открыть генератор
            </button>
            <button type="button" onClick={onCommit} disabled={busyAction !== null}>
              Закоммитить
            </button>
            <button type="button" onClick={onRevert} disabled={busyAction !== null}>
              Откатить
            </button>
            <button type="button" onClick={onToggleSourceEditor} disabled={busyAction !== null}>
              Вставить исходник
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}

interface PreviewPanelProps {
  activeManifest: UiManifest | null;
  busyAction: BusyAction;
  dashboard: LmsDashboardData;
  onOpenLesson: (lessonId: string) => void;
  onToggleSidebar: () => void;
  previewManifest: UiManifest | null;
  sidebarCollapsed: boolean;
}

export function PreviewPanel(props: PreviewPanelProps): JSX.Element {
  const { activeManifest, busyAction, dashboard, onOpenLesson, onToggleSidebar, previewManifest, sidebarCollapsed } = props;

  return (
    <section className="panel preview-panel">
      <header className="panel-header">
        <h2>Предпросмотр поверхности</h2>
        <div className="preview-actions">
          <span className="status-dot">{previewManifest ? 'Черновой предпросмотр' : 'Текущий манифест'}</span>
          <span className="status-dot">{busyAction ? `В работе: ${getBusyActionLabel(busyAction)}` : 'Готово'}</span>
          <button type="button" className="secondary-button" onClick={onToggleSidebar}>
            {sidebarCollapsed ? 'Показать сайдбар' : 'Скрыть сайдбар'}
          </button>
        </div>
      </header>

      {activeManifest ? (
        <ManifestCanvas
          manifest={activeManifest}
          dashboard={dashboard}
          sidebarCollapsed={sidebarCollapsed}
          onOpenLesson={onOpenLesson}
        />
      ) : (
        <div className="empty-state">
          <p>Манифест не загружен. Нажмите «Обновить».</p>
        </div>
      )}
    </section>
  );
}

interface GeneratorOverlayProps {
  busyAction: BusyAction;
  isOpen: boolean;
  mode: DuiMode;
  onClose: () => void;
  onCommit: () => void;
  onGenerate: () => void;
  onModeChange: (mode: DuiMode) => void;
  onPromptChange: (value: string) => void;
  onRevert: () => void;
  onTargetRevisionChange: (revision: number | null) => void;
  prompt: string;
  sortedRevisions: UiManifest[];
  targetRevision: number | null;
}

export function GeneratorOverlay(props: GeneratorOverlayProps): JSX.Element | null {
  const {
    busyAction,
    isOpen,
    mode,
    onClose,
    onCommit,
    onGenerate,
    onModeChange,
    onPromptChange,
    onRevert,
    onTargetRevisionChange,
    prompt,
    sortedRevisions,
    targetRevision,
  } = props;

  if (!isOpen) {
    return null;
  }

  return (
    <div className="generator-floating-backdrop" onClick={onClose}>
      <aside className="generator-floating-panel" onClick={(event) => event.stopPropagation()}>
        <div className="source-editor-header">
          <h3>Генератор DSL</h3>
          <div className="source-floating-actions">
            <button type="button" className="link-button" onClick={onClose}>
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
          onChange={(event) => onPromptChange(event.target.value)}
          rows={6}
          placeholder="Опишите изменение интерфейса..."
        />

        <div className="control-grid">
          <label className="field-label" htmlFor="mode-select">
            Режим
          </label>
          <select id="mode-select" value={mode} onChange={(event) => onModeChange(event.target.value as DuiMode)}>
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
            onChange={(event) => onTargetRevisionChange(event.target.value ? Number(event.target.value) : null)}
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
          <button type="button" className="secondary-button" onClick={onGenerate} disabled={busyAction !== null}>
            Сгенерировать
          </button>
          <button type="button" className="secondary-button" onClick={onCommit} disabled={busyAction !== null}>
            Закоммитить
          </button>
          <button type="button" className="secondary-button" onClick={onRevert} disabled={busyAction !== null}>
            Откатить
          </button>
        </div>
      </aside>
    </div>
  );
}

interface SourceEditorOverlayProps {
  busyAction: BusyAction;
  isOpen: boolean;
  onClose: () => void;
  onParse: () => void;
  onSetStarterSource: () => void;
  onSourceTextChange: (value: string) => void;
  sourceText: string;
}

export function SourceEditorOverlay(props: SourceEditorOverlayProps): JSX.Element | null {
  const { busyAction, isOpen, onClose, onParse, onSetStarterSource, onSourceTextChange, sourceText } = props;

  if (!isOpen) {
    return null;
  }

  return (
    <div className="source-floating-backdrop" onClick={onClose}>
      <aside className="source-floating-panel" onClick={(event) => event.stopPropagation()}>
        <div className="source-editor-header">
          <h3>DUI-исходник</h3>
          <div className="source-floating-actions">
            <button type="button" className="link-button" onClick={onSetStarterSource}>
              Подставить шаблон
            </button>
            <button type="button" className="link-button" onClick={onClose}>
              Закрыть
            </button>
          </div>
        </div>
        <textarea
          className="source-textarea source-floating-textarea"
          value={sourceText}
          onChange={(event) => onSourceTextChange(event.target.value)}
          rows={20}
          placeholder="Вставьте DUI-исходник..."
        />
        <div className="source-actions">
          <button type="button" className="secondary-button" onClick={onParse} disabled={busyAction !== null}>
            Разобрать исходник
          </button>
        </div>
      </aside>
    </div>
  );
}
