from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from tasks import process_agent_task
from task_store import TaskStore
import uuid
import os
import re
import json
import base64
from fastapi.responses import Response

app = FastAPI(title="AI Orchestrator Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

task_store = TaskStore()

@app.middleware("http")
async def basic_auth_middleware(request: Request, call_next):
    if request.url.path in ["/webhook/telegram", "/webhook/asana"]:
        return await call_next(request)
        
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Basic "):
        return Response("Unauthorized", status_code=401, headers={"WWW-Authenticate": "Basic"})
        
    try:
        encoded_credentials = auth_header.split(" ")[1]
        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
        username, password = decoded_credentials.split(":", 1)
        if username != ADMIN_USER or password != ADMIN_PASSWORD:
            raise ValueError()
    except Exception:
        return Response("Unauthorized", status_code=401, headers={"WWW-Authenticate": "Basic"})
        
    return await call_next(request)

class TaskRequest(BaseModel):
    prompt: str
    chat_id: Optional[int] = None
    priority: str = "normal"
    model: Optional[str] = "default"
    project_type: Optional[str] = "default"


def parse_telegram_message(text: str) -> Optional[dict]:
    """
    Парсит входящее сообщение Telegram.
    Проверяет наличие триггерных тегов (#task, #bug, #feature).
    Извлекает project_type (#mobile, #web, #project:xyz и т.д.) и модель (#gpt-4o, #model:xyz и т.д.).
    Возвращает dict с prompt, project_type, model при успехе, иначе None.
    """
    if not text:
        return None

    tags = re.findall(r'#([\w:.-]+)', text)
    tags_lower = [t.lower() for t in tags]

    trigger_tags = {"task", "bug", "feature"}
    if not any(t in trigger_tags for t in tags_lower):
        return None

    project_type = "default"
    model = "default"

    known_project_types = {"mobile", "web", "frontend", "backend", "python", "ios", "android", "react"}
    known_models = {"gpt-4o", "gpt-4", "gemini", "gemini-1.5-pro", "claude", "claude-3-5-sonnet", "antigravity-pro"}

    for tag in tags:
        low = tag.lower()
        if low in trigger_tags:
            continue
        elif low.startswith("project:"):
            project_type = low.split(":", 1)[1]
        elif low.startswith("model:"):
            model = low.split(":", 1)[1]
        elif low in known_project_types:
            project_type = low
        elif low in known_models:
            model = low
        else:
            if any(m in low for m in ["gpt", "gemini", "claude"]):
                model = low
            elif project_type == "default":
                project_type = low

    return {
        "prompt": text,
        "project_type": project_type,
        "model": model
    }


@app.post("/tasks")
def create_task(req: TaskRequest):
    """
    Создает задачу в TaskStore и ставит Celery задачу в очередь.
    """
    source = "telegram" if req.chat_id is not None else "ui"
    task_data = {
        "prompt": req.prompt,
        "chat_id": req.chat_id,
        "model": req.model or "default",
        "project_type": req.project_type or "default",
        "source": source,
        "status": "queued"
    }
    created_task = task_store.create_task(task_data)
    task_id = created_task["id"]

    process_agent_task.apply_async(args=[task_id], task_id=task_id)

    return {"task_id": task_id, "status": "queued"}


@app.get("/tasks/all")
def get_all_tasks():
    """
    Возвращает список всех задач из TaskStore.
    """
    return {"tasks": task_store.list_tasks()}


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    """
    Возвращает задачу по ее task_id из TaskStore.
    """
    task = task_store.get_task(task_id)
    if not task:
        return Response(content=json.dumps({"error": "Task not found"}), status_code=404, media_type="application/json")
    return {"task": task}


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Вебхук для Telegram бота.
    Фильтрует входящие сообщения по тегам #task, #bug, #feature.
    Извлекает project_type и model.
    """
    data = await request.json()
    message = data.get("message", {})
    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")

    if not text or not chat_id:
        return {"ok": True, "status": "ignored"}

    parsed = parse_telegram_message(text)
    if not parsed:
        return {"ok": True, "status": "ignored"}

    task_data = {
        "prompt": parsed["prompt"],
        "chat_id": chat_id,
        "model": parsed["model"],
        "project_type": parsed["project_type"],
        "source": "telegram",
        "status": "queued"
    }
    created_task = task_store.create_task(task_data)
    task_id = created_task["id"]

    process_agent_task.apply_async(args=[task_id], task_id=task_id)

    return {"ok": True, "task_id": task_id, "status": "queued"}


@app.post("/webhook/asana")
async def asana_webhook(request: Request):
    """
    Вебхук для Asana.
    Поддерживает рукопожатие X-Hook-Secret.
    Обрабатывает события задач из Asana, создает задачи в TaskStore и отправляет в Celery.
    """
    hook_secret = request.headers.get("X-Hook-Secret")
    if hook_secret:
        return Response(status_code=200, headers={"X-Hook-Secret": hook_secret})

    data = await request.json()
    created_tasks = []

    events = data.get("events")
    if events and isinstance(events, list):
        for event in events:
            resource = event.get("resource", {})
            task_gid = str(resource.get("gid") or event.get("task_gid") or "")
            if not task_gid:
                continue
            prompt = event.get("text") or event.get("name") or event.get("prompt") or f"Asana task {task_gid}"
            task_data = {
                "prompt": prompt,
                "chat_id": task_gid,
                "task_gid": task_gid,
                "source": "asana",
                "model": data.get("model", "default"),
                "project_type": data.get("project_type", "default"),
                "status": "queued"
            }
            created = task_store.create_task(task_data)
            task_id = created["id"]
            process_agent_task.apply_async(args=[task_id], task_id=task_id)
            created_tasks.append(task_id)
    else:
        task_gid = str(data.get("task_gid") or data.get("gid") or data.get("resource_gid") or "")
        prompt = data.get("prompt") or data.get("name") or data.get("text")
        if prompt or task_gid:
            task_data = {
                "prompt": prompt or f"Asana task {task_gid}",
                "chat_id": task_gid,
                "task_gid": task_gid,
                "source": "asana",
                "model": data.get("model", "default"),
                "project_type": data.get("project_type", "default"),
                "status": "queued"
            }
            created = task_store.create_task(task_data)
            task_id = created["id"]
            process_agent_task.apply_async(args=[task_id], task_id=task_id)
            created_tasks.append(task_id)

    return {"ok": True, "created_tasks": created_tasks}


# Mount frontend as static files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
