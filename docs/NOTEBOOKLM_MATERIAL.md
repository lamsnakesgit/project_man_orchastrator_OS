# Материал для NotebookLM: Автономная параллельная разработка агентами

Проект: 1_project_man_orchastrator_OS_
Завершённость: [██████░░░░░░] 30% — research material

> ⚠️ MCP-сервер для NotebookLM не подключён в текущей среде (доступны: Tavily, Exa, Context7).
> Этот файл — готовый материал для вставки в NotebookLM (https://notebook.google.com).
> Скопируй содержимое в новый источник NotebookLM.

---

## 1. Ключевая статья (оригинал)

**"I rebuilt Voicy with agents instead of rewriting it myself"** — Nikita Kolmogorov (borodutch)
URL: https://blog.borodutch.com/i-rebuilt-voicy-with-agents-instead-of-rewriting-it-myself/

### Суть статьи
Автор пересобрал свой Telegram-бот Voicy, превратив проект в агентный цикл (agent loop).
Он взаимодействовал с системой как исполнительный директор/PM через Telegram:
говорил OpenClaw что нужно, кидал скриншоты и правки в чат, а система превращала это в:
- задачи Kaneo
- запуски Symphony
- PR от Codex
- QA через Codex Computer Use
- деплои и решения по ревью

### Стек автора
| Компонент | Роль |
|---|---|
| **Kaneo** | бэклог и состояние задач (self-hosted Kanban с API) |
| **Symphony** | следит за Kaneo, роутит задачи в изолированные worktree, запускает Codex |
| **Codex** | scoped-реализация, тесты, коммиты, PR handoff |
| **OpenClaw** | супервизор из Telegram: читает контекст, управляет задачами Kaneo, credentials, QA через Codex Computer Use, деплой, merge |
| **Voicy** | бот-бэкенд + Windows GPU worker (Whisper) |

### Главный цикл
1. Пользователь говорит OpenClaw в Telegram что нужно (часто со скриншотами).
2. OpenClaw исследует, создаёт/обновляет задачи Kaneo, двигает доску.
3. Symphony видит задачи в активных статусах, создаёт изолированные workspace в `~/code/symphony-workspaces`.
4. Codex реализует только в склонированном репо.
5. Codex оставляет workpad и открывает обычный GitHub PR с валидацией и тестами.
6. OpenClaw мониторит review-ready работу, проверяет PR, гоняет недостающее ручное QA через Codex Computer Use, merge или отправляет на rework, деплоит, верифицирует, двигает задачу к done.

### 11 правил копирования паттерна
1. Выбери реальный бэклог (Kaneo, GitHub Issues, Linear — любой с API и статусами).
2. Сделай состояние задачи авторитетным (какие статусы исполняемые, какие review-only, какой терминальный).
3. Дай каждому проекту repo metadata: URL, base ref, slug, repo keys для multi-repo.
4. Создавай изолированные workspace: одна задача = одна папка = одна ветка.
5. Запускай кодинг-агента с узким контрактом (issue, repo scope, validation requirements).
6. Требуй workpad и PR handoff (что изменено, что запущено, что прошло, что заблокировано).
7. Отделяй автоматическую валидацию от реального QA (браузер, Telegram, платежи, GPU — нужны явные доказательства).
8. Кастомизируй runner под свои статусы, топологию репо, QA, permissions, деплой.
9. Держи credentials вне репо (password manager / secret store).
10. Автоматизируй watchdogs: stuck runners, retrying jobs, stale workers, pending queues.
11. Превращай блокеры в работу: найденная проблема = следующая задача, а не встреча.

### Уроки автора
- "Промпт — не источник истины. Доска — источник истины."
- "AI достаточно хорош, чтобы заменить целую маленькую компанию разработчиков."
- "Следующий прыжок: от управления кодинг-агентами к управлению PM-агентами, которые управляют кодинг-агентами."
- "Человек сдвигается от чтения каждого diff к установке границ, оценке результатов и решению что важно."

---

## 2. Репозитории для изучения

### Официальные / из статьи
- **backmeupplz/symphony** — диспетчер задач: превращает project work в изолированные автономные запуски.
  URL: https://github.com/backmeupplz/symphony
- **backmeupplz/voicy** — Telegram-бот, пересобранный агентами (62 PR за неделю).
  URL: https://github.com/backmeupplz/voicy
- **openclaw/openclaw** — персональный AI-ассистент (PM-слой через Telegram/WhatsApp/Slack).
  URL: https://github.com/openclaw/openclaw

### Оркестраторы (альтернативы Symphony)
- **Enderfga/claw-orchestrator** — рантайм для кодинг-агентов: оборачивает Claude Code, Codex, **Antigravity**, Cursor Agent как persistent-сессии; мульти-агентные советы; Planner/Coder/Reviewer loop.
  URL: https://github.com/Enderfga/claw-orchestrator
