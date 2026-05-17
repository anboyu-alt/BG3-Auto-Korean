from pathlib import Path

from bg3core.mcm.loca_handles import mirror_korean_to_source_languages


def _make_loca(tmp_path, files):
    """files: dict {lang_name: {filename: content}}"""
    root = tmp_path / "mod"
    loc = root / "Localization"
    for lang, entries in files.items():
        lang_dir = loc / lang
        lang_dir.mkdir(parents=True)
        for name, content in entries.items():
            (lang_dir / name).write_text(content, encoding="utf-8")
    return root


def test_mirror_overwrites_english_with_korean(tmp_path):
    root = _make_loca(tmp_path, {
        "English": {"mod_en.xml": "<en/>"},
        "Korean": {"mod_en.xml": "<ko-translated/>"},
    })
    mirrored = mirror_korean_to_source_languages(root)
    assert mirrored == 1
    assert (root / "Localization" / "English" / "mod_en.xml").read_text(encoding="utf-8") == "<ko-translated/>"
    # Korean 폴더는 그대로
    assert (root / "Localization" / "Korean" / "mod_en.xml").read_text(encoding="utf-8") == "<ko-translated/>"


def test_mirror_skips_when_no_korean(tmp_path):
    root = _make_loca(tmp_path, {
        "English": {"mod_en.xml": "<en/>"},
    })
    mirrored = mirror_korean_to_source_languages(root)
    assert mirrored == 0
    assert (root / "Localization" / "English" / "mod_en.xml").read_text(encoding="utf-8") == "<en/>"


def test_mirror_only_when_target_has_same_name(tmp_path):
    """Korean에 있는 파일과 동명 파일이 있는 언어 폴더에만 덮어쓴다."""
    root = _make_loca(tmp_path, {
        "English": {"mod_en.xml": "<en/>"},
        "French": {"mod_fr.xml": "<fr/>"},  # 이름이 다름
        "Korean": {"mod_en.xml": "<ko-translated/>"},
    })
    mirror_korean_to_source_languages(root)
    # English는 덮어쓰기
    assert (root / "Localization" / "English" / "mod_en.xml").read_text(encoding="utf-8") == "<ko-translated/>"
    # French는 같은 이름 파일 없으므로 안 건드림
    assert (root / "Localization" / "French" / "mod_fr.xml").read_text(encoding="utf-8") == "<fr/>"
    assert not (root / "Localization" / "French" / "mod_en.xml").exists()


def test_mirror_multiple_localization_folders(tmp_path):
    """모드 안에 Localization 폴더가 여러 개 있을 때 모두 처리."""
    root = tmp_path / "mod"
    for sub in ["Mods/A", "Mods/B"]:
        d = root / sub / "Localization"
        (d / "English").mkdir(parents=True)
        (d / "Korean").mkdir(parents=True)
        (d / "English" / "x.xml").write_text("<en/>", encoding="utf-8")
        (d / "Korean" / "x.xml").write_text("<ko/>", encoding="utf-8")
    mirrored = mirror_korean_to_source_languages(root)
    assert mirrored == 2
