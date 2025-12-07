import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skillport.shared.config import Config


class IndexStateStore:
    """Persists and compares index state."""

    def __init__(self, config: Config, schema_version: str, state_path: Path):
        self.config = config
        self.schema_version = schema_version
        self.state_path = state_path

    # --- hashing ---
    def _hash_skills_dir(self) -> dict[str, Any]:
        skills_dir = self.config.skills_dir
        entries: list[str] = []

        if not skills_dir.exists():
            return {"hash": "", "count": 0}

        for pattern in ("*/SKILL.md", "*/*/SKILL.md"):
            for skill_md in skills_dir.glob(pattern):
                try:
                    st = skill_md.stat()
                except FileNotFoundError:
                    continue
                try:
                    body_digest = hashlib.sha1(skill_md.read_bytes()).hexdigest()
                except Exception:
                    body_digest = "err"
                rel = skill_md.relative_to(skills_dir)
                entries.append(f"{rel.as_posix()}:{st.st_mtime_ns}:{st.st_size}:{body_digest}")

        entries.sort()
        joined = "|".join(entries)
        digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
        return {"hash": f"sha256:{digest}", "count": len(entries)}

    # --- IO helpers ---
    def _load_state(self) -> dict[str, Any] | None:
        if not self.state_path.exists():
            return None
        try:
            with open(self.state_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            print(f"Failed to load index state: {exc}", file=sys.stderr)
            return None

    def _write_state(self, state: dict[str, Any]) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"Failed to write index state: {exc}", file=sys.stderr)

    # --- public ---
    def build_current_state(self, embedding_signature: dict[str, Any]) -> dict[str, Any]:
        current = self._hash_skills_dir()
        return {
            "schema_version": self.schema_version,
            **embedding_signature,
            "skills_hash": current["hash"],
            "skill_count": current["count"],
        }

    def should_reindex(
        self,
        embedding_signature: dict[str, Any],
        *,
        force: bool = False,
        skip_auto: bool = False,
    ):
        current_state = self.build_current_state(embedding_signature)

        if force:
            return {
                "need": True,
                "reason": "force",
                "state": current_state,
                "previous": self._load_state(),
            }
        if skip_auto:
            return {
                "need": False,
                "reason": "skip_auto",
                "state": current_state,
                "previous": self._load_state(),
            }

        prev = self._load_state()
        if not prev:
            return {
                "need": True,
                "reason": "no_state",
                "state": current_state,
                "previous": prev,
            }

        if prev.get("schema_version") != self.schema_version:
            return {
                "need": True,
                "reason": "schema_changed",
                "state": current_state,
                "previous": prev,
            }
        if prev.get("embedding_provider") != embedding_signature.get("embedding_provider"):
            return {
                "need": True,
                "reason": "provider_changed",
                "state": current_state,
                "previous": prev,
            }
        if prev.get("embedding_model") != embedding_signature.get("embedding_model"):
            return {
                "need": True,
                "reason": "model_changed",
                "state": current_state,
                "previous": prev,
            }
        if prev.get("skills_hash") != current_state["skills_hash"]:
            return {
                "need": True,
                "reason": "hash_changed",
                "state": current_state,
                "previous": prev,
            }

        return {
            "need": False,
            "reason": "unchanged",
            "state": current_state,
            "previous": prev,
        }

    def persist(self, state: dict[str, Any], *, skills_dir: Path, db_path: Path) -> None:
        payload = dict(state)
        payload["built_at"] = datetime.now(timezone.utc).isoformat()
        payload["skills_dir"] = str(skills_dir)
        payload["db_path"] = str(db_path)
        self._write_state(payload)
