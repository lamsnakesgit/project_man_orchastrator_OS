## 2026-08-06T12:43:13Z
You are a Worker subagent (instance M5).
Your working directory is `.agents/teamwork_preview_worker_m5/`.
Your task is to implement Milestone 5: Omnichannel Task Ingestion & Feedback Dispatcher.

Specific tasks:
1. Create `notifier.py`:
   - Class `Notifier`: Sends feedback to task originator.
   - Method `send_telegram_notification(chat_id: int, message: str, pr_url: str = None)`: Sends Telegram message using Bot API (`TELEGRAM_BOT_TOKEN`).
   - Method `send_asana_notification(task_gid: str, comment: str)`: Posts comment/story to Asana task using Asana API (`ASANA_ACCESS_TOKEN`).
   - Method `notify_task_result(task_data: dict)`: Routes notification based on `task_data.get("source")` (`telegram`, `asana`, `ui`).
2. Update `api.py`:
   - Update `TaskRequest` model to include optional `model` and `project_type` fields.
   - Update `/tasks` (POST) to create task in `TaskStore` and enqueue Celery task `process_agent_task`.
   - Update `/webhook/telegram` (POST):
     - Filter incoming messages: check if text contains `#task`, `#bug`, or `#feature` tags. Ignore untagged text.
     - Extract project_type (e.g. `#mobile`, `#web`) and model tags if present.
     - Create task in `TaskStore` (source="telegram") and enqueue Celery task.
   - Add `/webhook/asana` (POST):
     - Support `X-Hook-Secret` handshake header response (echo header for webhook registration).
     - Process task events from Asana, parse task details, create task in `TaskStore` (source="asana"), and enqueue Celery task.
   - Update `/tasks/all` and `/tasks/{task_id}` to fetch from `TaskStore`.
3. Update `tasks.py`:
   - Refactor `process_agent_task`: Accept `task_id: str`.
   - Retrieve task data from `TaskStore`. Update status to `in_progress`.
   - Call `worktree_manager.create_worktree(task_id)` to create branch `feature/task-<id>` and `.worktrees/task-<id>`.
   - Call `git_workflow.execute_autonomous_workflow(...)`.
   - Update status in `TaskStore` (`completed` with `pr_url` or `failed` with `error`).
   - Call `notifier.notify_task_result(task_data)`.
   - Clean up worktree via `worktree_manager.remove_worktree(...)`.
4. Create tests in `tests/test_api_and_notifier.py` covering Telegram tag parsing, Asana webhook secret handshake, task store integration, and notification routing. Run `.venv/bin/pytest tests/` to verify.
