from skillport.modules.skills.internal.manager import add_local, detect_skills
from skillport.shared.config import Config


def test_add_local_custom_namespace(tmp_path):
    source = tmp_path / "collection"
    (source / "skill-a").mkdir(parents=True)
    (source / "skill-a" / "SKILL.md").write_text(
        "---\nname: skill-a\ndescription: A\n---\nbody", encoding="utf-8"
    )
    (source / "skill-b").mkdir(parents=True)
    (source / "skill-b" / "SKILL.md").write_text(
        "---\nname: skill-b\ndescription: B\n---\nbody", encoding="utf-8"
    )

    skills = detect_skills(source)
    target = tmp_path / "dest"
    cfg = Config(skills_dir=target)

    results = add_local(
        source_path=source,
        skills=skills,
        config=cfg,
        keep_structure=True,
        force=False,
        namespace_override="customns",
    )

    added_ids = [r.skill_id for r in results if r.success]
    assert set(added_ids) == {"customns/skill-a", "customns/skill-b"}
    assert (target / "customns" / "skill-a" / "SKILL.md").exists()
