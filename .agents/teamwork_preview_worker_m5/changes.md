# Изменения Milestone 5: Omnichannel Task Ingestion & Feedback Dispatcher

## Созданные файлы

1. **`notifier.py`**:
   - Класс `Notifier` для отправки обратной связи инициатору задачи в различных платформах.
   - Метод `send_telegram_notification(chat_id: int, message: str, pr_url: str = None)`: отправляет сообщение в Telegram через Bot API (`TELEGRAM_BOT_TOKEN`).
   - Метод `send_asana_notification(task_gid: str, comment: str)`: отправляет комментарий в Asana через Asana API (`ASANA_ACCESS_TOKEN`).
   - Метод `notify_task_result(task_data: dict)`: маршрутизирует результаты выполнения задачи на основе источника (`telegram`, `asana`, `ui`).

2. **`git_workflow.py`**:
   - Модуль и функция `execute_autonomous_workflow(...)` для автономного запуска разработки, прогона тестов, коммита и создания PR.

3. **`tests/test_api_and_notifier.py`**:
   - Полный набор модульных тестов, проверяющих:
     - Фильтрацию и парсинг тегов Telegram (`#task`, `#bug`, `#feature`, типа проекта `#mobile`/`#web` и модели `#gpt-4o`/`#gemini-1.5-pro` и т.д.).
     - Рукопожатие вебхука Asana (заголовок `X-Hook-Secret`).
     - Обработку событий Asana и создание задач в `TaskStore`.
     - Интеграцию `TaskStore` с API-эндпоинтами (`/tasks`, `/tasks/all`, `/tasks/{task_id}`).
     - Маршрутизацию уведомлений в `Notifier` (`telegram`, `asana`, `ui`).

## Обновленные файлы

1. **`api.py`**:
   - Модель `TaskRequest` обновлена опциональными полями `model` и `project_type`.
   - `task_store` переведен на полноценный экземпляр `TaskStore()`.
   - В обход аутентификации добавлен эндпоинт `/webhook/asana` наряду с `/webhook/telegram`.
   - Обновлен POST `/tasks`: сохранение задачи в `TaskStore` и передача `task_id` в Celery задачу `process_agent_task`.
   - Обновлен POST `/webhook/telegram`: проверка сообщений на теги `#task`, `#bug`, `#feature`, извлечение типа проекта и модели, создание задачи в `TaskStore` и постановка в Celery.
   - Добавлен POST `/webhook/asana`: обработка рукопожатия `X-Hook-Secret`, парсинг событий Asana, сохранение в `TaskStore` и запуск Celery.
   - Обновлены GET `/tasks/all` и GET `/tasks/{task_id}` для работы с `TaskStore`.

2. **`tasks.py`**:
   - Рефакторинг `process_agent_task`: принимает `task_id: str`.
   - Получение данных задачи из `TaskStore`, обновление статуса на `in_progress`.
   - Создание изолированного git worktree через `worktree_manager.create_worktree(task_id)` для ветки `feature/task-<id>`.
   - Вызов `git_workflow.execute_autonomous_workflow(...)`.
   - Обновление статуса в `TaskStore` (`completed` с `pr_url` или `failed` с `error`).
   - Отправка уведомления через `notifier.notify_task_result(task_data)`.
   - Гарантированная очистка worktree в блоке `finally` через `worktree_manager.remove_worktree(...)`.
