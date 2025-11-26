# Changelog
All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](https://semver.org/).

## [0.1.0](https://github.com/gotalab/skillhub-mcp/compare/v0.0.2...v0.1.0) (2025-11-26)


### Features

* add namespace filtering and custom add options ([#7](https://github.com/gotalab/skillhub-mcp/issues/7)) ([e8970e5](https://github.com/gotalab/skillhub-mcp/commit/e8970e54427f492e14b5e0cfa2aa86fbeadb0811))
* add namespace filtering, custom add options, and origin tracking ([9e846fd](https://github.com/gotalab/skillhub-mcp/commit/9e846fdb6817d30b2e201c8d8bc3078a4f26826a))
* improve CLI and fix env var parsing for filters ([51e598d](https://github.com/gotalab/skillhub-mcp/commit/51e598d3062054ab62973fa59238679e4faec3b7))
* namespace filtering and CLI improvements ([cc1b988](https://github.com/gotalab/skillhub-mcp/commit/cc1b988e34d7bf95132a9e70bfacd14ff3899435))

## 0.0.2 (2025-11-26)


### Features

* add `skillhub add` command and use ~/.skillhub/ as default ([#5](https://github.com/gotalab/skillhub-mcp/issues/5)) ([ea16ed4](https://github.com/gotalab/skillhub-mcp/commit/ea16ed463ec34602ced7cdb6be154a688b391ef8))
* Add multi-client support, skill scoping, and context-efficient skill loading with updated documentation and tests. ([4c2ddb7](https://github.com/gotalab/skillhub-mcp/commit/4c2ddb71dea4d83ac6f614bb454d1ec3b325f8b6))
* **ci:** migrate from semantic-release to Release Please ([3e11f85](https://github.com/gotalab/skillhub-mcp/commit/3e11f85a46f7705b36bb60da421a49d41772fddf))
* Dynamically generate LanceDB path based on skills directory hash and update README with improved onboarding and architecture overview. ([48bb8fd](https://github.com/gotalab/skillhub-mcp/commit/48bb8fdff3900c35b68994378eb771905b78376b))
* Enhance skill search and indexing with state management and a dedicated search service, and rename the `read_file` tool to `read_skill_file`. ([1fb139a](https://github.com/gotalab/skillhub-mcp/commit/1fb139a2619cc497973c8db070963fcfbe9c974c))
* Implement skill readiness checks, automated setup, and status reporting with updated skill metadata and CLI commands. ([ea8b74f](https://github.com/gotalab/skillhub-mcp/commit/ea8b74fe69a005b2566239ee3d0825a14c0bf72e))
* Improve skill reindexing by skipping skills with non-mapping frontmatter and dropping the table when no valid skills are present. ([4ba5f8d](https://github.com/gotalab/skillhub-mcp/commit/4ba5f8df12dc105d2b76dd30a78069e4a503bc68))
* Introduce `run_skill_command`, enhance `search_skills` with empty/wildcard query handling, and update execution environment documentation. ([0d010b5](https://github.com/gotalab/skillhub-mcp/commit/0d010b5ccf33fc4fb14dc356610bcec47b24a499))
* propagate settings overrides, normalize skill prefilters, drop stale indexes, and refine search result limiting ([693015e](https://github.com/gotalab/skillhub-mcp/commit/693015ed903229635901420220fd26d7afa1a2c1))
* Remove skill runtime and setup fields, and integrate uv for Python command execution. ([65fd58c](https://github.com/gotalab/skillhub-mcp/commit/65fd58c78cd511a39ad0fb63c04cdb62e2175daa))


### Bug Fixes

* **ci:** add write permission and push to main branch ([fe85f42](https://github.com/gotalab/skillhub-mcp/commit/fe85f4257b5f0df5b3dbb3bb0a39189a62a0b675))
* **ci:** exclude only tasks/AGENTS.md from release snapshot ([4f4e558](https://github.com/gotalab/skillhub-mcp/commit/4f4e558da3df055ea6f1157a3adddc0609bd99c1))
* **ci:** exclude tasks/ directory from release snapshot ([4117a02](https://github.com/gotalab/skillhub-mcp/commit/4117a02113189809620a17ddfc6f2882d7679628))
* **tests:** update test for uv run python command ([04086a6](https://github.com/gotalab/skillhub-mcp/commit/04086a6e1277344614711eb8360fcc1a1495f3db))


### Documentation

* rebuild documentation structure ([fe77eb0](https://github.com/gotalab/skillhub-mcp/commit/fe77eb005d8cff2c8d0be953b3d60f65aa584321))
* restore all documentation from 2f15525 ([b849349](https://github.com/gotalab/skillhub-mcp/commit/b849349bfc0a53519e61b68b250590e296309d02))


### Miscellaneous Chores

* trigger v0.0.1 release ([e02d59c](https://github.com/gotalab/skillhub-mcp/commit/e02d59c960939810f03fa294c851b9d6747aa445))
* trigger v0.0.2 release ([3b01da2](https://github.com/gotalab/skillhub-mcp/commit/3b01da2e384e0e36a94d754fd410d50ebea95e97))

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
