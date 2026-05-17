# BG3 MCM 의존 모드 한글화 — Cowork → Claude Code 핸드오프

## 문서의 목적

Cowork에서 진행한 1차 분석(2026-05-17)을 Claude Code 환경으로 인계한다. 분석 대상은 `Tooltip Manager`(작자 wtfbengt) 모드이고, 목표는 BG3-Auto-Korean 도구(https://github.com/anboyu-alt/BG3-Auto-Korean)에 MCM(Mod Configuration Menu) 의존 모드용 처리기를 추가하는 것이다. Tooltip Manager는 첫 번째 검증 샘플 역할을 한다.

이 문서는 Claude Code에서 새 세션을 열었을 때 곧장 이어 작업할 수 있도록, 분석 결과·전략·자동화 설계·검증 계획까지 자기완결적으로 정리했다.

---

## 1. 분석 대상 파일 트리

작업 폴더는 `F:\BG3ModFile\bg3-modders-multitool\UnpackedMods\Tooltip Manager` 아래에 다음 구조로 압축이 풀려 있다.

```
Tooltip Manager/
├── BG3 MCM 한글화/                      ← 이 문서가 들어가는 폴더
│   ├── HANDOFF_to_ClaudeCode.md         (본 문서)
│   └── lua_translation_candidates.json  (자동 추출 결과)
├── Localization/
│   ├── Test.xml
│   └── Test.loca.xml
└── Mods/Tooltip Manager/
    ├── MCM_blueprint.json
    ├── meta.lsx
    └── ScriptExtender/
        ├── Config.json
        └── Lua/
            ├── BootstrapClient.lua
            ├── BootstrapServer.lua
            └── Shared/ConfigUtils.lua
```

핵심 파일은 셋이다. `MCM_blueprint.json`, `Localization/Test.xml`, `ScriptExtender/Lua/BootstrapClient.lua`. 나머지는 한글화 작업에서 건드릴 필요가 없다.

---

## 2. 핵심 발견 — 일반 채팅 답변의 한계

작업 의뢰 시 일반 채팅에서 받은 답변은 MCM 표준 패턴(블루프린트에 모든 설정이 정의됨)을 전제로 Case A(Handles 있음)·Case B-1(블루프린트 직접 수정)·Case B-2(Handles 추가)의 세 분기를 제시했다. 그러나 Tooltip Manager는 이 분류에 깔끔하게 들어가지 않는다. 실제 구조는 하이브리드다.

`MCM_blueprint.json`은 사실상 비어 있다. Tab 하나(`"Tooltip Manager"`)만 정의되어 있고 Sections·Settings 배열이 아예 없다. 그 Tab 이름에는 이미 `NameHandle`이 박혀 있고(`h76690e654f384476b72e5d97653708bf041c`), `Localization/Test.xml`에 해당 핸들이 등록돼 있다. 즉 블루프린트만 보면 Case A에 해당한다.

문제는 사용자 화면에 보이는 거의 모든 텍스트가 블루프린트가 아닌 `BootstrapClient.lua` 코드 안에 직접 박혀 있다는 점이다. `SetupMCM()` 함수가 `Mods.BG3MCM.IMGUIAPI:InsertModMenuTab(ModuleUUID, "Tooltip Manager", function(tab) ... end)` 훅을 통해 탭 컨텐츠를 런타임에 IMGUI 호출로 그린다. 그 안에서 `tab:AddText("Configure tooltip visibility for items.")`, `tab:AddCollapsingHeader("Preset Management")`처럼 모든 UI 요소가 Lua 함수 호출로 생성된다.

따라서 블루프린트만 한글화하면 좌측 사이드바 탭 라벨 한 줄만 한글이 되고, 탭을 열었을 때 보이는 모든 컨텐츠는 영어 그대로 남는다. 실용적 한글화를 위해서는 Lua 코드 수정이 필수다. 이 점이 일반 채팅 답변이 놓친 핵심이다.

---

## 3. 한글화 3트랙 분류

### 트랙 A — 블루프린트 핸들 한글화

`Localization/Test.xml`의 핸들 `h76690e654f384476b72e5d97653708bf041c`의 값을 `"Tooltip Manager"`에서 적절한 한글(예: `"툴팁 관리자"`)로 치환하기만 하면 끝난다. 이 한 줄이 처리하는 것은 MCM 사이드바의 모드 이름과 탭 명칭뿐이다. 자동화 난이도는 낮다. 기존 BG3-Auto-Korean의 표준 XML 핸들 번역 큐에 그대로 합류시키면 된다.

### 트랙 B — Lua 문자열 직접 치환

`BootstrapClient.lua`를 직접 수정해 영문 문자열 리터럴을 한글로 바꾼다. 정규식 추출 결과 자동 처리 후보가 약 80건, 사람 검수가 필요한 콤보 옵션 배열이 7개 잡혔다(`lua_translation_candidates.json` 참조). 이 트랙은 다시 두 단계로 나뉜다.

B-1 단계는 단방향 표시 문자열의 치환이다. `:AddText(...)`, `:AddButton(...)`, `:AddCollapsingHeader(...)`, `:AddInputText(...)`의 라벨·초기값, `.Hint`, `.Text` 등의 인자 문자열은 표시 전용이므로 단순 치환이 가능하다.

B-2 단계는 표시·로직 양용 문자열의 처리다. 콤보 박스 옵션 중 상당수는 표시 라벨이면서 동시에 로직 비교 키다. 예를 들면 다음과 같다.

```lua
modCombo.Options = { "All", "Vanilla Only", "Modded Only" }
modCombo.OnChange = function(c)
    filterOptions.modStatus = c.Options[c.SelectedIndex + 1]
end
-- 이후 다른 함수에서
if filterOptions.modStatus == "Vanilla Only" and itemData.sourceMod ~= "Vanilla" then goto continue end
```

여기서 `"Vanilla Only"`를 한글로 바꾸면 옵션 배열과 비교 분기를 함께 바꿔야 한다. 한쪽만 치환하면 필터가 작동하지 않는다. 더 까다로운 것은 `"Vanilla"`처럼 짧은 키다. 이 단어는 UI 표시(`"Vanilla Only"`의 일부)이면서 동시에 `BootstrapServer.lua`의 `GetModName` 함수가 반환하는 모드 식별자다. 서버 코드는 건드리지 않는 게 원칙이므로, 클라이언트 측 비교 분기에서는 서버가 보내준 영문 키를 그대로 받아 한글 라벨로 매핑하는 구조로 가야 한다.

### 트랙 C — 별도 한글화 패치 모드(권장 형식)

Tooltip Manager 본체를 수정하지 않고 별도 모드로 한글화 산출물을 분리하는 방법이다. Script Extender의 Lua는 동일 경로 파일 오버라이드를 지원하지 않으므로, 가장 현실적인 우회로는 다음과 같다. Localization XML만 별도 한글화 패치 모드로 빼고, `BootstrapClient.lua`는 본체 PAK 안에서 핸들 기반으로 한 번 패치한 뒤 그 패치본을 본체 PAK에 다시 묶어 배포한다. 즉 본체+패치 통합 PAK 한 개 배포 방식이다. 이렇게 하면 한글 외 언어를 추가할 때 XML만 새로 만들면 된다.

이 트랙은 BG3MCM 자체의 ModEvents 후킹으로 IMGUI 위젯의 텍스트를 사후 변경하는 방법도 이론상 가능하나, 본체 코드가 위젯 핸들을 전역에 노출하지 않으므로 사실상 불가능에 가깝다. 첫 번째 안만 실용적이다.

---

## 4. BG3-Auto-Korean 처리기 통합 설계안

### 4.1 파이프라인 진입 분기

기존 도구가 PAK 압축을 푼 직후 다음 두 조건을 검사하도록 분기를 추가한다.

첫 번째 조건은 `MCM_blueprint.json` 존재 여부다. 존재하면 MCM 블루프린트 처리기를 호출한다. 두 번째 조건은 `ScriptExtender/Lua/**/*.lua` 디렉터리 존재 여부다. 존재하면 Lua 처리기를 호출한다. 두 처리기는 서로 독립이고, 한 모드에 둘 다 적용될 수 있다.

### 4.2 블루프린트 처리기 명세

블루프린트 처리기는 JSON을 파싱한 뒤 트리를 순회하면서 다음 두 동작 중 하나를 한다.

첫째, 노드에 `Handles` 객체가 있고 그 안에 `NameHandle`·`DescriptionHandle`·`TooltipHandle` 등이 있으면, 그 핸들 ID와 같은 노드의 평문 값(`Name`·`Description`·`Tooltip`)을 짝지어 표준 BG3 로컬라이제이션 큐로 보낸다. 이 핸들들은 모드 작자가 `Localization/*/english.xml`(또는 모드 내부 XML)에 미리 등록해 두었을 가능성이 높으므로, 같은 핸들이 모드 내부 XML에도 있는지 확인하고 양쪽 모두 갱신한다.

둘째, `Handles` 객체가 없는 노드의 화이트리스트 필드값은 직접 한글로 치환한다. 화이트리스트는 다음과 같다. `ModName`, `Tabs[].TabName`, `Tabs[].TabDescription`, `Sections[].SectionName`, `Sections[].SectionDescription`, `Settings[].Name`, `Settings[].Description`, `Settings[].Tooltip`, `Settings[].Options.Choices[]` 원소들, `Settings[].Options.Label`, `Settings[].Options.ConfirmDialog.{Title,Message,ConfirmText,CancelText}`.

블랙리스트(절대 건드리지 않을 키) 화이트리스트는 다음과 같다. `Id`, `TabId`, `SectionId`, `SettingId`, `Type`, `Default`, `Operator`, `ExpectedValue`, `Min`, `Max`, `Step`, `SchemaVersion`, `Optional`, `VisibleIf`.

JSON 재직렬화 시 `ensure_ascii=False`로 한글 깨짐을 방지하고, 원본의 들여쓰기와 키 순서를 유지하는 게 좋다. 디버깅이 쉬워진다.

블루프린트 스키마 자체는 https://github.com/AtilioA/BG3-MCM/blob/main/.vscode/schema.json에 정의돼 있어서, 화이트리스트를 하드코딩하지 않고 스키마에서 동적으로 추출하는 방식도 가능하다. 다만 도구를 첫 번째 모드부터 빠르게 돌리고 싶다면 하드코딩이 단순하다.

### 4.3 Lua 처리기 명세

Lua 처리기는 정규식 기반 추출의 한계가 명확하다. 다음 보수적인 패턴만 처리하고, 그 외는 사람 검수 대상으로 보고한다.

```regex
:AddText\(\s*"((?:[^"\\]|\\.)*)"\s*\)
:AddButton\(\s*"((?:[^"\\]|\\.)*)"\s*\)
:AddCollapsingHeader\(\s*"((?:[^"\\]|\\.)*)"\s*\)
:AddInputText\(\s*"((?:[^"\\]|\\.)*)"\s*,        # 첫 인자(라벨)
:AddInputText\(\s*"[^"]*"\s*,\s*"((?:[^"\\]|\\.)*)"\s*\)  # 둘째 인자(초기값)
\.Hint\s*=\s*"((?:[^"\\]|\\.)*)"
\.Text\s*=\s*"((?:[^"\\]|\\.)*)"
```

추출된 후보는 다음 블랙리스트로 한 번 더 거른다.

`^##`로 시작하는 문자열은 IMGUI 내부 ID이므로 제외한다. `[A-Z][a-zA-Z]+_[A-Z]` 패턴(예: `TooltipManager_ApplyConfigChunk`)은 네트워크 채널 이름이므로 제외한다. `^(Text|Button|FrameBg|TableRowBg|TableRowBgAlt|Header|Border)$`는 IMGUI 색상 슬롯이므로 제외한다. `^\.[a-z]+$`(예: `.json`)는 파일 확장자이므로 제외한다.

그리고 다음 짧은 단어들은 코드 내 다른 곳에서 비교 키로 쓰일 가능성이 매우 높으므로 **자동 처리 대상에서 빼고 사람 검수 큐로 보낸다**.

`All`, `Default`, `Root`, `Local`, `Vanilla`, `Hidden`, `On Hover`, `Alt-Highlight`, `Edited`, `Status`, `Icon`, `Visibility`, `Display Name`, `Internal Name`, `Lootable`, `Not Lootable`, `Containers Only`, `Non-Containers`, `Vanilla Only`, `Modded Only`, `Edited Only`, `Unedited Only`, `Hidden (0)`, `On Hover (1)`, `Alt-Highlight (2)`.

이 단어들에 대해서는 사람이 다음 두 방식 중 하나로 처리한다. (a) UI 표시용 라벨 맵을 도입해 영문 키와 한글 라벨을 분리한다. (b) 코드 전체에서 일관되게 한글로 일괄 치환하고 비교 분기까지 함께 수정한다. (a)가 더 깨끗하고 다국어 확장에도 유리하다.

Lua 파일을 다시 쓸 때는 들여쓰기와 라인 종료(`\r\n` vs `\n`)를 원본 그대로 유지해야 한다. 그래야 게임이 보고하는 줄 번호와 원본 줄 번호가 일치해 디버깅이 가능하다.

### 4.4 콤보 옵션 배열의 특별 처리

`combo.Options = { "A", "B", "C" }` 형태는 정규식 `(\w+)\.Options\s*=\s*\{([^}]*)\}`로 잡아 별도 큐에 보낸다. 추출 결과 Tooltip Manager에서 7개가 잡혔다. 이 큐는 자동 치환하지 않고 보고서에 “라벨 맵 도입 후보”로 표시한다. 사람이 각 옵션 배열에 대해 (a) 단순 표시인지 (b) 로직 키로도 쓰이는지 판단한 뒤 처리 방식을 결정한다.

### 4.5 산출물 구조

처리기는 다음 산출물을 생성한다.

원본 모드 PAK과 동일한 디렉터리 구조의 한글화본을 임시 디렉터리에 만든다. 그 안에는 (1) 한글 번역이 반영된 `MCM_blueprint.json`, (2) 한글 핸들 값이 들어간 `Localization/*.xml`, (3) 한글 치환된 `BootstrapClient.lua` 및 기타 Lua 파일이 들어간다. 마지막으로 이 디렉터리를 PAK으로 재패키징해 사용자가 BG3 모드 폴더에 바로 넣을 수 있도록 한다.

함께 생성할 보고서는 다음을 포함한다. 처리된 핸들 수, 처리된 Lua 문자열 수, 사람 검수 큐로 빠진 항목 목록(파일·줄 번호·원문 포함), 자동 처리 중 실패한 항목 목록.

---

## 5. 검증 계획 — Tooltip Manager 첫 사이클

첫 검증 사이클은 다음 순서로 돈다.

먼저 처리기를 실행해 한글화본을 생성한다. 그 다음 결과 diff를 사람이 직접 검토한다. 사람 검수 큐에 빠진 약 25~30개 짧은 단어(`"All"`, `"Vanilla Only"` 등)에 대해서는 라벨 맵 도입 방식으로 별도 패치를 만든다. 두 산출물을 합쳐 PAK으로 재패키징한다.

게임을 실행해 다음을 확인한다. MCM 사이드바에 모드 이름이 한글로 나오는가. 탭을 열었을 때 헤더·버튼·라벨이 한글로 나오는가. 콤보 박스 옵션이 한글로 나오고, 선택했을 때 필터가 정상 작동하는가(이게 핵심이다). 프리셋 저장·삭제·내보내기·불러오기가 정상 작동하는가. 아이템 테이블의 가시성 토글(`Hidden`/`On Hover`/`Alt-Highlight`)이 정상 작동하는가.

회귀가 발견되면 어떤 부류의 문자열이 잘못 처리됐는지 분류하고, 처리기의 화이트리스트·블랙리스트를 보정한다. 이 사이클을 두세 번 돌리면 다른 MCM 의존 모드에도 일반화할 만한 처리기가 완성될 것이다.

---

## 6. 다음 단계 작업 항목(Claude Code에서 착수)

Claude Code에서 BG3-Auto-Korean 저장소를 열고 다음 순서로 작업한다.

첫째, 본 문서와 `lua_translation_candidates.json`을 저장소 내부 `docs/mcm/` 디렉터리(없으면 생성)로 옮긴다. 그래야 저장소 git 이력에 분석 자료가 남는다.

둘째, 저장소 구조를 파악한다. 기존 처리 파이프라인이 어디서 PAK을 풀고, 어디서 XML 핸들 큐를 만들고, 어디서 번역 API를 호출하고, 어디서 재패키징하는지 위치를 식별한다. MCM 처리기는 PAK 압축 해제 직후·번역 큐 생성 직전 단계에 끼워 넣어야 한다.

셋째, 블루프린트 처리기 모듈을 작성한다. 입력은 모드 디렉터리 경로, 출력은 (a) 갱신된 `MCM_blueprint.json`과 (b) 표준 XML 핸들 큐에 추가할 항목 리스트다. 단위 테스트는 Tooltip Manager의 블루프린트로 작성한다.

넷째, Lua 처리기 모듈을 작성한다. 입력은 Lua 파일 경로, 출력은 (a) 한글 치환된 Lua 파일과 (b) 사람 검수 큐 리포트다. 단위 테스트는 Tooltip Manager의 `BootstrapClient.lua`로 작성한다.

다섯째, 두 처리기를 기존 파이프라인의 분기 지점에 통합한다. 통합 후 Tooltip Manager 전체 사이클을 한 번 돌려 PAK 산출물을 만든다.

여섯째, 게임에서 검증한다. 5절의 검증 항목을 따른다.

일곱째, 회귀가 있으면 처리기를 보정하고 사이클을 반복한다. 안정화되면 다른 MCM 의존 모드(사용자가 보유한 다른 샘플)로 검증을 확대한다.

---

## 7. 참고 자료

분석에 사용한 주요 파일은 다음 위치에 있다.

- 블루프린트: `F:\BG3ModFile\bg3-modders-multitool\UnpackedMods\Tooltip Manager\Mods\Tooltip Manager\MCM_blueprint.json`
- 로컬라이제이션: `F:\BG3ModFile\bg3-modders-multitool\UnpackedMods\Tooltip Manager\Localization\Test.xml`
- 클라이언트 Lua: `F:\BG3ModFile\bg3-modders-multitool\UnpackedMods\Tooltip Manager\Mods\Tooltip Manager\ScriptExtender\Lua\BootstrapClient.lua`
- 서버 Lua: `F:\BG3ModFile\bg3-modders-multitool\UnpackedMods\Tooltip Manager\Mods\Tooltip Manager\ScriptExtender\Lua\BootstrapServer.lua`
- meta.lsx: `F:\BG3ModFile\bg3-modders-multitool\UnpackedMods\Tooltip Manager\Mods\Tooltip Manager\meta.lsx`

외부 참조 자료는 다음과 같다.

- BG3MCM 저장소: https://github.com/AtilioA/BG3-MCM
- 블루프린트 JSON 스키마: https://github.com/AtilioA/BG3-MCM/blob/main/.vscode/schema.json
- Norbyte Script Extender 문서(Lua API): https://github.com/Norbyte/bg3se/blob/main/Docs/API.md
- 사용자 자체 도구: https://github.com/anboyu-alt/BG3-Auto-Korean

분석 일자는 2026-05-17이다. BG3MCM과 Script Extender는 자주 업데이트되므로, Claude Code에서 작업을 시작할 때 스키마와 API 문서의 최신 버전을 한 번 확인하는 게 좋다.
