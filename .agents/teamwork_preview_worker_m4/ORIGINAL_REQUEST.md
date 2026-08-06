## 2026-08-06T12:43:12Z
You are a Worker subagent (instance M4).
Your working directory is `.agents/teamwork_preview_worker_m4/`.
Your task is to implement Milestone 4: Antigravity SDK Runner & Autonomous Git Workflow (Unit Tests, Commit, Push, Draft PR).

Specific tasks:
1. Update `agent.py`:
   - Function `run_agent_task(prompt: str, model: str = None, project_type: str = "general", worktree_dir: str = None, task_id: str = None) -> dict`:
     - Load `ProjectProfile` from `project_profiles.py` using `project_type`.
     - Select model (passed model or profile default model).
     - Set up `LocalAgentConfig` with profile's system instructions and tools.
     - Execute task inside `worktree_dir` (or cwd if None).
     - Return result dict `{"status": "success", "output": agent_output, "files_created": [...]}`.
2. Create `git_workflow.py`:
   - Function `execute_autonomous_workflow(worktree_dir: str, branch_name: str, task_id: str, prompt: str, project_type: str = "general", model: str = None) -> dict`:
     - Calls `run_agent_task` to generate task solution and test stub file inside `worktree_dir`.
     - Executes unit test runner (`.venv/bin/pytest` or python test execution) inside `worktree_dir`.
     - Upon passing unit tests:
       - Executes `git add .` in `worktree_dir`.
       - Executes `git commit -m "feat(task-<id>): <prompt_summary>"`.
       - Executes `git push origin <branch_name>` (with graceful fallback/mock for local repos without remote origin).
       - Creates Draft PR via `gh pr create --draft --title "feat: task-<id>" --body "..."` or GitHub API fallback.
     - Returns dict: `{"status": "completed", "branch": branch_name, "pr_url": pr_url, "commit_hash": commit_hash, "test_output": test_output}` or `{"status": "failed", "error": error_msg}`.
3. Create unit tests `tests/test_agent_workflow.py` covering `agent.py` and `git_workflow.py`. Run `.venv/bin/pytest tests/` to verify.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write your changes summary to `.agents/teamwork_preview_worker_m4/changes.md`.
Write your handoff report to `.agents/teamwork_preview_worker_m4/handoff.md`.
Include passing build/test command and results in your handoff report.
Send a message back to parent when complete.
