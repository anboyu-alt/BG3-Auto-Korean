from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional

from .constants import CONTENT_INNER_RE, CONTENTUID_RE


@dataclass
class Entry:
    contentuid: str
    english: str
    korean: str
    modified: bool = False
    new_korean: str = ""

    @property
    def display_korean(self) -> str:
        return self.new_korean if self.modified else self.korean


@dataclass
class ReviewFile:
    filename: str
    entries: List[Entry]
    korean_xml_path: Path
    korean_xml_original: str


def extract_entries_from_xml(xml_text: str) -> Dict[str, str]:
    entries = {}
    for m in CONTENT_INNER_RE.finditer(xml_text):
        open_tag = m.group(1)
        inner = m.group(2)
        uid_match = CONTENTUID_RE.search(open_tag)
        if uid_match:
            uid = uid_match.group(1)
            entries[uid] = inner.strip()
    return entries


def load_review_files(unpacked_path: Path) -> List[ReviewFile]:
    review_files = []

    for loc_dir in unpacked_path.rglob("Localization"):
        if not loc_dir.is_dir():
            continue

        english_dir = None
        korean_dir = None
        for sub in loc_dir.iterdir():
            if sub.is_dir():
                if sub.name.lower() == "english":
                    english_dir = sub
                elif sub.name.lower() == "korean":
                    korean_dir = sub

        if not english_dir or not korean_dir:
            continue

        for kr_xml in sorted(korean_dir.glob("*.xml")):
            en_xml = english_dir / kr_xml.name
            if not en_xml.exists():
                en_xmls = list(english_dir.glob("*.xml"))
                if len(en_xmls) == 1:
                    en_xml = en_xmls[0]
                else:
                    continue

            try:
                en_text = en_xml.read_text(encoding="utf-8", errors="replace")
                kr_text = kr_xml.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            en_entries = extract_entries_from_xml(en_text)
            kr_entries = extract_entries_from_xml(kr_text)

            if not en_entries or not kr_entries:
                continue

            entries = []
            for uid, en_inner in en_entries.items():
                kr_inner = kr_entries.get(uid, "")
                if not kr_inner:
                    continue
                entries.append(Entry(
                    contentuid=uid,
                    english=en_inner,
                    korean=kr_inner,
                ))

            if entries:
                review_files.append(ReviewFile(
                    filename=kr_xml.name,
                    entries=entries,
                    korean_xml_path=kr_xml,
                    korean_xml_original=kr_text,
                ))

    return review_files


def save_modified_xml(review_file: ReviewFile) -> None:
    modified_entries = {e.contentuid: e.new_korean for e in review_file.entries if e.modified}
    if not modified_entries:
        return

    xml_text = review_file.korean_xml_original

    def replace_content(match):
        open_tag = match.group(1)
        close_tag = match.group(3)
        uid_match = CONTENTUID_RE.search(open_tag)
        if uid_match and uid_match.group(1) in modified_entries:
            return f"{open_tag}{modified_entries[uid_match.group(1)]}{close_tag}"
        return match.group(0)

    new_xml = CONTENT_INNER_RE.sub(replace_content, xml_text)
    review_file.korean_xml_path.write_text(new_xml, encoding="utf-8")
