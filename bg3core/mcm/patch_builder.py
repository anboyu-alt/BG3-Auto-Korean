"""한글 패치 모드 PAK 산출용 디렉토리 빌더.

원본 모드의 Localization을 한글화한 상태에서, 별도 UUID·Folder를 가진
한글 패치 모드 디렉토리를 만든다. 게임은 같은 contentuid를 가진 한글 XML이
후위로 로드되면 영문을 덮어쓴다 — 이 동작에 기대 패치 방식이 한글화
커뮤니티의 표준이다.
"""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..logger import CallbackLogger

from ..language import LanguageProfile, DEFAULT_PROFILE


def extract_original_meta(unpacked_root: Path) -> Optional[dict]:
    """원본 모드 디렉토리에서 meta.lsx의 ModuleInfo·Dependencies를 읽어 반환."""
    meta_paths = list(unpacked_root.rglob("meta.lsx"))
    if not meta_paths:
        return None

    meta_path = meta_paths[0]
    text = meta_path.read_text(encoding="utf-8", errors="replace")

    def find_attr(node_section: str, attr_id: str) -> Optional[str]:
        pattern = rf'<attribute\s+id="{re.escape(attr_id)}"\s+type="[^"]*"\s+value="([^"]*)"'
        m = re.search(pattern, node_section)
        return m.group(1) if m else None

    module_info_match = re.search(
        r'<node\s+id="ModuleInfo">(.*?)</node>\s*</children>\s*</node>\s*</region>',
        text,
        re.DOTALL,
    )
    module_info = module_info_match.group(1) if module_info_match else text

    dependencies_match = re.search(
        r'<node\s+id="Dependencies">(.*?)</node>\s*<node\s+id="ModuleInfo"',
        text,
        re.DOTALL,
    )
    dependencies_block = dependencies_match.group(0).rsplit("<node", 1)[0] if dependencies_match else None
    # dependencies_block은 ModuleShortDesc들을 포함한 Dependencies 노드 전체. 단, 닫는 </node>가
    # 정규식 캡처 범위에 있는지 확인 필요. 더 안전한 추출:
    deps_clean = re.search(
        r'<node\s+id="Dependencies">.*?</node>\s*</node>',
        text,
        re.DOTALL,
    )
    # 위 패턴은 Dependencies 노드 + 닫는 </node>(children) 까지 잡으니 부정확.
    # 가장 단순한 방식: Dependencies 블록만 추출.
    deps_inner = re.search(
        r'<node\s+id="Dependencies">\s*<children>(.*?)</children>\s*</node>',
        text,
        re.DOTALL,
    )

    return {
        "path": meta_path,
        "uuid": find_attr(module_info, "UUID"),
        "name": find_attr(module_info, "Name"),
        "folder": find_attr(module_info, "Folder"),
        "version64": find_attr(module_info, "Version64") or "144396663052566529",
        "dependencies_inner": deps_inner.group(1).strip() if deps_inner else "",
    }


def make_patch_uuid(original_uuid: str, lang_code: str = "KR") -> str:
    """원본 UUID 기반 deterministic UUID 생성 — 재실행 시 같은 ID."""
    h = hashlib.sha1(f"BG3-Auto-Korean:{lang_code}Patch:{original_uuid}".encode()).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


_META_TEMPLATE = '''<?xml version="1.0" encoding="utf-8"?>
<save>
  <version major="4" minor="0" revision="0" build="68" />
  <region id="Config">
    <node id="root">
      <children>
        <node id="Dependencies">
          <children>
{DEPENDENCIES}
          </children>
        </node>
        <node id="ModuleInfo">
          <attribute id="Author" type="LSWString" value="BG3-Auto-Korean" />
          <attribute id="CharacterCreationLevelName" type="FixedString" value="" />
          <attribute id="Description" type="LSWString" value="{LANG_DISPLAY_NAME} translation patch. Place below the original mod in Mod Manager." />
          <attribute id="Folder" type="LSWString" value="{PATCH_FOLDER}" />
          <attribute id="GMTemplate" type="FixedString" value="" />
          <attribute id="LobbyLevelName" type="FixedString" value="" />
          <attribute id="MD5" type="LSString" value="" />
          <attribute id="MainMenuBackgroundVideo" type="FixedString" value="" />
          <attribute id="MenuLevelName" type="FixedString" value="" />
          <attribute id="Name" type="FixedString" value="{PATCH_NAME}" />
          <attribute id="NumPlayers" type="uint8" value="4" />
          <attribute id="PhotoBooth" type="FixedString" value="" />
          <attribute id="StartupLevelName" type="FixedString" value="" />
          <attribute id="Tags" type="LSWString" value="Translation" />
          <attribute id="Type" type="FixedString" value="Add-on" />
          <attribute id="UUID" type="FixedString" value="{PATCH_UUID}" />
          <attribute id="Version64" type="int64" value="{VERSION64}" />
          <children>
            <node id="PublishVersion">
              <attribute id="Version64" type="int64" value="{VERSION64}" />
            </node>
            <node id="Scripts" />
            <node id="TargetModes">
              <children>
                <node id="Target">
                  <attribute id="Object" type="FixedString" value="Story" />
                </node>
              </children>
            </node>
          </children>
        </node>
      </children>
    </node>
  </region>
</save>
'''


def build_patch_meta_xml(
    original_meta: dict,
    target_profile: LanguageProfile = DEFAULT_PROFILE,
) -> str:
    """패치 모드용 meta.lsx 텍스트 생성."""
    patch_uuid = make_patch_uuid(original_meta["uuid"], lang_code=target_profile.lang_code)
    patch_folder = f"{original_meta['folder']}_{target_profile.lang_code}"
    patch_name = f"{original_meta['name']} ({target_profile.lang_code} Patch)"

    deps = original_meta.get("dependencies_inner", "").strip()
    if not deps:
        # 최소 — 원본 모드를 명시적 의존성으로 추가
        deps = (
            '            <node id="ModuleShortDesc">\n'
            f'              <attribute id="Folder" type="LSWString" value="{original_meta["folder"]}" />\n'
            f'              <attribute id="MD5" type="LSString" value="" />\n'
            f'              <attribute id="Name" type="FixedString" value="{original_meta["name"]}" />\n'
            f'              <attribute id="UUID" type="FixedString" value="{original_meta["uuid"]}" />\n'
            f'              <attribute id="Version64" type="int64" value="{original_meta["version64"]}" />\n'
            '            </node>'
        )

    return _META_TEMPLATE.format(
        DEPENDENCIES=deps,
        PATCH_FOLDER=patch_folder,
        PATCH_NAME=patch_name,
        PATCH_UUID=patch_uuid,
        LANG_DISPLAY_NAME=target_profile.display_name,
        VERSION64=original_meta["version64"],
    )


def build_patch_mod_dir(
    unpacked_root: Path,
    output_dir: Path,
    target_profile: LanguageProfile = DEFAULT_PROFILE,
    logger: Optional["CallbackLogger"] = None,
) -> Optional[dict]:
    """번역 패치 모드 디렉토리를 output_dir에 생성. divine_repack 대상 디렉토리 경로 반환.

    target_profile.folder_name 폴더의 *.xml을 패치 모드 안의 해당 언어/, English/, French/ 등
    모든 언어 폴더에 복사한다 (같은 contentuid를 모든 언어에 등록).
    """
    def _log(text: str) -> None:
        if logger:
            logger.info(text)
        else:
            print(text)

    original_meta = extract_original_meta(unpacked_root)
    if not original_meta or not original_meta.get("uuid") or not original_meta.get("folder"):
        _log("    [patch] meta.lsx에서 원본 모드 정보를 추출하지 못함. 패치 PAK 산출 스킵")
        return None

    patch_folder_name = f"{original_meta['folder']}_{target_profile.lang_code}"

    # 번역 Localization 수집
    target_xmls: List[Path] = []
    for loc_dir in unpacked_root.rglob("Localization"):
        if not loc_dir.is_dir():
            continue
        target_lang_dir = loc_dir / target_profile.folder_name
        if target_lang_dir.is_dir():
            target_xmls.extend(
                x for x in target_lang_dir.iterdir()
                if x.is_file() and x.suffix.lower() == ".xml"
            )

    if not target_xmls:
        _log(f"    [patch] {target_profile.folder_name}/*.xml이 없어 패치 PAK 산출 스킵")
        return None

    # 패치 모드 디렉토리 빌드
    if output_dir.exists():
        shutil.rmtree(output_dir, ignore_errors=True)
    mods_dir = output_dir / "Mods" / patch_folder_name
    mods_dir.mkdir(parents=True, exist_ok=True)
    loc_root = output_dir / "Localization"

    # meta.lsx
    meta_xml = build_patch_meta_xml(original_meta, target_profile=target_profile)
    (mods_dir / "meta.lsx").write_text(meta_xml, encoding="utf-8")

    # Localization: 번역 XML 복사 + 원본의 다른 언어 폴더에도 동명 번역 복사
    # 원본의 언어 폴더 이름 수집
    source_lang_names = set()
    for loc_dir in unpacked_root.rglob("Localization"):
        if not loc_dir.is_dir():
            continue
        for child in loc_dir.iterdir():
            if child.is_dir():
                source_lang_names.add(child.name)
    source_lang_names.add(target_profile.folder_name)  # 최소 target_profile 폴더

    copied = 0
    for lang in source_lang_names:
        lang_dir = loc_root / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        for src_xml in target_xmls:
            dst = lang_dir / src_xml.name
            dst.write_text(src_xml.read_text(encoding="utf-8"), encoding="utf-8")
            copied += 1

    _log(f"    [patch] 패치 모드 빌드: {patch_folder_name}, 번역 XML {len(target_xmls)}개 × 언어폴더 {len(source_lang_names)}개 = {copied}건")
    return {
        "patch_dir": output_dir,
        "patch_folder": patch_folder_name,
        "patch_uuid": make_patch_uuid(original_meta["uuid"], lang_code=target_profile.lang_code),
        "translated_xml_count": len(target_xmls),
        "lang_folders": sorted(source_lang_names),
    }
