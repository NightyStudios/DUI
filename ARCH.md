# ARCH: PoC AI-Driven Adaptive UI (Python + TSX)

Дата: 2026-02-08

## 1) Идея и цель

Мы хотим сделать PoC, где пользователь внутри уже готового приложения говорит ассистенту: «сделай стиль минималистичным», «перестрой дашборд под мои задачи», и UI меняется под запрос без переписывания фронта вручную.

Ключевая цель PoC:
- показать, что LLM может безопасно и предсказуемо менять интерфейс на основе natural language;
- сохранить интеграцию с существующими backend endpoint'ами;
- дать режим preview/commit/revert для контролируемых изменений.

## 2) Границы PoC

In scope:
- runtime-изменение темы, layout и состава виджетов;
- UI-схема хранится отдельно от кода и может патчиться;
- изменения через AI валидируются политиками;
- поддержка отката к прошлой ревизии.

Out of scope:
- генерация произвольного TSX/CSS кода моделью;
- прямой доступ модели к продовым секретам/БД;
- автопубликация изменений без подтверждения пользователя.

## 3) Почему такой подход

Для PoC критично избежать «LLM пишет фронт-код напрямую». Это быстро ломается и сложно защищается.

Вместо этого:
- UI описывается декларативно (JSON Manifest);
- модель предлагает только структурированные патчи (JSON Patch/DSL);
- клиент рендерит только allowlist-компоненты из каталога.

Это повторяет успешный паттерн из Flutter+Gemini/GenUI: каталог компонентов + tools/function calling + структурированный output.

## 4) Высокоуровневая архитектура

Компоненты:
- Existing App Backend (Python): текущие бизнес-endpoint'ы (данные, действия, auth).
- AI UI Orchestrator (Python, FastAPI): принимает user intent, общается с LLM, валидирует и выдает безопасный UI patch.
- UI Runtime (React + TSX): рендерит интерфейс из UI Manifest, применяет патчи, показывает preview.
- Surface Store (PostgreSQL или SQLite для PoC): хранит ревизии UI по `surface_id` (например `math_lms.dashboard`, `math_lms.lesson`).
- Audit Log: кто/когда/что поменял, исходный prompt, примененный patch, результат валидации.

Поток данных:
1. Пользователь отправляет команду: «сделай минимализм». 
2. UI Runtime формирует `A2UI envelope` с `session_id/surface_id/turn_id` и вызывает `POST /a2ui/envelope`.
3. Orchestrator собирает контекст: текущий манифест, каталог компонентов, capability map endpoint'ов.
4. LLM возвращает `UiPatchPlan` в строгой схеме.
5. Policy Engine валидирует (security + UX constraints).
6. UI Runtime получает preview-патч и показывает diff.
7. Пользователь нажимает Apply -> `commit.request` в `A2UI envelope`.
8. Новая ревизия сохраняется; есть `revert`.

### 4.1 A2UI Envelope (transport)

Envelope — это стандартная обертка сообщения между UI runtime и orchestrator:
- `envelope_version`
- `session_id`
- `surface_id`
- `turn_id`
- `mode`
- `catalog_version`
- `message_type`
- `payload`

`message_type` для PoC:
- `manifest.current.request/response`
- `manifest.revisions.request/response`
- `intent.request/response`
- `commit.request/response`
- `revert.request/response`

Плюс:
- трассируемость каждого шага (`turn_id`);
- строгая привязка patch plan к surface;
- единый контракт для multi-domain/multi-surface сценариев.

## 5) Контракт: UI Manifest и Patch DSL

### 5.1 UI Manifest (декларативный)

Примерная структура:
- `version`: номер схемы;
- `theme`: токены (цвета, радиусы, тени, spacing, typography);
- `layout`: зоны (header/sidebar/content/footer);
- `widgets`: список виджетов со связью на endpoint capability;
- `bindings`: как widget берет данные из API (только через разрешенные источники).

### 5.2 UiPatchPlan (что возвращает LLM)

Модель возвращает только такие операции:
- `set_theme_tokens`
- `move_widget`
- `add_widget_from_catalog`
- `remove_widget` (если не protected)
- `set_density`
- `set_typography_profile`

Каждая операция проходит:
- JSON Schema validation;
- policy validation;
- dry-run validation на клиенте.

## 6) Capability Map для endpoint'ов

Чтобы UI адаптировался «под endpoint'ы», нужен нормализованный слой `Capability Map`:
- `capability_id`: например `orders.list`, `orders.kpi`, `users.activity`;
- `endpoint`: URL + method;
- `input_schema`/`output_schema`;
- `ui_hints`: допустимые визуализации (`table`, `kpi`, `timeline`, `chart`);
- `sensitivity`: уровень (public/internal/restricted).

LLM видит именно capability map, а не «сырой» backend.

## 7) Безопасность и guardrails

Базовые меры для PoC:
- Strict structured output (без свободного кода).
- Allowlist компонентов/токенов/операций.
- Protected зоны UI (например billing/security нельзя удалять).
- Prompt injection defense: пользовательский текст как data, системные инструкции immutable.
- Rate limiting на AI endpoint'ы.
- Revisioned rollback: мгновенный откат на предыдущую версию UI.
- Human-in-the-loop: commit только после подтверждения.

## 8) API слой (минимум для PoC)

- `POST /ai/ui/intent`
  - input: `{ user_prompt, current_manifest_id, scope }`
  - output: `{ patch_plan, preview_manifest, warnings }`

- `POST /ai/ui/commit`
  - input: `{ patch_plan_id, approved_by }`
  - output: `{ manifest_id, revision }`

- `POST /ai/ui/revert`
  - input: `{ target_revision }`
  - output: `{ manifest_id, revision }`

- `GET /ui/manifest/current`
  - output: текущий manifest

- `POST /a2ui/envelope`
  - input: `A2UI envelope`
  - output: `A2UI envelope`
  - comment: единый transport и базовый шаг к multi-domain orchestration.

## 9) Frontend (TSX) архитектура

Слои:
- `Renderer`: рендерит manifest в React-компоненты из `WidgetCatalog`.
- `ThemeEngine`: применяет design tokens через CSS variables.
- `PatchApplier`: локально применяет patch в preview режиме.
- `DiffViewer`: показывает пользователю что изменится.
- `SessionStore`: хранит draft/preview/active revision.

Ключевой принцип: frontend исполняет только собственный код + декларативные конфиги, а не LLM-generated JSX.

## 10) Backend (Python) архитектура

Рекомендуемый стек для PoC:
- FastAPI
- Pydantic v2 (валидация схем)
- SQLAlchemy + PostgreSQL (или SQLite на первом шаге)
- Redis (опционально для rate limit/кеша)

Модули:
- `llm_gateway` (provider-agnostic: OpenAI/Gemini/Anthropic)
- `prompt_builder` (system + context pack)
- `schema_validator`
- `policy_engine`
- `manifest_service`
- `audit_service`

## 11) Поэтапная реализация (вертикальными срезами)

Этап 1: Static runtime manifest
- Приложение уже рендерится из manifest без AI.
- Есть ревизии и ручной revert.

Этап 2: AI theme adaptation
- Команды типа «минимализм», «liquid glass», «compact mode».
- Меняются только theme tokens + density.

Этап 3: AI layout adaptation
- Перестановка/скрытие/добавление виджетов из каталога.
- Preview + diff + commit.

Этап 4: Endpoint-aware adaptation
- Использование Capability Map.
- Ассистент может предлагать, какие виджеты лучше под конкретные endpoint'ы.

## 12) Критерии успеха PoC

- Изменение UI за <= 5 секунд в 80% запросов.
- >= 95% ответов модели проходят schema validation.
- 0 случаев выполнения произвольного кода из ответа LLM.
- Пользователь может откатить изменение за 1 действие.

## 13) Риски и решения

Риск: модель делает «красиво», но ухудшает usability.
Решение: policy + UX constraints + diff preview + rollback.

Риск: дрейф стиля между экранами.
Решение: глобальные design tokens и style profiles.

Риск: опасные изменения в критичных зонах.
Решение: protected components + scoped permissions.

Риск: vendor lock-in LLM.
Решение: `llm_gateway` и унифицированный `UiPatchPlan` контракт.

## 14) Мой pragmatic verdict

Для твоей идеи лучший PoC-путь: **не генерировать фронт-код**, а генерировать **валидируемые UI-патчи** поверх декларативного runtime UI.

Это даст:
- быстрый результат;
- контролируемую безопасность;
- понятный путь к production (через усиление policy, observability, AB-тесты).

## 15) Референсы (что посмотрел)

- Flutter GenUI SDK (каталоги компонентов, agent/provider модель): https://docs.flutter.cn/ai/genui/get-started/
- Gemini function calling (structured tool invocation): https://ai.google.dev/gemini-api/docs/function-calling
- Google Codelab Flutter + Gemini (функции, state sync, архитектурный паттерн): https://codelabs.developers.google.com/codelabs/flutter-gemini-colorist
- Flutter samples index (наличие `dynamic_theme`, `gemini_tasks`): https://github.com/flutter/samples
