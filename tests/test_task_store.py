import os
import sys
import unittest
import json
from unittest.mock import MagicMock

# Добавляем корневую директорию проекта в sys.path для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from task_store import TaskStore

class TestTaskStoreInMemory(unittest.TestCase):
    """
    Тестирование TaskStore в режиме fallback (in-memory).
    """

    def setUp(self):
        # Используем заведомо недействительный порт, чтобы гарантировать переключение на in-memory fallback
        self.store = TaskStore(port=59999, socket_timeout=0.1)
        self.assertFalse(self.store.use_redis, "Хранилище должно переключиться в in-memory режим")

    def test_create_and_get_task(self):
        """
        Проверка создания задачи и последующего получения по ID.
        """
        task_data = {
            "prompt": "Test prompt in-memory",
            "model": "gemini-1.5-pro",
            "project_type": "python",
            "chat_id": 123456
        }
        created = self.store.create_task(task_data)
        
        self.assertIn("id", created)
        self.assertEqual(created["prompt"], "Test prompt in-memory")
        self.assertEqual(created["status"], "queued")
        self.assertEqual(created["model"], "gemini-1.5-pro")
        self.assertEqual(created["chat_id"], 123456)
        self.assertIsNotNone(created["created_at"])
        self.assertIsNotNone(created["updated_at"])

        fetched = self.store.get_task(created["id"])
        self.assertEqual(fetched, created)

    def test_invalid_status_creation(self):
        """
        Проверка исключения при создании задачи с недействительным статусом.
        """
        with self.assertRaises(ValueError):
            self.store.create_task({"prompt": "Bad status", "status": "invalid_status"})

    def test_update_task_status(self):
        """
        Проверка обновления статуса задачи и кастомных полей.
        """
        created = self.store.create_task({"prompt": "Update test"})
        task_id = created["id"]

        updated = self.store.update_task_status(
            task_id,
            "in_progress",
            branch="feature/task-1",
            pr_url="https://github.com/org/repo/pull/1"
        )

        self.assertEqual(updated["status"], "in_progress")
        self.assertEqual(updated["branch"], "feature/task-1")
        self.assertEqual(updated["pr_url"], "https://github.com/org/repo/pull/1")

        # Проверка обновления статуса на completed
        completed = self.store.update_task_status(task_id, "completed")
        self.assertEqual(completed["status"], "completed")

        # Проверка недействительного статуса
        with self.assertRaises(ValueError):
            self.store.update_task_status(task_id, "unknown_status")

        # Проверка вызова с несуществующим task_id
        with self.assertRaises(KeyError):
            self.store.update_task_status("non-existent-id", "failed")

    def test_list_tasks(self):
        """
        Проверка получения списка всех задач.
        """
        t1 = self.store.create_task({"prompt": "Task 1"})
        t2 = self.store.create_task({"prompt": "Task 2"})
        
        all_tasks = self.store.list_tasks()
        self.assertEqual(len(all_tasks), 2)
        task_ids = [t["id"] for t in all_tasks]
        self.assertIn(t1["id"], task_ids)
        self.assertIn(t2["id"], task_ids)

    def test_get_nonexistent_task(self):
        """
        Запрос несуществующей задачи должен возвращать None.
        """
        res = self.store.get_task("random-missing-uuid")
        self.assertIsNone(res)

class TestTaskStoreRedisMocked(unittest.TestCase):
    """
    Тестирование TaskStore в режиме Redis с использованием mock-клиента.
    """

    def setUp(self):
        self.mock_redis = MagicMock()
        self.mock_redis.ping.return_value = True
        self.db_kv = {}
        self.db_sets = {}

        def mock_set(key, val):
            self.db_kv[key] = val
            return True

        def mock_get(key):
            return self.db_kv.get(key)

        def mock_sadd(key, val):
            if key not in self.db_sets:
                self.db_sets[key] = set()
            self.db_sets[key].add(val)
            return 1

        def mock_smembers(key):
            return self.db_sets.get(key, set())

        self.mock_redis.set.side_effect = mock_set
        self.mock_redis.get.side_effect = mock_get
        self.mock_redis.sadd.side_effect = mock_sadd
        self.mock_redis.smembers.side_effect = mock_smembers

        self.store = TaskStore(redis_client=self.mock_redis)
        self.assertTrue(self.store.use_redis, "Хранилище должно использовать Redis")

    def test_redis_crud_operations(self):
        """
        Проверка CRUD операций через Redis клиент.
        """
        # Создание задачи
        task = self.store.create_task({"prompt": "Redis task", "model": "gpt-4o"})
        task_id = task["id"]
        
        self.mock_redis.set.assert_called()
        self.mock_redis.sadd.assert_called_with("tasks:set", task_id)

        # Чтение задачи
        fetched = self.store.get_task(task_id)
        self.assertEqual(fetched["prompt"], "Redis task")

        # Обновление задачи
        updated = self.store.update_task_status(task_id, "completed", pr_url="http://pr.url")
        self.assertEqual(updated["status"], "completed")
        self.assertEqual(updated["pr_url"], "http://pr.url")

        # Получение списка задач
        tasks_list = self.store.list_tasks()
        self.assertEqual(len(tasks_list), 1)
        self.assertEqual(tasks_list[0]["id"], task_id)

if __name__ == "__main__":
    unittest.main()
