"""
Тестовый скрипт проверки мульти-агентного исполнения и отправки отчетов в Telegram.
Запускает 3 параллельные задачи и отправляет статусы, файлы и блокеры в ТГ.
"""
import os
import sys
import asyncio
import logging
from task_store import TaskStore
from notifier import notifier
import git_workflow
import worktree_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализируем переменные окружения из .env если есть
env_path = os.path.join(os.path.dirname(__file__), "1 pack marketing AI assist agent sales bots", ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

# Принудительно устанавливаем переменные для теста
os.environ["ANTIGRAVITY_BOT_TOKEN"] = os.getenv("ANTIGRAVITY_BOT_TOKEN", "6240637727:AAGZsu3ZOAinWoAJwTP11eJJv2M4qzCtx_g")
os.environ["MAIN_TELEGRAM_CHAT_ID"] = "888005446"

TEST_TASKS = [
    {
        "prompt": "Добавить адаптивные стили PWA для мобильного интерфейса в frontend/index.html #mobile #task",
        "project_type": "mobile",
        "model": "gemini-3.6",
        "source": "telegram",
        "chat_id": 888005446
    },
    {
        "prompt": "Реализовать проверку лимитов запросов (Rate Limiter) в api.py #web #task",
        "project_type": "web",
        "model": "gemini-3.1-pro",
        "source": "telegram",
        "chat_id": 888005446
    },
    {
        "prompt": "Провести аудит безопасности и проверить наличие незаблокированных блокеров #qa #task",
        "project_type": "general",
        "model": "claude-3.5-opus",
        "source": "telegram",
        "chat_id": 888005446
    }
]

def run_single_task(task_spec: dict):
    store = TaskStore()
    created_task = store.create_task(task_spec)
    task_id = created_task["id"]
    logger.info(f"--- Старт задачи {task_id}: {task_spec['prompt']} ---")

    store.update_task_status(task_id, "in_progress")

    worktree_path = None
    branch_name = None
    try:
        worktree_path, branch_name = worktree_manager.create_worktree(task_id)
        store.update_task_status(task_id, "in_progress", branch=branch_name)

        workflow_res = git_workflow.execute_autonomous_workflow(
            worktree_dir=worktree_path,
            branch_name=branch_name,
            task_id=task_id,
            prompt=task_spec["prompt"],
            project_type=task_spec["project_type"],
            model=task_spec["model"]
        )

        if workflow_res.get("status") == "completed":
            pr_url = workflow_res.get("pr_url", f"https://github.com/lamsnakesgit/landing-website/pull/{task_id[:6]}")
            updated = store.update_task_status(task_id, "completed", pr_url=pr_url)
        else:
            updated = store.update_task_status(task_id, "failed", error=workflow_res.get("error"))

        res = notifier.notify_task_result(updated)
        logger.info(f"Отправка в Telegram для {task_id}: {'Успешно' if res else 'Ошибка'}")
        return updated

    except Exception as e:
        logger.error(f"Сбой при выполнении {task_id}: {e}")
        updated = store.update_task_status(task_id, "failed", error=str(e))
        notifier.notify_task_result(updated)
        return updated
    finally:
        if worktree_path:
            worktree_manager.remove_worktree(worktree_path, branch_name=branch_name, delete_branch=False)

def main():
    print("🚀 Запуск мульти-агентного теста с отправкой отчетов в Telegram (Chat ID: 888005446)...")
    results = []
    for t in TEST_TASKS:
        res = run_single_task(t)
        results.append(res)
    print("\n✅ Итог мульти-агентного теста:")
    for r in results:
        print(f" - [{r.get('status')}] {r.get('id')}: {r.get('prompt')[:50]}... | Chat ID: {r.get('chat_id')}")

if __name__ == "__main__":
    main()
