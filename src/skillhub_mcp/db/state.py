import json
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List


class IndexStateStore:
    """
    Handles hashing of the skills directory and persistence of index state.
    Keeps I/O and change-detection concerns out of the DB/search orchestration.
    """

    def __init__(self, settings, schema_version: str, state_path: Path):
        self.settings = settings
        self.schema_version = schema_version
        self.state_path = state_path

    # --- Hashing ---
    def _hash_skills_dir(self) -> Dict[str, Any]:
        """
        Compute a stable hash of SKILL.md files under skills_dir.
        Uses relative path + mtime_ns + size + content hash to ensure updates
        to instructions are detected.
        """
        skills_dir = self.settings.get_effective_skills_dir()
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

    # --- Persistence helpers ---
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

    # --- Public API ---
    def build_current_state(self, embedding_signature: Dict[str, Any]) -> Dict[str, Any]:
        current = self._hash_skills_dir()
        return {
            "schema_version": self.schema_version,
            **embedding_signature,
            "skills_hash": current["hash"],
            "skill_count": current["count"],
        }

    def should_reindex(self, embedding_signature: Dict[str, Any], force: bool = False, skip_auto: bool = False):
        """
        Decide whether to rebuild the index.
        Returns dict with keys: need(bool), reason(str), state(dict), previous(dict|None)
        """
        current_state = self.build_current_state(embedding_signature)

        if force:
            return {"need": True, "reason": "force", "state": current_state, "previous": self._load_state()}

        if skip_auto:
            return {"need": False, "reason": "skip_auto", "state": current_state, "previous": self._load_state()}

        prev = self._load_state()
        if not prev:
            return {"need": True, "reason": "no_state", "state": current_state, "previous": prev}

        if prev.get("schema_version") != self.schema_version:
            return {"need": True, "reason": "schema_changed", "state": current_state, "previous": prev}

        if prev.get("embedding_provider") != embedding_signature.get("embedding_provider"):
            return {"need": True, "reason": "provider_changed", "state": current_state, "previous": prev}

        if prev.get("embedding_model") != embedding_signature.get("embedding_model"):
            return {"need": True, "reason": "model_changed", "state": current_state, "previous": prev}

        if prev.get("skills_hash") != current_state["skills_hash"]:
            return {"need": True, "reason": "hash_changed", "state": current_state, "previous": prev}

        return {"need": False, "reason": "unchanged", "state": current_state, "previous": prev}

    def persist(self, state: Dict[str, Any], skills_dir: Path, db_path: Path) -> None:
        payload = dict(state)
        payload["built_at"] = datetime.now(timezone.utc).isoformat()
        payload["skills_dir"] = str(skills_dir)
        payload["db_path"] = str(db_path)
        self._write_state(payload)
