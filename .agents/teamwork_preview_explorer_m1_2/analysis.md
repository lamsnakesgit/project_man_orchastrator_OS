# Анализ кодовой базы AI Orchestrator (Milestone 1 — Subagent Explorer 2)

## 1. Введение и область исследования

Данный отчет содержит результаты детализированного исследования кодовой базы проекта AI Orchestrator (`/Users/higherpower/Desktop/1_Active_Projects/2 Ai_agents/1_project_man_orchastrator_OS_`).

Объект исследования:
1. Ключевые файлы: `tasks.py`, `api.py`, `docker-compose.yml`, `deploy.sh`, а также `agent.py`, `litellm_config.yaml`, `pyproject.toml`.
2. **Требование R1**: Конвейер выполнения задач Celery-воркерами (Celery workers task execution flow) и интеграция с Antigravity SDK.
3. **Требование R2**: Изолированное выполнение задач агентами с использованием `Git Worktrees` и веток `feature/task-<id>`.

---

## 2. Детальный разбор существующих файлов

### 2.1. `tasks.py`
- **Назначение**: Конфигурация Celery-приложения и определение задач воркера.
- **Текущее состояние**:
  - Строки 10-14: Celery инициализируется с мостом Redis: `broker='redis://localhost:6379/0'`, `backend='redis://localhost:6379/0'`.
  - Строки 25-46: Определение задачи `@app.task(name="process_agent_task", bind=True) def process_agent_task(self, prompt: str, chat_id: int = None)`.
  - Внутренняя логика: запускает асинхронную функцию агента через `asyncio.run(run_agent_task(prompt))`.
  - Заглушка Telegram (строки 39-40): статус выполнения не отправляется в Telegram, а только логируется: `logger.info(f"Would send result to Telegram chat {chat_id}...")`.
  - Обработка ошибок (строка 45): выполняет повтор `self.retry(exc=e, countdown=10, max_retries=3)`.
- **Проблемы/Пропуски**:
  - Отсутствует передача метаданных задачи (ID, модель, тип проекта, ветка).
  - Отсутствует механизм обновления статусов задачи (Queued -> Running -> Testing -> Completed/Failed) в едином хранилище.
  - Отсутствует инициализация изолированного окружения Git Worktree перед вызовом `run_agent_task`.

### 2.2. `api.py`
- **Назначение**: FastAPI бэкенд шлюз (API Gateway) и Webhook обработчик.
- **Текущее состояние**:
  - Строки 24-42: Реализована Basic Auth авторизация по `ADMIN_USER` и `ADMIN_PASSWORD` (исключение — `/webhook/telegram`).
  - Строки 50: Хранилище задач `task_store = []` размещено в оперативной памяти FastAPI процесса.
  - Строки 54-68: Эндпоинт `POST /tasks` генерирует `task_id = str(uuid.uuid4())` и отправляет асинхронную задачу Celery через `process_agent_task.apply_async(...)`.
  - Строки 70-75: Эндпоинт `GET /tasks/all` возвращает локальный массив `task_store`.
  - Строки 77-97: Эндпоинт `POST /webhook/telegram` принимает сообщения из Telegram и ставит их в очередь Celery.
- **Проблемы/Пропуски**:
  - Хранилище `task_store` находится в памяти FastAPI и **не синхронизируется** с Celery-воркером. После отправки задачи статус в `task_store` навечно остается `"queued"`.
  - Нет интеграции с Redis Key-Value или реляционной базой данных для отслеживания состояний задач.

### 2.3. `agent.py`
- **Назначение**: Обертка над `google.antigravity` SDK для инициализации агента.
- **Текущее состояние**:
  - Строки 7-47: Функция `async def run_agent_task(prompt: str) -> str`.
  - Настройка возможностей (строка 21): `capabilities = types.CapabilitiesConfig(enable_subagents=True)`.
  - Инициализация агента (строки 29-37): создается `LocalAgentConfig` с базовой системной инструкцией.
  - Запуск диалога (строка 44): `response = await agent.chat(prompt)`.
- **Проблемы/Пропуски**:
  - Выбор модели (например, `antigravity-pro`, `claude-3.5-opus`, `gemini-3.5`) закомментирован и не параметризован.
  - Проксирование через LiteLLM (`localhost:4000`) описано только в комментариях.
  - Функция не принимает аргумент `working_dir` и выполняется в текущей рабочей директории процесса.

### 2.4. `docker-compose.yml`
- **Назначение**: Запуск вспомогательных сервисов инфраструктуры (Redis и LiteLLM).
- **Текущее состояние**:
  - Redis: запущен на порту `6379` с постоянным томом `redis_data`.
  - LiteLLM: запущен на порту `4000` (`ghcr.io/berriai/litellm:main-latest`), смонтированы `litellm_config.yaml` и `vertex_sa.json`.
- **Оценка**: Конфигурация корректна для обеспечения локального LLM-маршрутизатора и брокера сообщений Celery.

### 2.5. `deploy.sh`
- **Назначение**: Скрипт автоматического деплоя на VPS (`151.244.228.104`).
- **Текущее состояние**:
  - Строка 12: Синхронизация файлов через `rsync` с исключениями `--exclude '.venv' --exclude '__pycache__' --exclude '.git'`.
  - Строки 18-42: На VPS запускаются Docker Compose (Redis + LiteLLM), `uv sync`, и сервисы PM2 (`ai-api` и `ai-celery`).
- **КРИТИЧЕСКАЯ ПРОБЛЕМА для R2**:
  - Флаг `--exclude '.git'` при синхронизации на VPS приводит к тому, что в директории `/opt/ai_orchestrator/` **отсутствует папка `.git`**.
  - Любые команды Git (`git worktree add`, `git checkout`, `git commit`) на VPS будут завершаться ошибкой `fatal: not a git repository`.

---

## 3. Анализ выполнения Требования R1 (Celery Workers Task Execution Flow)

### Текущий поток выполнения (Current Flow):
1. Клиент / Telegram отправляет запрос на `POST /tasks` или `POST /webhook/telegram`.
2. `api.py` создаёт UUID `task_id` и ставит задачу в Redis через `process_agent_task.apply_async`.
3. Celery-воркер подхватывает задачу и вызывает `asyncio.run(run_agent_task(prompt))`.
4. Агент `google.antigravity` выполняет запрос в контексте рабочей директории воркера.
5. Результат возвращается в Celery result backend.

### Зафиксированные недостатки R1:
1. **Отсутствие передачи контекста**: В задачу Celery передается только `prompt` и `chat_id`. Не передаются `model_name`, `project_type`, `repo_url`, `priority`.
2. **Отсутствие обратной связи (Life-cycle state updates)**: Статусы задачи не обновляются на этапе выполнения.
3. **Отсутствие отправки в Telegram**: В `tasks.py` строки 39-40 содержат лишь `logger.info`, реальная отправка через Telegram Bot API отсутствует.
4. **Ненастроенный LiteLLM proxy**: SDK Antigravity по умолчанию не направляет запросы через LiteLLM (`localhost:4000`).

---

## 4. Анализ выполнения Требования R2 (Isolated Execution using Git Worktrees)

### Текущее состояние R2:
- В кодовой базе **полностью отсутствует** логика управления `git worktree`.
- Все воркеры выполняют задачи в корневой директории приложения `/opt/ai_orchestrator`, что при параллельном запуске нескольких воркеров приведет к конфликтам файлов и сбоям.

### Необходимые архитектурные изменения для R2:
1. **Создание модуля управления Git Worktree (`worktree_manager.py`)**:
   - Формирование имени ветки: `feature/task-<task_id>`.
   - Создание директории воркстри: `git worktree add ./worktrees/task-<task_id> -b feature/task-<task_id> main`.
   - Изолированный запуск агента с установкой рабочей директории `cwd=./worktrees/task-<task_id>`.
   - Очистка/удаление воркстри после завершения задачи: `git worktree remove --force ./worktrees/task-<task_id>`.
2. **Исправление процесса деплоя (`deploy.sh`)**:
   - Удаление `--exclude '.git'` из rsync или инициализация/клонирование git-репозитория на VPS.
   - Настройка Git credentials (`user.name`, `user.email`, SSH-ключ / GitHub Token) на VPS для выполнения push и создания PR.

---

## 5. Сводный список проблем и рекомендаций

| Компонент | Выявленная проблема | Рекомендация по исправлению |
|---|---|---|
| `deploy.sh` | `--exclude '.git'` лишает VPS git-репозитория | Синхронизировать `.git` или клонировать репозиторий на VPS |
| `tasks.py` | Нет управления Git Worktree | Добавить создание worktree перед запуском агента и teardown после |
| `tasks.py` / `agent.py` | Нет динамического выбора моделей LiteLLM | Передавать `model` в аргументах задачи и конфигурировать `LocalAgentConfig` / base_url |
| `api.py` | `task_store` в памяти процесса не обновляется воркером | Использовать Redis для хранения состояний задач (`task:<id>`) |
| `tasks.py` | Telegram сообщение не отправляется | Интегрировать отправку через `httpx` / `aiogram` в Celery task |

