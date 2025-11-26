# Documentation & Release Operating Model

Audience: team-wide reference for how we manage docs, versions, and branches. Keep this short; deeper detail lives in AGENTS, VERSIONING, RUNBOOK, and per-feature specs.

## Minimal required docs
- **PRD** (`docs/latest/PRD.md`): required。リリースで「何を出荷するか」（ユーザ価値・スコープ・受入れ基準）のSSOT。
- **SPEC** (`docs/latest/specs/**`): 必要に応じて。受入れ基準やテスト観点をPRDと一致させる。
- **PLAN** (`docs/latest/PLAN.md`): 「どう作るか」のSSOT。タスク索引と小粒作業の手順をここに記載し、Task ID・Spec/PRD ID・Owner・Status・主要テスト・並列可否を必須フィールドとする。
- **TASKS** (`docs/latest/tasks/<task-id>.md`): 中〜大規模またはリスク高のタスクだけ詳細実装計画を別ファイルで持つ（ExecPlan相当）。
- **CHANGELOG.md** (root): Release Please管理。手編集しない。
- その他のspecは必要に応じて追加（API/data/search/safetyなど）。
- WIP用の作業計画は `docs/latest/tasks/wip/` に置く。タグ時スナップショットから除外される。

## Layout
- `docs/latest/` — 次リリースのSSOT。PRD/SPEC（何を作るか）、PLAN/TASKS（どう作るか）を含む。
- `docs/latest/tasks/` — 実装計画（ExecPlan相当）。小粒タスクはPLAN内だけで完結。大粒/並列/リスク高の場合のみファイルを作成し、PLANからリンク。
- `docs/releases/vX.Y.Z/` — タグ時にCIが`docs/latest`を丸ごとスナップショット（`specs/wip/**` と `tasks/wip/**` は除外）。手編集禁止。
- Optional temporary tracks (`docs/next/`) only for major rework; merge back into `latest` before tagging.
- WIP specs live under `docs/latest/specs/wip/**` and are excluded/blocked from release snapshots.

## Spec organization (large features)
- Core/contract stays small and stable (interfaces, glossary, non-functional policies).
- Split by domain/layer as needed: `specs/api`, `specs/service-<domain>`, `specs/data`, `specs/search`, `specs/safety`, `specs/rollout`, `specs/tests`.
- Each spec should name Owner, Last updated, and required review level (core/api/data/safety: approval; others may be lighter).
- WIP chapters stay in `specs/wip/<feature>/SPEC.md`; move to formal paths once approved.

## Branch & release strategy (trunk-friendly + Release Please)
- Develop on **main** with feature flags to keep trunk releasable (trunk-based development).
- **PR必須フィールド**（PR本文に記載）: `Task ID`、`Spec/PRD ID (or N/A)`、`tasks/<file>.md`リンク（大粒時）、`主要テストコマンド`（例: `uv run verify_server.py`）。
- **CI gates (ci.yml)**: lint (`ruff`), test (`pytest`), verify (`verify_server.py`).
- **Release flow (Release Please)**:
  1. Conventional Commits (`feat:`, `fix:`, etc.) on main.
  2. Release Please auto-creates/updates "Release PR" with CHANGELOG and version bump.
  3. Merge Release PR → tag created → `docs/releases/vX.Y.Z/` snapshot created.
- **Manual version override**: Edit `.release-please-manifest.json` or use `Release-As: X.Y.Z` commit footer.
- Never edit `docs/releases/*`. CI/branch protection should block it.

## How to avoid doc drift
- Single edit point: `docs/latest` (plus WIP area).  
- If release-branch docs must change, keep the edit minimal, then cherry-pick to main and re-snapshot on the next tag.
- Consider CI checks: fail if `docs/releases/*` is modified or if WIP/DRAFT markers remain when tagging.

## When running with only PRD + PLAN
- 小粒開発では `docs/latest/PRD.md` と `PLAN.md` と CHANGELOG だけでも運用可能。複雑性や並列度が上がったら SPEC と `docs/latest/tasks/<task-id>.md` を追加する。

## Behavioral/contract tests
- Optional but recommended: golden traces / contract tests to guard spec-defined interfaces. Add to CI before semantic-release when adopted.

## Pointers
- Core principles: `AGENTS.md`
- Versioning & CI details: `docs/steering/VERSIONING.md`, `docs/steering/VERSIONING_TEMPLATE.md`
- Operations: `docs/steering/RUNBOOK.md`
- Technical policies: `docs/steering/ENGINEERING_GUIDE.md`
