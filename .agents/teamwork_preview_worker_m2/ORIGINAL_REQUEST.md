## 2026-08-06T12:39:24Z
<USER_REQUEST>
You are a Worker subagent (instance M2).
Your working directory is `.agents/teamwork_preview_worker_m2/`.
Your task is to implement Milestone 2: Core Configuration, LiteLLM Model Routing, and Project Profiles.

Specific tasks:
1. Update `litellm_config.yaml`: Configure model aliases for `claude-3.5-opus`, `gemini-3.1-pro`, `gemini-3.5`, `gemini-3.6`, `antigravity-pro`, and `free-fast` with appropriate provider parameters.
2. Update `docker-compose.yml`: Ensure environment variables for LiteLLM (`ANTHROPIC_API_KEY`, `VERTEX_PROJECT_ID`, `GEMINI_API_KEY`) and Redis are properly declared.
3. Update `deploy.sh`: Remove `--exclude '.git'` from rsync so that VPS retains `.git` directory required for Git Worktrees.
4. Create `project_profiles.py`: Define project profile configurations (`web`, `mobile_dev`, `marketing`, `general`) with custom system instructions, default model selection, and toolsets/capabilities.
5. Create a unit test `tests/test_project_profiles.py` to verify `project_profiles.py` loads profiles correctly and model routing maps as expected. Run pytest using `.venv/bin/pytest tests/test_project_profiles.py` (or python -m unittest) to verify.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write your changes summary to `.agents/teamwork_preview_worker_m2/changes.md`.
Write your handoff report to `.agents/teamwork_preview_worker_m2/handoff.md`.
Include passing build/test command and results in your handoff report.
Send a message back to parent when complete.
</USER_REQUEST>
