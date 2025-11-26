# Changelog
All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](https://semver.org/).

## [0.0.1](https://github.com/gotalab/skillhub-mcp/compare/v0.0.1...v0.0.1) (2025-11-26)


### Features

* Add multi-client support, skill scoping, and context-efficient skill loading with updated documentation and tests. ([5eddfbb](https://github.com/gotalab/skillhub-mcp/commit/5eddfbbcb99e0d187ee63e7e88899b8f7b5cf888))
* **ci:** migrate from semantic-release to Release Please ([bf8ce99](https://github.com/gotalab/skillhub-mcp/commit/bf8ce9922fd654cc789308c311dba0756419de47))
* Dynamically generate LanceDB path based on skills directory hash and update README with improved onboarding and architecture overview. ([a3c85ac](https://github.com/gotalab/skillhub-mcp/commit/a3c85ac1ae05cd8f78d1941318bbebe5f6b1583d))
* Enhance skill search and indexing with state management and a dedicated search service, and rename the `read_file` tool to `read_skill_file`. ([7b66c55](https://github.com/gotalab/skillhub-mcp/commit/7b66c55b895466946c48102b90b96f66ffb1c2ce))
* Implement skill readiness checks, automated setup, and status reporting with updated skill metadata and CLI commands. ([53cd9a2](https://github.com/gotalab/skillhub-mcp/commit/53cd9a22c1ffe38f879fcdebd00aa6cd9aca4be2))
* Improve skill reindexing by skipping skills with non-mapping frontmatter and dropping the table when no valid skills are present. ([53c9be3](https://github.com/gotalab/skillhub-mcp/commit/53c9be36ca86bf6652ac0bc61c06de7deb1312c8))
* Introduce `run_skill_command`, enhance `search_skills` with empty/wildcard query handling, and update execution environment documentation. ([90b11bc](https://github.com/gotalab/skillhub-mcp/commit/90b11bc69e39a274d03da8fdd369d91341be7ac8))
* propagate settings overrides, normalize skill prefilters, drop stale indexes, and refine search result limiting ([0500dc8](https://github.com/gotalab/skillhub-mcp/commit/0500dc87d406ec17d59dc5afe34c92209800ce7e))
* Remove skill runtime and setup fields, and integrate uv for Python command execution. ([5903849](https://github.com/gotalab/skillhub-mcp/commit/5903849e8a497f8fe42337676c0896b98c1479ab))


### Bug Fixes

* **ci:** add write permission and push to main branch ([a59e957](https://github.com/gotalab/skillhub-mcp/commit/a59e957adc365e9c78b65e10c4186d245faa19ba))
* **ci:** exclude only tasks/AGENTS.md from release snapshot ([597e4cc](https://github.com/gotalab/skillhub-mcp/commit/597e4ccc0560a24b5de07395c03d476e72cb201d))
* **ci:** exclude tasks/ directory from release snapshot ([003bbc6](https://github.com/gotalab/skillhub-mcp/commit/003bbc6d9d880c1c786488c212df1c9268987299))
* **tests:** update test for uv run python command ([77babc2](https://github.com/gotalab/skillhub-mcp/commit/77babc2d239dd5ed5e67272ae4102e9e2c3fb4a0))


### Documentation

* Update and refine various project planning, steering, and technical documentation files. ([c9b06ca](https://github.com/gotalab/skillhub-mcp/commit/c9b06caccb49e6347b72c1132a8acbf9e6006bad))
* update release documentation for Release Please ([04c06dd](https://github.com/gotalab/skillhub-mcp/commit/04c06dd4091500b3403d21861aba060ca40775ac))


### Miscellaneous Chores

* trigger v0.0.1 release ([569e86e](https://github.com/gotalab/skillhub-mcp/commit/569e86ed322be795ee2b448e33b6da39df04fe2a))

## [0.0.1](https://github.com/gotalab/skillhub-mcp/compare/v0.0.0...v0.0.1) (2025-11-26)


### Features

* **ci:** migrate from semantic-release to Release Please ([bf8ce99](https://github.com/gotalab/skillhub-mcp/commit/bf8ce9922fd654cc789308c311dba0756419de47))


### Bug Fixes

* **ci:** exclude only tasks/AGENTS.md from release snapshot ([597e4cc](https://github.com/gotalab/skillhub-mcp/commit/597e4ccc0560a24b5de07395c03d476e72cb201d))
* **ci:** exclude tasks/ directory from release snapshot ([003bbc6](https://github.com/gotalab/skillhub-mcp/commit/003bbc6d9d880c1c786488c212df1c9268987299))
* **tests:** update test for uv run python command ([77babc2](https://github.com/gotalab/skillhub-mcp/commit/77babc2d239dd5ed5e67272ae4102e9e2c3fb4a0))


### Documentation

* update release documentation for Release Please ([04c06dd](https://github.com/gotalab/skillhub-mcp/commit/04c06dd4091500b3403d21861aba060ca40775ac))


### Miscellaneous Chores

* trigger v0.0.1 release ([569e86e](https://github.com/gotalab/skillhub-mcp/commit/569e86ed322be795ee2b448e33b6da39df04fe2a))

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
