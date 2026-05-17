import json
from pathlib import Path

from bg3core.mcm.blueprint import (
    find_blueprints,
    process_blueprints,
    _collect_strings_recursive,
    _apply_recursive,
)


def test_find_blueprints(tooltip_manager_root):
    blueprints = find_blueprints(tooltip_manager_root)
    assert len(blueprints) == 1
    assert blueprints[0].name == "MCM_blueprint.json"


def test_tooltip_manager_plain_candidates(tooltip_manager_root):
    """Tooltip Manager는 ModName만 평문, Tabs[0].TabName은 Handles로 보호됨."""
    bp = find_blueprints(tooltip_manager_root)[0]
    data = json.loads(bp.read_text(encoding="utf-8"))
    plain = []
    _collect_strings_recursive(data, plain)
    # ModName만 잡혀야 한다. TabName은 같은 노드의 NameHandle로 보호.
    assert plain == ["Tooltip Manager"]


def test_tooltip_manager_processor_translates_modname_only(tooltip_manager_root, passthrough_translate):
    bp = find_blueprints(tooltip_manager_root)[0]
    stats = process_blueprints(tooltip_manager_root, passthrough_translate)
    after = json.loads(bp.read_text(encoding="utf-8"))
    assert stats["blueprints"] == 1
    assert stats["translated"] == 1
    assert after["ModName"] == "[KO]Tooltip Manager"
    # TabName은 Handles로 보호돼 영문 유지
    assert after["Tabs"][0]["TabName"] == "Tooltip Manager"


def test_synthetic_blueprint_translatable_fields(tmp_path, passthrough_translate):
    """Sections/Settings가 있는 합성 블루프린트로 화이트리스트 추출 검증."""
    bp_dir = tmp_path / "Mods" / "Demo"
    bp_dir.mkdir(parents=True)
    bp_path = bp_dir / "MCM_blueprint.json"
    bp_path.write_text(json.dumps({
        "SchemaVersion": 1,
        "ModName": "Demo Mod",
        "Tabs": [
            {
                "TabId": "main",
                "TabName": "Main Tab",
                "TabDescription": "Main settings",
                "Sections": [
                    {
                        "SectionId": "vis",
                        "SectionName": "Visibility",
                        "SectionDescription": "Toggle visibility",
                        "Settings": [
                            {
                                "SettingId": "show_x",
                                "Name": "Show X",
                                "Description": "Show item X",
                                "Tooltip": "Click to toggle X",
                                "Type": "checkbox",
                                "Default": True,
                                "Options": {
                                    "Choices": ["First", "Second", "Third"],
                                    "Label": "Pick one",
                                    "ConfirmDialog": {
                                        "Title": "Confirm",
                                        "Message": "Are you sure?",
                                        "ConfirmText": "Yes",
                                        "CancelText": "No",
                                    },
                                },
                            }
                        ],
                    }
                ],
            }
        ],
    }, indent=4), encoding="utf-8")

    stats = process_blueprints(tmp_path, passthrough_translate)
    assert stats["blueprints"] == 1
    assert stats["translated"] >= 14  # ModName + TabName + TabDescription + SectionName + SectionDescription + Name + Description + Tooltip + 3 Choices + Label + Title + Message + ConfirmText + CancelText = 16

    data = json.loads(bp_path.read_text(encoding="utf-8"))
    assert data["ModName"] == "[KO]Demo Mod"
    assert data["Tabs"][0]["TabName"] == "[KO]Main Tab"
    assert data["Tabs"][0]["Sections"][0]["Settings"][0]["Name"] == "[KO]Show X"
    assert data["Tabs"][0]["Sections"][0]["Settings"][0]["Options"]["Choices"] == ["[KO]First", "[KO]Second", "[KO]Third"]
    assert data["Tabs"][0]["Sections"][0]["Settings"][0]["Options"]["ConfirmDialog"]["Title"] == "[KO]Confirm"
    # 블랙리스트 키는 그대로
    assert data["SchemaVersion"] == 1
    assert data["Tabs"][0]["TabId"] == "main"
    assert data["Tabs"][0]["Sections"][0]["Settings"][0]["Type"] == "checkbox"
    assert data["Tabs"][0]["Sections"][0]["Settings"][0]["Default"] is True


def test_blueprint_with_handles_skips_plain_fields(tmp_path, passthrough_translate):
    """노드에 Handles가 있고 형제 평문 필드가 있으면, 그 필드는 건드리지 않는다."""
    bp_dir = tmp_path / "Mods" / "Demo"
    bp_dir.mkdir(parents=True)
    bp_path = bp_dir / "MCM_blueprint.json"
    bp_path.write_text(json.dumps({
        "SchemaVersion": 1,
        "ModName": "Demo",
        "Tabs": [
            {
                "TabId": "with_handle",
                "TabName": "English Label",
                "Handles": {"NameHandle": "h1234567890abcdef"},
            },
            {
                "TabId": "no_handle",
                "TabName": "Plain Label",
            },
        ],
    }, indent=4), encoding="utf-8")

    process_blueprints(tmp_path, passthrough_translate)
    data = json.loads(bp_path.read_text(encoding="utf-8"))
    # Handles 있는 탭의 TabName은 영문 그대로
    assert data["Tabs"][0]["TabName"] == "English Label"
    # Handles 없는 탭은 치환됨
    assert data["Tabs"][1]["TabName"] == "[KO]Plain Label"
