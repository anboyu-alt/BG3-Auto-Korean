"""④ 공식 언어팩 참조 글로서리.

BG3 설치 폴더의 공식 언어팩(English.pak + 대상언어 팩)을 네이티브 pak/loca로 추출하여
contentuid로 조인 → "공식 영어 → 공식 대상언어" 사전을 만든다. 디스크에 캐시하며
소스 .pak의 크기/수정시각이 바뀌면 자동 재생성한다.

사용처:
  1) 모드 문자열이 공식 용어와 정확히 일치하면 공식 번역을 그대로 사용(AI 절약).
  2) 문장 속에 등장하는 공식 용어를 프롬프트에 주입해 공식 표기와 일관되게 번역.

저작권: 이용자 로컬 게임 파일을 번역 메모리로 참조할 뿐, 공식 텍스트를 재배포하지 않는다.

이 모듈의 상단(파싱·조인·조회·캐시키)은 Divine 비호출 순수 함수로, 단위 테스트 대상.
"""
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Tuple

if TYPE_CHECKING:
    from .logger import CallbackLogger

# <content contentuid="h..." version="N">텍스트</content> — inner 텍스트와 uid 캡처.
# self-closing(<content ... />)은 텍스트가 없으므로 매칭하지 않는다.
_CONTENT_RE = re.compile(
    r'<content\b[^>]*\bcontentuid="([^"]+)"[^>]*>(.*?)</content>',
    re.DOTALL | re.IGNORECASE,
)

# XML 엔티티 역변환 (loca.xml에서 텍스트 복원). &amp;는 마지막에 처리.
_UNESCAPE = [
    ("&lt;", "<"),
    ("&gt;", ">"),
    ("&quot;", '"'),
    ("&apos;", "'"),
    ("&amp;", "&"),
]


def _unescape(text: str) -> str:
    for ent, ch in _UNESCAPE:
        text = text.replace(ent, ch)
    return text


def parse_loca_xml(xml_text: str) -> Dict[str, str]:
    """loca.xml 문자열에서 {contentuid: 텍스트} 사전을 만든다. 빈 텍스트는 제외."""
    result: Dict[str, str] = {}
    for uid, raw in _CONTENT_RE.findall(xml_text):
        text = _unescape(raw).strip()
        if text:
            result[uid] = text
    return result


def build_official_dict(
    english: Dict[str, str],
    target: Dict[str, str],
) -> Dict[str, str]:
    """contentuid로 영어↔대상 사전을 조인해 {영어텍스트: 대상텍스트}를 만든다.

    - 대상에 없는 핸들(모드 전용 등)은 건너뛴다.
    - 같은 영어 텍스트가 서로 다른 번역으로 매핑되면(맥락 의존 모호어) 무조건 치환을
      피하기 위해 해당 영어 키 전체를 제외한다.
    - 양쪽 모두 공백/빈 값은 제외.
    """
    mapping: Dict[str, str] = {}
    ambiguous: set = set()
    for uid, en_text in english.items():
        en = en_text.strip()
        if not en or uid not in target:
            continue
        tgt = target[uid].strip()
        if not tgt:
            continue
        if en in mapping:
            if mapping[en] != tgt:
                ambiguous.add(en)
        else:
            mapping[en] = tgt
    for en in ambiguous:
        mapping.pop(en, None)
    return mapping


def lookup_official(text: str, official: Dict[str, str]) -> Optional[str]:
    """문자열 전체가 공식 용어와 정확히 일치하면 공식 번역을 반환, 아니면 None."""
    return official.get(text.strip())


def build_official_prompt_section(text: str, official: Dict[str, str]) -> str:
    """text 본문에 등장하는 공식 용어만 골라 프롬프트 섹션 문자열을 만든다.

    매칭이 없으면 빈 문자열. (전체 사전을 주입하면 수만 줄이 되므로 본문 매칭만.)
    """
    if not official:
        return ""
    matched = []
    seen = set()
    # 긴 용어 우선(부분 매칭 우선순위) — 같은 표기 중복 방지.
    for src in sorted(official, key=len, reverse=True):
        if src in seen:
            continue
        if re.search(r"\b" + re.escape(src) + r"\b", text):
            matched.append(src)
            seen.add(src)
    if not matched:
        return ""
    lines = [
        "[Official terminology — match the game's official translation]",
    ]
    for src in matched:
        lines.append(f"  {src} -> {official[src]}")
    lines.append("")
    return "\n".join(lines) + "\n"


def cache_signature(pak_paths: Iterable[Path]) -> str:
    """소스 .pak들의 (이름, 크기, mtime)로 캐시 무효화 시그니처를 만든다. 순서 무관."""
    parts: List[str] = []
    for p in pak_paths:
        try:
            st = p.stat()
            parts.append(f"{p.name}:{st.st_size}:{int(st.st_mtime)}")
        except OSError:
            parts.append(f"{p.name}:missing")
    blob = "|".join(sorted(parts))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def find_language_paks(
    bg3_install_path: str,
    target_folder_name: str,
) -> Tuple[List[Path], List[Path]]:
    """설치 폴더의 Localization에서 (영어 팩들, 대상언어 팩들)을 찾는다.

    표준 구조:
      Data/Localization/English.pak  (또는 Data/Localization/English/*.pak)
      Data/Localization/<Lang>/*.pak (예: Korean/Korean.pak + Korean/KoreanData.pak)
    하나도 못 찾으면 빈 리스트(기능 비활성).
    """
    if not bg3_install_path:
        return [], []
    loc = Path(bg3_install_path) / "Data" / "Localization"
    if not loc.is_dir():
        return [], []

    def _collect(name: str) -> List[Path]:
        found: List[Path] = []
        flat = loc / f"{name}.pak"
        if flat.is_file():
            found.append(flat)
        sub = loc / name
        if sub.is_dir():
            found.extend(p for p in sorted(sub.glob("*.pak")) if p.is_file())
        return found

    return _collect("English"), _collect(target_folder_name)


def save_cache(cache_path: Path, signature: str, data: Dict[str, str]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"signature": signature, "entries": data}
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def load_cache(cache_path: Path, signature: str) -> Optional[Dict[str, str]]:
    """시그니처가 일치할 때만 캐시 사전을 반환. 불일치/없음/손상 시 None."""
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return None
    if payload.get("signature") != signature:
        return None
    entries = payload.get("entries")
    return entries if isinstance(entries, dict) else None


def get_cache_path(target_folder_name: str) -> Path:
    appdata = os.environ.get("APPDATA", Path.home())
    return (
        Path(appdata)
        / "BG3-Auto-Korean"
        / f"official_glossary_{target_folder_name}.json"
    )


# ── IO 오케스트레이션 (네이티브 pak/loca) ───────────────────
def _extract_dict_from_paks(
    paks: List[Path],
    logger: Optional["CallbackLogger"],
) -> Dict[str, str]:
    """pak들을 추출·변환·파싱해 {contentuid: 텍스트} 병합 사전을 만든다."""
    from . import packio as _packio

    merged: Dict[str, str] = {}
    for pak in paks:
        with tempfile.TemporaryDirectory(prefix="bg3_official_") as tmp:
            dest = Path(tmp)
            if not _packio.extract_pak(pak, dest):
                if logger:
                    logger.warning(f"    ⚠️ Official pack extract failed: {pak.name}")
                continue
            _packio.convert_loca_to_xml(dest, logger=logger)
            for xml in dest.rglob("*.loca.xml"):
                try:
                    text = xml.read_text(encoding="utf-8")
                except Exception:
                    continue
                merged.update(parse_loca_xml(text))
    return merged


def extract_official_glossary(
    bg3_install_path: str,
    target_folder_name: str,
    logger: Optional["CallbackLogger"] = None,
    force: bool = False,
) -> Optional[Dict[str, str]]:
    """공식 영어→대상 사전을 만든다(또는 캐시에서 로드). 사용 불가 시 None.

    None 조건: BG3 경로 미설정, 공식 팩 미발견 → 기능 비활성(파이프라인은 그냥 진행).
    """
    english_paks, target_paks = find_language_paks(bg3_install_path, target_folder_name)
    if not english_paks or not target_paks:
        return None

    cache_path = get_cache_path(target_folder_name)
    signature = cache_signature(english_paks + target_paks)
    if not force:
        cached = load_cache(cache_path, signature)
        if cached is not None:
            if logger:
                logger.info(
                    f"  Official glossary: {len(cached)} terms (cached, {target_folder_name})"
                )
            return cached

    if logger:
        logger.info(
            f"  Building official glossary from game packs ({target_folder_name})..."
        )
    english_map = _extract_dict_from_paks(english_paks, logger)
    target_map = _extract_dict_from_paks(target_paks, logger)
    official = build_official_dict(english_map, target_map)
    if logger:
        logger.info(f"  Official glossary: {len(official)} terms built")
    save_cache(cache_path, signature, official)
    return official
