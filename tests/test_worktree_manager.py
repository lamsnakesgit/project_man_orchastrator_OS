import os
import sys
import subprocess
import tempfile
import unittest

# Добавляем корневую директорию проекта в sys.path для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from worktree_manager import ensure_git_repo, create_worktree, remove_worktree

class TestWorktreeManager(unittest.TestCase):
    """
    Модульные тесты для модуля управления git worktree.
    """

    def setUp(self):
        # Создаем временную директорию для изолированных тестов git
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ensure_git_repo(self):
        """
        Проверка автоматической инициализации git репозитория и создания начального коммита.
        """
        ensure_git_repo(self.base_dir)
        git_dir = os.path.join(self.base_dir, ".git")
        self.assertTrue(os.path.exists(git_dir), "Папка .git должна существовать")
        
        # Проверяем наличие коммита HEAD
        res = subprocess.run(
            ["git", "-C", self.base_dir, "rev-parse", "HEAD"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, "HEAD коммит должен быть доступен")

    def test_create_worktree(self):
        """
        Проверка создания git worktree и соответствующей ветки.
        """
        task_id = "test-task-1"
        worktree_path, branch_name = create_worktree(task_id, base_dir=self.base_dir)
        
        self.assertEqual(branch_name, f"feature/task-{task_id}")
        self.assertTrue(os.path.exists(worktree_path), "Директория worktree должна быть создана")
        self.assertTrue(os.path.isdir(worktree_path))

        # Проверяем, что ветка существует в git
        res = subprocess.run(
            ["git", "-C", self.base_dir, "show-ref", "--verify", f"refs/heads/{branch_name}"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, "Ветка должна быть зарегистрирована в git")

    def test_remove_worktree_keep_branch(self):
        """
        Проверка удаления worktree с сохранением ветки.
        """
        task_id = "test-task-2"
        worktree_path, branch_name = create_worktree(task_id, base_dir=self.base_dir)
        self.assertTrue(os.path.exists(worktree_path))

        remove_worktree(worktree_path, branch_name=branch_name, delete_branch=False, base_dir=self.base_dir)
        self.assertFalse(os.path.exists(worktree_path), "Директория worktree должна быть удалена")

        # Ветка все еще должна существовать
        res = subprocess.run(
            ["git", "-C", self.base_dir, "show-ref", "--verify", f"refs/heads/{branch_name}"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, "Ветка должна сохраниться")

    def test_remove_worktree_delete_branch(self):
        """
        Проверка удаления worktree с полным удалением ветки.
        """
        task_id = "test-task-3"
        worktree_path, branch_name = create_worktree(task_id, base_dir=self.base_dir)
        self.assertTrue(os.path.exists(worktree_path))

        remove_worktree(worktree_path, branch_name=branch_name, delete_branch=True, base_dir=self.base_dir)
        self.assertFalse(os.path.exists(worktree_path), "Директория worktree должна быть удалена")

        # Ветка должна быть удалена
        res = subprocess.run(
            ["git", "-C", self.base_dir, "show-ref", "--verify", f"refs/heads/{branch_name}"],
            capture_output=True,
            text=True
        )
        self.assertNotEqual(res.returncode, 0, "Ветка должна быть удалена")

if __name__ == "__main__":
    unittest.main()
