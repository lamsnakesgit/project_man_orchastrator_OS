# План: Автономная параллельная разработка (управляемая)

Проект: 1_project_man_orchastrator_OS_
Завершённость: [██████░░░░░░] 35% — research + plan

## Что строим глобально

Система, где идея/задача из Telegram или Asana превращается в автономную работу
агентов: агенты параллельно выполняют задачи по нескольким проектам, пока не
выполнятся критерии приёмки (тесты + PR + QA). Человек управляет через
Telegram/дашборд, не сидя в чате с каждым агентом.

**Ключевой принцип (из статьи borodutch):** не чат, а loop. Промпт — не source
of truth. Source of truth — трекер задач (доска). Агенты действуют только на
активных статусах (`to-do`, `in-progress`, `rework`). Done — терминальный.

## Что уже есть (60% стека borodutch)

| Компонент | Статус | Файл |
|---|---|---|
| FastAPI API-шлюз + Telegram webhook | ✅ | `api.py` |
| TaskStore (Redis + fallback) | ✅ | `task_store.py` |
| Worktree-изоляция задач | ✅ | `worktree_manager.py` |
| Git workflow (ветка → тесты → commit → push → Draft PR) | ✅ | `git_workflow.py` |
| Telegram-уведомления | ✅ | `notifier.py` |
| Профили проектов (web, mobile, marketing, general) | ✅ | `project_profiles.py` |
| Antigravity SDK запуск агента | ⚠️ баг | `agent.py` |
| Asana webhook | ✅ заглушка | `api.py` |
| Celery очередь | ✅ | `tasks.py` |

## Что нужно добавить (по фазам)

### Фаза 0: Фикс бага (30 минут)

**Баг:** `agent.py:83` — `api_key=api_key`, переменная не определена → NameError.

**Фикс:**
```python
# agent.py
import os

# Вместо api_key=api_key:
# 1. Если vertex=True — api_key не нужен (ADC-аутентификация)
# 2. Если локально — читать из env
api_key = os.getenv("ANTIGRAVITY_API_KEY")
config = LocalAgentConfig(
    system_instructions=profile.system_instructions,
    capabilities=capabilities,
    model=selected_model,
    policies=[policy.allow_all()],
    vertex=True,                          # Google Cloud (Gemini Enterprise)
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    # api_key=api_key,  # только для локального режима без vertex
)
```

**Проверка Vertex-режима:**
```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT=<project-id>
export GOOGLE_CLOUD_LOCATION=us-central1
```

### Фаза 1: Asana как трекер (1 день)

У пользователя есть Asana Free — используем её как Kaneo-замену (control plane).

**Паттерн (из Symphony):**
- Asana = source of truth (доска, статусы, acceptance criteria)
- Наш FastAPI = диспетчер (Symphony-замена)
- Агенты действуют только на активных статусах

**Интеграция:**
1. **Asana Personal Access Token** → `ASANA_TOKEN` в `.env`
2. **Webhook уже есть** в `api.py` (`POST /webhook/asana`) — доработать:
   - При создании задачи → `queued`
   - При смене статуса на `In Progress` → `in_progress`
   - При смене на `Rework` → `rework`
3. **Обратная запись** (notifier):
   - PR открыт → комментарий в Asana с ссылкой
   - Тесты прошли → статус `In Review`
   - Merge → статус `Done`

**Схема статусов Asana ↔ TaskStore:**
```
Asana: To Do        → TaskStore: queued
Asana: In Progress  → TaskStore: in_progress
Asana: In Review    → TaskStore: review
Asana: Rework       → TaskStore: rework
Asana: Done         → TaskStore: done
```

### Фаза 2: Параллельность (1-2 дня)

**Celery воркеры:**
```bash
celery -A tasks worker --concurrency=4 --loglevel=info
```

**Ограничение параллельности (из Symphony):**
- Global limit: максимум 4 активных задачи
- Per-project limit: максимум 2 задачи на проект
- Exponential backoff при ретраях

**Worktrees:** каждая задача в своей папке `~/.worktrees/task-<id>` (уже есть).

### Фаза 3: QA-агент (2-3 дня)

**Паттерн borodutch:** Codex Computer Use для браузерного QA.

**Наша замена:**
- Antigravity SDK + Playwright (skill `browser-automation`)
- QA-агент открывает PR, проверяет реальный UI, скриншоты
- Результат → `review` → `done` или `rework`

### Фаза 4: Мульти-проект (3-5 дней)

**Реестр проектов (как в Symphony):**
```yaml
# projects.yaml
projects:
  - slug: voicy
    repo_url: "https://github.com/user/voicy"
    repo_ref: "main"
    profile: web
  - slug: marketing
    repo_url: "https://github.com/user/marketing"
    repo_ref: "main"
    profile: marketing
```

**Роутинг:** задача → slug проекта → worktree → агент.

## Готовый стек (не писать с нуля)

### Ядро (уже есть в проекте)
- FastAPI + Celery + Redis + TaskStore + worktree_manager + git_workflow + notifier

### Трекер
- **Asana Free** (уже есть у пользователя) — доска, статусы, комментарии
- Альтернатива: **Cline Kanban** (`npm i -g kanban`) — браузерная доска для параллельных агентов с worktree, dependency chains, diff review

### Исполнители (агенты)
- **Antigravity SDK** (уже есть) — основной исполнитель
- **Cline CLI** (`npm i -g cline`) — альтернативный исполнитель, headless режим
- **OpenHands** (`All-Hands-AI/OpenHands`) — автономный AI software engineer (68K stars, SWE-Bench 72%)
- **OpenCode** (`opencode-ai/opencode`) — Go-терминальный агент (95K stars, 75+ моделей)

### Оркестрация
- **Symphony** (`backmeupplz/symphony`) — эталонная архитектура диспетчера (Elixir, но SPEC.md language-agnostic)
- **Cline Kanban** — готовая доска для параллельных агентов
- **Enderfga/claw-orchestrator** — обёртка для Antigravity CLI (мульти-агент)

### Облако
- **Google Cloud $300 триал** — Vertex AI / Gemini Enterprise Agent Platform
- **Antigravity SDK с `vertex=True`** — агенты в облаке

## Бюджет

| Ресурс | Стоимость | Стратегия |
|---|---|---|
| Google Cloud триал | $300 / 90 дней | Gemini API через Vertex |
| Antigravity AI Pro | уже есть | локальные задачи |
| Antigravity AI Ultra | $100-200/мес | только если упрёмся в лимиты |
| Asana Free | $0 | трекер |
| Cline Kanban | $0 (open source) | доска |

**Стратегия экономии:**
- Gemini 3.5 Flash для простых задач ($0.30/M input)
- Gemini 3.1 Flash-Lite для тривиальных ($0.25/M input)
- Gemini 3.1 Pro только для сложных ($2/M input)
- $300 триал = ~4 метра биллинга при активной разработке

## Риски

- $300 триал быстро уходит — мониторить billing alerts
- Antigravity SDK молодой (v0.1.7) — API может меняться
- Параллельные агенты в одном репо конфликтуют — worktrees решают (уже есть)
- Asana Free имеет rate limits — кэшировать статусы в TaskStore

## Следующие шаги (чек-лист)

- [ ] Починить баг `api_key` в `agent.py` + добавить `vertex=True`
- [ ] Настроить Google Cloud: проект, billing, ADC
- [ ] Доработать Asana webhook в `api.py`
- [ ] Добавить обратную запись статусов в Asana (notifier)
- [ ] Запустить Celery worker `--concurrency=4`
- [ ] Проверить: задача из Asana → код → PR → статус в Asana
- [ ] Добавить QA-агента (Playwright)
- [ ] Создать `projects.yaml` для мульти-проекта