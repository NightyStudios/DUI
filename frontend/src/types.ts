export type Zone = 'header' | 'sidebar' | 'content' | 'footer';
export type WidgetKind = 'kpi' | 'table' | 'activity' | 'chart' | 'card' | 'list' | 'panel' | 'tabs' | 'form';
export type ThemeProfile = 'default' | 'minimal' | 'liquid_glass';
export type Density = 'comfortable' | 'compact';
export type DuiMode = 'safe' | 'extended' | 'experimental';
export type A2UiMessageType =
  | 'intent.request'
  | 'intent.response'
  | 'commit.request'
  | 'commit.response'
  | 'revert.request'
  | 'revert.response'
  | 'manifest.current.request'
  | 'manifest.current.response'
  | 'manifest.revisions.request'
  | 'manifest.revisions.response'
  | 'dsl.current.request'
  | 'dsl.current.response'
  | 'dsl.intent.request'
  | 'dsl.intent.response'
  | 'dsl.parse.request'
  | 'dsl.parse.response'
  | 'dsl.revisions.request'
  | 'dsl.revisions.response'
  | 'dsl.validate.request'
  | 'dsl.validate.response'
  | 'dsl.commit.request'
  | 'dsl.commit.response'
  | 'error';

export interface ThemeConfig {
  profile: ThemeProfile;
  density: Density;
  tokens: Record<string, string>;
}

export interface WidgetConfig {
  id: string;
  title: string;
  kind: WidgetKind;
  zone: Zone;
  capability_id: string;
  protected: boolean;
  template_id?: string | null;
  props: Record<string, unknown>;
}

export interface SectionConfig {
  id: string;
  title: string;
  zone: Zone;
  child_widget_ids: string[];
  layout: Record<string, unknown>;
}

export interface UiManifest {
  schema_version: 1;
  manifest_id: string;
  revision: number;
  created_at: string;
  theme: ThemeConfig;
  widgets: WidgetConfig[];
  sections: SectionConfig[];
  layout_constraints: Record<string, unknown>;
  metadata: Record<string, string>;
}

export interface PatchOperation {
  op:
    | 'set_theme_profile'
    | 'set_density'
    | 'set_theme_tokens'
    | 'set_layout_constraints'
    | 'move_widget'
    | 'remove_widget'
    | 'add_widget'
    | 'add_widget_from_template'
    | 'compose_section';

  profile?: ThemeProfile;
  density?: Density;
  tokens?: Record<string, string>;
  layout_constraints?: Record<string, unknown>;

  widget_id?: string;
  zone?: Zone;
  widget?: WidgetConfig;

  template_id?: string;
  title?: string;
  capability_id?: string;
  props?: Record<string, unknown>;

  section_id?: string;
  section_title?: string;
  child_widget_ids?: string[];
  section_layout?: Record<string, unknown>;
}

export interface UiPatchPlan {
  patch_plan_id: string;
  user_prompt: string;
  session_id: string;
  surface_id: string;
  turn_id?: string | null;
  mode: DuiMode;
  operations: PatchOperation[];
  warnings: string[];
  created_at: string;
  status: 'draft' | 'committed' | 'rejected';
}

export interface IntentResponse {
  patch_plan: UiPatchPlan;
  preview_manifest: UiManifest;
  warnings: string[];
}

export interface DuiDslSurface {
  id: string;
  title: string;
  route: string;
}

export interface DuiDslMeta {
  document_id: string;
  revision: number;
  created_at: string;
  created_by: string;
}

export interface DuiDslTheme {
  profile: ThemeProfile;
  density: Density;
  tokens: Record<string, string>;
}

export interface DuiDslState {
  locals: Record<string, unknown>;
}

export interface DuiDslNode {
  id: string;
  type: string;
  props: Record<string, unknown>;
  style: Record<string, unknown>;
  layout: Record<string, unknown>;
  a11y: Record<string, unknown>;
  visible_when: Record<string, unknown> | null;
  enabled_when: Record<string, unknown> | null;
  children: string[];
  slots: Record<string, string[]>;
  on: Record<string, string>;
}

export interface DuiDslBinding {
  id: string;
  source: string;
  select: string;
  args: Record<string, unknown>;
  cache: Record<string, unknown>;
}

export interface DuiDslAction {
  id: string;
  type: string;
  params: Record<string, unknown>;
}

export interface DuiDslDocument {
  dsl_version: string;
  surface: DuiDslSurface;
  meta: DuiDslMeta;
  theme: DuiDslTheme;
  state: DuiDslState;
  nodes: DuiDslNode[];
  bindings: DuiDslBinding[];
  actions: DuiDslAction[];
  layout_constraints: Record<string, unknown>;
}

export type DuiIssueSeverity = 'error' | 'warning';

export interface DuiDslValidationIssue {
  severity: DuiIssueSeverity;
  code: string;
  message: string;
  path: string;
}

export interface DuiDslValidationResult {
  valid: boolean;
  errors: DuiDslValidationIssue[];
  warnings: DuiDslValidationIssue[];
  stats: Record<string, number>;
}

export interface DuiDslValidateResponse {
  result: DuiDslValidationResult;
  compiled_manifest: UiManifest | null;
}

export interface DuiDslParseResponse {
  document: DuiDslDocument;
  validation_result: DuiDslValidationResult;
  compiled_manifest: UiManifest | null;
}

export interface DuiDslIntentResponse {
  document: DuiDslDocument;
  validation_result: DuiDslValidationResult;
  preview_manifest: UiManifest | null;
  warnings: string[];
}

export interface DuiDslCommitResponse {
  document: DuiDslDocument;
  manifest: UiManifest;
}

export interface A2UiEnvelope {
  envelope_version: 'a2ui.v0';
  message_id: string;
  session_id: string;
  surface_id: string;
  turn_id: string;
  sent_at: string;
  mode: DuiMode;
  catalog_version: string;
  message_type: A2UiMessageType;
  payload: Record<string, unknown>;
}

export interface LearningPathItem {
  id: string;
  title: string;
  topic: string;
  difficulty: string;
  duration_min: number;
  status: string;
}

export interface PracticeQueueItem {
  id: string;
  title: string;
  focus: string;
  problems: number;
  due_date: string;
}

export interface LmsDashboardData {
  learner: {
    name: string;
    track: string;
    streak_days: number;
    weekly_goal: number;
    lessons_done: number;
    mastery_percent: number;
  };
  learning_path: LearningPathItem[];
  practice_queue: PracticeQueueItem[];
  recent_activity: string[];
  mastery_trend: number[];
  weak_topics: string[];
  quick_actions: Array<{ id: string; label: string }>;
  formulas: string[];
  next_lesson_id: string;
  assignments: Array<{ title: string; due_date: string }>;
}

export interface LessonExercise {
  id: string;
  prompt: string;
  type: string;
}

export interface LmsLessonData {
  id: string;
  title: string;
  topic: string;
  estimated_min: number;
  objectives: string[];
  theory_points: string[];
  exercises: LessonExercise[];
}
