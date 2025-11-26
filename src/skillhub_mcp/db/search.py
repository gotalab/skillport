import json
import sys
from typing import List, Optional, Any, Dict

import lancedb
from pathlib import Path

from .embeddings import get_embedding
from .models import SkillRecord
from .state import IndexStateStore
from .search_service import SkillSearchService
from ..config import settings
from ..utils import parse_frontmatter


class SkillDB:
    schema_version = "fts-v2"

    def __init__(self, settings_override=None):
        self.settings = settings_override or settings
        self.db_path = self.settings.get_effective_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(self.db_path)
        self.table_name = "skills"
        self._normalize = lambda q: " ".join(q.strip().split())
        # state sidecar lives next to db
        self.state_path = self.db_path.parent / "index_state.json"
        self.state_store = IndexStateStore(self.settings, self.schema_version, self.state_path)
        def _embed(text: str):
            # Support both get_embedding(text, settings) and stubbed get_embedding(text)
            try:
                return get_embedding(text, self.settings)
            except TypeError:
                return get_embedding(text)

        self.search_service = SkillSearchService(
            self.settings,
            embed_fn=_embed,
        )

    # --- Normalization helpers ---
    def _norm_token(self, value: str) -> str:
        """Lowercase + trim for category/tags normalization."""
        return " ".join(str(value).strip().split()).lower()

    def _escape_sql_string(self, value: str) -> str:
        """Basic SQL escaping for string literals."""
        return value.replace("'", "''")

    # --- Table helpers ---
    def _get_table(self):
        if self.table_name in self.db.table_names():
            return self.db.open_table(self.table_name)
        return None

    def _build_prefilter(self) -> str:
        """
        Constructs a SQL WHERE clause based on enabled skills/categories settings.
        Mirrors is_skill_enabled logic:
        1) If skills specified: restrict to names.
        2) Else if namespaces/prefixes specified: restrict by id prefix.
        3) Else if categories specified: restrict to categories.
        4) Else: no filter.
        """
        enabled_skills = self.settings.get_enabled_skills()
        if enabled_skills:
            safe_skills = [
                f"'{self._escape_sql_string(self._norm_token(s))}'" for s in enabled_skills
            ]
            return f"id IN ({', '.join(safe_skills)})"

        enabled_namespaces = self.settings.get_enabled_namespaces()
        if enabled_namespaces:
            clauses = []
            for ns in enabled_namespaces:
                prefix = self._escape_sql_string(self._norm_token(ns).rstrip("/"))
                if prefix:
                    clauses.append(f"lower(id) LIKE '{prefix}%'")
            if clauses:
                return "(" + " OR ".join(clauses) + ")"

        enabled_categories = self.settings.get_enabled_categories()
        if enabled_categories:
            safe_cats = [
                f"'{self._escape_sql_string(self._norm_token(c))}'" for c in enabled_categories
            ]
            return f"category IN ({', '.join(safe_cats)})"

        return ""

    # --- Index lifecycle ---
    def _embedding_signature(self) -> Dict[str, Any]:
        """
        Returns the provider + model tuple used for embeddings so that state
        comparisons can detect model switches within the same provider.
        """
        provider = self.settings.embedding_provider
        if provider == "openai":
            return {"embedding_provider": provider, "embedding_model": self.settings.embedding_model}
        if provider == "gemini":
            return {"embedding_provider": provider, "embedding_model": self.settings.gemini_embedding_model}
        return {"embedding_provider": provider, "embedding_model": None}

    def initialize_index(self):
        """Scans SKILLS_DIR and (re)creates the index."""

        # Fail fast if embeddings are requested but credentials are missing.
        if self.settings.embedding_provider == "openai" and not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when embedding_provider='openai'")
        if self.settings.embedding_provider == "gemini" and not self.settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required when embedding_provider='gemini'")

        skills_dir = self.settings.get_effective_skills_dir()
        if not skills_dir.exists():
            print(f"Skills dir not found: {skills_dir}; dropping existing index if present", file=sys.stderr)
            if self.table_name in self.db.table_names():
                self.db.drop_table(self.table_name)
            return

        records: List[SkillRecord] = []
        vectors_present = False
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
                    # Support up to 2 levels (namespace/skill)
                    if len(rel.parts) > 2:
                        print(f"Skipping deep skill path (>2 levels): {skill_dir}", file=sys.stderr)
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

            # Normalize metadata block
            metadata_block = meta.get("metadata", {})
            if not isinstance(metadata_block, dict):
                metadata_block = {}

            name = meta.get("name") or skill_path.name
            description = meta.get("description") or ""
            skillhub_meta = metadata_block.get("skillhub", {})
            if not isinstance(skillhub_meta, dict):
                skillhub_meta = {}

            # New layout only: metadata.skillhub.*
            category = skillhub_meta.get("category", "")
            tags = skillhub_meta.get("tags", [])

            # Prefer camelCase alwaysApply, accept snake_case as secondary
            always_apply = skillhub_meta.get("alwaysApply", skillhub_meta.get("always_apply", False))
            if not isinstance(always_apply, bool):
                always_apply = False

            # Normalize category/tags for consistent search & filtering
            category_norm = self._norm_token(category) if category else ""
            tags_norm: List[str] = []
            if isinstance(tags, list):
                tags_norm = [self._norm_token(t) for t in tags]
            elif isinstance(tags, str):
                tags_norm = [self._norm_token(tags)]

            rel = skill_path.relative_to(skills_dir)
            if len(rel.parts) == 1:
                skill_id = rel.parts[0]
            elif len(rel.parts) == 2:
                skill_id = "/".join(rel.parts[:2])
            else:
                continue

            if skill_id in ids_seen:
                print(f"Skipping duplicate skill id '{skill_id}' at {skill_path}", file=sys.stderr)
                continue
            ids_seen.add(skill_id)

            text_to_embed = f"{skill_id} {name} {description} {category_norm} {' '.join(tags_norm)}"
            vec = self.search_service.embed_fn(text_to_embed)
            if vec:
                vectors_present = True

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
                    self._canonical_metadata(meta, metadata_block, skillhub_meta, category, tags, always_apply)
                ),
                vector=vec,
            )
            records.append(record)

        if not records:
            if self.table_name in self.db.table_names():
                self.db.drop_table(self.table_name)
            return

        # Drop & recreate to keep schema simple in v0.x
        if self.table_name in self.db.table_names():
            self.db.drop_table(self.table_name)

        data: List[Dict[str, Any]] = []
        for r in records:
            d = r.model_dump()
            if isinstance(d.get("tags"), list):
                d["tags_text"] = " ".join(d["tags"])
            else:
                d["tags_text"] = str(d.get("tags", ""))
            if not vectors_present:
                d.pop("vector", None)
            data.append(d)

        if not data:
            return

        self.db.create_table(self.table_name, data=data, mode="overwrite")

        tbl = self.db.open_table(self.table_name)
        try:
            tbl.create_fts_index(
                ["id", "name", "description", "tags_text", "category"],
                replace=True,
                use_tantivy=True,
            )
        except Exception as e:
            print(f"FTS index creation failed (maybe already exists or not supported): {e}", file=sys.stderr)

        try:
            tbl.create_scalar_index("id", index_type="HASH", replace=True)
        except Exception as e:
            print(f"ID scalar index creation failed: {e}", file=sys.stderr)

        try:
            tbl.create_scalar_index("category", index_type="BITMAP", replace=True)
        except Exception as e:
            print(f"Category scalar index creation failed: {e}", file=sys.stderr)
        try:
            tbl.create_scalar_index("tags", index_type="LABEL_LIST", replace=True)
        except Exception as e:
            print(f"Tags scalar index creation failed: {e}", file=sys.stderr)

    def _canonical_metadata(
        self,
        original_meta: Dict[str, Any],
        metadata_block: Dict[str, Any],
        skillhub_meta: Dict[str, Any],
        category: Any,
        tags: Any,
        always_apply: bool,
    ) -> Dict[str, Any]:
        """
        Builds a normalized metadata dict to store in DB.
        - Ensures `metadata` exists and carries category/tags/skillhub.
        - Avoids mutating the original parsed frontmatter.
        """
        meta_copy = dict(original_meta)

        meta_metadata = dict(metadata_block) if isinstance(metadata_block, dict) else {}
        skillhub = dict(skillhub_meta) if isinstance(skillhub_meta, dict) else {}

        # Set skillhub fields canonically (but preserve parsed values if present)
        if category is not None:
            skillhub["category"] = category
        if tags is not None:
            skillhub["tags"] = tags
        # store as camelCase in metadata
        skillhub["alwaysApply"] = bool(skillhub.get("alwaysApply", skillhub.get("always_apply", always_apply)))
        skillhub.pop("always_apply", None)

        # Remove deprecated fields
        skillhub.pop("env_version", None)
        skillhub.pop("requires_setup", None)
        skillhub.pop("requiresSetup", None)
        skillhub.pop("runtime", None)

        # Attach skillhub under metadata
        meta_metadata["skillhub"] = skillhub

        meta_copy["metadata"] = meta_metadata

        # Legacy top-level fields stay as-is; consumer should read from metadata.*
        return meta_copy

    def should_reindex(self, force: bool = False, skip_auto: bool = False) -> Dict[str, Any]:
        """
        Decide whether to rebuild the index.
        Returns dict with keys: need(bool), reason(str), state(dict), current(dict)
        """
        embedding_sig = self._embedding_signature()
        return self.state_store.should_reindex(embedding_sig, force=force, skip_auto=skip_auto)

    def persist_state(self, state: Dict[str, Any]) -> None:
        self.state_store.persist(
            state,
            skills_dir=self.settings.get_effective_skills_dir(),
            db_path=self.db_path,
        )

    # --- Query helpers ---
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        tbl = self._get_table()
        return self.search_service.search(
            table=tbl,
            query=query,
            limit=limit,
            prefilter=self._build_prefilter(),
            normalize_query=self._normalize,
        )

    def get_skill(self, identifier: str) -> Optional[Dict[str, Any]]:
        tbl = self._get_table()
        if not tbl:
            return None

        safe = self._escape_sql_string(identifier)
        # 1) Exact id match first
        res = tbl.search().where(f"id = '{safe}'").limit(1).to_list()
        if res:
            return res[0]

        # 2) Fallback to name match; detect ambiguity
        name_matches = tbl.search().where(f"name = '{safe}'").limit(5).to_list()
        if len(name_matches) == 1:
            return name_matches[0]
        if len(name_matches) > 1:
            ids = [m.get("id") for m in name_matches if m.get("id")]
            raise ValueError(f"Ambiguous skill name '{identifier}'. Specify full id. Candidates: {', '.join(ids)}")
        return None

    def get_core_skills(self) -> List[Dict[str, Any]]:
        tbl = self._get_table()
        if not tbl:
            return []

        base_clause = "always_apply = true"
        prefilter = self._build_prefilter()
        where_clause = base_clause if not prefilter else f"{base_clause} AND ({prefilter})"
        try:
            return tbl.search().where(where_clause).limit(100).to_list()
        except Exception as e:
            print(f"Error fetching core skills: {e}", file=sys.stderr)
            return []

    def list_all_skills(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List all skills (respecting prefilter) without search scoring."""
        tbl = self._get_table()
        if not tbl:
            return []

        prefilter = self._build_prefilter()
        try:
            query = tbl.search()
            if prefilter:
                query = query.where(prefilter)
            results = query.limit(limit).to_list()
            # Add a default score for consistency with search results
            for r in results:
                if "_score" not in r:
                    r["_score"] = 1.0
            return results
        except Exception as e:
            print(f"Error listing skills: {e}", file=sys.stderr)
            return []
