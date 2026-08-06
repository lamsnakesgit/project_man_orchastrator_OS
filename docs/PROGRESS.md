# Прогресс Проекта (PROGRESS.md)

## ✅ Завершенные Этапы (Completed Milestones)

### 1. Инфраструктура и Бэкенд (Milestone 1-3)
- [x] Разработан бэкенд на FastAPI (`api.py`) с роутингом задач и аутентификацией.
- [x] Реализована гибридная система хранения `TaskStore` (Redis + In-Memory Fallback).
- [x] Создан модуль `worktree_manager.py` для безопасного изолирования агентских задач в отдельные `git worktree` ветки.
- [x] Интегрирован LiteLLM прокси-сервер (`litellm_config.yaml`) для динамического выбора моделей (Claude 3.5 Opus, Gemini 3.1 Pro, Gemini 3.5/3.6).

### 2. Мульти-Агентное Исполнение и Отчетность (Milestone 4)
- [x] Реализована автоматическая омниканальная отправка отчетов в Telegram (`notifier.py`).
- [x] Успешно протестирована параллельная работа 3 субагентов (Mobile Dev, Web Limiter, QA Security Audit).
- [x] Настроен Git Workflow: авто-создание веток (`feature/task-<id>`), запуск unit-тестов в `tests/`, коммиты, пуш и **авто-создание Draft Pull Requests на GitHub**.
- [x] Все отклики, PR-ссылки, созданные файлы и статус блокеров отсылаются прямо в Telegram (Chat ID `888005446`).

### 3. Исследование архитектуры автономной разработки (Milestone 5)
- [x] Изучена статья borodutch "I rebuilt Voicy with agents" — паттерн Kaneo + Symphony + Codex + OpenClaw.
- [x] Исследован Antigravity SDK (`google-antigravity` v0.1.7): `LocalAgentConfig(vertex=True)` для Google Cloud, MCP-интеграция, политики `allow_all()`.
- [x] Подтверждено: текущий проект = 60% стека borodutch (FastAPI + Celery/Redis + TaskStore + worktree + Antigravity SDK + Telegram webhook + Draft PR).
- [x] Составлена архитектура в `docs/ARCHITECTURE.md` — 3 фазы: фикс/запуск, параллельность/трекинг, мульти-проект.

## ✅ Завершенные Этапы (Completed Milestones)

### 4. План автономной разработки + фикс багов (Milestone 6)
- [x] Составлен полный план в `docs/AUTONOMOUS_DEV_PLAN.md`: готовый стек, фазы, трекер, бюджет, риски.
- [x] Починен баг `api_key` в `agent.py` — теперь читается из env + добавлен `vertex=True`.
- [x] Добавлены статусы `review`/`rework` в `TaskStore` для цикла QA.
- [x] Исправлена маршрутизация Asana в `notifier.py` (asana-задачи больше не уходят в Telegram).
- [x] Все 35 тестов проходят.
- [x] Скачан Symphony от backmeupplz (диспетчер, Elixir, с Kaneo-интеграцией).
- [x] Kaneo (self-hosted трекер) добавлен в `docker-compose.yml`.
- [x] Составлен гайд установки `docs/SETUP_GUIDE.md` с реальными ссылками на готовые решения.

## 🚧 Текущие Блокеры (Blockers)
- **Symphony требует Elixir/Erlang** (`mise` + `mix`) — нужно установить на машине.
- **Нет ключей для Cline/Claude Code:** подписка Google Pro / Gemini — это человеческие подписки, не API-ключ. Для Cline нужен `GEMINI_API_KEY` (AI Studio, бесплатный тир) или OAuth через Claude Code.

## 🚀 Следующие Шаги (Next Steps)
1. Поднять Kaneo: `docker compose up -d kaneo kaneo-postgres` → http://localhost:5173 — создать проект и колонки.
2. Установить Symphony: `cd symphony/elixir && mise trust && mise install && mise exec -- mix setup && mise exec -- mix build`.
3. Создать свой `WORKFLOW.md` (по шаблону из `symphony/elixir/WORKFLOW.md`) с endpoint Kaneo.
4. Установить исполнителя: `npm i -g cline` или `npm i -g @anthropic-ai/claude-code`.
5. Подключить Telegram-шлюз: наш FastAPI создаёт задачи в Kaneo, Symphony подхватывает.
6. QA: добавить Playwright-проверку агенту.
7. Деплой на VPS (`151.244.228.104`) через `./deploy.sh` для работы 24/7.
