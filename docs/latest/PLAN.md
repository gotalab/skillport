# Plan & Context: SkillHub (package: skillhub-mcp)

**Status:** Active Development
**Goal:** Provide a reusable Agent Skills hub via MCP.

> このPLANは「どう作るか」のSSOTです。小粒タスクは本ファイルに1行で完結させます。中〜大規模・並列・リスク高の作業は Task ID を振り、詳細は `docs/latest/tasks/<task-id>.md` に記述して本ファイルからリンクしてください。

## Context

- **PRD:** [docs/releases/v0.0.1/PRD.md](../releases/v0.0.1/PRD.md)
- **Philosophy:** [docs/releases/v0.0.1/SKILL_PHILOSOPHY.md](../releases/v0.0.1/SKILL_PHILOSOPHY.md)
- **Core Tech:** Python 3.10+, FastMCP, LanceDB, Pydantic
- **Environment:** `uv` for dependency management

## Directory Structure

```
~/.skillhub/
├── skills/              # Default skills directory
└── indexes/
    ├── default/         # Index for ~/.skillhub/skills/
    └── {hash}/          # Index for custom SKILLS_DIR
```

## CLI Commands

```bash
# Skills management (preparation)
skillhub add hello-world   # Add sample skill (auto-creates directory)
skillhub add template      # Add skill template
skillhub --list            # List indexed skills
skillhub --lint            # Validate SKILL.md files

# Server (execution)
skillhub                   # Start MCP server (auto-creates index)
skillhub --reindex         # Force reindex on startup
```

## Roadmap & Tasks

### Completed (v0.0.1)

See [docs/releases/v0.0.1/PLAN.md](../releases/v0.0.1/PLAN.md) for full history.

Key features:
- Core MCP tools: `search_skills`, `load_skill`, `read_skill_file`
- Hybrid search (Vector + FTS) with fallback chain
- `alwaysApply` skills in system prompt
- Skill validation (`--lint`, `--list`)
- Execution model simplification (PEP 723, path-based design)

### Phase 7: Distribution & CLI Enhancement (Current)

#### 7.1 Default Paths
- [x] Change default `SKILLS_DIR` from `./.agent/skills` to `~/.skillhub/skills`
- [x] Change default `DB_PATH` to `~/.skillhub/indexes/default/`
- [x] Use `~/.skillhub/indexes/{hash}/` for custom `SKILLS_DIR`
- [x] Remove `platformdirs` dependency (use simple `~/.skillhub/` convention)

#### 7.2 CLI Restructure
- [x] Remove `init` command (unnecessary with auto-creation)
- [x] Add `add` command for built-in skills
  - [x] `skillhub add hello-world` - Sample skill
  - [x] `skillhub add template` - Skill template
  - [x] Auto-create `~/.skillhub/skills/` on first `add`
- [x] Update README.md with new CLI

#### 7.3 Documentation
- [x] Update README.md (Quick Start, Configuration, CLI)
- [x] Create `docs/latest/PLAN.md` (this file)

### Phase 8: Future Enhancements (Planned)

#### 8.1 CLI Extensions
- [ ] `skillhub add <local-path>` - Copy local skill to skills directory
- [ ] `skillhub add <git-url>` - Clone skill from Git repository
- [ ] `skillhub remove <skill-name>` - Remove skill

#### 8.2 Search Improvements
- [ ] FTS field boosts (blocked: LanceDB API limitation)
- [ ] Behavioral regression tests (golden traces)

#### 8.3 Distribution
- [ ] PyPI publication
- [ ] One-click install buttons for MCP clients

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLS_DIR` | Path to skills directory | `~/.skillhub/skills` |
| `DB_PATH` | Path to LanceDB index | `~/.skillhub/indexes/default/` |
| `EMBEDDING_PROVIDER` | `none`, `openai`, or `gemini` | `none` |
| `SEARCH_LIMIT` | Max search results | `10` |
| `SEARCH_THRESHOLD` | Minimum score threshold | `0.2` |

## Verification

```bash
# Full verification
SKILLS_DIR=.agent/skills uv run verify_server.py

# Quick checks
skillhub --list
skillhub --lint
```

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2024-11-27 | Use `~/.skillhub/` instead of `platformdirs` | Simpler, follows CLI tool convention (~/.npm, ~/.cargo), easier for users to find |
| 2024-11-27 | Replace `init` with `add` command | `init` implies index creation; `add` is clearer for skill management |
| 2024-11-27 | Auto-create directories on `add` | Reduces setup steps; directory creation is implicit |
