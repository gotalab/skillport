# Changelog
All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](https://semver.org/).

## [Unreleased]
- Add GitHub Actions workflow for tag-driven releases (docs snapshot + changelog update + verify).
- Optional: add behavioral regression tests (golden traces) to release gate.
- Clarify branding (SkillHub) vs package/CLI name (`skillhub-mcp`) and add CLI alias `skillhub`.

## [0.0.0] - 2025-11-23
### Added
- Initial MCP server with search/load/read/execute tools.
- FTS-based search with category/tags normalization and fallbacks.
- English guides: AGENTS (core), ENGINEERING_GUIDE, RUNBOOK, VERSIONING.

### Changed
- Default `EMBEDDING_PROVIDER=none`; search defaults `limit=10`, `threshold=0.3`.

### Security
- Path traversal guards, command allowlist + timeout.
- Logging to stderr only (stdout reserved for JSON-RPC).

<!-- Links -->
[Unreleased]: https://github.com/gota/skillhub-mcp/compare/v0.0.0...HEAD
[0.0.0]: https://github.com/gota/skillhub-mcp/releases/tag/v0.0.0
