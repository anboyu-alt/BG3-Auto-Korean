"""BG3 `.loca` 바이너리 ↔ XML 변환 (Divine 비의존, 순수 Python).

LSLib `LS/Localization.cs`를 충실히 포팅했다. 바이너리 레이아웃(리틀엔디언, Pack=1):
  - LocaHeader(12B): Signature u32 = 0x41434F4C('LOCA'), NumEntries u32, TextsOffset u32
  - LocaEntry(70B): Key byte[64](UTF-8, null-pad), Version u16, Length u32(= UTF-8 바이트수 + 1)
  - 텍스트 영역(TextsOffset부터): 엔트리 순서대로 (Length-1) 바이트 UTF-8 + null(0x00)

중요: 바이너리 `.loca`의 텍스트는 **raw**(예: `<LSTag ...>...</LSTag>`)로 저장되고,
`.loca.xml`에서는 XML 이스케이프(`&lt;LSTag&gt;`)된다. 우리 번역 파이프라인은
이스케이프 형태를 가정하므로, to_xml은 이스케이프하고 from_xml은 역이스케이프한다.

XML 형식은 Divine 출력과 동일: `<contentList>` 루트, 자식 `<content contentuid="..."
version="...">TEXT</content>`. 파이프라인의 CONTENT_BLOCK_RE/CONTENT_INNER_RE와 호환.
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union
from xml.sax.saxutils import escape as _xml_escape, unescape as _xml_unescape

LOCA_SIGNATURE = 0x41434F4C  # 'LOCA' (리틀엔디언)

_HEADER = struct.Struct("<III")    # signature, num_entries, texts_offset
_ENTRY = struct.Struct("<64sHI")   # key[64], version u16, length u32
HEADER_SIZE = _HEADER.size         # 12
ENTRY_SIZE = _ENTRY.size           # 70

# <content ...>inner</content> (또는 self-closing). 속성에서 uid/version 추출.
_BLOCK_RE = re.compile(
    r"<content\b([^>]*?)(?:/\s*>|>(.*?)</content>)",
    re.DOTALL | re.IGNORECASE,
)
_UID_RE = re.compile(r'contentuid="([^"]*)"', re.IGNORECASE)
_VER_RE = re.compile(r'version="([^"]*)"', re.IGNORECASE)


@dataclass
class LocalizedText:
    key: str
    version: int
    text: str


# ── 바이너리 ───────────────────────────────────────────────
def read_loca(data: bytes) -> List[LocalizedText]:
    """`.loca` 바이트를 파싱해 LocalizedText 목록을 반환."""
    if len(data) < HEADER_SIZE:
        raise ValueError("loca too small for header")
    sig, num, texts_off = _HEADER.unpack_from(data, 0)
    if sig != LOCA_SIGNATURE:
        raise ValueError(f"bad LOCA signature: 0x{sig:08x}")

    meta = []
    off = HEADER_SIZE
    for _ in range(num):
        key_raw, version, length = _ENTRY.unpack_from(data, off)
        off += ENTRY_SIZE
        nul = key_raw.find(b"\x00")
        key = key_raw[: nul if nul >= 0 else len(key_raw)].decode("utf-8", "replace")
        meta.append((key, version, length))

    result: List[LocalizedText] = []
    pos = texts_off
    for key, version, length in meta:
        text_len = length - 1 if length > 0 else 0
        raw = data[pos : pos + text_len]
        pos += text_len + 1  # null 종단 1바이트 건너뜀
        result.append(LocalizedText(key, version, raw.decode("utf-8", "replace")))
    return result


def write_loca(entries: List[LocalizedText]) -> bytes:
    """LocalizedText 목록을 `.loca` 바이트로 직렬화."""
    num = len(entries)
    texts_offset = HEADER_SIZE + ENTRY_SIZE * num
    out = bytearray()
    out += _HEADER.pack(LOCA_SIGNATURE, num, texts_offset)
    blobs: List[bytes] = []
    for e in entries:
        b = e.text.encode("utf-8")
        blobs.append(b)
        # struct "64s"가 64바이트로 자동 null-pad/절단. version은 u16 마스킹.
        out += _ENTRY.pack(e.key.encode("utf-8"), e.version & 0xFFFF, len(b) + 1)
    for b in blobs:
        out += b
        out += b"\x00"
    return bytes(out)


# ── XML ────────────────────────────────────────────────────
def to_xml(entries: List[LocalizedText]) -> str:
    """LocalizedText 목록을 Divine 호환 `.loca.xml` 문자열로 변환(텍스트 이스케이프)."""
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<contentList>"]
    for e in entries:
        lines.append(
            f'\t<content contentuid="{e.key}" version="{e.version}">'
            f"{_xml_escape(e.text)}</content>"
        )
    lines.append("</contentList>")
    return "\n".join(lines) + "\n"


def from_xml(xml_text: str) -> List[LocalizedText]:
    """`.loca.xml`(또는 모더 작성 `*.xml`)을 파싱해 LocalizedText 목록을 반환(역이스케이프)."""
    out: List[LocalizedText] = []
    for attrs, inner in _BLOCK_RE.findall(xml_text):
        m = _UID_RE.search(attrs)
        if not m:
            continue
        key = m.group(1)
        vm = _VER_RE.search(attrs)
        version = int(vm.group(1)) if vm and vm.group(1).isdigit() else 1
        text = _xml_unescape(inner or "")
        out.append(LocalizedText(key, version, text))
    return out


# ── 파일 단위 편의 함수 ────────────────────────────────────
def loca_file_to_xml(loca_path: Union[str, Path]) -> str:
    return to_xml(read_loca(Path(loca_path).read_bytes()))


def xml_to_loca_bytes(xml_path: Union[str, Path]) -> bytes:
    text = Path(xml_path).read_text(encoding="utf-8", errors="replace")
    return write_loca(from_xml(text))
