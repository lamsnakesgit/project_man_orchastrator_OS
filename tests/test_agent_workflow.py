"""
Модульное тестирование agent.py и git_workflow.py.
Проверяет инициализацию Antigravity агента, генерацию результатов,
прохождение unit-тестов, гитовые операции и создание Draft PR.
"""

import os
import sys
import shutil
import tempfile
import asyncio
import unittest
import subprocess

# Добавляем корневую директорию проекта в sys.path для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent import run_agent_task
from git_workflow import execute_autonomous_workflow
from worktree_manager import create_worktree, remove_worktree, ensure_git_repo


class TestAgentAndWorkflow(unittest.TestCase):
    """
    Тесты для функционала agent.py и git_workflow.py.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_agent_wf_")
        ensure_git_repo(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_run_agent_task_general_profile(self):
        """
        Проверяет выполнение run_agent_task с дефолтным профилем general.
        """
        worktree_path = os.path.join(self.test_dir, "worktree_1")
        os.makedirs(worktree_path, exist_ok=True)

        res = asyncio.run(run_agent_task(
            prompt="Создать веб-страницу с заголовком",
            project_type="general",
            worktree_dir=worktree_path,
            task_id="test-1"
        ))

        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("status"), "success")
        self.assertIn("output", res)
        self.assertIsInstance(res.get("files_created"), list)

    def test_run_agent_task_web_profile_custom_model(self):
        """
        Проверяет выполнение run_agent_task с профилем web и явной моделью.
        """
        worktree_path = os.path.join(self.test_dir, "worktree_2")
        os.makedirs(worktree_path, exist_ok=True)

        res = asyncio.run(run_agent_task(
            prompt="Создать React компонент кнопки",
            model="claude-3.5-opus",
            project_type="web",
            worktree_dir=worktree_path,
            task_id="test-2"
        ))

        self.assertEqual(res.get("status"), "success")
        self.assertIn("output", res)

    def test_execute_autonomous_workflow_success(self):
        """
        Проверяет полный цикл execute_autonomous_workflow в git worktree.
        """
        worktree_path, branch_name = create_worktree(task_id="m4-success", base_dir=self.test_dir)
        try:
            res = execute_autonomous_workflow(
                worktree_dir=worktree_path,
                branch_name=branch_name,
                task_id="m4-success",
                prompt="Добавить калькулятор процентов",
                project_type="web"
            )

            self.assertEqual(res.get("status"), "completed")
            self.assertEqual(res.get("branch"), branch_name)
            self.assertTrue(res.get("pr_url").startswith("http"))
            self.assertTrue(len(res.get("commit_hash")) > 0)
            self.assertIn("test session starts", res.get("test_output"))

            # Проверяем, что коммит зарегистрирован в git
            hash_check = subprocess.run(
                ["git", "-C", worktree_path, "rev-parse", "HEAD"],
                capture_output=True, text=True
            )
            self.assertEqual(hash_check.stdout.strip(), res.get("commit_hash"))
        finally:
            remove_worktree(worktree_path, branch_name=branch_name, delete_branch=True, base_dir=self.test_dir)

    def test_execute_autonomous_workflow_failing_tests(self):
        """
        Проверяет реакцию execute_autonomous_workflow на проваливающийся unit-тест.
        """
        worktree_path, branch_name = create_worktree(task_id="m4-fail", base_dir=self.test_dir)
        try:
            # Создаем сломанный тест в worktree до вызова воркфлоу
            tests_dir = os.path.join(worktree_path, "tests")
            os.makedirs(tests_dir, exist_ok=True)
            with open(os.path.join(tests_dir, "test_broken.py"), "w", encoding="utf-8") as f:
                f.write("def test_broken():\n    assert 1 == 2\n")

            res = execute_autonomous_workflow(
                worktree_dir=worktree_path,
                branch_name=branch_name,
                task_id="m4-fail",
                prompt="Задача с ломанными тестами",
                project_type="general"
            )

            self.assertEqual(res.get("status"), "failed")
            self.assertIn("Unit tests failed", res.get("error"))
        finally:
            remove_worktree(worktree_path, branch_name=branch_name, delete_branch=True, base_dir=self.test_dir)


if __name__ == "__main__":
    unittest.main()
