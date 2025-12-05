from pathlib import Path

from skillport.modules.skills import add_skill
from skillport.shared.config import Config


def _write_skill(dir_path: Path, dir_name: str, skill_name: str) -> Path:
    skill_dir = dir_path / dir_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {skill_name}\ndescription: test\n---\n",
        encoding="utf-8",
    )
    return skill_dir


def test_prefetched_dir_cleanup_after_rename(tmp_path: Path):
    """Ensure pre_fetched_dir is cleaned when renamed for single-skill repos."""
    download_dir = tmp_path / "download"
    download_dir.mkdir()
    prefetched = _write_skill(download_dir, "temp-repo", "renamed-skill")

    cfg = Config(
        skills_dir=tmp_path / "skills",
        db_path=tmp_path / "index" / "skills.lancedb",
    )

    result = add_skill(
        "https://github.com/example/repo",
        config=cfg,
        pre_fetched_dir=prefetched,
    )

    assert "temp-repo" not in result.added  # renamed
    assert "renamed-skill" in result.added

    # Temp extraction directory (renamed internally) should be removed
    assert not prefetched.exists()
    assert not (download_dir / "renamed-skill").exists()

    # Skill should be copied into target skills_dir
    assert (cfg.skills_dir / "renamed-skill" / "SKILL.md").exists()
