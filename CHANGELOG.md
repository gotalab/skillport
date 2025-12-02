# Changelog

## 0.0.2 (2025-12-02)


### Features

* add `skillhub add` command and use ~/.skillhub/ as default ([#5](https://github.com/gotalab/skillport/issues/5)) ([ea16ed4](https://github.com/gotalab/skillport/commit/ea16ed463ec34602ced7cdb6be154a688b391ef8))
* Add multi-client support, skill scoping, and context-efficient skill loading with updated documentation and tests. ([4c2ddb7](https://github.com/gotalab/skillport/commit/4c2ddb71dea4d83ac6f614bb454d1ec3b325f8b6))
* add namespace filtering and custom add options ([#7](https://github.com/gotalab/skillport/issues/7)) ([e8970e5](https://github.com/gotalab/skillport/commit/e8970e54427f492e14b5e0cfa2aa86fbeadb0811))
* add namespace filtering, custom add options, and origin tracking ([9e846fd](https://github.com/gotalab/skillport/commit/9e846fdb6817d30b2e201c8d8bc3078a4f26826a))
* **ci:** migrate from semantic-release to Release Please ([3e11f85](https://github.com/gotalab/skillport/commit/3e11f85a46f7705b36bb60da421a49d41772fddf))
* Dynamically generate LanceDB path based on skills directory hash and update README with improved onboarding and architecture overview. ([48bb8fd](https://github.com/gotalab/skillport/commit/48bb8fdff3900c35b68994378eb771905b78376b))
* Enhance skill search and indexing with state management and a dedicated search service, and rename the `read_file` tool to `read_skill_file`. ([1fb139a](https://github.com/gotalab/skillport/commit/1fb139a2619cc497973c8db070963fcfbe9c974c))
* Implement skill readiness checks, automated setup, and status reporting with updated skill metadata and CLI commands. ([ea8b74f](https://github.com/gotalab/skillport/commit/ea8b74fe69a005b2566239ee3d0825a14c0bf72e))
* improve CLI and fix env var parsing for filters ([51e598d](https://github.com/gotalab/skillport/commit/51e598d3062054ab62973fa59238679e4faec3b7))
* Improve skill reindexing by skipping skills with non-mapping frontmatter and dropping the table when no valid skills are present. ([4ba5f8d](https://github.com/gotalab/skillport/commit/4ba5f8df12dc105d2b76dd30a78069e4a503bc68))
* Introduce `run_skill_command`, enhance `search_skills` with empty/wildcard query handling, and update execution environment documentation. ([0d010b5](https://github.com/gotalab/skillport/commit/0d010b5ccf33fc4fb14dc356610bcec47b24a499))
* namespace filtering and CLI improvements ([cc1b988](https://github.com/gotalab/skillport/commit/cc1b988e34d7bf95132a9e70bfacd14ff3899435))
* propagate settings overrides, normalize skill prefilters, drop stale indexes, and refine search result limiting ([693015e](https://github.com/gotalab/skillport/commit/693015ed903229635901420220fd26d7afa1a2c1))
* Remove skill runtime and setup fields, and integrate uv for Python command execution. ([65fd58c](https://github.com/gotalab/skillport/commit/65fd58c78cd511a39ad0fb63c04cdb62e2175daa))


### Bug Fixes

* **ci:** add write permission and push to main branch ([fe85f42](https://github.com/gotalab/skillport/commit/fe85f4257b5f0df5b3dbb3bb0a39189a62a0b675))
* **ci:** exclude only tasks/AGENTS.md from release snapshot ([4f4e558](https://github.com/gotalab/skillport/commit/4f4e558da3df055ea6f1157a3adddc0609bd99c1))
* **ci:** exclude tasks/ directory from release snapshot ([4117a02](https://github.com/gotalab/skillport/commit/4117a02113189809620a17ddfc6f2882d7679628))
* **tests:** update test for uv run python command ([04086a6](https://github.com/gotalab/skillport/commit/04086a6e1277344614711eb8360fcc1a1495f3db))


### Documentation

* rebuild documentation structure ([fe77eb0](https://github.com/gotalab/skillport/commit/fe77eb005d8cff2c8d0be953b3d60f65aa584321))
* restore all documentation from 2f15525 ([b849349](https://github.com/gotalab/skillport/commit/b849349bfc0a53519e61b68b250590e296309d02))


### Miscellaneous Chores

* trigger v0.0.1 release ([e02d59c](https://github.com/gotalab/skillport/commit/e02d59c960939810f03fa294c851b9d6747aa445))
* trigger v0.0.2 release ([3b01da2](https://github.com/gotalab/skillport/commit/3b01da2e384e0e36a94d754fd410d50ebea95e97))
