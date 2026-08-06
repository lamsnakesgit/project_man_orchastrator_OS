import os
import subprocess
import shutil
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

def ensure_git_repo(base_dir: str = ".") -> None:
    """
    Проверяет, является ли base_dir действительным git-репозиторием.
    Если нет, инициализирует git-репозиторий и создает начальный коммит.
    """
    abs_base_dir = os.path.abspath(base_dir)
    if not os.path.exists(abs_base_dir):
        os.makedirs(abs_base_dir, exist_ok=True)
    
    # Проверяем, находится ли папка внутри git-репозитория
    res = subprocess.run(
        ["git", "-C", abs_base_dir, "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True
    )
    
    if res.returncode != 0:
        logger.info(f"Инициализация git-репозитория в {abs_base_dir}")
        subprocess.run(["git", "-C", abs_base_dir, "init"], check=True, capture_output=True, text=True)
    
    # Разрешаем работающему пользователю использовать директорию проекта (предотвращает dubiuos ownership 128 на Linux)
    subprocess.run(["git", "config", "--global", "--add", "safe.directory", "*"], capture_output=True)
    subprocess.run(["git", "config", "--global", "--add", "safe.directory", abs_base_dir], capture_output=True)
    subprocess.run(["git", "-C", abs_base_dir, "config", "user.name", "Worker Agent"], capture_output=True)
    subprocess.run(["git", "-C", abs_base_dir, "config", "user.email", "worker@agent.local"], capture_output=True)

    # Проверяем наличие хотя бы одного коммита (HEAD)
    head_check = subprocess.run(
        ["git", "-C", abs_base_dir, "rev-parse", "HEAD"],
        capture_output=True,
        text=True
    )
    if head_check.returncode != 0:
        logger.info(f"Создание начального пустой коммита в {abs_base_dir}")
        subprocess.run(
            ["git", "-C", abs_base_dir, "-c", "user.name=Worker Agent", "-c", "user.email=worker@agent.local", "commit", "--allow-empty", "-m", "Initial commit"],
            capture_output=True,
            text=True
        )

def create_worktree(task_id: str, base_dir: str = ".") -> Tuple[str, str]:
    """
    Создает git-ветку feature/task-<task_id> и git worktree в районе .worktrees/task-<task_id>.
    Возвращает кортеж (worktree_path, branch_name).
    """
    ensure_git_repo(base_dir)
    abs_base_dir = os.path.abspath(base_dir)
    
    worktrees_dir = os.path.join(abs_base_dir, ".worktrees")
    os.makedirs(worktrees_dir, exist_ok=True)
    
    worktree_path = os.path.abspath(os.path.join(worktrees_dir, f"task-{task_id}"))
    branch_name = f"feature/task-{task_id}"
    
    # Проверяем, существует ли уже ветка
    branch_check = subprocess.run(
        ["git", "-C", abs_base_dir, "show-ref", "--verify", f"refs/heads/{branch_name}"],
        capture_output=True,
        text=True
    )
    
    if branch_check.returncode == 0:
        # Ветка существует - добавляем worktree к существующей ветке
        cmd = ["git", "-C", abs_base_dir, "worktree", "add", worktree_path, branch_name]
    else:
        # Ветка не существует - создаем новую ветку при создании worktree
        cmd = ["git", "-C", abs_base_dir, "worktree", "add", "-b", branch_name, worktree_path]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        logger.error(f"Ошибка при создании worktree: {res.stderr}")
        raise RuntimeError(f"Failed to create git worktree: {res.stderr}")
    
    return (worktree_path, branch_name)

def remove_worktree(worktree_path: str, branch_name: Optional[str] = None, delete_branch: bool = False, base_dir: str = ".") -> None:
    """
    Безопасно удаляет git worktree, выполняет prune и при необходимости удаляет ветку.
    """
    abs_base_dir = os.path.abspath(base_dir)
    abs_worktree_path = os.path.abspath(worktree_path)
    
    # Удаляем worktree через git CLI
    res = subprocess.run(
        ["git", "-C", abs_base_dir, "worktree", "remove", "--force", abs_worktree_path],
        capture_output=True,
        text=True
    )
    if res.returncode != 0:
        logger.warning(f"Предупреждение при удалении worktree: {res.stderr}")
    
    # Выполняем очистку устаревших worktree ссылок
    subprocess.run(["git", "-C", abs_base_dir, "worktree", "prune"], capture_output=True, text=True)
    
    # Удаляем директорию с файловой системы, если она осталась
    if os.path.exists(abs_worktree_path):
        shutil.rmtree(abs_worktree_path, ignore_errors=True)
        
    # Удаляем ветку, если затребовано
    if delete_branch:
        target_branch = branch_name
        if not target_branch:
            # Пытаемся извлечь имя ветки из пути worktree (task-<id> -> feature/task-<id>)
            folder_name = os.path.basename(abs_worktree_path)
            if folder_name.startswith("task-"):
                target_branch = f"feature/{folder_name}"
        
        if target_branch:
            logger.info(f"Удаление ветки {target_branch}")
            subprocess.run(["git", "-C", abs_base_dir, "branch", "-D", target_branch], capture_output=True, text=True)
