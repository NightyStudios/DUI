# Adaptive UI PoC: Math LMS + DUI

Первая прикладная версия PoC:
- домен: мини LMS для изучения математики;
- frontend: 2 страницы (`Dashboard`, `Lesson`) на React + TSX;
- backend: FastAPI (Python) c DUI API (`intent -> preview -> commit -> revert`) и mock LMS endpoint'ами;
- хранение UI теперь в `surface store` (отдельные ревизии по `surface_id`);
- transport между агентом и UI поддерживает `A2UI envelope` (`POST /a2ui/envelope`);
- стилистика: Material Design-inspired (M3-подобные color roles, top app bar, tabs, cards, elevation).
- DUI режимы: `safe`, `extended` (по умолчанию), `experimental`.

## Структура

- `backend/` API, manifest revision store, mock LMS data
- `frontend/` TSX runtime renderer + DUI controls
- `ARCH.md` архитектурный blueprint

## Backend endpoints

- `GET /health`
- `POST /dev/reset-seed` (удобно в демо, чтобы вернуть начальный layout)
- `GET /lms/dashboard`
- `GET /lms/lesson/{lesson_id}`
- `GET /ui/manifest/current`
- `GET /ui/manifest/revisions`
- `GET /ui/dsl/current`
- `GET /ui/dsl/revisions`
- `GET /ui/surfaces`
- `POST /ui/dsl/parse`
- `POST /ui/dsl/validate`
- `POST /ui/dsl/commit`
- `POST /ai/dsl/intent`
- `POST /ai/ui/intent`
- `POST /ai/ui/commit`
- `POST /ai/ui/revert`
- `POST /a2ui/envelope` (новый основной transport)
- `GET /ops/metrics` (базовые runtime метрики)

## DUI v1-core (реализация)

В backend добавлен первый рабочий слой DUI:
- `dui-lang/1.0` документная модель;
- allowlist-каталог node/action типов;
- validator (структура, graph-check, policy limits, token allowlist);
- compiler `DUI -> UiManifest` для совместимого runtime preview/commit;
- seed DUI документы для `math_lms.dashboard` и `math_lms.lesson`;
- хранение DUI ревизий в `surface store` (`dsl_revisions`).

## A2UI envelope (v1)

`/a2ui/envelope` принимает и возвращает стандартизированный конверт:

- context: `session_id`, `surface_id`, `turn_id`
- policy context: `mode`, `catalog_version`
- routing: `message_type`
- data: `payload`

Быстрый пример `intent.request`:

```json
{
  "envelope_version": "a2ui.v0",
  "session_id": "demo-session",
  "surface_id": "math_lms.dashboard",
  "turn_id": "turn-42",
  "mode": "extended",
  "message_type": "intent.request",
  "payload": {
    "user_prompt": "Сделай стиль минимализм и compact",
    "current_manifest_id": "..."
  }
}
```

Ответ будет `message_type: "intent.response"` и в `payload` вернет:
- `patch_plan`
- `preview_manifest`
- `warnings`

Дополнительно поддержаны message types:
- `dsl.current.request/response`
- `dsl.intent.request/response`
- `dsl.parse.request/response`
- `dsl.revisions.request/response`
- `dsl.validate.request/response`
- `dsl.commit.request/response`

## Текстовый DUI синтаксис

Поддерживается парсинг текстового DUI в документ:

```text
surface math_lms.dashboard {
  theme { profile: minimal density: compact tokens { accent: "#111111" } }
  state { selectedLessonId: "lesson-linear-equations" }

  action act_open_lesson {
    type: nav.open_route
    params { route: "/lesson" }
  }

  node root: layout.page { children: [header_region, content_region] }
  node header_region: layout.region { props { zone: header } children: [course_progress] }
  node content_region: layout.region { props { zone: content } children: [learning_path] }

  node course_progress: data.kpi_card {
    props { title: "Progress", zone: header, capability_id: math.progress_overview, protected: true }
    on { click: act_open_lesson }
  }

  node learning_path: data.data_table {
    props { title: "Learning Path", zone: content, capability_id: math.learning_path }
  }
}
```

Frontend теперь включает DUI-workbench:
- `Generate DUI` (через `dsl.intent.request`) из natural-language prompt;
- `Parse Source` (`dsl.parse.request`) для проверки текстового DUI;
- `Validate DUI` (`dsl.validate.request`) для готового документа;
- `Commit DUI` (`dsl.commit.request`) с записью DUI + manifest ревизий;
- редактор `DUI Source` с автозаполнением текущего документа из `dsl.current.request`.

## Запуск

### Быстрый старт (frontend + backend)

```bash
cd /Users/temmie/coding/dui
cp .env.example .env
./dev.sh
```

По умолчанию:
- backend: `http://127.0.0.1:8000`
- frontend: `http://localhost:5173`

Можно переопределить порты и хосты:

```bash
BACKEND_HOST=127.0.0.1 BACKEND_PORT=8000 FRONTEND_HOST=0.0.0.0 FRONTEND_PORT=5173 ./dev.sh
```

Для CORS используйте `DUI_CORS_ORIGINS` (comma-separated), например:

```bash
export DUI_CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
```

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Локальная модель через OpenAI-совместимый endpoint (например Ollama):

```bash
export DUI_LLM_PROVIDER="local"
export DUI_LLM_BASE_URL="http://127.0.0.1:11434/v1"
export DUI_LLM_MODEL="qwen2.5:14b-instruct"
```

Облачный провайдер через APIFree:

```bash
export APIFREE_API_KEY="..."
export APIFREE_MODEL="deepseek-ai/deepseek-r1-0528"
export APIFREE_BASE_URL="https://api.apifree.ai/v1"
```

Если локальный/облачный LLM не задан или запрос к провайдеру не проходит, backend автоматически использует rule-based fallback.

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend по умолчанию использует `http://localhost:8000`.

## Тесты

```bash
backend/.venv/bin/python -m unittest -v backend.tests.test_storage_resilience backend.tests.test_dsl_parser backend.tests.test_dsl_validator backend.tests.test_dsl_compiler backend.tests.test_policy backend.tests.test_dsl_service
```

В репозитории также добавлен GitHub Actions workflow:
- backend unit tests
- frontend production build

Live-проверка именно model-generated DUI intent (опционально, не входит в CI):

```bash
DUI_LIVE_LLM_TESTS=1 \
DUI_LLM_PROVIDER=local \
DUI_LLM_BASE_URL=http://127.0.0.1:11434/v1 \
DUI_LLM_MODEL=qwen2.5:14b-instruct \
backend/.venv/bin/python -m unittest -v backend.tests.test_live_llm_prompts
```

## DUI prompts (v1)

- `Сделай стиль минимализм и compact`
- `Сделай liquid glass`
- `Убери сайдбар`
- `Фокус на практик`
- `Добавь weak topics в сайдбар`
- `Собери секция практика в content`
- `Добавь quick actions в header`

## Ограничение v1

LLM-интеграция работает в режиме structured-output с fallback. Реальный quality результата зависит от выбранной локальной/облачной модели.

## Архитектурный hardening (v2)

- orchestration вынесен в service layer (`backend/app/services/`);
- policy rules вынесены в data-профили (`backend/app/policy_profiles.py`);
- добавлен optimistic concurrency (`expected_*_revision`, `base_revision`) в commit pipeline;
- при patch commit now синхронизируются и manifest, и DUI-документ (единая ревизионная модель);
- добавлены runtime метрики (`GET /ops/metrics`);
- для multi-surface consistency есть опциональный guard `DUI_ENFORCE_CROSS_SURFACE_THEME=1`.

## Extended DUI (кратко)

В `extended` режиме доступны операции:
- `set_theme_tokens`
- `set_layout_constraints`
- `add_widget_from_template`
- `compose_section`

Это дает агенту больше свободы без генерации произвольного JSX/CSS.
