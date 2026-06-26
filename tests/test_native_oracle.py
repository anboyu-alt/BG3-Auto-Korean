"""네이티브 pak/loca를 Divine·실제 게임 파일과 대조하는 오라클 테스트.

Divine.exe와 BG3 설치가 모두 있을 때만 실행되며, 없으면 전체 모듈을 skip한다.
(CI/일반 개발 환경에서는 자동으로 건너뛴다.)
"""
import subprocess
import tempfile
from pathlib import Path

import pytest

from bg3core import lspk, loca
from bg3core.config import load_config

_cfg = load_config()
_DIVINE = _cfg.divine_exe_path
_BG3 = _cfg.bg3_install_path

pytestmark = pytest.mark.skipif(
    not (_DIVINE and Path(_DIVINE).is_file() and _BG3 and Path(_BG3).is_dir()),
    reason="Divine.exe / BG3 install not available",
)


def _divine(*args, timeout=120):
    r = subprocess.run(
        [_DIVINE, "-g", "bg3", *args], capture_output=True, text=True, timeout=timeout
    )
    return r.returncode


def _english_pak():
    loc = Path(_BG3) / "Data" / "Localization"
    cands = list(loc.glob("English.pak")) + list((loc / "English").glob("*.pak"))
    return cands[0] if cands else None


def test_read_official_english_pak_and_parse_loca():
    pak = _english_pak()
    if pak is None:
        pytest.skip("English.pak not found")
    entries = lspk.read_entries(pak)
    big = max(entries, key=lambda e: e.size_on_disk)
    with open(pak, "rb") as f:
        f.seek(big.offset)
        raw = lspk._decompress(f.read(big.size_on_disk), big.uncompressed_size, big.flags)
    assert raw[:4] == b"LOCA"
    texts = loca.read_loca(raw)
    assert len(texts) > 100000  # 공식 영어는 20만+ 엔트리
    joined = "\n".join(t.text for t in texts[:30000])
    assert "Fireball" in joined


def test_divine_reads_our_written_pak(tmp_path):
    # 우리가 쓴 pak을 Divine이 읽을 수 있어야 한다(인터롭).
    src = tmp_path / "src"
    (src / "Mods" / "T" / "Localization" / "English").mkdir(parents=True)
    (src / "Mods" / "T" / "meta.lsx").write_bytes(b"<save/>")
    (src / "Mods" / "T" / "big.txt").write_bytes(b"hello " * 4000)
    (src / "Mods" / "T" / "Localization" / "English" / "t.loca").write_bytes(
        loca.write_loca([loca.LocalizedText("h1", 1, "Fireball")])
    )
    pak = tmp_path / "ours.pak"
    lspk.write_package(src, pak)

    assert _divine("-a", "list-package", "-s", str(pak)) == 0
    out = tmp_path / "divine_out"
    assert _divine("-a", "extract-package", "-s", str(pak), "-d", str(out), "-l", "all") == 0
    for rel in ["Mods/T/meta.lsx", "Mods/T/big.txt", "Mods/T/Localization/English/t.loca"]:
        assert (src / rel).read_bytes() == (out / rel).read_bytes()


def test_loca_conversion_matches_divine(tmp_path):
    # 작은 .loca를 우리/Divine 양쪽으로 xml 변환 → 파싱 결과 동일.
    ents = [
        loca.LocalizedText("hA", 1, 'A <LSTag Tooltip="Strength">Force</LSTag> & co'),
        loca.LocalizedText("hB", 2, "Plain text"),
    ]
    lf = tmp_path / "x.loca"
    lf.write_bytes(loca.write_loca(ents))
    xo = tmp_path / "divine.xml"
    assert _divine("-a", "convert-loca", "-s", str(lf), "-d", str(xo)) == 0
    divine_dict = {t.key: t.text for t in loca.from_xml(xo.read_text(encoding="utf-8"))}
    our_dict = {t.key: t.text for t in ents}
    assert divine_dict == our_dict
