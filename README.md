# BG3 모드 자동 한글화 스크립트

발더스 게이트 3(Baldur's Gate 3) 모드의 텍스트를  
Google Gemini AI를 이용하여 자동으로 한국어로 번역해주는 스크립트입니다.

---

## 📋 전체 작업 흐름

```
모드 다운로드(.zip)
    → 압축 해제 → .pak 파일 획득
        → BG3 Modder's Multitool로 .pak 언팩
            → BG3_AutoKorean.py 실행 (한글화)
                → BG3 Modder's Multitool로 .pak 재압축
                    → 모드 매니저로 설치
```

---

## 🛠️ 사전 준비: 필요한 프로그램

### 1. Python (스크립트 실행용)
- [https://www.python.org/downloads/](https://www.python.org/downloads/) 에서 다운로드
- 설치 시 **"Add Python to PATH"** 옵션을 반드시 체크

### 2. BG3 Modder's Multitool (pak 파일 압축/해제용)
- [https://github.com/ShinyHobo/BG3-Modders-Multitool](https://github.com/ShinyHobo/BG3-Modders-Multitool) 에서 다운로드
- Releases 탭에서 최신 버전 다운로드 후 압축 해제

### 3. Gemini API 키 (번역 엔진용, 무료 발급)
- [https://aistudio.google.com](https://aistudio.google.com) 접속
- Google 계정으로 로그인
- 왼쪽 메뉴에서 **"Get API key"** 클릭
- **"Create API key"** 버튼 클릭
- 생성된 키(`AIzaSy...`로 시작)를 복사해 둡니다

> ⚠️ API 키는 타인에게 공유하지 마세요. 무단 사용 시 본인 계정에 요금이 부과될 수 있습니다.

---

## 📖 상세 작업 절차

### 1단계: 모드 파일 준비

1. 한글화할 모드를 다운로드합니다 (보통 `.zip` 형태로 배포)
2. 압축을 해제하면 `.pak` 확장자 파일이 나옵니다

```
다운로드한 파일 예시:
  SomeMod_v1.0.zip
    └── SomeMod.pak   ← 이 파일을 다음 단계에서 사용
```

---

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

---

### 3단계: BG3_AutoKorean.py 설정 및 실행

#### API 키와 경로 설정

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
> 탐색기에서 해당 폴더의 주소창을 클릭하면 전체 경로가 표시됩니다.

설정을 비워두면 실행 시 직접 입력하는 창이 나타납니다.

#### 실행

- `BG3_AutoKorean.py`를 **더블클릭**
- 또는 터미널에서: `python BG3_AutoKorean.py`

설정 확인 화면에서 내용을 확인하고 **엔터**를 누르면 번역이 시작됩니다.

#### 번역 완료 후 결과

번역이 완료되면 `Localization` 폴더 안에 `Korean` 폴더가 자동 생성됩니다.

```
SomeMod/
└── Localization/
    ├── English/          ← 원본 (변경 없음)
    │   └── SomeMod.xml
    └── Korean/           ← 번역 결과 (자동 생성)
        └── SomeMod.xml
```

---

### 4단계: BG3 Modder's Multitool로 pak 재압축

1. **BG3 Modder's Multitool**을 실행합니다
2. 번역이 완료된 모드 폴더(`Korean` 폴더가 생긴 상태)를 다시 불러옵니다
3. **"Pack"** 기능으로 재압축하면 `.zip` 파일이 생성됩니다

> 💡 이 `.zip` 파일은 **Vortex**, **BG3 Mod Manager** 등  
> 모드 매니저에서 바로 설치 가능한 형태입니다.

---

### 5단계: 모드 매니저로 설치

생성된 `.zip` 파일을 모드 매니저(Vortex 또는 BG3 Mod Manager)로 설치합니다.

---

## 📝 번역 실패 로그

번역 중 일부 구간이 실패하면 스크립트와 같은 폴더에  
`translation_errors.txt` 파일이 생성됩니다.

```
SomeMod.xml | 청크 2/5 | 상태: 429 wait 40s (gemini-2.5-flash)
```

로그에 기록된 파일을 재번역하려면 해당 모드의 `Korean` 폴더를 삭제 후  
스크립트를 다시 실행하면 됩니다.

---

## ❓ 자주 묻는 질문

**Q. Korean 폴더가 이미 있는 모드는 건너뜁니다**  
재번역하려면 해당 모드의 `Korean` 폴더를 삭제 후 재실행하세요.

**Q. "429 제한" 메시지가 자주 뜨는 경우**  
Gemini 무료 플랜의 분당 요청 한도에 도달한 것입니다.  
스크립트가 자동으로 대기 후 재시도하므로 그냥 기다리면 됩니다.

**Q. 번역 후에도 일부 영어가 남아있는 경우**  
`translation_errors.txt`에서 어느 파일이 실패했는지 확인 후  
해당 모드의 `Korean` 폴더를 삭제하고 재실행하면 됩니다.

**Q. pak 파일이 여러 개인 경우**  
pak 파일마다 개별적으로 언팩 → 번역 → 재압축을 반복하면 됩니다.

**Q. 영어가 아닌 다른 언어(포르투갈어 등)로 된 모드도 되나요?**  
됩니다. 스크립트가 원본 언어에 관계없이 한국어로 번역합니다.

---

## ⚠️ 주의사항

- 번역 결과는 AI가 생성한 것으로 오역이 포함될 수 있습니다
- 모드 원본 파일은 수정되지 않으며 `Korean` 폴더에만 결과가 저장됩니다
- API 키를 타인과 공유하거나 인터넷에 업로드하지 마세요
- BG3 Modder's Multitool의 자세한 사용법은 해당 프로그램의 공식 페이지를 참고하세요  
  → [https://github.com/ShinyHobo/BG3-Modders-Multitool](https://github.com/ShinyHobo/BG3-Modders-Multitool)
