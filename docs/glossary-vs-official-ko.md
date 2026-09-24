# 기본 용어집 vs 게임 공식 한국어 표기 대조

게임 설치본의 공식 언어팩(English.pak + Korean.pak·KoreanData.pak)을 contentuid로 조인해 만든 사전과 기본 용어집(`bg3core/glossary.py`의 `GLOSSARY`)을 비교한 결과입니다. 2026-09-24 생성.

- 기본 용어집 347개 중 공식 사전에 같은 영어 문자열이 있는 항목: 295개
- 그중 표기가 다른 항목: 75개 (Bonus Action·Bonus Actions는 v7.2에서 공식 표기로 수정 완료)

공식 사전은 **문자열 단위 정확 일치**라 UI 라벨 등 다른 문맥의 번역이 걸릴 수 있습니다. "검토 필요" 표시는 문맥상 공식 값이 용어로 부적절해 보이는 항목입니다. 일괄 교체하지 말고 항목별로 확인하세요.

| 영어 | 기본 용어집 | 공식 표기 | 비고 |
|---|---|---|---|
| Chosen | 선택받은 자 | 선택한 주문 | 검토 필요 |
| Cazador | 카자도르 | 카사도어 |  |
| Dame Aylin | 에일린 경 | 고귀한 에일린 |  |
| Myrkul | 미어쿨 | 머쿨 |  |
| Lolth | 롤쓰 | 롤스 |  |
| Flaming Fist | 불주먹 용병대 | 불주먹 | 검토 필요 |
| Astral Plane | 아스트랄계 | 영계 | 검토 필요 |
| Lolth-Sworn Drow | 롤쓰 스원 드로우 | 롤스 스원 드로우 |  |
| Rock Gnome | 바위 노움 | 락 노움 |  |
| Forest Gnome | 숲 노움 | 포레스트 노움 |  |
| High Half-Elf | 하이 하프 엘프 | 하이 하프엘프 |  |
| Wood Half-Elf | 우드 하프 엘프 | 우드 하프엘프 |  |
| Drow Half-Elf | 드로우 하프 엘프 | 드로우 하프엘프 |  |
| Wildheart | 야생의심장 | 야생의 심장 |  |
| Oathbreaker | 맹세파기자 | 맹세 파기자 |  |
| Gloom Stalker | 어둠 추척자 | 어둠 추적자 |  |
| Draconic Bloodline | 용의 혈통 | 드래곤 혈통 |  |
| Storm Sorcery | 폭풍 술사 | 폭풍 마법 |  |
| School of Abjuration | 방호술 | 방호학파 |  |
| Abjuration School | 방호술 | 방호학파 |  |
| School of Evocation | 방출술 | 방출학파 |  |
| Evocation School | 방출술 | 방출학파 |  |
| School of Necromancy | 사령술 | 사령학파 |  |
| School of Conjuration | 창조술 | 창조학파 |  |
| School of Enchantment | 환혹술 | 환혹학파 |  |
| School of Divination | 예지술 | 예지학파 |  |
| School of Illusion | 환영술 | 환영학파 |  |
| School of Transmutation | 변환술 | 변환학파 |  |
| Invisibility | 투명화 | 투명 | 검토 필요 |
| Greater Invisibility | 상위 투명화 | 상급 투명 |  |
| Cure Wounds | 상처 치유 | 상처 치료 |  |
| Shield of Faith | 신념의 보호막 | 신앙의 방패 |  |
| Spirit Guardians | 영혼의 수호자 | 영혼 수호자 |  |
| Eldritch Blast | 섬뜩한 작렬 | 섬뜩한 파동 |  |
| Magic Missile | 마법의 화살 | 마력탄 |  |
| Sacred Flame | 신성한 불꽃 | 신성한 불길 |  |
| Daylight | 일광 | 햇빛 |  |
| Dispel Magic | 마법 해제 | 마법 무효화 |  |
| Hold Person | 인물 속박 | 인간형 포박 |  |
| Hold Monster | 괴물 속박 | 괴물 포박 |  |
| Knock | 개방 | 노크 | 검토 필요 |
| Pass Without Trace | 흔적 없는 이동 | 신출귀몰 |  |
| Divine Smite | 신성 강타 | 신성한 강타 |  |
| Sneak Attack | 급소 공격 | 암습 |  |
| Wild Shape | 야생 변신 | 야생 형상 |  |
| Action Surge | 행동 쇄도 | 행동 폭증 |  |
| Second Wind | 재기 | 재기의 바람 |  |
| Lay on Hands | 레이온핸즈 | 치유의 손길 |  |
| Bardic Inspiration | 바드의 영감 | 바드의 격려 |  |
| Channel Divinity | 신성한 도관 | 신성한 권능 |  |
| Attack Roll | 공격 굴림 | 명중 굴림 |  |
| Hit Points | 체력 | 생명력 |  |
| Hit Dice | 생명력 주사위 | 생명 주사위 |  |
| Advantage | 유리 | 유리 보정 | 검토 필요 |
| Disadvantage | 불리 | 불리 보정 | 검토 필요 |
| Reaction | 반응 | 대응 |  |
| Reactions | 반응 | 대응 |  |
| Multiclassing | 멀티 클래싱 | 다중 직업 |  |
| Background | 배경 | 출신 |  |
| Prone | 쓰러짐 | 넘어짐 |  |
| Frightened | 공포 | 겁에 질림 |  |
| Restrained | 속박 | 구속 |  |
| Incapacitated | 행동불능 | 행동 불능 |  |
| Burning | 불타는 | 발화 | 검토 필요 |
| Cursed | 저주받은 | 저주받음 | 검토 필요 |
| Entangled | 얽힘 | 휘감김 |  |
| Necrotic Damage | 괴저 피해 | 사령 피해 |  |
| Acid Damage | 산 피해 | 산성 피해 |  |
| Temporary Hit Points | 임시 체력 | 임시 생명력 |  |
| Necrotic | 괴저 | 사령 |  |
| Arcana | 비전학 | 비전 | 검토 필요 |
| Intimidation | 위협 | 협박 |  |
| Investigation | 수사 | 조사 |  |
| Perception | 인지 | 포착 |  |
| Superior Darkvision | 상위 암시야 | 우수한 암시야 |  |
