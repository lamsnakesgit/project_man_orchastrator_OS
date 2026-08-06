## 2026-08-06T12:39:24Z
You are a Worker subagent (instance M3).
Your working directory is `.agents/teamwork_preview_worker_m3/`.
Your task is to implement Milestone 3: Git Worktree Manager and Redis Task Store.

Specific tasks:
1. Create `worktree_manager.py`:
   - Function `create_worktree(task_id: str, base_dir: str = ".") -> Tuple[str, str]`: Creates branch `feature/task-<id>` and worktree at `.worktrees/task-<id>`. Returns `(worktree_path, branch_name)`.
   - Function `remove_worktree(worktree_path: str, branch_name: str = None, delete_branch: bool = False)`: Safely removes git worktree and prunes.
   - Function `ensure_git_repo(base_dir: str = ".")`: Ensures base_dir is a valid git repository (initializes git if needed).
2. Create `task_store.py`:
   - Redis-backed task manager (`TaskStore` class) using `redis.Redis` with fallback to thread-safe in-memory store if Redis is unreachable.
   - Methods: `create_task(data: dict) -> dict`, `update_task_status(task_id: str, status: str, **kwargs) -> dict`, `get_task(task_id: str) -> dict`, `list_tasks() -> List[dict]`.
   - Schema: `id`, `prompt`, `status` (`queued`, `in_progress`, `completed`, `failed`), `model`, `project_type`, `source`, `chat_id`, `branch`, `pr_url`, `error`, `created_at`, `updated_at`.
3. Create unit tests `tests/test_worktree_manager.py` and `tests/test_task_store.py`. Run unit tests using `.venv/bin/pytest tests/` (or python -m unittest) to verify.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write your changes summary to `.agents/teamwork_preview_worker_m3/changes.md`.
Write your handoff report to `.agents/teamwork_preview_worker_m3/handoff.md`.
Include passing build/test command and results in your handoff report.
Send a message back to parent when complete.
