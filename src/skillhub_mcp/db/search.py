import json
import sys
from typing import List, Optional, Any, Dict

import lancedb

from .embeddings import get_embedding
from .models import SkillRecord
from .state import IndexStateStore
from .search_service import SkillSearchService
from ..config import settings
from ..utils import parse_frontmatter


class SkillDB:
    schema_version = "fts-v1"

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
        2) Else if categories specified: restrict to categories.
        3) Else: no filter.
        """
        if self.settings.skillhub_enabled_skills:
            safe_skills = [
                f"'{self._escape_sql_string(self._norm_token(s))}'" for s in self.settings.skillhub_enabled_skills
            ]
            return f"lower(name) IN ({', '.join(safe_skills)})"

        if self.settings.skillhub_enabled_categories:
            safe_cats = [
                f"'{self._escape_sql_string(self._norm_token(c))}'" for c in self.settings.skillhub_enabled_categories
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

        for skill_path in skills_dir.iterdir():
            if not skill_path.is_dir():
                continue
            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists():
                continue

            meta, body = parse_frontmatter(skill_md)

            # Normalize metadata block
            metadata_block = meta.get("metadata", {})
            if not isinstance(metadata_block, dict):
                metadata_block = {}

            name = meta.get("name", skill_path.name)
            description = meta.get("description", "")
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

            text_to_embed = f"{name} {description} {category_norm} {' '.join(tags_norm)}"
            vec = self.search_service.embed_fn(text_to_embed)
            if vec:
                vectors_present = True

            record = SkillRecord(
                name=name,
                description=description,
                category=category_norm,
                tags=tags_norm,
                always_apply=always_apply,
                instructions=body,
                path=str(skill_path.absolute()),
                metadata=json.dumps(
                    self._canonical_metadata(meta, metadata_block, skillhub_meta, category, tags, always_apply)
                ),
                vector=vec,
            )
            records.append(record)

        if not records:
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
                ["name", "description", "tags_text", "category"],
                replace=True,
                use_tantivy=True,
            )
        except Exception as e:
            print(f"FTS index creation failed (maybe already exists or not supported): {e}", file=sys.stderr)

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

    def get_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        tbl = self._get_table()
        if not tbl:
            return None

        safe_name = self._escape_sql_string(skill_name)
        res = tbl.search().where(f"name = '{safe_name}'").limit(1).to_list()
        if res:
            return res[0]
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
