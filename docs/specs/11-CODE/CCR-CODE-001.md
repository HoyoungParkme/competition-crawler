---
doc_id: CCR-CODE-001
type: CODE
title: 구현 계획 — 대회 수집 배치
status: draft
upstream: [CCR-MS-001, CCR-SEQ-001, CCR-DOM-002, CCR-DOM-003, CCR-INFRA-001, CCR-SCN-001]
---

# 구현 계획 — 대회 수집 배치

## 0. 이 문서가 다루는 것

배치를 어떤 차례의 조각(슬라이스)으로 만들었는지와, 조각마다 무엇을 구현하고 무엇으로 확인했는지다. 함수의 처리는 [[CCR-MS-001]], 흐름은 [[CCR-SEQ-001]]에 있다. 조각은 도메인 경계를 따라 나눴고, 조각 하나가 커밋 하나다. 커밋마다 그 커밋까지의 테스트가 혼자 통과한다. 명세 초안을 코드와 대조한 검증에서 나온 수정은 마지막 커밋 하나에 모았다.

**확인하는 법.** `batch/`에서 `uv run pytest`(네트워크를 쓰지 않는다). 실제 소스에 수집만 해 보려면 `uv run python -m collector collect --show`. 노션 · OpenAI는 미리보기(`python -m collector`, 로컬은 늘 미리보기)로 본다.

**아직 하지 않은 것.** Kaggle 실측(토큰이 없다)과, 노션 · OpenAI 실물로 한 번 돌려 보는 일(시크릿이 없다). 둘 다 사용자가 준비할 것이 있다(4장).

## 1. 슬라이스

#### A 기반

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-INFRA-001]] 3 · 4 · 5.4 · 8.5 · [[CCR-API-001]] 1.1 · 1.2 · 2.1 |
| 구현 | `batch/`의 uv 프로젝트(`pyproject.toml` · `uv.lock` · uv 버전 고정) · `settings.toml` · `core/settings.py`(조정값 · 비밀값 · 실행 문맥) · `core/logging.py`(가리기) · `shared/dates.py` · `shared/text.py` · `infra/http.py` · `infra/robots.py` · `.gitignore` · `.env.example` |
| 구현 함수 | [[CCR-MS-001#RunContext.from_env]] · [[CCR-MS-001#Settings.load]] · [[CCR-MS-001#Secrets.from_env]] · [[CCR-MS-001#settings.read_dotenv]] · [[CCR-MS-001#logging.secret_variants]] · [[CCR-MS-001#logging.register_actions_masks]] · [[CCR-MS-001#SecretFilter.filter]] · [[CCR-MS-001#dates.parse_to_kst_date]] · [[CCR-MS-001#dates.kst_date_of]] · [[CCR-MS-001#dates.kst_midnight_utc]] · [[CCR-MS-001#text.clean_text]] · [[CCR-MS-001#text.html_text]] · [[CCR-MS-001#SourceHttp.fetch]] · [[CCR-MS-001#http.parse_retry_after]] · [[CCR-MS-001#robots.ensure_allowed]] |
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
| 완료 | `993cf0c` · `fe8a3d7`(HTML 대회명은 `html_text`) |

#### B2 기록

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-UC-001#UC-S4]] 2 · [[CCR-UC-001#UC-S7]] · [[CCR-INFRA-001]] 6.2 · [[CCR-DOM-003]] |
| 구현 | `domains/record/` — `HistoryRecord` · `RunLine` · `RecordCrud`(읽기 · 추가분 통째로 쓰기 · main 판 꺼내기) · `RecordService`(남김 수 견주기 · 소스 0건 경고) |
| 구현 함수 | [[CCR-MS-001#RecordService.start]] · [[CCR-MS-001#RecordService.load]] · [[CCR-MS-001#RecordService.history_shrank]] · [[CCR-MS-001#RecordService.append]] · [[CCR-MS-001#RecordService.zero_count_warnings]] · [[CCR-MS-001#RecordService.write_run]] · [[CCR-MS-001#RecordCrud.read_history]] · [[CCR-MS-001#RecordCrud.read_runs]] · [[CCR-MS-001#record._atomic_write]] · [[CCR-MS-001#record.export_main_state]] |
| API | 없음(상태 파일) |
| 화면 | 없음 |
| 테스트 | `tests/domains/record` — 첫 실행 · 읽히지 않는 줄 · 필수 필드 · 남김 감소 · 추가분 통째로 쓰기 · 미리보기는 쓰지 않음 · 줄의 필드 · 소스 0건(연속 · 같은 날 합침 · 실패 건너뜀) · main 판 꺼내기 |
| 선행 | A · B1 |
| 완료 | `cdcd353` · `fe8a3d7`(git이 없거나 시간 초과여도 처리 이력 읽기 실패) |

#### B3 노션

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-UC-001#UC-S4]] 1 · [[CCR-UC-001#UC-S6]] · [[CCR-API-001]] 1.4 · 2.3 |
| 구현 | `infra/notion.py`(읽기 · 쓰기 재시도 규칙 · 초당 3회) · `domains/notion/`(`NotionRow` · `NotionCrud` 네 호출 · `NotionService`) |
| 구현 함수 | [[CCR-MS-001#NotionHttp.read]] · [[CCR-MS-001#NotionHttp.write]] · [[CCR-MS-001#NotionCrud.query_pages]] · [[CCR-MS-001#NotionService.read_rows]] · [[CCR-MS-001#notion.row_of]] · [[CCR-MS-001#NotionService.check_columns]] · [[CCR-MS-001#notion.check_schema]] · [[CCR-MS-001#NotionService.create_row]] · [[CCR-MS-001#notion.properties_of]] |
| API | [[CCR-API-001#GET/api.notion.com/v1/data_sources/{id}]] · [[CCR-API-001#PATCH/api.notion.com/v1/data_sources/{id}]] · [[CCR-API-001#POST/api.notion.com/v1/data_sources/{id}/query]] · [[CCR-API-001#POST/api.notion.com/v1/pages]] |
| 화면 | 노션 `대회목록`(사람이 보는 곳) |
| 테스트 | `tests/infra/test_notion.py` · `tests/domains/notion` — 헤더 · 읽기 재시도 · 4xx 한 번 · 쓰기는 429 · 529 · 닿지 않은 연결 오류만 다시 · 503과 새 행 id · 초당 3회 · 행 읽기 · 커서 · incomplete · 컬럼 확인과 만들기 · 행 값 |
| 선행 | A · B1 |
| 완료 | `0950717` · `fe8a3d7`(503의 `retry_guidance`를 로그에) |

#### B4 선별

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-UC-001#UC-S3]] · [[CCR-UC-001#UC-S4]] · [[CCR-UC-001#UC-S5]] · [[CCR-PRD-001]] 5.2 · [[CCR-SCN-001#S2]] · [[CCR-SCN-001#S3]] · [[CCR-SCN-001#S4]] |
| 구현 | `domains/screen/` — 판정 규칙(`matching.py`) · `ScreenService`(마감 · 묶기 · 아는 대회 · 판별) · `Judge` 포트 · `OpenAiJudge` |
| 구현 함수 | [[CCR-MS-001#matching.normalize_title]] · [[CCR-MS-001#matching.extract_marks]] · [[CCR-MS-001#matching.normalize_link]] · [[CCR-MS-001#matching.similarity]] · [[CCR-MS-001#matching.judge_pair]] · [[CCR-MS-001#matching.group]] · [[CCR-MS-001#matching.representative_order]] · [[CCR-MS-001#ScreenService.drop_expired]] · [[CCR-MS-001#ScreenService.bundle]] · [[CCR-MS-001#ScreenService.build_known]] · [[CCR-MS-001#ScreenService.split_known]] · [[CCR-MS-001#ScreenService._matches]] · [[CCR-MS-001#ScreenService._record_known]] · [[CCR-MS-001#screen.entries_for]] · [[CCR-MS-001#ScreenService.judge]] · [[CCR-MS-001#ScreenService._ask_all]] · [[CCR-MS-001#OpenAiJudge.judge]] · [[CCR-MS-001#openai_judge.build_input]] |
| API | [[CCR-API-001#POST/api.openai.com/v1/responses]] |
| 화면 | 없음 |
| 테스트 | `tests/domains/screen` · `tests/shared/test_text.py` — 정규화 · 연도 · 회차 · 링크 · PRD의 유사도 0.94 · 0.85 재현 · 2 · 3단계로 가르기 · 마감 연장 · 노션 링크와 연도 · 이름만 같음 · 사슬 끊기 · 대표 · 아는 대회와 구성원 기록 · 남김이 버림을 이김 · 판별(버림 · 절반 규칙 · 치명 오류 · 키 없음 · 오늘 마감) · OpenAI 오류 가름 · BOM |
| 선행 | A · B1 · B2 · B3 |
| 완료 | `79c55c9` |

#### B5 실행 흐름

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-UC-001#UC-A1]] · [[CCR-UC-001#UC-S7]] · [[CCR-SCN-001#S1]] · [[CCR-SCN-001#S6]] · [[CCR-SCN-001#S7]] |
| 구현 | `run/pipeline.py`(`Pipeline`) · `__main__.py`(입구 · 신호 · `collect` 하위 명령) |
| 구현 함수 | [[CCR-MS-001#__main__.main]] · [[CCR-MS-001#__main__.run_batch]] · [[CCR-MS-001#__main__.run_collect]] · [[CCR-MS-001#Pipeline.run]] · [[CCR-MS-001#Pipeline._run]] · [[CCR-MS-001#Pipeline._load]] · [[CCR-MS-001#Pipeline._finish]] |
| API | 없음 |
| 화면 | 없음 |
| 테스트 | `tests/run/test_pipeline.py` — 정상 흐름의 건수와 기록 · 미리보기는 아무것도 쓰지 않음 · 설정 누락 · 전 소스 실패 · 노션 읽기 실패 · 처리 이력 읽기 실패 · 처리 이력 감소 · 오늘 마감 행 실패는 실패 · 컬럼 문제 · 키 없음 · 소스 실패 표시 · 신호면 줄 없음. 실측: 로컬에서 설정 없이 돌리면 설정 누락으로 1, Actions에서 `DRY_RUN`이 비면 2 |
| 선행 | B2 · B3 · B4 |
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
| 구현 | `.github/workflows/daily.yml`(예약 08:50 KST · 수동 입력 둘 · 동시성 줄 세우기 · 쓰기 여부와 노션 환경 · 액션 SHA 고정 · [[CCR-INFRA-001]] 8.1의 다섯 차례를 스텝 일곱으로) · `.github/dependabot.yml` · `README.md`(준비 · 운영) · `AGENTS.md`(에이전트 규칙) |
| 구현 함수 | 없음 |
| API | 없음 |
| 화면 | 없음 |
| 테스트 | actionlint 1.7.12(아직 모르는 `concurrency.queue` 한 건을 빼고 통과. GitHub 문서로 `queue: max` · `schedule.timezone`을 확인) · YAML 구문 |
| 선행 | B5 · B6 |
| 완료 | `7a4a002` |

## 2. 통합 테스트

| 시나리오 | 슬라이스 | 검증하는 것 |
|---|---|---|
| [[CCR-SCN-001#S1]] 평소 아침 | B5 | `test_happy_path_loads_keeps_and_records_discards` — 마감 지난 대회 · 노션에 있는 대회 · 버림이 빠지고 남김 하나가 들어가며, 남김 · 버림 · 아는 대회의 구성원이 처리 이력에 적힌다 |
| [[CCR-SCN-001#S2]] 처음 돌리는 날 | B4 | `test_notion_row_keeps_and_wins_over_discard` · 링크가 같은 노션 행 — 손으로 넣은 행과 같은 공고가 빠지고 남김으로 적힌다 |
| [[CCR-SCN-001#S3]] 여러 갈래 | B4 | `test_group_merges_duplicate_notices_across_sources` · `test_representative_prefers_more_dates_then_priority` · 실측 후보 321건의 묶음([[CCR-DOM-002]] 6장 미결) |
| [[CCR-SCN-001#S4]] 관심 없는 대회 | B4 · B5 | 판별 버림 · 절반 규칙 · 키 없음 · 치명 오류 |
| [[CCR-SCN-001#S5]] 소스 하나가 깨짐 | B1 · B5 | 실패 종류 여섯 · `test_failed_source_is_marked_and_run_continues` · 소스 0건 경고 |
| [[CCR-SCN-001#S6]] 실패한 날 다시 | B5 · B6 | 실패 사유 넷 · 오늘 마감 미적재 · 신호로 멈추면 중단 줄 · 이미 올린 실행을 다시 얹지 않음 |
| [[CCR-SCN-001#S7]] 마감이 지남 | B4 | `test_drop_expired_keeps_today_and_unknown_deadlines` — 노션 행은 건드리지 않는다(행을 고치는 호출이 없다) |

실물(노션 · OpenAI · GitHub Actions)로 도는 통합 확인은 시크릿을 넣은 뒤 미리보기 한 번, 그다음 실제 실행 한 번으로 한다(4장).

## 3. 커밋 · PR 목록

| 커밋 | 슬라이스 | 내용 |
|---|---|---|
| `77a61ec` | A | 배치 기반: 설정 · 로그 가리기 · KST 날짜 · 소스 요청 도구 |
| `993cf0c` | B1 | 수집: 여섯 소스 어댑터와 소스별 결과 |
| `cdcd353` | B2 | 기록: 처리 이력 · 실행 요약 읽기와 추가분 쓰기 |
| `0950717` | B3 | 노션: 행 읽기 · 컬럼 확인 · 행 만들기 |
| `79c55c9` | B4 | 선별: 마감 판정 · 같은 대회 묶기 · 아는 대회 가르기 · 관심 분야 판별 |
| `546d3e7` | B5 | 실행 흐름: 하루치를 차례로 돌리고 실행 요약 한 줄을 남긴다 |
| `4f689f6` | B6 | 마무리 단계: 추가분을 main 최신 판 위에 다시 얹어 한 커밋으로 올린다 |
| `7a4a002` | C | 운영: 매일 08:50 KST 워크플로 · Dependabot · 안내 문서 |
| `fe8a3d7` | A · B1 · B2 · B3 | 검증 반영: 본문을 받는 동안에도 시간 예산으로 끊고, 대회명 다듬기를 명세에 맞췄다 |

PR은 [#1](https://github.com/HoyoungParkme/competition-crawler/pull/1) 하나다(`feat/batch` → `main`). 위 커밋 해시를 그대로 남기려고 병합 커밋으로 합친다.

## 4. 미결사항

- [ ] **사용자가 준비할 것.** GitHub 환경 `notion-write` · `notion-read`와 각 `NOTION_TOKEN`, 저장소 시크릿 `NOTION_DATA_SOURCE_ID` · `OPENAI_API_KEY`(· `KAGGLE_API_TOKEN`), 규칙셋(강제 push 차단 · 삭제 제한), 액션 SHA 고정 요구, 실패 알림. 순서는 `README.md`
- [ ] **실물 확인.** 시크릿을 넣은 뒤 `main`에서 미리보기(`dry_run`) 한 번으로 노션 읽기 · 컬럼 확인 · 판별을 보고, 그다음 수동 실행 한 번으로 행 만들기와 마무리 단계의 커밋을 본다
- [ ] **Kaggle 실측.** 토큰이 생기면 [[CCR-API-001]] 5장대로 실측하고 `kaggle.py`와 테스트를 맞춘다
- [ ] **같은 대회 판정 규칙.** [[CCR-DOM-002]] 6장. 규칙이 바뀌면 B4에 조각 하나를 더한다
