import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';

import {
  commitDslDocument,
  fetchCurrentManifest,
  fetchCurrentDslDocument,
  fetchDashboardData,
  fetchDslRevisions,
  fetchLesson,
  fetchRevisions,
  parseDslSource,
  requestDslIntent,
  revertRevision,
  validateDslDocument,
} from './api';
import { serializeDuiDslDocument } from './dslText';
import { applyTheme } from './theme';
import type {
  DuiDslDocument,
  DuiDslValidationIssue,
  DuiMode,
  LmsDashboardData,
  LmsLessonData,
  SectionConfig,
  UiManifest,
  WidgetConfig,
  Zone,
} from './types';

const ZONES: Zone[] = ['header', 'sidebar', 'content', 'footer'];

type Page = 'dashboard' | 'lesson';
const SURFACE_ID = 'math_lms.dashboard';
const SESSION_ID = 'demo-session';

function StudyProgressCard({ data }: { data: LmsDashboardData }) {
  const goalPercent = Math.min(100, Math.round((data.learner.lessons_done / data.learner.weekly_goal) * 100));

  return (
    <div className="widget-content">
      <p className="value">{data.learner.mastery_percent}% mastery</p>
      <p className="muted">{data.learner.track}</p>
      <p className="muted">Streak: {data.learner.streak_days} days</p>
      <div className="progress-track" aria-hidden>
        <div className="progress-fill" style={{ width: `${goalPercent}%` }} />
      </div>
      <small>
        Weekly goal: {data.learner.lessons_done}/{data.learner.weekly_goal} lessons
      </small>
    </div>
  );
}

function LearningPathCard({
  data,
  onOpenLesson,
}: {
  data: LmsDashboardData;
  onOpenLesson: (lessonId: string) => void;
}) {
  return (
    <div className="widget-content">
      <ul className="list-reset list-gap">
        {data.learning_path.map((lesson) => (
          <li key={lesson.id} className="item-row">
            <div>
              <strong>{lesson.title}</strong>
              <p className="muted tiny">
                {lesson.topic} | {lesson.difficulty} | {lesson.duration_min} min
              </p>
            </div>
            <button type="button" className="button tonal" onClick={() => onOpenLesson(lesson.id)}>
              Open
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function PracticeQueueCard({ data }: { data: LmsDashboardData }) {
  return (
    <div className="widget-content">
      <ul className="list-reset list-gap">
        {data.practice_queue.map((set) => (
          <li key={set.id}>
            <strong>{set.title}</strong>
            <p className="muted tiny">{set.focus}</p>
            <small>
              {set.problems} problems | due {new Date(set.due_date).toLocaleDateString('ru-RU')}
            </small>
          </li>
        ))}
      </ul>
    </div>
  );
}

function MasteryTrendCard({ data }: { data: LmsDashboardData }) {
  return (
    <div className="widget-content">
      <div className="trend-chart" aria-hidden>
        {data.mastery_trend.map((point, index) => (
          <div key={`${point}-${index}`} className="trend-col" style={{ height: `${Math.max(20, point)}%` }} />
        ))}
      </div>
      <small className="muted">Last 6 sessions</small>
    </div>
  );
}

function renderTemplateContent(widget: WidgetConfig, data: LmsDashboardData, onOpenLesson: (lessonId: string) => void) {
  switch (widget.template_id) {
    case 'weak_topics_list':
      return (
        <div className="widget-content">
          <ul className="list-reset list-gap">
            {data.weak_topics.map((topic) => (
              <li key={topic}>{topic}</li>
            ))}
          </ul>
        </div>
      );

    case 'next_lesson_card':
      return (
        <div className="widget-content">
          <p className="muted">Recommended next step</p>
          <button type="button" className="button" onClick={() => onOpenLesson(data.next_lesson_id)}>
            Open Next Lesson
          </button>
        </div>
      );

    case 'quick_actions':
      return (
        <div className="widget-content action-chips">
          {data.quick_actions.map((action) => (
            <button key={action.id} type="button" className="button outlined">
              {action.label}
            </button>
          ))}
        </div>
      );

    case 'formula_cheatsheet':
      return (
        <div className="widget-content">
          <ul className="list-reset list-gap">
            {data.formulas.map((formula) => (
              <li key={formula} className="mono">
                {formula}
              </li>
            ))}
          </ul>
        </div>
      );

    case 'study_streak_panel':
      return (
        <div className="widget-content">
          <p className="value">{data.learner.streak_days} days</p>
          <p className="muted">Current study streak</p>
        </div>
      );

    case 'assignment_calendar':
      return (
        <div className="widget-content">
          <ul className="list-reset list-gap">
            {data.assignments.map((assignment) => (
              <li key={`${assignment.title}-${assignment.due_date}`}>
                <strong>{assignment.title}</strong>
                <p className="muted tiny">Due {new Date(assignment.due_date).toLocaleDateString('ru-RU')}</p>
              </li>
            ))}
          </ul>
        </div>
      );

    case 'focus_timer':
      return (
        <div className="widget-content">
          <p className="value">25:00</p>
          <p className="muted">Pomodoro focus timer</p>
          <button type="button" className="button tonal">
            Start Focus
          </button>
        </div>
      );

    default:
      return null;
  }
}

function renderCapabilityContent(widget: WidgetConfig, data: LmsDashboardData, onOpenLesson: (lessonId: string) => void) {
  if (widget.capability_id === 'math.progress_overview') {
    return <StudyProgressCard data={data} />;
  }
  if (widget.capability_id === 'math.learning_path') {
    return <LearningPathCard data={data} onOpenLesson={onOpenLesson} />;
  }
  if (widget.capability_id === 'math.practice_queue') {
    return <PracticeQueueCard data={data} />;
  }
  if (widget.capability_id === 'math.mastery_trend') {
    return <MasteryTrendCard data={data} />;
  }

  return <p className="muted tiny">Capability: {widget.capability_id}</p>;
}

function WidgetCard({
  widget,
  dashboard,
  onOpenLesson,
}: {
  widget: WidgetConfig;
  dashboard: LmsDashboardData;
  onOpenLesson: (lessonId: string) => void;
}) {
  const templateContent = renderTemplateContent(widget, dashboard, onOpenLesson);

  return (
    <article className="widget">
      <header className="widget__header">
        <h4>{widget.title}</h4>
        <span>{widget.kind}</span>
      </header>

      {templateContent ?? renderCapabilityContent(widget, dashboard, onOpenLesson)}
      {widget.template_id ? <small className="muted tiny">Template: {widget.template_id}</small> : null}
      {widget.protected ? <small className="badge">Protected</small> : null}
    </article>
  );
}

function SectionBlock({
  section,
  widgets,
  dashboard,
  onOpenLesson,
}: {
  section: SectionConfig;
  widgets: WidgetConfig[];
  dashboard: LmsDashboardData;
  onOpenLesson: (lessonId: string) => void;
}) {
  return (
    <article className="section-block">
      <header>
        <h4>{section.title}</h4>
      </header>
      <div className="section-grid">
        {widgets.map((widget) => (
          <WidgetCard key={widget.id} widget={widget} dashboard={dashboard} onOpenLesson={onOpenLesson} />
        ))}
      </div>
    </article>
  );
}

function DashboardView({
  manifest,
  dashboard,
  onOpenLesson,
}: {
  manifest: UiManifest;
  dashboard: LmsDashboardData;
  onOpenLesson: (lessonId: string) => void;
}) {
  const maxColumnsRaw = manifest.layout_constraints.max_columns;
  const maxColumns = typeof maxColumnsRaw === 'number' ? Math.max(1, Math.min(4, maxColumnsRaw)) : 2;
  const style = { '--zone-columns': String(maxColumns) } as CSSProperties;

  return (
    <div className="layout-grid" style={style}>
      {ZONES.map((zone) => {
        const widgets = manifest.widgets.filter((widget) => widget.zone === zone);
        const sections = manifest.sections.filter((section) => section.zone === zone);
        const widgetMap = new Map(widgets.map((widget) => [widget.id, widget]));
        const usedWidgetIds = new Set<string>();

        const sectionBlocks = sections.map((section) => {
          const children = section.child_widget_ids
            .map((widgetId) => widgetMap.get(widgetId))
            .filter((widget): widget is WidgetConfig => Boolean(widget));

          children.forEach((widget) => usedWidgetIds.add(widget.id));
          return { section, children };
        });

        const looseWidgets = widgets.filter((widget) => !usedWidgetIds.has(widget.id));

        return (
          <section key={zone} className="zone">
            <h3>{zone}</h3>
            {sectionBlocks.map(({ section, children }) => (
              <SectionBlock
                key={section.id}
                section={section}
                widgets={children}
                dashboard={dashboard}
                onOpenLesson={onOpenLesson}
              />
            ))}

            {looseWidgets.length === 0 && sectionBlocks.length === 0 ? <p className="muted">No widgets</p> : null}
            {looseWidgets.map((widget) => (
              <WidgetCard key={widget.id} widget={widget} dashboard={dashboard} onOpenLesson={onOpenLesson} />
            ))}
          </section>
        );
      })}
    </div>
  );
}

function LessonView({ lesson }: { lesson: LmsLessonData }) {
  return (
    <section className="lesson-shell">
      <article className="lesson-card">
        <header className="lesson-header">
          <h2>{lesson.title}</h2>
          <p className="muted">
            {lesson.topic} | {lesson.estimated_min} min
          </p>
        </header>

        <section>
          <h3>Learning Objectives</h3>
          <ul>
            {lesson.objectives.map((objective) => (
              <li key={objective}>{objective}</li>
            ))}
          </ul>
        </section>

        <section>
          <h3>Core Theory</h3>
          <ul>
            {lesson.theory_points.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </section>
      </article>

      <article className="lesson-card">
        <h3>Practice</h3>
        <ol>
          {lesson.exercises.map((exercise) => (
            <li key={exercise.id}>
              <strong>{exercise.prompt}</strong>
              <p className="muted tiny">Type: {exercise.type}</p>
            </li>
          ))}
        </ol>
        <button type="button" className="button">
          Start Practice Session
        </button>
      </article>
    </section>
  );
}

function formatDslIssue(issue: DuiDslValidationIssue): string {
  return `[${issue.code}] ${issue.path}: ${issue.message}`;
}

export default function App() {
  const [manifest, setManifest] = useState<UiManifest | null>(null);
  const [previewManifest, setPreviewManifest] = useState<UiManifest | null>(null);
  const [prompt, setPrompt] = useState('Сделай стиль минимализм и compact, добавь weak topics');
  const [duiMode, setDuiMode] = useState<DuiMode>('extended');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [revisions, setRevisions] = useState<UiManifest[]>([]);
  const [dslRevisions, setDslRevisions] = useState<DuiDslDocument[]>([]);
  const [dslSource, setDslSource] = useState('');
  const [dslSourceDirty, setDslSourceDirty] = useState(false);
  const [dslDraft, setDslDraft] = useState<DuiDslDocument | null>(null);
  const [dslWarnings, setDslWarnings] = useState<string[]>([]);
  const [dslValidationErrors, setDslValidationErrors] = useState<DuiDslValidationIssue[]>([]);
  const [dslValidationWarnings, setDslValidationWarnings] = useState<DuiDslValidationIssue[]>([]);
  const [dslValidationValid, setDslValidationValid] = useState<boolean | null>(null);
  const [dashboard, setDashboard] = useState<LmsDashboardData | null>(null);
  const [activeLesson, setActiveLesson] = useState<LmsLessonData | null>(null);
  const [activeLessonId, setActiveLessonId] = useState<string>('lesson-linear-equations');
  const [page, setPage] = useState<Page>('dashboard');
  const surfaceContext = useMemo(
    () => ({ surfaceId: SURFACE_ID, sessionId: SESSION_ID, mode: duiMode }),
    [duiMode],
  );

  const activeManifest = previewManifest ?? manifest;

  useEffect(() => {
    void (async () => {
      try {
        const [current, history, dashboardData, currentDsl, dslHistory] = await Promise.all([
          fetchCurrentManifest({ surfaceId: SURFACE_ID, sessionId: SESSION_ID }),
          fetchRevisions({ surfaceId: SURFACE_ID, sessionId: SESSION_ID }),
          fetchDashboardData(),
          fetchCurrentDslDocument({ surfaceId: SURFACE_ID, sessionId: SESSION_ID }),
          fetchDslRevisions({ surfaceId: SURFACE_ID, sessionId: SESSION_ID }),
        ]);
        setManifest(current);
        setRevisions(history);
        setDslDraft(currentDsl);
        setDslSource(serializeDuiDslDocument(currentDsl));
        setDslSourceDirty(false);
        setDslRevisions(dslHistory);
        setDashboard(dashboardData);
        if (dashboardData.learning_path.length > 0) {
          setActiveLessonId(dashboardData.learning_path[0].id);
        }
      } catch (unknownError) {
        setError((unknownError as Error).message);
      }
    })();
  }, []);

  useEffect(() => {
    void (async () => {
      if (!activeLessonId) {
        return;
      }
      try {
        const lesson = await fetchLesson(activeLessonId);
        setActiveLesson(lesson);
      } catch (unknownError) {
        setError((unknownError as Error).message);
      }
    })();
  }, [activeLessonId]);

  useEffect(() => {
    if (activeManifest) {
      applyTheme(activeManifest.theme);
    }
  }, [activeManifest]);

  const olderRevision = useMemo(() => {
    if (!manifest || revisions.length < 2) {
      return null;
    }
    return revisions[revisions.length - 2].revision;
  }, [manifest, revisions]);

  function resetDslValidationState() {
    setDslValidationValid(null);
    setDslValidationErrors([]);
    setDslValidationWarnings([]);
  }

  function applyDslValidationState(valid: boolean, errors: DuiDslValidationIssue[], warnings: DuiDslValidationIssue[]) {
    setDslValidationValid(valid);
    setDslValidationErrors(errors);
    setDslValidationWarnings(warnings);
  }

  async function handleGenerateDslFromPrompt() {
    if (!prompt.trim()) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await requestDslIntent(prompt, duiMode, surfaceContext);
      setDslDraft(response.document);
      setDslSource(serializeDuiDslDocument(response.document));
      setDslSourceDirty(false);
      setDslWarnings(response.warnings);
      applyDslValidationState(
        response.validation_result.valid,
        response.validation_result.errors,
        response.validation_result.warnings,
      );
      setPreviewManifest(response.preview_manifest);
    } catch (unknownError) {
      setError((unknownError as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleParseDslSource() {
    if (!dslSource.trim()) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await parseDslSource(dslSource, surfaceContext);
      setDslDraft(response.document);
      setDslSourceDirty(false);
      setDslWarnings([]);
      applyDslValidationState(
        response.validation_result.valid,
        response.validation_result.errors,
        response.validation_result.warnings,
      );
      if (response.compiled_manifest) {
        setPreviewManifest(response.compiled_manifest);
      } else {
        setPreviewManifest(null);
      }
    } catch (unknownError) {
      setError((unknownError as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleValidateDslDocument() {
    if (!dslDraft) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await validateDslDocument(dslDraft, surfaceContext);
      applyDslValidationState(response.result.valid, response.result.errors, response.result.warnings);
      if (response.compiled_manifest) {
        setPreviewManifest(response.compiled_manifest);
      }
    } catch (unknownError) {
      setError((unknownError as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleCommitDslDocument() {
    if (!dslDraft) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await commitDslDocument(dslDraft, 'poc-user', surfaceContext);
      setManifest(response.manifest);
      setPreviewManifest(null);
      setDslDraft(response.document);
      setDslSource(serializeDuiDslDocument(response.document));
      setDslSourceDirty(false);
      setDslWarnings([]);
      resetDslValidationState();
      const [manifestHistory, dslHistory] = await Promise.all([
        fetchRevisions(surfaceContext),
        fetchDslRevisions(surfaceContext),
      ]);
      setRevisions(manifestHistory);
      setDslRevisions(dslHistory);
    } catch (unknownError) {
      setError((unknownError as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleLoadCurrentDsl() {
    setBusy(true);
    setError(null);
    try {
      const [currentDsl, dslHistory] = await Promise.all([
        fetchCurrentDslDocument(surfaceContext),
        fetchDslRevisions(surfaceContext),
      ]);
      setDslDraft(currentDsl);
      setDslSource(serializeDuiDslDocument(currentDsl));
      setDslSourceDirty(false);
      setDslWarnings([]);
      resetDslValidationState();
      setDslRevisions(dslHistory);
      setPreviewManifest(null);
    } catch (unknownError) {
      setError((unknownError as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleRevertManifest() {
    if (!olderRevision) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const revertedManifest = await revertRevision(olderRevision, surfaceContext);
      setManifest(revertedManifest);
      setPreviewManifest(null);
      setRevisions(await fetchRevisions(surfaceContext));
    } catch (unknownError) {
      setError((unknownError as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function openLesson(lessonId: string) {
    setActiveLessonId(lessonId);
    setPage('lesson');
  }

  if (!manifest || !dashboard || !activeLesson) {
    return <main className="app-shell">Loading...</main>;
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>MathPath LMS</h1>
          <p>
            Learner: {dashboard.learner.name} | Revision {manifest.revision} | Theme {manifest.theme.profile} |
            {' '}Mode {duiMode} | Surface {SURFACE_ID} | DSL rev {dslDraft?.meta.revision ?? '-'}
          </p>
        </div>
        <nav className="tab-row" aria-label="Main pages">
          <button
            type="button"
            className={`tab-button ${page === 'dashboard' ? 'active' : ''}`}
            onClick={() => setPage('dashboard')}
          >
            Dashboard
          </button>
          <button
            type="button"
            className={`tab-button ${page === 'lesson' ? 'active' : ''}`}
            onClick={() => setPage('lesson')}
          >
            Lesson
          </button>
        </nav>
      </header>

      <section className="assistant-panel">
        <label htmlFor="intent">DUI Assistant Prompt</label>
        <textarea
          id="intent"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          rows={3}
          placeholder="Например: сделай минимализм, добавь weak topics и секция практика"
        />
        <div className="mode-row">
          <label htmlFor="mode">Mode</label>
          <select id="mode" value={duiMode} onChange={(event) => setDuiMode(event.target.value as DuiMode)}>
            <option value="safe">safe</option>
            <option value="extended">extended</option>
            <option value="experimental">experimental</option>
          </select>
        </div>
        <div className="actions">
          <button type="button" className="button" onClick={handleGenerateDslFromPrompt} disabled={busy}>
            Generate DSL
          </button>
          <button type="button" className="button tonal" onClick={handleParseDslSource} disabled={busy || !dslSource.trim()}>
            Parse Source
          </button>
          <button
            type="button"
            className="button tonal"
            onClick={handleValidateDslDocument}
            disabled={busy || !dslDraft || dslSourceDirty}
          >
            Validate DSL
          </button>
          <button
            type="button"
            className="button tonal"
            onClick={handleCommitDslDocument}
            disabled={busy || !dslDraft || dslValidationValid === false || dslSourceDirty}
          >
            Commit DSL
          </button>
          <button type="button" className="button outlined" onClick={handleLoadCurrentDsl} disabled={busy}>
            Load Current DSL
          </button>
          <button
            type="button"
            className="button outlined"
            onClick={handleRevertManifest}
            disabled={busy || !olderRevision}
          >
            Revert
          </button>
          <button
            type="button"
            className="button outlined"
            onClick={() => {
              setDslWarnings([]);
              resetDslValidationState();
              setPreviewManifest(null);
            }}
          >
            Clear Preview
          </button>
        </div>
        <label htmlFor="dsl-source">DUI-Lang Source</label>
        <textarea
          id="dsl-source"
          className="dsl-source-editor mono"
          value={dslSource}
          onChange={(event) => {
            setDslSource(event.target.value);
            setDslSourceDirty(true);
          }}
          rows={16}
          placeholder="surface math_lms.dashboard { ... }"
        />
      </section>

      {dslDraft ? (
        <section className="patch-summary">
          <h2>DUI DSL Draft</h2>
          <p>
            Document: {dslDraft.meta.document_id} | revision: {dslDraft.meta.revision} | nodes: {dslDraft.nodes.length} |
            {' '}actions: {dslDraft.actions.length} | bindings: {dslDraft.bindings.length}
          </p>
          <p>
            Validation: {dslValidationValid === null ? 'not checked' : dslValidationValid ? 'valid' : 'invalid'} |
            {' '}Manifest revisions: {revisions.length} | DSL revisions: {dslRevisions.length}
          </p>
          {dslSourceDirty ? <p className="muted tiny">Source changed locally. Run Parse Source before Validate/Commit.</p> : null}
          {dslWarnings.length ? (
            <div className="warnings">
              {dslWarnings.map((warning) => (
                <p key={warning}>{warning}</p>
              ))}
            </div>
          ) : null}
          {dslValidationErrors.length ? (
            <div className="warnings">
              <p>Validation errors:</p>
              <ul className="list-reset list-gap">
                {dslValidationErrors.map((issue, index) => (
                  <li key={`${issue.code}-${index}`}>{formatDslIssue(issue)}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {dslValidationWarnings.length ? (
            <div className="warnings">
              <p>Validation warnings:</p>
              <ul className="list-reset list-gap">
                {dslValidationWarnings.map((issue, index) => (
                  <li key={`${issue.code}-${index}`}>{formatDslIssue(issue)}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}

      {error ? <section className="error">{error}</section> : null}

      {page === 'dashboard' && activeManifest ? (
        <DashboardView manifest={activeManifest} dashboard={dashboard} onOpenLesson={openLesson} />
      ) : null}
      {page === 'lesson' ? <LessonView lesson={activeLesson} /> : null}
    </main>
  );
}
