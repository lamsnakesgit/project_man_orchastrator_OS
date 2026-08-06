# Детальный Анализ Кодовой Базы и Рекомендации по Реализации

> **Проект:** AI Orchestrator OS
> **Рабочая директория субагента:** `.agents/teamwork_preview_explorer_m1_3/`
> **Дата:** 2026-08-06
> **Режим:** Только для чтения (Read-only investigation)

---

## 1. Обзор Кодовой Базы и Текущего Состояния

В ходе детального исследования файлов репозитория `/Users/higherpower/Desktop/1_Active_Projects/2 Ai_agents/1_project_man_orchastrator_OS_` были проанализированы следующие компоненты:

| Файл / Папка | Размер / Строки | Назначение и Текущее Состояние |
|---|---|---|
| `api.py` | 105 строк | FastAPI шлюз с Basic Auth (`ADMIN_USER`/`ADMIN_PASSWORD`), эндпоинтами `POST /tasks`, `GET /tasks/all`, `POST /webhook/telegram` и раздачей статики `frontend/`. Хранилище задач `task_store` исключительно в оперативной памяти (in-memory list). |
| `tasks.py` | 46 строк | Celery-воркер с Redis брокером (`redis://localhost:6379/0`). Содержит таску `process_agent_task`, вызывающую `asyncio.run(run_agent_task(prompt))`. Ответ в Telegram не отправляется (стоит заглушка `logger.info`). |
| `agent.py` | 48 строк | Запуск `google.antigravity` агента (`LocalAgentConfig`, `CapabilitiesConfig(enable_subagents=True)`). Отсутствуют вызовы Git, написание тестов, маршрутизация моделей LiteLLM и создание PR. |
| `frontend/index.html` | 243 строки | Адаптивная Kanban-доска на стеклянном неоморфном дизайне (Колонки: В очереди, В процессе, Готово). Опрашивает `/tasks/all` каждые 5 секунд. Статусы задач не обновляются бэкендом динамически. |
| `docs/DIARY.md` | 22 строки | Дневник разработки с целями, гипотезами и журналом решений (от 2026-08-06). |
| `docs/teamwork_prompt_draft.md` | 41 строка | Черновик ТЗ проекта с требованиями R1-R6 и критериями приемки (Acceptance Criteria). |
| `pyproject.toml` | 16 строк | Зависимости: `fastapi`, `celery`, `redis`, `aiogram`, `google-antigravity`, `python-dotenv`, `uvicorn`. |
| `deploy.sh` | 45 строк | Скрипт деплоя на VPS (151.244.228.104) через `rsync`, Docker Compose (Redis + LiteLLM) и PM2 (`ai-api`, `ai-celery`). |
| `docker-compose.yml` | 31 строка | Контейнеры Redis (7-alpine, порт 6379) и LiteLLM (main-latest, порт 4000). |
| `litellm_config.yaml` | 20 строк | Конфигурация LiteLLM маршрутизатора с моделями `antigravity-pro` (Vertex AI Gemini 1.5 Pro) и фолбэками (`antigravity-pro-backup`, `free-fast`). |

---

## 2. Анализ Требования R3: Автономный Git Workflow и Юнит-Тесты

### 2.1. Требование (Requirement R3)
> После написания кода агент (включая мобильных фронтенд-разработчиков) обязан написать и запустить Unit-тесты. Только при успешном прохождении локальных тестов агент делает коммит, пушит ветку и создает Pull Request (Draft). Вливание в `main` происходит после финального апрува.

### 2.2. Выявленные Зазоры (Gaps)
1. **Отсутствие изоляции в `tasks.py` / `agent.py`**: Задачи Celery выполняются напрямую в текущем рабочей директории без создания `git worktree` и изолированной ветки `feature/task-<id>`.
2. **Отсутствие конвейера написания и запуска тестов**: `agent.py` отправляет только промпт пользователем в `agent.chat(prompt)`. Нет системных инструкций, обязывающих агента создавать юнит-тесты и запускать тест-раннер (`pytest`, `npm test`, `flutter test`).
3. **Отсутствие интеграции с GitHub API / CLI**: Нет логики выполнения `git commit`, `git push` и вызова `gh pr create --draft`.

### 2.3. Рекомендации по Реализации R3

#### Архитектурная схема Worktree + Test + Draft PR:
```
[Celery Worker (tasks.py)]
       │
       ├──> 1. GitWorktreeManager.create_worktree(task_id)
       │    └── Ветка: feature/task-<id> в .worktrees/task-<id>
       │
       ├──> 2. AgentRunner (agent.py) в директории worktree
       │    ├── Агент пишет исходный код
       │    ├── Агент пишет unit-тесты
       │    └── Агент запускает тест-раннер (pytest / npm test / CLI)
       │         └── [Самоисправление при ошибках]
       │
       ├──> 3. Git & GitHub Integration (при успехе тестов)
       │    ├── git add . && git commit -m "feat(task-<id>): ..."
       │    ├── git push origin feature/task-<id>
       │    └── gh pr create --draft --title "..." --body "..."
       │
       └──> 4. GitWorktreeManager.cleanup_worktree(task_id)
```

#### Конкретные шаги реализации:
1. **Модуль `git_manager.py`**:
   - `create_task_worktree(task_id: str) -> str`: исполняет `git worktree add -b feature/task-{task_id} .worktrees/{task_id} main` и возвращает абсолютный путь.
   - `cleanup_worktree(task_id: str)`: исполняет `git worktree remove --force .worktrees/{task_id}` и `git branch -D feature/task-{task_id}` в случае сбоя или завершения.
2. **Инструкции Агенту (`agent.py`)**:
   - Расширить `system_instructions` в `LocalAgentConfig`: Потребовать от агента запуска команды тестов через инструментарий или CLI, разбор вывода консоли и повторные итерации до 100% успеха.
3. **Создание Draft PR (`github_client.py` или `gh` CLI)**:
   - Использовать `subprocess.run(["gh", "pr", "create", "--draft", ...])` или PyGithub / GitHub REST API.
   - Возвращать `pr_url` в отчете о выполнении задачи.

---

## 3. Анализ Требования R5: Омниканальный Прием Задач и Обратная Связь

### 3.1. Требование (Requirement R5)
> Система должна уметь принимать задачи не только из Kanban UI, но и из внешних систем (Telegram через теги, вебхуки из Asana). По завершении задачи (успех или ошибка) агент должен возвращать статус обратно в исходный канал (например, отправлять уведомление в ТГ или менять статус в Asana).

### 3.2. Выявленные Зазоры (Gaps)
1. **В Telegram Webhook (`api.py:77-97`)**:
   - Нет фильтрации и парсинга хештегов (`#task`, `#bug`, `#dev` и т.д.). Любое сообщение из чата ставится в очередь.
   - Нет проверки безопасности Telegram Webhook Secret Token (`X-Telegram-Bot-Api-Secret-Token`).
2. **Отсутствие Asana Webhook**:
   - Эндпоинт `/webhook/asana` полностью отсутствует в `api.py`.
   - Нет обработки Handshake заголовока Asana (`X-Hook-Secret`).
3. **Отсутствие обратного уведомления (Callback Feedback Loop)**:
   - В `tasks.py` строки 39-40 содержат только лог `logger.info(f"Would send result to Telegram chat {chat_id}...")`. Отправка реального сообщения пользователю в Telegram или обновление Asana не реализованы.
4. **Недостаток структуры данных задач**:
   - Объект задачи в `task_store` не содержит полей `source` (`"kanban"`, `"telegram"`, `"asana"`), `source_id`, `pr_url`, `error_message`, `project_type`, `model_name`.

### 3.3. Рекомендации по Реализации R5

#### Схема Омниканальной Интеграции:
```
[ Входные каналы ]
 ├── Kanban UI ──> POST /tasks ─────────────────────┐
 ├── Telegram ───> POST /webhook/telegram (с тегом) ┼─> [ Task Database / Store ]
 └── Asana ──────> POST /webhook/asana ─────────────┘         │
                                                              ▼
                                                   [ Celery Queue & Worker ]
                                                              │
                                                              ▼
                                                    [ Antigravity Agent ]
                                                              │
                                                              ▼
                                                  [ Feedback Dispatcher ]
                                                              │
 ┌────────────────────────────────────────────────────────────┼────────────────────────┐
 ▼                                                            ▼                        ▼
[ Telegram Bot ]                                       [ Asana API ]            [ Kanban UI ]
(Ответ в чат: статус,                                  (Добавление коммента,    (Обновление карточки:
ссылка на Draft PR)                                    смена колонки/поля)      Done / Failed + PR)
```

#### Конкретные шаги реализации:
1. **Парсер Тегов Telegram (`telegram_parser.py`)**:
   - Извлекать хэштеги (например, `#task`, `#bug`, `#mobile`, `#web`) из `message.text`.
   - Игнорировать групповые сообщения без соответствующих тегов.
   - Сохранять `chat_id`, `message_id`, `thread_id` для точного ответа в ветку.
2. **Эндпоинт `/webhook/asana` в `api.py`**:
   - Обработать первоначальный заголовок подтверждения Asana `X-Hook-Secret`: при получении возвращать его в заголовке ответа.
   - При входящем события создания/изменения таски (с тегом `#ai` или в колонке `To Do`), запрашивать детали через Asana REST API (`https://app.asana.com/api/1.0/tasks/{task_gid}`).
3. **Диспетчер Обратной Связи (`notifier.py`)**:
   - **Для Telegram**: Использовать `aiogram` Bot или `httpx.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage")` с HTML/Markdown форматированием статуса, результатов тестов и ссылки на Draft PR.
   - **Для Asana**: Отправлять POST запрос на `https://app.asana.com/api/1.0/tasks/{task_gid}/stories` с текстом отчета агента и ссылкой на Pull Request.

---

## 4. Сводка Рекомендуемых Изменений в Файлах Проекта

| Файл | Рекомендуемые измененния / Новые модули |
|---|---|
| `api.py` | Добавить валидацию и парсинг тегов в `/webhook/telegram`, добавить `/webhook/asana` (с Handshake), расширить модель `TaskRequest` полями `source`, `project_type`, `priority`, `model`. |
| `tasks.py` | Интегрировать `GitWorktreeManager` для создания ветки перед вызовом агента, вызыват `notifier.dispatch()` для отправки результатов в Telegram / Asana по завершении таски. |
| `agent.py` | Добавить настройку целевой директории (worktree), системный промпт с требованием юнит-тестов и их автономного запуска, интеграцию с LiteLLM моделями. |
| `git_manager.py` *(Новый)* | Модуль управления `git worktree` (создание, удаление, коммит, пуш, создание Draft PR через CLI `gh`). |
| `notifier.py` *(Новый)* | Модуль отправки уведомлений в Telegram (`aiogram`) и Asana (`httpx`). |
| `db.py` / `models.py` *(Новый)* | Замена `task_store` в оперативной памяти на SQLite / Redis / Pydantic хранилище с персистентностью. |
| `frontend/index.html` | Добавление отображения источников задач (Telegram, Asana), ссылок на Pull Request и фильтрации. |

---
*Документ подготовлен субагентом Explorer (m1_3) в соответствии с правилами проекта.*
