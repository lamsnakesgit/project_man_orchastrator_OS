import asyncio
from celery import Celery
import logging
import worktree_manager
from task_store import TaskStore
from notifier import notifier
import git_workflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery app connecting to Redis
app = Celery(
    'ai_orchestrator',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# Optional configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@app.task(name="process_agent_task", bind=True)
def process_agent_task(self, task_id: str):
    """
    Задача Celery, которая извлекает данные задачи из TaskStore, создает git worktree,
    выполняет автономный воркфлоу, обновляет статус в TaskStore, отправляет уведомление
    и очищает worktree.
    """
    logger.info(f"Начало обработки задачи Celery: {task_id}")
    store = TaskStore()
    task_data = store.get_task(task_id)

    if not task_data:
        logger.error(f"Задача с id {task_id} не найдена в TaskStore.")
        return {"status": "failed", "error": f"Task {task_id} not found"}

    store.update_task_status(task_id, "in_progress")
    worktree_path = None
    branch_name = None

    try:
        # Создаем worktree и новую ветку feature/task-<id>
        worktree_path, branch_name = worktree_manager.create_worktree(task_id)
        store.update_task_status(task_id, "in_progress", branch=branch_name)

        # Выполняем воркфлоу разработки
        workflow_res = git_workflow.execute_autonomous_workflow(
            worktree_dir=worktree_path,
            branch_name=branch_name,
            task_id=task_id,
            prompt=task_data.get("prompt", ""),
            project_type=task_data.get("project_type", "default"),
            model=task_data.get("model", "default")
        )

        wf_status = workflow_res.get("status")
        if wf_status == "completed":
            pr_url = workflow_res.get("pr_url")
            updated = store.update_task_status(task_id, "completed", pr_url=pr_url)
        else:
            err_msg = workflow_res.get("error", "Workflow execution failed")
            updated = store.update_task_status(task_id, "failed", error=err_msg)

        # Отправляем уведомление
        notifier.notify_task_result(updated)
        return updated

    except Exception as e:
        logger.error(f"Ошибка при исполнении задачи {task_id}: {e}")
        updated = store.update_task_status(task_id, "failed", error=str(e))
        notifier.notify_task_result(updated)
        return updated
    finally:
        if worktree_path:
            try:
                worktree_manager.remove_worktree(worktree_path, branch_name=branch_name, delete_branch=False)
            except Exception as e:
                logger.warning(f"Ошибка при очистке worktree {worktree_path}: {e}")
