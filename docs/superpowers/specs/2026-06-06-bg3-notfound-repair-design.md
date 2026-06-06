# BG3 한글화 모드 "Not Found" 일괄 수리 도구 — 설계 문서

- 작성일: 2026-06-06
- 상태: 승인됨 (구현 계획 대기)
- 대상 저장소: BG3-Auto-Korean

## 1. 배경 / 문제

게임 내에서 일부 한글화 모드의 아이템 이름·클래스 이름 등이 **"Not Found"** 로 표시된다.

BG3에서 이름은 stat(`.txt`)·루트템플릿(`.lsx`)에 텍스트가 아니라 **핸들(`contentuid` + version)** 참조로 저장되고, 게임은 로드된 Localization(`.xml`/`.loca`)을 핸들→텍스트로 조회한다. 조회 결과는 둘로 갈린다.

- **영문 표시(fallback)**: 핸들 항목이 있으나 한글이 아니라 영어임
- **"Not Found"**: 핸들에 대응하는 항목이 *유효한 형태로 어디에도 없음*

즉 "Not Found" = 핸들과 번역 항목 연결이 끊긴 상태다. 이 도구가 단독 `_Korean.pak`만 켜게 만들기 때문에, 항목이 빠지면 영어로 메꿔줄 원본조차 없어 곧장 "Not Found"가 뜬다.

### 근본 원인 분류

1. **원인 1 — XML 깨짐 (지배적)**: 과거 버전(v3.6 이전)이 만든 결과에서 AI가 raw `<`, `>`, `&`(예: `<내성 굴림>`, `[3] & [4]`)를 `<content>` inner에 넣어 XML이 깨졌고, 파일 파싱 실패로 그 안 핸들이 통째로 등록 실패.
2. **원인 2 — strip 빈틈**: 변환 실패한 `.loca`가 XML 대체본 없이 삭제되어 항목 소실(소수).
3. **원인 3 — 항목 부재**: 핸들 정의 자체가 산출물에 없음(소수).

### 핵심 관찰 (수리 가능성의 근거)

`bg3core/pipeline.py`의 `translate_unpacked_mod`은 **English 폴더를 수정하지 않고** `Korean` 폴더만 새로 만들어 번역 결과를 쓴다([pipeline.py:92-146]). 따라서 산출 `_Korean.pak` 안에는 보통 `Localization/English/*.xml`(원본)과 `Localization/Korean/*.xml`(번역)이 **공존**한다 → **수리 원천이 pak 내부에 이미 존재 → 재다운로드 불필요.**

## 2. 목표 / 비목표

### 목표
- 사용자가 한글화한 모드들을 폴더에서 자동 식별하고, "Not Found"를 유발하는 깨진/누락 핸들을 **오프라인으로** 수리한다.
- 수리 후 worst case는 영어 표시이며, **"Not Found"는 구조적으로 발생 불가능**하게 만든다.
- 게임 설치 폴더의 pak을 안전하게(백업 후) 제자리 교체한다.

### 비목표
- AI 재번역(이번 도구 범위 외 — 오프라인 복구만). 빈 핸들은 영어 backfill로 처리.
- MCM 블루프린트/Lua 텍스트 수리(별도 영역). 이 도구는 Localization 핸들 수리에 집중.
- `.pak` 포맷 직접 파싱(divine 재사용).

## 3. 사용자 결정 사항 (확정)

| 항목 | 결정 |
|------|------|
| 대상 식별 | **내용 기반 자동 감지** — 날짜로 후보를 추린 뒤 `Localization/.../Korean` 폴더가 실제 있는 pak만 |
| 출력 방식 | **백업 후 제자리 교체** — 원본을 별도 백업 폴더에 복사 후 수리본으로 덮어씀 |
| 복구 전략 | **오프라인만** — escape 재적용 + English backfill (API 미사용) |
| 폼팩터 | **독립 CLI 스크립트** — `bg3core` 재사용 |

## 4. 아키텍처 / 컴포넌트

### 4.1 신규 파일
- `bg3core/repair.py` — 순수 로직(파일/divine 비의존). 단위 테스트 1차 대상.
- `bg3_repair_notfound.py` — CLI 오케스트레이션 진입점.
- `tests/test_repair.py` — 순수 로직 단위 테스트.

### 4.2 `bg3core/divine.py` 추가
- `list_package(divine_path, pak_path) -> List[str]`: `divine -a list-package`로 전체 추출 없이 내부 엔트리 경로 목록만 반환. Korean 폴더 유무 판정에 사용.

### 4.3 재사용 (수정 없음)
- `bg3core/divine.py`: `divine_extract`, `convert_loca_to_xml`, `strip_loca_artifacts`, `divine_repack`
- `bg3core/constants.py`: `CONTENT_BLOCK_RE`, `CONTENT_INNER_RE`, `CONTENTUID_RE`
- `bg3core/translate.py`: `escape_unescaped_angle_brackets` (원인 1의 근본 수정 함수)
- `bg3core/pipeline.py`: `find_localization_folders`, `list_source_language_dirs`, `has_korean_folder`

## 5. 핵심 로직 — `bg3core/repair.py`

### 5.1 `parse_content_blocks(text) -> Dict[str, str]`
`CONTENT_BLOCK_RE`로 모든 `<content>` 블록(self-closing 포함)을 찾고, 각 블록에서 `CONTENTUID_RE`로 contentuid를 추출해 `{contentuid: full_block}` 매핑 반환. contentuid 없는 블록은 무시.

### 5.2 `repair_xml_text(korean_text, english_text) -> RepairResult`
입력은 문자열, 출력은 문자열 — **순수 함수**(divine/파일 비의존).

1. **재escape**: `CONTENT_INNER_RE`로 각 `<content>`의 inner를 찾아 `escape_unescaped_angle_brackets` 적용. open/close 태그와 contentuid 속성은 보존, inner만 변환.
2. **검증**: 결과를 `xml.etree.ElementTree`로 파싱.
   - 파싱 성공 → 진행.
   - 파싱 실패 → 더 나쁜 결과를 쓰지 않기 위해 재escape 결과는 보류하고, 파싱 실패를 `unfixable`로 기록(원본 유지).
3. **backfill (2번 검증 통과 시에만)**: English에 있고 Korean에 없는 핸들 → English의 `<content>` 블록을 **버전 속성까지 그대로** Korean 텍스트 끝(루트 닫기 태그 직전)에 삽입. (버전 매칭 보존, worst case 영어 표시) 검증 실패 파일은 backfill도 생략하고 `unfixable`로 둔다.
   - English 블록 자체가 깨졌거나 inner가 한글(MCM 미러로 영어 폴더가 덮인 경우)이면 backfill 불가 → 해당 핸들을 `unfixable`로 기록.
4. **반환**: `RepairResult(new_text, changed: bool, reescaped: int, backfilled: int, unfixable: List[(file, contentuid|reason)])`.

`changed`는 `new_text != korean_text`일 때만 True → **멱등성** 보장(재실행 시 2회차는 변경 없음).

### 5.3 한글 판정 / English-깨짐 판정
- backfill 원천 유효성: English inner에 한글 음절(가–힣)이 임계 이상 포함되면 "미러로 덮임"으로 보고 backfill 제외(파이프라인 `is_already_korean` 휴리스틱 재사용 가능).

## 6. 데이터 흐름 — CLI (`bg3_repair_notfound.py`)

```
Mods 폴더
  → ① 날짜 필터: mtime >= --since (기본 2026-03-01). --all 이면 생략.
  → ② 내용 감지: 각 후보에 list_package → 'Localization/.../Korean/' 엔트리 있는 pak만 채택.
  → ③ pak마다 ("대상 pak" = 지금 수리 중인 그 번역본 .pak 자체):
        divine_extract(temp)
        → convert_loca_to_xml(temp)            # 전부 .xml로 정규화
        → Localization 폴더별로 Korean dir ↔ source(English 우선) dir 짝짓기
        → 파일별(스템 매칭) repair_xml_text(korean, english)
        → 변경 있음?
             ├ 예 & not dry-run:
             │     대상 pak을 backup-dir에 복사(이미 있으면 보존)
             │     → strip_loca_artifacts(temp)
             │     → divine_repack(temp → 임시 출력) → 성공 시 대상 pak 경로로 교체
             ├ 예 & dry-run: "수리 예정"으로만 기록
             └ 아니오: 건드리지 않음(clean)
        temp 정리
  → ④ 리포트 작성: repair_report_<날짜>.json + .md
```

### 6.1 파일 짝짓기 규칙
- `list_source_language_dirs(loc_path)`로 source 디렉터리 선택(English 우선).
- Korean 파일 `X.xml`(또는 `X.loca.xml`)에 대해 source 디렉터리에서 동일 베이스 스템 파일을 English로 매칭. 없으면 backfill 원천 없음 → reescape만.

### 6.2 CLI 인자
| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--mods PATH` | (필수) | Mods 폴더 |
| `--divine PATH` | 설정값/필수 | Divine.exe 경로 |
| `--since YYYY-MM-DD` | `2026-03-01` | 날짜 후보 필터 |
| `--all` | off | 날짜 필터 무시(전체 661개 후보) |
| `--dry-run` | off | 쓰기 없이 리포트만 |
| `--backup-dir PATH` | `<Mods 상위>/Mods_backup_<날짜>` | 원본 백업 위치 |
| `--report PATH` | `./repair_report_<날짜>.json` | 리포트 출력(.md 동시 생성) |
| `--work-dir PATH` | 임시폴더 | 추출 임시 공간 |

### 6.3 리포트 스키마(JSON)
```
{
  "generated": "2026-06-06",
  "dry_run": true,
  "summary": {"candidates": N, "translated": N, "repaired": N, "clean": N, "failed": N, "unfixable_paks": N},
  "paks": [
    {"name": "...", "status": "repaired|would-repair|clean|failed|skipped",
     "reescaped": 12, "backfilled": 3,
     "unfixable": [{"file": "...", "contentuid": "h..."}],
     "note": "..."}
  ]
}
```

## 7. 엣지케이스

1. **재escape 후에도 파싱 실패** (깨진 contentuid 속성, inner 내 리터럴 `</content>` 등) → 원본 보존, 해당 파일/핸들 `unfixable` 기록.
2. **MCM 미러**: English 폴더가 한글로 덮인 모드 → backfill 원천 깨짐 감지 → `unfixable`("재다운로드 필요") 기록, 크래시 없음.
3. **플랫 Localization**(언어 서브폴더 없음, Tooltip Manager류) → English 원천 없음 → reescape만 수행.
4. **빈 self-closing 핸들** `<content .../>` → inner 없음, 무시.
5. **멱등성**: 두 번 실행 시 2회차는 `changed=False`.
6. **백업 보호**: backup-dir에 동명 파일이 이미 있으면 덮어쓰지 않음(최초 원본 보존).
7. **Korean이 `.loca` 바이너리**(구버전 산출물) → `convert_loca_to_xml`로 정규화; 변환 실패 시 스킵 + 기록.
8. **`_Korean` 미포함 이름**(`_Korean_Reviewed`, 리네임 등) → 내용 감지라 이름 무관하게 처리.

## 8. 에러 처리 / 안전

- **pak 단위 격리**: try/except로 한 pak 실패가 배치를 멈추지 않음. 로그 + 리포트.
- divine 추출/list/패킹 실패 → 원본 그대로 두고 스킵 + 기록.
- **백업 성공 + 재패킹 성공 이전엔 원본을 절대 삭제/교체하지 않음.** (재패킹은 임시 출력 → 성공 시 원본 경로로 이동/교체)
- pak별 temp 폴더 항상 정리(finally).
- `--dry-run`은 어떤 쓰기도 하지 않음.

## 9. 테스트 — `tests/test_repair.py`

순수 `repair_xml_text` / `parse_content_blocks` 중심(합성 XML 픽스처):

1. raw `<`, `>`, `&`가 inner에 있는 깨진 Korean → 재escape 후 파싱 성공, valid XML.
2. English엔 있고 Korean엔 없는 핸들 → backfill됨(버전 속성 보존 확인).
3. valid entity(`&amp;`, `&lt;`)·`&lt;LSTag.../&gt;`·`&lt;br&gt;` 보존.
4. self-closing `<content .../>` 무시.
5. 멱등성: 동일 입력 2회 → 2회차 `changed=False`.
6. 재escape 후에도 파싱 실패하는 입력 → 원본 유지 + `unfixable` 기록.
7. English inner가 한글(미러) → backfill 제외 + `unfixable` 기록.
8. 변경 없는 정상 Korean → `changed=False`.

divine 오케스트레이션은 얇게 유지하고 수동 검증(소수 실제 pak으로 `--dry-run`). 순수 코어는 전수 단위 테스트.

## 10. 구현 순서(요약)

1. `repair.py` 순수 로직 + `tests/test_repair.py` (TDD).
2. `divine.list_package` 래퍼.
3. `bg3_repair_notfound.py` CLI 오케스트레이션.
4. 실제 Mods 폴더에서 `--dry-run`으로 리포트 검증 → 소수 실수리 → 전체 적용.
