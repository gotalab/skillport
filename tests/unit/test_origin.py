from skillport.modules.skills.internal import origin as origin_mod
from skillport.shared.config import Config


def test_record_and_remove_origin(tmp_path):
    cfg = Config(meta_dir=tmp_path)

    origin_mod.record_origin("abc", {"source": "local"}, config=cfg)
    path = tmp_path / "origins.json"
    assert path.exists()

    data = path.read_text(encoding="utf-8")
    assert "abc" in data
    assert str(cfg.skills_dir) in data

    origin_mod.remove_origin("abc", config=cfg)
    assert path.read_text(encoding="utf-8") == "{}"
