# Tasks directory (implementation plans)

This directory holds detailed implementation plans (ExecPlan equivalent) for large/parallel/high-risk tasks. Small fixes stay in `docs/latest/PLAN.md` only.

Naming: `TASK-<id>-short-name.md` where `<id>` matches the Task ID in PLAN and external tickets (GitHub Projects/Linear).

Place WIP drafts under `docs/latest/tasks/wip/`; CI/tagging should exclude this path from release snapshots.

Each task file **must be self-contained**: reading the file alone should let a contributor execute the task and know how completion will be accepted. Acceptance criteria should be written in EARS form and point to source paths.

## Required Sections (template)
1) **Purpose** — what the task delivers.  
2) **Context Sources (paths only)** — list paths to the authoritative inputs for this task (approved PRDs/specs/plans/code files/configs). Avoid hardcoding irrelevant “latest” files; pick the exact paths relevant at authoring time.  
3) **Acceptance Criteria (EARS, paths preferred; inline allowed)** — EARS-form statements of done/acceptance conditions. Reference source sections by path when they exist; if none, write them inline here.  
4) **Plan of Work** — ordered steps or checklist; note any parallelizable items.  
5) **Validation** — commands or data to prove completion (e.g., `uv run ruff check .`, `uv run pytest -q`, `uv run verify_server.py`).  
6) **Progress Log (optional)** — dated updates.  
7) **Decision Log (optional)** — key decisions and rationale.  
8) **Outcomes** — artifacts produced and their paths.

## Operating Rules
- Use paths-first for context and acceptance. Only summarize external context in-body when a path is impossible; state that explicitly.
- When a task starts, register its Task ID in `docs/latest/PLAN.md`; close it with `- [x]` on completion.
- Store any supporting docs (golden traces, etc.) under `docs/latest` and reference them by path from the task file.
