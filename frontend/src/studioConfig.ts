import type {
  DuiMode,
  LmsDashboardData,
  LmsLessonData,
  UiSurfaceSummary,
  Zone,
} from './types';

export const DASHBOARD_SURFACE_ID = 'math_lms.dashboard';
export const LESSON_SURFACE_ID = 'math_lms.lesson';
export const DEFAULT_LESSON_ID = 'lesson-linear-equations';
export const SESSION_ID = 'studio-session';

export const MODE_OPTIONS: DuiMode[] = ['safe', 'extended', 'experimental'];

export const FALLBACK_SURFACES: UiSurfaceSummary[] = [
  {
    surface_id: DASHBOARD_SURFACE_ID,
    session_id: SESSION_ID,
    catalog_version: 'v1',
    manifest_revision_count: '0',
    dsl_revision_count: '0',
  },
  {
    surface_id: LESSON_SURFACE_ID,
    session_id: SESSION_ID,
    catalog_version: 'v1',
    manifest_revision_count: '0',
    dsl_revision_count: '0',
  },
];

export const FALLBACK_DASHBOARD: LmsDashboardData = {
  learner: {
    name: 'Амина',
    track: 'Алгебра + Геометрия',
    streak_days: 12,
    weekly_goal: 5,
    lessons_done: 3,
    mastery_percent: 68,
  },
  learning_path: [
    {
      id: 'lesson-linear-equations',
      title: 'Линейные уравнения: одна переменная',
      topic: 'Алгебра',
      difficulty: 'Начальный',
      duration_min: 30,
      status: 'in_progress',
    },
    {
      id: 'lesson-quadratic-intro',
      title: 'Квадратичные функции: интуиция',
      topic: 'Алгебра',
      difficulty: 'Средний',
      duration_min: 40,
      status: 'recommended',
    },
    {
      id: 'lesson-triangles-core',
      title: 'Треугольники и подобие',
      topic: 'Геометрия',
      difficulty: 'Средний',
      duration_min: 35,
      status: 'locked',
    },
  ],
  practice_queue: [
    {
      id: 'set-linear-drill-01',
      title: 'Тренировка по линейным уравнениям №1',
      focus: 'Решение уравнений',
      problems: 12,
      due_date: '2026-02-10',
    },
    {
      id: 'set-geometry-angles-01',
      title: 'Углы в треугольниках',
      focus: 'База геометрии',
      problems: 10,
      due_date: '2026-02-12',
    },
  ],
  mastery_trend: [61, 62, 64, 65, 67, 68],
  weak_topics: ['Разложение квадратных выражений', 'Погоня за углами', 'Преобразование неравенств'],
  quick_actions: [
    { id: 'resume_lesson', label: 'Продолжить урок' },
    { id: 'start_practice', label: 'Начать практику' },
    { id: 'review_mistakes', label: 'Разобрать ошибки' },
  ],
  formulas: ['a^2 - b^2 = (a-b)(a+b)', '\\sin^2(x) + \\cos^2(x) = 1', 'x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}'],
  next_lesson_id: 'lesson-quadratic-intro',
  assignments: [
    { title: 'Набор B: линейные уравнения', due_date: '2026-02-11' },
    { title: 'Контрольная: треугольники', due_date: '2026-02-13' },
  ],
};

export const ZONE_LABELS: Record<Zone, string> = {
  header: 'Шапка',
  content: 'Основной контент',
  sidebar: 'Сайдбар',
  footer: 'Подвал',
};

export const MODE_LABELS: Record<DuiMode, string> = {
  safe: 'Безопасный',
  extended: 'Расширенный',
  experimental: 'Экспериментальный',
};

export const KIND_LABELS: Record<string, string> = {
  kpi: 'Метрика',
  table: 'Таблица',
  activity: 'Активность',
  chart: 'График',
  card: 'Карточка',
  list: 'Список',
  panel: 'Панель',
  tabs: 'Вкладки',
  form: 'Форма',
};

export const CAPABILITY_TITLES: Record<string, string> = {
  'math.progress_overview': 'Прогресс курса',
  'math.learning_path': 'Траектория обучения',
  'math.practice_queue': 'Очередь практики',
  'math.mastery_trend': 'Динамика освоения',
  'math.weak_topics': 'Слабые темы',
  'math.quick_actions': 'Быстрые действия',
  'math.formulas': 'Шпаргалки по формулам',
  'math.assignments': 'Задания',
  'math.next_lesson': 'Следующий урок',
  'math.focus_timer': 'Фокус-таймер',
};

export const SECTION_TITLE_LABELS: Record<string, string> = {
  learning_overview: 'Обзор обучения',
  'Learning Overview': 'Обзор обучения',
  'Main Content': 'Основной контент',
  'Lesson Content': 'Контент урока',
  'Lesson Header': 'Шапка урока',
  'Lesson Sidebar': 'Сайдбар урока',
  Cheatsheets: 'Шпаргалки',
  Header: 'Шапка',
  Sidebar: 'Сайдбар',
  Footer: 'Подвал',
};

export const FALLBACK_LESSONS: Record<string, LmsLessonData> = {
  'lesson-linear-equations': {
    id: 'lesson-linear-equations',
    title: 'Линейные уравнения: одна переменная',
    topic: 'Алгебра',
    estimated_min: 30,
    objectives: [
      'Изолировать переменную шаг за шагом',
      'Проверять решение подстановкой',
      'Переводить условие задачи в уравнение',
    ],
    theory_points: [
      'Одинаковые операции с обеих сторон сохраняют равенство.',
      'Сначала приводите подобные слагаемые.',
      'Всегда делайте проверку в исходном уравнении.',
    ],
    exercises: [
      { id: 'ex-1', prompt: 'Решите: 3x + 7 = 25', type: 'numeric' },
      { id: 'ex-2', prompt: 'Решите: 5(x - 2) = 20', type: 'numeric' },
      { id: 'ex-3', prompt: 'Число плюс 9 равно удвоенному числу минус 3. Найдите число.', type: 'word_problem' },
    ],
  },
  'lesson-quadratic-intro': {
    id: 'lesson-quadratic-intro',
    title: 'Квадратичные функции: интуиция',
    topic: 'Алгебра',
    estimated_min: 40,
    objectives: [
      'Определять направление ветвей параболы',
      'Оценивать положение вершины по формуле',
      'Связывать корни с пересечениями оси X',
    ],
    theory_points: [
      'Квадратичная функция имеет вид ax^2 + bx + c.',
      'Знак a задает направление ветвей параболы.',
      'Корни — это значения x, при которых y = 0.',
    ],
    exercises: [
      { id: 'ex-1', prompt: 'Для y = x^2 - 4x + 3 найдите корни.', type: 'numeric' },
      { id: 'ex-2', prompt: 'Функция y = -2x^2 + 1 направлена вверх или вниз?', type: 'single_choice' },
    ],
  },
  'lesson-triangles-core': {
    id: 'lesson-triangles-core',
    title: 'Треугольники и подобие',
    topic: 'Геометрия',
    estimated_min: 35,
    objectives: [
      'Применять признаки подобия треугольников',
      'Находить неизвестные стороны через пропорции',
      'Решать задачи на углы в треугольниках',
    ],
    theory_points: [
      'Подобные треугольники имеют равные углы и пропорциональные стороны.',
      'Сумма углов треугольника равна 180°.',
      'Пропорции — основной инструмент для вычисления длин.',
    ],
    exercises: [
      { id: 'ex-1', prompt: 'Найдите сторону AB, если треугольники подобны и коэффициент подобия равен 2.', type: 'numeric' },
      { id: 'ex-2', prompt: 'В треугольнике два угла 35° и 65°. Найдите третий угол.', type: 'numeric' },
    ],
  },
};
