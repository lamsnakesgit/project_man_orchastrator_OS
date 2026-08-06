import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Добавляем корневую директорию проекта в sys.path для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api import app, parse_telegram_message, task_store
from notifier import Notifier, notifier
from task_store import TaskStore

client = TestClient(app)
AUTH = ("admin", "admin")


class TestTelegramTagParsing(unittest.TestCase):
    """
    Тесты для фильтрации и извлечения тегов Telegram сообщений.
    """

    def test_untagged_message_ignored(self):
        """Немаркированные сообщения без тегов #task/#bug/#feature должны игнорироваться."""
        text = "Обычное сообщение без тегов для бота"
        res = parse_telegram_message(text)
        self.assertIsNone(res)

    def test_task_tag_parsing(self):
        """Извлечение тега #task, типа проекта #web и модели #gpt-4o."""
        text = "Создать новый компонент входа #task #web #gpt-4o"
        res = parse_telegram_message(text)
        self.assertIsNotNone(res)
        self.assertEqual(res["project_type"], "web")
        self.assertEqual(res["model"], "gpt-4o")
        self.assertEqual(res["prompt"], text)

    def test_bug_tag_parsing(self):
        """Извлечение тега #bug, типа проекта #mobile и модели #gemini-1.5-pro."""
        text = "Исправить падение на старте #bug #mobile #gemini-1.5-pro"
        res = parse_telegram_message(text)
        self.assertIsNotNone(res)
        self.assertEqual(res["project_type"], "mobile")
        self.assertEqual(res["model"], "gemini-1.5-pro")

    def test_feature_tag_parsing(self):
        """Извлечение тега #feature с префиксами #project:frontend и #model:claude-3-5-sonnet."""
        text = "Добавить переключатель темы #feature #project:frontend #model:claude-3-5-sonnet"
        res = parse_telegram_message(text)
        self.assertIsNotNone(res)
        self.assertEqual(res["project_type"], "frontend")
        self.assertEqual(res["model"], "claude-3-5-sonnet")

    @patch("tasks.process_agent_task.apply_async")
    def test_telegram_webhook_untagged_endpoint(self, mock_celery):
        """Эндпоинт /webhook/telegram игнорирует немаркированные сообщения."""
        payload = {
            "message": {
                "chat": {"id": 12345},
                "text": "Просто привет"
            }
        }
        response = client.post("/webhook/telegram", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("status"), "ignored")
        mock_celery.assert_not_called()

    @patch("tasks.process_agent_task.apply_async")
    def test_telegram_webhook_tagged_endpoint(self, mock_celery):
        """Эндпоинт /webhook/telegram создает задачу в TaskStore при наличии тега #task."""
        payload = {
            "message": {
                "chat": {"id": 67890},
                "text": "Сделать рефакторинг API #task #backend"
            }
        }
        response = client.post("/webhook/telegram", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("task_id", data)
        mock_celery.assert_called_once()


class TestAsanaWebhook(unittest.TestCase):
    """
    Тесты для Asana вебхука (рукопожатие X-Hook-Secret и обработка событий).
    """

    def test_asana_secret_handshake(self):
        """Проверка эхо-ответа заголовка X-Hook-Secret при регистрации вебхука."""
        secret = "secret-handshake-token-999"
        response = client.post(
            "/webhook/asana",
            headers={"X-Hook-Secret": secret}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Hook-Secret"), secret)

    @patch("tasks.process_agent_task.apply_async")
    def test_asana_event_processing(self, mock_celery):
        """Обработка событий Asana, создание задачи в TaskStore и запуск Celery."""
        payload = {
            "events": [
                {
                    "action": "changed",
                    "resource": {"gid": "1122334455", "resource_type": "task"},
                    "text": "Обновить документацию модуля"
                }
            ]
        }
        response = client.post("/webhook/asana", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("created_tasks", data)
        self.assertEqual(len(data["created_tasks"]), 1)
        mock_celery.assert_called_once()


class TestTaskStoreAPIIntegration(unittest.TestCase):
    """
    Тестирование интеграции TaskStore с API эндпоинтами (/tasks, /tasks/all, /tasks/{task_id}).
    """

    @patch("tasks.process_agent_task.apply_async")
    def test_create_task_and_fetch(self, mock_celery):
        """Создание задачи через POST /tasks и последующее чтение по ID и списком."""
        payload = {
            "prompt": "Реализовать авторизацию OAuth #task",
            "model": "gpt-4o",
            "project_type": "web"
        }
        resp = client.post("/tasks", json=payload, auth=AUTH)
        self.assertEqual(resp.status_code, 200)
        task_id = resp.json()["task_id"]

        # Получение задачи по ID
        resp_get = client.get(f"/tasks/{task_id}", auth=AUTH)
        self.assertEqual(resp_get.status_code, 200)
        task_info = resp_get.json()["task"]
        self.assertEqual(task_info["id"], task_id)
        self.assertEqual(task_info["prompt"], "Реализовать авторизацию OAuth #task")
        self.assertEqual(task_info["model"], "gpt-4o")

        # Получение всех задач
        resp_all = client.get("/tasks/all", auth=AUTH)
        self.assertEqual(resp_all.status_code, 200)
        all_tasks = resp_all.json()["tasks"]
        self.assertTrue(any(t["id"] == task_id for t in all_tasks))

    def test_get_nonexistent_task(self):
        """Запрос несуществующего task_id должен возвращать 404."""
        resp = client.get("/tasks/non-existent-uuid-000", auth=AUTH)
        self.assertEqual(resp.status_code, 404)


class TestNotifierRouting(unittest.TestCase):
    """
    Тестирование модуля Notifier и маршрутизации уведомлений.
    """

    def setUp(self):
        self.notifier = Notifier()

    @patch("urllib.request.urlopen")
    def test_send_telegram_notification(self, mock_urlopen):
        """Отправка уведомления Telegram с mock HTTP ответа."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "mock_tg_token"}):
            res = self.notifier.send_telegram_notification(12345, "Задача выполнена", pr_url="http://pr.url")
            self.assertTrue(res)
            mock_urlopen.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_send_asana_notification(self, mock_urlopen):
        """Отправка комментария в Asana с mock HTTP ответа."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "mock_asana_token"}):
            res = self.notifier.send_asana_notification("gid_123", "Задача готова")
            self.assertTrue(res)
            mock_urlopen.assert_called_once()

    @patch.object(Notifier, "send_telegram_notification")
    def test_notify_task_result_telegram(self, mock_tg):
        """Маршрутизация результатов задачи для источника 'telegram'."""
        mock_tg.return_value = True
        task_data = {
            "source": "telegram",
            "status": "completed",
            "chat_id": 999888,
            "prompt": "Тестовый промпт",
            "pr_url": "https://github.com/pr/1"
        }
        res = self.notifier.notify_task_result(task_data)
        self.assertTrue(res)
        mock_tg.assert_called_once()

    @patch.object(Notifier, "send_asana_notification")
    def test_notify_task_result_asana(self, mock_asana):
        """Маршрутизация результатов задачи для источника 'asana'."""
        mock_asana.return_value = True
        task_data = {
            "source": "asana",
            "status": "failed",
            "chat_id": "asana_gid_456",
            "prompt": "Исправить баг",
            "error": "Syntax error"
        }
        res = self.notifier.notify_task_result(task_data)
        self.assertTrue(res)
        mock_asana.assert_called_once()

    def test_notify_task_result_ui(self):
        """Маршрутизация результатов задачи для источника 'ui'."""
        task_data = {
            "source": "ui",
            "status": "completed",
            "prompt": "UI Задача"
        }
        res = self.notifier.notify_task_result(task_data)
        self.assertTrue(res)


if __name__ == "__main__":
    unittest.main()
