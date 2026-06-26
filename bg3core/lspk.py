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

압축 플래그(하위 니블=method, 상위 니블=level): None=0, Zlib=1, LZ4=2, Zstd=3.
zstd는 디코드만 지원(선택 의존 `zstandard`); BG3 모드/공식팩은 LZ4가 표준이다.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

import lz4.block as _lz4

LSPK_SIGNATURE = 0x4B50534C  # 'LSPK'
LSPK_V18 = 18

_HEADER = struct.Struct("<IQIBB16sH")        # 36B (시그니처 제외)
_ENTRY = struct.Struct("<256sIHBBII")        # 272B
HEADER_SIZE = _HEADER.size                   # 36
HEADER_TOTAL = 4 + HEADER_SIZE               # 40 (시그니처 포함, 데이터 시작 오프셋)
ENTRY_SIZE = _ENTRY.size                     # 272

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
        version, file_list_offset, _flsize, flags, _prio, _md5, num_parts = (
            _HEADER.unpack_from(head, 4)
        )
        if version != LSPK_V18:
            raise ValueError(f"unsupported .pak version {version} (only V18/BG3)")
        if flags & _FLAG_SOLID:
            raise ValueError(f"solid-mode .pak not supported: {pak_path}")
        if num_parts > 1:
            raise ValueError(f"multi-part .pak not supported: {pak_path}")
        return _read_file_table(f, file_list_offset)


def _read_file_table(f, offset: int) -> List[FileEntry]:
    f.seek(offset)
    num_files, comp_size = struct.unpack("<II", f.read(8))
    compressed = f.read(comp_size)
    table = _lz4.decompress(compressed, uncompressed_size=num_files * ENTRY_SIZE)
    entries: List[FileEntry] = []
    for i in range(num_files):
        name_raw, off1, off2, apart, eflags, sod, unc = _ENTRY.unpack_from(
            table, i * ENTRY_SIZE
        )
        nul = name_raw.find(b"\x00")
        name = name_raw[: nul if nul >= 0 else len(name_raw)].decode("utf-8", "replace")
        entries.append(
            FileEntry(name, off1 | (off2 << 32), apart, eflags, sod, unc)
        )
    return entries


def list_package(pak_path: Union[str, Path]) -> List[str]:
    """pak 내부 파일 경로 목록(슬래시 정규화)."""
    return [e.name.replace("\\", "/") for e in read_entries(pak_path)]


def read_package(pak_path: Union[str, Path], dest_dir: Union[str, Path]) -> int:
    """pak을 dest_dir에 추출. 추출한 파일 수 반환."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    extracted = 0
    with open(pak_path, "rb") as f:
        for e in read_entries(pak_path):
            if e.archive_part != 0 or _is_deletion(e.offset):
                continue
            f.seek(e.offset)
            blob = f.read(e.size_on_disk)
            raw = _decompress(blob, e.uncompressed_size, e.flags)
            out_path = dest / e.name.replace("\\", "/")
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
