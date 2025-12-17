from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import lancedb

from skillport.shared.config import Config
from skillport.shared.utils import normalize_token, parse_frontmatter

from .embeddings import get_embedding
from .models import SkillRecord
from .search_service import SearchService
from .state import IndexStateStore


class IndexStore:
    """LanceDB-backed index store."""

    schema_version = "fts-v2"

    def __init__(self, config: Config):
        self.config = config
        self.db_path = config.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(self.db_path)
        self.table_name = "skills"
        self.state_path = self.db_path.parent / "index_state.json"
        self.state_store = IndexStateStore(config, self.schema_version, self.state_path)
        self.search_service = SearchService(
            search_threshold=config.search_threshold,
            embed_fn=lambda text: get_embedding(text, config),
        )

    # --- helpers ---------------------------------------------------------
    @staticmethod
    def _normalize_query(value: str) -> str:
        return " ".join(value.strip().split())

    @staticmethod
    def _escape_sql(value: str) -> str:
        return value.replace("'", "''")

    def _prefilter_clause(self) -> str:
        """Build WHERE clause reflecting enabled filters."""
        if self.config.enabled_skills:
            safe = [f"'{self._escape_sql(normalize_token(s))}'" for s in self.config.enabled_skills]
            return f"id IN ({', '.join(safe)})"

        if self.config.enabled_namespaces:
            clauses = []
            for ns in self.config.enabled_namespaces:
                prefix = self._escape_sql(normalize_token(ns).rstrip("/"))
                if prefix:
                    clauses.append(f"lower(id) LIKE '{prefix}%'")
            if clauses:
                return "(" + " OR ".join(clauses) + ")"

        if self.config.enabled_categories:
            safe = [
                f"'{self._escape_sql(normalize_token(c))}'" for c in self.config.enabled_categories
            ]
            return f"category IN ({', '.join(safe)})"

        return ""

    def _embedding_signature(self) -> dict[str, Any]:
        provider = self.config.embedding_provider
        if provider == "openai":
            return {
                "embedding_provider": provider,
                "embedding_model": self.config.openai_embedding_model,
            }
        return {"embedding_provider": provider, "embedding_model": None}

    # --- indexing --------------------------------------------------------
    def _canonical_metadata(
        self,
        original_meta: dict[str, Any],
        metadata_block: dict[str, Any],
        skillport_meta: dict[str, Any],
        category: Any,
        tags: Any,
        always_apply: bool,
    ) -> dict[str, Any]:
        meta_copy = dict(original_meta)
        meta_metadata = dict(metadata_block) if isinstance(metadata_block, dict) else {}
        skillport = dict(skillport_meta) if isinstance(skillport_meta, dict) else {}

        if category is not None:
            skillport["category"] = category
        if tags is not None:
            skillport["tags"] = tags
        skillport["alwaysApply"] = bool(
            skillport.get("alwaysApply", skillport.get("always_apply", always_apply))
        )
        skillport.pop("always_apply", None)

        skillport.pop("env_version", None)
        skillport.pop("requires_setup", None)
        skillport.pop("requiresSetup", None)
        skillport.pop("runtime", None)

        meta_metadata["skillport"] = skillport
        meta_copy["metadata"] = meta_metadata
        return meta_copy

    def initialize_index(self) -> None:
        """Scan skills_dir and (re)build the LanceDB table."""
        # Fail fast for embeddings if needed (double-check even though Config validates)
        if self.config.embedding_provider == "openai" and not self.config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when embedding_provider='openai'")

        skills_dir = self.config.skills_dir
        if not skills_dir.exists():
            print(
                f"Skills dir not found: {skills_dir}; dropping existing index if present",
                file=sys.stderr,
            )
            if self.table_name in self.db.list_tables().tables:
                self.db.drop_table(self.table_name)
            return

        records: list[SkillRecord] = []
        vectors_present = False
        tags_present = False
        ids_seen: set[str] = set()

        def _iter_skill_dirs(base: Path):
            seen: set[Path] = set()
            for pattern in ("*/SKILL.md", "*/*/SKILL.md"):
                for skill_md in base.glob(pattern):
                    skill_dir = skill_md.parent
                    if skill_dir in seen:
                        continue
                    seen.add(skill_dir)
                    rel = skill_dir.relative_to(base)
                    if len(rel.parts) > 2:
                        print(
                            f"Skipping deep skill path (>2 levels): {skill_dir}",
                            file=sys.stderr,
                        )
                        continue
                    yield skill_dir

        for skill_path in _iter_skill_dirs(skills_dir):
            skill_md = skill_path / "SKILL.md"
            content = skill_md.read_text(encoding="utf-8")
            line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)

            meta, body = parse_frontmatter(skill_md)
            if not isinstance(meta, dict):
                print(
                    f"Skipping skill '{skill_path.name}' because frontmatter is not a mapping",
                    file=sys.stderr,
                )
                continue

            metadata_block = meta.get("metadata", {})
            if not isinstance(metadata_block, dict):
                metadata_block = {}

            name = meta.get("name") or skill_path.name
            description = meta.get("description") or ""
            skillport_meta = (
                metadata_block.get("skillport", {}) if isinstance(metadata_block, dict) else {}
            )
            if not isinstance(skillport_meta, dict):
                skillport_meta = {}

            category = skillport_meta.get("category", "")
            tags = skillport_meta.get("tags", [])
            always_apply = skillport_meta.get(
                "alwaysApply", skillport_meta.get("always_apply", False)
            )
            if not isinstance(always_apply, bool):
                always_apply = False

            category_norm = normalize_token(category) if category else ""
            tags_norm: list[str] = []
            if isinstance(tags, list):
                tags_norm = [normalize_token(t) for t in tags]
            elif isinstance(tags, str):
                tags_norm = [normalize_token(tags)]

            rel = skill_path.relative_to(skills_dir)
            if len(rel.parts) == 1:
                skill_id = rel.parts[0]
            elif len(rel.parts) == 2:
                skill_id = "/".join(rel.parts[:2])
            else:
                continue

            if skill_id in ids_seen:
                print(
                    f"Skipping duplicate skill id '{skill_id}' at {skill_path}",
                    file=sys.stderr,
                )
                continue
            ids_seen.add(skill_id)

            text_to_embed = f"{skill_id} {name} {description} {category_norm} {' '.join(tags_norm)}"
            vec = self.search_service.embed_fn(text_to_embed)
            if vec:
                vectors_present = True
            if tags_norm:
                tags_present = True

            record = SkillRecord(
                id=skill_id,
                name=name,
                description=description,
                category=category_norm,
                tags=tags_norm,
                always_apply=always_apply,
                instructions=body,
                path=str(skill_path.absolute()),
                lines=line_count,
                metadata=json.dumps(
                    self._canonical_metadata(
                        meta,
                        metadata_block,
                        skillport_meta,
                        category,
                        tags,
                        always_apply,
                    )
                ),
                vector=vec,
            )
            records.append(record)

        if not records:
            if self.table_name in self.db.list_tables().tables:
                self.db.drop_table(self.table_name)
            return

        if self.table_name in self.db.list_tables().tables:
            self.db.drop_table(self.table_name)

        data: list[dict[str, Any]] = []
        for r in records:
            d = r.model_dump()
            d["tags_text"] = (
                " ".join(d["tags"]) if isinstance(d.get("tags"), list) else str(d.get("tags", ""))
            )
            if not vectors_present:
                d.pop("vector", None)
            data.append(d)

        if not data:
            return

        tbl = self.db.create_table(self.table_name, data=data, mode="overwrite")

        try:
            tbl.create_fts_index(
                ["id", "name", "description", "tags_text", "category"],
                replace=True,
                use_tantivy=True,
            )
        except Exception as exc:
            print(f"FTS index creation failed: {exc}", file=sys.stderr)

        try:
            tbl.create_scalar_index("id", index_type="BTREE", replace=True)
        except Exception as exc:
            print(f"ID scalar index creation failed: {exc}", file=sys.stderr)

        try:
            tbl.create_scalar_index("category", index_type="BITMAP", replace=True)
        except Exception as exc:
            print(f"Category scalar index creation failed: {exc}", file=sys.stderr)

        if tags_present:
            try:
                tbl.create_scalar_index("tags", index_type="LABEL_LIST", replace=True)
            except Exception as exc:
                print(f"Tags scalar index creation failed: {exc}", file=sys.stderr)

    # --- state -----------------------------------------------------------
    def should_reindex(self, *, force: bool = False, skip_auto: bool = False) -> dict[str, Any]:
        return self.state_store.should_reindex(
            self._embedding_signature(), force=force, skip_auto=skip_auto
        )

    def persist_state(self, state: dict[str, Any]) -> None:
        self.state_store.persist(state, skills_dir=self.config.skills_dir, db_path=self.db_path)

    # --- query -----------------------------------------------------------
    def _table(self):
        if self.table_name in self.db.list_tables().tables:
            return self.db.open_table(self.table_name)
        return None

    def search(self, query: str, *, limit: int) -> list[dict[str, Any]]:
        tbl = self._table()
        return self.search_service.search(
            tbl,
            query,
            limit=limit,
            prefilter=self._prefilter_clause(),
            normalize_query=self._normalize_query,
        )

    def get_by_id(self, identifier: str) -> dict[str, Any] | None:
        tbl = self._table()
        if not tbl:
            return None

        safe = self._escape_sql(identifier)
        res = tbl.search().where(f"id = '{safe}'").limit(1).to_list()
        if res:
            return res[0]

        name_matches = tbl.search().where(f"name = '{safe}'").limit(5).to_list()
        if len(name_matches) == 1:
            return name_matches[0]
        if len(name_matches) > 1:
            ids = [m.get("id") for m in name_matches if m.get("id")]
            raise ValueError(
                f"Ambiguous skill name '{identifier}'. Specify full id. Candidates: {', '.join(ids)}"
            )
        return None

    def get_core_skills(self) -> list[dict[str, Any]]:
        tbl = self._table()
        if not tbl:
            return []

        base = "always_apply = true"
        prefilter = self._prefilter_clause()
        clause = base if not prefilter else f"{base} AND ({prefilter})"
        try:
            return tbl.search().where(clause).limit(100).to_list()
        except Exception as exc:
            print(f"Error fetching core skills: {exc}", file=sys.stderr)
            return []

    def list_all(self, *, limit: int) -> list[dict[str, Any]]:
        tbl = self._table()
        if not tbl:
            return []

        prefilter = self._prefilter_clause()
        try:
            query = tbl.search()
            if prefilter:
                query = query.where(prefilter)
            rows = query.limit(limit).to_list()
            for r in rows:
                if "_score" not in r:
                    r["_score"] = 1.0
            return rows
        except Exception as exc:
            print(f"Error listing skills: {exc}", file=sys.stderr)
            return []
