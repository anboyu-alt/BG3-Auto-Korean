"""BG3 `.pak`(LSPK V18) 읽기/쓰기 (Divine 비의존, 순수 Python).

LSLib `LS/PackageFormat.cs`(LSPKHeader16/FileEntry18)·PackageReader/Writer를 포팅했다.
모든 정수는 리틀엔디언, 구조체는 Pack=1.

레이아웃:
  - 오프셋 0: 시그니처 'LSPK' u32 = 0x4B50534C
  - 헤더(36B): Version u32, FileListOffset u64, FileListSize u32, Flags u8, Priority u8,
    Md5[16], NumParts u16  → 총합 40B(HEADER_TOTAL) 뒤부터 데이터 영역
  - 파일리스트(FileListOffset): NumFiles u32, CompressedSize u32, LZ4블록(엔트리테이블)
    엔트리테이블 = NumFiles × FileEntry18(272B)
  - FileEntry18: Name[256](UTF-8 null-term), Off1 u32, Off2 u16, ArchivePart u8,
    Flags u8(압축), SizeOnDisk u32, UncompressedSize u32
    실제 오프셋 = Off1 | (Off2 << 32) — BG3 단일파트는 파일 시작 기준 절대값

구버전(V15/V16, 2023년 이전 LSLib로 묶인 모드) 읽기도 지원한다. 게임은 이 버전을
그대로 로드하므로 번역 도구도 읽어야 한다(쓰기는 항상 V18):
  - V15 헤더(34B): NumParts 없음. V16 헤더는 V18과 동일(36B).
  - 엔트리 테이블은 둘 다 FileEntry15(296B): Name[256], OffsetInFile u64,
    SizeOnDisk u64, UncompressedSize u64, ArchivePart u32, Flags u32, Crc u32, Unknown2 u32
  - 구버전 LSLib 라이터는 첫 파일의 엔트리를 하나 더(오프셋 +64, 크기 −64로 어긋난
    stale 항목) 남긴다. 실측: 이 PC의 V16 모드 6개 전부 동일 패턴. 게임은 이런 pak을
    정상 로드하므로, 같은 이름이 여럿이면 뒤에서부터 압축 해제가 되는 항목을 택한다.

압축 플래그(하위 니블=method, 상위 니블=level): None=0, Zlib=1, LZ4=2, Zstd=3.
zstd는 디코드만 지원(선택 의존 `zstandard`); BG3 모드/공식팩은 LZ4가 표준이다.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

import lz4.block as _lz4

LSPK_SIGNATURE = 0x4B50534C  # 'LSPK'
LSPK_V15 = 15
LSPK_V16 = 16
LSPK_V18 = 18
SUPPORTED_READ_VERSIONS = (LSPK_V15, LSPK_V16, LSPK_V18)

_HEADER = struct.Struct("<IQIBB16sH")        # 36B (시그니처 제외) — V16/V18
_HEADER15 = struct.Struct("<IQIBB16s")       # 34B — V15 (NumParts 없음)
_ENTRY = struct.Struct("<256sIHBBII")        # 272B — FileEntry18
_ENTRY15 = struct.Struct("<256sQQQIIII")     # 296B — FileEntry15 (V15/V16)
HEADER_SIZE = _HEADER.size                   # 36
HEADER_TOTAL = 4 + HEADER_SIZE               # 40 (시그니처 포함, 데이터 시작 오프셋)
ENTRY_SIZE = _ENTRY.size                     # 272
ENTRY15_SIZE = _ENTRY15.size                 # 296

# 압축 method/level 플래그
_M_NONE, _M_ZLIB, _M_LZ4, _M_ZSTD = 0, 1, 2, 3
_LEVEL_DEFAULT = 0x20

# PackageFlags
_FLAG_SOLID = 0x04

# 삭제 마커(패치 pak) — 해당 엔트리는 추출 제외
_DELETION_MASK = 0x0000FFFFFFFFFFFF
_DELETION_MARKER = 0xBEEFDEADBEEF


@dataclass
class FileEntry:
    name: str
    offset: int
    archive_part: int
    flags: int
    size_on_disk: int
    uncompressed_size: int


def _decompress(buf: bytes, uncompressed_size: int, flags: int) -> bytes:
    # 빈 파일(크기 0)에도 LSLib·툴킷은 압축 플래그를 그대로 붙인다(예: 빈 Stats txt).
    # python-lz4는 빈 입력 해제를 에러로 취급하므로 먼저 빈 결과로 돌려준다.
    if uncompressed_size == 0 or not buf:
        return b""
    method = flags & 0x0F
    if method == _M_NONE:
        return buf
    if method == _M_ZLIB:
        return zlib.decompress(buf)
    if method == _M_LZ4:
        return _lz4.decompress(buf, uncompressed_size=uncompressed_size)
    if method == _M_ZSTD:
        try:
            import zstandard
        except ImportError as e:  # pragma: no cover - 드문 경로
            raise RuntimeError(
                "zstd-compressed .pak entry requires the 'zstandard' package"
            ) from e
        return zstandard.ZstdDecompressor().decompress(
            buf, max_output_size=uncompressed_size
        )
    raise ValueError(f"unsupported compression method: {method}")


def _compress(raw: bytes) -> tuple[bytes, int]:
    """LZ4 블록으로 압축. 압축본이 더 크면 무압축(method=None)으로 저장."""
    if not raw:
        return b"", _M_NONE
    comp = _lz4.compress(raw, mode="high_compression", store_size=False)
    if len(comp) >= len(raw):
        return raw, _M_NONE
    return comp, _M_LZ4 | _LEVEL_DEFAULT


def _is_deletion(offset: int) -> bool:
    return (offset & _DELETION_MASK) == _DELETION_MARKER


# ── 읽기 ───────────────────────────────────────────────────
def read_entries(pak_path: Union[str, Path]) -> List[FileEntry]:
    """추출 없이 파일 엔트리 메타데이터만 읽는다."""
    with open(pak_path, "rb") as f:
        head = f.read(HEADER_TOTAL)
        if len(head) < HEADER_TOTAL:
            raise ValueError(f"not a valid .pak (too small): {pak_path}")
        sig = struct.unpack_from("<I", head, 0)[0]
        if sig != LSPK_SIGNATURE:
            raise ValueError(f"not a valid .pak (bad signature 0x{sig:08x}): {pak_path}")
        version = struct.unpack_from("<I", head, 4)[0]
        if version not in SUPPORTED_READ_VERSIONS:
            raise ValueError(
                f"unsupported .pak version {version} (supported: V15/V16/V18)"
            )
        if version == LSPK_V15:
            _v, file_list_offset, _flsize, flags, _prio, _md5 = _HEADER15.unpack_from(head, 4)
            num_parts = 1
        else:
            _v, file_list_offset, _flsize, flags, _prio, _md5, num_parts = (
                _HEADER.unpack_from(head, 4)
            )
        if flags & _FLAG_SOLID:
            raise ValueError(f"solid-mode .pak not supported: {pak_path}")
        if num_parts > 1:
            raise ValueError(f"multi-part .pak not supported: {pak_path}")
        return _read_file_table(f, file_list_offset, version)


def _name_of(name_raw: bytes) -> str:
    nul = name_raw.find(b"\x00")
    return name_raw[: nul if nul >= 0 else len(name_raw)].decode("utf-8", "replace")


def _read_file_table(f, offset: int, version: int = LSPK_V18) -> List[FileEntry]:
    f.seek(offset)
    num_files, comp_size = struct.unpack("<II", f.read(8))
    compressed = f.read(comp_size)
    entries: List[FileEntry] = []
    if version == LSPK_V18:
        table = _lz4.decompress(compressed, uncompressed_size=num_files * ENTRY_SIZE)
        for i in range(num_files):
            name_raw, off1, off2, apart, eflags, sod, unc = _ENTRY.unpack_from(
                table, i * ENTRY_SIZE
            )
            entries.append(
                FileEntry(_name_of(name_raw), off1 | (off2 << 32), apart, eflags, sod, unc)
            )
    else:  # V15/V16 — FileEntry15
        table = _lz4.decompress(compressed, uncompressed_size=num_files * ENTRY15_SIZE)
        for i in range(num_files):
            name_raw, off, sod, unc, apart, eflags, _crc, _unk = _ENTRY15.unpack_from(
                table, i * ENTRY15_SIZE
            )
            entries.append(FileEntry(_name_of(name_raw), off, apart, eflags, sod, unc))
    return entries


def _group_by_name(entries: List[FileEntry]) -> "dict[str, List[FileEntry]]":
    """슬래시 정규화한 이름별로 엔트리를 등장 순서대로 묶는다(삭제 마커·타 파트 제외)."""
    groups: dict = {}
    for e in entries:
        if e.archive_part != 0 or _is_deletion(e.offset):
            continue
        groups.setdefault(e.name.replace("\\", "/"), []).append(e)
    return groups


def list_package(pak_path: Union[str, Path]) -> List[str]:
    """pak 내부 파일 경로 목록(슬래시 정규화, 중복 이름은 한 번만)."""
    return list(_group_by_name(read_entries(pak_path)).keys())


def read_package(pak_path: Union[str, Path], dest_dir: Union[str, Path]) -> int:
    """pak을 dest_dir에 추출. 추출한 파일 수 반환."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    extracted = 0
    with open(pak_path, "rb") as f:
        for name, candidates in _group_by_name(read_entries(pak_path)).items():
            # 같은 이름이 여럿이면 마지막 항목부터 시도한다(패치·덮어쓰기 의미론).
            # 구버전 LSLib의 stale 중복 엔트리는 압축 해제에 실패하므로 자연히 걸러진다.
            raw = None
            last_err: Optional[Exception] = None
            for e in reversed(candidates):
                f.seek(e.offset)
                blob = f.read(e.size_on_disk)
                try:
                    raw = _decompress(blob, e.uncompressed_size, e.flags)
                    break
                except Exception as err:  # zlib.error / lz4 error / ValueError
                    last_err = err
            if raw is None:
                raise ValueError(f"cannot decompress entry {name!r}: {last_err}")
            out_path = dest / name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(raw)
            extracted += 1
    return extracted


# ── 쓰기 ───────────────────────────────────────────────────
def write_package(src_dir: Union[str, Path], out_pak: Union[str, Path]) -> int:
    """src_dir 트리를 LSPK V18 pak으로 패킹. 패킹한 파일 수 반환.

    엔트리 이름은 src_dir 기준 상대경로(슬래시). 블롭은 LZ4 압축(또는 무압축),
    헤더(40B) 뒤부터 연속 배치(오프셋 명시). 파일리스트는 LZ4 압축.
    """
    src = Path(src_dir)
    files = sorted(
        (p for p in src.rglob("*") if p.is_file()),
        key=lambda p: str(p.relative_to(src)).replace("\\", "/").lower(),
    )
    out_pak = Path(out_pak)
    out_pak.parent.mkdir(parents=True, exist_ok=True)

    with open(out_pak, "wb") as f:
        f.write(b"\x00" * HEADER_TOTAL)  # 헤더 자리 예약(끝에서 되돌아 기록)
        cursor = HEADER_TOTAL
        entries: List[FileEntry] = []
        for p in files:
            rel = str(p.relative_to(src)).replace("\\", "/")
            name_b = rel.encode("utf-8")
            if len(name_b) >= 256:
                raise ValueError(f"file name too long for LSPK entry (>=256B): {rel}")
            raw = p.read_bytes()
            blob, method = _compress(raw)
            f.write(blob)
            entries.append(
                FileEntry(rel, cursor, 0, method, len(blob), len(raw))
            )
            cursor += len(blob)

        file_list_offset = cursor
        table = bytearray()
        for e in entries:
            table += _ENTRY.pack(
                e.name.encode("utf-8"),
                e.offset & 0xFFFFFFFF,
                (e.offset >> 32) & 0xFFFF,
                0,
                e.flags,
                e.size_on_disk,
                e.uncompressed_size,
            )
        compressed_table = _lz4.compress(
            bytes(table), mode="high_compression", store_size=False
        )
        f.write(struct.pack("<II", len(entries), len(compressed_table)))
        f.write(compressed_table)
        file_list_size = len(compressed_table) + 8

        f.seek(0)
        f.write(struct.pack("<I", LSPK_SIGNATURE))
        f.write(
            _HEADER.pack(
                LSPK_V18, file_list_offset, file_list_size, 0, 0, b"\x00" * 16, 1
            )
        )
    return len(entries)
