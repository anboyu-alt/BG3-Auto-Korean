"""Localization 폴더의 .loca/.loca.xml 정리 검증.

BG3 모드는 .xml만으로 작동(공식 가이드)이므로 패킹 직전 .loca와 .loca.xml은
정리해 깔끔하게 .xml만 남긴다.
"""

from pathlib import Path

from bg3core.divine import strip_loca_artifacts


def _make(tmp_path, files):
    """files: dict { 'Localization/Korean/x.xml': 'content', ... }"""
    root = tmp_path / "mod"
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return root


def test_removes_loca_binaries(tmp_path):
    root = _make(tmp_path, {
        "Localization/Korean/english.loca": "binary",
        "Localization/Korean/english.xml": "<korean/>",
    })
    n = strip_loca_artifacts(root)
    assert n == 1
    assert not (root / "Localization/Korean/english.loca").exists()
    assert (root / "Localization/Korean/english.xml").exists()


def test_removes_loca_xml_when_xml_sibling_exists(tmp_path):
    root = _make(tmp_path, {
        "Localization/Korean/english.xml": "<korean/>",
        "Localization/Korean/english.loca.xml": "<en-loca/>",
    })
    n = strip_loca_artifacts(root)
    assert n == 1
    assert (root / "Localization/Korean/english.xml").exists()
    assert not (root / "Localization/Korean/english.loca.xml").exists()


def test_renames_loca_xml_when_no_xml_sibling(tmp_path):
    """원본 PAK에 .loca만 있고 .xml이 없는 모드의 경우, .loca.xml을 .xml로 rename."""
    root = _make(tmp_path, {
        "Localization/English/english.loca.xml": "<en/>",
    })
    n = strip_loca_artifacts(root)
    assert n == 1
    assert (root / "Localization/English/english.xml").exists()
    assert not (root / "Localization/English/english.loca.xml").exists()


def test_skips_non_localization_paths(tmp_path):
    """Localization 폴더 밖의 .loca/.loca.xml은 건드리지 않는다."""
    root = _make(tmp_path, {
        "Public/foo.loca": "binary",
        "Stats/bar.loca.xml": "<x/>",
        "Localization/Korean/english.xml": "<korean/>",
        "Localization/Korean/english.loca.xml": "<en-loca/>",
    })
    strip_loca_artifacts(root)
    # Localization 밖은 그대로
    assert (root / "Public/foo.loca").exists()
    assert (root / "Stats/bar.loca.xml").exists()
    # Localization 안은 정리됨
    assert not (root / "Localization/Korean/english.loca.xml").exists()


def test_multiple_localization_folders(tmp_path):
    """모드 안에 여러 Localization 폴더가 있을 때 모두 처리."""
    root = _make(tmp_path, {
        "Mods/A/Localization/Korean/x.xml": "<ko/>",
        "Mods/A/Localization/Korean/x.loca.xml": "<en/>",
        "Mods/B/Localization/English/y.loca.xml": "<en/>",  # .xml 없음 → rename
    })
    n = strip_loca_artifacts(root)
    assert n == 2
    assert not (root / "Mods/A/Localization/Korean/x.loca.xml").exists()
    assert (root / "Mods/B/Localization/English/y.xml").exists()
