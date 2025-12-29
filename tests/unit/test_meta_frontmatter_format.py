from pathlib import Path

from skillport.interfaces.cli.commands.meta import _write_frontmatter
from skillport.shared.utils import parse_frontmatter


def test_write_frontmatter_is_readable_yaml(tmp_path: Path):
    skill_md = tmp_path / "SKILL.md"
    meta = {
        "name": "anthropic-design",
        "description": (
            "Applies warm, human-centered brand design with earth-tone colors (#C96442 accent, "
            "cream backgrounds) and serif/sans-serif typography pairing. Use when creating "
            "React/HTML artifacts, dashboards, landing pages, or UI components requiring a "
            "trustworthy, approachable aesthetic. Triggers: Anthropic style, Claude branding, "
            "warm design, brand colors, professional theme, human-centered UI, earth tones."
        ),
        "metadata": {"author": "gota"},
    }
    body = "# Skill\n\nHello.\n"

    _write_frontmatter(skill_md, meta, body)

    text = skill_md.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert '"name":' not in text
    assert '"description":' not in text
    assert '"metadata":' not in text
    assert "\\\n" not in text  # avoid PyYAML double-quoted line-wrap continuation

    parsed_meta, parsed_body = parse_frontmatter(skill_md)
    assert parsed_meta == meta
    assert parsed_body == body

