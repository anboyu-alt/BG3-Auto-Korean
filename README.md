# BG3 모드 자동 한글화 스크립트

발더스 게이트 3(Baldur's Gate 3) 모드의 텍스트를
Google Gemini AI를 이용하여 자동으로 한국어로 번역해주는 스크립트입니다.

---

## 🆕 업데이트 이력

### v2.1 / v3.1 (2025.03)

단어형 텍스트(주문 이름 등)가 번역되지 않고 영어로 남던 버그를 수정했습니다.

- **번역 스킵 패턴 수정**: `Fireball`, `Bless` 등 일반 영단어가 코드성 상수(`STRENGTH`, `DEX_MOD`)와 함께 번역에서 제외되던 문제 해결
- 두 버전 모두 동일하게 적용

### v2.0 / v3.0 (2025.03)

v3.0에서 **pak 직접 처리 버전**(`BG3_AutoKorean_Pak.py`)이 추가되었습니다.
기존 폴더 모드(`BG3_AutoKorean.py`)도 그대로 사용 가능합니다.

- **pak 직접 모드 추가**: `.pak` 파일을 넣으면 언팩 → 번역 → 리팩까지 전자동 처리
- **다중 pak 일괄 처리**: 폴더를 지정하면 안에 있는 모든 `.pak` 파일을 한번에 번역
- **BG3 Modder's Multitool 불필요** (pak 모드 사용 시): LSLib의 `divine.exe`로 대체
- **번역 캐시**: JSON 캐시 파일로 이미 번역한 텍스트 재사용
- **경량 API 포맷**: 텍스트만 추출하여 토큰 절감
- **용어집 확장**: 350개+ (종족, 능력치, 상태이상, 피해유형, 기술 등)
- **로컬 선처리**: 숫자/코드/용어집 매칭은 API 없이 즉시 처리
- **중복 제거**: 동일 텍스트 자동 제거 후 한 번만 번역

### 버전 대응표

| 폴더 모드 (`BG3_AutoKorean.py`) | pak 모드 (`BG3_AutoKorean_Pak.py`) | 내용 |
|------|------|------|
| v2.1 | v3.1 | 단어형 텍스트 번역 스킵 버그 수정 |
| v2.0 | v3.0 | 번역 엔진 개선 + pak 직접 모드 추가 |
| v1.0 | — | 최초 배포 |

---

## 📊 두 버전 비교

| 항목 | `BG3_AutoKorean.py` (폴더 모드) | `BG3_AutoKorean_Pak.py` (pak 직접 모드) |
|------|------|------|
| **작업 방식** | 이미 언팩된 폴더를 번역 | `.pak` 파일을 직접 처리 (언팩→번역→리팩 자동) |
| **필요 프로그램** | Python + BG3 Modder's Multitool | Python + LSLib(divine.exe) + .NET 8.0 |
| **작업 단계** | 5단계 (언팩 → 번역 → 리팩 → 설치) | 2단계 (스크립트 실행 → 설치) |
| **자동화 수준** | 번역만 자동, 언팩/리팩은 수동 | 전자동 (언팩부터 리팩까지) |
| **다중 pak 처리** | 불가 (하나씩 수동 처리) | 폴더 지정 시 일괄 처리 |
| **출력 결과** | `Korean` 폴더 생성 (리팩은 직접) | `원본이름_Korean.pak` 파일 자동 생성 |
| **권장 대상** | Multitool을 이미 사용 중인 분 | 신규 사용자 / 편의를 원하는 분 |
| **번역 엔진** | 동일 (v2.0 엔진) | 동일 (v2.0 엔진) |

> 💡 **어떤 버전을 선택해야 할까요?**
> - 처음 사용하시거나 간편한 방법을 원하시면 → **pak 직접 모드** (`BG3_AutoKorean_Pak.py`)
> - BG3 Modder's Multitool을 이미 설치하여 사용 중이시면 → **폴더 모드** (`BG3_AutoKorean.py`)

---

## 🛠️ 사전 준비

### 공통 필수

#### 1. Python (스크립트 실행용)
- [https://www.python.org/downloads/](https://www.python.org/downloads/) 에서 다운로드
- 설치 시 **"Add Python to PATH"** 옵션을 반드시 체크

#### 2. Gemini API 키 (번역 엔진용, 무료 발급)
- [https://aistudio.google.com](https://aistudio.google.com) 접속
- Google 계정으로 로그인
- 왼쪽 메뉴에서 **"Get API key"** 클릭
- **"Create API key"** 버튼 클릭
- 생성된 키(`AIzaSy...`로 시작)를 복사해 둡니다

> ⚠️ API 키는 타인에게 공유하지 마세요. 무단 사용 시 본인 계정에 요금이 부과될 수 있습니다.

---

### pak 직접 모드 전용 (`BG3_AutoKorean_Pak.py`)

#### 3-A. LSLib (ExportTool) 다운로드

1. [https://github.com/Norbyte/lslib/releases](https://github.com/Norbyte/lslib/releases) 접속
2. 최신 버전의 **`ExportTool-vX.X.X.zip`** 파일을 다운로드
3. 압축 해제
4. `Divine.exe` 위치 확인:

```
ExportTool-v1.20.4/
└── Packed/
    └── Tools/
        └── Divine.exe   ← 이 경로를 스크립트에 입력
```

#### 3-B. .NET 8.0 런타임 설치

`Divine.exe`를 실행하려면 .NET 8.0 런타임이 필요합니다.
이미 설치되어 있다면 이 단계를 건너뛰세요.

- [https://dotnet.microsoft.com/download/dotnet/8.0](https://dotnet.microsoft.com/download/dotnet/8.0) 접속
- **".NET Desktop Runtime"** 다운로드 후 설치

> 💡 .NET 8.0이 없는 상태에서 `Divine.exe`를 실행하면 설치 안내가 자동으로 뜹니다.

---

### 폴더 모드 전용 (`BG3_AutoKorean.py`)

#### 3. BG3 Modder's Multitool (pak 파일 압축/해제용)
- [https://github.com/ShinyHobo/BG3-Modders-Multitool](https://github.com/ShinyHobo/BG3-Modders-Multitool) 에서 다운로드
- Releases 탭에서 최신 버전 다운로드 후 압축 해제

---

## 📖 사용법 A: pak 직접 모드 (`BG3_AutoKorean_Pak.py`)

### 전체 작업 흐름

```
모드 다운로드(.zip)
    → 압축 해제 → .pak 파일 획득
        → BG3_AutoKorean_Pak.py 실행 (언팩 → 번역 → 리팩 전자동)
            → 생성된 _Korean.pak 파일을 모드 매니저로 설치
```

### 1단계: 모드 파일 준비

1. 한글화할 모드를 다운로드합니다 (보통 `.zip` 형태로 배포)
2. 압축을 해제하면 `.pak` 확장자 파일이 나옵니다

```
다운로드한 파일 예시:
  SomeMod_v1.0.zip
    └── SomeMod.pak   ← 이 파일의 경로를 기억해두세요
```

### 2단계: 설정 및 실행

`BG3_AutoKorean_Pak.py`를 메모장이나 텍스트 편집기로 열고
**[설정 구간]** 부분을 수정합니다.

```python
# ==========================================
# [설정 구간] ← 여기를 수정하세요
# ==========================================

API_KEY = "여기에 발급받은 API 키 붙여넣기"

DIVINE_EXE = r"C:\ExportTool-v1.20.4\Packed\Tools\Divine.exe"

TARGET_PAK = r"C:\Mods\SomeMod.pak"
# 폴더를 지정하면 안의 모든 .pak을 한번에 처리:
# TARGET_PAK = r"C:\Mods"
```

> 💡 경로 앞에 `r`을 붙이고 큰따옴표로 감싸야 `\`(역슬래시)가 올바르게 인식됩니다.

설정을 비워두면 실행 시 직접 입력하는 창이 나타납니다.

#### 실행

- `BG3_AutoKorean_Pak.py`를 **더블클릭**
- 또는 터미널에서: `python BG3_AutoKorean_Pak.py`

설정 확인 화면에서 내용을 확인하고 **엔터**를 누르면 번역이 시작됩니다.

### 3단계: 결과 확인 및 설치

번역이 완료되면 원본 `.pak`과 같은 폴더에 `_Korean.pak` 파일이 생성됩니다.

```
C:\Mods\
├── SomeMod.pak            ← 원본 (변경 없음)
└── SomeMod_Korean.pak     ← 한글화된 모드 (자동 생성)
```

생성된 `_Korean.pak` 파일을 모드 매니저(Vortex 또는 BG3 Mod Manager)로 설치합니다.

> 💡 **다중 pak 처리**: 폴더를 지정하면 안에 있는 모든 `.pak` 파일이 한번에 처리됩니다.
> 이미 `_Korean.pak`이 존재하는 파일은 자동으로 스킵합니다.

---

## 📖 사용법 B: 폴더 모드 (`BG3_AutoKorean.py`)

### 전체 작업 흐름

```
모드 다운로드(.zip)
    → 압축 해제 → .pak 파일 획득
        → BG3 Modder's Multitool로 .pak 언팩
            → BG3_AutoKorean.py 실행 (한글화)
                → BG3 Modder's Multitool로 .pak 재압축
                    → 모드 매니저로 설치
```

### 1단계: 모드 파일 준비

1. 한글화할 모드를 다운로드합니다 (보통 `.zip` 형태로 배포)
2. 압축을 해제하면 `.pak` 확장자 파일이 나옵니다

### 2단계: BG3 Modder's Multitool로 pak 파일 언팩

1. **BG3 Modder's Multitool**을 실행합니다
2. 상단 메뉴에서 **"Utilities"** 클릭
3. **"Unpack Game"** 또는 드래그 앤 드롭으로 `.pak` 파일을 불러옵니다
4. 언팩이 완료되면 같은 폴더 또는 지정한 폴더에 모드 폴더가 생성됩니다

```
언팩 결과 예시:
  bg3-modders-multitool/
  └── UnpackedMods/
      └── SomeMod/
          └── Localization/
              └── English/
                  └── SomeMod.xml   ← 번역 대상 파일
```

> 💡 언팩된 폴더의 경로를 기억해두세요. 다음 단계에서 입력해야 합니다.

### 3단계: BG3_AutoKorean.py 설정 및 실행

`BG3_AutoKorean.py`를 메모장이나 텍스트 편집기로 열고
**[설정 구간]** 부분을 수정합니다.

```python
# ==========================================
# [설정 구간] ← 여기를 수정하세요
# ==========================================

API_KEY = "여기에 발급받은 API 키 붙여넣기"

TARGET_ROOT_FOLDER = r"C:\경로\bg3-modders-multitool"
# 예시: r"C:\Users\홍길동\Downloads\bg3-modders-multitool"
```

> 💡 경로 앞에 `r`을 붙이고 큰따옴표로 감싸야 `\`(역슬래시)가 올바르게 인식됩니다.

설정을 비워두면 실행 시 직접 입력하는 창이 나타납니다.

#### 실행

- `BG3_AutoKorean.py`를 **더블클릭**
- 또는 터미널에서: `python BG3_AutoKorean.py`

설정 확인 화면에서 내용을 확인하고 **엔터**를 누르면 번역이 시작됩니다.

### 4단계: 번역 결과 확인

번역이 완료되면 `Localization` 폴더 안에 `Korean` 폴더가 자동 생성됩니다.

```
SomeMod/
└── Localization/
    ├── English/          ← 원본 (변경 없음)
    │   └── SomeMod.xml
    └── Korean/           ← 번역 결과 (자동 생성)
        └── SomeMod.xml
```

### 5단계: BG3 Modder's Multitool로 pak 재압축

1. **BG3 Modder's Multitool**을 실행합니다
2. 번역이 완료된 모드 폴더(`Korean` 폴더가 생긴 상태)를 다시 불러옵니다
3. **"Pack"** 기능으로 재압축하면 `.zip` 파일이 생성됩니다

> 💡 이 `.zip` 파일은 **Vortex**, **BG3 Mod Manager** 등
> 모드 매니저에서 바로 설치 가능한 형태입니다.

### 6단계: 모드 매니저로 설치

생성된 `.zip` 파일을 모드 매니저(Vortex 또는 BG3 Mod Manager)로 설치합니다.

---

## 📝 번역 실패 로그

번역 중 일부 구간이 실패하면 스크립트와 같은 폴더에
`translation_errors.txt` 파일이 생성됩니다.

```
SomeMod.xml | 청크 2/5 | 상태: 429 wait 40s (gemini-2.5-flash-lite)
```

---

## ❓ 자주 묻는 질문

### 공통

**Q. "429 제한" 메시지가 자주 뜨는 경우**
Gemini 무료 플랜의 분당 요청 한도에 도달한 것입니다.
스크립트가 자동으로 대기 후 재시도하므로 그냥 기다리면 됩니다.

**Q. 번역 후에도 일부 영어가 남아있는 경우**
`translation_errors.txt`에서 어느 파일이 실패했는지 확인하세요.
해당 모드를 재번역하면 됩니다. (아래 "재번역 방법" 참고)

**Q. 영어가 아닌 다른 언어(포르투갈어 등)로 된 모드도 되나요?**
됩니다. 스크립트가 원본 언어에 관계없이 한국어로 번역합니다.

**Q. 번역 캐시 파일은 어디에 있나요?**
스크립트와 같은 폴더에 `translation_cache.json`으로 자동 생성됩니다.
이전에 번역한 텍스트가 저장되어 있어, 재실행 시 동일한 텍스트는 API 호출 없이 바로 적용됩니다.

**Q. 캐시를 초기화하고 싶어요**
`translation_cache.json` 파일을 삭제하면 됩니다.
다음 실행부터 모든 텍스트를 새로 번역합니다.

### pak 직접 모드 (`BG3_AutoKorean_Pak.py`)

**Q. 이미 한글화한 모드를 재번역하고 싶어요**
기존에 생성된 `_Korean.pak` 파일을 삭제하고 스크립트를 다시 실행하세요.

**Q. pak 파일이 여러 개인 경우**
`TARGET_PAK`에 폴더 경로를 지정하면 안의 모든 `.pak` 파일이 한번에 처리됩니다.
이미 `_Korean.pak`이 존재하는 파일은 자동으로 건너뜁니다.

**Q. Divine.exe 실행 시 오류가 나는 경우**
.NET 8.0 런타임이 설치되어 있는지 확인하세요.
→ [https://dotnet.microsoft.com/download/dotnet/8.0](https://dotnet.microsoft.com/download/dotnet/8.0)
→ ".NET Desktop Runtime" 설치

**Q. 임시 파일은 어디에 생기나요?**
스크립트와 같은 폴더에 `_pak_temp/` 폴더가 생성되며, 각 pak 처리 완료 후 자동으로 정리됩니다.

### 폴더 모드 (`BG3_AutoKorean.py`)

**Q. 이미 한글화한 모드를 재번역하고 싶어요**
해당 모드의 `Korean` 폴더를 삭제한 후 스크립트를 다시 실행하세요.

**Q. pak 파일이 여러 개인 경우**
pak 파일마다 개별적으로 언팩 → 번역 → 재압축을 반복하면 됩니다.
여러 pak을 한번에 처리하고 싶다면 pak 직접 모드(`BG3_AutoKorean_Pak.py`)를 사용하세요.

---

## ⚠️ 주의사항

- 번역 결과는 AI가 생성한 것으로 오역이 포함될 수 있습니다
- 모드 원본 파일은 수정되지 않습니다
  - 폴더 모드: `Korean` 폴더에만 결과 저장
  - pak 모드: `_Korean.pak` 파일로 별도 생성
- API 키를 타인과 공유하거나 인터넷에 업로드하지 마세요
- BG3 Modder's Multitool 사용법: [https://github.com/ShinyHobo/BG3-Modders-Multitool](https://github.com/ShinyHobo/BG3-Modders-Multitool)
- LSLib (ExportTool) 사용법: [https://github.com/Norbyte/lslib](https://github.com/Norbyte/lslib)
