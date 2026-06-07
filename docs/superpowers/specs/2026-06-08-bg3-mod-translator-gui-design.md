# BG3 Mod Translator — GUI 재설계 스펙

## 개요

**목표:** `bg3gui/`를 customtkinter에서 PySide6로 완전 재작성. `bg3core/`는 건드리지 않음.

**앱 이름:** BG3 Mod Translator (기존: BG3 Auto-Korean)

**버전:** 5.0 유지 (GUI 재설계는 버전 범프 없음)

**프레임워크:** PySide6 6.x (LGPL 라이선스 — 무료 배포 가능)

---

## 아키텍처

```
bg3core/          ← 변경 없음 (번역 엔진, MCM, divine 래퍼)
bg3gui/           ← 완전 재작성 (PySide6)
  app.py          ← QMainWindow, frameless window, 레이아웃 조립
  titlebar.py     ← 커스텀 드래그 가능 헤더 위젯
  sidebar.py      ← 아이콘+텍스트 세로 내비게이션
  theme.py        ← 색상 상수, QSS 스타일시트 생성
  i18n.py         ← UI 언어 로더 (ko/en 선택)
  i18n/
    ko.py         ← 한국어 UI 문자열 딕셔너리
    en.py         ← English UI 문자열 딕셔너리
  settings_tab.py ← 설정 화면 (QWidget)
  translate_tab.py← 번역 화면 (QWidget)
  reviewer_tab.py ← 검수 화면 (QWidget)
  glossary_tab.py ← 용어집 화면 (QWidget)
  workers.py      ← QThread 기반 번역 워커 (bg3core.pipeline 호출)
  widgets/
    path_picker.py← 파일/폴더 선택 복합 위젯
bg3_mod_translator.py  ← 새 진입점 (기존 bg3_autokorean_gui.py 대체)
bg3_autokorean_gui.py  ← 기존 진입점 유지 (하위 호환, 새 진입점으로 리디렉션)
```

`bg3core/config.py`에 필드 2개 추가:
- `app_language: str = "ko"` — 앱 UI 표시 언어 (기존 `target_language`와 별개)
- 기존 `target_language: str = "Korean"` 유지

---

## 비주얼 디자인

### 색상 팔레트 (theme.py 상수)

| 역할 | 값 |
|---|---|
| 배경 (앱) | `#1e1e1e` |
| 배경 (사이드바) | `#151515` |
| 배경 (입력/카드) | `#2a2a2a` |
| 배경 (로그) | `#111111` |
| 포인트 (골드) | `#d4a843` |
| 포인트 밝게 | `#e8b840` |
| 포인트 어둡게 | `#c49a30` |
| 헤더 그라디언트 시작 | `#1a1400` |
| 헤더 그라디언트 끝 | `#2d2100` |
| 구분선 | `#2a2a2a` |
| 텍스트 기본 | `#cccccc` |
| 텍스트 보조 | `#888888` |
| 텍스트 비활성 | `#555555` |
| 성공 | `#4a9a4a` |
| 경고 | `#d4a843` |
| 닫기 버튼 배경 | `#5a1a1a` |

### 창 구조

```
┌─────────────────────────────────────────────┐  ← 커스텀 타이틀바 (드래그 가능)
│ ⚔ BG3 MOD TRANSLATOR          _ □ ✕        │    골드 그라디언트 배경
├──────────┬──────────────────────────────────┤
│          │                                  │
│  사이드바 │   탭 컨텐츠 영역                  │  ← 스택 위젯 (탭 전환)
│  (96px)  │                                  │
│          │                                  │
├──────────┴──────────────────────────────────┤
│ 상태바: 현재 파일 · 언어 · 모델              │  ← 하단 상태바 (항상 표시)
└─────────────────────────────────────────────┘

기본 창 크기: 900 × 620 (최소: 720 × 500)
```

---

## 컴포넌트 상세

### 1. 커스텀 타이틀바 (`titlebar.py`)

- `Qt.WindowType.FramelessWindowHint`로 시스템 타이틀바 제거
- 골드 그라디언트 QLabel 배경
- ⚔ 아이콘 + "BG3 MOD TRANSLATOR" + "Powered by Gemini AI · v5.0"
- 최소화/최대화/닫기 버튼 (커스텀 QToolButton)
- `mousePressEvent` / `mouseMoveEvent`로 드래그 이동 구현

### 2. 사이드바 (`sidebar.py`)

- 96px 고정 폭
- 각 항목: 이모지 아이콘(⚙ 🔄 🔍 📖) + 텍스트 레이블 (SVG 교체는 향후)
- 활성 항목: `#2a2000` 배경 + 왼쪽 3px `#d4a843` 보더
- 비활성: `#666` 텍스트, hover 시 `#2a2a2a` 배경
- 메뉴 4개: 설정 / 번역 / 검수 / 용어집 (i18n 적용)
- 하단: 버전 문자열 (`#3a3a3a`)

### 3. 번역 탭 (`translate_tab.py`) — 로그 중심 레이아웃

위에서 아래 순서:
1. **파일 선택 행**: 경로 표시 QLineEdit + 찾기 버튼
2. **언어/모델 행**: 번역 대상 언어 드롭다운 + Gemini 모델 드롭다운 (가로 반반)
3. **버튼 행**: 번역 시작(골드, flex) + 일시정지 + 중단
4. **진행 바**: QProgressBar (골드 그라디언트) + "N/M 파일 · X%" 레이블
5. **로그 영역**: QPlainTextEdit (읽기 전용, 다크 배경, 색상 구분 로그) — **화면의 나머지 전부 차지**

로그 색상 규칙:
- 완료 줄: `#4a9a4a`
- 진행 중: `#d4a843`
- 대기: `#444444`
- 에러: `#cc4444`

### 4. 설정 탭 (`settings_tab.py`)

기존 customtkinter 버전과 동일한 필드 + 신규 2개:
- Gemini API Key (마스킹, 표시/숨김 토글)
- Divine.exe 경로 (PathPicker)
- AI 모델 1순위 / 2순위
- UI 배율 (auto / 1.0 / 1.25 / 1.5 / 1.75 / 2.0)
- **번역 대상 언어** (15개 BG3 언어, 기존)
- **[신규] 앱 UI 언어** (한국어 / English — 변경 시 재시작 안내 다이얼로그)
- 번역 캐시 파일 경로
- 번역 완료 스킵 여부 (체크박스)
- MCM 자동 처리 (체크박스)
- 저장 / API 테스트 버튼

### 5. i18n 시스템 (`i18n.py` + `i18n/`)

```python
# i18n/ko.py 예시
STRINGS = {
    "menu.settings": "설정",
    "menu.translate": "번역",
    "menu.review": "검수",
    "menu.glossary": "용어집",
    "translate.start": "번역 시작",
    "translate.pause": "일시정지",
    "translate.stop": "중단",
    "translate.file_label": "PAK 파일 / 폴더",
    "translate.browse": "찾기",
    "translate.log_header": "TRANSLATION LOG",
    "translate.log_clear": "지우기",
    # ... 전체 UI 문자열
}
```

```python
# i18n.py
_current: dict = {}

def load(lang_code: str) -> None:
    global _current
    if lang_code == "en":
        from .i18n.en import STRINGS
    else:
        from .i18n.ko import STRINGS
    _current = STRINGS

def t(key: str) -> str:
    return _current.get(key, key)
```

모든 위젯 텍스트는 `t("key")` 로 설정. `config.app_language` 변경 시 재시작 필요 (QMessageBox 안내).

### 6. 워커 (`workers.py`)

`QThread` 기반으로 재작성 (기존 `threading.Thread` → `QThread`).
`bg3core.pipeline.run_batch` 호출 시그니처는 동일 — `target_language=cfg.target_language` 포함.
진행 이벤트는 Qt 시그널(`pyqtSignal` → `Signal`)로 메인 스레드에 전달.

---

## config.py 변경

```python
# bg3core/config.py 에 추가
app_language: str = "ko"   # "ko" | "en"
```

기존 JSON config와 하위 호환 (`setattr` 루프로 자동 처리).

---

## 진입점

`bg3_mod_translator.py` (신규):
```python
"""BG3 Mod Translator — 진입점."""
# bg3gui (PySide6) 임포트 후 실행
```

`bg3_autokorean_gui.py` (기존):
- 기존 파일 유지, 내용을 `bg3_mod_translator.py`로 리디렉션하는 한 줄로 교체
- PyInstaller spec 파일도 신규 진입점 기준으로 업데이트

---

## 범위 외 (이번 작업에서 하지 않음)

- GitHub 레포 이름 변경 (`BG3-Auto-Korean` → `BG3-Mod-Translator`)
- 앱 UI 언어 3개 이상 추가 (ko/en만 우선)
- 다크/라이트 테마 전환
- 버전 범프 (5.0 유지)

---

## 검증 방법

1. `python bg3_mod_translator.py` 실행 → 앱 정상 기동, v5.0 표시
2. 설정 탭에서 앱 UI 언어를 English로 변경 → 재시작 후 모든 메뉴·버튼 영문 표시
3. 번역 탭에서 PAK 선택 후 번역 시작 → 로그 실시간 표시, 진행바 동작
4. 검수 / 용어집 탭 기능 기존과 동일
5. `python -m pytest tests/ -v` — bg3core 테스트 전부 통과 (GUI 변경과 무관)
6. PyInstaller 빌드: `pyinstaller bg3_mod_translator.spec` → EXE 정상 생성
