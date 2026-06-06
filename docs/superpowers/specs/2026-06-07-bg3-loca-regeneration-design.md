# BG3 `.loca` 재생성 — "Not Found" 회귀 수정 설계 문서

- 작성일: 2026-06-07
- 상태: 승인됨 (구현 계획 대기)
- 대상 저장소: BG3-Auto-Korean
- 선행: `2026-06-06-bg3-notfound-repair-design.md` (escape/backfill 수리 도구)

## 1. 배경 / 확정된 근본 원인

게임 내 다수 한글화 모드의 아이템·클래스 이름이 "Not Found"로 표시된다. 체계적 디버깅으로 근본 원인을 **확정**했다.

**근본 원인: 바이너리 `.loca` 누락.** BG3는 표준 구조 모드(`Localization/<Lang>/`)의 로컬라이제이션을 **`.loca` 바이너리에서 읽고, 느슨한 `.xml`로는 읽지 않는다.** 그런데 v3.7이 `.loca` 생성(`convert_xml_to_loca` 호출)을 제거하고 `strip_loca_artifacts`로 `.loca`를 삭제해 산출 pak을 **xml-only**로 만들었다 → 게임이 읽을 로컬라이제이션이 없어 **모든 핸들(이름·설명)이 Not Found**.

### 검증 (게임 실측)
- InvisibleItems, CombatBodysuit: Korean `.xml`에서 `.loca`를 재생성해 넣은 테스트 pak으로 교체 → 게임에서 **한글 정상 출력 확인**.
- 사용자 관찰: InvisibleItems의 4개 아이템 **전부**, 이름·설명 **모두** Not Found였음 → 핸들 단위 문제(버전 불일치 등)가 아니라 파일 전체 미로딩임을 입증.

### 규모
- 번역본 표본 25개 중 **25개 전부 바이너리 `.loca` 없음**. v3.7은 만드는 모든 pak에서 `.loca`를 제거하므로, 사용자의 번역본 ~219개가 **사실상 전부** 동일 원인으로 깨져 있다.

### 헛다리(디버깅으로 배제)
- InvisibleItems "버전 불일치(ref v2/def v1)", CombatBodysuit "raw-UUID 핸들 형식·빈 contentuid" — 모두 원인 아님. 4개 전부·이름설명 전부 깨진 사실과 `.loca` 추가로 해결된 사실이 이를 배제.

### v3.7의 masking 전제 반증
v3.7은 "원본 영문 `.loca.xml`이 한글 `.xml`을 가린다"는 이유로 `.loca`를 제거했다. 그러나 CombatBodysuit 테스트 pak은 **English `.loca` + Korean `.loca`가 둘 다** 들어있었는데도 게임에서 **한글이 정상 출력**됐다. 즉 언어별 `.loca`를 제대로 생성하면 masking은 발생하지 않는다. v3.7은 오진이었고, 올바른 해법은 애초에 "Korean `.loca` 생성"이었다.

## 2. 목표 / 비목표

### 목표
- **기존 모드 일괄 복구**: `.loca` 없는 모든 번역본에 `.loca`를 재생성해 재패킹(재번역·재다운로드 없이). 사용자 결정: **전체 일괄 스윕**.
- **본 파이프라인 수정**: 앞으로의 번역이 `.loca`를 포함하도록 v3.7 회귀를 되돌림.
- **언어 범위**: 존재하는 **모든 언어 폴더**의 xml에서 각 언어 `.loca` 생성(사용자 결정).
- **멱등성**: 이미 `.loca`가 있는 폴더는 건드리지 않음 → 재실행 시 불필요한 재패킹 없음.

### 비목표
- escape/backfill 수리 로직 변경(기존 `repair_xml_text` 유지). `.loca` 생성은 그 뒤 단계로 추가.
- `.loca.xml` 중간 산출물 적극 정리(게임이 무시하므로 무해 — 그대로 둠).
- AI 재번역.

## 3. 접근법 결정

| 안 | 내용 | 채택 |
|----|------|------|
| A | 멱등 `ensure_loca` + 순수 `plan_loca_generation`, strip→generate 교체 | **채택** |
| B | 옛 `convert_xml_to_loca` 호출만 부활(비멱등, 전부 재생성) | 기각 |
| C | 본 파이프라인만 고치고 재번역 유도(원본 삭제됨이라 불가) | 기각 |

## 4. 아키텍처 / 컴포넌트

### 4.1 `bg3core/divine.py` 추가

```
def plan_loca_generation(localization_root: Path) -> list[tuple[Path, Path]]
```
순수 함수(divine 비호출). `localization_root` 하위에서 경로에 `Localization` 컴포넌트가 있는 모든 `*.xml`을 보고, 생성할 `(src_xml, out_loca)` 목록을 반환.
- 출력 `.loca` 경로 규칙:
  - `X.loca.xml` → `X.loca`
  - `X.xml` → `X.loca` (예: `__MT_GEN_LOCA_abc.xml` → `__MT_GEN_LOCA_abc.loca`)
- **dedup**: 같은 `out_loca`가 둘 이상이면 한 번만. `X.xml`과 `X.loca.xml`이 공존하면 **`X.xml`(정식 소스)** 을 src로 선택.
- **멱등**: `out_loca`가 이미 디스크에 존재하면 목록에서 제외.

```
def ensure_loca(divine_path: str, unpacked_path: Path) -> int
```
`plan_loca_generation` 결과를 순회하며 `convert-loca -s src -d out`으로 `.loca` 생성. 성공 개수 반환. 실패는 stderr 일부를 로그(기존 `convert_xml_to_loca` 패턴 따름).

> 기존 `convert_xml_to_loca`(v3.7이 호출만 제거, 함수는 잔존, 현재 어디서도 import 안 됨)는 비멱등(전부 재생성)이라 사용하지 않는다. **결정: `convert_xml_to_loca`는 건드리지 않고(레거시 미사용 함수로 잔존) 신규 `ensure_loca`를 추가해 그것만 사용한다.** (제거 시 부수효과 위험 회피.)

### 4.2 수리 도구 `bg3_repair_notfound.py` (`process_pak`)
변경된 흐름:
```
extract → convert_loca_to_xml → (Korean xml별 repair_xml_text: escape/backfill)
        → ensure_loca(모든 언어, 누락분 .loca 생성)            # strip_loca_artifacts 호출 제거
        → changed = (xml 변경됨) or (loca_generated > 0)
            ├ 예 & not dry-run: 백업 → 재패킹(원자적 교체)
            ├ 예 & dry-run: "would-repair" 기록
            └ 아니오: clean
```
- `--dry-run`: 쓰기 없이 `len(plan_loca_generation(loc))`로 "생성 예정 .loca" 개수만 집계.
- 리포트 스키마에 `loca_generated`(실제) / dry-run 시 `loca_missing` 추가.
- `strip_loca_artifacts` 호출 제거(이제 `.loca`를 **남겨야** 함).

### 4.3 본 파이프라인 `bg3core/pipeline.py` (`process_pak_file`)
- 패킹 직전 `strip_loca_artifacts(temp_dir)` 호출 → `ensure_loca(divine_path, temp_dir)`로 **교체**. 로그: `🧩 .loca 생성: N개`.
- `.xml`은 소스로 유지, `.loca` 추가. 게임은 `.loca`를 읽음.

### 4.4 README / 버전
- v3.8 항목 추가: ".loca 재생성 복원(v3.7 회귀 수정). BG3는 표준 구조에서 .loca를 읽는다." 한글화 원리 섹션의 "v3.7 .loca 정리" 설명 정정.

## 5. 데이터 흐름 (운영)

```
[기존 모드 복구]
Mods 폴더 → 후보(date/all) → list_package로 번역본 감지
  → pak마다: 추출 → xml 수리(escape/backfill) → ensure_loca(누락 .loca 생성)
            → 변경분 백업 후 재패킹(제자리, os.replace)
  → 리포트(loca_generated 포함)

[앞으로의 번역]
process_pak_file: ... 번역 → ensure_loca(.loca 생성) → 재패킹
```

## 6. 엣지케이스

1. **`X.xml` + `X.loca.xml` 공존**(Artificer) → 출력 `X.loca` 한 번, src는 `X.xml`. dedup으로 중복 변환 방지.
2. **이미 `.loca` 존재**(구버전 v3.5 산출물) → 멱등 스킵, 재패킹 안 함.
3. **`--dry-run`** → 어떤 쓰기·재패킹·백업도 없음. 생성 예정 개수만 보고.
4. **대용량 pak**(예: 198MB) → 추출·재패킹 시간 큼. 전체 스윕은 1회성 장시간 작업. pak별 진행 로그.
5. **변환 실패**(divine 오류) → 해당 pak 실패로 기록, 원본 보존, 배치 계속.
6. **Localization 밖 `.xml`**(lsx 등) → `plan_loca_generation`이 `Localization` 컴포넌트 필터로 제외.
7. **언어 폴더 없는 평면 구조** → `Localization/Test.xml`(언어 서브폴더 없음)도 `Localization` 컴포넌트 필터에 걸리므로 `.loca`를 생성한다(무해, 게임 동작과 일치). 결정: 평면/서브폴더 구분 없이 Localization 하위 모든 xml을 대상으로 한다(별도 분기 없음).

## 7. 에러 처리 / 안전

- 기존 수리 도구의 안전 규칙 유지: pak 단위 try/except, 백업·재패킹 성공 전 원본 미교체(원자적 `os.replace`), temp 정리(finally).
- masking 회귀 방지: 언어별 `.loca`를 각 언어 xml에서 생성(검증됨). DBW류는 구현·검증 단계에서 watch-item으로 1개 실측 권장.

## 8. 테스트

`tests/test_loca.py` — 순수 `plan_loca_generation`(tmp_path 픽스처):
1. `.loca` 없는 `X.xml` → 대상에 포함, out=`X.loca`.
2. 이미 `X.loca` 존재 → 대상에서 제외(멱등).
3. `X.xml` + `X.loca.xml` 공존 → 대상 1개(out=`X.loca`), src=`X.xml`.
4. `Localization` 밖 `*.xml`(예: RootTemplates lsx 아님, 일반 xml) → 제외.
5. 다중 언어 폴더(English+Korean) 각각 대상 산출.
6. `__MT_GEN_LOCA_*.xml` 네이밍 → out 정확.

divine 호출부(`ensure_loca`)와 CLI/파이프라인 통합은 실제 1~2개 pak `--dry-run` + 1개 실수리 게임 확인으로 검증(외부 바이너리 의존이라 단위 테스트 대신 수동).

## 9. 구현 순서(요약)

1. `plan_loca_generation` 순수 함수 + `tests/test_loca.py` (TDD).
2. `ensure_loca` divine 래퍼.
3. 수리 도구 `process_pak`: strip 제거 + `ensure_loca` 통합 + 리포트 필드 + dry-run 카운트.
4. 본 파이프라인 `process_pak_file`: strip → `ensure_loca` 교체.
5. README v3.8 갱신.
6. 운영: `--dry-run`으로 누락 개수 확인 → 전체 일괄 스윕 → 게임 확인.
