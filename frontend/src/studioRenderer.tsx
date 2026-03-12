import { useMemo } from 'react';
import type { CSSProperties, ReactNode } from 'react';

import {
  CAPABILITY_TITLES,
  KIND_LABELS,
  SECTION_TITLE_LABELS,
  ZONE_LABELS,
} from './studioConfig';
import { MathFormulaList } from './mathFormulaList';
import type {
  LmsDashboardData,
  LmsLessonData,
  SectionConfig,
  UiManifest,
  WidgetConfig,
  Zone,
} from './types';

type JsonRecord = Record<string, unknown>;

interface WidgetStyleBundle {
  shell: CSSProperties;
  shape: CSSProperties;
  content: CSSProperties;
}

function asRecord(value: unknown): JsonRecord {
  return value && typeof value === 'object' ? (value as JsonRecord) : {};
}

function readString(source: JsonRecord, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === 'string' && value.trim().length > 0) {
      return value.trim();
    }
  }
  return undefined;
}

function readNumber(source: JsonRecord, keys: string[]): number | undefined {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === 'string' && value.trim().length > 0) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }
  return undefined;
}

function toCssSize(value: unknown): string | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return `${value}px`;
  }
  if (typeof value === 'string' && value.trim().length > 0) {
    return value.trim();
  }
  return undefined;
}

function shapeToClipPath(shapeRaw: unknown): string | undefined {
  if (typeof shapeRaw !== 'string') {
    return undefined;
  }
  const shape = shapeRaw.trim().toLowerCase();
  if (shape === 'triangle') {
    return 'polygon(50% 3%, 100% 100%, 0 100%)';
  }
  if (shape === 'diamond') {
    return 'polygon(50% 0, 100% 50%, 50% 100%, 0 50%)';
  }
  if (shape === 'hexagon') {
    return 'polygon(24% 0, 76% 0, 100% 50%, 76% 100%, 24% 100%, 0 50%)';
  }
  if (shape === 'parallelogram') {
    return 'polygon(12% 0, 100% 0, 88% 100%, 0 100%)';
  }
  if (shape === 'pill') {
    return 'inset(0 round 999px)';
  }
  return undefined;
}

function formatDueDate(rawDate: string): string {
  const parsed = new Date(rawDate);
  if (Number.isNaN(parsed.getTime())) {
    return rawDate;
  }
  return parsed.toLocaleDateString('ru-RU');
}

function getWidgetCapability(widget: WidgetConfig): string {
  if (typeof widget.capability_id === 'string' && widget.capability_id.length > 0) {
    return widget.capability_id;
  }
  const props = asRecord(widget.props);
  return typeof props.capability_id === 'string' ? props.capability_id : 'ui.generic';
}

function getWidgetDisplayTitle(widget: WidgetConfig): string {
  const capability = getWidgetCapability(widget);
  if (CAPABILITY_TITLES[capability]) {
    return CAPABILITY_TITLES[capability];
  }
  if (typeof widget.title === 'string' && widget.title.trim().length > 0) {
    return widget.title;
  }
  return 'Виджет';
}

function getWidgetKindLabel(kind: string): string {
  return KIND_LABELS[kind] ?? kind.toUpperCase();
}

function getSectionDisplayTitle(section: SectionConfig): string {
  if (SECTION_TITLE_LABELS[section.id]) {
    return SECTION_TITLE_LABELS[section.id];
  }
  if (SECTION_TITLE_LABELS[section.title]) {
    return SECTION_TITLE_LABELS[section.title];
  }
  return section.title;
}

function getWidgetStyle(widget: WidgetConfig): WidgetStyleBundle {
  const style = asRecord(widget.style);
  const layout = asRecord(widget.layout);

  const cardBackground =
    readString(style, ['background', 'background_color']) ?? readString(layout, ['background']) ?? 'var(--dui-surface-muted)';
  const cardColor = readString(style, ['color', 'text']) ?? 'var(--dui-text)';
  const cardPadding =
    toCssSize(layout.padding ?? layout.content_padding ?? style.padding ?? style.content_padding) ?? '20px';
  const radius = toCssSize(style.border_radius ?? style.radius ?? layout.border_radius ?? layout.radius) ?? '16px';
  const borderColor = readString(style, ['border_color']) ?? 'var(--dui-border)';
  const borderWidth = toCssSize(style.border_width) ?? '1px';
  const borderStyle = readString(style, ['border_style']) ?? 'solid';
  const shadow = readString(style, ['shadow']) ?? 'var(--dui-shadow-soft)';
  const rotation = readNumber(style, ['rotate', 'rotation']);

  const shell: CSSProperties = {
    position: 'relative',
    borderRadius: radius,
    border: `${borderWidth} ${borderStyle} ${borderColor}`,
    boxShadow: shadow,
    overflow: 'hidden',
    minHeight: toCssSize(layout.min_height ?? layout.minHeight ?? style.min_height ?? style.minHeight) ?? '160px',
    width: toCssSize(layout.width ?? style.width),
    height: toCssSize(layout.height ?? style.height),
    maxWidth: toCssSize(layout.max_width ?? layout.maxWidth ?? style.max_width ?? style.maxWidth),
    maxHeight: toCssSize(layout.max_height ?? layout.maxHeight ?? style.max_height ?? style.maxHeight),
    minWidth: toCssSize(layout.min_width ?? layout.minWidth ?? style.min_width ?? style.minWidth),
  };

  const span = readNumber(layout, ['span', 'grid_span', 'col_span', 'column_span']);
  if (typeof span === 'number' && span > 0) {
    shell.gridColumn = `span ${Math.min(12, Math.max(1, Math.floor(span)))}`;
  }

  const clipPath = shapeToClipPath(style.shape ?? layout.shape);

  const shape: CSSProperties = {
    position: 'absolute',
    inset: 0,
    background: cardBackground,
    clipPath,
    transform: typeof rotation === 'number' && Number.isFinite(rotation) ? `rotate(${rotation}deg)` : undefined,
    transformOrigin: 'center center',
    pointerEvents: 'none',
  };

  const content: CSSProperties = {
    position: 'relative',
    zIndex: 1,
    color: cardColor,
    padding: cardPadding,
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    height: '100%',
    overflowWrap: 'anywhere',
  };

  return { shell, shape, content };
}

function renderWidgetBody(widget: WidgetConfig, dashboard: LmsDashboardData, onOpenLesson: (lessonId: string) => void): ReactNode {
  const capability = getWidgetCapability(widget);

  if (capability === 'math.progress_overview') {
    const progress = dashboard.learner;
    const completion = Math.max(0, Math.min(100, progress.mastery_percent));
    return (
      <>
        <p className="widget-kpi">{completion}% освоения</p>
        <p className="widget-muted">{progress.track}</p>
        <p className="widget-muted">Серия: {progress.streak_days} дней</p>
        <div className="progress-track">
          <span style={{ width: `${completion}%` }} />
        </div>
        <p className="widget-muted">
          Недельная цель: {progress.lessons_done}/{progress.weekly_goal} уроков
        </p>
        {widget.protected ? <span className="chip chip-locked">Защищено</span> : null}
      </>
    );
  }

  if (capability === 'math.learning_path') {
    return (
      <div className="table-list">
        {dashboard.learning_path.map((lesson) => (
          <div key={lesson.id} className="table-item">
            <div>
              <p className="table-title">{lesson.title}</p>
              <p className="widget-muted">
                {lesson.topic} | {lesson.difficulty} | {lesson.duration_min} мин
              </p>
            </div>
            <button type="button" className="ghost-button" onClick={() => onOpenLesson(lesson.id)}>
              Открыть
            </button>
          </div>
        ))}
      </div>
    );
  }

  if (capability === 'math.practice_queue') {
    return (
      <div className="stack-list">
        {dashboard.practice_queue.map((task) => (
          <article key={task.id} className="stack-item">
            <p className="table-title">{task.title}</p>
            <p className="widget-muted">{task.focus}</p>
            <p className="widget-muted">
              {task.problems} задач | дедлайн {formatDueDate(task.due_date)}
            </p>
          </article>
        ))}
      </div>
    );
  }

  if (capability === 'math.mastery_trend') {
    const points = dashboard.mastery_trend;
    const minValue = Math.min(...points);
    const maxValue = Math.max(...points);
    const range = Math.max(1, maxValue - minValue);

    return (
      <>
        <div className="chart-bars">
          {points.map((point, index) => {
            const normalized = (point - minValue) / range;
            const height = 30 + normalized * 70;
            return <span key={`${point}-${index}`} style={{ height: `${height}%` }} />;
          })}
        </div>
        <p className="widget-muted">Последние {points.length} сессий</p>
      </>
    );
  }

  if (capability === 'math.weak_topics') {
    return (
      <ul className="plain-list">
        {dashboard.weak_topics.map((topic) => (
          <li key={topic}>{topic}</li>
        ))}
      </ul>
    );
  }

  if (capability === 'math.quick_actions') {
    return (
      <div className="quick-action-grid">
        {dashboard.quick_actions.map((action) => (
          <button key={action.id} type="button" className="ghost-button">
            {action.label}
          </button>
        ))}
      </div>
    );
  }

  if (capability === 'math.formulas') {
    return <MathFormulaList formulas={dashboard.formulas} />;
  }

  if (capability === 'math.assignments') {
    return (
      <div className="stack-list">
        {dashboard.assignments.map((assignment) => (
          <article key={assignment.title} className="stack-item">
            <p className="table-title">{assignment.title}</p>
            <p className="widget-muted">Срок: {formatDueDate(assignment.due_date)}</p>
          </article>
        ))}
      </div>
    );
  }

  if (capability === 'math.next_lesson') {
    const nextLesson =
      dashboard.learning_path.find((lesson) => lesson.id === dashboard.next_lesson_id) ?? dashboard.learning_path[0];
    return nextLesson ? (
      <>
        <p className="table-title">{nextLesson.title}</p>
        <p className="widget-muted">
          {nextLesson.topic} | {nextLesson.difficulty} | {nextLesson.duration_min} мин
        </p>
        <button type="button" className="ghost-button" onClick={() => onOpenLesson(nextLesson.id)}>
          Продолжить
        </button>
      </>
    ) : null;
  }

  if (capability === 'math.focus_timer') {
    return (
      <>
        <p className="widget-kpi">25:00</p>
        <p className="widget-muted">Помодоро-таймер концентрации</p>
        <button type="button" className="ghost-button">
          Начать фокус
        </button>
      </>
    );
  }

  return <pre className="props-dump">{JSON.stringify(asRecord(widget.props), null, 2)}</pre>;
}

function WidgetCard(props: { widget: WidgetConfig; dashboard: LmsDashboardData; onOpenLesson: (lessonId: string) => void }): JSX.Element {
  const { widget, dashboard, onOpenLesson } = props;
  const styleBundle = getWidgetStyle(widget);

  return (
    <article className={`widget-card kind-${widget.kind}`} style={styleBundle.shell}>
      <div className="widget-shape" style={styleBundle.shape} />
      <div className="widget-content" style={styleBundle.content}>
        <header className="widget-header">
          <h4>{getWidgetDisplayTitle(widget)}</h4>
          <span>{getWidgetKindLabel(widget.kind)}</span>
        </header>
        <div className="widget-body">{renderWidgetBody(widget, dashboard, onOpenLesson)}</div>
        {widget.template_id ? <p className="widget-meta">Шаблон: {widget.template_id}</p> : null}
      </div>
    </article>
  );
}

function SectionBlock(props: {
  section: SectionConfig;
  widgetsById: Map<string, WidgetConfig>;
  dashboard: LmsDashboardData;
  onOpenLesson: (lessonId: string) => void;
}): JSX.Element {
  const { section, widgetsById, dashboard, onOpenLesson } = props;
  const style = asRecord(section.style);
  const layout = asRecord(section.layout);
  const resolvedWidgets = section.child_widget_ids
    .map((widgetId) => widgetsById.get(widgetId))
    .filter((widget): widget is WidgetConfig => widget !== undefined);

  if (resolvedWidgets.length === 0) {
    return <></>;
  }

  const columns = Math.max(1, Math.min(4, Math.floor(readNumber(layout, ['columns']) ?? 1)));
  const sectionStyle: CSSProperties = {
    background: readString(style, ['background']) ?? 'var(--dui-surface-muted)',
    borderRadius: toCssSize(style.border_radius ?? style.radius) ?? '14px',
    border: `1px solid ${readString(style, ['border_color']) ?? 'var(--dui-border)'}`,
    padding: toCssSize(style.padding ?? layout.padding) ?? '14px',
    boxShadow: readString(style, ['shadow']) ?? 'none',
  };

  const gridStyle = { '--section-columns': `${columns}` } as CSSProperties;

  return (
    <article className="section-block" style={sectionStyle}>
      <header className="section-header">
        <h3>{getSectionDisplayTitle(section)}</h3>
      </header>
      <div className="section-grid" style={gridStyle}>
        {resolvedWidgets.map((widget) => (
          <WidgetCard key={widget.id} widget={widget} dashboard={dashboard} onOpenLesson={onOpenLesson} />
        ))}
      </div>
    </article>
  );
}

function ZoneBlock(props: {
  zone: Zone;
  sections: SectionConfig[];
  orphanWidgets: WidgetConfig[];
  widgetsById: Map<string, WidgetConfig>;
  dashboard: LmsDashboardData;
  onOpenLesson: (lessonId: string) => void;
}): JSX.Element {
  const { zone, sections, orphanWidgets, widgetsById, dashboard, onOpenLesson } = props;
  const visibleSections = sections.filter((section) =>
    section.child_widget_ids.some((widgetId) => widgetsById.has(widgetId)),
  );

  if (visibleSections.length === 0 && orphanWidgets.length === 0) {
    return <></>;
  }

  return (
    <section className={`zone zone-${zone}`}>
      <header className="zone-header">
        <h2>{ZONE_LABELS[zone]}</h2>
      </header>

      {visibleSections.map((section) => (
        <SectionBlock key={section.id} section={section} widgetsById={widgetsById} dashboard={dashboard} onOpenLesson={onOpenLesson} />
      ))}

      {orphanWidgets.length > 0 ? (
        <div className="orphan-grid">
          {orphanWidgets.map((widget) => (
            <WidgetCard key={widget.id} widget={widget} dashboard={dashboard} onOpenLesson={onOpenLesson} />
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function ManifestCanvas(props: {
  manifest: UiManifest;
  dashboard: LmsDashboardData;
  sidebarCollapsed: boolean;
  onOpenLesson: (lessonId: string) => void;
}): JSX.Element {
  const { manifest, dashboard, sidebarCollapsed, onOpenLesson } = props;

  const widgetsById = useMemo(() => new Map(manifest.widgets.map((widget) => [widget.id, widget])), [manifest.widgets]);

  const sectionWidgetIds = useMemo(() => {
    const ids = new Set<string>();
    for (const section of manifest.sections) {
      for (const widgetId of section.child_widget_ids) {
        ids.add(widgetId);
      }
    }
    return ids;
  }, [manifest.sections]);

  const sectionsByZone = useMemo(() => {
    const map: Record<Zone, SectionConfig[]> = {
      header: [],
      content: [],
      sidebar: [],
      footer: [],
    };

    for (const section of manifest.sections) {
      map[section.zone].push(section);
    }

    return map;
  }, [manifest.sections]);

  const orphanWidgetsByZone = useMemo(() => {
    const map: Record<Zone, WidgetConfig[]> = {
      header: [],
      content: [],
      sidebar: [],
      footer: [],
    };

    for (const widget of manifest.widgets) {
      if (!sectionWidgetIds.has(widget.id)) {
        map[widget.zone].push(widget);
      }
    }

    return map;
  }, [manifest.widgets, sectionWidgetIds]);

  const hasSidebarContent = sectionsByZone.sidebar.length > 0 || orphanWidgetsByZone.sidebar.length > 0;
  const showSidebar = hasSidebarContent && !sidebarCollapsed;

  return (
    <div className={`surface-grid ${showSidebar ? '' : 'surface-grid-no-sidebar'}`}>
      <ZoneBlock
        zone="header"
        sections={sectionsByZone.header}
        orphanWidgets={orphanWidgetsByZone.header}
        widgetsById={widgetsById}
        dashboard={dashboard}
        onOpenLesson={onOpenLesson}
      />

      <ZoneBlock
        zone="content"
        sections={sectionsByZone.content}
        orphanWidgets={orphanWidgetsByZone.content}
        widgetsById={widgetsById}
        dashboard={dashboard}
        onOpenLesson={onOpenLesson}
      />

      {showSidebar ? (
        <ZoneBlock
          zone="sidebar"
          sections={sectionsByZone.sidebar}
          orphanWidgets={orphanWidgetsByZone.sidebar}
          widgetsById={widgetsById}
          dashboard={dashboard}
          onOpenLesson={onOpenLesson}
        />
      ) : null}

      <ZoneBlock
        zone="footer"
        sections={sectionsByZone.footer}
        orphanWidgets={orphanWidgetsByZone.footer}
        widgetsById={widgetsById}
        dashboard={dashboard}
        onOpenLesson={onOpenLesson}
      />
    </div>
  );
}

export function LessonPage(props: {
  lesson: LmsLessonData | null;
  manifest: UiManifest | null;
  dashboard: LmsDashboardData;
  loading: boolean;
  onBack: () => void;
  onOpenLesson: (lessonId: string) => void;
}): JSX.Element {
  const { lesson, manifest, dashboard, loading, onBack, onOpenLesson } = props;

  const lessonCapabilities = useMemo(() => {
    if (!manifest || manifest.widgets.length === 0) {
      return null;
    }
    return new Set(
      manifest.widgets
        .map((widget) => widget.capability_id)
        .filter((capability): capability is string => typeof capability === 'string' && capability.trim().length > 0),
    );
  }, [manifest]);

  const showObjectives = !lessonCapabilities || lessonCapabilities.has('math.lesson_objectives');
  const showTheory = !lessonCapabilities || lessonCapabilities.has('math.lesson_theory');
  const showExercises = !lessonCapabilities || lessonCapabilities.has('math.lesson_exercises');
  const showReferenceCards = showObjectives || showTheory;
  const showAnyCards = showObjectives || showTheory || showExercises;
  const hasManifestDrivenLessonContent =
    !!manifest &&
    manifest.widgets.some(
      (widget) => typeof widget.capability_id === 'string' && widget.capability_id.trim().length > 0 && !widget.capability_id.startsWith('math.lesson_'),
    );

  if (loading) {
    return (
      <section className="panel lesson-panel">
        <header className="panel-header">
          <h2>Загрузка урока…</h2>
        </header>
      </section>
    );
  }

  if (!lesson) {
    return (
      <section className="panel lesson-panel">
        <header className="panel-header">
          <h2>Урок не найден</h2>
          <button type="button" className="secondary-button" onClick={onBack}>
            К панели
          </button>
        </header>
      </section>
    );
  }

  return (
    <section className="panel lesson-panel">
      <header className="panel-header lesson-top">
        <div>
          <h2>{lesson.title}</h2>
          <p className="widget-muted">
            {lesson.topic} | {lesson.estimated_min} мин
          </p>
        </div>
        <button type="button" className="secondary-button" onClick={onBack}>
          К панели
        </button>
      </header>

      {hasManifestDrivenLessonContent && manifest ? (
        <ManifestCanvas manifest={manifest} dashboard={dashboard} sidebarCollapsed={false} onOpenLesson={onOpenLesson} />
      ) : showAnyCards ? (
        <div className={`lesson-grid ${showReferenceCards ? '' : 'lesson-grid-single'}`}>
          {showObjectives ? (
            <article className="lesson-card">
              <h3>Цели урока</h3>
              <ul className="plain-list">
                {lesson.objectives.map((objective) => (
                  <li key={objective}>{objective}</li>
                ))}
              </ul>
            </article>
          ) : null}

          {showTheory ? (
            <article className="lesson-card">
              <h3>Ключевая теория</h3>
              <ul className="plain-list">
                {lesson.theory_points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </article>
          ) : null}

          {showExercises ? (
            <article className={`lesson-card ${showReferenceCards ? 'lesson-card-wide' : ''}`}>
              <h3>Упражнения</h3>
              <div className="stack-list">
                {lesson.exercises.map((exercise) => (
                  <article key={exercise.id} className="stack-item">
                    <p className="table-title">{exercise.prompt}</p>
                    <p className="widget-muted">Тип: {exercise.type}</p>
                  </article>
                ))}
              </div>
            </article>
          ) : null}
        </div>
      ) : (
        <div className="empty-state">
          <p>В манифесте нет включённых блоков урока.</p>
        </div>
      )}

      <article className="lesson-links">
        <p className="widget-muted">Другие уроки:</p>
        <div className="quick-action-grid">
          <button type="button" className="ghost-button" onClick={() => onOpenLesson('lesson-linear-equations')}>
            Линейные
          </button>
          <button type="button" className="ghost-button" onClick={() => onOpenLesson('lesson-quadratic-intro')}>
            Квадратичные
          </button>
          <button type="button" className="ghost-button" onClick={() => onOpenLesson('lesson-triangles-core')}>
            Треугольники
          </button>
        </div>
      </article>
    </section>
  );
}
