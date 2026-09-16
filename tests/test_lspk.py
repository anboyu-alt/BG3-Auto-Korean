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


# ── 제보 3: 구버전 LSLib로 묶인 V15/V16 pak도 읽어야 한다 ─────────
_ENTRY15 = struct.Struct("<256sQQQIIII")  # FileEntry15 (296B) — V15/V16 공용


def _write_legacy_pak(path, version, files, stale_dup_first=False):
    """LSLib PackageWriter의 V15/V16 레이아웃을 흉내 낸 최소 pak 생성기.

    V15 헤더는 NumParts가 없고(34B), V16은 V18과 같은 36B 헤더를 쓴다.
    엔트리 테이블은 둘 다 FileEntry15(296B)이며 LZ4 블록으로 압축된다.
    stale_dup_first=True면 구버전 LSLib 라이터의 버그처럼 첫 파일의 엔트리를
    (오프셋 +64, 크기 −64로 어긋난) stale 복제본으로 하나 더 앞에 넣는다.
    """
    import lz4.block
    header_total = 4 + (34 if version == 15 else 36)
    blobs = []
    cursor = header_total
    entries = bytearray()
    for i, (name, raw) in enumerate(files):
        comp = lz4.block.compress(raw, mode="high_compression", store_size=False)
        blobs.append(comp)
        if i == 0 and stale_dup_first:
            entries += _ENTRY15.pack(
                name.encode("utf-8"), cursor + 64, len(comp) - 64, len(raw), 0, 0x22, 0, 0
            )
        entries += _ENTRY15.pack(
            name.encode("utf-8"), cursor, len(comp), len(raw), 0, 0x22, 0, 0
        )
        cursor += len(comp)
    table = lz4.block.compress(bytes(entries), mode="high_compression", store_size=False)
    with open(path, "wb") as f:
        f.write(struct.pack("<I", lspk.LSPK_SIGNATURE))
        if version == 15:
            f.write(struct.pack("<IQIBB16s", version, cursor, len(table) + 8, 0, 0, b"\x00" * 16))
        else:
            f.write(struct.pack("<IQIBB16sH", version, cursor, len(table) + 8, 0, 0, b"\x00" * 16, 1))
        for b in blobs:
            f.write(b)
        f.write(struct.pack("<II", len(files) + (1 if stale_dup_first else 0), len(table)))
        f.write(table)


@pytest.mark.parametrize("version", [15, 16])
def test_read_legacy_v15_v16_pak(tmp_path, version):
    files = [
        ("Mods/Legacy/meta.lsx", b"<save>meta</save>" * 20),
        ("Mods/Legacy/Localization/English/l.loca", b"LOCA" + b"\x01" * 100),
    ]
    pak = tmp_path / f"legacy_v{version}.pak"
    _write_legacy_pak(pak, version, files)

    assert lspk.list_package(pak) == [n for n, _ in files]
    out = tmp_path / "out"
    assert lspk.read_package(pak, out) == 2
    for name, raw in files:
        assert (out / name).read_bytes() == raw


def test_legacy_pak_with_stale_duplicate_entry(tmp_path):
    """실제 V16 모드에서 관측된 패턴: 첫 엔트리의 stale 복제본은 무시하고 유효본을 추출."""
    # 첫 파일은 압축본이 64B를 넘어야 stale 복제본(크기 −64)을 만들 수 있다.
    files = [("Mods/L/meta.lsx", bytes(range(256)) * 3), ("Mods/L/b.txt", b"B" * 300)]
    pak = tmp_path / "dup.pak"
    _write_legacy_pak(pak, 16, files, stale_dup_first=True)
    assert len(lspk.read_entries(pak)) == 3
    assert lspk.list_package(pak) == [n for n, _ in files]
    out = tmp_path / "out"
    assert lspk.read_package(pak, out) == 2
    assert (out / "Mods/L/meta.lsx").read_bytes() == files[0][1]


def test_unsupported_version_still_rejected(tmp_path):
    pak = tmp_path / "v13.pak"
    _write_legacy_pak(pak, 16, [("a.txt", b"x" * 50)])
    data = bytearray(pak.read_bytes())
    struct.pack_into("<I", data, 4, 13)
    pak.write_bytes(bytes(data))
    with pytest.raises(ValueError, match="unsupported .pak version 13"):
        lspk.read_entries(pak)


# ── 제보 4: 빈 파일에 LZ4 플래그가 붙은 엔트리(툴킷 모드의 빈 Stats txt) ─────────
def test_decompress_empty_entry_with_compression_flag():
    assert lspk._decompress(b"", 0, 0x12) == b""   # LZ4 fast
    assert lspk._decompress(b"", 0, 0x21) == b""   # zlib
    assert lspk._decompress(b"", 0, 0x00) == b""


def test_legacy_pak_with_empty_lz4_flagged_file(tmp_path):
    files = [("Public/M/Stats/Generated/Data/Spell_Target.txt", b""), ("Mods/M/meta.lsx", b"<save/>" * 30)]
    pak = tmp_path / "empty.pak"
    _write_legacy_pak(pak, 16, files)
    out = tmp_path / "out"
    assert lspk.read_package(pak, out) == 2
    assert (out / files[0][0]).read_bytes() == b""
