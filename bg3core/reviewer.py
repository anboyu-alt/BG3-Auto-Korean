from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional

from .constants import CONTENT_INNER_RE, CONTENTUID_RE


@dataclass
class Entry:
    contentuid: str
    english: str
    target_text: str
    modified: bool = False
    new_target: str = ""

    @property
    def display_target(self) -> str:
        return self.new_target if self.modified else self.target_text


@dataclass
class ReviewFile:
    filename: str
    entries: List[Entry]
    target_xml_path: Path
    target_xml_original: str


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


def load_review_files(unpacked_path: Path, target_folder: str = "Korean") -> List[ReviewFile]:
    review_files = []

    for loc_dir in unpacked_path.rglob("Localization"):
        if not loc_dir.is_dir():
            continue

        english_dir = None
        target_dir = None
        for sub in loc_dir.iterdir():
            if sub.is_dir():
                if sub.name.lower() == "english":
                    english_dir = sub
                elif sub.name.lower() == target_folder.lower():
                    target_dir = sub

        if not english_dir or not target_dir:
            continue

        for target_xml in sorted(target_dir.glob("*.xml")):
            en_xml = english_dir / target_xml.name
            if not en_xml.exists():
                en_xmls = list(english_dir.glob("*.xml"))
                if len(en_xmls) == 1:
                    en_xml = en_xmls[0]
                else:
                    continue

            try:
                en_text = en_xml.read_text(encoding="utf-8", errors="replace")
                target_text = target_xml.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            en_entries = extract_entries_from_xml(en_text)
            target_entries = extract_entries_from_xml(target_text)

            if not en_entries or not target_entries:
                continue

            entries = []
            for uid, en_inner in en_entries.items():
                target_inner = target_entries.get(uid, "")
                if not target_inner:
                    continue
                entries.append(Entry(
                    contentuid=uid,
                    english=en_inner,
                    target_text=target_inner,
                ))

            if entries:
                review_files.append(ReviewFile(
                    filename=target_xml.name,
                    entries=entries,
                    target_xml_path=target_xml,
                    target_xml_original=target_text,
                ))

    return review_files


def save_modified_xml(review_file: ReviewFile) -> None:
    modified_entries = {e.contentuid: e.new_target for e in review_file.entries if e.modified}
    if not modified_entries:
        return

    xml_text = review_file.target_xml_original

    def replace_content(match):
        open_tag = match.group(1)
        close_tag = match.group(3)
        uid_match = CONTENTUID_RE.search(open_tag)
        if uid_match and uid_match.group(1) in modified_entries:
            return f"{open_tag}{modified_entries[uid_match.group(1)]}{close_tag}"
        return match.group(0)

    new_xml = CONTENT_INNER_RE.sub(replace_content, xml_text)
    review_file.target_xml_path.write_text(new_xml, encoding="utf-8")
