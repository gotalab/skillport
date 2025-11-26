# API Stability

This document defines the stability guarantees for SkillHub's public API.

## Versioning Policy

- **v0.x.x**: Development phase. Breaking changes allowed in MINOR versions.
- **v1.0.0+**: Stable. Breaking changes only in MAJOR versions.

## Stability Levels

### Stable (v1.0.0+で破壊的変更なし)

These APIs will not change without a MAJOR version bump:

**MCP Tools:**
- `search_skills(query, category?, tags?, limit?)`
- `load_skill(name)`
- `read_skill_file(skill_name, file_path)`

**CLI:**
- `skillhub-mcp` / `skillhub` entry points
- `--list`, `--lint`, `--reindex` flags

**Configuration:**
- `SKILLS_DIR`, `EMBEDDING_PROVIDER`, `SEARCH_LIMIT`, `SEARCH_THRESHOLD`

### Experimental (変更あり得る)

These may change in MINOR versions:

- `run_skill_command` (disabled by default, may be removed)
- Internal DB schema (`SkillRecord` fields)
- Embedding provider implementations
- Search algorithm tuning parameters

### Internal (変更自由)

Not part of public API:

- `skillhub_mcp.db.*` internals
- `skillhub_mcp.tools.*` implementation details
- Test utilities

## Migration Guide

When breaking changes occur:

1. CHANGELOG.md will document the change
2. `feat!:` or `BREAKING CHANGE:` in commit
3. Migration instructions provided in release notes

## Reporting Issues

If you depend on an Experimental API and need stability:
- Open an issue requesting promotion to Stable
- Describe your use case
