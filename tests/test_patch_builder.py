import re
from pathlib import Path

from bg3core.mcm.patch_builder import (
    extract_original_meta,
    make_patch_uuid,
    build_patch_meta_xml,
    build_patch_mod_dir,
)


META_TEMPLATE = '''<?xml version="1.0" encoding="utf-8"?>
<save>
  <version major="4" minor="0" revision="9" build="328" />
  <region id="Config">
    <node id="root">
      <children>
        <node id="Dependencies">
          <children>
            <node id="ModuleShortDesc">
              <attribute id="Folder" type="LSWString" value="BG3MCM" />
              <attribute id="MD5" type="LSString" value="" />
              <attribute id="Name" type="FixedString" value="BG3MCM" />
              <attribute id="UUID" type="FixedString" value="755a8a72-407f-4f0d-9a33-274ac0f0b53d" />
              <attribute id="Version64" type="int64" value="36028797018963968" />
            </node>
          </children>
        </node>
        <node id="ModuleInfo">
          <attribute id="Author" type="LSWString" value="TestAuthor" />
          <attribute id="Folder" type="LSWString" value="Demo_Mod" />
          <attribute id="Name" type="FixedString" value="Demo Mod" />
          <attribute id="UUID" type="FixedString" value="b3ba01c6-b385-416f-9bbe-7ad7f6a256f0" />
          <attribute id="Version64" type="int64" value="144396663052566529" />
        </node>
      </children>
    </node>
  </region>
</save>
'''


def _make_mod_tree(tmp_path, with_korean=True):
    root = tmp_path / "mod"
    mods_dir = root / "Mods" / "Demo_Mod"
    mods_dir.mkdir(parents=True)
    (mods_dir / "meta.lsx").write_text(META_TEMPLATE, encoding="utf-8")
    loc = root / "Localization"
    (loc / "English").mkdir(parents=True)
    (loc / "English" / "demo.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n<content contentuid="h1" version="1">Hello</content>\n</contentList>\n',
        encoding="utf-8",
    )
    if with_korean:
        (loc / "Korean").mkdir()
        (loc / "Korean" / "demo.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n<content contentuid="h1" version="1">안녕</content>\n</contentList>\n',
            encoding="utf-8",
        )
    return root


def test_extract_original_meta(tmp_path):
    root = _make_mod_tree(tmp_path)
    meta = extract_original_meta(root)
    assert meta is not None
    assert meta["uuid"] == "b3ba01c6-b385-416f-9bbe-7ad7f6a256f0"
    assert meta["folder"] == "Demo_Mod"
    assert meta["name"] == "Demo Mod"
    assert meta["version64"] == "144396663052566529"


def test_make_patch_uuid_is_deterministic():
    uuid_a = make_patch_uuid("b3ba01c6-b385-416f-9bbe-7ad7f6a256f0")
    uuid_b = make_patch_uuid("b3ba01c6-b385-416f-9bbe-7ad7f6a256f0")
    assert uuid_a == uuid_b
    assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", uuid_a)
    # 다른 원본은 다른 UUID
    assert make_patch_uuid("other-uuid") != uuid_a


def test_build_patch_meta_xml_contains_required_fields(tmp_path):
    root = _make_mod_tree(tmp_path)
    meta = extract_original_meta(root)
    xml = build_patch_meta_xml(meta)
    assert "Demo_Mod_KR" in xml
    assert "Demo Mod (Korean Patch)" in xml
    assert "Translation" in xml
    assert meta["uuid"] != make_patch_uuid(meta["uuid"])
    assert make_patch_uuid(meta["uuid"]) in xml


def test_build_patch_mod_dir_creates_complete_structure(tmp_path):
    root = _make_mod_tree(tmp_path)
    output = tmp_path / "patch_build"
    info = build_patch_mod_dir(root, output)
    assert info is not None
    assert info["patch_folder"] == "Demo_Mod_KR"
    assert info["korean_xml_count"] == 1

    # 디렉토리 구조 검증
    assert (output / "Mods" / "Demo_Mod_KR" / "meta.lsx").exists()
    assert (output / "Localization" / "Korean" / "demo.xml").exists()
    # 원본 언어 폴더에도 한글이 복사돼 있어야 함
    assert (output / "Localization" / "English" / "demo.xml").exists()
    english = (output / "Localization" / "English" / "demo.xml").read_text(encoding="utf-8")
    assert "안녕" in english


def test_build_patch_mod_dir_skips_when_no_korean(tmp_path):
    root = _make_mod_tree(tmp_path, with_korean=False)
    output = tmp_path / "patch_build"
    info = build_patch_mod_dir(root, output)
    assert info is None
