export type Zone = 'header' | 'sidebar' | 'content' | 'footer';
export type WidgetKind = 'kpi' | 'table' | 'activity' | 'chart' | 'card' | 'list' | 'panel' | 'tabs' | 'form';
export type ThemeProfile = 'default' | 'minimal' | 'liquid_glass';
export type Density = 'comfortable' | 'compact';
export type DuiMode = 'safe' | 'extended' | 'experimental';

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
  style?: Record<string, unknown>;
  layout?: Record<string, unknown>;
}

export interface SectionConfig {
  id: string;
  title: string;
  zone: Zone;
  child_widget_ids: string[];
  layout: Record<string, unknown>;
  style?: Record<string, unknown>;
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
  profile?: ThemeProfile | null;
  density?: Density | null;
  tokens?: Record<string, string> | null;
  layout_constraints?: Record<string, unknown> | null;
  widget_id?: string | null;
  zone?: Zone | null;
  widget?: WidgetConfig | null;
  template_id?: string | null;
  title?: string | null;
  capability_id?: string | null;
  props?: Record<string, unknown> | null;
  section_id?: string | null;
  section_title?: string | null;
  child_widget_ids?: string[] | null;
  section_layout?: Record<string, unknown> | null;
}

export interface UiSurfaceSummary {
  surface_id: string;
  session_id: string;
  catalog_version: string;
  manifest_revision_count: string;
  dsl_revision_count: string;
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

export interface DuiDslWidgetLink {
  page?: string | null;
  widget?: string | null;
  route?: string | null;
  rel: string;
  payload: Record<string, unknown>;
}

export interface DuiDslWidget {
  id: string;
  kind: string;
  title?: string | null;
  zone?: Zone | null;
  group_id?: string | null;
  capability_id?: string | null;
  binding_id?: string | null;
  template_id?: string | null;
  visible: boolean;
  props: Record<string, unknown>;
  style: Record<string, unknown>;
  layout: Record<string, unknown>;
  behavior: Record<string, unknown>;
  a11y: Record<string, unknown>;
  links: DuiDslWidgetLink[];
}

export interface DuiDslWidgetGroup {
  id: string;
  title: string;
  page_id?: string | null;
  zone: Zone;
  widget_ids: string[];
  visible: boolean;
  layout: Record<string, unknown>;
  style: Record<string, unknown>;
  behavior: Record<string, unknown>;
}

export interface DuiDslPage {
  id: string;
  title: string;
  route: string;
  group_ids: string[];
  is_default: boolean;
  layout: Record<string, unknown>;
  style: Record<string, unknown>;
  behavior: Record<string, unknown>;
}

export interface DuiDslDocument {
  dsl_version: string;
  surface: DuiDslSurface;
  meta: DuiDslMeta;
  theme: DuiDslTheme;
  state: DuiDslState;
  pages: DuiDslPage[];
  groups: DuiDslWidgetGroup[];
  widgets: DuiDslWidget[];
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

export interface DuiDslParseResponse {
  document: DuiDslDocument;
  validation_result: DuiDslValidationResult;
  compiled_manifest: UiManifest | null;
}

export interface DuiDslIntentResponse {
  document: DuiDslDocument;
  validation_result: DuiDslValidationResult;
  preview_manifest: UiManifest | null;
  operations: PatchOperation[];
  warnings: string[];
}

export interface DuiDslCommitResponse {
  document: DuiDslDocument;
  manifest: UiManifest;
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
  learning_path: Array<{
    id: string;
    title: string;
    topic: string;
    difficulty: string;
    duration_min: number;
    status: string;
  }>;
  practice_queue: Array<{
    id: string;
    title: string;
    focus: string;
    problems: number;
    due_date: string;
  }>;
  mastery_trend: number[];
  weak_topics: string[];
  quick_actions: Array<{ id: string; label: string }>;
  formulas: string[];
  next_lesson_id: string;
  assignments: Array<{ title: string; due_date: string }>;
}

export interface LmsLessonData {
  id: string;
  title: string;
  topic: string;
  estimated_min: number;
  objectives: string[];
  theory_points: string[];
  exercises: Array<{ id: string; prompt: string; type: string }>;
}
