from bg3core.repair import (
    RepairResult, parse_content_blocks, base_stem, has_korean_localization,
)


def test_parse_content_blocks_basic():
    text = ('<content contentuid="h1" version="1">A</content>'
            '<content contentuid="h2">B</content>')
    blocks = parse_content_blocks(text)
    assert set(blocks) == {"h1", "h2"}
    assert blocks["h1"] == '<content contentuid="h1" version="1">A</content>'


def test_parse_content_blocks_self_closing():
    text = '<content contentuid="h3" version="1"/>'
    blocks = parse_content_blocks(text)
    assert "h3" in blocks


def test_base_stem_variants():
    assert base_stem("Foo.xml") == "Foo"
    assert base_stem("english.loca.xml") == "english"
    assert base_stem("english.loca") == "english"
    assert base_stem("Bar") == "Bar"


def test_has_korean_localization_true():
    entries = ["Mods/Foo/Localization/English/Foo.xml",
               "Mods/Foo/Localization/Korean/Foo.xml"]
    assert has_korean_localization(entries) is True


def test_has_korean_localization_backslash():
    assert has_korean_localization(["Mods\\Foo\\Localization\\Korean\\Foo.loca"]) is True


def test_has_korean_localization_false():
    entries = ["Mods/Foo/Localization/English/Foo.xml", "Public/Foo/Stats/x.txt"]
    assert has_korean_localization(entries) is False


def test_repair_result_defaults():
    r = RepairResult("x", False, 0, 0)
    assert r.unfixable == []
