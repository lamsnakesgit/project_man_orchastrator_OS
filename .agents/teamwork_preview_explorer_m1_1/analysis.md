# Детальный анализ кодовой базы и рекомендации (Milestone M1)

## 1. Общий обзор архитектуры

Проект представляет собой **AI Orchestrator** — автономный конвейер выполнения задач с использованием:
- **FastAPI (`api.py`)** — REST API и Telegram Webhook для приема задач.
- **Celery (`tasks.py`)** — брокер/воркер очередей (через Redis).
- **Google Antigravity SDK (`agent.py`)** — движок AI-агентов.
- **LiteLLM (`litellm_config.yaml`, `docker-compose.yml`)** — локальный прокси для маршрутизации LLM API.
- **Docker Compose & PM2 (`deploy.sh`)** — развертывание на VPS (`151.244.228.104`).

---

## 2. Анализ существующих файлов

### 2.1 `agent.py`
- **Текущее состояние**:
  - Реализует `run_agent_task(prompt: str) -> str`.
  - Использует `google.antigravity` (`Agent`, `LocalAgentConfig`, `types.CapabilitiesConfig`).
  - Жестко зашитая системная инструкция ("You are an autonomous AI Orchestrator Worker...").
  - Закомментирована строка вызова модели (`# model="models/gemini-1.5-pro"`).
  - Принимает только `prompt`. Не поддерживает динамическую передачу `model`, `project_type`, `worktree_path`, `tools`.
- **Проблемы и узкие места**:
  - Отсутствует гибкая настройка эндпоинта LiteLLM proxy (не переопределен base_url / API-ключи для локального LiteLLM `http://localhost:4000`).
  - Нет разделения на типы проектов (R6) и наборы инструментов.
  - Нет возможности передавать выбор модели (R4).

### 2.2 `litellm_config.yaml`
- **Текущее состояние**:
  - Содержит базовую конфигурацию с устаревшими именами моделей (`antigravity-pro` -> `vertex_ai/gemini-1.5-pro`, `antigravity-pro-backup` -> `gemini/gemini-1.5-pro`, `free-fast` -> `gemini/gemini-1.5-flash`).
- **Проблемы и узкие места**:
  - Отсутствуют модели согласно Требованию R4:
    - `claude-3.5-opus` (Anthropic API / Bedrock / Vertex).
    - `gemini-3.1-pro` (Gemini Pro актуальной версии).
    - `gemini-3.5` / `gemini-3.6` (Быстрые кодинг-модели, e.g. Gemini Flash 2.0 / 1.5).
  - Не настроены aliases и переменные окружения для Anthropic API key (`ANTHROPIC_API_KEY`).

### 2.3 `pyproject.toml` & `.python-version` & `.venv`
- **Текущее состояние**:
  - Python version: `3.12` (совместима со всеми библиотеками).
  - Зависимости: `aiogram>=3.30.0`, `celery>=5.6.3`, `fastapi>=0.141.1`, `google-antigravity>=0.1.10`, `python-dotenv>=1.2.2`, `redis>=8.1.0`, `uvicorn>=0.52.1`.
- **Проблемы и узкие места**:
  - Нет прямых библиотек для работы с Git (например, `GitPython` или вызов `git worktree` через `subprocess`).
  - Для поддержки Anthropic в LiteLLM Docker не требуется менять python dependencies backend'а, но для вызова Telegram уведомлений или Git операторов нужно расширить сервисную слой-логику.

### 2.4 `tasks.py` & `api.py`
- **Текущее состояние**:
  - `tasks.py`: Celery-задача `process_agent_task(prompt, chat_id)` запускает `asyncio.run(run_agent_task(prompt))`.
  - `api.py`: FastAPI эндпоинт `POST /tasks` принимает `TaskRequest(prompt, chat_id, priority)`.
- **Проблемы и узкие места**:
  - Сигнатуры функций не принимают `model` и `project_type`.
  - Воркер Celery не передает промежуточные статусы задачи (например: "Создание git worktree", "Запуск агента", "Запуск тестов", "Пуш PR").
  - Обратная связь в Telegram содержит только placeholder `logger.info("Would send result...")`.

---

## 3. Анализ Требования R1: Интеграция Celery с `google-antigravity-sdk`

### Наблюдение и задачи:
1. **Синхронный воркер vs Async SDK**:
   - Celery по умолчанию работает в синхронном режиме (`prefork`). Вызов `asyncio.run(run_agent_task(...))` внутри задачи валиден, но при повторных запусках или встроенных асинхронных подзадачах в том же потоке требуется убедиться в правильной изоляции event loop.
2. **Передача контекста задачи**:
   - Celery-воркер должен получать расширенный контекст:
     - `task_id` (UUID)
     - `prompt` (Текст задачи)
     - `project_type` (`web`, `mobile_dev`, `marketing`, `general`)
     - `model` (`claude-3.5-opus`, `gemini-3.1-pro`, `gemini-3.6`)
     - `chat_id` (Для обратной связи в Telegram)
3. **Отслеживание прогресса**:
   - Celery-воркер должен обновлять состояния через `self.update_state(state='PROGRESS', meta={...})` или сохранять их в Redis, чтобы Kanban UI видел реальный статус.

---

## 4. Анализ Требования R4: Маршрутизация моделей и API (LiteLLM)

### Наблюдение и задачи:
1. **Конфигурация LiteLLM (`litellm_config.yaml`)**:
   - Необходимо добавить четкие алиасы моделей:
     ```yaml
     model_list:
       - model_name: claude-3.5-opus
         litellm_params:
           model: anthropic/claude-3-5-sonnet-20241022 # или claude-3-opus-20240229
           api_key: "os.environ/ANTHROPIC_API_KEY"

       - model_name: gemini-3.1-pro
         litellm_params:
           model: gemini/gemini-1.5-pro
           api_key: "os.environ/GEMINI_API_KEY"

       - model_name: gemini-3.6
         litellm_params:
           model: gemini/gemini-2.0-flash-exp # или gemini-1.5-flash
           api_key: "os.environ/GEMINI_API_KEY"

       - model_name: gemini-3.5
         litellm_params:
           model: gemini/gemini-1.5-flash
           api_key: "os.environ/GEMINI_API_KEY"
     ```
2. **Интеграция с `google-antigravity` SDK**:
   - `google-antigravity` SDK отправляет запросы к эндпоинтам Google Gemini.
   - Для перенаправления запросов через LiteLLM Proxy (`http://localhost:4000`), в `agent.py` или окружении процесса воркера необходимо установить:
     - `GEMINI_API_BASE="http://localhost:4000"` (или `http://litellm:4000` в Docker Compose).
     - В `LocalAgentConfig(model=model_name)` передавать выбранную модель (`claude-3.5-opus`, `gemini-3.1-pro`, `gemini-3.6`).

---

## 5. Анализ Требования R6: Поддержка разных типов проектов и динамические тулсеты

### Наблюдение и задачи:
1. **Профили проектов (Project Profiles)**:
   - Создать реестр профилей проектов (например, `project_profiles.py` или JSON/YAML конфигурацию):
     - **`mobile_dev`**:
       - Системная инструкция: "Вы — Mobile Development AI Agent (Android/iOS). Обязательно пишите юнит-тесты и проверяйте сборку."
       - Тулсет / Инструменты: `android-cli`, `xcode-project-setup`, unit-test runner, code search.
     - **`web`**:
       - Системная инструкция: "Вы — Web Development AI Agent (FastAPI/React). Соблюдайте чистую архитектуру, пишите тесты pytest/jest."
       - Тулсет / Инструменты: `browser-automation`, `frontend-design`, `a11y-debugging`, `pytest`.
     - **`marketing`**:
       - Системная инструкция: "Вы — Marketing AI Agent. Анализируйте рынки, создавайте тексты и карусели."
       - Тулсет / Инструменты: `web-search`, `carousel-generator`, `transcript-analyzer`.
2. **Динамическая генерация `LocalAgentConfig`**:
   - `agent.py` на основе `project_type` загружает соответствующую инструкцию, список допустимых инструментов (tools / capabilities) и формирует конфигурацию агента.

---

## 6. Предлагаемая архитектура изменений (Рекомендации для Имплементатора)

### Предложение 1: Модификация `litellm_config.yaml`
```yaml
model_list:
  - model_name: claude-3.5-opus
    litellm_params:
      model: anthropic/claude-3-5-sonnet-20241022
      api_key: "os.environ/ANTHROPIC_API_KEY"

  - model_name: gemini-3.1-pro
    litellm_params:
      model: gemini/gemini-1.5-pro
      api_key: "os.environ/GEMINI_API_KEY"

  - model_name: gemini-3.6
    litellm_params:
      model: gemini/gemini-2.0-flash-exp
      api_key: "os.environ/GEMINI_API_KEY"

  - model_name: gemini-3.5
    litellm_params:
      model: gemini/gemini-1.5-flash
      api_key: "os.environ/GEMINI_API_KEY"

router_settings:
  routing_strategy: usage-based-routing
  fallbacks:
    - {"claude-3.5-opus": ["gemini-3.1-pro"]}
    - {"gemini-3.1-pro": ["gemini-3.6"]}
```

### Предложение 2: Расширение `agent.py`
```python
# Псевдокод / Предложение для agent.py
PROJECT_PROFILES = {
    "web": {
        "instructions": "You are a Web Engineering Agent (FastAPI/React). Write clean code and unit tests.",
        "capabilities": types.CapabilitiesConfig(enable_subagents=True),
    },
    "mobile_dev": {
        "instructions": "You are a Mobile Engineering Agent (Android/iOS). Write unit tests and verify builds.",
        "capabilities": types.CapabilitiesConfig(enable_subagents=True),
    },
    "marketing": {
        "instructions": "You are a Marketing & Content Agent. Analyze target audience and write compelling copy.",
        "capabilities": types.CapabilitiesConfig(enable_subagents=False),
    }
}

async def run_agent_task(prompt: str, model: str = "gemini-3.6", project_type: str = "web", worktree_dir: str = None) -> str:
    profile = PROJECT_PROFILES.get(project_type, PROJECT_PROFILES["web"])
    
    config = LocalAgentConfig(
        system_instructions=profile["instructions"],
        capabilities=profile["capabilities"],
        model=f"models/{model}" # Маршрутизация через LiteLLM Proxy
    )
    
    # Установка рабочей директории в worktree (если передана)
    if worktree_dir:
        os.chdir(worktree_dir)

    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        return await response.text()
```

### Предложение 3: Обновление `tasks.py` и `api.py`
- Добавить поля `model` и `project_type` в `TaskRequest`.
- В Celery-задаче `process_agent_task(prompt, chat_id, project_type, model, task_id)` передавать все параметры в `run_agent_task`.
- Добавить логику обратной связи в Telegram по окончанию выполнения задачи.
