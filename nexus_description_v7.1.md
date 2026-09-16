⚠ IMPORTANT — Output is for personal use only
This tool repackages the entire original mod, so the translated .pak it produces contains the original author's assets and scripts. Do NOT upload or redistribute the output without the original author's explicit permission — doing so violates their rights and Nexus rules and can lead to an account ban. Keep translated files for personal use, or get the author's permission before sharing.

⚠ This is a one-time-setup tool, NOT a drag-and-drop mod. Downloading the file alone is not enough — you MUST follow the full setup guide on GitHub (link below) before using it.

🆕 What's new in v7.1 (bug-fix release)
- Legacy PAK support: mods packed with older LSLib (V15/V16) now unpack correctly. This fixes the "PAK unpack failed" error and the case where "Translation complete" appeared right away but no translated PAK was created.
- Fixed unpack failure on PAKs that contain empty (zero-byte) files — common in Toolkit-built mods (e.g. Thor, several class mods). Those mods now translate normally.
- Failure reasons are now visible: if unpacking or repacking fails, the reason is shown in red in the translation log and in the Review tab's error dialog, with a "Failed" summary line.
- Your custom glossary now takes top priority over the translation cache and the official language pack (e.g. Bonus Action → the term you set).
- Log display fixes: no more raw "LogEvent(...)" lines, and "Translation complete!" no longer appears twice.

🆕 What's new in v7.0
- No external tools needed anymore: Divine.exe (LSLib) and the .NET runtime are gone. The app now reads and repacks .pak/.loca natively, so the only setup is a free Gemini API key.
- Official language-pack reference is now ON by default: exact matches reuse the official translation with zero API calls — more consistent terminology and lower cost.
- Now distributed as a portable ZIP (folder build): just extract and run, with no antivirus false positives.

🆕 What's new in v6.0
- App interface now available in 15 languages, and it auto-detects your game's language on first launch (target + UI matched for you).
- Official language-pack reference: use your installed game's official translations as a reference — exact matches reuse the official wording (saving API calls) and in-sentence terms are kept consistent. Works for all 15 languages.
- Review tab redesigned as a vertical card list: source and translation are stacked per entry with the full source text shown (no more truncation), and the translation box grows to fit.
- My Glossary is now edited inline, spreadsheet-style.
- First-run setup wizard + automatic BG3 install-folder detection (Steam) make the initial setup much easier.

Description
BG3 Mod Translator is a free, standalone desktop app that automatically translates the text of Baldur's Gate 3 mods using Google Gemini AI. It is NOT an in-game mod — it's a tool you run on your PC to turn a mod's .pak into a translated version.
Unlike one-way translators, it works any language to any language: the source language is auto-detected, and you can translate into any of 15 target languages (e.g. a Russian mod into English, a Polish mod into Korean, or an English mod into Japanese).

Main features
- 15 target languages: Korean, English, Japanese, French, German, Spanish, Latin Spanish, Italian, Polish, Russian, Ukrainian, Turkish, Brazilian Portuguese, Chinese (Simplified), Chinese (Traditional)
- App interface available in all 15 languages — auto-matched to your game's language (falls back to English for any untranslated text)
- Source language is auto-detected
- No Python, no installation, and no external tools required (handles .pak/.loca natively — Divine.exe and .NET are no longer needed)
- Works with both current (V18) and legacy (V15/V16) .pak files
- First-run setup wizard guides you through the API key and the BG3 folder; the BG3 install folder is auto-detected (Steam)
- Batch mode: translate every .pak in a folder at once
- Official language-pack reference (on by default): reuse your installed game's official translations for consistent terminology across all 15 languages, and to save API calls. The dictionary is built once from your local game files and cached — official text is never redistributed.
- Built-in 347-term BG3 glossary (character names, abilities, spells) — English to Korean. You can also add and edit your own custom glossary inline (spreadsheet-style); your own entries always take priority over the built-in glossary, the cache and the official pack. For other languages, enable the official language-pack reference above for consistent official terms.
- Translation cache reuses past results to save time and API usage
- Review tab: a vertical card list that shows each entry's full source text with the translation right below it (edit inline; the box auto-resizes), so you can proofread and fix errors before building the final .pak
- MCM support: also translates Mod Configuration Menu mods (blueprint + Lua text)
- The original .pak is never modified; a separate _<language>.pak is created

Requirement (one-time, free)
- A free Google Gemini API key — https://aistudio.google.com (the AI that performs the translation). That's the only thing you need — no Divine.exe and no .NET runtime.

About API cost
The Gemini API has a free tier that is enough for most users. Very heavy use may exceed the free limits and could incur charges on your own Google account. You can check usage at https://aistudio.google.com. By default the tool uses a lightweight, low-cost model.

Installation
1. Download the ZIP from the Files tab, extract ALL files into one folder, and run BG3_ModTranslator.exe inside that folder. No installation needed. The folder build has no antivirus false positives — don't delete the other files next to the .exe; they're required.
2. On first launch, a setup wizard walks you through entering your free Gemini API key and confirming the BG3 folder (auto-detected when possible). You can also change these later in Settings.
3. In the Translate tab, pick a .pak (or a folder), choose the target language and AI model, then press Start.
4. Install the resulting _<language>.pak with your mod manager and set the game language accordingly. Enable ONLY the translated PAK — do not enable the original .pak alongside it (same mod UUID → conflicts).

Please note (AI-generated content)
Translations are generated by Google Gemini AI and may contain mistakes. Use the built-in Review tab and glossary to proofread and correct them.

Reporting problems
Since v7.1 the translation log shows the exact reason when something fails (red lines). If you report an issue, please include the mod name and those red log lines — it makes fixing things much faster.

⚠ READ THIS BEFORE USING — full setup & usage guide
This tool requires a one-time setup (a free Gemini API key). It will NOT work if you only download the file here. Please follow the complete step-by-step guide on GitHub — it walks you through everything with screenshots, in English and Korean:
👉 https://github.com/anboyu-alt/BG3-Auto-Korean
Almost every "how do I use this?" question is already answered there. Please read it first before posting in the comments. Thank you!

Shout outs
Thanks to everyone who reported bugs on v7.0 — every fix in v7.1 came straight from your reports.
Special thanks to frodocompl for the ideas and suggestions that shaped recent updates — much appreciated!
Special thanks to the Baldur's Gate 3 community at DCInside for the countless bug reports, testing, and reviews throughout development — this tool would not be what it is without you. https://gall.dcinside.com/mgallery/board/lists/?id=bg3
Thanks also to Norbyte for LSLib — its .pak/.loca format made the native implementation possible — and to the entire BG3 modding community.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[한국어]

참고: Nexus는 실행 파일이 포함된 업로드를 자동으로 검토(일시 격리)할 수 있습니다. 이 ZIP은 폴더형 빌드라 백신 오탐이 없지만, 검토 중 다운로드가 일시적으로 막히면 GitHub 릴리스를 이용하세요.

⚠ 중요 — 출력물은 개인적인 용도로만 사용하십시오.
이 도구는 원본 모드 전체를 다시 패키징하므로, 생성된 번역된 .pak 파일에는 원작자의 에셋과 스크립트가 모두 포함되어 있습니다. 원작자의 명시적 허가 없이 번역된 파일을 업로드·재배포하지 마십시오. 이는 원작자의 권리와 Nexus 규칙 위반이며 계정 정지 등 불이익을 받을 수 있습니다. 번역된 파일은 개인 용도로만 사용하거나, 공유 전 반드시 원작자의 허가를 받으십시오.

⚠ 이 도구는 1회 설정이 필요한 도구이며, 드래그 앤 드롭 방식의 모드가 아닙니다. 파일 다운로드만으로는 작동하지 않으며, 사용 전 GitHub(하단 링크)의 전체 설정 가이드를 반드시 따라야 합니다.

🆕 v7.1의 새로운 점 (오류 수정 판)
- 구버전 PAK 지원: 예전 LSLib(V15·V16)로 묶인 모드도 정상 언팩됩니다. "PAK 언팩에 실패했습니다" 오류와, 곧바로 "번역 완료"만 뜨고 번역 PAK이 생성되지 않던 문제가 해결됩니다.
- 빈 파일(크기 0)이 든 PAK 언팩 실패 수정 — 툴킷으로 만든 모드(Thor, 여러 클래스 모드 등)에 흔한 경우로, 이제 정상 번역됩니다.
- 실패 이유가 보입니다: 언팩·리팩이 실패하면 번역 로그에 빨간색으로 이유가 표시되고, 검수 탭 오류 창에도 나타나며 "Failed" 요약 줄이 남습니다.
- 내 용어집이 번역 캐시·공식 언어팩보다 먼저 적용됩니다(예: Bonus Action → 내가 정한 용어).
- 로그 표시 오류 수정: "LogEvent(...)" 형태로 찍히던 문제, "번역 완료!"가 두 번 뜨던 문제.

🆕 v7.0의 새로운 점
- 외부 툴이 더 이상 필요 없습니다: Divine.exe(LSLib)와 .NET 런타임이 사라졌습니다. 앱이 .pak/.loca를 자체적으로 읽고 다시 패킹하므로, 설정은 무료 Gemini API 키 하나뿐입니다.
- 공식 언어팩 참조가 기본 켜짐: 정확히 일치하는 텍스트는 API 호출 없이 공식 번역을 그대로 재사용합니다 — 용어 일관성↑, 비용↓.
- 포터블 ZIP(폴더형)으로 배포: 압축만 풀어 실행하면 되고, 백신 오탐이 없습니다.

🆕 v6.0의 새로운 점
- 앱 화면이 15개 언어를 지원하며, 첫 실행 시 게임 설정 언어를 자동 감지해 번역 대상 언어와 UI를 함께 맞춰 줍니다.
- 공식 언어팩 참조(신규, 선택): 설치된 게임의 공식 번역을 기준으로 활용합니다. 정확히 일치하는 텍스트는 공식 번역을 그대로 재사용해 API 사용을 줄이고, 문장 속 용어는 공식 표기와 일관되게 번역합니다. 15개 언어 모두 지원합니다.
- 검수 탭을 세로 카드 리스트로 개편: 항목마다 원문과 번역이 위아래로 쌓이고, 긴 원문도 잘리지 않고 전부 표시되며 번역 칸은 내용에 맞춰 늘어납니다.
- 내 용어집을 표에서 바로 입력·수정(엑셀식 인라인 편집)할 수 있습니다.
- 첫 실행 안내 위저드 + BG3 설치 폴더 자동 감지(Steam)로 초기 설정이 훨씬 쉬워졌습니다.

설명
BG3 Mod Translator는 Google Gemini AI로 Baldur's Gate 3 모드 텍스트를 자동 번역하는 무료 독립형 데스크톱 앱입니다. 게임 내 모드가 아니라, PC에서 실행해 모드의 .pak을 번역본으로 변환하는 도구입니다.
단방향 번역기와 달리 어떤 언어→어떤 언어로든 번역됩니다. 원어는 자동 감지되며 15개 대상 언어 중 원하는 언어로 번역할 수 있습니다(예: 러시아어→영어, 폴란드어→한국어, 영어→일본어).

주요 특징
- 15개 지원 언어: 한국어, 영어, 일본어, 프랑스어, 독일어, 스페인어, 라틴 스페인어, 이탈리아어, 폴란드어, 러시아어, 우크라이나어, 터키어, 브라질 포르투갈어, 중국어(간체), 중국어(번체)
- 앱 화면도 15개 언어 전부 제공 — 게임 언어에 자동으로 맞춰지며, 번역되지 않은 텍스트는 영어로 표시됩니다
- 원어 자동 감지
- 파이썬·설치·외부 툴 모두 불필요 (.pak/.loca를 자체 처리 — Divine.exe와 .NET이 더 이상 필요 없습니다)
- 최신(V18)·구버전(V15·V16) .pak 모두 지원
- 첫 실행 안내 위저드가 API 키·BG3 폴더 설정을 안내하며, BG3 설치 폴더는 자동 감지(Steam)됩니다
- 일괄 모드: 폴더 안 모든 .pak 한 번에 번역
- 공식 언어팩 참조(기본 켜짐): 설치된 게임의 공식 번역을 기준으로 활용해 15개 언어 모두에서 용어를 일관되게 유지하고 API 사용을 줄입니다. 사전은 내 로컬 게임 파일에서 한 번만 만들어 캐시하며, 공식 텍스트를 외부로 재배포하지 않습니다.
- 347개 용어 내장 BG3 용어집(캐릭터·능력·주문) — 영어→한국어. 사용자 지정 용어집을 표에서 바로 추가·수정(엑셀식 인라인)할 수 있으며, 내 용어집은 기본 용어집·캐시·공식 언어팩보다 항상 우선합니다. 다른 언어는 위의 공식 언어팩 참조를 켜면 공식 용어를 일관되게 쓸 수 있습니다.
- 번역 캐시로 시간·API 사용량 절약
- 검수 탭: 세로 카드 리스트로, 항목마다 원문 전체와 그 아래 번역을 함께 보여줍니다(바로 편집, 칸 높이 자동 조절). 최종 .pak 생성 전 교정·수정하세요.
- MCM 지원: 모드 구성 메뉴(MCM) 모드(블루프린트 + Lua)도 번역
- 원본 .pak은 절대 수정되지 않고 별도 _<언어>.pak 생성

필수 사항 (1회, 무료)
- 무료 Google Gemini API 키 — https://aistudio.google.com (번역을 수행하는 AI). 필요한 건 이것 하나뿐이며, Divine.exe와 .NET 런타임은 필요 없습니다.

API 비용에 관하여
Gemini API는 대부분 사용자에게 충분한 무료 요금제를 제공합니다. 사용량이 매우 많으면 무료 한도를 초과해 본인 Google 계정에 요금이 부과될 수 있습니다. 사용량은 https://aistudio.google.com 에서 확인하세요. 기본적으로 가볍고 저렴한 모델을 사용합니다.

설치 방법
1. 파일 탭에서 ZIP을 받아 모든 파일을 한 폴더에 압축 해제한 뒤, 그 폴더 안의 BG3_ModTranslator.exe를 실행하세요. 설치 불필요. 폴더형 빌드라 백신 오탐이 없습니다 — .exe 옆의 다른 파일들은 실행에 필요하니 지우지 마세요.
2. 첫 실행 시 안내 위저드가 무료 Gemini API 키 입력과 BG3 폴더 확인을 단계별로 도와줍니다(가능하면 자동으로 채워집니다). 이 값들은 나중에 설정에서 바꿀 수 있습니다.
3. 번역 탭에서 .pak(또는 폴더)을 선택하고 대상 언어·AI 모델을 고른 뒤 시작을 누르세요.
4. 생성된 _<언어>.pak을 모드 매니저로 설치하고 게임 언어를 설정하세요. 번역 PAK 하나만 활성화하고, 원본 .pak은 함께 등록하지 마세요(같은 모드 UUID라 충돌합니다).

참고 (AI 생성 콘텐츠)
번역은 Google Gemini AI가 생성하므로 오류가 있을 수 있습니다. 내장 검수 탭과 용어집으로 교정·수정하세요.

문제 제보 시
v7.1부터 번역이 실패하면 로그에 정확한 이유가 빨간색으로 표시됩니다. 제보하실 때 모드 이름과 그 빨간 로그 줄을 함께 적어주시면 훨씬 빨리 고칠 수 있습니다.

⚠ 사용 전 반드시 읽어주세요 — 전체 설치·사용 가이드
이 도구는 1회 설정(무료 Gemini API 키)이 필요합니다. 여기서 파일만 받아서는 작동하지 않습니다. GitHub의 전체 단계별 가이드(영어·한국어 스크린샷 포함)를 따라주세요:
👉 https://github.com/anboyu-alt/BG3-Auto-Korean
"어떻게 쓰나요?"에 대한 답은 거의 모두 README에 있습니다. 댓글 전에 먼저 README를 읽어주세요. 감사합니다!

샤우트아웃
v7.0의 오류를 제보해 주신 모든 분께 감사드립니다. v7.1의 수정은 전부 여러분의 제보에서 나왔습니다.
최근 업데이트의 방향을 잡아준 아이디어와 제안을 주신 frodocompl님께 특별히 감사드립니다. 덕분에 더 좋은 도구가 되었습니다!
개발 기간 내내 수많은 버그 제보·테스트·리뷰로 도와주신 디시인사이드 발더스 게이트 3 갤러리 여러분께 진심으로 감사드립니다. 여러분이 없었다면 이 도구는 지금의 모습이 될 수 없었습니다. https://gall.dcinside.com/mgallery/board/lists/?id=bg3
LSLib을 만들어주신 Norbyte님께 감사드립니다 — 그 .pak/.loca 포맷 덕분에 자체 구현이 가능했습니다. BG3 모딩 커뮤니티 전체에도 감사드립니다.
