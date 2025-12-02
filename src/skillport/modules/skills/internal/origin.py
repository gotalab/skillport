import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from skillport.shared.config import Config


def _path_for_config(config: Config):
    return (config.meta_dir / "origins.json").expanduser().resolve()


def _load(config: Config) -> Dict[str, Any]:
    path = _path_for_config(config)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        print(f"[WARN] Failed to load origins.json: {exc}", file=sys.stderr)
    return {}


def _save(config: Config, data: Dict[str, Any]) -> None:
    path = _path_for_config(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_origin(skill_id: str, payload: Dict[str, Any], *, config: Config) -> None:
    data = _load(config)
    enriched = dict(payload)
    enriched.setdefault("added_at", datetime.now(timezone.utc).isoformat())
    enriched.setdefault("skills_dir", str(config.skills_dir))
    data[skill_id] = enriched
    _save(config, data)


def remove_origin(skill_id: str, *, config: Config) -> None:
    data = _load(config)
    if skill_id in data:
        del data[skill_id]
        _save(config, data)
