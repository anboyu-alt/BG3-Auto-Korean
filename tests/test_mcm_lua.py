import json
from pathlib import Path

from bg3core.mcm.lua_handler import (
    find_lua_files,
    scan_lua,
    apply_translations,
    process_lua_files,
)
from bg3core.mcm.whitelist import is_lua_skippable, is_lua_short_key


def test_find_lua_files(tooltip_manager_root):
    files = find_lua_files(tooltip_manager_root)
    names = {f.name for f in files}
    assert "BootstrapClient.lua" in names
    assert "BootstrapServer.lua" in names
    assert "ConfigUtils.lua" in names


def test_scan_bootstrap_client_options(tooltip_manager_root):
    client = next(f for f in find_lua_files(tooltip_manager_root) if f.name == "BootstrapClient.lua")
    content = client.read_text(encoding="utf-8")
    _, _, options = scan_lua(content)
    # 핸드오프에 정리된 옵션 배열 7개
    assert len(options) == 7

    variables = {o["variable"] for o in options}
    assert {"combo", "editedCombo", "modCombo", "lootableCombo", "containerCombo", "visibilityCombo", "scopeCombo"} <= variables

    mod_combo = next(o for o in options if o["variable"] == "modCombo")
    assert mod_combo["items"] == ["All", "Vanilla Only", "Modded Only"]


def test_scan_bootstrap_client_auto_and_review(tooltip_manager_root):
    client = next(f for f in find_lua_files(tooltip_manager_root) if f.name == "BootstrapClient.lua")
    content = client.read_text(encoding="utf-8")
    auto, review, _ = scan_lua(content)
    # 자동 후보는 충분히 많고, 검수 큐도 비어있지 않다
    assert len(auto) >= 40
    assert len(review) >= 5

    review_texts = {r["text"] for r in review}
    # 짧은 키들이 검수 큐로 분리됐는지
    assert "Edited" in review_texts or "Root" in review_texts or "Local" in review_texts


def test_blacklist_filters_network_channels():
    # 네트워크 채널 패턴은 자동 처리에서 제외돼야 한다
    assert is_lua_skippable("TooltipManager_ApplyConfigChunk")
    assert is_lua_skippable("Foo_BarBaz")


def test_blacklist_filters_imgui_internal_ids():
    assert is_lua_skippable("##ItemCount")
    assert is_lua_skippable("##EditedFilter")


def test_blacklist_filters_color_slots():
    assert is_lua_skippable("Text")
    assert is_lua_skippable("Button")
    assert is_lua_skippable("FrameBg")
    assert is_lua_skippable("TableRowBg")


def test_blacklist_filters_file_extension():
    assert is_lua_skippable(".json")


def test_short_key_detection():
    assert is_lua_short_key("All")
    assert is_lua_short_key("Vanilla Only")
    assert is_lua_short_key("On Hover")
    assert not is_lua_short_key("Configure tooltip visibility for items.")


def test_apply_translations_preserves_unmapped_text(tooltip_manager_root):
    client = next(f for f in find_lua_files(tooltip_manager_root) if f.name == "BootstrapClient.lua")
    content = client.read_text(encoding="utf-8")
    auto, _, _ = scan_lua(content)
    # 첫 자동 후보만 한글로 매핑
    target = auto[0]
    mapping = {target["text"]: f"한글-{target['text']}"}
    new_content, count = apply_translations(content, auto, mapping)
    assert count == 1
    assert f'"한글-{target["text"]}"' in new_content
    # 다른 위치는 원본과 동일 (길이는 한글로 약간 변할 수 있으니 패턴으로 확인)
    other = auto[1]
    assert f'"{other["text"]}"' in new_content


def test_apply_translations_escapes_special_chars(tmp_path):
    src = 'local x = ":AddText(\\"Hello\\")"\n:AddText("Hello")\n'
    # 위 src에서 첫 줄은 문자열 안의 escape이므로 정규식이 잡지 않음. 둘째 줄만 매칭.
    auto, _, _ = scan_lua(src)
    assert len(auto) == 1
    new_content, count = apply_translations(src, auto, {"Hello": 'a"b\nc'})
    assert count == 1
    assert 'a\\"b\\nc' in new_content


def test_scan_picks_up_string_format(tooltip_manager_root):
    client = next(f for f in find_lua_files(tooltip_manager_root) if f.name == "BootstrapClient.lua")
    content = client.read_text(encoding="utf-8")
    auto, _, _ = scan_lua(content)
    texts = {e["text"] for e in auto}
    assert "Showing %d / %d items" in texts


def test_string_format_skips_when_specifiers_mismatch():
    src = 'itemCountText.Text = string.format("Showing %d items", n)\n'
    auto, _, _ = scan_lua(src)
    assert any(e["pattern"] == "StringFormat" for e in auto)
    # specifier가 깨진 번역 — 치환 안 돼야 함
    new_src, count = apply_translations(src, auto, {"Showing %d items": "표시 중인 항목"})
    assert count == 0
    assert "Showing %d items" in new_src


def test_string_format_applies_when_specifiers_preserved():
    src = 'itemCountText.Text = string.format("Showing %d / %d items", a, b)\n'
    auto, _, _ = scan_lua(src)
    new_src, count = apply_translations(src, auto, {"Showing %d / %d items": "%d / %d 항목 표시 중"})
    assert count == 1
    assert "%d / %d 항목 표시 중" in new_src


def test_process_lua_files_end_to_end(tooltip_manager_root, passthrough_translate, tmp_path):
    report_path = tmp_path / "review.json"
    stats = process_lua_files(tooltip_manager_root, passthrough_translate, review_report_path=report_path)
    assert stats["files"] >= 1
    assert stats["auto"] >= 40
    assert stats["report"] == str(report_path)
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert any("BootstrapClient.lua" in k for k in report.keys())

    # 자동 치환된 자리에 [KO] prefix가 들어갔는지 확인
    client = next(f for f in find_lua_files(tooltip_manager_root) if f.name == "BootstrapClient.lua")
    after = client.read_text(encoding="utf-8")
    assert "[KO]" in after
