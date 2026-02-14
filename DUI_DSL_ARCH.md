# ARCH: DUI-Lang (Controlled UI DSL) + React Transpiler

Дата: 2026-02-08  
Статус: Draft v1.0 (дизайн-спецификация для реализации)

## 1. Зачем это нужно

Мы хотим убрать текущий конфликт:
- если дать агенту слишком мало свободы, UX остается «деревянным»;
- если дать агенту право писать произвольный TSX/CSS/JS, риски безопасности становятся неприемлемыми.

Решение: **DUI-Lang** — ограниченный декларативный язык UI, который:
- достаточно выразительный для серьезной адаптации интерфейса;
- строго валидируется и компилируется в безопасный React runtime;
- полностью контролируется allowlist-каталогом компонентов, пропсов, действий и data-binding.

## 2. Цели и не-цели

### 2.1 Цели

- Поддержать сложные перестройки UI без генерации произвольного кода.
- Разделить контент/структуру/поведение на уровне DSL.
- Обеспечить auditability: каждый patch и каждая операция воспроизводимы.
- Сохранить A2UI envelope и surface-based архитектуру.

### 2.2 Не-цели

- Никакого исполнения JS-кода, пришедшего от агента.
- Никаких динамических `import`, `eval`, `Function`, `dangerouslySetInnerHTML`.
- Никакого прямого доступа к сырому HTTP из DSL (только capability map).

## 3. Термины

- `Surface`: отдельная UI-поверхность (`math_lms.dashboard`, `math_lms.lesson`).
- `DUI Document`: полный документ DSL для поверхности.
- `Node`: элемент DSL-дерева (виджет/контейнер/контрол).
- `Capability`: разрешенный backend-контракт данных или действия.
- `Action`: разрешенная реакция на событие.
- `Policy Engine`: набор правил безопасности и UX-ограничений.
- `Transpiler`: компилятор DSL -> React IR -> React Runtime.

## 4. Архитектура решения

### 4.1 Компоненты

- `Agent Planner` (LLM): генерирует patch над DSL, не код.
- `DUI Backend Orchestrator`:
  - принимает envelope;
  - вызывает LLM;
  - валидирует DSL patch;
  - пишет ревизию в surface store.
- `DSL Validator`:
  - schema/type validation;
  - policy validation;
  - capability validation.
- `React Transpiler Runtime` (frontend):
  - компилирует DSL AST в безопасный React IR;
  - рендерит только allowlist-компоненты.
- `Surface Store`:
  - хранит ревизии документов по surface_id;
  - хранит patch plan и статус commit/revert.

### 4.2 Поток запроса

1. Пользователь пишет intent.
2. Frontend отправляет `intent.request` в `/a2ui/envelope`.
3. Backend строит `DUI Patch`.
4. Validator прогоняет:
   - schema;
   - references;
   - policy;
   - capability ACL.
5. Если ок: отдает preview document.
6. Frontend компилирует preview document в React IR и показывает diff.
7. Пользователь подтверждает: `commit.request`.
8. Backend сохраняет новую ревизию surface document.

### 4.3 ASCII схема

```text
User Prompt
   |
   v
Frontend (A2UI Envelope) ----> Backend Orchestrator ----> LLM Planner
   |                                  |                        |
   |                                  v                        |
   |                           DSL Patch Proposal <------------
   |                                  |
   |                                  v
   |                           DSL Validator + Policy
   |                                  |
   |                 (preview doc) or (rejected + violations)
   v
React Transpiler Runtime (safe allowlist renderer)
   |
   v
Preview -> Commit -> Surface Store Revision
```

## 5. Спецификация DUI-Lang

### 5.1 Формат документа

Канонический wire-формат: JSON (строго схемный).

```json
{
  "dsl_version": "dui-lang/1.0",
  "surface": {
    "id": "math_lms.dashboard",
    "title": "Math Dashboard",
    "route": "/dashboard"
  },
  "meta": {
    "document_id": "doc_7f8d...",
    "revision": 12,
    "created_at": "2026-02-08T18:30:00Z",
    "created_by": "agent"
  },
  "theme": {
    "profile": "minimal",
    "density": "compact",
    "tokens": {
      "bg": "#f8fafc",
      "surface": "#ffffff",
      "accent": "#0f172a",
      "radius": "12px"
    }
  },
  "state": {
    "locals": {
      "selectedLessonId": "lesson-linear-equations"
    }
  },
  "nodes": [
    {
      "id": "root",
      "type": "layout.page",
      "props": {
        "maxWidth": "1280px"
      },
      "children": ["header", "content"]
    }
  ],
  "bindings": [],
  "actions": []
}
```

### 5.2 Базовый контракт Node

Каждый node обязан удовлетворять следующему контракту:

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| `id` | `string` | Да | Уникальный ID в документе, regex: `^[a-z][a-z0-9_\\-.]{2,63}$` |
| `type` | `string` | Да | Тип элемента из каталога DSL |
| `props` | `object` | Нет | Типизированные props конкретного `type` |
| `style` | `object` | Нет | Только token-based стили (`token(...)`) |
| `layout` | `object` | Нет | Grid/flex/spacing правила из allowlist |
| `a11y` | `object` | Нет | `role`, `label`, `describedBy`, `tabIndex` в safe-пределах |
| `visibleWhen` | `Expr` | Нет | Условие видимости |
| `enabledWhen` | `Expr` | Нет | Условие доступности |
| `children` | `string[]` | Нет | Список дочерних node ID |
| `slots` | `object` | Нет | Именованные слоты (`header`, `footer`, `actions`...) |
| `on` | `object` | Нет | События -> action references |

### 5.3 Типы данных языка

- `string`
- `number`
- `boolean`
- `null`
- `color` (строка в формате `#RRGGBB`, `rgba(...)`, `token(...)`)
- `size` (`px`, `%`, `rem`, `vh`, `vw`)
- `enum`
- `array<T>`
- `object`
- `Expr` (ограниченные выражения)
- `BindingRef`
- `ActionRef`

### 5.4 Выражения (Expr)

Выражения не содержат JS, только whitelist операторов:

- логические: `and`, `or`, `not`
- сравнения: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`
- работа со строками: `contains`, `startsWith`, `endsWith`, `lower`, `upper`, `trim`
- арифметика: `add`, `sub`, `mul`, `div`, `min`, `max`, `round`, `abs`
- null-safe: `coalesce`
- условные: `if`
- коллекции: `len`, `some`, `every`, `mapValue` (ограниченный)

Пример:

```json
{
  "op": "and",
  "args": [
    { "op": "gt", "args": [{ "binding": "cap.math.streak_days" }, 0] },
    { "op": "neq", "args": [{ "state": "selectedLessonId" }, null] }
  ]
}
```

### 5.5 Data binding модель

Binding всегда проходит через capability map.

```json
{
  "id": "bind_learning_path",
  "source": "capability:math.learning_path",
  "select": "$.items",
  "args": {
    "limit": 10
  },
  "cache": {
    "ttl_sec": 30
  }
}
```

Ограничения:
- `source` только из allowlist capability IDs.
- `args` валидируются по capability input schema.
- `select` — только безопасный JSONPath subset.
- Нельзя задавать URL/headers/метод руками.

### 5.6 Action модель

Допустимые action types v1:

- `nav.open_route`
- `nav.open_surface`
- `state.set`
- `state.toggle`
- `ui.open_modal`
- `ui.close_modal`
- `ui.toast`
- `dui.request_patch`
- `dui.commit_patch`
- `dui.revert_revision`
- `capability.invoke` (только allowlist command-capabilities)

Пример:

```json
{
  "id": "act_open_lesson",
  "type": "nav.open_surface",
  "params": {
    "surface_id": "math_lms.lesson",
    "payload": {
      "lesson_id": { "state": "selectedLessonId" }
    }
  }
}
```

### 5.7 Styling и tokens

Правило: raw CSS из агента запрещен. Разрешены только:
- theme profiles;
- token override из allowlist ключей;
- component variant enums.

Token allowlist v1:
- `bg`
- `surface`
- `surface_container`
- `text`
- `muted`
- `accent`
- `accent_container`
- `outline`
- `radius`
- `shadow`
- `font`
- `gap`
- `padding`
- `row_height`
- `focus_ring`
- `danger`
- `warning`
- `success`
- `info`

### 5.8 Layout модель

Global constraints:
- `max_columns`: `1..6`
- `sidebar_width`: `narrow|normal|wide`
- `content_density`: `comfortable|compact`
- `emphasis_zone`: `header|sidebar|content|footer`
- `max_nodes`: `<= 400`
- `max_depth`: `<= 16`

Node-level layout props allowlist:
- `width`, `height`, `minWidth`, `maxWidth`, `minHeight`, `maxHeight`
- `grow`, `shrink`, `basis`
- `align`, `justify`
- `gap`, `padding`, `margin`
- `columns`, `rows`, `colSpan`, `rowSpan`
- `sticky`, `zIndex` (ограниченно)

### 5.9 Accessibility

Обязательные требования:
- Все интерактивные элементы имеют `a11y.label`.
- Контраст текста к фону не ниже WCAG AA (4.5:1).
- Фокус-стили обязательны для keyboard navigation.
- Табличные компоненты требуют корректные header semantics.

### 5.10 I18n

Строки могут быть:
- literal (`"Start practice"`);
- i18n-key (`{"i18n":"lms.start_practice"}`).

Запрещено смешивать HTML и текст в i18n-строке.

### 5.11 Ограничения исполнения

- Нет сетевого доступа из DSL кроме capability map.
- Нет inline script.
- Нет внешних font/script источников из DSL.
- Нет загрузки сторонних npm-пакетов из DSL.

## 6. Формальная грамматика (EBNF для текстового sugar-синтаксиса)

```ebnf
document        = "surface" ident "{" meta theme state? node+ binding* action* "}" ;
meta            = "meta" "{" kv* "}" ;
theme           = "theme" "{" ("profile" ":" ident) ("density" ":" ident)? token_block? "}" ;
token_block     = "tokens" "{" token_pair* "}" ;
state           = "state" "{" state_pair* "}" ;
node            = "node" ident ":" type "{" prop_block? layout_block? style_block? a11y_block? cond_block? children_block? slots_block? on_block? "}" ;
binding         = "binding" ident "{" "source" ":" string "select" ":" string ("args" ":" object)? ("cache" ":" object)? "}" ;
action          = "action" ident "{" "type" ":" ident ("params" ":" object)? "}" ;
type            = ident "." ident ;
children_block  = "children" ":" "[" ident* "]" ;
slots_block     = "slots" ":" "{" slot_pair* "}" ;
on_block        = "on" ":" "{" event_pair* "}" ;
cond_block      = ("visibleWhen" ":" expr)? ("enabledWhen" ":" expr)? ;
expr            = literal | ref | call ;
call            = ident "(" (expr ("," expr)*)? ")" ;
ref             = "state." ident | "binding." ident ;
ident           = letter { letter | digit | "_" | "-" | "." } ;
```

Примечание: для API и хранения используется canonical JSON AST, не sugar-синтаксис.

## 7. Patch DSL (изменения документа)

Операции patch v1:

- `create_node`
- `update_node_props`
- `update_node_layout`
- `update_node_style`
- `move_node`
- `delete_node`
- `attach_binding`
- `detach_binding`
- `attach_action`
- `detach_action`
- `set_theme_profile`
- `set_theme_tokens`
- `set_layout_constraints`

Patch constraints:
- atomic batch commit;
- all references resolvable после применения;
- rollback на предыдущую ревизию обязателен.

## 8. Транслятор в React

### 8.1 Pipeline

1. `JSON parse`
2. `Schema validation`
3. `Reference graph build`
4. `Type check`
5. `Policy check`
6. `Capability ACL check`
7. `Normalize AST`
8. `Lowering AST -> React IR`
9. `IR -> React element map (allowlist)`
10. `Hydration state/bindings`
11. `Render`

### 8.2 React IR

IR-узел:

```ts
type ReactIrNode = {
  id: string;
  componentKey: string; // map key в allowlist
  props: Record<string, unknown>;
  children: ReactIrNode[];
  slots?: Record<string, ReactIrNode[]>;
  visibleWhen?: CompiledExpr;
  enabledWhen?: CompiledExpr;
  events?: Record<string, CompiledActionRef>;
};
```

### 8.3 Component Registry (frontend)

```ts
const registry: Record<string, SafeRenderer> = {
  "layout.page": LayoutPage,
  "content.text": ContentText,
  "data.kpi_card": DataKpiCard,
  ...
};
```

Правило: любой `type`, которого нет в `registry`, отклоняется до рендера.

### 8.4 Безопасность транслятора

- Нет генерации строкового JSX.
- Нет `new Function`.
- Все выражения интерпретируются через безопасный evaluator.
- Все actions исполняются через `ActionDispatcher` с ACL.

## 9. Policy Engine (подробно)

Валидации:

- structural:
  - уникальность node IDs;
  - отсутствие циклов;
  - корректность parent/child ссылок;
  - максимальные лимиты узлов и глубины.
- semantic:
  - props type-check;
  - compatibility `type` + `props`;
  - допустимые `events`.
- security:
  - capability ACL;
  - запрет внешних URL;
  - запрет небезопасных схем (`javascript:`, `data:` кроме явно разрешенных media).
- UX:
  - protected nodes нельзя удалить;
  - обязательные ключевые виджеты surface не теряются;
  - критичные CTA не скрываются без замены.

## 10. Версионирование

- `dsl_version`: semver-like (`dui-lang/1.0`, `dui-lang/1.1`).
- `catalog_version`: версия каталога доступных элементов.
- `migrations`:
  - forward-transform при загрузке старой ревизии;
  - backward-compat только в пределах major.

## 11. Наблюдаемость и аудит

Логи:
- `envelope_id`, `session_id`, `surface_id`, `turn_id`;
- `policy_result` (ok/rejected + violations);
- `node_count_before/after`;
- `actions_count_before/after`;
- `capability_calls_predicted`.

Метрики:
- compile latency p50/p95;
- reject rate;
- rollback rate;
- top violation classes.

## 12. План реализации по этапам

1. `v1-core`:
   - AST schema;
   - validator;
   - react IR renderer;
   - 40 базовых элементов.
2. `v1.1-layout+forms`:
   - расширенный layout;
   - формы;
   - action dispatcher ACL.
3. `v1.2-analytics+lms`:
   - charts;
   - lms-блоки;
   - domain templates.
4. `v2`:
   - multi-surface choreography;
   - cross-surface actions;
   - richer expression engine.

## 13. Полный каталог элементов вёрстки (ИСЧЕРПЫВАЮЩИЙ для DUI-Lang v1.0)

Ниже полный список доступных `type` в каталоге `dui-catalog-v1`.  
Каждая строка задает контракт использования.

Колонки:
- `ID`: ключ элемента в DSL.
- `Назначение`: зачем нужен элемент.
- `Ключевые props`: обязательные/важные параметры.
- `События/действия`: разрешенные события и типичные action hooks.

### 13.1 Layout и структура (24)

| ID | Назначение | Ключевые props | События/действия |
|---|---|---|---|
| `layout.surface` | Корень surface | `zoneMap`, `maxWidth`, `scrollMode` | `onMount`, `onResize` |
| `layout.page` | Корневой контейнер страницы | `maxWidth`, `padding`, `align` | `onMount` |
| `layout.region` | Именованная зона (`header/sidebar/...`) | `zone`, `sticky`, `minSize` | `onVisible` |
| `layout.container` | Универсальный контейнер | `variant`, `padding`, `border` | `onClick` (опц.) |
| `layout.stack` | Вертикальный поток | `gap`, `align`, `wrap` | нет |
| `layout.inline` | Горизонтальный поток | `gap`, `justify`, `wrap` | нет |
| `layout.grid` | CSS-grid модель | `columns`, `rows`, `gap` | `onResize` |
| `layout.columns` | Колоночный layout | `count`, `ratio`, `gap` | `onResize` |
| `layout.split` | Разделяемая панель | `direction`, `ratio`, `resizable` | `onSplitChange` |
| `layout.tabs` | Контейнер вкладок | `items`, `activeId` | `onChange` |
| `layout.accordion` | Группы раскрытия | `items`, `multiple`, `defaultOpen` | `onToggle` |
| `layout.drawer` | Выезжающая панель | `side`, `width`, `modal` | `onOpen`, `onClose` |
| `layout.sidebar` | Sidebar-секция | `width`, `collapsible`, `defaultCollapsed` | `onToggle` |
| `layout.section` | Секция контента | `title`, `subtitle`, `actionsSlot` | `onAction` |
| `layout.card` | Карточный контейнер | `elevation`, `radius`, `padding` | `onClick` |
| `layout.panel` | Панель без карточного chrome | `tone`, `padding` | нет |
| `layout.list` | Контейнер списка | `dense`, `divider`, `virtualized` | `onScrollEnd` |
| `layout.list_item` | Элемент списка | `selected`, `leading`, `trailing` | `onClick` |
| `layout.table` | Табличный контейнер | `columns`, `stickyHeader`, `zebra` | `onSort`, `onPage` |
| `layout.table_row` | Строка таблицы | `selected`, `hoverable` | `onClick` |
| `layout.table_cell` | Ячейка таблицы | `align`, `truncate`, `colSpan` | нет |
| `layout.timeline` | Лента событий | `orientation`, `dense` | `onItemClick` |
| `layout.carousel` | Карусель карточек | `itemsPerView`, `autoplay`, `loop` | `onSlideChange` |
| `layout.portal_anchor` | Точка портала overlays | `anchorId` | нет |

### 13.2 Контент и типографика (20)

| ID | Назначение | Ключевые props | События/действия |
|---|---|---|---|
| `content.heading` | Заголовок | `level`, `text`, `truncate` | нет |
| `content.text` | Основной текст | `text`, `tone`, `maxLines` | нет |
| `content.caption` | Подпись/микротекст | `text`, `tone` | нет |
| `content.label` | Label для полей/секций | `text`, `required` | нет |
| `content.code_block` | Блок кода | `code`, `language`, `lineNumbers` | `onCopy` |
| `content.math_inline` | Инлайн-формула | `latex`, `fallbackText` | нет |
| `content.math_block` | Блок формулы | `latex`, `align`, `numbered` | нет |
| `content.markdown` | Ограниченный markdown | `source`, `allowedMarks` | `onLinkClick` |
| `content.rich_text` | Структурированный rich text | `fragments`, `maxLines` | `onLinkClick` |
| `content.quote` | Цитата | `text`, `author` | нет |
| `content.divider` | Разделитель | `orientation`, `inset` | нет |
| `content.badge` | Короткий статус | `text`, `tone`, `size` | нет |
| `content.chip` | Чип/фильтр | `text`, `selected`, `closable` | `onClick`, `onRemove` |
| `content.avatar` | Аватар | `src`, `alt`, `size`, `fallback` | `onClick` |
| `content.icon` | Иконка из safe set | `name`, `size`, `tone` | `onClick` |
| `content.image` | Изображение | `srcRef`, `alt`, `fit`, `ratio` | `onLoad`, `onError`, `onClick` |
| `content.video` | Видео-плеер (ограниченный) | `srcRef`, `controls`, `posterRef` | `onPlay`, `onPause`, `onEnd` |
| `content.audio` | Аудио-плеер | `srcRef`, `controls` | `onPlay`, `onPause`, `onEnd` |
| `content.kbd` | Клавиша/шорткат | `text` | нет |
| `content.tag` | Тег-категория | `text`, `tone` | `onClick` |

### 13.3 Навигация (14)

| ID | Назначение | Ключевые props | События/действия |
|---|---|---|---|
| `nav.app_bar` | Верхняя панель | `title`, `leading`, `actions` | `onAction` |
| `nav.breadcrumbs` | Хлебные крошки | `items`, `maxItems` | `onNavigate` |
| `nav.nav_rail` | Боковая rail-навигация | `items`, `selectedId` | `onSelect` |
| `nav.nav_drawer` | Drawer-навигация | `items`, `open`, `side` | `onSelect`, `onClose` |
| `nav.tab_bar` | Горизонтальные табы | `tabs`, `active` | `onChange` |
| `nav.pager` | Пагинация | `page`, `pageSize`, `total` | `onPageChange` |
| `nav.stepper` | Пошаговый flow | `steps`, `activeStep` | `onStepChange` |
| `nav.link` | Безопасная ссылка | `label`, `to`, `externalAllowed` | `onClick` |
| `nav.button` | Кнопка | `label`, `variant`, `size`, `disabled` | `onClick` |
| `nav.icon_button` | Иконка-кнопка | `icon`, `variant`, `ariaLabel` | `onClick` |
| `nav.segmented` | Сегментированный селектор | `segments`, `value` | `onChange` |
| `nav.command_palette` | Палитра команд | `commands`, `open` | `onCommand`, `onClose` |
| `nav.search_bar` | Поиск | `value`, `placeholder`, `debounceMs` | `onChange`, `onSubmit` |
| `nav.back_button` | Назад | `fallbackRoute` | `onClick` |

### 13.4 Формы и ввод (26)

| ID | Назначение | Ключевые props | События/действия |
|---|---|---|---|
| `form.form` | Контейнер формы | `submitAction`, `validateOn` | `onSubmit`, `onReset` |
| `form.fieldset` | Группа полей | `legend`, `columns` | нет |
| `form.input_text` | Текстовый ввод | `name`, `value`, `placeholder`, `maxLength` | `onChange`, `onBlur` |
| `form.input_password` | Пароль | `name`, `value`, `strengthMeter` | `onChange`, `onBlur` |
| `form.input_email` | Email | `name`, `value`, `autocomplete` | `onChange`, `onBlur` |
| `form.input_phone` | Телефон | `name`, `value`, `mask` | `onChange`, `onBlur` |
| `form.input_number` | Числовой ввод | `name`, `value`, `min`, `max`, `step` | `onChange`, `onBlur` |
| `form.textarea` | Многострочный ввод | `name`, `value`, `rows`, `maxLength` | `onChange`, `onBlur` |
| `form.select` | Выпадающий список | `name`, `value`, `options` | `onChange` |
| `form.multiselect` | Множественный выбор | `name`, `values`, `options` | `onChange` |
| `form.radio_group` | Радио-группа | `name`, `value`, `options` | `onChange` |
| `form.checkbox` | Чекбокс | `name`, `checked`, `label` | `onChange` |
| `form.switch` | Тумблер | `name`, `checked`, `label` | `onChange` |
| `form.slider` | Ползунок | `name`, `value`, `min`, `max` | `onChange`, `onChangeEnd` |
| `form.range_slider` | Диапазон | `name`, `start`, `end`, `min`, `max` | `onChange`, `onChangeEnd` |
| `form.date_picker` | Выбор даты | `name`, `value`, `minDate`, `maxDate` | `onChange` |
| `form.time_picker` | Выбор времени | `name`, `value`, `stepMin` | `onChange` |
| `form.datetime_picker` | Дата+время | `name`, `value`, `timezone` | `onChange` |
| `form.file_upload` | Загрузка файлов | `name`, `accept`, `multiple`, `maxSizeMb` | `onSelect`, `onRemove` |
| `form.color_picker` | Выбор цвета | `name`, `value`, `palette` | `onChange` |
| `form.tag_input` | Ввод тегов | `name`, `values`, `suggestions` | `onAdd`, `onRemove` |
| `form.rating` | Рейтинг-звезды | `name`, `value`, `max` | `onChange` |
| `form.matrix_input` | Матрица ответов | `name`, `rows`, `cols`, `values` | `onChange` |
| `form.math_expression` | Математический ввод | `name`, `latex`, `syntaxMode` | `onChange`, `onValidate` |
| `form.code_input` | Ввод кода/формул | `name`, `value`, `language`, `lineNumbers` | `onChange`, `onValidate` |
| `form.form_error_summary` | Сводка ошибок формы | `errors`, `title` | `onItemClick` |

### 13.5 Данные и состояния (20)

| ID | Назначение | Ключевые props | События/действия |
|---|---|---|---|
| `data.kpi_card` | KPI карточка | `label`, `value`, `trend`, `tone` | `onClick` |
| `data.stat_group` | Группа KPI | `items`, `columns` | `onItemClick` |
| `data.progress_bar` | Линейный прогресс | `value`, `max`, `showLabel` | нет |
| `data.progress_circle` | Круговой прогресс | `value`, `max`, `size` | нет |
| `data.skeleton` | Скелетон | `shape`, `count`, `animated` | нет |
| `data.empty_state` | Пустое состояние | `title`, `description`, `cta` | `onAction` |
| `data.error_state` | Ошибка загрузки/блока | `title`, `message`, `retryAction` | `onRetry` |
| `data.info_callout` | Инфо-алерт | `title`, `message` | `onClose` |
| `data.warning_callout` | Warning-алерт | `title`, `message` | `onClose` |
| `data.success_callout` | Success-алерт | `title`, `message` | `onClose` |
| `data.activity_feed` | Лента активности | `items`, `maxItems` | `onItemClick` |
| `data.log_view` | Журнал событий | `entries`, `levelFilter` | `onFilterChange` |
| `data.key_value` | Пара ключ-значение | `items`, `columns` | `onItemClick` |
| `data.property_list` | Список свойств | `groups`, `dense` | `onItemClick` |
| `data.data_table` | Дата-таблица | `columns`, `rows`, `pagination` | `onSort`, `onRowClick`, `onPage` |
| `data.pivot_table` | Пивот-таблица | `dimensions`, `measures`, `rows` | `onConfigChange` |
| `data.calendar` | Календарь | `view`, `events`, `range` | `onDateSelect`, `onEventClick` |
| `data.agenda` | Повестка/список событий | `items`, `groupByDate` | `onItemClick` |
| `data.kanban_board` | Канбан-доска | `columns`, `cards`, `draggable` | `onCardMove`, `onCardClick` |
| `data.tree_view` | Дерево | `nodes`, `expanded`, `selectable` | `onToggle`, `onSelect` |

### 13.6 Графики и аналитика (16)

| ID | Назначение | Ключевые props | События/действия |
|---|---|---|---|
| `chart.line` | Линейный график | `series`, `xKey`, `yKey` | `onPointClick`, `onLegendToggle` |
| `chart.area` | Областной график | `series`, `stacked`, `opacity` | `onPointClick` |
| `chart.bar` | Столбчатый график | `series`, `categoryKey` | `onBarClick` |
| `chart.stacked_bar` | Стек-бар | `series`, `categoryKey`, `normalize` | `onBarClick` |
| `chart.pie` | Pie chart | `series`, `labelKey`, `valueKey` | `onSliceClick` |
| `chart.donut` | Donut chart | `series`, `innerRadius`, `centerLabel` | `onSliceClick` |
| `chart.scatter` | Scatter plot | `points`, `xKey`, `yKey` | `onPointClick` |
| `chart.bubble` | Bubble chart | `points`, `sizeKey`, `colorKey` | `onPointClick` |
| `chart.heatmap` | Тепловая карта | `matrix`, `xLabels`, `yLabels` | `onCellClick` |
| `chart.radar` | Radar chart | `axes`, `series` | `onPointClick` |
| `chart.histogram` | Гистограмма | `bins`, `values` | `onBinClick` |
| `chart.boxplot` | Boxplot | `groups`, `quartiles` | `onGroupClick` |
| `chart.sparkline` | Мини-график | `values`, `strokeWidth` | `onClick` |
| `chart.gauge` | Gauge | `value`, `min`, `max`, `zones` | нет |
| `chart.funnel` | Funnel | `steps`, `values` | `onStepClick` |
| `chart.waterfall` | Waterfall | `steps`, `values` | `onBarClick` |

### 13.7 Overlays и feedback (12)

| ID | Назначение | Ключевые props | События/действия |
|---|---|---|---|
| `overlay.modal` | Модальное окно | `open`, `title`, `size`, `closeOnEsc` | `onClose`, `onConfirm` |
| `overlay.dialog_confirm` | Диалог подтверждения | `open`, `message`, `confirmTone` | `onConfirm`, `onCancel` |
| `overlay.popover` | Поповер | `open`, `anchorId`, `placement` | `onClose` |
| `overlay.tooltip` | Подсказка | `text`, `anchorId`, `placement` | нет |
| `overlay.toast` | Toast уведомление | `message`, `tone`, `durationMs` | `onDismiss` |
| `overlay.snackbar` | Snackbar | `message`, `actionLabel` | `onAction`, `onDismiss` |
| `overlay.context_menu` | Контекстное меню | `items`, `anchor` | `onSelect` |
| `overlay.command_menu` | Меню команд | `commands`, `open` | `onCommand`, `onClose` |
| `overlay.loading_overlay` | Экран загрузки | `visible`, `label`, `spinner` | нет |
| `overlay.spotlight_tour` | Тур по интерфейсу | `steps`, `activeStep` | `onNext`, `onSkip`, `onFinish` |
| `overlay.bottom_sheet` | Нижний sheet | `open`, `height`, `snapPoints` | `onClose`, `onSnap` |
| `overlay.fullscreen_panel` | Полноэкранная панель | `open`, `title`, `showClose` | `onClose` |

### 13.8 Agent-control элементы (10)

| ID | Назначение | Ключевые props | События/действия |
|---|---|---|---|
| `agent.prompt_box` | Поле запроса к агенту | `value`, `placeholder`, `maxLength` | `onSubmit`, `onChange` |
| `agent.patch_diff_view` | Визуализация diff patch | `patch`, `showJson`, `showVisual` | `onSelectOp` |
| `agent.patch_preview_toggle` | Переключатель preview/live | `previewActive` | `onToggle` |
| `agent.revision_timeline` | История ревизий | `revisions`, `activeRevision` | `onSelectRevision`, `onRevert` |
| `agent.approval_panel` | Панель approve/reject | `status`, `violationsCount` | `onApprove`, `onReject` |
| `agent.policy_violations` | Список policy ошибок | `items`, `groupBySeverity` | `onOpenDoc` |
| `agent.tool_call_log` | Лог tool-callов агента | `entries`, `expandable` | `onSelectEntry` |
| `agent.surface_switcher` | Переключение surface | `surfaces`, `activeSurface` | `onSurfaceChange` |
| `agent.mode_switcher` | Переключение `safe/extended/experimental` | `mode`, `allowedModes` | `onModeChange` |
| `agent.capability_browser` | Просмотр capability map | `capabilities`, `filter` | `onSelectCapability` |

### 13.9 LMS/Math доменные виджеты (18)

| ID | Назначение | Ключевые props | События/действия |
|---|---|---|---|
| `lms.lesson_card` | Карточка урока | `lessonId`, `title`, `difficulty`, `durationMin` | `onOpenLesson` |
| `lms.lesson_objectives` | Цели урока | `items`, `checked` | `onToggleObjective` |
| `lms.theory_points` | Теоретические тезисы | `items`, `collapsible` | `onExpand` |
| `lms.exercise_list` | Список упражнений | `items`, `statusMap` | `onOpenExercise` |
| `lms.exercise_card` | Карточка упражнения | `exerciseId`, `prompt`, `type` | `onStart`, `onSkip` |
| `lms.answer_input` | Ответ ученика | `answerType`, `value`, `validationMode` | `onChange`, `onSubmit` |
| `lms.hint_panel` | Панель подсказок | `hints`, `revealedCount` | `onRevealHint` |
| `lms.solution_panel` | Панель решения | `steps`, `lockedUntil` | `onRevealSolution` |
| `lms.formula_sheet` | Шпаргалка формул | `formulas`, `groups` | `onSelectFormula`, `onCopy` |
| `lms.topic_mastery_map` | Карта освоения тем | `topics`, `masteryPercent` | `onTopicClick` |
| `lms.weak_topics_list` | Слабые темы | `topics`, `recommendations` | `onOpenPractice` |
| `lms.practice_queue` | Очередь практики | `sets`, `dueDate` | `onStartSet` |
| `lms.study_streak` | Стрик и прогресс недели | `days`, `goal`, `completed` | `onOpenStats` |
| `lms.assignment_calendar` | Календарь заданий | `assignments`, `view` | `onOpenAssignment` |
| `lms.focus_timer` | Таймер фокуса | `durationMin`, `mode`, `autostart` | `onStart`, `onPause`, `onComplete` |
| `lms.quiz_block` | Квиз блок | `questions`, `currentIndex`, `shuffle` | `onAnswer`, `onFinish` |
| `lms.flashcard_deck` | Дека флеш-карт | `cards`, `spacedRepetition` | `onFlip`, `onRateRecall` |
| `lms.mistake_review` | Разбор ошибок | `mistakes`, `groupByTopic` | `onOpenExample`, `onRetry` |

## 14. Глобальные ограничения каталога (v1.0)

- `max_nodes_per_document`: 400
- `max_children_per_node`: 64
- `max_actions_per_node`: 12
- `max_bindings_per_document`: 120
- `max_chart_points_per_series`: 2000
- `max_table_rows_client_render`: 1000 (больше только виртуализация)
- `max_file_upload_size_mb`: 25
- `max_prompt_length`: 2000

## 15. Что это дает для продукта

- Можно дать агенту сильно больше свободы по UI.
- Мы не открываем дыру “агент пишет произвольный фронт-код”.
- У нас появляется масштабируемая мультидоменная модель: разные surfaces, один DSL, одна policy-система.
- Реализация хорошо ложится в текущий A2UI envelope и surface store.

## 16. Критичный принцип

**Агент генерирует только данные (DSL), а не исполняемый код.**  
Вся логика исполнения — внутри нашего проверенного runtime.
