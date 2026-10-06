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

세 시기가 있다. **A ~ C**는 2026-09-24 ~ 09-28에 노션 `대회목록`에 넣는 배치로 만들어 병합한 것이다. 조각 하나가 커밋 하나였고 PR 둘로 합쳤다(3장). **D1 ~ D3**은 2026-09-29의 결정(노션 대신 우리 페이지)에 따라 새로 만드는 것이다. 카드마다 브랜치와 PR 하나, 함수 하나가 커밋 하나다(`code(D1): 함수 — 요약`, 싱크독 개발 규약 SYNC-STD-004 DEV-13 · DEV-15). **D4** · **D5**는 2026-10-01의 사용자 요청(쪽 나누기와 칸 · 버튼 크기, 미참 · 별표와 상태 색)으로 더한 카드다. 병합은 사용자가 웹에서 읽고 난 뒤에 한다. **E1** · **E2**는 2026-10-06의 사용자 결정(GitHub를 빼고 노트북에서 돌린다 — 일배치는 노트북 cron, 목록 페이지는 노트북 페이지 서버)으로 더한 카드다. 원본이 싱크독 서버 저장소라 PR이 없다. 카드마다 브랜치 하나이고 커밋은 `code(E1): 함수 — 요약` 꼴이다. 끝나면 `--no-ff`로 `main`에 합쳐 원본에 push한다. 완료란은 「`code/e1-laptop-batch` → `main` · 병합 `해시` · YYYY-MM-DD. 커밋 n개」 꼴이다.

**확인하는 법.** 배치는 `batch/`에서 `uv run pytest`(네트워크를 쓰지 않는다) · `uv run ruff check .` · `uv run ruff format --check .`. 실제 소스에 수집만 해 보려면 `uv run python -m collector collect --show`. 판별까지는 미리보기(`python -m collector`, 노트북 실행기 밖은 늘 미리보기)로 본다. 실행기 안의 미리보기는 `scripts/daily.sh --manual --dry-run`이다. 페이지는 `frontend/`에서 `npm test`(vitest, 순수 모듈만) · `npm run build`. 페이지 서버는 `batch/`의 pytest가 임시 bare 저장소를 원본으로 삼아 띄워 본다. 명세와 코드의 대조는 싱크독 `tools/check_code.py`(MS 시그니처 · docstring ID)와 `tools/check_ui.py`(`data-el` 번호)로 한다(DEV-14).

**아직 하지 않은 것.** 노트북으로 옮기는 E1 · E2다. 사용자가 켜기로 했던 GitHub의 실패 알림은 E1의 윈도 알림(`scripts/notify.sh`)으로 바뀐다(4장). Kaggle은 2026-10-01에 토큰을 받아 실측하고 fix(#21) · fix(#23)로 맞췄다. 페이지의 실물 확인도 같은 날 마쳤다(4장). D1 · D2 · D3은 2026-09-30에 병합했고, 같은 날 예약 실행이 처음으로 목록 파일을 만들었다. 노션 환경 둘과 시크릿도 같은 날 지웠다. 페이지의 실제 저장 코드는 같은 날 확인 커밋 둘로 돌려 봤다(4장).

## 1. 슬라이스

#### A 기반

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-INFRA-001]] 3 · 4 · 5.4 · 8.5 · [[CCR-API-001]] 1.1 · 1.2 · 2.1 |
| 구현 | `batch/`의 uv 프로젝트(`pyproject.toml` · `uv.lock` · uv 버전 고정) · `settings.toml` · `core/settings.py`(조정값 · 비밀값 · 실행 문맥) · `core/logging.py`(가리기) · `shared/dates.py` · `shared/text.py` · `infra/http.py` · `infra/robots.py` · `.gitignore` · `.env.example`. 노션 ID의 두 표기를 만들던 `secret_variants`는 D1에서 뺀다 |
| 구현 함수 | [[CCR-MS-001#RunContext.from_env]] · [[CCR-MS-001#Settings.load]] · [[CCR-MS-001#Secrets.from_env]] · [[CCR-MS-001#settings.read_dotenv]] · `logging.register_actions_masks`(2026-10-06에 지움) · [[CCR-MS-001#SecretFilter.filter]] · [[CCR-MS-001#dates.parse_to_kst_date]] · [[CCR-MS-001#dates.kst_date_of]] · [[CCR-MS-001#dates.kst_midnight_utc]] · [[CCR-MS-001#text.clean_text]] · [[CCR-MS-001#text.html_text]] · [[CCR-MS-001#SourceHttp.fetch]] · [[CCR-MS-001#http.parse_retry_after]] · [[CCR-MS-001#robots.ensure_allowed]] |
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
| 구현 함수 | [[CCR-MS-001#ListEntry.id]] · [[CCR-MS-001#ListEntry.to_dict]] · [[CCR-MS-001#ListEntry.from_dict]] · [[CCR-MS-001#list.entry_of]] · [[CCR-MS-001#ListService.load]] · [[CCR-MS-001#ListFile.ids]] · [[CCR-MS-001#ListService.append]] · [[CCR-MS-001#ListService.appended_count]] · [[CCR-MS-001#ListCrud.read]] · [[CCR-MS-001#ListCrud.reset_appends]] · [[CCR-MS-001#ListCrud.write_appends]] · [[CCR-MS-001#matching.key_of_entry]] · [[CCR-MS-001#ScreenService.build_known]] · [[CCR-MS-001#Pipeline._run]] · [[CCR-MS-001#Pipeline._load]] · [[CCR-MS-001#__main__.run_batch]] · [[CCR-MS-001#RecordService.start]] · [[CCR-MS-001#RecordService.load]] · [[CCR-MS-001#record.export_main_state]] · [[CCR-MS-001#Secrets.from_env]] · [[CCR-MS-001#Settings.load]] · `logging.register_actions_masks`(2026-10-06에 지움) · [[CCR-MS-001#finish.finish]] · [[CCR-MS-001#finish.read_additions]] · [[CCR-MS-001#finish.existing_ids]] · [[CCR-MS-001#Git.commit_and_push]] |
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
| 구현 함수 | MS 밖(TypeScript). 모듈과 시그니처는 [[CCR-DOM-002#CompetitionList]] · `SettingsDialog`(2026-10-06에 지움) · [[CCR-DOM-002#StatusStore]] · [[CCR-DOM-002#RepoFiles]] · `TokenStore`(2026-10-06에 지움) |
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
| 테스트 | actionlint · YAML 구문 · `pages.yml`이 `frontend/`만 바뀐 push에 돌고 `data/`만 바뀐 커밋에는 돌지 않음(첫 배포 뒤 실측) · 페이지가 `https://hoyoungparkme.github.io/competition-crawler/`에서 열림 · 수동 실행 한 번으로 미리보기 · 실제 실행이 환경 없이 돎. 결과(2026-09-30): actionlint 1.7.12로 `pages.yml` 0건, `daily.yml`은 C 때부터 알던 `concurrency.queue` 한 건. `git archive`로 꺼낸 깨끗한 `frontend/`에서 Node 24 · `npm ci` · `npm run build` 통과(자산 경로 `/competition-crawler/assets/…`). 병합 커밋이 돌린 첫 배포(실행 36660069757)가 모든 스텝 성공, 주소가 200을 내고 목록 49건을 그린다. 병합 뒤 `main`의 미리보기(실행 36660197145)가 환경 없이 성공했다 — 마무리 스텝은 건너뛰었고 노션 환경의 배포 기록이 새로 생기지 않았다. 후보 332건 · 묶음 264개가 모두 아는 대회라 판별 0건, 46.2초. `data/`만 바뀐 커밋에 `pages.yml`이 돌지 않는지와 환경 없는 실제 실행은 다음 예약 실행(2026-10-01)에서 본다. 2026-10-01 예약 실행에서 둘 다 확인했다(4장) |
| 선행 | D2 |
| 완료 | [#9](https://github.com/HoyoungParkme/competition-crawler/pull/9)(`code/d3-pages` → `main`) · 병합 `2b820b6` · 2026-09-30. 커밋 4개(3장). Pages는 병합 전에 API로 켰다(소스 GitHub Actions). GitHub가 만든 배포 환경 `github-pages`는 `main`에서만 배포를 받는다. `pages.yml`의 잡은 이 환경으로 배포한다(deploy-pages의 요구). [[CCR-INFRA-001]] v6이 5.1의 예외와 8.11 표에 적었다. 잡 시간 한도 10분을 더했다. 노션 환경 둘과 시크릿 `NOTION_DATA_SOURCE_ID`는 사용자 결정으로 2026-09-30에 지웠다. 남은 환경은 `github-pages` 하나, 저장소 시크릿은 `OPENAI_API_KEY` 하나다 |

#### D4 쪽 나누기와 칸 · 버튼 크기

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-UI-001#UI-1]] 3 · 7 · 9 · 13 · 13.1 ~ 13.5 · S-6 · [[CCR-UI-001]] 3장 · [[CCR-DOM-002]] 1 · 2.4 · 3.2 · 4.11. 사용자 요청(2026-10-01)이고, 고친 안의 화면을 보고 사용자가 골랐다 |
| 구현 | `components/Pager.tsx` 신설(쪽 나누기 줄 · `paginate` · `pageOfRow` · `PAGE_SIZES` · `DEFAULT_PAGE_SIZE`). `CompetitionTable`은 지금 쪽의 줄만 받아 그리고, 접힌 줄의 표시를 줄의 값(`expired` · `hidden`)으로 정하며, 쪽 나누기 줄을 표와 접힌 구역 사이에 둔다. 칸 너비는 132 · 136 · 84 · 116 · 108px. `CompetitionList`는 쪽 상태(`page` · `pageSize`)와 쪽 이동(거르기 · 개수 · 넘기기 · 펼치기), 개수 기억(`ccr.pageSize`). `styles.css` — 칸 여백 12px 16px, 표 안의 조작 36px(`--control-height-row`), 머리 · 거르기 · 쪽 나누기의 조작 40px, 쪽 나누기 줄, 줄을 가리킬 때의 색, 키보드 포커스 테두리 |
| 구현 함수 | MS 밖(TypeScript). [[CCR-DOM-002#CompetitionList]] |
| API | 없음 |
| 화면 | [[CCR-UI-001#UI-1]] |
| 테스트 | `tests/components/Pager.test.ts` — `paginate`(첫 쪽 · 마지막 쪽의 남은 줄 · 넘친 쪽은 마지막 쪽으로 · 1보다 작으면 첫 쪽으로 · 빈 목록) · `pageOfRow`. `npm test` · `npm run lint` · `npm run build`, `check_ui.py` UI-1 요소 33. 로컬 미리보기에서 넘기기 · 개수 바꾸기 · 펼치기 · 거르기와 폰 폭(390px)을 본다. 커밋 전에 미리 본 결과(2026-10-01): 쪽 이동이 모두 UI 명세대로였고, 1280px 화면에서 대회명 칸 607px · 줄 높이 평균 78px · 지우기 59×36px · 머리와 거르기의 조작 40px, 390px에서는 가로로 넘치지 않았다. 커밋 뒤: `npm test` 34 통과(`Pager.test.ts` 7개를 더했다) · `npm run lint` · `npm run build` 통과, `check_ui.py` UI-1 요소 33 · 일치 33, UI-2 9 · 9 |
| 선행 | D2 · D3 |
| 완료 | [#19](https://github.com/HoyoungParkme/competition-crawler/pull/19)(`code/d4-pager` → `main`) · 병합 `4717c58` · 2026-10-01. 커밋 4개(3장). 병합이 돌린 페이지 배포(실행 36800025511)가 성공했고, 배포된 페이지에서 20줄 · 쪽 나누기 줄 · 칸 너비 132 · 607 · 136 · 84 · 116 · 108px · 표 안의 조작 36px · 머리와 거르기의 조작 40px을 확인했다 |

#### D5 미참 · 별표와 상태 색

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-PRD-001#R10]] · [[CCR-UC-001#UC-A2]] 2 · 4 · [[CCR-UC-001#UC-H1]] 1 · 1c · 3 · 5 · [[CCR-UI-001#UI-1]] 3 · 7 · 7.4 · 7.7 · 11 · S-7 · [[CCR-UI-001]] 3장 · [[CCR-DOM-001#Status]] · [[CCR-DOM-003#status]] · [[CCR-API-001]] 1.4 · 4.2 · [[CCR-DOM-002]] 2.1 · 2.3 · 2.4 · 4.11 · [[CCR-SEQ-001#SEQ-11]]. 사용자 요청(2026-10-01)이고, 근거는 RFQ를 고치지 않고 PRD에 적기로 사용자가 골랐다 |
| 구현 | `domain/types.ts`(`skipped` · `미참`, `Status.starred`, `DEFAULT_STATUS`) · `api/data.ts`(`starred`가 없거나 불 값이 아니면 `false`) · `store/status.ts`(`star` · `unstar`, `mergeChange` · `commitMessage`) · `components/FilterBar.tsx`(3.4 별표만 보기, `Filters.starredOnly`) · `components/CompetitionTable.tsx`(7.7 별표 단추, 미참 줄) · `pages/CompetitionList.tsx`(별표만 거르기, `onStar`) · `styles.css`(상태 다섯의 색, 미참 줄의 흐림, 별표) |
| 구현 함수 | MS 밖(TypeScript). [[CCR-DOM-002#CompetitionList]] · [[CCR-DOM-002#StatusStore]] · [[CCR-DOM-002#RepoFiles]] |
| API | [[CCR-API-001#PUT/api.github.com/…/contents/data/status.json]] — 값에 `starred`가 붙고 커밋 메시지가 두 꼴 는다 |
| 화면 | [[CCR-UI-001#UI-1]] |
| 테스트 | `tests/api/data.test.ts` — `skipped`를 읽는다 · `starred`가 없거나 불 값이 아니면 `false`. `tests/store/status.test.ts` — `mergeChange`의 별표 붙이기 · 떼기(다른 값은 그대로) · `commitMessage`의 `별표` · `별표 뗌` · `미참`. `npm test` · `npm run lint` · `npm run build`, `check_ui.py` UI-1 요소 35. 로컬 미리보기에서 별표 · 별표만 보기 · 미참 줄 · 다섯 색을 본다. 실제 저장은 사용자가 브라우저에서 한다. 커밋 뒤: `npm test` 36 통과(새로 2개, `commitMessage`에 단언 셋을 더했다) · `npm run lint` · `npm run build` 통과, `check_ui.py` UI-1 요소 35 · 일치 35, UI-2 9 · 9. 로컬 미리보기에서 상태 파일 응답만 가짜로 바꿔(읽기만) 다섯 색 · 별표 · 미참 줄의 흐림 · 별표만 보기(3건, `3개 중 1–3`)를 봤고, 토큰 없이 별표를 누르면 값은 그대로이고 토큰 없음(11)이 떴다 |
| 선행 | D4 |
| 완료 | [#20](https://github.com/HoyoungParkme/competition-crawler/pull/20)(`code/d5-skip-star` → `main`) · 병합 `96b081e` · 2026-10-01. 커밋 7개(3장). 병합이 돌린 페이지 배포(실행 36804148774)가 성공했고, 배포된 페이지에서 상태 셀렉트와 거르기의 `미참`, 별표만 보기(3.4), 줄마다 별표(7.7)를 확인했다. 별표의 실제 저장은 사용자가 브라우저에서 한다 |

#### E1 노트북 일배치

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-RFQ-001#Q5]] · [[CCR-RFQ-001#Q6]] · [[CCR-RFQ-001#Q9]] · [[CCR-RFQ-001#Q10]] · [[CCR-PRD-001#R7]] · [[CCR-PRD-001#R8]] · [[CCR-INFRA-001#C1]] · [[CCR-INFRA-001#C2]] · [[CCR-INFRA-001#C3]] · [[CCR-INFRA-001#C11]] · [[CCR-INFRA-001#C12]] · [[CCR-INFRA-001]] 4.1 · 5 · 5.4 · 5.5 · 5.6 · 6.3 · 8.1 · 8.2 · 8.6 · 8.7 · [[CCR-UC-001#UC-A1]] 1b5 · 1b7 · \*a · [[CCR-SEQ-001#SEQ-1]] · [[CCR-SEQ-001#SEQ-7]] · [[CCR-SEQ-001#SEQ-8]] · [[CCR-SEQ-001#SEQ-10]]. 사용자 결정 2026-10-06 — 노트북 cron · 윈도 알림 |
| 구현 | 배치 — `core/settings.py`(`RunContext`의 `in_actions` → `in_runner`, 입력 `BATCH_RUNNER` · `RUN_KIND` · `WORK_DIR`. `GITHUB_ACTIONS` · `GITHUB_REF` · `GITHUB_EVENT_NAME` · `RUNNER_TEMP`는 읽지 않는다) · `__main__.py`(실행기 밖만 `.env`를 읽고, Actions에 가릴 값 알리기를 뺀다) · `core/logging.py`(`register_actions_masks` 지움) · `finish.py`(`RUN_KIND` · `WORK_DIR` · `REMOTE_URL` · `PUSH_TOKEN`, 작성자 · 커미터 `ccr-batch <ccr-batch@localhost>`) · `infra/http.py`(User-Agent에서 GitHub 주소를 뺀 `competition-crawler/<버전>`). 실행기 — `scripts/daily.sh`(노트북 실행기. 줄 서기 15분 · `batch.env` 읽기 · 시작 시각과 `RUN_ID` · 원본 `main`을 얕게 받아 받은 쪽의 실행기로 넘기기 · 오늘 것 확인 · `uv sync --frozen --no-dev` · 배치 8분 · 마무리 3분 · 실행 로그와 90일 지난 로그 지우기 · 실패 알림 · 끊기, [[CCR-INFRA-001]] 8.1) · `scripts/notify.sh`(윈도 알림 — `powershell.exe -EncodedCommand`, 한글이 깨지지 않게 UTF-16LE Base64). `.github/`(`daily.yml` · `pages.yml` · `dependabot.yml`)를 지운다. `README.md` · `AGENTS.md`(실행기 · `batch.env` · crontab 줄 · 손 실행). 노트북 설정: `~/.config/ccr/batch.env`(권한 600)와 crontab `50 8-23 * * *`. GitHub 쪽 정리(운영) — Actions 시크릿 둘을 지우고 저장소를 보관한다. 옛 fine-grained 페이지 토큰은 사람이 GitHub 설정에서 폐기한다 |
| 구현 함수 | [[CCR-MS-001#RunContext.from_env]] · [[CCR-MS-001#__main__.main]] · [[CCR-MS-001#finish.finish]] · [[CCR-MS-001#Git.commit_and_push]] · [[CCR-MS-001#finish.main]]. `logging.register_actions_masks`는 코드와 MS 항목을 함께 지운다. 글만 고친 MS 항목(코드는 그대로): [[CCR-MS-001#Secrets.from_env]] · [[CCR-MS-001#Secrets.values]] · [[CCR-MS-001#settings.read_dotenv]] · [[CCR-MS-001#RecordService.start]] |
| API | 없음(git). 원본은 싱크독 git 입구다([[CCR-INFRA-001]] 5.5) |
| 화면 | 없음 |
| 테스트 | `tests/core/test_settings.py` — 실행기 묶음(쓰기 · KST 기준일 · 종류 · 실행 식별자 · 받은 main · `WORK_DIR/append`) · 실행기 안에서 깨진 `DRY_RUN`은 `RunModeError` · 실행기 밖은 쓰지 않고 main 판을 꺼냄 · 옛 `GITHUB_ACTIONS` · `CI` 표시로는 쓰지 않음 · 실행기 안의 미리보기 · `RUN_KIND`. `tests/run/test_pipeline.py`의 `context()`를 실행기 환경으로. `tests/core/test_logging.py`에서 가릴 값 알리기의 테스트를 지운다. `tests/test_finish.py` — 작성자 · 커미터 `ccr-batch <ccr-batch@localhost>` · `finish.main`은 네 이름 가운데 하나라도 없으면 1 · 실행기가 넘긴 원격 · 작업 폴더 · 종류로 올리고 토큰을 찍지 않음. `uv run ruff check .` · `uv run ruff format --check .`, 싱크독 `check_code.py`. 실물: 노트북에서 손 실행(미리보기 · 쓰기) · 예약 실행 뒤 같은 날 두 번째 예약의 건너뜀 · Ctrl-C로 끊기 · 윈도 알림 시험(한글 제목과 본문) · 실제 원본(싱크독 git 입구)으로 crontab의 첫 예약 실행과 `ccr-batch` 커밋. 커밋 전에 본 결과(2026-10-06, 임시 bare 저장소를 원본으로): 미리보기 · 손 실행 · 예약 실행 뒤 건너뜀이 돌았고, Ctrl-C로 끊으면 배치가 130으로 끝나고 마무리 단계가 중단 줄(`aborted`)을 썼으며 알림은 뜨지 않았다 |
| 선행 | D5 |
| 완료 | `code/e1-laptop-batch` → `main` · 병합 `8116635` · 2026-10-06. 커밋 7개(3장). 임시 bare 원격으로 미리보기 · 손 실행(`ccr-batch` 커밋) · 예약 실행 뒤 같은 날 건너뜀 · Ctrl-C 끊기(배치 130 → 마무리가 중단 줄, 알림 없음)를 돌려 봤다. 원본(싱크독 git 입구)으로 미리보기와 손 실행 한 번(`local-20261006T132730`, 커밋 `4f1fd64`, 싱크독이 읽음)을 했다. crontab `50 8-23 * * *`을 넣고, GitHub daily를 끈 뒤 Actions 시크릿 둘을 지우고 저장소를 보관했다. OpenAI · Kaggle 키는 아직 `batch.env`에 없어 그 실행은 판별을 미루고(6묶음) Kaggle을 건너뛰었다 — 사람이 넣는다. 08:50 예약 실행은 2026-10-07에 처음 돈다 |

#### E2 노트북 페이지

| 항목 | 내용 |
|---|---|
| 근거 | [[CCR-RFQ-001#Q3]] · [[CCR-RFQ-001#Q7]] · [[CCR-RFQ-001#Q16]] · [[CCR-PRD-001#R10]] · [[CCR-INFRA-001#C14]] · [[CCR-INFRA-001]] 4.1 · 5.5 · 5.8 · 6.4 · 8.11 · [[CCR-UC-001#UC-A2]] · [[CCR-UC-001#UC-H1]] · [[CCR-UI-001#UI-1]] · [[CCR-API-001]] 1.4 · 2.3 · 3.3 · [[CCR-DOM-002]] 4.11 · [[CCR-SEQ-001#SEQ-11]]. UC-H2 · UI-2 · SEQ-12는 2026-10-06에 폐기했다. 사용자 결정 2026-10-06 — 노트북에서 살린다 · 늘 떠 있게 |
| 구현 | `batch/page_server.py`(노트북 페이지 서버 — 표준 라이브러리와 git만. 원본의 bare 사본 `~/.local/share/ccr/page.git` · `127.0.0.1:8090` · Host · Origin 지킴 · 빌드된 정적 파일 · 두 데이터 파일 · 상태 파일의 판 읽기와 쓰기. `http.server`의 훅 `do_GET` · `do_PUT`은 `serve_get` · `serve_put`을 부르기만 하고 MS 항목이 없다) · `scripts/page.sh`(crontab `@reboot` · `*/5 * * * *`. 떠 있지 않으면 띄운다. 원본 `main`의 `frontend/` 트리가 지난 빌드와 다르면 `npm ci && npm run build` 뒤 다시 띄우고, `batch/page_server.py`가 바뀌어도 다시 띄운다. 빌드가 실패하면 이전 빌드를 내고 윈도 알림 「CCR 페이지 빌드 실패」. 기록 `~/.local/state/ccr/page.log`). frontend — `config.ts`(`OWNER` · `REPO` · `RAW_BASE` · `API_BASE`를 지우고 `dataUrl(file)`(같은 출처 `/data/…?t=`) · `CONTENTS_URL = '/api/contents/data/status.json'`. `COMMIT_AUTHOR`는 그대로) · `api/data.ts`(같은 출처 `/data/…?t=`) · `api/github.ts` → `api/contents.ts`(`ContentsError` · `readStatusVersion()` · `writeStatusFile(file, sha, message)`, 토큰 인자 없음) · `store/status.ts`(`StatusStore(api, onChange)` · `ContentsApi`) · `store/token.ts` · `components/SettingsDialog.tsx` 지움 · 화면에서 설정(6) · 토큰 없음(11 · 11.1) · 「설정 열기」(12.1)를 빼고 저장 실패 문구를 「페이지 서버 · 싱크독에 닿지 못했다」 꼴로 · `vite.config.ts`(`base: '/'`) · `README.md`. 옛 페이지 토큰은 사람이 GitHub 설정에서 폐기한다 |
| 구현 함수 | [[CCR-MS-001#Mirror.refresh]] · [[CCR-MS-001#Mirror.read]] · [[CCR-MS-001#Mirror.write]] · [[CCR-MS-001#page_server.allowed]] · [[CCR-MS-001#PageHandler.serve_get]] · [[CCR-MS-001#PageHandler.serve_put]] · [[CCR-MS-001#page_server.main]]. 페이지는 MS 밖(TypeScript) — [[CCR-DOM-002#CompetitionList]] · [[CCR-DOM-002#StatusStore]] · [[CCR-DOM-002#RepoFiles]] |
| API | [[CCR-API-001]] 3.3 — 페이지 서버의 `GET /data/{file}` · `GET /api/contents/data/status.json` · `PUT /api/contents/data/status.json` |
| 화면 | [[CCR-UI-001#UI-1]] 대회 목록(설정 · 토큰 없음 · 「설정 열기」를 뺀다) |
| 테스트 | `batch/tests/test_page_server.py`(임시 bare 저장소를 원본으로 서버를 띄운다) — 두 데이터 파일을 캐시 없이 · 판 읽기의 블롭 해시와 Base64 · 맞는 판이면 그 파일만 바꾼 커밋 하나(작성자 · 커미터 · 곧바로 보임) · 어긋난 판 409와 판 없음 422는 아무것도 올리지 않음 · 첫 쓰기가 파일을 만듦(201) · 그사이 배치가 push하면 다시 얹음 · Host · Origin 지킴 · 정적 파일과 틀린 요청(폴더 밖 · 다른 경로 · Base64 아님 · `message` 없음) · 원본이 사라지면 마지막 판을 내고 쓰기는 502(토큰이 새지 않음). `frontend/tests/` — `api/contents.test.ts`(옛 `github.test.ts`, 토큰 없이 같은 출처로) · `store/status.test.ts` · `pages/CompetitionList.test.ts`(토큰 갈래의 테스트를 지운다). `npm test` · `npm run lint` · `npm run build`, 싱크독 `check_code.py` · `check_ui.py`(UI-1). 사람이 노트북 브라우저에서 `http://localhost:8090`을 열어 요소 번호대로 눌러 본다(DEV-17) — 상태 · 지우기 · 되살리기 · 별표가 원본에 커밋되고 새로 고침에 곧바로 보인다. `scripts/page.sh`의 다시 띄우기 · 다시 빌드 · 빌드 실패 알림 |
| 선행 | E1 |
| 완료 | `code/e2-laptop-page` → `main` · 병합 `2a1b2ac` · 2026-10-06. 커밋 8개(3장). 페이지 서버 pytest 10 · vitest 33 · tsc · eslint · prettier · 빌드 · check_code 142/142 · check_ui UI-1 31/31. 임시 bare 원격으로 `page.sh`를 돌려 빌드 · 띄우기 · PUT 커밋 · Origin 없는 PUT 403 · 다시 불러도 그대로 · 토큰이 바뀌면 다시 띄움을 봤다. crontab `@reboot` · `*/5`를 넣고, 노트북 브라우저로 http://localhost:8090 을 열어 열린 대회 42 · 거르기 · 쪽 나누기 · 바닥 줄(「싱크독 CCR · main」)을 보고, 별표 붙이기 · 떼기가 원본 커밋 둘(`7f89639` · `b1cf44c`)로 남아 곧바로 보이는 것을 확인했다(콘솔 오류 0, 싱크독이 읽음) |

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
| [[CCR-SCN-001#S8]] 페이지에서 상태를 바꾼다 | D2 | `mergeChange` · `commitMessage` · `encodeStatusFile` · `writeStatusFile`이 보내는 작성자(fix(#12)) · `readStatusForView`의 세 갈래(fix(#14))의 vitest. 화면은 사용자가 요소 번호대로 확인한다. 실물은 확인 커밋 둘(4장) |
| [[CCR-SCN-001#S1]] 평소 아침 · [[CCR-SCN-001#S6]] 실패한 날 다시 — 노트북 실행기 | E1 | `test_settings.py`의 실행기 묶음 · `test_finish.py`의 `finish.main`(실행기가 넘긴 원격 · 작업 폴더 · 종류). 실물은 노트북에서 손 실행 · 같은 날 두 번째 예약의 건너뜀 · Ctrl-C로 끊으면 중단 줄 · 실패면 윈도 알림 · crontab의 첫 예약 실행(E1 테스트) |
| [[CCR-SCN-001#S8]] 페이지에서 상태를 바꾼다 — 노트북 페이지 서버 | E2 | `test_page_server.py` — 판이 맞으면 그 파일만 바꾼 커밋 · 다른 탭이나 브라우저가 먼저 썼으면 409 · 그사이 배치가 push하면 다시 얹음 · Host · Origin 지킴. vitest(`contents.test.ts` · `status.test.ts`). 화면은 사용자가 노트북 브라우저에서 요소 번호대로 확인한다 |

실물(노트북 실행기 · OpenAI · 노트북 페이지 서버 · 싱크독 git 입구)로 도는 통합 확인은 4장의 차례로 한다. 2026-10-06까지는 GitHub Actions · Pages · Contents API로 했다.

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
| `eaa57b1` | fix(#12) · D2 | `COMMIT_AUTHOR` — 상태 커밋의 작성자를 저장소 주인의 noreply 주소로 둔다. 이슈 #12 |
| `233223b` | fix(#12) · D2 | `writeStatusFile` — author · committer를 보내 개인 이메일이 공개 커밋에 남지 않게 한다. 이슈 #12 |
| `fe9c018` | fix(#14) · D2 | `readStatusForView` — 토큰이 있으면 상태 파일을 판 읽기로 받고, 실패하면 raw로. 이슈 #14 |
| `bcbe061` | fix(#14) · D2 | `CompetitionList` — 페이지를 열 때와 새로 고칠 때 상태 파일을 `readStatusForView`로 읽는다. 이슈 #14 |
| `8f8fe0a` | fix(#14) · D2 | `README.md` — 로컬 페이지도 상태 파일은 토큰이 있으면 Contents API로 읽는다. 이슈 #14 |
| `b9a6c02` | fix(#17) · D2 | `styles.css` 토큰 — 본문 16px · 보조 글 14px · 표 머리 · 칩 · 바닥 줄 13px · 날짜 15px, 회색을 `#45423a` · `#57534a`로 진하게. 이슈 #17 |
| `145bfae` | fix(#17) · D2 | `styles.css` 대회명 링크 — `#174a54`로 굵게(600), 밑줄은 가리킬 때만. 이슈 #17 |
| `826a530` | fix(#17) · D2 | `styles.css` 상태 셀렉트 — 최소 높이를 36px에서 40px로. 이슈 #17 |
| `e8cd761` | D4 | `Pager` — 쪽 나누기 줄(13)과 `paginate` · `pageOfRow`, 테스트 |
| `631414d` | D4 | `CompetitionTable` — 지금 쪽의 줄만 그리고 쪽 나누기 줄을 표 아래에, 칸 너비를 글에 맞춤 |
| `971a9a9` | D4 | `CompetitionList` — 쪽 상태와 개수 기억, 거르기 · 개수 · 넘기기 · 펼치기의 쪽 이동 |
| `b813b81` | D4 | `styles.css` — 칸 여백 · 표 안 조작 36px · 머리와 거르기 조작 40px · 쪽 나누기 줄 · 포커스 테두리 |
| `3afe1e4` | D5 | `types` — 미참(`skipped`)과 별표(`starred`) |
| `a1c9206` | D5 | `parseStatusFile` — `starred`가 없거나 불 값이 아니면 `false`, 테스트 |
| `fecee63` | D5 | `StatusStore` — `star` · `unstar`와 별표 커밋 메시지, 테스트 |
| `9d53d00` | D5 | `FilterBar` — 별표만 보기(3.4) |
| `c5352f1` | D5 | `CompetitionTable` — 별표 단추(7.7)와 미참 줄 |
| `efeed2c` | D5 | `CompetitionList` — 별표만 거르기와 `onStar` |
| `32f7698` | D5 | `styles.css` — 상태 다섯의 색 · 미참 줄 · 별표 |
| `9d25c60` | fix(#21) · A | `http.new_client` — 소스가 심는 쿠키를 남기지 않는 클라이언트, 테스트의 가짜 HTTP도 같은 클라이언트로. 이슈 #21 |
| `f5af5a4` | fix(#21) · B1 | `KaggleSource.collect` — `page`로 넘기고 빈 쪽에서 멈춘다, `parse_page`는 대회 목록만. 2026-10-01에 저장한 실제 응답 두 쪽으로 테스트. 이슈 #21 |
| `82212ac` | fix(#23) · B4 | `matching.judge_pair` — Kaggle끼리는 원천 ID가 다르면 1단계에서 다른 대회. 이슈 #23 |
| `5d9b9f1` | E1 | `RunContext.from_env` — 노트북 실행기 안(`BATCH_RUNNER=laptop`)에서만 쓴다, 테스트 |
| `bc2ee6e` | E1 | `__main__.main` — 실행기 안에서는 `.env`를 읽지 않고 `register_actions_masks`를 지운다 |
| `3cab11c` | E1 | `finish.main` · `finish.finish` · `Git.commit_and_push` — 실행기가 넘긴 원격 · 토큰 · 작업 폴더, 작성자 `ccr-batch`, 테스트 |
| `915ee24` | E1 | `USER_AGENT` — GitHub 주소를 뺀다 |
| `9b4b5f5` | E1 | `scripts/daily.sh` · `notify.sh` — 노트북 실행기와 윈도 알림 |
| `bcf955e` | E1 | `.github` 지움 — `daily.yml` · `pages.yml` · `dependabot.yml` |
| `4d6985b` | E1 | `README.md` · `AGENTS.md` — 노트북에서 돌리는 법 |
| `23698bb` | E2 | `page_server.py` — 노트북 페이지 서버(`Mirror` · `allowed` · `PageHandler` · `main`), 테스트 |
| `9645962` | E2 | `scripts/page.sh` — 늘 띄우고, main의 frontend나 페이지 서버가 바뀌면 다시 빌드 |
| `ae250f0` | E2 | `contents.ts` · `data.ts` · `config.ts` — GitHub raw · Contents API 대신 같은 출처의 페이지 서버, 테스트 |
| `595585c` | E2 | `StatusStore` — 토큰 없이 `ContentsApi`로, 테스트 |
| `6285ed9` | E2 | `CompetitionList` · `Notice` — 설정 · 토큰 요소(6 · 11 · 11.1 · 12.1)를 빼고 문구를 페이지 서버로, 테스트 |
| `4ed5ed5` | E2 | `SettingsDialog` · `TokenStore` 지움 — UI-2 폐기 |
| `4052f92` | E2 | `vite.config.ts` — `base: '/'` |
| `5c2fd2d` | E2 | `README.md` · `AGENTS.md` — 노트북 페이지(localhost:8090)와 `page.sh` crontab |

PR은 둘이다. [#1](https://github.com/HoyoungParkme/competition-crawler/pull/1)(`feat/batch` → `main`)은 A ~ C와 검증 반영을, [#2](https://github.com/HoyoungParkme/competition-crawler/pull/2)(`fix/matching-wevity` → `main`)는 fix(#3) · fix(#4)를 담았다. 위 커밋 해시를 그대로 남기려고 둘 다 병합 커밋으로 합쳤다. 이 둘은 규약 DEV-13 · DEV-15보다 앞서 만든 것이라 커밋 메시지의 꼴이 다르다. 이력은 고치지 않는다.

D1 ~ D3은 카드마다 브랜치 · PR 하나이고, 커밋은 `code(D1): 함수 — 요약` 꼴로 함수 하나에 하나다. [#7](https://github.com/HoyoungParkme/competition-crawler/pull/7)(`code/d1-list` → `main`, 병합 커밋 `d791197`, 2026-09-30)이 D1이고 이슈 #5 · #6을 닫았다. [#8](https://github.com/HoyoungParkme/competition-crawler/pull/8)(`code/d2-frontend` → `main`, 병합 커밋 `bbd2d23`, 2026-09-30)이 D2다. 페이지 코드는 MS 밖(TypeScript)이라 커밋을 함수가 아니라 모듈 하나에 하나로 나눴다. [#9](https://github.com/HoyoungParkme/competition-crawler/pull/9)(`code/d3-pages` → `main`, 병합 커밋 `2b820b6`, 2026-09-30)이 D3이다. 워크플로와 안내 문서뿐이라 파일 하나에 커밋 하나다. [#11](https://github.com/HoyoungParkme/competition-crawler/pull/11)(`fix/page-leftovers` → `main`, 병합 커밋 `4d3559f`, 2026-09-30)은 이슈 #10을 고친 fix 둘이다. 끝난 카드의 수정이라 카드는 건드리지 않았다(DEV-15). 병합이 돌린 페이지 배포(실행 36681669374)가 성공했고, 배포된 번들에서 지운 문구가 빠진 것을 확인했다. [#13](https://github.com/HoyoungParkme/competition-crawler/pull/13)(`fix/commit-author` → `main`, 병합 커밋 `8c5c7a1`, 2026-09-30)은 이슈 #12를 고친 fix 둘이다. 명세를 먼저 고쳤다([[CCR-INFRA-001]] v8 · [[CCR-DOM-002]] v8 · [[CCR-API-001]] v6). 병합이 돌린 페이지 배포(실행 36686351923)가 성공했고, 배포된 번들에 noreply 주소가 들어간 것을 확인했다. [#15](https://github.com/HoyoungParkme/competition-crawler/pull/15)(`fix/status-read` → `main`, 병합 커밋 `d36485a`, 2026-09-30)는 이슈 #14를 고친 fix 둘이다. 명세를 먼저 고쳤다([[CCR-INFRA-001]] v9 · [[CCR-DOM-002]] v9 · [[CCR-UI-001]] v3 · [[CCR-API-001]] v7 · [[CCR-SEQ-001]] v6). 병합이 돌린 페이지 배포(실행 36691692088)가 성공했다. 배포된 페이지를 토큰 없이 열면 raw 두 파일만 읽고, 가짜 토큰을 넣고 열면 판 읽기가 401을 받은 뒤 상태 파일을 raw로 읽어 목록 49건을 그렸다. [#16](https://github.com/HoyoungParkme/competition-crawler/pull/16)(`fix/status-read-readme` → `main`, 병합 커밋 `51f436f`, 2026-09-30)은 같은 이슈의 뒷정리로 README의 로컬 읽기 설명을 명세에 맞췄다. #11 · #13 · #15 모두 본문의 `Closes`가 이슈에 이어지지 않아 이슈는 손으로 닫았다. [#18](https://github.com/HoyoungParkme/competition-crawler/pull/18)(`fix/readability` → `main`, 병합 커밋 `2bfe254`, 2026-10-01)은 이슈 #17을 고친 fix 셋이다. 글이 잘 안 보인다는 사용자 의견에 고친 안의 화면을 보이고, 사용자가 고른 대로 명세를 먼저 고쳤다([[CCR-UI-001]] v4 · v5 3장). 바꾼 것은 `styles.css` 하나다. 병합이 돌린 페이지 배포(실행 36796530043)가 성공했고, 배포된 페이지에서 계산된 글 크기와 색이 [[CCR-UI-001]] 3장과 같은 것을 확인했다. 이번에는 본문의 `Closes`가 이슈 #17을 닫았다. [#19](https://github.com/HoyoungParkme/competition-crawler/pull/19)(`code/d4-pager` → `main`, 병합 커밋 `4717c58`, 2026-10-01)가 D4다. 사용자가 고친 안의 화면을 보고 고른 뒤 명세를 먼저 고쳤다([[CCR-UI-001]] v6 · [[CCR-DOM-002]] v10 · 이 문서 v13). 커밋은 모듈 하나에 하나로 넷이고, 병합이 돌린 페이지 배포(실행 36800025511)가 성공했다. [#20](https://github.com/HoyoungParkme/competition-crawler/pull/20)(`code/d5-skip-star` → `main`, 병합 커밋 `96b081e`, 2026-10-01)이 D5다. 명세 아홉을 먼저 고쳤다([[CCR-PRD-001]] v12 · [[CCR-UC-001]] v10 · [[CCR-INFRA-001]] v10 · [[CCR-DOM-001]] v5 · [[CCR-UI-001]] v7 · [[CCR-API-001]] v8 · [[CCR-DOM-003]] v5 · [[CCR-DOM-002]] v11 · [[CCR-SEQ-001]] v7 · 이 문서 v15). 커밋은 모듈 하나에 하나로 일곱이고, 병합이 돌린 페이지 배포(실행 36804148774)가 성공했다. [#22](https://github.com/HoyoungParkme/competition-crawler/pull/22)(`fix/kaggle-paging` → `main`, 병합 커밋 `dc7edd2`, 2026-10-01)는 이슈 #21을 고친 fix 둘이다. 사용자가 Kaggle 토큰을 준 날 실측하니 쪽 넘김과 쿠키가 명세와 달라, 명세를 먼저 고쳤다([[CCR-API-001]] v9 · [[CCR-MS-001]] v6 · [[CCR-DOM-002]] v12 · [[CCR-DOM-001]] v6 · [[CCR-SEQ-001]] v8 · [[CCR-INFRA-001]] v11). [#24](https://github.com/HoyoungParkme/competition-crawler/pull/24)(`fix/kaggle-same-id` → `main`, 병합 커밋 `0968d08`, 2026-10-01)는 이슈 #23을 고친 fix 하나다. #22 병합 뒤 미리보기에서 Kaggle의 서로 다른 두 대회가 한 묶음이 된 것을 보고 명세를 먼저 고쳤다([[CCR-PRD-001]] v13 · [[CCR-DOM-002]] v13 · [[CCR-DOM-001]] v7). 같은 규칙을 적은 [[CCR-UC-001]] v11 · [[CCR-MS-001]] v7은 처음 저장이 도중에 멈춰, 사용자의 지시로 병합 뒤에 저장했다. 끝난 카드의 수정이라 카드는 건드리지 않았다(DEV-15). 둘 다 본문의 `Closes`가 이슈를 닫았다.

E1 · E2는 원본이 싱크독 서버 저장소라 PR이 없다. 카드마다 브랜치 하나를 `--no-ff`로 `main`에 합쳐 git 입구로 push했다 — E1 병합 `8116635`, E2 병합 `2a1b2ac`. 그 앞에 명세 13문서를 `spec/laptop-move` 브랜치로 고쳐 병합 `a904692`로 먼저 합쳤다.

## 4. 미결사항

2026-09-30에 네 가지를 마무리했다. 토큰 검증이 쓰기 권한까지 보지 못하는 것은 사용자 결정대로 명세를 코드에 맞췄다([[CCR-UC-001]] v9 · [[CCR-UI-001]] v2 · [[CCR-API-001]] v4 · [[CCR-DOM-002]] v6 · [[CCR-SEQ-001]] v4). `github-pages` 환경은 [[CCR-INFRA-001]] v6의 5.1과 8.11에 적었다. 노션 환경 둘과 시크릿은 지웠다(D3). D2 페이지 코드와 DOM-002가 다르던 곳도 사용자 결정대로 닫았다. 이름과 값의 모양, 응답 sha를 기억하는지는 명세를 코드에 맞췄고([[CCR-DOM-002]] v7 · [[CCR-API-001]] v5), 쓰지 않는 정렬 인자와 뜰 일 없는 404 문구는 fix(#10)으로 코드에서 지웠다(3장). 같은 날 SEQ-001이 되먹인 INFRA 8.2의 필수 필드 문장도 ERD를 가리키게 고쳤다([[CCR-INFRA-001]] v7 · [[CCR-DOM-003]] v4 · [[CCR-SEQ-001]] v5). 페이지가 만들 상태 커밋에 계정의 기본 이메일이 남는 문제도 사용자 결정대로 명세([[CCR-INFRA-001]] v8 · [[CCR-DOM-002]] v8 · [[CCR-API-001]] v6)와 fix(#12)로 막았다(3장). 확인 커밋으로 잰 raw 캐시(`max-age=300`, `?t=`로 못 피함, 58초 · 267초)는 사용자 결정대로 토큰이 있으면 상태 파일을 Contents API로 읽게 해 풀었다. 명세([[CCR-INFRA-001]] v9 6.4 · [[CCR-DOM-002]] v9 · [[CCR-UI-001]] v3 · [[CCR-API-001]] v7 · [[CCR-SEQ-001]] v6)와 fix(#14)다(3장). 목록 파일은 하루 한 번 바뀌어 raw 그대로 두고, 토큰이 없는 브라우저의 상태도 5분까지 늦을 수 있다([[CCR-INFRA-001]] 8.10). E2부터는 페이지 서버가 원본을 곧바로 읽어 이 늦음이 없다([[CCR-INFRA-001]] 6.4).

2026-10-01에는 환경 없는 첫 예약 실행이 성공해 예약 실행 항목을 닫았다. 실행 36806021819가 08:50 예약보다 늦은 11:28 KST에 시작해 58초 만에 끝났다. 다섯 소스 457건(event-us 41 · DACON 30 · wevity 156 · AI팩토리 과제 112 → 88 · 콘테스트코리아 118, Kaggle은 설정 누락)에서 마감 지남 154 · 아는 대회 208 · 버림 15 · 판별 실패 0이라 새로 넣은 대회는 0건이고, 남김 기록은 68, 배치는 46.5초였다. 마무리 단계가 처리 이력 21줄(남김 1 · 버림 20)과 실행 요약 한 줄을 커밋 `87dde20` 하나로 올렸고 목록 파일은 그대로다. `data/`만 바뀐 그 커밋에는 `pages.yml`이 돌지 않았다. 사흘 내리 예약이 11:00 ~ 11:46에 시작한 것은 GitHub의 지연이고 [[CCR-INFRA-001]] 8.4의 받아들인 한계다.

실물 확인도 2026-10-01에 마쳤다. 2026-09-30: D1 · D2 병합 → 그날 예약 실행(실행 36659861590, 08:50 예약이 11:26 KST에 시작)이 D1 · D2의 코드로 실제 적재 — 결과 성공, 목록 49건 · 버림 215 · 판별 실패 0 · 남김 기록 67, 144.1초. 세 파일이 커밋 `8c15cfa` 하나로 올라왔다 → D3 병합과 Pages 첫 배포 → 페이지에 목록 49건이 보인다 → 미리보기에서 그날 후보가 모두 아는 대회. fix(#12) 병합 뒤에는 사용자가 허락한 확인 커밋 둘로 페이지의 실제 저장 코드(`StatusStore` · `defaultGitHub`, 배포된 번들과 같은 소스)를 브라우저 밖에서 돌렸다. 토큰은 저장소 주인의 CLI 로그인 토큰을 환경 변수로만 넘겼고 브라우저에는 넣지 않았다. 한 대회(`콘테스트코리아:202609160051`)를 `진행 중`으로(`eb2de81`), 다시 `시작 전`으로(`cb4b5eb`) 바꿨다. 상태 파일이 없던 때라 첫 커밋이 파일을 만들었다(판 없이 쓰기). 두 번 모두 1.5초에 끝났고, 작성자 · 커미터가 저장소 주인의 noreply 주소로 GitHub 계정에 이어졌다. `data/`만 바뀐 두 커밋에는 `pages.yml` · `daily.yml` 어느 것도 돌지 않았다. 토큰 없이 연 배포된 페이지는 raw에 반영된 뒤 첫 줄의 그 대회를 `진행 중`으로, 되돌린 뒤 `시작 전`으로 그렸다. 2026-10-01 09:43에는 사용자가 배포된 페이지에 자기 토큰을 넣고(UI-2) 첫 줄 대회(`event-us:135633`)를 `진행 중`으로 바꿨다(7.4). 커밋 `62ca07b`가 작성자 · 커미터 모두 noreply 주소로 생겼고 `data/status.json`만 바뀌었으며, 어느 워크플로도 돌지 않았다. 같은 날 11:11에는 D5 배포 뒤 사용자가 그 대회를 `미참`으로 바꿨다(커밋 `f01f22d`). 새 상태 값이 그대로 저장됐고, 페이지가 파일 전체를 다시 쓰면서 두 항목 모두에 `starred: false`가 붙었다. 지우기 · 되살리기 · 별표는 배포된 페이지에서 GitHub 요청을 가로채 확인했다(가짜 토큰, 저장소에는 쓰지 않음). 별표 · 별표 뗌 · 지움 · 되살림 넷 모두 정해진 커밋 메시지(`status: <대회명> 별표` 등)와 noreply 작성자 · 커미터, 읽은 판(`sha`)을 실어 보냈고, 내용은 그 대회의 `starred` · `hidden`만 바뀌었다. 지운 줄은 목록에서 빠져 접힌 구역의 마지막 쪽(3 / 3)에 되살리기와 함께 있었고, 되살리면 돌아왔다. 저장 중 표시는 사라지고 저장 실패(12)는 뜨지 않았다. 실제 저장 길(`StatusStore` · `writeStatusFile`)은 사용자의 상태 커밋 둘이 이미 지났다. 지운 대회가 다시 들어오지 않는 것은 구조로 보장된다. 지우기는 상태 파일만 바꾸고 목록 파일의 항목은 그대로이며, 배치는 상태 파일을 읽지 않는다. 같은 날 예약 실행도 목록의 항목을 모두 아는 대회로 보고 하나도 다시 넣지 않았다(새 대회 0건).

Kaggle도 2026-10-01에 닫았다. 사용자가 새 토큰을 발급해 줬고, 저장소 시크릿 `KAGGLE_API_TOKEN`에 등록했다. 실측에서 쪽 넘김(`page`로만 넘어감)과 쿠키(익명 세션 쿠키가 실리면 토큰이 있어도 401)가 명세와 달라 fix(#21)로 고쳤다([[CCR-API-001]] 3.1 Kaggle · 1.1). 로컬 `collect`에서 여섯 소스가 모두 성공했다(event-us 41 · DACON 30 · Kaggle 21 · wevity 156 · AI팩토리 과제 112 → 88 · 콘테스트코리아 122). 병합 뒤 미리보기 수동 실행 36816035699(`dc7edd2`)는 Kaggle 21건을 받고 성공했지만, 넣었을 대회에서 Kaggle의 `ARC Prize 2026 - ARC-AGI-2`와 `ARC-AGI-3`이 한 묶음이 되어 있어 fix(#23)로 고쳤다. 고친 뒤 미리보기 36819786546(`0968d08`)은 넣었을 묶음 8개(Kaggle 7 · 콘테스트코리아 1)로 끝났다. 커뮤니티 탭은 받지 않기로 했다([[CCR-API-001]] 3.1). Kaggle 대회는 다음 예약 실행부터 목록에 들어간다.

- [x] **사용자가 켤 것.** 실패 알림 — GitHub 설정의 알림(Notifications)에서 Actions의 실패한 워크플로 알림을 켠다. 계정 설정이라 저장소나 API로는 켤 수 없다. 사용자가 직접 켜기로 했다(2026-10-01). 페이지 토큰과 Kaggle 토큰은 2026-10-01에 넣었다. 2026-10-06부터 없다 — 실패는 노트북의 윈도 알림으로 알린다(E1). 페이지 토큰도 없앤다(E2)
- [x] **가리키는 곳이 없는 참조.** 끝난 카드 A · D1의 구현 함수가 가리키던 `CCR-MS-001#logging.register_actions_masks`는 2026-10-06에 그 MS 항목을 지워 가리키는 곳이 없어졌다. 싱크독이 이것을 「가리키는 곳이 없는 참조」로 세어 이 문서의 완료를 막으므로, 그 두 링크만 글자로 풀었다(싱크독 카드 O와 같은 처리). 같은 날 DOM-002에서 블록을 지운 `SettingsDialog` · `TokenStore`를 가리키던 끝난 카드 D2의 두 링크도 같이 풀었다. 카드의 다른 내용은 그대로다
