# Гайд: Автономная разработка с Symphony + Kaneo + Cline

Проект: 1_project_man_orchastrator_OS_
Завершённость: [███████░░░░░] 45% — setup guide

## Короткий вывод

Скачали готовый диспетчер **Symphony** от backmeupplz (тот самый, что у бородача в статье про Voicy) — он уже умеет работать с **Kaneo** трекером из коробки. Не выдумываем свой диспетчер и свой трекер.

## Что скачано и где лежит

| Компонент | Что это | Путь |
|---|---|---|
| **Symphony** | Диспетчер задач (Elixir) | `symphony/` |
| **Kaneo** | Self-hosted Kanban трекер | docker-compose → kaneo |
| **Наш проект** | FastAPI + Celery (для CLI-агентов) | корень проекта |

## Шаг 1: Поднять Kaneo (трекер задач)

Kaneo уже добавлен в `docker-compose.yml`. Запуск:

```bash
export KANEO_DB_PASSWORD=$(openssl rand -hex 16)
export KANEO_AUTH_SECRET=$(openssl rand -hex 32)
docker compose up -d kaneo kaneo-postgres
```

Открыть `http://localhost:5173` — создать аккаунт, проект, колонки:

Колонки Kaneo (как в WORKFLOW.md у Symphony):
- `planned` (бэклог — не трогаем)
- `to-do`
- `in-progress`
- `in-review`
- `testing`
- `rework`
- `done`

Потом получить API-ключ (в настройках Kaneo).

## Шаг 2: Запустить Symphony (диспетчер)

Symphony скачан в `symphony/`. Установка (нужен Elixir + mise):

```bash
cd symphony/elixir
# Установить mise если нет: curl https://mise.jdx.dev/install.sh | sh
mise trust && mise install
mise exec -- mix setup
mise exec -- mix build
```

Создать свой `WORKFLOW.md` (копия из `symphony/elixir/WORKFLOW.md`) с конфигом:

```yaml
tracker:
  kind: kaneo
  endpoint: "http://localhost:5173/api"   # адрес Kaneo
  api_key: "$KANEO_API_KEY"               # твой ключ
  project_id: "$KANEO_PROJECT_ID"         # ID проекта в Kaneo
  active_states:
    - to-do
    - in-progress
    - rework
  terminal_states:
    - done
polling:
  interval_ms: 5000
workspace:
  root: ~/code/symphony-workspaces
hooks:
  after_create: |
    git clone --depth 1 "$SOURCE_REPO_URL" .  # клонируем нужный репо
agent:
  backend: claude           # или codex
  max_concurrent_agents: 4
  max_turns: 20
claude:
  command: claude
  model: claude-opus-4-8
  effort: high
  permission_mode: bypassPermissions
  env_file: ~/.config/symphony/anthropic.env
```

Запуск:

```bash
export KANEO_API_KEY=...
export KANEO_PROJECT_ID=...
mise exec -- ./bin/symphony ./WORKFLOW.md
```

Symphony сам следит за Kaneo, клонирует репо в worktree, запускает агента, шлёт PR, обновляет статусы.

## Шаг 3: Исполнитель — Cline (вместо Antigravity SDK)

Тебе не нужен Antigravity SDK — он платный и для него нужен API-ключ. У тебя уже есть подписка Google Pro, и её можно использовать через Cline/Claude Code.

**Cline CLI** — open-source, работает с любыми моделями через API-ключи:

```bash
npm i -g @cline/cli  # или cline
```

В Cline задаёшь провайдера (Google, Anthropic, OpenAI) и ключ. Он умеет:
- писать код автономно
- запускать тесты
- git commit + push
- открывать PR

**Альтернатива: Claude Code** — тот самый `claude` бэкенд у Symphony:
```bash
npm i -g @anthropic-ai/claude-code
```

## Шаг 4: Подключить Cline/Claude Code к Symphony

В `WORKFLOW.md` бэкенд = `claude` (Claude Code) или `codex` (Codex CLI). Оба работают локально без Antigravity.

Symphony сам запускает агента, даёт ему промпт, следит за PR, обновляет статус в Kaneo.

## Шаг 5: Подключить наш FastAPI (для Telegram)

Наш проект (FastAPI + Celery) можно оставить как Telegram-шлюз:
- Telegram-бот получает команду → создаёт задачу в Kaneo (через API)
- Kaneo → Symphony подхватывает → агент работает
- Результат → Telegram-уведомление

## Что не нужно делать

- ❌ Не пиши свой диспетчер на Python — Symphony уже есть и работает.
- ❌ Не используй Antigravity SDK — платно, нужен ключ.
- ❌ Не выдумывай свой трекер — Kaneo уже есть, бесплатный, self-hosted.

## Твой стек (итого)

| Слой | Решение | Стоимость |
|---|---|---|
| Трекер | Kaneo (docker) | $0 |
| Диспетчер | Symphony (backmeupplz) | $0 |
| Исполнитель | Cline / Claude Code | $0 + подписка ключей |
| Модели | Google Pro (уже есть) / Claude | уже оплачено |
| QA | Playwright (через Cline) | $0 |
| PM | Telegram-бот (наш FastAPI) | $0 |

## Ссылки на готовые решения

- **Symphony**: https://github.com/backmeupplz/symphony
- **Kaneo**: https://github.com/usekaneo/kaneo
- **Cline**: https://github.com/cline/cline
- **Cline Kanban**: https://github.com/cline/kanban
- **Claude Code**: https://github.com/anthropics/claude-code
- **Статья borodutch**: https://blog.borodutch.com/i-rebuilt-voicy-with-agents-instead-of-rewriting-it-myself

## Подводные камни (gotchas)

1. **Symphony — prototype**: README предупреждает, что это prototype для evaluation. Для боевого использования рекомендуют свою реализацию по `SPEC.md`.
2. **Kaneo API**: адрес API и порт могут отличаться — проверять `http://localhost:5173/api` через браузер.
3. **Model в Cline/Claude**: подписка Google Pro — это человеческая подписка, не API-ключ. Для API Gemini нужен `GEMINI_API_KEY` (отдельно).
4. **CLAUDE_CODE_OAUTH**: для Claude Code можно авторизоваться через OAuth (подписка Pro/Max) — тогда не нужен API-ключ Anthropic.