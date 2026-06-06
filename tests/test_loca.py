from pathlib import Path
from bg3core.divine import plan_loca_generation


def _mk(p: Path, content: str = "x") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_plain_xml_missing_loca(tmp_path):
    x = tmp_path / "Localization" / "Korean" / "Foo.xml"
    _mk(x)
    plan = plan_loca_generation(tmp_path)
    assert len(plan) == 1
    src, out = plan[0]
    assert src == x
    assert out == tmp_path / "Localization" / "Korean" / "Foo.loca"


def test_existing_loca_skipped(tmp_path):
    _mk(tmp_path / "Localization" / "Korean" / "Foo.xml")
    _mk(tmp_path / "Localization" / "Korean" / "Foo.loca")
    assert plan_loca_generation(tmp_path) == []


def test_dual_xml_dedup_prefers_plain(tmp_path):
    x = tmp_path / "Localization" / "Korean" / "Artificer.xml"
    lx = tmp_path / "Localization" / "Korean" / "Artificer.loca.xml"
    _mk(x)
    _mk(lx)
    plan = plan_loca_generation(tmp_path)
    assert len(plan) == 1
    src, out = plan[0]
    assert out == tmp_path / "Localization" / "Korean" / "Artificer.loca"
    assert src == x  # plain .xml preferred as source


def test_loca_xml_only(tmp_path):
    lx = tmp_path / "Localization" / "English" / "english.loca.xml"
    _mk(lx)
    plan = plan_loca_generation(tmp_path)
    assert len(plan) == 1
    src, out = plan[0]
    assert src == lx
    assert out == tmp_path / "Localization" / "English" / "english.loca"


def test_xml_outside_localization_ignored(tmp_path):
    _mk(tmp_path / "Public" / "Foo" / "meta.xml")
    _mk(tmp_path / "Mods" / "Foo" / "something.xml")
    assert plan_loca_generation(tmp_path) == []


def test_multiple_language_folders(tmp_path):
    _mk(tmp_path / "Localization" / "English" / "M.xml")
    _mk(tmp_path / "Localization" / "Korean" / "M.xml")
    plan = plan_loca_generation(tmp_path)
    outs = sorted(str(o) for _, o in plan)
    assert len(plan) == 2
    assert any("English" in o and o.endswith("M.loca") for o in outs)
    assert any("Korean" in o and o.endswith("M.loca") for o in outs)


def test_mt_gen_loca_naming(tmp_path):
    x = tmp_path / "Localization" / "Korean" / "__MT_GEN_LOCA_abc.xml"
    _mk(x)
    plan = plan_loca_generation(tmp_path)
    assert plan[0][1].name == "__MT_GEN_LOCA_abc.loca"
