# BG3 모드 자동 한글화 스크립트 v2.2

발더스 게이트 3(Baldur's Gate 3) 모드의 텍스트를
Google Gemini AI를 이용하여 자동으로 한국어로 번역해주는 스크립트입니다.
번역 후 오역을 직접 검수하고 수정할 수 있는 검수 도구도 포함되어 있습니다.

---

## 한글화의 원리

BG3 모드의 텍스트는 모드 파일(`.pak`) 안에 아래와 같은 구조로 들어있습니다:

```
SomeMod.pak (모드 파일)
└── Mods/
    └── SomeMod/
        └── Localization/        ← 여기가 언어 파일이 모여있는 곳
            └── English/         ← 영어 원문
                └── SomeMod.xml  ← 실제 텍스트가 들어있는 XML 파일
```

XML 파일을 열어보면 이런 식입니다:

```xml
<content contentuid="h12345">This spell deals 2d6 fire damage.</content>
<content contentuid="h12346">Fireball</content>
```

**이 스크립트가 하는 일:**
1. `English` 폴더 안의 XML을 읽어서
2. `<content>` 태그 안의 텍스트를 Gemini AI로 한국어 번역하고
3. 번역된 XML을 `Korean` 폴더에 저장합니다

```
Localization/
├── English/         ← 원본 (절대 수정하지 않음)
│   └── SomeMod.xml
└── Korean/          ← 번역 결과 (스크립트가 자동 생성)
    └── SomeMod.xml
```

BG3는 게임 설정에서 언어를 "한국어"로 바꾸면 자동으로 `Korean` 폴더의 파일을 읽습니다.
그래서 `Korean` 폴더에 번역된 파일만 넣어주면 한글화가 되는 것입니다.

> **참고: `.loca` 바이너리 형식**
> 일부 모드는 텍스트를 XML이 아닌 `.loca`라는 바이너리 형식으로 저장합니다. PAK 모드는 이런 파일을 자동으로 XML로 변환한 후 번역하므로 신경 쓸 필요 없습니다.

이 원리를 이해하면 코드를 자신의 환경에 맞게 수정하기도 쉬워집니다.

---

## 파일 구성

이 프로젝트에는 세 개의 파일이 있습니다:

| 파일 | 설명 |
|------|------|
| `BG3_AutoKorean_PAK_v2.2.py` | **PAK 모드** — .pak 파일을 넣으면 전자동 번역 |
| `BG3_AutoKorean_Folder_v2.2.py` | **폴더 모드** — 이미 풀어놓은 모드 폴더를 번역 |
| `BG3_AutoKorean_Reviewer_v2.2.py` | **번역 검수 도구** — 한글화된 .pak의 번역을 검수하고 수정 |

### 번역 스크립트 (PAK 모드 vs 폴더 모드)

두 번역 스크립트의 **번역 엔진은 완전히 동일**합니다.
용어집, 캐시, AI 호출 방식, 번역 품질 전부 같습니다.

**유일한 차이는 "번역 전후 작업을 어떤 도구로 처리하느냐"입니다:**

- **PAK 모드**: `.pak` 파일을 넣으면 `divine.exe`(LSLib)가 자동으로 풀고(언팩) → 번역하고 → 다시 묶어줍니다(리팩). 한 번에 끝!
- **폴더 모드**: 사용자가 직접 BG3 Modder's Multitool로 `.pak`을 풀어서 폴더를 만든 다음, 이 스크립트로 번역만 수행합니다. 리팩(다시 묶기)도 직접 해야 합니다.

### 어떤 버전을 선택해야 할까요?

- **처음 사용하시거나 편한 방법을 원하시면** → `BG3_AutoKorean_PAK_v2.2.py` (PAK 모드)
- **BG3 Modder's Multitool을 이미 쓰고 계시면** → `BG3_AutoKorean_Folder_v2.2.py` (폴더 모드)
- **번역 결과를 검수/수정하고 싶으면** → `BG3_AutoKorean_Reviewer_v2.2.py` (검수 도구)

---

## 사전 준비

### 공통 (두 버전 모두 필요)

**1. Python 설치**
- [python.org/downloads](https://www.python.org/downloads/) 에서 다운로드
- 설치할 때 **"Add Python to PATH"** 옵션을 반드시 체크하세요

**2. Gemini API 키 발급 (무료)**
1. [aistudio.google.com](https://aistudio.google.com) 접속 (Google 계정 필요)
2. 왼쪽 메뉴에서 **"Get API key"** 클릭
3. **"Create API key"** 버튼 클릭
4. 생성된 키(`AIzaSy...`로 시작)를 복사해 둡니다

> API 키는 타인에게 공유하지 마세요.

### PAK 모드 / 검수 도구 — 추가로 필요한 것

**3. LSLib (ExportTool) 다운로드** — PAK 모드와 검수 도구 모두 필요
1. [github.com/Norbyte/lslib/releases](https://github.com/Norbyte/lslib/releases) 에서 `ExportTool-vX.X.X.zip` 다운로드
2. 압축 해제
3. `Divine.exe` 위치: `ExportTool폴더/Packed/Tools/Divine.exe`

**4. .NET 8.0 런타임**
- `Divine.exe` 실행에 필요합니다
- [dotnet.microsoft.com/download/dotnet/8.0](https://dotnet.microsoft.com/download/dotnet/8.0) → ".NET Desktop Runtime" 설치
- 이미 설치되어 있으면 이 단계를 건너뛰세요

> **참고:** 검수 도구(`BG3_AutoKorean_Reviewer_v2.2.py`)도 `divine.exe`를 사용합니다. PAK 모드를 이미 설정했다면 추가 준비 없이 바로 사용 가능합니다.

### 폴더 모드 전용 — 추가로 필요한 것

**3. BG3 Modder's Multitool**
- [github.com/ShinyHobo/BG3-Modders-Multitool](https://github.com/ShinyHobo/BG3-Modders-Multitool) 에서 다운로드

---

## 사용법: PAK 모드 (`BG3_AutoKorean_PAK_v2.2.py`)

가장 간단한 방법입니다. `.pak` 파일만 있으면 됩니다.

### 단계 요약

```
.pak 파일 준비 → 스크립트 실행 → _Korean.pak 생성 → 모드 매니저로 설치
```

### 1. 모드 파일 준비

한글화할 모드를 다운로드하면 보통 `.zip` 안에 `.pak` 파일이 있습니다.

### 2. 설정

`BG3_AutoKorean_PAK_v2.2.py`를 메모장으로 열어서 **[설정 구간]**을 수정합니다:

```python
API_KEY = "여기에 발급받은 API 키 붙여넣기"
DIVINE_EXE = r"C:\ExportTool-v1.20.4\Packed\Tools\Divine.exe"
TARGET_PAK = r"C:\Mods\SomeMod.pak"
```

> 경로 앞에 `r`을 붙이고 큰따옴표로 감싸세요. (예: `r"C:\경로\파일"`)
>
> 세 값을 모두 비워두면 실행할 때 하나씩 입력할 수 있습니다.

### 3. 실행

`BG3_AutoKorean_PAK_v2.2.py`를 **더블클릭**하거나 터미널에서 실행:
```
python BG3_AutoKorean_PAK_v2.2.py
```

### 4. 결과

원본 `.pak`과 같은 폴더에 `_Korean.pak`이 생성됩니다:
```
C:\Mods\
├── SomeMod.pak            ← 원본 (변경 없음)
└── SomeMod_Korean.pak     ← 한글화된 모드 (자동 생성)
```

이 `_Korean.pak`을 모드 매니저(Vortex, BG3 Mod Manager)로 설치하면 끝!

> **여러 모드 한번에 한글화하기:** `.pak` 파일 하나가 아니라 **폴더 경로**를 지정하면, 그 안에 있는 모든 `.pak`을 자동으로 찾아서 한번에 처리합니다. 한글화할 모드를 한 폴더에 모아놓고 그 폴더 경로를 지정하세요.

---

## 사용법: 폴더 모드 (`BG3_AutoKorean_Folder_v2.2.py`)

BG3 Modder's Multitool로 이미 `.pak`을 풀어놓은 경우에 사용합니다.

### 단계 요약

```
.pak 언팩(Multitool) → 스크립트 실행 → Korean 폴더 생성 → 리팩(Multitool) → 설치
```

### 1. Multitool로 .pak 언팩

BG3 Modder's Multitool의 "Unpack" 기능으로 `.pak` 파일을 풀어줍니다.

### 2. 설정

`BG3_AutoKorean_Folder_v2.2.py`를 메모장으로 열어서 **[설정 구간]**을 수정합니다:

```python
API_KEY = "여기에 발급받은 API 키 붙여넣기"
TARGET_ROOT_FOLDER = r"C:\경로\bg3-modders-multitool"
```

### 3. 실행

`BG3_AutoKorean_Folder_v2.2.py`를 **더블클릭**하거나 터미널에서 실행:
```
python BG3_AutoKorean_Folder_v2.2.py
```

### 4. 결과 확인

`Localization` 폴더 안에 `Korean` 폴더가 자동 생성됩니다:
```
Localization/
├── English/         ← 원본
└── Korean/          ← 번역 결과 (자동 생성)
```

### 5. Multitool로 리팩 후 설치

Multitool의 "Pack" 기능으로 다시 `.pak`으로 묶은 후 모드 매니저로 설치합니다.

> **여러 모드 한번에 한글화하기:** 여러 모드를 Multitool로 언팩해놓았다면, **상위 폴더 경로**를 `TARGET_ROOT_FOLDER`에 지정하세요. 스크립트가 하위 폴더를 자동으로 탐색하여 `Localization` 폴더가 있는 모드를 모두 찾아 한번에 번역합니다.
>
> ```
> UnpackedMods/                ← 이 경로를 지정하면
> ├── ModA/.../Localization/   ← 자동 탐색 → 번역
> ├── ModB/.../Localization/   ← 자동 탐색 → 번역
> └── ModC/.../Localization/Korean/  ← 이미 한글화됨 → 스킵
> ```

---

## 사용법: 번역 검수 도구 (`BG3_AutoKorean_Reviewer_v2.2.py`)

AI 번역은 오역이 포함될 수 있습니다. 이 도구로 영어 원문과 한국어 번역을 나란히 비교하면서 직접 수정할 수 있습니다.

### 단계 요약

```
한글화된 .pak 파일 → 검수 도구 실행 → 원문/번역 비교 → 수정 → 저장
```

### 1. 설정

`BG3_AutoKorean_Reviewer_v2.2.py`를 메모장으로 열어서 `DIVINE_EXE`만 설정합니다:

```python
DIVINE_EXE = r"C:\ExportTool-v1.20.4\Packed\Tools\Divine.exe"
```

> PAK 모드 번역 스크립트에서 이미 설정했다면 같은 경로를 넣으면 됩니다.
>
> `TARGET_PAK`은 비워두세요. 실행할 때마다 다른 파일을 검수하게 되니까요.

### 2. 실행 (3가지 방법)

**방법 1: 드래그 앤 드롭 (가장 간편)**
검수할 `.pak` 파일을 `BG3_AutoKorean_Reviewer_v2.2.py` 위에 끌어다 놓으면 바로 실행됩니다.

**방법 2: 더블클릭 후 경로 입력**
스크립트를 더블클릭하면 `.pak` 파일 경로나 폴더 경로를 입력할 수 있습니다.
폴더를 입력하면 안에 있는 `.pak` 목록이 표시되어 번호로 선택할 수 있습니다.

**방법 3: 터미널에서 실행**
```
python BG3_AutoKorean_Reviewer_v2.2.py
```

### 3. 검수 화면

영어 원문과 한국어 번역이 나란히 표시됩니다:

```
══════════════════════════════════════════════════════
  번역 검수 도구 v2.2  |  ModName.xml  |  3 / 127
══════════════════════════════════════════════════════

  [원문 - English]
  This spell deals 2d6 fire damage to all creatures
  within a 20-foot radius.

  [번역 - Korean]
  이 주문은 20피트 반경 내 모든 크리처에게 2d6 화염
  피해를 줍니다.

──────────────────────────────────────────────────────
  스페이스: 다음  |  b: 이전  |  e: 수정
  s: 저장  |  q: 종료  |  /: 검색
══════════════════════════════════════════════════════
```

### 4. 조작법

| 키 | 동작 |
|----|------|
| 스페이스 / 엔터 | 다음 항목 |
| `b` | 이전 항목 |
| `e` | 현재 번역 수정 |
| `s` | 수정사항 저장 후 .pak 재생성 |
| `q` | 종료 |
| `g` | 번호로 이동 |
| `/` | 텍스트 검색 (영문/한글 모두) |
| `m` | 수정한 항목만 보기 |

### 5. 팁

> **게임 폴더에서 바로 검수 가능:** `.pak` 파일을 게임 모드 폴더에서 꺼내지 않아도 됩니다. 게임 폴더에 있는 `.pak` 파일을 그대로 드래그하거나 경로를 입력하면 바로 검수할 수 있습니다.

> **한글화 직후 검수가 가장 편합니다:** PAK 모드로 한글화를 완료하면 `_Korean.pak`이 생성되는데, 이걸 바로 검수 도구에 넣으면 번역 품질을 즉시 확인하고 수정할 수 있습니다. 게임에 설치한 뒤에 나중에 검수하는 것보다 훨씬 편합니다.

---

## 주요 기능

- **AI 번역**: Google Gemini를 이용한 고품질 번역
- **용어집 350개+**: 캐릭터명, 능력치, 주문명, 상태이상 등 BG3 고유 용어를 정확하게 번역
- **번역 캐시**: 한 번 번역한 텍스트는 `translation_cache.json`에 저장하여 재사용
- **로컬 선처리**: 숫자, 코드, 이미 한국어인 텍스트는 API 호출 없이 즉시 처리
- **중복 제거**: 같은 텍스트가 여러 번 나오면 한 번만 번역
- **태그 보호**: XML 태그가 번역 중 깨지지 않도록 자동 보호 및 복원
- **다중 모델 폴백**: 1순위 모델 실패 시 자동으로 다른 모델로 재시도
- **번역 검수 도구**: 영어 원문과 한국어 번역을 나란히 비교하며 오역 수정 가능

---

## 코드 수정 가이드

이 스크립트는 자유롭게 수정해서 사용하셔도 됩니다. 코드 안에 각 섹션마다 설명이 달려 있으니 참고하세요.

**수정하기 좋은 부분:**

| 섹션 | 설명 |
|------|------|
| `[설정 구간]` | API 키, 경로 등 기본 설정 |
| `[용어집]` | 고유명사 번역 추가/수정 (GLOSSARY 딕셔너리) |
| `[고급 설정]` | AI 모델 변경, 청크 크기 조정 |
| `[번역 파이프라인]` | 번역 로직 자체를 바꾸고 싶을 때 |
| `[divine.exe 연동]` | 언팩/리팩 옵션 변경 (PAK 모드만) |

---

## 자주 묻는 질문

**Q. "429 제한" 메시지가 자주 뜹니다**
Gemini 무료 플랜의 분당 요청 한도입니다. 스크립트가 자동으로 대기 후 재시도하므로 기다리면 됩니다.

**Q. 번역 후에도 일부 영어가 남아있습니다**
`translation_errors.txt`에서 실패한 파일을 확인하고 재번역하세요.

**Q. 영어가 아닌 다른 언어 모드도 되나요?**
됩니다. 어떤 언어든 한국어로 번역합니다.

**Q. 캐시를 초기화하고 싶어요**
`translation_cache.json` 파일을 삭제하면 됩니다.

**Q. 재번역하고 싶어요**
- PAK 모드: `_Korean.pak` 파일을 삭제하고 다시 실행
- 폴더 모드: `Korean` 폴더를 삭제하고 다시 실행

**Q. Divine.exe 실행 시 오류가 나요**
.NET 8.0 런타임이 설치되어 있는지 확인하세요.

---

## 업데이트 이력

### v2.2 (2025.03)
- **`.loca` 바이너리 형식 지원**: 일부 모드가 사용하는 `.loca` 바이너리 파일을 자동으로 XML 변환 후 번역 (PAK 모드)
- 폴더 모드에서 `.loca` 파일 감지 시 해결 방법 안내 메시지 추가
- XML 파일 미발견 시 진단 메시지 추가 (디버깅 용이)

### v2.1 (2025.03)
- **번역 검수 도구 추가** (`BG3_AutoKorean_Reviewer_v2.2.py`): 영어/한국어 비교 검수 및 수정 기능
  - 드래그 앤 드롭으로 .pak 파일 바로 검수 가능
  - 폴더 경로 입력 시 .pak 목록에서 선택 가능
- 파일명 변경: 버전과 모드를 파일명에 명시하여 구분 용이
- 단어형 텍스트(주문 이름 등) 번역 스킵 버그 수정
- 코드 주석 대폭 보강 (수정 가이드 역할)

### v2.0 (2025.03)
- PAK 직접 모드 추가 (divine.exe 기반 전자동 처리)
- 번역 캐시, 경량 API 포맷, 용어집 350개+ 확장
- 로컬 선처리, 중복 제거 등 성능 개선

### v1.0
- 최초 배포

---

## 주의사항

- 번역 결과는 AI가 생성한 것이므로 오역이 포함될 수 있습니다
- 모드 원본 파일은 절대 수정되지 않습니다
- API 키를 인터넷에 업로드하지 마세요
- **`translation_cache.json` 파일을 지우지 마세요** — 스크립트를 처음 실행하면 같은 폴더에 이 파일이 자동 생성됩니다. 이전에 번역했던 텍스트를 기억해두는 파일이라서, 이게 있으면 같은 텍스트를 다시 API로 보내지 않아 **번역 속도가 빨라지고 API 사용량도 절약**됩니다. 삭제하면 다음 실행 시 모든 텍스트를 처음부터 다시 번역하게 됩니다.
