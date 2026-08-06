# Project Plan: AI Orchestrator Task Pipeline

## Objective
Build an autonomous AI Orchestrator task execution pipeline backed by Celery, Git Worktrees, Antigravity SDK, LiteLLM proxy routing, omnichannel task ingestion (Telegram/Asana), and dynamic worker toolsets, verified by GitHub Draft PR creation.

## Milestones

| # | Milestone Name | Scope | Requirements | Status |
|---|----------------|-------|--------------|--------|
| M1 | Exploration & Architecture Design | Inspect codebase, evaluate gaps, design modular architecture | R1-R6 | DONE |
| M2 | Core Configuration & Proxy Setup | Update `litellm_config.yaml`, `docker-compose.yml`, `deploy.sh` (keep `.git`), `project_profiles.py` | R4, R6 | DONE |
| M3 | Worktree Manager & Redis Task Store | Create `worktree_manager.py` (`feature/task-<id>`) and `task_store.py` (Redis status persistence) | R1, R2 | DONE |
| M4 | Antigravity SDK & Autonomous Git Engine | Implement `agent.py` runner with LiteLLM routing, test runner, git commit, push & Draft PR creation | R1, R3, R4, R6 | IN_PROGRESS |
| M5 | Omnichannel Ingestion & Feedback Dispatcher | Implement Telegram tag parser (`#task`, `#bug`), `/webhook/asana` endpoint, and `notifier.py` | R5 | IN_PROGRESS |
| M6 | Test Suite & E2E Acceptance Verification | Create unit tests, execute build & test suite, verify full acceptance criteria loop | Criteria 1-4 | PLANNED |

## Verification Criteria
- Task creation via UI, Telegram, or Asana triggers Celery worker.
- Celery worker creates git branch `feature/task-<id>` and worktree `.worktrees/task-<id>`.
- Antigravity agent runs inside worktree, generates code/test stubs, passes unit tests, commits.
- Agent pushes branch and creates Draft PR on GitHub.
- Status feedback is delivered to Telegram/Asana/UI.
