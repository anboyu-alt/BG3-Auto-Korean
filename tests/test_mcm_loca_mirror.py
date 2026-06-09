from pathlib import Path

from bg3core.mcm.loca_handles import mirror_loca_to_source_languages


def _make(tmp_path, files):
    """files: dict {lang_name: {filename: content}} — Localization 트리 생성."""
    root = tmp_path / "mod"
    loc = root / "Localization"
    for lang, entries in files.items():
        lang_dir = loc / lang
        lang_dir.mkdir(parents=True)
        for name, content in entries.items():
            (lang_dir / name).write_text(content, encoding="utf-8")
    return root


def test_mirror_copies_loca_and_preserves_english_xml(tmp_path):
    """.loca는 한글로 복사하되, 영어 .xml 원문은 그대로 보존한다(검수·원문 유지)."""
    root = _make(tmp_path, {
        "English": {"english.xml": "<en-source/>", "english.loca": "EN-LOCA"},
        "Korean": {"english.xml": "<ko/>", "english.loca": "KO-LOCA"},
    })
    mirrored = mirror_loca_to_source_languages(root)
    assert mirrored == 1
    loc = root / "Localization"
    # .loca는 한글 내용으로 덮어써짐
    assert (loc / "English" / "english.loca").read_text(encoding="utf-8") == "KO-LOCA"
    # .xml 영어 원문은 보존
    assert (loc / "English" / "english.xml").read_text(encoding="utf-8") == "<en-source/>"
    # Korean은 그대로
    assert (loc / "Korean" / "english.loca").read_text(encoding="utf-8") == "KO-LOCA"


def test_mirror_does_not_touch_xml_even_without_loca(tmp_path):
    """소스 폴더에 .loca가 없으면 아무것도 덮어쓰지 않고 .xml도 보존."""
    root = _make(tmp_path, {
        "English": {"english.xml": "<en-source/>"},  # .loca 없음
        "Korean": {"english.xml": "<ko/>", "english.loca": "KO-LOCA"},
    })
    mirrored = mirror_loca_to_source_languages(root)
    assert mirrored == 0
    loc = root / "Localization"
    assert (loc / "English" / "english.xml").read_text(encoding="utf-8") == "<en-source/>"
    assert not (loc / "English" / "english.loca").exists()


def test_mirror_skips_when_no_target_loca(tmp_path):
    root = _make(tmp_path, {
        "English": {"english.xml": "<en/>", "english.loca": "EN-LOCA"},
        "Korean": {"english.xml": "<ko/>"},  # target에 .loca 없음
    })
    mirrored = mirror_loca_to_source_languages(root)
    assert mirrored == 0
    assert (root / "Localization" / "English" / "english.loca").read_text(encoding="utf-8") == "EN-LOCA"


def test_mirror_only_when_prefix_matches(tmp_path):
    """prefix(파일명 베이스)가 같은 .loca에만 복사한다."""
    root = _make(tmp_path, {
        "English": {"english.loca": "EN-LOCA"},
        "French": {"french.loca": "FR-LOCA"},   # prefix 다름
        "Korean": {"english.loca": "KO-LOCA"},
    })
    mirror_loca_to_source_languages(root)
    loc = root / "Localization"
    assert (loc / "English" / "english.loca").read_text(encoding="utf-8") == "KO-LOCA"
    assert (loc / "French" / "french.loca").read_text(encoding="utf-8") == "FR-LOCA"


def test_mirror_multiple_localization_folders(tmp_path):
    root = tmp_path / "mod"
    for sub in ["Mods/A", "Mods/B"]:
        d = root / sub / "Localization"
        (d / "English").mkdir(parents=True)
        (d / "Korean").mkdir(parents=True)
        (d / "English" / "x.loca").write_text("EN", encoding="utf-8")
        (d / "Korean" / "x.loca").write_text("KO", encoding="utf-8")
    mirrored = mirror_loca_to_source_languages(root)
    assert mirrored == 2
