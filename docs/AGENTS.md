# Docs Governance (Read Me First)

Purpose: explain how documentation is organized in this repo so anyone can navigate, edit, and release docs consistently.

## Layout
- `docs/latest/` — Living source of truth for product docs (PRD, SPEC, PLAN). Always edit here.
- `docs/steering/` — Project constitutional governance and guides (AGENTS core, ENGINEERING_GUIDE, RUNBOOK, VERSIONING, VERSIONING_TEMPLATE).
- `docs/releases/vX.Y.Z/` — Frozen snapshots taken at release time (copied from `docs/latest/`).

## Roles
- **AGENTS.md (root)** — Core principles for all work (SSOT, safe defaults, logging, normalization, fallback, regression intent).
- **docs/steering/ENGINEERING_GUIDE.md** — Technical policies (search/indexing, defaults, logging rules).
- **docs/steering/RUNBOOK.md** — Operational steps (setup, verify, release flow, PAT setup).
- **docs/steering/VERSIONING.md** — Repo-specific versioning/release strategy (latest vs releases/, SemVer, CI flow).
- **docs/steering/VERSIONING_TEMPLATE.md** — Reusable template to apply this strategy in other repos.
- **docs/steering/OPERATING_MODEL.md** — How we run docs, specs, branches, and releases (minimal docs, WIP handling, trunk/release flow).
- **CHANGELOG.md (root)** — Human-readable history; updated by semantic-release and included in snapshots.
- **PRD / SPEC** — Require review/approval before changes (formal design). Not always needed for every task.
- **PLAN** — Living document (`docs/latest/PLAN.md`); update continuously as work progresses.
- **PLAN format (convention)** — Keep a short Context/Goal, then phases with checkbox lists. Add new work to phases or a small “Next” section. Update statuses in place; avoid duplicating tasks across plans. Feature-level plans (e.g., `docs/latest/specs/feature1/PLAN.md`) are OK for large efforts, but merge progress back into `docs/latest/PLAN.md` before release; main PLAN is the SSOT at tag time.
- **Acceptance Criteria** — Write them in EARS form and keep them close to the spec/PRD/API section they validate. Prefer path references (PRD/SPEC/code) over prose; each task markdown must be self-contained with paths to its context and acceptance criteria.

## Semantic Versioning & PLAN.md
- The living plan is `docs/latest/PLAN.md`; it tracks tasks and status for the current version under development.
- When releasing, `docs/latest` is snapshotted to `docs/releases/vX.Y.Z/`; the PLAN in the snapshot reflects the state of that release.
- Semantic-release + GitHub Actions create tags/releases and update CHANGELOG; docs snapshot step copies `docs/latest` to the matching release folder.

## Edit Rules
- Edit only `docs/latest` and `docs/steering`; never edit `docs/releases/*`.
- Keep defaults consistent across code, PRD, PLAN, and steering guides (e.g., search_limit=10, search_threshold=0.2).
- Package manager / runners: use `uv` for sync/run/test/build; ad-hoc execution is `uvx` (ok), but prefer `uv run ...` in docs/CI examples.
- Log/debug must stay off stdout (MCP constraint); stderr only.

## Quick Start
1) Need specs/tasks? Open `docs/latest/PLAN.md` (SSOT).  
2) Need architecture or search details? `docs/steering/ENGINEERING_GUIDE.md`.  
3) Need commands to run/verify/release? `docs/steering/RUNBOOK.md`.  
4) Need versioning policy or to port it elsewhere? `docs/steering/VERSIONING.md` / `VERSIONING_TEMPLATE.md`.  
5) Ready to release? Tag `vX.Y.Z`; CI runs semantic-release, updates CHANGELOG, snapshots `docs/latest` to `docs/releases/vX.Y.Z/`.

## About additional tracks (next/preview)
- Default: keep only `latest` (SSOT) and `releases/vX.Y.Z` (frozen).
- If you must prepare a long-running major, create `docs/next/` as a temporary workspace, then merge back into `docs/latest` before tagging. Avoid multiple parallel tracks to reduce drift.
