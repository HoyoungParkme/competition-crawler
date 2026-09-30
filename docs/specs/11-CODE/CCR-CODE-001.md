---
doc_id: CCR-CODE-001
type: CODE
title: 구현 계획 — 대회 수집 배치
status: draft
upstream: [CCR-MS-001, CCR-SEQ-001, CCR-DOM-002, CCR-DOM-003, CCR-INFRA-001, CCR-SCN-001, CCR-UI-001, CCR-API-001]
---

# 구현 계획 — 대회 수집 배치

## 0. 이 문서가 다루는 것

배치와 대회 목록 페이지를 어떤 차례의 조각(슬라이스 · 카드)으로 만들었고 만들 것인지, 조각마다 무엇을 구현하고 무엇으로 확인하는지다. 함수의 처리는 [[CCR-MS-001]], 흐름은 [[CCR-SEQ-001]]에 있다. 조각은 도메인 경계를 따라 나눴다.

두 시기가 있다. **A ~ C**는 2026-09-24 ~ 09-28에 노션 `대회목록`에 넣는 배치로 만들어 병합한 것이다. 조각 하나가 커밋 하나였고 PR 둘로 합쳤다(3장). **D1 ~ D3**은 2026-09-29의 결정(노션 대신 우리 페이지)에 따라 새로 만드는 것이다. 카드마다 브랜치와 PR 하나, 함수 하나가 커밋 하나다(`code(D1): 함수 — 요약`, 싱크독 개발 규약 SYNC-STD-004 DEV-13 · DEV-15). 병합은 사용자가 웹에서 읽고 난 뒤에 한다.

**확인하는 법.** 배치는 `batch/`에서 `uv run pytest`(네트워크를 쓰지 않는다) · `uv run ruff check .` · `uv run ruff format --check .`. 실제 소스에 수집만 해 보려면 `uv run python -m collector collect --show`. 판별까지는 미리보기(`python -m collector`, 로컬은 늘 미리보기)로 본다. 페이지는 `frontend/`에서 `npm test`(vitest, 순수 모듈만) · `npm run build`. 명세와 코드의 대조는 싱크독 `tools/check_code.py`(MS 시그니처 · docstring ID)와 `tools/check_ui.py`(`data-el` 번호)로 한다(DEV-14).

**아직 하지 않은 것.** Kaggle 실측(토큰이 없다), 페이지에서 상태를 바꿔 저장하는 실물 확인(토큰이 필요하다). D1 · D2 · D3은 2026-09-30에 병합했고, 같은 날 예약 실행이 처음으로 목록 파일을 만들었다. 노션 환경 둘과 시크릿도 같은 날 지웠다(4장).

## 1. 슬라이스

#### A 기반

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-INFRA-001]] 3 · 4 · 5.4 · 8.5 · [[CCR-API-001]] 1.1 · 1.2 · 2.1 |
| 구현 | `batch/`의 uv 프로젝트(`pyproject.toml` · `uv.lock` · uv 버전 고정) · `settings.toml` · `core/settings.py`(조정값 · 비밀값 · 실행 문맥) · `core/logging.py`(가리기) · `shared/dates.py` · `shared/text.py` · `infra/http.py` · `infra/robots.py` · `.gitignore` · `.env.example`. 노션 ID의 두 표기를 만들던 `secret_variants`는 D1에서 뺀다 |
| 구현 함수 | [[CCR-MS-001#RunContext.from_env]] · [[CCR-MS-001#Settings.load]] · [[CCR-MS-001#Secrets.from_env]] · [[CCR-MS-001#settings.read_dotenv]] · [[CCR-MS-001#logging.register_actions_masks]] · [[CCR-MS-001#SecretFilter.filter]] · [[CCR-MS-001#dates.parse_to_kst_date]] · [[CCR-MS-001#dates.kst_date_of]] · [[CCR-MS-001#dates.kst_midnight_utc]] · [[CCR-MS-001#text.clean_text]] · [[CCR-MS-001#text.html_text]] · [[CCR-MS-001#SourceHttp.fetch]] · [[CCR-MS-001#http.parse_retry_after]] · [[CCR-MS-001#robots.ensure_allowed]] |
| API | 대회 소스 공통 규칙([[CCR-API-001]] 1.1 · 1.2 · 2.1) |
| 화면 | 없음 |
| 테스트 | `tests/core` · `tests/shared/test_dates.py` · `tests/infra/test_http.py` · `tests/infra/test_robots.py` — 기준일 · 쓰기 여부 · 가리기 · 재시도 · 예산(본문을 받는 중 포함) · 압축 본문 · 리디렉션 · robots |
| 선행 | 없음 |
| 완료 | `77a61ec` · `fe8a3d7`(본문을 받는 중에도 예산으로 끊기 · 대회명 앞뒤만 다듬기) |

#### B1 수집

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-UC-001#UC-S1]] · [[CCR-UC-001#UC-S2]] · [[CCR-SCN-001#S5]] |
| 구현 | `domains/collect/` — 모델 · `Source` 포트 · `CollectService` · 어댑터 여섯. 테스트 픽스처(실측을 줄이고 연락처를 뺀 것) |
| 구현 함수 | [[CCR-MS-001#CollectService.collect_all]] · [[CCR-MS-001#CollectService._collect_one]] · [[CCR-MS-001#eventus.build_query]] · [[CCR-MS-001#eventus.normalize]] · [[CCR-MS-001#EventUsSource.collect]] · [[CCR-MS-001#dacon.normalize]] · [[CCR-MS-001#DaconSource.collect]] · [[CCR-MS-001#kaggle.normalize]] · [[CCR-MS-001#kaggle.is_practice]] · [[CCR-MS-001#KaggleSource.collect]] · [[CCR-MS-001#wevity.parse_list]] · [[CCR-MS-001#wevity.parse_detail_end]] · [[CCR-MS-001#wevity.deadline_of]] · [[CCR-MS-001#WevitySource.collect]] · [[CCR-MS-001#WevitySource._calibrate]] · [[CCR-MS-001#aifactory.extract_payload]] · [[CCR-MS-001#aifactory.parse_tasks]] · [[CCR-MS-001#aifactory.group_tasks]] · [[CCR-MS-001#aifactory.competition_name]] · [[CCR-MS-001#aifactory.to_competition]] · [[CCR-MS-001#contestkorea.parse_list]] · [[CCR-MS-001#contestkorea.resolve_dates]] · [[CCR-MS-001#ContestKoreaSource.collect]] |
| API | [[CCR-API-001#POST/api.event-us.kr/api/v1/engine/search]] · [[CCR-API-001#GET/app.dacon.io/api/v1/competition/list]] · [[CCR-API-001#POST/api.kaggle.com/v1/…/ListCompetitions]] · [[CCR-API-001#GET/www.wevity.com/?c=find]] · [[CCR-API-001#GET/www.wevity.com/?c=find&gbn=view]] · [[CCR-API-001#GET/aifactory.space/ko/competition]] · [[CCR-API-001#GET/www.contestkorea.com/sub/list.php]] |
| 화면 | 없음 |
| 테스트 | `tests/domains/collect` — 저장한 응답으로 소스마다 건수 · 대회명 · 링크 · 날짜, 멈추는 때, 쪽 상한, wevity 보정(0 · −1 · 실패), 실패의 종류. 실측: 2026-09-27 다섯 소스 성공(event-us 39 · DACON 30 · wevity 168 · AI팩토리 과제 112 → 88 · 콘테스트코리아 136), Kaggle 설정 누락 |
| 선행 | A |
| 완료 | `993cf0c` · `fe8a3d7`(HTML 대회명은 `html_text`) · `0487ff4`(fix(#4) wevity 멈추는 때, 3장) |

#### B2 기록

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-UC-001#UC-S4]] 2 · [[CCR-UC-001#UC-S7]] · [[CCR-INFRA-001]] 6.2 · [[CCR-DOM-003]] |
| 구현 | `domains/record/` — `HistoryRecord` · `RunLine` · `RecordCrud`(읽기 · 추가분 통째로 쓰기 · main 판 꺼내기) · `RecordService`(남김 수 견주기 · 소스 0건 경고) |
| 구현 함수 | [[CCR-MS-001#RecordService.start]] · [[CCR-MS-001#RecordService.load]] · [[CCR-MS-001#RecordService.history_shrank]] · [[CCR-MS-001#RecordService.append]] · [[CCR-MS-001#RecordService.zero_count_warnings]] · [[CCR-MS-001#RecordService.write_run]] · [[CCR-MS-001#RecordCrud.read_history]] · [[CCR-MS-001#RecordCrud.read_runs]] · [[CCR-MS-001#record._atomic_write]] · [[CCR-MS-001#record.export_main_state]] |
| API | 없음(기록 파일) |
| 화면 | 없음 |
| 테스트 | `tests/domains/record` — 첫 실행 · 읽히지 않는 줄 · 필수 필드 · 남김 감소 · 추가분 통째로 쓰기 · 미리보기는 쓰지 않음 · 줄의 필드 · 소스 0건(연속 · 같은 날 합침 · 실패 건너뜀) · main 판 꺼내기 |
| 선행 | A · B1 |
| 완료 | `cdcd353` · `fe8a3d7`(git이 없거나 시간 초과여도 처리 이력 읽기 실패) |

#### B4 선별

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-UC-001#UC-S3]] · [[CCR-UC-001#UC-S4]] · [[CCR-UC-001#UC-S5]] · [[CCR-PRD-001]] 5.2 · [[CCR-SCN-001#S2]] · [[CCR-SCN-001#S3]] · [[CCR-SCN-001#S4]] |
| 구현 | `domains/screen/` — 판정 규칙(`matching.py`) · `ScreenService`(마감 · 묶기 · 아는 대회 · 판별) · `Judge` 포트 · `OpenAiJudge` |
| 구현 함수 | [[CCR-MS-001#matching.normalize_title]] · [[CCR-MS-001#matching.extract_marks]] · [[CCR-MS-001#matching.normalize_link]] · [[CCR-MS-001#matching.similarity]] · [[CCR-MS-001#matching.judge_pair]] · [[CCR-MS-001#matching.group]] · [[CCR-MS-001#matching.representative_order]] · [[CCR-MS-001#ScreenService.drop_expired]] · [[CCR-MS-001#ScreenService.bundle]] · [[CCR-MS-001#ScreenService.build_known]] · [[CCR-MS-001#ScreenService.split_known]] · [[CCR-MS-001#ScreenService._matches]] · [[CCR-MS-001#ScreenService._record_known]] · [[CCR-MS-001#screen.entries_for]] · [[CCR-MS-001#ScreenService.judge]] · [[CCR-MS-001#ScreenService._ask_all]] · [[CCR-MS-001#OpenAiJudge.judge]] · [[CCR-MS-001#openai_judge.build_input]] |
| API | [[CCR-API-001#POST/api.openai.com/v1/responses]] |
| 화면 | 없음 |
| 테스트 | `tests/domains/screen` · `tests/shared/test_text.py` — 정규화 · 연도 · 회차 · 링크 · PRD의 유사도 0.94 · 0.85 재현 · 2 · 3단계로 가르기 · 마감 연장 · 링크와 연도 · 이름만 같음 · 사슬 끊기 · 대표 · 아는 대회와 구성원 기록 · 남김이 버림을 이김 · 판별(버림 · 절반 규칙 · 치명 오류 · 키 없음 · 오늘 마감) · OpenAI 오류 가름 · BOM. 아는 대회의 한쪽이던 노션 행은 D1에서 목록 항목으로 바뀐다 |
| 선행 | A · B1 · B2 |
| 완료 | `79c55c9` · `7d63b56`(fix(#3) 문턱 0.90과 모든 짝 규칙, 3장) |

#### B5 실행 흐름

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-UC-001#UC-A1]] · [[CCR-UC-001#UC-S7]] · [[CCR-SCN-001#S1]] · [[CCR-SCN-001#S6]] · [[CCR-SCN-001#S7]] |
| 구현 | `run/pipeline.py`(`Pipeline`) · `__main__.py`(입구 · 신호 · `collect` 하위 명령) |
| 구현 함수 | [[CCR-MS-001#__main__.main]] · [[CCR-MS-001#__main__.run_batch]] · [[CCR-MS-001#__main__.run_collect]] · [[CCR-MS-001#Pipeline.run]] · [[CCR-MS-001#Pipeline._run]] · [[CCR-MS-001#Pipeline._load]] · [[CCR-MS-001#Pipeline._finish]] |
| API | 없음 |
| 화면 | 없음 |
| 테스트 | `tests/run/test_pipeline.py` — 정상 흐름의 건수와 기록 · 미리보기는 아무것도 쓰지 않음 · 전 소스 실패 · 처리 이력 읽기 실패 · 처리 이력 감소 · 키 없음 · 소스 실패 표시 · 신호면 줄 없음. 실측: Actions에서 `DRY_RUN`이 비면 2. 노션 읽기 · 컬럼 · 오늘 마감 행 실패의 테스트는 D1에서 목록 파일의 것으로 바뀐다 |
| 선행 | B2 · B4 |
| 완료 | `546d3e7` |

#### B6 마무리 단계

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-UC-001#UC-A1]] 9 · \*a2 · [[CCR-INFRA-001]] 8.2 · [[CCR-DOM-003#runs]] |
| 구현 | `batch/finish.py`(표준 라이브러리 · git만) |
| 구현 함수 | [[CCR-MS-001#finish.finish]] · [[CCR-MS-001#finish.read_additions]] · [[CCR-MS-001#Git.fresh_main]] · [[CCR-MS-001#Git.commit_and_push]] · [[CCR-MS-001#finish.append_lines]] |
| API | 없음(git) |
| 화면 | 없음 |
| 테스트 | `tests/test_finish.py`(로컬 bare 저장소를 원격으로) — 추가분과 남김 수 · 봇 작성자와 메시지 · 중단 줄 · 형식이 틀린 줄 · 이미 올린 실행 · 경합 뒤 다시 얹기(관리자 수정이 남음) · 빈 저장소의 첫 실행 · KST 기준일 · 줄바꿈 |
| 선행 | B2 |
| 완료 | `4f689f6` |

#### C 운영

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-INFRA-001]] 5.1 · 5.5 · 5.6 · 8.1 · 8.8 |
| 구현 | `.github/workflows/daily.yml`(예약 08:50 KST · 수동 입력 둘 · 동시성 줄 세우기 · 액션 SHA 고정 · [[CCR-INFRA-001]] 8.1의 다섯 차례를 스텝 일곱으로) · `.github/dependabot.yml` · `README.md`(준비 · 운영) · `AGENTS.md`(에이전트 규칙). 쓰기 여부를 가르던 노션 환경(`notion-write` · `notion-read`)은 D3에서 뺀다 |
| 구현 함수 | 없음 |
| API | 없음 |
| 화면 | 없음 |
| 테스트 | actionlint 1.7.12(아직 모르는 `concurrency.queue` 한 건을 빼고 통과. GitHub 문서로 `queue: max` · `schedule.timezone`을 확인) · YAML 구문 |
| 선행 | B5 · B6 |
| 완료 | `7a4a002` |

#### D1 목록 경계

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-UC-001#UC-S4]] 1 · [[CCR-UC-001#UC-S6]] · [[CCR-UC-001#UC-A1]] 1d · 7 · 9 · [[CCR-DOM-002]] 1 · 4.5 · 4.7 · 4.10 · [[CCR-DOM-003#competitions]] · [[CCR-INFRA-001]] 5 · 6.2 · 8.2 · [[CCR-SEQ-001#SEQ-3]] · [[CCR-SEQ-001#SEQ-5]] · [[CCR-SEQ-001#SEQ-7]] |
| 구현 | `domains/list/`(`ListEntry` · `entry_of` · `ListCrud` · `ListService`) 신설. `domains/notion/` · `infra/notion.py`와 그 테스트 삭제. `Pipeline._run`(목록 파일 → 처리 이력 차례, 실패 사유 넷) · `Pipeline._load`(항목 더하기 → 곧바로 남김 기록) · `__main__.run_batch`(서비스 넷 조립) · `RecordService.start`(데이터 폴더 꺼내기) · `record.export_main_state`(세 파일) · `matching.key_of_entry` · `finish.py`(세 파일 · `existing_ids` · 세 경로 커밋). `Secrets` 둘, `Settings`에서 notion 표 제거, `secret_variants` 제거, `RunLine`에서 `create_failed`와 노션 실패 사유 · 경고 종류 제거. `settings.toml` · `.env.example` · `AGENTS.md` · `README.md`의 노션 문구 정리. 함께 닫는 규약 미준수 둘: 모든 공개 함수의 docstring 첫 줄을 `CCR-MS-001#항목`으로(#5), `ruff`를 `pyproject.toml`에 넣고 `check` · `format`을 통과시킨다(#6, 싱크독 백엔드의 ruff 설정을 따른다) |
| 구현 함수 | [[CCR-MS-001#ListEntry.id]] · [[CCR-MS-001#ListEntry.to_dict]] · [[CCR-MS-001#ListEntry.from_dict]] · [[CCR-MS-001#list.entry_of]] · [[CCR-MS-001#ListService.load]] · [[CCR-MS-001#ListFile.ids]] · [[CCR-MS-001#ListService.append]] · [[CCR-MS-001#ListService.appended_count]] · [[CCR-MS-001#ListCrud.read]] · [[CCR-MS-001#ListCrud.reset_appends]] · [[CCR-MS-001#ListCrud.write_appends]] · [[CCR-MS-001#matching.key_of_entry]] · [[CCR-MS-001#ScreenService.build_known]] · [[CCR-MS-001#Pipeline._run]] · [[CCR-MS-001#Pipeline._load]] · [[CCR-MS-001#__main__.run_batch]] · [[CCR-MS-001#RecordService.start]] · [[CCR-MS-001#RecordService.load]] · [[CCR-MS-001#record.export_main_state]] · [[CCR-MS-001#Secrets.from_env]] · [[CCR-MS-001#Settings.load]] · [[CCR-MS-001#logging.register_actions_masks]] · [[CCR-MS-001#finish.finish]] · [[CCR-MS-001#finish.read_additions]] · [[CCR-MS-001#finish.existing_ids]] · [[CCR-MS-001#Git.commit_and_push]] |
| API | 없음(파일). 배치는 GitHub에 HTTP 요청을 보내지 않는다([[CCR-API-001]] 3.3) |
| 화면 | 없음 |
| 테스트 | `tests/domains/list`(구조 거울) — 첫 실행 · 깨진 줄 · 필수 필드 · 겹친 식별자 · 더하기 두 번 · 같은 식별자는 `None` · 미리보기는 쓰지 않음 · 임시 파일 없음. `tests/domains/screen` — `key_of_entry`(원천 ID 1단계 · 링크만 같고 연도 다름) · 목록 항목이 버림 기록을 이김. `tests/run/test_pipeline.py` — 목록 파일 읽기 실패 · 넣은 묶음마다 항목과 남김 줄 · 이미 있는 식별자 · 시크릿 없이 수집 · 실패 사유 넷. `tests/test_finish.py` — 세 파일 붙이기 · 이미 있는 식별자 건너뜀 · 상태 파일 그대로 · 세 경로만 커밋. `tests/domains/record` — 세 파일 꺼내기. 규약: `uv run ruff check .` · `uv run ruff format --check .` 0건(74 files), 싱크독 `check_code.py` 대상 135 · 일치 135 · 미완 0. 키워드 전용 인자 둘도 일치했다(싱크독 #196이 고쳐져 [[CCR-MS-001]] 3장의 그 미결은 지운다). pytest 182. 실측(2026-09-30): 로컬 미리보기가 시크릿 없이 끝까지 돌았다 — 다섯 소스 473건 · 마감 지남 143 · 묶음 263 · 키가 없어 판별 미룸(경고 `judge_deferred` / `missing_key`) · 오늘 마감 56건이 「넣었을 대회」로 로그에 남고 파일은 쓰지 않았다 |
| 선행 | B6 |
| 완료 | [#7](https://github.com/HoyoungParkme/competition-crawler/pull/7)(`code/d1-list` → `main`) · 병합 `d791197` · 2026-09-30. 커밋 12개(3장). #5 · #6을 닫았다. `daily.yml`의 노션 환경 줄과 `NOTION_*` 시크릿 줄은 카드대로 D3에 남겼다 |

#### D2 대회 목록 페이지

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-UI-001#UI-1]] · [[CCR-UI-001#UI-2]] · [[CCR-UC-001#UC-A2]] · [[CCR-UC-001#UC-H1]] · [[CCR-UC-001#UC-H2]] · [[CCR-DOM-002]] 1 · 3.2 · 4.11 · 5장 결정 9 · 10 · 11 · [[CCR-DOM-003#competitions]] · [[CCR-DOM-003#status]] · [[CCR-API-001]] 1.4 · 2.3 · 3.3 · 4.2 · [[CCR-INFRA-001]] 4 · 5.8 · 6.4 · [[CCR-SEQ-001#SEQ-11]] · [[CCR-SEQ-001#SEQ-12]] |
| 구현 | `frontend/` — Vite + React + TypeScript. `src/config.ts` · `src/styles.css`(UI 명세 3장의 토큰) · `src/domain/types.ts` · `src/api/data.ts` · `src/api/github.ts` · `src/store/token.ts` · `src/store/status.ts` · `src/pages/CompetitionList.tsx` · `src/components/FilterBar.tsx` · `CompetitionTable.tsx` · `Notice.tsx` · `SettingsDialog.tsx` · `index.html`(폰트 링크 하나, 외부 스크립트 없음) · `vite.config.ts`(`base: '/competition-crawler/'`) · eslint · prettier · vitest. 요소마다 `data-el`에 UI 명세의 번호. `.gitignore`에 `node_modules` · `frontend/dist` |
| 구현 함수 | MS 밖(TypeScript). 모듈과 시그니처는 [[CCR-DOM-002#CompetitionList]] · [[CCR-DOM-002#SettingsDialog]] · [[CCR-DOM-002#StatusStore]] · [[CCR-DOM-002#RepoFiles]] · [[CCR-DOM-002#TokenStore]] |
| API | [[CCR-API-001#GET/raw.githubusercontent.com/…/data/{file}]] · [[CCR-API-001#GET/api.github.com/…/contents/data/status.json]] · [[CCR-API-001#PUT/api.github.com/…/contents/data/status.json]] |
| 화면 | [[CCR-UI-001#UI-1]] 대회 목록 · [[CCR-UI-001#UI-2]] 설정 대화상자 |
| 테스트 | `frontend/tests/`(vitest, 브라우저 없음) — `parseListFile`(깨진 줄 건너뜀 · 겹친 식별자는 앞의 것) · `parseStatusFile`(객체 아님 · 모양이 다른 값) · `sortByDeadline`(오름차순 · `null`은 맨 뒤 · 같은 날은 대회명) · `isExpired` · `mergeChange`(그 대회만 · 되살리기는 `hidden=false`) · `commitMessage`(세 꼴 · 60자) · `encodeStatusFile` · `decodeContent`(줄바꿈 섞인 Base64) · `tokenProblem`. `npm run build` 통과. 싱크독 `check_ui.py`로 `data-el` 번호와 요소 표 대조. 화면은 사용자가 브라우저에서 요소 번호대로 눌러 확인한다(DEV-14). 실측은 D3 배포 뒤(4장). 결과(2026-09-30): vitest 22 통과(위 관점에 `StatusStore`의 큐 · 판 어긋남에 한 번 다시 · 두 번째 어긋남은 포기 · 되돌리기와 다시 시도, `kstToday` · `dueLabel` · `saveFailureText`를 더했다). `npm run build` · `npm run lint`(eslint · prettier) 0건. `check_ui.py` UI-1 요소 27 · 일치 27, UI-2 요소 9 · 일치 9, 불일치 0(셀렉트 · 입력 칸에 배지가 안 그려진다는 알림 둘). 로컬 `npm run dev`에서 raw 응답을 가짜 파일로 바꿔 마감일 순 · 마감일 없음 맨 뒤 · 7일 안 강조 · 상태 색 · 토큰 없이 바꾸면 토큰 없음(11)과 값 유지 · 접힌 구역과 되살리기(9.1) · 설정 대화상자와 Esc를 봤다. TypeScript는 6.0에 묶었다(typescript-eslint가 6.1 미만을 요구한다) |
| 선행 | D1(목록 파일의 형식은 ERD가 정하므로 코드 의존은 없다. D1이 먼저 병합돼야 실측할 파일이 생긴다) |
| 완료 | [#8](https://github.com/HoyoungParkme/competition-crawler/pull/8)(`code/d2-frontend` → `main`) · 병합 `bbd2d23` · 2026-09-30. 커밋 9개(3장). 요소 번호대로 눌러 보기와 실제 쓰기는 D3 배포 뒤(4장) |

#### D3 배포와 저장소 설정

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-INFRA-001#C12]] · [[CCR-INFRA-001#C14]] · [[CCR-INFRA-001]] 5.1 · 5.6 · 5.8 · 8.1 · 8.10 · 8.11 |
| 구현 | `.github/workflows/pages.yml`(`frontend/**` push와 수동 실행 · `pages: write` · `id-token: write` · `contents: read` · Node 24 · `npm ci` · `npm run build` · `configure-pages` → `upload-pages-artifact(frontend/dist)` → `deploy-pages` · 액션 SHA 고정) · `daily.yml`에서 환경(`environment:`)을 빼고 마무리 스텝 조건을 `if: always() && github.ref == 'refs/heads/main' && env.DRY_RUN == 'false'`로, 시크릿은 `OPENAI_API_KEY` · `KAGGLE_API_TOKEN`만 · `dependabot.yml`에 npm · `README.md`(페이지 토큰 만드는 법 · Pages 켜기 · 시크릿 둘). 저장소 설정: Pages 배포 소스를 GitHub Actions로 켜기, 환경 `notion-write` · `notion-read`와 시크릿 `NOTION_DATA_SOURCE_ID` 지우기 |
| 구현 함수 | 없음 |
| API | 없음 |
| 화면 | 없음 |
| 테스트 | actionlint · YAML 구문 · `pages.yml`이 `frontend/`만 바뀐 push에 돌고 `data/`만 바뀐 커밋에는 돌지 않음(첫 배포 뒤 실측) · 페이지가 `https://hoyoungparkme.github.io/competition-crawler/`에서 열림 · 수동 실행 한 번으로 미리보기 · 실제 실행이 환경 없이 돎. 결과(2026-09-30): actionlint 1.7.12로 `pages.yml` 0건, `daily.yml`은 C 때부터 알던 `concurrency.queue` 한 건. `git archive`로 꺼낸 깨끗한 `frontend/`에서 Node 24 · `npm ci` · `npm run build` 통과(자산 경로 `/competition-crawler/assets/…`). 병합 커밋이 돌린 첫 배포(실행 36660069757)가 모든 스텝 성공, 주소가 200을 내고 목록 49건을 그린다. 병합 뒤 `main`의 미리보기(실행 36660197145)가 환경 없이 성공했다 — 마무리 스텝은 건너뛰었고 노션 환경의 배포 기록이 새로 생기지 않았다. 후보 332건 · 묶음 264개가 모두 아는 대회라 판별 0건, 46.2초. `data/`만 바뀐 커밋에 `pages.yml`이 돌지 않는지와 환경 없는 실제 실행은 다음 예약 실행(2026-10-01)에서 본다 |
| 선행 | D2 |
| 완료 | [#9](https://github.com/HoyoungParkme/competition-crawler/pull/9)(`code/d3-pages` → `main`) · 병합 `2b820b6` · 2026-09-30. 커밋 4개(3장). Pages는 병합 전에 API로 켰다(소스 GitHub Actions). GitHub가 만든 배포 환경 `github-pages`는 `main`에서만 배포를 받는다. `pages.yml`의 잡은 이 환경으로 배포한다(deploy-pages의 요구). [[CCR-INFRA-001]] v6이 5.1의 예외와 8.11 표에 적었다. 잡 시간 한도 10분을 더했다. 노션 환경 둘과 시크릿 `NOTION_DATA_SOURCE_ID`는 사용자 결정으로 2026-09-30에 지웠다. 남은 환경은 `github-pages` 하나, 저장소 시크릿은 `OPENAI_API_KEY` 하나다 |

## 2. 통합 테스트

| 시나리오 | 슬라이스 | 검증하는 것 |
|---|---|---|
| [[CCR-SCN-001#S1]] 평소 아침 | B5 · D1 | `test_happy_path_loads_keeps_and_records_discards` — 마감 지난 대회 · 목록에 있는 대회 · 버림이 빠지고 남김 하나가 목록 파일에 더해지며, 남김 · 버림 · 아는 대회의 구성원이 처리 이력에 적힌다(D1에서 노션 행을 목록 항목으로 바꿔 다시 쓴다) |
| [[CCR-SCN-001#S2]] 처음 돌리는 날 | B4 · D1 | 목록 항목이 버림 기록을 이겨 남김으로 적힘 · 링크가 같은 목록 항목(원천 ID가 바뀐 공고). `test_prd_pair_at_082_is_undecided` — 이름을 많이 다르게 쓴 같은 대회(0.82)는 판단하지 않아 항목이 하나 더 생길 수 있다 |
| [[CCR-SCN-001#S3]] 여러 갈래 | B4 | `test_group_merges_duplicate_notices_across_sources` · `test_representative_prefers_more_dates_then_priority` · `test_group_needs_every_pair_to_be_the_same` · `test_group_keeps_templated_idea_contests_apart` · 실측 후보 321건의 묶음(가장 큰 묶음 3건, [[CCR-PRD-001]] 5.2) |
| [[CCR-SCN-001#S4]] 관심 없는 대회 | B4 · B5 | 판별 버림 · 절반 규칙 · 키 없음 · 치명 오류 |
| [[CCR-SCN-001#S5]] 소스 하나가 깨짐 | B1 · B5 | 실패 종류 여섯 · `test_failed_source_is_marked_and_run_continues` · 소스 0건 경고 |
| [[CCR-SCN-001#S6]] 실패한 날 다시 | B5 · B6 · D1 | 실패 사유 넷(목록 파일 읽기 실패 포함) · 신호로 멈추면 중단 줄 · 이미 올린 실행을 다시 얹지 않음 · 세 파일이 한 커밋 |
| [[CCR-SCN-001#S7]] 마감이 지남 | B4 · D1 | `test_drop_expired_keeps_today_and_unknown_deadlines` — 목록 항목은 건드리지 않는다(항목을 고치거나 지우는 길이 없다) |
| [[CCR-SCN-001#S8]] 페이지에서 상태를 바꾼다 | D2 | `mergeChange` · `commitMessage` · `encodeStatusFile`의 vitest. 화면은 사용자가 요소 번호대로 확인한다. 실물은 4장의 차례로 |

실물(GitHub Actions · OpenAI · Pages · Contents API)로 도는 통합 확인은 4장의 차례로 한다.

## 3. 커밋 · PR 목록

| 커밋 | 슬라이스 | 내용 |
|---|---|---|
| `77a61ec` | A | 배치 기반: 설정 · 로그 가리기 · KST 날짜 · 소스 요청 도구 |
| `993cf0c` | B1 | 수집: 여섯 소스 어댑터와 소스별 결과 |
| `cdcd353` | B2 | 기록: 처리 이력 · 실행 요약 읽기와 추가분 쓰기 |
| `0950717` | (B3 노션, D1에서 제거) | 노션: 행 읽기 · 컬럼 확인 · 행 만들기. 2026-09-29의 결정으로 D1이 이 코드를 지운다. 이력으로만 남는다 |
| `79c55c9` | B4 | 선별: 마감 판정 · 같은 대회 묶기 · 아는 대회 가르기 · 관심 분야 판별 |
| `546d3e7` | B5 | 실행 흐름: 하루치를 차례로 돌리고 실행 요약 한 줄을 남긴다 |
| `4f689f6` | B6 | 마무리 단계: 추가분을 main 최신 판 위에 다시 얹어 한 커밋으로 올린다 |
| `7a4a002` | C | 운영: 매일 08:50 KST 워크플로 · Dependabot · 안내 문서 |
| `fe8a3d7` | A · B1 · B2 | 검증 반영: 본문을 받는 동안에도 시간 예산으로 끊고, 대회명 다듬기를 명세에 맞췄다 |
| `7d63b56` | fix(#3) · B4 | 선별: 같은 대회 판정 문턱을 0.90으로 올리고, 묶음은 모든 짝이 같을 때만 묶는다([[CCR-DOM-002]] 5장 결정 7). 이슈 #3 |
| `0487ff4` | fix(#4) · B1 | 수집: wevity는 쪽의 마지막 공고가 마감일 때 분야를 멈춘다([[CCR-DOM-002]] 5장 결정 8). 이슈 #4 |
| `5fe3d33` | D1 | `list.entry_of` — 목록 항목 모델과 대표에서 항목 만들기 |
| `6d7c583` | D1 | `ListCrud.read` — 목록 파일 읽기와 추가분 통째로 쓰기 |
| `e390051` | D1 | `ListService.load` — 목록 파일 읽기와 더하기, 테스트 |
| `1e1d80d` | D1 | `matching.key_of_entry` — 목록 항목의 판정 값, 아는 대회를 목록 항목으로 |
| `751f60b` | D1 | `RecordService.start` — 데이터 폴더 꺼내기(세 파일)와 기록 파일 필드 정리 |
| `aea7779` | D1 | `Secrets.from_env` — 비밀값 둘, 노션 설정과 `secret_variants` 제거 |
| `e895fdf` | D1 | `Pipeline._load` — 목록 파일에 더하고 곧바로 남김을 적는다, 실패 사유 넷, 노션 코드와 테스트 삭제 |
| `abdfb21` | D1 | `__main__.run_batch` — 서비스 넷 조립 |
| `478d90a` | D1 | `finish.existing_ids` — 목록 추가분을 세 파일과 함께 올린다, 있는 식별자는 건너뜀 |
| `da8fda3` | D1 | 공개 함수 전부 — docstring 첫 줄에 `CCR-MS-001` 항목 ID, 따옴표 반환 주석 제거(#5) |
| `b52d9c8` | D1 | ruff 도입 — line-length 100 · E F I UP B, format과 check 통과(#6) |
| `1a2b725` | D1 | `AGENTS.md` · `README.md` — 노션 문구를 목록 파일과 페이지로, 코드 규약 절 |
| `972ca00` | D2 | frontend 틀 — Vite · React · TypeScript, 설정 상수, 두 개념의 타입, 공통 틀 토큰 |
| `54670a3` | D2 | `readListFile` — raw 읽기와 두 파일의 파싱(깨진 줄 건너뜀 · 겹친 식별자는 앞의 것) |
| `c425b68` | D2 | `writeStatusFile` — Contents API 판 읽기 · 쓰기, 상태 파일 인코딩 |
| `bbe6790` | D2 | `TokenStore` — localStorage의 페이지 토큰 |
| `44fb8d1` | D2 | `StatusStore` — 화면 먼저, 요청 하나씩, 판 어긋남에 한 번 다시, 실패면 되돌림 |
| `14dfd45` | D2 | `CompetitionTable` — 목록 표 · 접힌 구역 · 거르기 줄 · 알림 |
| `71da19a` | D2 | `SettingsDialog` — UI-2, 판 읽기로 검증한 뒤 토큰 저장 |
| `19c31c4` | D2 | `CompetitionList` — UI-1, 두 파일을 Row로 합쳐 마감일 순으로 |
| `1346169` | D2 | `README.md` — 페이지 로컬 실행 |
| `150953a` | D3 | `pages.yml` — frontend 빌드와 GitHub Pages 배포, 액션 SHA 고정 |
| `13427d5` | D3 | `daily.yml` — 노션 환경과 `NOTION_*` 시크릿 줄 제거 |
| `47f9d02` | D3 | `dependabot.yml` — frontend npm 갱신 |
| `b1de848` | D3 | `README.md` · `AGENTS.md` — Pages 켜기, 노션 설정 지우기, 페이지 확인 명령 |
| `571cb8b` | fix(#10) · D2 | `sortByDeadline` — 쓰지 않는 `today` 인자를 뺀다. 이슈 #10 |
| `3171257` | fix(#10) · D2 | `tokenProblem` — 뜰 일 없는 404 문구를 지운다. 이슈 #10 |

PR은 둘이다. [#1](https://github.com/HoyoungParkme/competition-crawler/pull/1)(`feat/batch` → `main`)은 A ~ C와 검증 반영을, [#2](https://github.com/HoyoungParkme/competition-crawler/pull/2)(`fix/matching-wevity` → `main`)는 fix(#3) · fix(#4)를 담았다. 위 커밋 해시를 그대로 남기려고 둘 다 병합 커밋으로 합쳤다. 이 둘은 규약 DEV-13 · DEV-15보다 앞서 만든 것이라 커밋 메시지의 꼴이 다르다. 이력은 고치지 않는다.

D1 ~ D3은 카드마다 브랜치 · PR 하나이고, 커밋은 `code(D1): 함수 — 요약` 꼴로 함수 하나에 하나다. [#7](https://github.com/HoyoungParkme/competition-crawler/pull/7)(`code/d1-list` → `main`, 병합 커밋 `d791197`, 2026-09-30)이 D1이고 이슈 #5 · #6을 닫았다. [#8](https://github.com/HoyoungParkme/competition-crawler/pull/8)(`code/d2-frontend` → `main`, 병합 커밋 `bbd2d23`, 2026-09-30)이 D2다. 페이지 코드는 MS 밖(TypeScript)이라 커밋을 함수가 아니라 모듈 하나에 하나로 나눴다. [#9](https://github.com/HoyoungParkme/competition-crawler/pull/9)(`code/d3-pages` → `main`, 병합 커밋 `2b820b6`, 2026-09-30)이 D3이다. 워크플로와 안내 문서뿐이라 파일 하나에 커밋 하나다. [#11](https://github.com/HoyoungParkme/competition-crawler/pull/11)(`fix/page-leftovers` → `main`, 병합 커밋 `4d3559f`, 2026-09-30)은 이슈 #10을 고친 fix 둘이다. 끝난 카드의 수정이라 카드는 건드리지 않았다(DEV-15). 병합이 돌린 페이지 배포(실행 36681669374)가 성공했고, 배포된 번들에서 지운 문구가 빠진 것을 확인했다.

## 4. 미결사항

2026-09-30에 네 가지를 마무리했다. 토큰 검증이 쓰기 권한까지 보지 못하는 것은 사용자 결정대로 명세를 코드에 맞췄다([[CCR-UC-001]] v9 · [[CCR-UI-001]] v2 · [[CCR-API-001]] v4 · [[CCR-DOM-002]] v6 · [[CCR-SEQ-001]] v4). `github-pages` 환경은 [[CCR-INFRA-001]] v6의 5.1과 8.11에 적었다. 노션 환경 둘과 시크릿은 지웠다(D3). D2 페이지 코드와 DOM-002가 다르던 곳도 사용자 결정대로 닫았다. 이름과 값의 모양, 응답 sha를 기억하는지는 명세를 코드에 맞췄고([[CCR-DOM-002]] v7 · [[CCR-API-001]] v5), 쓰지 않는 정렬 인자와 뜰 일 없는 404 문구는 fix(#10)으로 코드에서 지웠다(3장). 같은 날 SEQ-001이 되먹인 INFRA 8.2의 필수 필드 문장도 ERD를 가리키게 고쳤다([[CCR-INFRA-001]] v7 · [[CCR-DOM-003]] v4 · [[CCR-SEQ-001]] v5).

- [ ] **사용자가 준비할 것.** (1) 페이지 토큰 — GitHub 설정에서 fine-grained 토큰을 이 저장소 하나 · Contents 읽기·쓰기만 · 만료 기한을 두고 만들어, 배포된 페이지의 설정(UI-2)에 넣는다. 저장소에는 넣지 않는다([[CCR-INFRA-001]] 5.8). (2) 실패 알림(GitHub 알림 설정). (3) `KAGGLE_API_TOKEN`은 선택
- [ ] **실물 확인 차례.** 여기까지 했다(2026-09-30): D1 · D2 병합 → 그날 예약 실행(실행 36659861590, 08:50 예약이 11:26 KST에 시작)이 D1 · D2의 코드로 실제 적재 — 결과 성공, 목록 49건 · 버림 215 · 판별 실패 0 · 남김 기록 67, 144.1초. 세 파일이 커밋 `8c15cfa` 하나로 올라왔다 → D3 병합과 Pages 첫 배포 → 페이지에 목록 49건이 보인다 → 미리보기에서 그날 후보가 모두 아는 대회. 남은 것: 페이지에서 상태를 바꾸면 `data/status.json` 커밋이 생김(토큰이 필요하다) → 다음 실행이 지운 대회를 다시 넣지 않음 → `data/`만 바뀐 커밋에 `pages.yml`이 돌지 않음. raw 캐시의 `?t=`가 CDN까지 피하는지도 이때 본다([[CCR-INFRA-001]] 9장)
- [ ] **Kaggle 실측.** 토큰이 생기면 [[CCR-API-001]] 5장대로 실측하고 `kaggle.py`와 테스트를 맞춘다
- [ ] **예약 실행.** 2026-09-28 · 09-29의 예약 실행은 생겼다(각각 11:00 · 11:46 KST로 두세 시간 늦게, GitHub의 지연). 둘 다 실패인데 노션 설정이 없어 설정 누락으로 끝난 것이다. 2026-09-30의 예약 실행은 11:26 KST에 시작해 D1 · D2의 코드로 성공했다(위 실물 확인). 이때까지는 워크플로가 `notion-write` 환경을 가리켰고, 환경 없는 첫 예약 실행은 2026-10-01이다. 지연은 [[CCR-INFRA-001]] 8.4의 받아들인 한계다
