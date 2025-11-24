import json
import sys
import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict

import lancedb

from .embeddings import get_embedding
from .models import SkillRecord
from ..config import settings
from ..utils import parse_frontmatter


class SkillDB:
    schema_version = "fts-v1"

    def __init__(self):
        self.db_path = settings.get_effective_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(self.db_path)
        self.table_name = "skills"
        self._normalize = lambda q: " ".join(q.strip().split())
        # state sidecar lives next to db
        self.state_path = self.db_path.parent / "index_state.json"

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
        if settings.skillhub_enabled_skills:
            safe_skills = [f"'{self._escape_sql_string(s)}'" for s in settings.skillhub_enabled_skills]
            return f"name IN ({', '.join(safe_skills)})"

        if settings.skillhub_enabled_categories:
            safe_cats = [f"'{self._escape_sql_string(self._norm_token(c))}'" for c in settings.skillhub_enabled_categories]
            return f"category IN ({', '.join(safe_cats)})"

        return ""

    # --- Index lifecycle ---
    def initialize_index(self):
        """Scans SKILLS_DIR and (re)creates the index."""

        # Fail fast if embeddings are requested but credentials are missing.
        if settings.embedding_provider == "openai" and not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when embedding_provider='openai'")
        if settings.embedding_provider == "gemini" and not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required when embedding_provider='gemini'")

        skills_dir = settings.get_effective_skills_dir()
        if not skills_dir.exists():
            print(f"Skills dir not found: {skills_dir}", file=sys.stderr)
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
            vec = get_embedding(text_to_embed)
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

    # --- State helpers for incremental rebuild decisions ---
    def _hash_skills_dir(self) -> Dict[str, Any]:
        """
        Compute a stable hash of SKILL.md files under skills_dir.
        Uses relative path + mtime_ns + size + content hash to ensure updates
        to instructions are detected.
        """
        skills_dir = settings.get_effective_skills_dir()
        entries: List[str] = []

        if not skills_dir.exists():
            return {"hash": "", "count": 0}

        for skill_path in skills_dir.iterdir():
            if not skill_path.is_dir():
                continue
            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists():
                continue
            try:
                st = skill_md.stat()
            except FileNotFoundError:
                continue
            try:
                body_digest = hashlib.sha1(skill_md.read_bytes()).hexdigest()
            except Exception:
                body_digest = "err"
            rel = skill_md.relative_to(skills_dir)
            entries.append(f"{rel}:{st.st_mtime_ns}:{st.st_size}:{body_digest}")

        entries.sort()
        joined = "|".join(entries)
        digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
        return {"hash": f"sha256:{digest}", "count": len(entries)}

    def _load_state(self) -> Optional[Dict[str, Any]]:
        if not self.state_path.exists():
            return None
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load index state: {e}", file=sys.stderr)
            return None

    def _write_state(self, state: Dict[str, Any]) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to write index state: {e}", file=sys.stderr)

    def should_reindex(self, force: bool = False, skip_auto: bool = False) -> Dict[str, Any]:
        """
        Decide whether to rebuild the index.
        Returns dict with keys: need(bool), reason(str), state(dict), current(dict)
        """
        current = self._hash_skills_dir()
        current_state = {
            "schema_version": self.schema_version,
            "embedding_provider": settings.embedding_provider,
            "skills_hash": current["hash"],
            "skill_count": current["count"],
        }

        if force:
            return {"need": True, "reason": "force", "state": current_state, "previous": self._load_state()}

        if skip_auto:
            return {"need": False, "reason": "skip_auto", "state": current_state, "previous": self._load_state()}

        prev = self._load_state()
        if not prev:
            return {"need": True, "reason": "no_state", "state": current_state, "previous": prev}

        if prev.get("schema_version") != self.schema_version:
            return {"need": True, "reason": "schema_changed", "state": current_state, "previous": prev}

        if prev.get("embedding_provider") != settings.embedding_provider:
            return {"need": True, "reason": "provider_changed", "state": current_state, "previous": prev}

        if prev.get("skills_hash") != current["hash"]:
            return {"need": True, "reason": "hash_changed", "state": current_state, "previous": prev}

        return {"need": False, "reason": "unchanged", "state": current_state, "previous": prev}

    def persist_state(self, state: Dict[str, Any]) -> None:
        payload = dict(state)
        payload["built_at"] = datetime.now(timezone.utc).isoformat()
        payload["skills_dir"] = str(settings.get_effective_skills_dir())
        payload["db_path"] = str(self.db_path)
        self._write_state(payload)

    # --- Query helpers ---
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        tbl = self._get_table()
        if not tbl:
            return []

        threshold = settings.search_threshold
        query = self._normalize(query)
        prefilter = self._build_prefilter()
        fetch_limit = limit * 4

        try:
            vec = get_embedding(query)
        except Exception as e:
            print(f"Embedding fetch failed, falling back to FTS: {e}", file=sys.stderr)
            vec = None

        results: List[Dict[str, Any]] = []

        try:
            if vec:
                search_op = tbl.search(vec)
                if prefilter:
                    search_op = search_op.where(prefilter)
                results = search_op.limit(fetch_limit).to_list()
            else:
                try:
                    search_op = tbl.search(query, query_type="fts")
                    if prefilter:
                        search_op = search_op.where(prefilter)
                    results = search_op.limit(fetch_limit).to_list()
                except Exception as e:
                    print(f"FTS search failed, using substring fallback: {e}", file=sys.stderr)
                    search_op = tbl.search()
                    if prefilter:
                        search_op = search_op.where(prefilter)
                    rows = search_op.limit(fetch_limit * 3).to_list()

                    qlow = query.lower()
                    for row in rows:
                        if qlow in str(row.get("name", "")).lower() or qlow in str(row.get("description", "")).lower():
                            row["_score"] = 0.1
                            results.append(row)
                            if len(results) >= fetch_limit:
                                break
        except Exception as e:
            print(f"Search error: {e}", file=sys.stderr)
            return []

        if not results:
            return []

        results.sort(key=lambda x: x.get("_score", 0), reverse=True)

        if len(results) <= 5:
            return results[:limit]

        top_score = results[0].get("_score", 0)
        if top_score <= 0:
            return results[:limit]

        filtered_results = []
        for res in results:
            score = res.get("_score", 0)
            if score / top_score >= threshold:
                filtered_results.append(res)
            else:
                break

        return filtered_results[:limit]

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
