import os
import json
import logging
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class Notifier:
    """
    Класс для отправки обратной связи инициатору задачи в различных платформах (Telegram, Asana, UI).
    """

    def send_telegram_notification(self, chat_id: int, message: str, pr_url: Optional[str] = None) -> bool:
        """
        Отправляет сообщение в Telegram с использованием Telegram Bot API (TELEGRAM_BOT_TOKEN).
        """
        token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("ANTIGRAVITY_BOT_TOKEN")
        if not token:
            logger.warning("TELEGRAM_BOT_TOKEN / ANTIGRAVITY_BOT_TOKEN не задан. Уведомление Telegram пропущено.")
            return False

        full_message = message
        if pr_url and pr_url not in full_message:
            full_message = f"{message}\nPR: {pr_url}"

        if len(full_message) > 3900:
            full_message = full_message[:3800] + "\n\n...[сообщение сокращено]"

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({
            "chat_id": chat_id,
            "text": full_message
        }).encode("utf-8")

        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    logger.info(f"Успешно отправлено Telegram-уведомление в чат {chat_id}.")
                    return True
                else:
                    logger.error(f"Ошибка отправки Telegram-уведомления, статус: {response.status}.")
                    return False
        except Exception as e:
            logger.error(f"Исключение при отправке Telegram-уведомления: {e}")
            return False

    def send_asana_notification(self, task_gid: str, comment: str) -> bool:
        """
        Публикует комментарий (story) к задаче в Asana через Asana API (ASANA_ACCESS_TOKEN).
        """
        token = os.getenv("ASANA_ACCESS_TOKEN")
        if not token:
            logger.warning("ASANA_ACCESS_TOKEN не задан. Уведомление Asana пропущено.")
            return False

        url = f"https://app.asana.com/api/1.0/tasks/{task_gid}/stories"
        payload = json.dumps({
            "data": {
                "text": comment
            }
        }).encode("utf-8")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (200, 201):
                    logger.info(f"Успешно опубликован комментарий Asana к задаче {task_gid}.")
                    return True
                else:
                    logger.error(f"Ошибка отправки уведомления Asana, статус: {response.status}.")
                    return False
        except Exception as e:
            logger.error(f"Исключение при отправке уведомления Asana: {e}")
            return False

    def notify_task_result(self, task_data: dict) -> bool:
        """
        Маршрутизирует уведомление в зависимости от источника задачи (telegram, asana, ui).
        """
        source = task_data.get("source", "ui")
        status = task_data.get("status", "unknown")
        pr_url = task_data.get("pr_url")
        error = task_data.get("error")
        prompt = task_data.get("prompt", "")

        if status == "completed":
            msg = f"Task completed successfully: {prompt}"
            if pr_url:
                msg += f"\nPR: {pr_url}"
        elif status == "failed":
            msg = f"Task failed: {prompt}\nError: {error or 'Unknown error'}"
        else:
            msg = f"Task status update ({status}): {prompt}"

        default_chat_id = os.getenv("MAIN_TELEGRAM_CHAT_ID", "888005446")
        target_chat_id = task_data.get("chat_id") or default_chat_id

        if source == "telegram" or target_chat_id:
            try:
                chat_id_int = int(target_chat_id)
                return self.send_telegram_notification(chat_id_int, msg, pr_url=pr_url)
            except (ValueError, TypeError):
                logger.error(f"Недопустимый chat_id '{target_chat_id}' для Telegram уведомления.")
                return False
        elif source == "asana":
            task_gid = str(task_data.get("task_gid") or task_data.get("chat_id") or task_data.get("id", ""))
            if task_gid:
                return self.send_asana_notification(task_gid, msg)
            else:
                logger.warning("task_gid отсутствует для Asana уведомления.")
                return False
        else:
            logger.info(f"Уведомление для источника '{source}': {msg}")
            if default_chat_id:
                try:
                    self.send_telegram_notification(int(default_chat_id), f"[UI Task Alert]\n{msg}", pr_url=pr_url)
                except Exception as e:
                    logger.warning(f"Не удалось отправить копию в Telegram: {e}")
            return True

# Экземпляр по умолчанию
notifier = Notifier()
