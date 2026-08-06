# Изменения (Changes Summary) — Worker M2

## Краткое описание проведенных работ
В рамках задачи Milestone 2 (Core Configuration, LiteLLM Model Routing & Project Profiles) были внесены и успешно протестированы следующие изменения:

### 1. `litellm_config.yaml`
- Добавлены алиасы моделей: `claude-3.5-opus`, `gemini-3.1-pro`, `gemini-3.5`, `gemini-3.6`, `antigravity-pro` и `free-fast`.
- Настроены соответствующие параметры провайдеров (`anthropic`, `gemini`, `vertex_ai`) с использованием переменных окружения (`os.environ/ANTHROPIC_API_KEY`, `os.environ/GEMINI_API_KEY`, `os.environ/VERTEX_PROJECT_ID`).
- Настроена стратегия роутинга `usage-based-routing` и правильные резервные маршруты (fallbacks).

### 2. `docker-compose.yml`
- В сервис `litellm` добавлены переменные окружения: `ANTHROPIC_API_KEY`, `VERTEX_PROJECT_ID`, `GEMINI_API_KEY`.
- В сервис `redis` добавлена декларация переменной `REDIS_PORT`.

### 3. `deploy.sh`
- Из команды `rsync` удален флаг `--exclude '.git'`, благодаря чему на VPS сохраняется папка `.git`, необходимая для полноценной работы Git Worktrees.

### 4. `project_profiles.py` (Создан новый модуль)
- Создан класс данных `ProjectProfile` для описания типов проектов.
- Определен реестр профилей `PROJECT_PROFILES`:
  - `web` (модель по умолчанию: `claude-3.5-opus`, тулы: `code_editor`, `browser_automation`, `terminal`, `git_worktree`).
  - `mobile_dev` (модель по умолчанию: `gemini-3.1-pro`, тулы: `code_editor`, `mobile_emulator`, `terminal`, `git_worktree`).
  - `marketing` (модель по умолчанию: `gemini-3.5`, тулы: `web_search`, `content_generator`, `analytics`, `seo_auditor`).
  - `general` (модель по умолчанию: `antigravity-pro`, тулы: `code_editor`, `terminal`, `git_worktree`, `web_search`).
- Реализованы безопасные функции-хелперы `get_project_profile()`, `list_project_profiles()`, `get_default_model()` с поддержкой отката (fallback) на `general`.

### 5. `pyproject.toml`
- В список зависимостей добавлен `pyyaml>=6.0`.

### 6. `tests/test_project_profiles.py` (Создан новый тест-сюит)
- Добавлен набор модульных тестов, проверяющих:
  - Загрузку всех 4 предустановленных профилей.
  - Фолбэк неизвестных имен профилей на `general`.
  - Валидность моделей по умолчанию для каждого профиля.
  - Соответствие всех моделей профилей реальным алиасам в `litellm_config.yaml`.
  - Сериализацию `to_dict()`.

---

## Статус сборки и тестов
- Сборка и тестирование: **УСПЕШНО**
- Команда запуска тестов: `.venv/bin/pytest tests/test_project_profiles.py`
- Результаты: 6 из 6 тестов `test_project_profiles.py` успешно пройдены (всего 16 из 16 тестов проекта пройдены).
