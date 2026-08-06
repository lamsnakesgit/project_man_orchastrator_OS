import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import redis

logger = logging.getLogger(__name__)

class TaskStore:
    """
    Управление задачами с использованием Redis и со встроенным (in-memory) потокобезопасным резервным хранилищем.
    """
    VALID_STATUSES = {"queued", "in_progress", "completed", "failed"}

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        redis_client: Optional[redis.Redis] = None,
        socket_timeout: float = 1.0
    ):
        self.use_redis = False
        self._lock = threading.Lock()
        self._in_memory_store: Dict[str, dict] = {}

        if redis_client is not None:
            self.redis = redis_client
        else:
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                socket_timeout=socket_timeout,
                decode_responses=True
            )

        try:
            self.redis.ping()
            self.use_redis = True
            logger.info("Успешное подключение к Redis хранилищу задач.")
        except Exception as e:
            logger.warning(f"Не удалось подключиться к Redis ({e}). Использование in-memory хранилища.")
            self.use_redis = False

    def create_task(self, data: dict) -> dict:
        """
        Создает новую запись задачи в хранилище.
        """
        now = datetime.now(timezone.utc).isoformat()
        task_id = str(data.get("id") or uuid.uuid4())
        status = data.get("status", "queued")

        if status not in self.VALID_STATUSES:
            raise ValueError(f"Недопустимый статус '{status}'. Допустимые статусы: {self.VALID_STATUSES}")

        task = {
            "id": task_id,
            "prompt": data.get("prompt", ""),
            "status": status,
            "model": data.get("model", "default"),
            "project_type": data.get("project_type", "default"),
            "source": data.get("source", "api"),
            "chat_id": data.get("chat_id"),
            "branch": data.get("branch"),
            "pr_url": data.get("pr_url"),
            "error": data.get("error"),
            "created_at": data.get("created_at", now),
            "updated_at": data.get("updated_at", now),
        }

        if self.use_redis:
            try:
                self.redis.set(f"task:{task_id}", json.dumps(task))
                self.redis.sadd("tasks:set", task_id)
                return task
            except redis.RedisError as e:
                logger.error(f"Ошибка Redis при создании задачи ({e}), использование fallback.")
                self.use_redis = False

        with self._lock:
            self._in_memory_store[task_id] = task.copy()
        return task

    def update_task_status(self, task_id: str, status: str, **kwargs: Any) -> dict:
        """
        Обновляет статус и дополнительные поля задачи.
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Недопустимый статус '{status}'. Допустимые статусы: {self.VALID_STATUSES}")

        task = self.get_task(task_id)
        if not task:
            raise KeyError(f"Задача с id {task_id} не найдена.")

        task["status"] = status
        for k, v in kwargs.items():
            task[k] = v
        task["updated_at"] = datetime.now(timezone.utc).isoformat()

        if self.use_redis:
            try:
                self.redis.set(f"task:{task_id}", json.dumps(task))
                return task
            except redis.RedisError as e:
                logger.error(f"Ошибка Redis при обновлении задачи ({e}), использование fallback.")
                self.use_redis = False

        with self._lock:
            self._in_memory_store[task_id] = task.copy()
        return task

    def get_task(self, task_id: str) -> Optional[dict]:
        """
        Возвращает данные задачи по ее ID.
        """
        if self.use_redis:
            try:
                raw_data = self.redis.get(f"task:{task_id}")
                if raw_data:
                    return json.loads(raw_data)
                return None
            except redis.RedisError as e:
                logger.error(f"Ошибка Redis при получении задачи ({e}), использование fallback.")
                self.use_redis = False

        with self._lock:
            task = self._in_memory_store.get(task_id)
            return task.copy() if task else None

    def list_tasks(self) -> List[dict]:
        """
        Возвращает список всех задач.
        """
        if self.use_redis:
            try:
                task_ids = self.redis.smembers("tasks:set")
                tasks = []
                for tid in task_ids:
                    raw_data = self.redis.get(f"task:{tid}")
                    if raw_data:
                        tasks.append(json.loads(raw_data))
                return tasks
            except redis.RedisError as e:
                logger.error(f"Ошибка Redis при получении списка задач ({e}), использование fallback.")
                self.use_redis = False

        with self._lock:
            return [task.copy() for task in self._in_memory_store.values()]
