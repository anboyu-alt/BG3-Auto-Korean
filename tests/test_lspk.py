"""bg3core.lspk — LSPK V18 `.pak` 읽기/쓰기 단위 테스트 (Divine 비의존).

순수 라운드트립 위주. Divine·BG3 설치가 있는 환경에서만 도는 인터롭 오라클은
tests/test_native_oracle.py 참고(없으면 자동 skip).
"""
import struct

import pytest

from bg3core import lspk


def _make_tree(root):
    (root / "Mods" / "Test" / "Localization" / "English").mkdir(parents=True)
    (root / "Mods" / "Test" / "meta.lsx").write_bytes(b"<save>meta</save>")
    # 압축이 잘 되는 큰 파일 + 작은 파일 + 비ASCII 경로 텍스트
    (root / "Mods" / "Test" / "big.txt").write_bytes(b"ABCDEF" * 5000)
    (root / "Mods" / "Test" / "small.bin").write_bytes(b"\x00\x01\x02\x03")
    (root / "Mods" / "Test" / "Localization" / "English" / "t.loca").write_bytes(
        b"LOCA" + b"\x00" * 8
    )


def test_roundtrip_extract_pack_extract(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_tree(src)
    pak = tmp_path / "out.pak"
    n = lspk.write_package(src, pak)
    assert n == 4

    out = tmp_path / "out"
    extracted = lspk.read_package(pak, out)
    assert extracted == 4
    for rel in [
        "Mods/Test/meta.lsx",
        "Mods/Test/big.txt",
        "Mods/Test/small.bin",
        "Mods/Test/Localization/English/t.loca",
    ]:
        assert (src / rel).read_bytes() == (out / rel).read_bytes()


def test_header_is_valid_lspk_v18(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_tree(src)
    pak = tmp_path / "out.pak"
    lspk.write_package(src, pak)
    data = pak.read_bytes()
    assert struct.unpack_from("<I", data, 0)[0] == lspk.LSPK_SIGNATURE
    version = struct.unpack_from("<I", data, 4)[0]
    assert version == lspk.LSPK_V18


def test_list_package_returns_slash_paths(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _make_tree(src)
    pak = tmp_path / "out.pak"
    lspk.write_package(src, pak)
    names = sorted(lspk.list_package(pak))
    assert "Mods/Test/meta.lsx" in names
    assert all("\\" not in n for n in names)


def test_compressible_file_is_stored_compressed(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_bytes(b"A" * 100000)
    pak = tmp_path / "out.pak"
    lspk.write_package(src, pak)
    [entry] = lspk.read_entries(pak)
    assert entry.flags & 0x0F == lspk._M_LZ4  # LZ4 method
    assert entry.size_on_disk < entry.uncompressed_size


def test_incompressible_small_file_stored_raw(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.bin").write_bytes(b"\x00\x01\x02")
    pak = tmp_path / "out.pak"
    lspk.write_package(src, pak)
    [entry] = lspk.read_entries(pak)
    # 작은/비압축 데이터는 method=None으로 저장(압축본이 더 커서)
    assert entry.flags & 0x0F == lspk._M_NONE


def test_bad_signature_raises(tmp_path):
    bad = tmp_path / "bad.pak"
    bad.write_bytes(b"XXXX" + b"\x00" * 40)
    with pytest.raises(ValueError):
        lspk.read_entries(bad)


def test_too_small_raises(tmp_path):
    bad = tmp_path / "bad.pak"
    bad.write_bytes(b"LSPK")
    with pytest.raises(ValueError):
        lspk.read_entries(bad)
