---
doc_id: CCR-MS-001
type: MS
title: MINISPEC — 대회 수집 배치
status: approved
upstream: [CCR-DOM-002, CCR-DOM-003, CCR-SEQ-001, CCR-API-001, CCR-UC-001]
---

# MINISPEC — 대회 수집 배치

## 0. 이 문서가 다루는 것

클래스 명세([[CCR-DOM-002]])의 메서드와 모듈 함수 하나하나가 무엇을 받아 무엇을 하는지다. 시간순 흐름은 [[CCR-SEQ-001]], 타입은 [[CCR-DOM-002]] 2.4, 줄 형식은 [[CCR-DOM-003]]에서만 찾는다.

- 항목 ID는 `클래스.메서드` 또는 `접두어.함수`다. 접두어는 모듈이 있는 곳이다. 파일 이름과 같으면 그 파일(`matching` · `eventus` · `dacon` · `kaggle` · `wevity` · `aifactory` · `contestkorea` · `openai_judge` · `settings` · `logging` · `dates` · `text` · `http` · `robots` · `finish`), 그 밖은 경계 이름이다. `screen` = `domains/screen/service.py`, `list` = `domains/list/`(`models.py`의 `entry_of`), `record` = `domains/record/crud.py`, `__main__` = `collector/__main__.py`. 2026-09-29에 노션 경계의 함수 열넷과 `NotionHttp` · `secret_variants`를 지우고 목록 경계의 함수 열하나를 더했다.
- 처리가 몇 줄이면 간략형(시그니처 · 처리 · 테스트 관점)으로 쓴다.
- 시그니처는 코드와 글자 그대로 적는다. 이름은 함수 이름만(점 없이), `self` · `cls`는 빼고, 타입과 기본값까지. 코드의 함수 docstring 첫 줄은 `CCR-MS-001#항목`이고, 싱크독 `tools/check_code.py`가 둘을 대조한다(싱크독 개발 규약 SYNC-STD-004 DEV-3 · DEV-14).
- 날짜는 모두 KST 날짜(`date`)다. 기준일은 `RunContext.base_date` 하나다.
- 테스트 관점은 `batch/tests/`에 있는 테스트가 확인하는 것이다. 테스트가 아니라 손으로 재 본 것은 (실측)이라 적는다.
- 대회 목록 페이지(`frontend/`)의 함수는 이 문서에 두지 않는다. 모듈과 시그니처는 [[CCR-DOM-002]] 4.11이 정했고, TypeScript라 `check_code.py`의 대상이 아니다. 순수 함수의 테스트는 `frontend/tests/`가 본다([[CCR-DOM-002]] 5장 결정 11).

## 1. 함수 목록

| 모듈 | 함수 |
|---|---|
| core · shared | [[#RunContext.from_env]] · [[#Settings.load]] · [[#Secrets.from_env]] · [[#Secrets.values]] · [[#settings.read_dotenv]] · [[#logging.register_actions_masks]] · [[#SecretFilter.filter]] · [[#logging.setup_logging]] · [[#dates.parse_to_kst_date]] · [[#dates.kst_date_of]] · [[#dates.kst_midnight_utc]] · [[#text.clean_text]] · [[#text.html_text]] |
| infra | [[#SourceHttp.fetch]] · [[#SourceHttp.remaining]] · [[#SourceHttp.close]] · [[#http.parse_retry_after]] · [[#http.new_client]] · [[#robots.ensure_allowed]] |
| 수집 | [[#Competition.dates_filled]] · [[#SourceResult.normalized]] · [[#SourceResult.failed]] · [[#Source.collect]] · [[#Source.missing_config]] · [[#CollectService.collect_all]] · [[#CollectService._collect_one]] · [[#eventus.build_query]] · [[#eventus.parse_page]] · [[#eventus.normalize]] · [[#EventUsSource.collect]] · [[#EventUsSource.missing_config]] · [[#dacon.parse_page]] · [[#dacon.normalize]] · [[#dacon.link_for]] · [[#DaconSource.collect]] · [[#DaconSource.missing_config]] · [[#kaggle.parse_page]] · [[#kaggle.normalize]] · [[#kaggle.is_practice]] · [[#KaggleSource.collect]] · [[#KaggleSource.missing_config]] · [[#wevity.parse_list]] · [[#wevity.parse_detail_end]] · [[#wevity.deadline_of]] · [[#WevitySource.collect]] · [[#WevitySource._calibrate]] · [[#WevitySource.missing_config]] · [[#aifactory.extract_payload]] · [[#aifactory.parse_tasks]] · [[#aifactory.parse_page]] · [[#aifactory.group_tasks]] · [[#aifactory.competition_name]] · [[#aifactory.to_competition]] · [[#AiFactorySource.collect]] · [[#AiFactorySource.missing_config]] · [[#contestkorea.parse_list]] · [[#contestkorea.resolve_dates]] · [[#ContestKoreaSource.collect]] · [[#ContestKoreaSource.missing_config]] |
| 선별 | [[#matching.normalize_title]] · [[#matching.extract_marks]] · [[#matching.normalize_link]] · [[#matching.key_of_competition]] · [[#matching.key_of_entry]] · [[#matching.key_of_history]] · [[#matching.similarity]] · [[#matching.judge_pair]] · [[#matching.group]] · [[#matching.representative_order]] · [[#Bundle.deadline]] · [[#ScreenService.drop_expired]] · [[#ScreenService.bundle]] · [[#ScreenService.build_known]] · [[#KnownSet.add]] · [[#ScreenService.split_known]] · [[#ScreenService._matches]] · [[#ScreenService._record_known]] · [[#screen.entries_for]] · [[#ScreenService.judge]] · [[#ScreenService._ask_all]] · [[#Judge.judge]] · [[#OpenAiJudge.judge]] · [[#openai_judge.build_input]] |
| 목록 | [[#ListEntry.id]] · [[#ListEntry.to_dict]] · [[#ListEntry.from_dict]] · [[#list.entry_of]] · [[#ListService.load]] · [[#ListFile.ids]] · [[#ListService.append]] · [[#ListService.appended_count]] · [[#ListCrud.read]] · [[#ListCrud.reset_appends]] · [[#ListCrud.write_appends]] |
| 기록 | [[#HistoryRecord.of]] · [[#HistoryRecord.to_dict]] · [[#HistoryRecord.from_dict]] · [[#SourceLine.to_dict]] · [[#RunWarning.to_dict]] · [[#RunLine.fail]] · [[#RunLine.to_dict]] · [[#RecordService.start]] · [[#RecordService.load]] · [[#State.keep_count]] · [[#State.last_keep_count]] · [[#RecordService.history_shrank]] · [[#RecordService.append]] · [[#RecordService.appended_count]] · [[#RecordService.zero_count_warnings]] · [[#RecordService.write_run]] · [[#RecordCrud.read_history]] · [[#RecordCrud.read_runs]] · [[#RecordCrud.prepare]] · [[#RecordCrud.reset_appends]] · [[#RecordCrud.write_history_appends]] · [[#RecordCrud.write_run_append]] · [[#record._atomic_write]] · [[#record.export_main_state]] |
| 실행의 흐름 | [[#__main__.main]] · [[#__main__.run_batch]] · [[#__main__.run_collect]] · [[#__main__.sources_of]] · [[#Pipeline.run]] · [[#Pipeline._run]] · [[#Pipeline._load]] · [[#Pipeline._finish]] |
| 마무리 단계 | [[#finish.finish]] · [[#finish.read_additions]] · [[#finish.base_date_of]] · [[#finish.has_run]] · [[#finish.count_keep]] · [[#finish.existing_ids]] · [[#Git.fresh_main]] · [[#Git.commit_and_push]] · [[#finish.append_lines]] · [[#finish.main]] |

## 2. 함수

### 2.1 core · shared

#### RunContext.from_env 실행 문맥 만들기

**시그니처** `from_env(env: Mapping[str, str], *, now: datetime | None = None) -> RunContext`

**근거** [[CCR-UC-001#UC-A1]] 1 · 1b5 · 1b6 · 1b7 · [[CCR-INFRA-001]] 8.1 · [[CCR-SEQ-001#SEQ-8]]

**입력** 환경 변수. `GITHUB_ACTIONS` · `DRY_RUN` · `RUN_STARTED_AT` · `RUN_ID` · `GITHUB_EVENT_NAME` · `GITHUB_REF` · `IGNORE_DISCARDS` · `STATE_DIR` · `APPEND_DIR` · `RUNNER_TEMP`

**처리**
1. `in_actions = GITHUB_ACTIONS == "true"`.
2. if `in_actions` 이고 `DRY_RUN`이 `true` · `false`가 아님 → `RunModeError` · else → 다음.
3. `write = in_actions and DRY_RUN == "false"`. Actions 밖은 늘 거짓이다.
4. 시작 시각 = `RUN_STARTED_AT`(ISO, `Z` 허용. 시간대가 없으면 UTC로 본다) · 없으면 `now` · 그것도 없으면 지금. `base_date = kst_date_of(시작 시각)`.
5. `run_id = RUN_ID` · 없으면 `local-YYYYMMDDTHHMMSS`. `kind = schedule` if `GITHUB_EVENT_NAME == schedule` · else `manual`.
6. `ignore_discards_requested = IGNORE_DISCARDS == "true"`, `ignore_discards = requested and not write`.
7. 상태 폴더: if `STATE_DIR` → 그것(꺼내지 않음) · else if `in_actions` 이고 `GITHUB_REF == refs/heads/main` → `REPO_ROOT/data` · else → 새 임시 폴더, `state_from_main = True`.
8. 추가분 폴더: `APPEND_DIR` · 없으면 `RUNNER_TEMP/append` · 없으면 시스템 임시 폴더 아래 `competition-crawler-append`.

**출력** `RunContext`

**예외** Actions 안에서 `DRY_RUN`이 깨짐 → `RunModeError`

**테스트 관점** 08:50 KST(UTC 전날 23:50)의 기준일이 KST 날짜다 · `DRY_RUN`이 `""` · `True` · `1`이면 `RunModeError` · Actions 밖은 `write=False`이고 main 판을 꺼낸다 · 브랜치 실행도 꺼낸다 · 쓰는 실행에서 버림 무시는 꺼진다 · `workflow_dispatch`는 `manual`

#### Settings.load 조정값 읽기

**시그니처** `load(env: Mapping[str, str], path: Path | None = None) -> Settings`

**처리**
1. `batch/settings.toml`(또는 `path`)을 읽어 `source` · `judge` · `warning` 표를 타입에 맞춰 옮긴다.
2. 판별 모델 = `OPENAI_MODEL`(앞뒤 공백을 뗀 값) if 비어 있지 않음 · else `settings.toml`의 기본값.

**테스트 관점** 쪽 상한 20 · 예산 120 · 동시 4 · 0건 연속 3일 · `OPENAI_MODEL`이 덮고 공백은 무시

#### Secrets.from_env 비밀값 읽기

**시그니처** `from_env(env: Mapping[str, str]) -> Secrets`

**처리** 두 이름(`OPENAI_API_KEY` · `KAGGLE_API_TOKEN`)을 읽고 앞뒤 공백을 뗀다. 빈 문자열은 `None`이다. 등록되지 않은 시크릿은 빈 문자열로 들어오기 때문이다([[CCR-INFRA-001]] 5장).

**테스트 관점** 빈 값 · 공백만 있는 값이 `None`

#### Secrets.values 가릴 비밀값

**시그니처** `values() -> list[str]`

**처리** 두 비밀값 가운데 있는 값만 차례대로 돌려준다. 로그 가리기와 Actions 가릴 값 알리기가 쓴다([[#logging.register_actions_masks]] · [[#SecretFilter.filter]]).

**테스트 관점** [[#Secrets.from_env]]의 테스트가 함께 본다

#### settings.read_dotenv 로컬 .env 읽기

**시그니처** `read_dotenv(path: Path) -> dict[str, str]`

**처리** 파일이 없으면 빈 것. 줄마다 `#`로 시작하거나 `=`가 없는 줄은 건너뛰고, `export ` 머리를 떼고, 값의 짝이 맞는 따옴표를 뗀다. 로컬 실행에서만 부르고 이미 있는 환경 변수가 이긴다([[#__main__.main]]).

**테스트 관점** 주석 · 따옴표 · `export` · 빈 값 · 깨진 줄

#### logging.register_actions_masks Actions에 가릴 값 알리기

**시그니처** `register_actions_masks(values: Iterable[str], emit: Callable[[str], None] | None = None) -> None`

**처리** 값마다 `::add-mask::값`을 표준 출력에 찍는다. 노션 ID의 두 표기를 만들던 `secret_variants`는 노션과 함께 없앴다([[CCR-DOM-002]] 4.9). 어떤 로그보다 먼저 부른다. Actions 안에서만 부른다.

**테스트 관점** 값마다 한 줄

#### SecretFilter.filter 로그 가리기

**시그니처** `filter(record: logging.LogRecord) -> bool`

**처리**
1. 메시지를 완성한 뒤(`getMessage`) 값마다 `***`로 바꾸고 `args`를 비운다. 긴 값부터 바꾼다.
2. if 예외가 붙음 → 예외 원문을 미리 만들어(`exc_text`) 같이 가린다. 포매터는 이미 만든 원문을 다시 만들지 않는다.
3. 늘 참을 돌려준다(기록은 버리지 않는다).

**테스트 관점** 메시지와 예외 원문 모두에서 키 값이 사라진다

#### logging.setup_logging 로그 설정

**시그니처** `setup_logging(secrets: Iterable[str]) -> None`

**처리** 표준 출력 처리기 하나에 `SecretFilter(secrets)`를 걸고 루트 로거를 INFO로 둔다. 형식은 `수준 이름: 메시지`. `httpx` · `httpcore` · `openai` 로거는 요청 헤더가 섞일 수 있어 WARNING 이상만 남긴다.

**테스트 관점** 가리기는 [[#SecretFilter.filter]]의 테스트가 본다

#### dates.parse_to_kst_date 시각을 KST 날짜로

**시그니처** `parse_to_kst_date(text: str | None) -> date | None`

**처리** 비었으면 `None`. 끝의 `Z`를 `+00:00`으로 바꿔 ISO로 읽는다. 읽지 못하면 `None`. if 시간대 있음 → KST로 바꾼 날짜 · else → 그대로 날짜(KST로 본다)([[CCR-API-001]] 1.1 · [[CCR-PRD-001]] 5.3).

**테스트 관점** `2026-08-04T15:00:00+00:00` → 8월 5일 · 시간대 없는 값은 바꾸지 않음 · 읽지 못하는 값은 `None`

#### dates.kst_date_of 시각의 KST 날짜

**시그니처** `kst_date_of(moment: datetime) -> date`

**처리** 시간대가 없으면 `ValueError`. 있으면 KST 날짜. 기준일은 이 함수로만 구한다.

**테스트 관점** UTC 23:50 → 다음 날 · 시간대 없는 값은 거부

#### dates.kst_midnight_utc KST 자정의 UTC 시각

**시그니처** `kst_midnight_utc(day: date) -> datetime`

**처리** KST 그날 0시를 UTC로. event-us 조회 조건에 쓴다([[#eventus.build_query]]).

**테스트 관점** 2026-09-23 → `2026-09-22T15:00:00+00:00`

#### text.clean_text 앞뒤 다듬기

**시그니처** `clean_text(value: Any) -> str`

**근거** [[CCR-UC-001#UC-S2]] 4

**처리** `None`은 빈 문자열. 앞과 뒤에서 공백(줄바꿈 · NBSP 포함)이나 서식 문자(유니코드 범주 `Cf`: BOM · 폭 없는 공백 등)인 글자를 뗀다. 가운데는 건드리지 않는다. JSON 소스의 대회명과 판정의 정규화 첫머리에 쓴다.

**테스트 관점** 앞의 BOM 셋과 뒤의 폭 없는 공백이 빠지고 가운데 NBSP는 남는다

#### text.html_text HTML 글자 다듬기

**시그니처** `html_text(value: Any) -> str`

**처리** 이어진 공백을 하나로 모은 뒤 `clean_text`. 브라우저가 보여 주는 글자와 같다. HTML 소스(wevity · 콘테스트코리아)의 대회명에 쓴다.

**테스트 관점** 줄바꿈 · 탭 · NBSP가 공백 하나로

### 2.2 infra

#### SourceHttp.fetch 소스에 요청

**시그니처** `fetch(method: str, url: str, *, parse: Callable[[httpx.Response], T], params: Mapping[str, Any] | None = None, json: Any = None, headers: Mapping[str, str] | None = None, follow_redirects: bool = False, accept_client_errors: bool = False) -> T`

**근거** [[CCR-API-001]] 1.1 · 1.2 · 2.1 · [[CCR-INFRA-001]] 8.5 · [[CCR-SEQ-001#SEQ-2]]

**입력** 요청 내용과 응답을 읽는 `parse`. 설정값: 타임아웃 20초 · 재시도 2 · 간격 2 · 4초 · `Retry-After` 상한 30초 · 요청 간격 1초. 만들 때 받은 기한(시간 예산)과 멈춤 표시.

**처리** 최대 1 + 재시도 번 되풀이한다.
1. if 멈춤 표시 → `Stopped` · if 남은 예산 ≤ 0 → `HttpFailure(budget)`.
2. 앞 요청과 1초 간격을 둔다(기다림은 0.5초씩 잘라 멈춤 표시를 본다. 남은 예산보다 길면 `budget`).
3. 타임아웃 = min(20초, 남은 예산)으로 보내고 본문을 흘려 받는다. 조각마다 if 멈춤 표시 → `Stopped` · if 남은 예산 ≤ 0 → `HttpFailure(budget)`. httpx 타임아웃은 단계마다 걸려 요청 전체를 묶지 못한다. 받은 본문은 압축을 푼 채로 응답을 다시 만들어 `parse`에 넘긴다.
4. if 연결 오류 · 타임아웃 → 마지막이면 `HttpFailure(connection)` · else 간격만큼 쉬고 다시.
5. if 3xx → `HttpFailure(status)`. 리디렉션을 따라가지 않는다(`follow_redirects`면 클라이언트가 다섯 번까지 따라간 뒤의 응답을 본다).
6. if 429 · 5xx → 마지막이면 `HttpFailure(status)` · else if `Retry-After` 있음 → 상한이나 남은 예산보다 길면 곧바로 `HttpFailure(status)`, 아니면 그만큼 기다려 다시 · else 간격만큼 쉬고 다시.
7. if 그 밖의 4xx 이고 `accept_client_errors`가 아님 → `HttpFailure(status)`. 다시 보내지 않는다.
8. `parse(응답)`. if `FormatError` → 마지막이면 `HttpFailure(format)` · else 쉬고 다시.

**출력** `parse`의 결과. `requests`에 보낸 요청 수가 쌓인다.

**예외** 끝내 받지 못함 → `HttpFailure(category)` · 신호 → `Stopped`

**호출하는 것** [[#http.parse_retry_after]]

**테스트 관점** 조금씩 오는 본문이 기한을 넘기면 `budget` · 압축 본문은 한 번만 풀림 · 5xx 두 번 뒤 성공(기다림 2 + 4초) · 세 번 모두 5xx면 `status` · 404는 한 번만 · 301은 따라가지 않고 `status` · `Retry-After: 45`는 기다리지 않고 실패 · `Retry-After: 7`은 7초 기다림 · 틀이 다르면 세 번 뒤 `format` · 연결 오류 뒤 성공 · 요청 사이 1초 · 예산을 넘기면 `budget` · 멈춤 표시면 `Stopped` · User-Agent가 배치를 밝힌다

#### SourceHttp.remaining 남은 시간 예산

**시그니처** `remaining() -> float`

**처리** 기한에서 지금 시각을 뺀 초. 음수일 수 있다. [[#SourceHttp.fetch]]가 요청 · 기다림 · 본문 조각마다 본다.

**테스트 관점** [[#SourceHttp.fetch]]의 예산 테스트가 함께 본다

#### SourceHttp.close 연결 닫기

**시그니처** `close() -> None`

**처리** 안의 httpx 클라이언트를 닫는다. [[#CollectService._collect_one]]이 소스 하나를 다 받은 뒤 부른다.

**테스트 관점** 없음(닫기만 한다)

#### http.parse_retry_after Retry-After 읽기

**시그니처** `parse_retry_after(value: str | None, now: datetime | None = None) -> float | None`

**처리** if 비었음 → `None` · if 숫자 → 그 초(음수는 0) · else if HTTP 날짜 → 지금부터의 초 · else `None`.

**테스트 관점** 초 · 날짜 · 읽지 못하는 값

#### http.new_client 소스용 클라이언트

**시그니처** `new_client(transport: httpx.BaseTransport | None = None) -> httpx.Client`

**근거** [[CCR-API-001]] 1.1

**처리** User-Agent를 붙이고 리디렉션은 다섯 번까지 따라가며 쿠키는 남기지 않는 httpx 클라이언트를 만든다. 모든 도메인을 막은 쿠키 정책을 주어, 응답이 심은 쿠키가 다음 요청에 실리지 않는다. Kaggle은 익명 세션 쿠키가 실린 요청을 토큰이 있어도 401로 거절한다(2026-10-01 실측). `SourceHttp`는 클라이언트를 받지 않으면 이것을 쓴다. `transport`는 테스트가 가짜 응답을 끼울 때 준다.

**테스트 관점** 응답이 심은 쿠키가 다음 요청에 실리지 않음. 테스트의 가짜 HTTP도 이 클라이언트에 가짜 전송만 끼우므로 소스 테스트가 모두 같은 설정으로 돈다

#### robots.ensure_allowed robots.txt 확인

**시그니처** `ensure_allowed(http: SourceHttp, origin: str, paths: Iterable[str]) -> None`

**근거** [[CCR-API-001]] 1.2 · [[CCR-UC-001#UC-S1]] 2

**처리**
1. `origin/robots.txt`를 `fetch`한다. 리디렉션은 다섯 번까지 따라가고(RFC 9309), 429를 뺀 4xx는 받아들인다. 429는 다른 요청처럼 다시 보내고 끝내 받지 못하면 실패다.
2. if 429를 뺀 4xx → 제한 없음. 끝.
3. 표준 라이브러리 `robotparser`로 읽고, 경로마다 에이전트 `competition-crawler`로 허용되는지 본다. 막힌 경로가 있으면 `RobotsDisallowed(경로)`.
4. 5xx · 연결 오류로 끝내 받지 못하면 `fetch`의 `HttpFailure`가 그대로 나간다(목록을 요청하지 않는다).

**테스트 관점** 허용 · 막힘 · 에이전트 이름 규칙 · 404는 제한 없음 · 503은 실패

### 2.3 수집

#### Competition.dates_filled 채워진 접수 날짜 수

**시그니처** `dates_filled() -> int`

**처리** 접수시작일 · 접수마감일 가운데 있는 것의 수(0 · 1 · 2). 묶음의 대표를 고를 때 쓴다([[#matching.representative_order]]).

**테스트 관점** [[#matching.representative_order]]의 테스트가 함께 본다

#### SourceResult.normalized 정규화 뒤 건수

**시그니처** `normalized() -> int`

**처리** 속성. 맞춰 낸 대회의 수(`len(competitions)`). 실행 요약의 소스별 `normalized`가 이 값이다([[CCR-DOM-003#run_sources]]).

**테스트 관점** [[#Pipeline._finish]]의 테스트가 함께 본다(소스 건수)

#### SourceResult.failed 실패한 소스의 결과

**시그니처** `failed(source: SourceName, kind: FailureKind, detail: str) -> SourceResult`

**처리** 대회 없음 · 수집 0 · 탈락 0에 실패 종류와 원문 사유를 담아 만든다. 원문 사유는 로그에만 간다.

**테스트 관점** [[#CollectService._collect_one]]의 테스트가 함께 본다

#### Source.collect 소스 포트 — 수집

**시그니처** `collect(http: SourceHttp, base_date: date, page_cap: int) -> Collected`

**처리** 포트. 목록을 받아 공통 형식으로 맞춘다. 틀을 찾지 못하면 `FormatError`, 요청이 실패하면 `HttpFailure`. 구현은 어댑터 여섯이다([[#EventUsSource.collect]] 등).

**테스트 관점** 어댑터마다의 테스트가 본다

#### Source.missing_config 소스 포트 — 설정 누락

**시그니처** `missing_config() -> bool`

**처리** 포트. 필요한 자격증명이 설정에 없으면 참. 그때는 요청하지 않는다([[CCR-UC-001#UC-S1]] 1a).

**테스트 관점** [[#KaggleSource.missing_config]]의 테스트가 본다

#### CollectService.collect_all 여섯 소스 수집

**시그니처** `collect_all(base_date: date) -> list[SourceResult]`

**근거** [[CCR-UC-001#UC-S1]] · [[CCR-SEQ-001#SEQ-2]]

**처리**
1. 소스 수만큼의 스레드로 `_collect_one`을 동시에 돌린다.
2. 결과를 소스 목록의 차례로 모은다.
3. if 멈춤 표시 → `Stopped` · else 결과.

**출력** 소스마다 `SourceResult` 하나. 실패한 소스도 빈 목록과 실패 종류로 들어 있다.

**테스트 관점** 여섯 가지 실패가 각 종류로 바뀌고 성공한 소스는 대회를 갖는다

#### CollectService._collect_one 소스 하나

**시그니처** `_collect_one(source: Source, base_date: date) -> SourceResult`

**근거** [[CCR-UC-001#UC-S1]] 1a · 2a · \*a · [[CCR-API-001]] 2.1

**처리**
1. if `source.missing_config()` → `failed(missing_config)`. 요청하지 않는다.
2. 기한 = 지금 + 예산 120초로 `SourceHttp`를 만든다.
3. `ensure_allowed(origin, robots_paths)` 뒤 `source.collect(http, base_date, 쪽 상한)`.
4. 예외를 종류로 바꾼다. `Stopped` → `connection` · `RobotsDisallowed` → `robots` · `HttpFailure` → `connection`(connection · budget) · `http_status`(status) · `format`(format) · `FormatError` → `format` · 그 밖의 예외 → `format`(로그에 스택).
5. `notes`와 쪽 상한에 닿았는지 · 수집 · 정규화 · 탈락 · 요청 수 · 걸린 초를 로그에 남긴다.

**출력** `SourceResult`. 원문 사유는 `detail`로 로그에만.

**테스트 관점** 예산 초과는 `connection` · robots 금지는 `robots` · 파서의 `KeyError`는 `format`

#### eventus.build_query event-us 조회 조건

**시그니처** `build_query(base_date: date, page: int) -> dict[str, Any]`

**처리** [[CCR-API-001#POST/api.event-us.kr/api/v1/engine/search]]의 본문을 만든다. 쪽 크기 100. `all` 조건 넷(대회/공모전 · 진행 중 · 공개 · 무시되지 않음)과, `any` 조건(접수마감일이 기준일 KST 자정 이후 · 또는 접수마감일이 없고 행사 종료일이 기준일 이후이거나 없음). 접수마감일 오름차순.

**테스트 관점** 쪽 · 조건 · 기준일 자정이 UTC 전날 15시

#### eventus.parse_page event-us 응답 한 쪽

**시그니처** `parse_page(response: httpx.Response) -> tuple[list[dict[str, Any]], int]`

**처리** JSON이 아니면 `FormatError`. 최상위가 객체이고 `results`가 배열이며 `meta.page.total_pages`가 정수여야 한다. 아니면 `FormatError`. (레코드 목록, 전체 쪽 수)를 돌려준다.

**테스트 관점** 저장한 쪽에서 레코드 40건과 전체 쪽 수 1

#### eventus.normalize event-us 공고 하나

**시그니처** `normalize(item: dict[str, Any]) -> Competition | None`

**처리** 필드마다 `raw` 값을 읽는다. if `id` · 대회명 · `subdomain` 가운데 하나라도 없음 → `None`(탈락). 링크 `https://event-us.kr/{subdomain}/event/{id}`, 접수시작일 · 마감일은 UTC 시각을 KST 날짜로, 부가 정보는 분야 둘과 태그.

**테스트 관점** 저장한 쪽 40건이 모두 맞춰지고 135608의 날짜가 9/17 · 9/23 · `subdomain`이 없으면 탈락

#### EventUsSource.collect event-us 수집

**시그니처** `collect(http: SourceHttp, base_date: date, page_cap: int) -> Collected`

**처리** 1쪽부터 `total_pages`까지 `POST`한다. if 쪽 번호 > 상한 → `page_cap_hit`으로 멈춤. 레코드마다 `normalize`, `None`이면 탈락.

**테스트 관점** 두 쪽을 차례로 읽음 · 상한에 닿으면 멈춤

#### EventUsSource.missing_config event-us 설정 누락

**시그니처** `missing_config() -> bool`

**처리** 늘 거짓. 자격증명이 필요 없다.

**테스트 관점** 없음(늘 거짓)

#### dacon.parse_page DACON 응답 한 쪽

**시그니처** `parse_page(response: httpx.Response) -> list[dict[str, Any]]`

**처리** JSON이 아니면 `FormatError`. 최상위가 객체이고 `data`가 배열이어야 한다. 아니면 `FormatError`. `data`를 돌려준다.

**테스트 관점** 저장한 쪽에서 레코드 15건

#### dacon.normalize DACON 대회 하나

**시그니처** `normalize(item: dict[str, Any]) -> Competition | None`

**처리** if `cpt_id` · `name`이 없음 → `None`. 링크는 [[#dacon.link_for]]. 날짜는 `period_start` · `period_end`(시간대 없음 → KST). 부가 정보는 `keyword`를 `|`로 나눈 것.

**테스트 관점** 236746의 링크 · 날짜 · 키워드

#### dacon.link_for DACON 상세 링크

**시그니처** `link_for(cpt_id: str, is_landing: Any) -> str`

**처리** if `is_landing_cpt`가 1 → `https://dacon.io/competition/{id}/overview` · else → `https://dacon.io/competitions/official/{id}/overview/description`.

**테스트 관점** 대회 페이지(236746)와 공식 대회 페이지 두 꼴

#### DaconSource.collect DACON 수집

**시그니처** `collect(http: SourceHttp, base_date: date, page_cap: int) -> Collected`

**처리** `offset` 0부터 상한까지 `GET ?offset=N&range=`. if 빈 쪽 → 멈춤. 쪽마다 맞춘 뒤, if 그 쪽에 접수마감일 ≥ 기준일인 대회가 없음 → 멈춤(종료일이 늦은 차례라 뒤쪽도 끝났다). 상한까지 가면 `page_cap_hit`.

**테스트 관점** 둘째 쪽에 접수 중인 대회가 없어 두 쪽에서 멈춤

#### DaconSource.missing_config DACON 설정 누락

**시그니처** `missing_config() -> bool`

**처리** 늘 거짓. 자격증명이 필요 없다.

**테스트 관점** 없음(늘 거짓)

#### kaggle.parse_page Kaggle 응답 한 쪽

**시그니처** `parse_page(response: httpx.Response) -> list[dict[str, Any]]`

**처리** JSON이 아니면 `FormatError`. 최상위가 객체여야 하고 `competitions`(없으면 빈 목록)가 배열이어야 한다. 대회 목록을 돌려준다. 마지막 쪽 다음은 빈 객체 `{}`로 오므로 빈 목록이 된다. `nextPageToken`은 오지 않아 읽지 않는다([[CCR-API-001]] 3.1 Kaggle).

**테스트 관점** 저장한 응답(2026-10-01) 20건 · 빈 객체는 빈 목록

#### kaggle.normalize Kaggle 대회 하나

**시그니처** `normalize(item: dict[str, Any]) -> Competition | None`

**처리** `ref`(전체 URL)의 마지막 조각이 원천 ID(slug). if slug · `title`이 없음 → `None`. 링크 `https://www.kaggle.com/competitions/{slug}`, 접수시작일 `enabledDate`, 접수마감일 `newEntrantDeadline` · 없으면 `deadline`(UTC → KST). 부가 정보는 `category`와 태그 이름. `practice = is_practice(category)`.

**테스트 관점** 저장한 응답 20건이 모두 대회가 되고 연습용이 13건 · 새 참가 마감일을 쓰고 UTC 23:59가 KST 다음 날 · 밀리초가 붙은 마감

#### kaggle.is_practice 상시 연습용 대회인가

**시그니처** `is_practice(category: Any) -> bool`

**처리** 공백을 빼고 소문자로 바꾼 값이 `gettingstarted` · `playground` 가운데 하나인가. 실제 값은 `Getting Started` · `Playground`이고(2026-10-01), [[CCR-RFQ-001#Q4]]의 표기 `gettingStarted`도 맞게 견준다.

**테스트 관점** `Getting Started` · `gettingStarted` · `Playground`는 참 · `Featured` · `Research` · `Community`는 거짓

#### KaggleSource.collect Kaggle 수집

**시그니처** `collect(http: SourceHttp, base_date: date, page_cap: int) -> Collected`

**처리** `page`를 1부터 올리며 `POST ListCompetitions`(일반 탭 · 분야 전체 · 마감 늦은 차례 · `page`)에 `Authorization: Bearer 토큰`. `pageSize` · `pageToken`은 효과가 없어 보내지 않는다. 한 쪽은 20건이다. if 빈 쪽 → 멈춤 · else 대회를 담고, if 그 쪽이 모두 마감됨(`deadline` < 기준일) → 멈춤. 쪽 상한에 닿으면 `page_cap_hit`. 토큰이 없으면 `CollectService`가 부르지 않는다(`missing_config`).

**테스트 관점** 저장한 두 쪽과 빈 쪽으로 `page` 1 · 2 · 3을 보내고 21건 · `pageSize` · `pageToken`을 보내지 않음 · Bearer 헤더 · 마감된 쪽에서 멈춤 · 쪽 상한

#### KaggleSource.missing_config Kaggle 설정 누락

**시그니처** `missing_config() -> bool`

**처리** API 토큰이 없으면 참. 그때 `CollectService`가 요청하지 않고 `missing_config`로 끝낸다([[CCR-UC-001#UC-S1]] 1a).

**테스트 관점** 토큰이 없으면 참 · 있으면 거짓

#### wevity.parse_list wevity 목록 한 쪽

**시그니처** `parse_list(response: httpx.Response) -> list[WevityItem]`

**처리** `ul.list`가 없으면 `FormatError`. 머리 줄(`li.top`)을 뺀 `li`마다 `div.tit a`의 `href`에서 `ix`, 제목(배지 `span.stat`를 뺀 글자 · `html_text`), 분야(`div.sub-tit`의 `:` 뒤를 쉼표로), 주최(`div.organ`), 날수(`div.day`의 `D-N` · `D+N`), 상태(`span.dday`)를 읽는다.

**테스트 관점** 저장한 쪽 15건 · 첫 공고의 제목에서 배지가 빠짐 · `D-5` · `마감임박`

#### wevity.parse_detail_end wevity 상세의 접수마감일

**시그니처** `parse_detail_end(response: httpx.Response) -> date`

**처리** 글자에서 `접수기간` 뒤의 첫 `YYYY-MM-DD ~ YYYY-MM-DD`를 찾아 뒤 날짜. 못 찾으면 `FormatError`.

**테스트 관점** 110675 → 2026-10-07

#### wevity.deadline_of 날수로 접수마감일

**시그니처** `deadline_of(item: WevityItem, base_date: date, offset: int) -> date | None`

**처리** if 날수가 없음 → `None` · if `D-N` → 기준일 + N + 보정값 · else(`D+N`, 마감 뒤) → 기준일 − N + 보정값. 마감 뒤인 공고는 마감 판정에서 버려진다.

**테스트 관점** 보정값 0 · −1 · `D+3`

#### WevitySource.collect wevity 수집

**시그니처** `collect(http: SourceHttp, base_date: date, page_cap: int) -> Collected`

**근거** [[CCR-API-001#GET/www.wevity.com/?c=find]] · [[CCR-SEQ-001#SEQ-2]]

**처리**
1. 분야 다섯(20 · 21 · 22 · 3 · 1)을 차례로, 분야마다 1쪽부터 읽는다. 쪽 상한은 다섯 분야 합산이다.
2. 쪽마다 `ix`로 합친다. 이미 본 공고면 분야만 더한다.
3. if 그 쪽의 마지막 공고가 상태 `마감` · 빈 쪽 → 그 분야를 멈춤. 첫 쪽 위쪽 홍보 칸의 마감 공고로는 멈추지 않는다([[CCR-DOM-002]] 5장 결정 8).
4. `_calibrate`로 보정값을 잰다.
5. 합친 공고마다 대회로 맞춘다. if 제목이 없거나 `ix` · `href`가 모두 없음 → 탈락. 링크 `?c=find&s=1&gbn=view&ix={ix}`, `ix`를 못 읽으면 목록 링크를 절대 주소로(원천 ID도 그것). 접수시작일은 없다. 부가 정보는 분야와 주최.
6. 보정 결과를 `notes`로.

**테스트 관점** 다섯 분야가 같은 쪽을 줘도 15건 · 쪽 상한 합산 · 1쪽 가운데의 마감 공고로 멈추지 않고 2쪽 끝의 마감에서 멈춤

#### WevitySource._calibrate 날수 맞춰 보기

**시그니처** `_calibrate(http: SourceHttp, items: list[WevityItem], base_date: date) -> tuple[int, str]`

**근거** [[CCR-API-001#GET/www.wevity.com/?c=find&gbn=view]]

**처리**
1. 상태가 `접수중` · `마감임박`이고 `D-N`이며 `ix`가 있는 첫 공고를 고른다. if 없음 → (−1, 사유).
2. 상세 `?c=find&s=1&gbn=view&ix=…`를 받는다. 목록 요청과 달리 이 요청은 리디렉션(`gbn=viewok`로의 302)을 따라간다. if 실패 · 날짜를 못 읽음 → (−1, 사유).
3. 보정값 = (상세의 마감일 − 기준일) − N. if 0 · −1이 아님 → (−1, 사유) · else (보정값, 설명).

**테스트 관점** 저녁처럼 맞으면 0 · 아침처럼 목록이 하루 많으면 −1 · 상세 404면 −1 · 2026-09-28 09:02에 −1(실측)

#### WevitySource.missing_config wevity 설정 누락

**시그니처** `missing_config() -> bool`

**처리** 늘 거짓. 자격증명이 필요 없다.

**테스트 관점** 없음(늘 거짓)

#### aifactory.extract_payload 페이로드 꺼내기

**시그니처** `extract_payload(html: str) -> str`

**처리** `self.__next_f.push([1,"…"])` 조각을 모두 찾아 JSON 문자열로 풀어 이어 붙인다. 조각이 없으면 `FormatError`.

**테스트 관점** 페이로드가 없는 페이지는 `FormatError`

#### aifactory.parse_tasks 과제 읽기

**시그니처** `parse_tasks(payload: str) -> list[Task]`

**처리**
1. 줄마다 `키:JSON`으로 읽는다. 읽은 객체를 키로 기억한다(`$키` 참조를 풀기 위해).
2. 객체를 깊이 40까지 돌며 `id` · `name` · `page`와 `endDate` 또는 `participationDeadline`을 가진 것을 과제로 모은다.
3. `id`는 정수로 바꾼다. 같은 id는 한 번만. 페이지 이름은 `{"name"}` 객체이거나 `$키`가 가리키는 객체의 이름이다.
4. 접수시작일 = `participationStartDate` · 없으면 `startDate`, 마감일 = `participationDeadline` · 없으면 `endDate`. `1970-01-01`로 시작하는 값은 없는 것으로 본다.

**테스트 관점** 저장한 페이지에서 과제 112건 · `1970` 마감일은 `None`

#### aifactory.parse_page AI팩토리 페이지

**시그니처** `parse_page(response: httpx.Response) -> list[Task]`

**처리** `parse_tasks(extract_payload(본문))`. if 과제가 없음 → `FormatError`.

**테스트 관점** 저장한 페이지에서 과제 112건 · 페이로드가 없는 페이지는 `FormatError`

#### aifactory.group_tasks 같은 대회의 과제 합치기

**시그니처** `group_tasks(tasks: list[Task]) -> list[list[Task]]`

**처리** 페이지 이름과 접수시작일이 같은 과제끼리 모은다. id 차례.

**테스트 관점** 112건 → 88개

#### aifactory.competition_name 대회명 정하기

**시그니처** `competition_name(page: str, tasks: list[Task], start: date | None) -> str`

**근거** [[CCR-API-001#GET/aifactory.space/ko/competition]] 대회명

**처리** 앞에서 정해지면 뒤는 보지 않는다.
1. if 페이지 이름에 연도(20으로 시작하는 네 자리)가 있고 그 연도가 접수시작일의 해나 다음 해 → 페이지 이름.
2. if 과제가 하나 → 그 과제명.
3. 과제명들의 공통 앞부분을 정리한다(앞뒤 공백 · 끝의 `_ - : ·` · 짝이 맞지 않는 여는 괄호부터 끝까지를 뗀다). if 10자 이상 → 그것.
4. 머리 꼬리표(`[…]` · `(…)`) 하나를 뗀 과제명으로 3을 다시. if 10자 이상 → 그것.
5. 가장 작은 id의 과제명. 다만 그것이 주제 번호(`주제 1` · `문제1` · `[분야1]` · `track` 등)로 시작하고 페이지 이름이 있으면 페이지 이름.

**테스트 관점** 9304 · 9235 · 9159 · 6684 · 2367의 이름 · 기관명 페이지는 이름이 되지 않음 · 공통 앞부분의 끝 구분 기호 떼기 · 꼬리표를 떼고 다시 보기 · 주제 번호면 페이지 이름

#### aifactory.to_competition 과제 묶음을 대회로

**시그니처** `to_competition(group: list[Task]) -> Competition | None`

**처리** 이름 있는 과제만 쓴다. if 없음 → `None`. 원천 ID는 가장 작은 id, 링크 `https://aifactory.space/competitions/{id}`, 접수시작일은 가장 이른 값, 마감일은 가장 늦은 값. if 시작일 > 마감일 → 시작일을 비운다. 부가 정보는 페이지 이름과 과제명들.

**테스트 관점** 다섯 대회의 날짜와 링크

#### AiFactorySource.collect AI팩토리 수집

**시그니처** `collect(http: SourceHttp, base_date: date, page_cap: int) -> Collected`

**처리** 목록 한 쪽을 `GET`해 `parse_page`로 과제를 읽고, `group_tasks`로 묶은 뒤 묶음마다 `to_competition`. `None`이면 그 묶음의 과제 수만큼 탈락이다. 수집 건수는 합치기 전 과제의 수다([[CCR-DOM-001#SourceResult]]).

**테스트 관점** 수집 건수는 과제 112건, 대회는 88개

#### AiFactorySource.missing_config AI팩토리 설정 누락

**시그니처** `missing_config() -> bool`

**처리** 늘 거짓. 자격증명이 필요 없다.

**테스트 관점** 없음(늘 거짓)

#### contestkorea.parse_list 콘테스트코리아 목록 한 쪽

**시그니처** `parse_list(response: httpx.Response) -> list[CkItem]`

**처리** `div.list_style_2`가 없으면 `FormatError`. `div.list_style_2 > ul > li`마다 `div.title > a`의 `str_no`, 대회명(`span.txt` · `html_text`), 분야(`span.category`), 주최 · 대상(`ul.host`), 접수 기간(`span.step-1`의 `MM.DD~MM.DD`), 날수(`span.day`의 `D-N`).

**테스트 관점** 저장한 쪽 12건 · 첫 공고의 접수 기간 8/18 ~ 9/27 · D-0

#### contestkorea.resolve_dates 접수 날짜의 연도 정하기

**시그니처** `resolve_dates(base_date: date, period: tuple[int, int, int, int] | None, days: int | None) -> tuple[date | None, date | None]`

**근거** [[CCR-API-001#GET/www.contestkorea.com/sub/list.php]]

**처리**
1. if 날수가 없음 → (None, None). 연도를 정할 수 없다.
2. 어림 = 기준일 + N. if 접수 기간이 없음 → (None, 어림).
3. 마감일 = 찍힌 `MM.DD`를 어림의 전 · 같은 · 다음 해로 놓아 어림에 가장 가까운 날. 날수가 하루 어긋나도 찍힌 날짜를 쓴다.
4. 시작일 = 마감일의 해에 찍힌 시작 `MM.DD`. if 그것이 마감일보다 뒤 → 한 해 앞.

**테스트 관점** 오늘 마감 · 날수가 하루 어긋남 · 해를 넘기는 접수 기간 · 날수 없음

#### ContestKoreaSource.collect 콘테스트코리아 수집

**시그니처** `collect(http: SourceHttp, base_date: date, page_cap: int) -> Collected`

**처리** 분야 둘(`030310001` · `031410001`)을 차례로, 접수 마감이 이른 차례의 쪽(12건)을 읽는다. 쪽 상한은 합산이다. `str_no`로 합치고 분야를 더한다. if 12건보다 적은 쪽 → 그 분야를 멈춤. 링크 `/sub/view.php?int_gbn=1&str_no={str_no}`, 날짜는 `resolve_dates`, 부가 정보는 분야 · 주최 · 대상.

**테스트 관점** 두 분야의 쪽 요청 차례 · 합쳐서 12건 · 링크와 마감일

#### ContestKoreaSource.missing_config 콘테스트코리아 설정 누락

**시그니처** `missing_config() -> bool`

**처리** 늘 거짓. 자격증명이 필요 없다.

**테스트 관점** 없음(늘 거짓)

### 2.4 선별

#### matching.normalize_title 대회명 정규화

**시그니처** `normalize_title(title: str) -> str`

**근거** [[CCR-UC-001#UC-S4]] 판정 4 · 5단계 · [[CCR-PRD-001]] 5.2

**처리**
1. `clean_text` 뒤 NFKC로 맞춘다(전각 → 반각).
2. 머리의 대괄호 묶음(`[…]` · `【…】` · `〔…〕`, 여럿이면 모두)을 뗀다. 다만 떼면 글자가 남지 않으면(대회명 전체가 대괄호 안) 떼지 않는다.
3. 괄호 안이 날짜뿐인 것을 뗀다. 날짜 말은 `년 월 일 시 분 까지 마감 접수 연장 오전 오후 요일`과 요일 글자다. if 숫자가 있음 → 숫자 · `~ - . : / ,` · 날짜 말만 있으면 뗀다 · else → 세 글자 이하이고 날짜 말만이면 뗀다(`(금)` · `(마감)` · `(접수)` · `(오후)`). 안쪽 괄호부터 네 번까지 되풀이한다(`(~9/20(금))`).
4. 꼬리말을 뗀다. 끝의 기호를 떼고, 끝이 `모집` · `공고` · `안내`(앞에 떨어진 `참가자` · `참가팀` · `참여자` · `참가` · `작품`이 있으면 함께)면 뗀다. 바뀌지 않을 때까지 되풀이하되 글자가 남지 않게 되면 멈춘다(`모집 공고`).
5. `2026년` → `2026`.
6. 글자와 숫자만 남기고(`[\W_]` 제거) 소문자로.

`참가자 모집`을 함께 떼는 것은 [[CCR-PRD-001]] 5.2 검증의 유사도 0.85(`2026년 Big Data 활용 대회 참가자 모집` · `[부산광역시] Big Data 활용 대회`)를 재현하는 규칙이다.

**출력** 정규화한 대회명. 비어 있을 수 있다.

**테스트 관점** 꼬리말 · 대괄호 머리말 · 괄호 날짜 · `2026년` · 전체가 대괄호인 대회명 · 회차 괄호는 남김 · BOM · PRD의 유사도 0.94 · 0.85를 재현

#### matching.extract_marks 연도 · 회차 뽑기

**시그니처** `extract_marks(title: str) -> tuple[frozenset[int], frozenset[int]]`

**처리** `clean_text` · NFKC 뒤, 연도는 앞뒤에 숫자가 붙지 않은 `20xx`. 회차는 `제N회` · `제N차` · `제N기` · `N회차` · `N회`(뒤에 한글이 붙지 않음) · `Nst · Nnd · Nrd · Nth` · `N기`(뒤에 한글이 붙지 않음). 괄호 안의 날짜에 든 연도도 연도로 센다.

**테스트 관점** `2026` · `제5회` · `The 2nd … 2026` · `16기` · `[제5차]` · `20251`은 연도가 아님

#### matching.normalize_link 링크 정규화

**시그니처** `normalize_link(link: str | None) -> str | None`

**처리** 비었으면 `None`. 호스트가 없으면 그대로. 쿼리에서 `utm_`로 시작하는 것과 `fbclid`만 뗀다. 원천 ID가 쿼리에 있는 소스(wevity · 콘테스트코리아)가 있어 쿼리를 통째로 떼지 않는다. `http`는 `https`로, 호스트는 소문자로, 경로 끝의 `/`는 뗀다.

**테스트 관점** wevity 링크의 `ix`는 남고 추적 매개변수만 빠짐 · 대소문자 · 끝 `/`

#### matching.key_of_competition 대회의 판정 값

**시그니처** `key_of_competition(competition: Competition) -> MatchKey`

**처리** 출처 · 원천 ID · 정규화한 링크와, 대회명에서 뽑은 정규화 대회명 · 연도 · 회차 · 글자 집합, 접수시작일 · 마감일을 담는다. 목록 항목이 아니다(`from_list=False`).

**테스트 관점** [[#matching.judge_pair]]의 테스트가 함께 본다

#### matching.key_of_entry 목록 항목의 판정 값

**시그니처** `key_of_entry(entry: ListEntry) -> MatchKey`

**처리** 출처 · 원천 ID와 정규화한 링크를 싣고 목록 항목으로 표시한다(`from_list=True`). 나머지는 [[#matching.key_of_competition]]과 같다. 링크는 소스 개편으로 원천 ID가 바뀐 공고를 잇는 예비다([[CCR-DOM-001#ListEntry]]).

**테스트 관점** 원천 ID가 같으면 1단계 · 링크만 같고 연도가 다르면 다름([[#matching.judge_pair]])

#### matching.key_of_history 처리 이력 기록의 판정 값

**시그니처** `key_of_history(record: HistoryRecord) -> MatchKey`

**처리** 출처 · 원천 ID를 싣고 링크는 싣지 않는다. 링크는 목록 항목과 견줄 때만 쓴다.

**테스트 관점** 작년 공고를 3단계로 가름([[#matching.judge_pair]])

#### matching.similarity 대회명 유사도

**시그니처** `similarity(a: MatchKey, b: MatchKey) -> float`

**처리**
1. if 두 길이의 합이 0 · 2 × 짧은 길이 < 0.90 × 합 → 0.
2. 한쪽에만 있는 글자는 적어도 한 번씩 나오므로, 맞는 글자 수 ≤ min(la − 한쪽에만 있는 글자 수, lb − …). if 2 × 그 상한 < 0.90 × 합 → 0.
3. `SequenceMatcher(autojunk=False)`의 `quick_ratio`가 0.90 미만 → 0 · else `ratio()`.

거르기는 0.90에 닿을 수 없는 짝만 건너뛴다. 결과를 바꾸지 않는다.

**테스트 관점** `2026 · 2025 한국관광 데이터랩` 0.94 · `Big Data`는 비율이 0.85라 0.90에 닿을 수 없어 계산하지 않고 0

#### matching.judge_pair 두 대회가 같은가

**시그니처** `judge_pair(a: MatchKey, b: MatchKey) -> PairResult`

**근거** [[CCR-UC-001#UC-S4]] 판정표 · [[CCR-SEQ-001#SEQ-3]]

**처리** 앞 단계에서 결론이 나면 뒤는 보지 않는다.
1. if 원천 ID가 있고 출처 · 원천 ID가 같음 → 같음(1단계, 확실).
2. if 둘 다 `ONE_ID_PER_COMPETITION`(Kaggle)의 같은 소스이고 원천 ID가 둘 다 있음(이미 1에서 같지 않음) → 다름(1단계). Kaggle은 같은 대회를 두 번 올리지 않는다.
3. if 한쪽이 목록 항목이고 두 링크(정규화)가 같음 → 둘 다 연도가 있는데 겹치지 않거나 둘 다 회차가 있는데 겹치지 않으면 다름(2단계) · else 같음(1단계, 확실). 이 경우 3단계는 보지 않는다.
4. 2단계: if 둘 다 연도가 있음 → 맞대 봄 표시, 겹치지 않으면 다름. 회차도 같다.
5. 3단계: if `a.start`와 `b.deadline`이 있음 → 맞대 봄, `a.start > b.deadline`이면 다름. 반대 방향도 같다. if 두 마감일이 있음 → 맞대 봄, 180일 넘게 떨어지면 다름.
6. if 한쪽 정규화 대회명이 비었음 → 판단하지 않음.
7. 4단계: if 정규화 대회명이 같음 → 같음(4단계, 확실 = 맞대 봤는가).
8. 5단계: 유사도 ≥ 0.90 → 같음(5단계, 유사도, 확실 = 맞대 봤는가) · else 판단하지 않음(유사도).

연도 · 회차가 "다르다"는 두 집합이 겹치지 않는 것이다. `2025-2026`과 `2026`은 다르지 않다.

**출력** `PairResult`

**테스트 관점** 2단계로 가르는 PRD 예 · 작년 공고를 3단계로 가름 · 마감 180일 · 마감 연장은 같음(4단계 · 확실) · 1단계는 날짜가 바뀌어도 같음 · 목록 항목의 링크가 같아도 연도가 다르면 다름 · 이름만으로 같으면 확실하지 않음 · 문턱 미만은 판단하지 않음 · PRD의 0.82 짝은 판단하지 않음 · 0.90 경계 · Kaggle은 원천 ID가 다르면 다름(ARC-AGI-2 · 3, 묶지도 않음) · 다른 소스는 같은 소스 안의 중복 공고를 그대로 같다고 봄 · slug가 다른 Kaggle 목록 항목은 다름

#### matching.group 후보끼리 묶기

**시그니처** `group(competitions: list[Competition], keys: list[MatchKey]) -> list[list[int]]`

**근거** [[CCR-UC-001#UC-S4]] 4 · 4b

**처리**
1. 모든 짝에 `judge_pair`. 같음은 (단계, −유사도, 앞선 쪽의 (우선순위 · 원천 ID · 대회명), 뒤쪽의 같은 것)로 차례를 매기고, 같음인 짝의 집합을 따로 둔다.
2. 같음을 그 차례로 보며 두 묶음을 합친다. if 두 묶음을 가로지르는 짝 가운데 같음이 아닌 것(다름 · 판단하지 않음)이 하나라도 있음 → 합치지 않는다(먼저 본 짝 쪽 묶음에 남는다). 같다는 짝을 사슬로만 잇지 않는다([[CCR-DOM-002]] 5장 결정 7).
3. 묶음마다 구성원 번호 목록.

**테스트 관점** 연도 없는 공고가 두 해의 공고를 잇지 못함 · A~B · B~C가 같아도 A–C가 판단하지 않음이면 C는 따로 · 이름 틀이 비슷한 공모전 셋은 묶이지 않음 · 소스가 다른 같은 공고는 묶임

#### matching.representative_order 대표를 고르는 차례

**시그니처** `representative_order(competition: Competition) -> tuple[int, int, str]`

**처리** (−채워진 접수 날짜 수, 소스 우선순위, 원천 ID). 가장 작은 것이 대표다([[CCR-UC-001#UC-S4]] 4a).

**테스트 관점** 날짜가 더 채워진 event-us가 DACON보다 먼저

#### Bundle.deadline 묶음의 접수마감일

**시그니처** `deadline() -> date | None`

**처리** 속성. 구성원 접수마감일 가운데 가장 늦은 값 · 없으면 `None`. 오늘 마감인지 가를 때만 쓴다([[CCR-DOM-002]] 5장 결정 1).

**테스트 관점** [[#ScreenService.judge]]의 테스트가 함께 본다(오늘 마감 구성원이 있어도 더 늦은 구성원이 있으면 미룸)

#### ScreenService.drop_expired 마감 지난 대회 버리기

**시그니처** `drop_expired(competitions: list[Competition]) -> tuple[list[Competition], int]`

**근거** [[CCR-UC-001#UC-S3]]

**처리** if 상시 연습용 → 버림 · else if 접수마감일 < 기준일 → 버림 · else 남김(오늘 마감 · 마감일 없음 포함). 버린 수를 함께 돌려준다.

**테스트 관점** 어제 마감 · 오늘 마감 · 마감 모름 · 연습용

#### ScreenService.bundle 묶음 만들기

**시그니처** `bundle(competitions: list[Competition]) -> list[Bundle]`

**처리** 대회마다 `key_of_competition`, `group`으로 묶고, 묶음마다 `representative_order`가 가장 작은 구성원을 대표로, 구성원의 판정 값(`keys`)을 함께 싣는다. 묶음 수와 여럿인 묶음 수를 로그에.

**테스트 관점** 대표 고르기

#### ScreenService.build_known 아는 대회 모으기

**시그니처** `build_known(entries: list[ListEntry], history: list[HistoryRecord]) -> KnownSet`

**근거** [[CCR-UC-001#UC-S4]] 3 · [[CCR-UC-001#UC-A1]] 1b6

**처리**
1. 목록 항목마다 `Known(list, key_of_entry, keep)`. 참가자가 지운 항목도 파일에 남아 있어 그대로 아는 대회다([[CCR-UC-001#UC-S4]] 3).
2. 처리 이력 기록마다 `(출처, 원천 ID)`를 `history_ids`에 넣는다. if 버림을 없는 것으로 봄 이고 버림 → 넣지 않음 · else `Known(history, key_of_history, 그 결과)`.
3. 넣을 때 색인 셋(`by_id` · `by_link`(목록 항목만) · `by_title`)을 채운다.

**테스트 관점** 버림 무시면 버림 기록과 같은 공고가 아는 대회가 아님 · 목록 항목은 원천 ID로도 링크로도 찾힘

#### KnownSet.add 아는 대회 하나 넣기

**시그니처** `add(known: Known) -> None`

**처리** 목록에 붙이고 색인 셋을 채운다. 출처 · 원천 ID가 있으면 `by_id`, 목록 항목이고 링크가 있으면 `by_link`, 정규화 대회명이 있으면 `by_title`.

**테스트 관점** [[#ScreenService.build_known]]의 테스트가 함께 본다

#### ScreenService.split_known 아는 대회로 빠진 묶음 빼기

**시그니처** `split_known(bundles: list[Bundle], known: KnownSet) -> tuple[list[Bundle], int]`

**근거** [[CCR-UC-001#UC-S4]] 5 · 6 · 7

**처리** 묶음마다 `_matches`. if 짝이 없음 → 모르는 묶음 · else 처리 결과 `known`, 짝을 싣고 `_record_known`.

**출력** (모르는 묶음, 아는 대회로 빠진 묶음의 수)

**테스트 관점** 원천 ID가 같은 기록 · 목록 항목이 버림 기록을 이겨 남김으로 적힘 · 이름만 같으면 빼되 적지 않음 · 작년 기록은 올해 공고를 막지 않음

#### ScreenService._matches 묶음과 같은 아는 대회 찾기

**시그니처** `_matches(bundle: Bundle, known: KnownSet) -> list[tuple[Known, PairResult]]`

**처리**
1. 후보 좁히기. 구성원마다 `by_id`(같은 출처 · 원천 ID) · `by_link`(같은 링크) · `by_title`(같은 정규화 대회명)과, 모든 아는 대회 가운데 유사도 0.90에 닿을 수 있는 것(`similarity`의 1 · 2와 같은 거르기).
2. 후보마다 모든 구성원과 `judge_pair`.
3. if 1단계로 같은 구성원이 있음 → 짝(그 결과). 다른 구성원의 2 · 3단계는 보지 않는다.
4. else if 다름인 구성원이 있음 → 건너뜀.
5. else if 같음인 구성원이 있음 → 짝(확실한 것 · 앞선 단계 · 높은 유사도 차례로 가장 좋은 결과).

**테스트 관점** `split_known`의 테스트가 함께 본다. 기록 5,000줄 · 후보 600건에 2초 안팎(실측)

#### ScreenService._record_known 아는 대회로 빠진 묶음 적기

**시그니처** `_record_known(bundle: Bundle, matches: list[tuple[Known, PairResult]], known: KnownSet) -> None`

**근거** [[CCR-UC-001#UC-S4]] 6 · [[CCR-DOM-002]] 5장 결정 2

**처리**
1. 1단계가 아닌 짝이면 무엇과 같았는지(단계 · 유사도)를 로그에.
2. 확실한 짝만 모은다. if 없음 → 적지 않음(이름만으로 같음).
3. 결과 = 남김 if 확실한 짝 가운데 남김(목록 항목 · 남김 기록)이 있음 · else 버림.
4. `history_ids`에 없는 구성원만 `entries_for(묶음, 결과, 그 구성원)`으로 `RecordService.append`.

**테스트 관점** 자기 기록이 없는 구성원만 적고 날짜는 대표의 것으로 채움 · 목록 항목과 버림 기록이 함께면 남김

#### screen.entries_for 처리 이력에 적을 값

**시그니처** `entries_for(bundle: Bundle, result: Result, members: list[Competition] | None = None) -> list[HistoryEntry]`

**처리** 구성원(또는 주어진 구성원)마다 한 줄. 같은 (출처, 원천 ID)는 한 번만. 접수시작일 · 마감일이 없으면 대표의 값으로 채운다([[CCR-UC-001]] 0.1).

**테스트 관점** 대표의 날짜로 채우기

#### ScreenService.judge 관심 분야 판별

**시그니처** `judge(bundles: list[Bundle]) -> JudgeOutcome`

**근거** [[CCR-UC-001#UC-S5]] · [[CCR-SEQ-001#SEQ-4]]

**처리**
1. if 묶음이 없음 → 빈 결과. 부르지 않는다.
2. 접수마감일이 이른 차례로 놓는다.
3. if 판별기가 없음(OpenAI 키 없음) → 모든 묶음 판별 실패, 원인 `missing_key` · else `_ask_all`, 원인 `call_failed`.
4. 판별 실패 묶음에 표시를 한다.
5. if 판별 실패 × 2 > 묶음 수 → 실패 묶음 가운데 묶음의 접수마감일 ≠ 기준일인 것은 미룸(처리 결과 `deferred`), 나머지는 넣을 묶음에 · else 실패 묶음을 모두 넣을 묶음에.
6. if 미룬 것이 있음 → 원인을 싣는다.
7. 넣을 묶음을 접수마감일이 이른 차례로.

**출력** `JudgeOutcome`

**테스트 관점** 버림은 적히고 남김은 돌아옴 · 실패가 절반 이하면 남김 · 절반 초과면 오늘 마감만 남기고 미룸(적지 않음) · 치명 오류 뒤로 묻지 않음 · 키가 없으면 `missing_key` · 오늘 마감 구성원이 있어도 더 늦은 구성원이 있으면 미룸 · 미리보기는 쓰지 않음

#### ScreenService._ask_all 동시에 묻기

**시그니처** `_ask_all(bundles: list[Bundle], outcome: JudgeOutcome) -> list[Bundle]`

**처리**
1. 스레드 넷(설정값)에 묶음마다 `ask`를 맡긴다. `ask`: if 멈춤 표시 → `Stopped` · if 치명 오류 표시 → 묻지 않고 실패 · else `judge.judge(대표)`. `JudgeError(fatal)`이면 치명 오류 표시를 켠다. 그 밖의 예외도 그 묶음의 실패다.
2. 끝나는 차례대로 받는다. if 실패 → 실패 목록 · else if 남김 → 근거를 싣고 넣을 묶음에 · else(버림) → 처리 결과 `discarded`, 버림 수 +1, `append(entries_for(묶음, 버림))`. 결과와 근거를 로그에.
3. 예외(신호 등)가 나면 기다리지 않고 풀을 닫는다(`cancel_futures`).

**출력** 판별 실패 묶음

**테스트 관점** `judge`의 테스트가 함께 본다

#### Judge.judge 판별 포트

**시그니처** `judge(competition: Competition) -> Answer`

**처리** 포트. 묶음의 대표 하나가 관심 분야인지 묻는다. 실패하면 `JudgeError`. 구현은 [[#OpenAiJudge.judge]]이고, 테스트는 가짜를 넣는다.

**테스트 관점** [[#ScreenService.judge]]의 테스트가 가짜 판별기로 본다

#### OpenAiJudge.judge 판별 모델에 묻기

**시그니처** `judge(competition: Competition) -> Answer`

**근거** [[CCR-API-001#POST/api.openai.com/v1/responses]] · [[CCR-API-001]] 1.3 · 2.2

**처리** 최대 1 + 2번.
1. if 멈춤 표시 → `Stopped`.
2. `responses.parse(model, instructions=CRITERIA, input=build_input, text_format=Relevance, reasoning={effort: none}, max_output_tokens=300, store=false, timeout=30)`.
3. if 검증 예외(스키마 불일치 · 잘림) → `JudgeError`.
4. if 상태 오류 → 401 · 403 · 404와 429 중 `code`가 크레딧 · 지출 한도 넷이거나 `type`이 `insufficient_quota` → `JudgeError(fatal)` · else if 408 · 409 · 429 · 5xx 이고 마지막이 아님 → 2 · 4초 쉬고 다시 · else `JudgeError`.
5. if 연결 오류 · 타임아웃 → 마지막이면 `JudgeError` · else 쉬고 다시.
6. 응답: if `status ≠ completed` → `JudgeError(status · 사유)` · if `output_parsed`가 없음(거절) → `JudgeError` · else `Answer(decision == keep, reason)`.

**예외** 다시 물어도 같은 답 → `JudgeError(fatal=True)` · 이 묶음만 → `JudgeError`

**테스트 관점** 요청 모양(모델 · 기준 · 추론 없음 · 저장 안 함 · 300 · 입력) · 버림 · 치명 넷은 한 번만 · 400은 한 번만 · 속도 제한과 503 뒤 성공 · 타임아웃 세 번이면 실패 · incomplete · 거절 · 스키마 불일치는 한 번만

#### openai_judge.build_input 판별 입력

**시그니처** `build_input(competition: Competition) -> str`

**처리** `대회명: …` · `출처: …` · (있으면) `부가 정보: …`를 줄로. 부가 정보는 쉼표로 잇고 800자에서 자른다.

**테스트 관점** 긴 부가 정보가 잘림

### 2.5 목록

#### ListEntry.id 식별자

**시그니처** `id() -> str`

**처리** 속성. `f"{source}:{source_id}"`. 파일에 적힌 `id`를 믿지 않고 두 값에서 만든다([[CCR-DOM-003#competitions]] · [[CCR-DOM-002#ListEntry]]).

**테스트 관점** [[#ListEntry.from_dict]]의 테스트가 함께 본다(적힌 `id`가 달라도 두 값으로)

#### ListEntry.to_dict 목록 항목 한 줄

**시그니처** `to_dict() -> dict[str, Any]`

**처리** [[CCR-DOM-003#competitions]]의 필드 아홉. `id`는 속성에서, 날짜는 ISO, 없으면 `null`.

**테스트 관점** [[#ListService.append]]의 테스트가 함께 본다(줄의 필드 아홉과 `id`)

#### ListEntry.from_dict 목록 항목 한 줄 읽기

**시그니처** `from_dict(data: dict[str, Any]) -> ListEntry`

**처리** if 필수 다섯(`source` · `source_id` · `title` · `link` · `collected_on`) 가운데 없거나 빈 것이 있음 → `ValueError`. 날짜가 `YYYY-MM-DD`가 아니면 `ValueError`([[CCR-DOM-003#competitions]]). `reason`은 없으면 `""`. 적힌 `id`는 읽지 않는다.

**테스트 관점** [[#ListService.load]]의 테스트가 함께 본다(필수 필드 없음 · 날짜 깨짐)

#### list.entry_of 대표에서 항목 만들기

**시그니처** `entry_of(competition: Competition, base_date: date, reason: str) -> ListEntry`

**근거** [[CCR-UC-001#UC-S6]] 1 · [[CCR-DOM-001#ListEntry]]

**처리** 대표의 출처 · 원천 ID · 대회명 · 링크 · 접수시작일 · 접수마감일에 기준일(`collected_on`)과 판별 근거를 붙인다. 근거는 앞뒤 공백을 떼고 300자에서 자른다. `domains/list/models.py`에 있다.

**테스트 관점** 값 여덟이 대표와 기준일에서 옴 · 근거가 없으면 `""`

#### ListService.load 목록 파일 읽기

**시그니처** `load() -> ListFile`

**근거** [[CCR-UC-001#UC-S4]] 1 · 1a · 1b · [[CCR-SEQ-001#SEQ-3]]

**처리**
1. if 쓰는 실행 → `ListCrud.reset_appends`.
2. `ListCrud.read`. if `None`(파일 없음) → 빈 목록, `exists=False` · if `ListReadFailed` → `error`에 사유를 담고 돌려준다(로그) · else 항목들. 식별자가 겹친 줄이 있으면 로그.
3. 읽은 식별자 집합을 기억해 `append`가 쓴다.

**출력** `ListFile`

**테스트 관점** 첫 실행 · 깨진 줄 · 필수 필드 없음 · 식별자가 겹친 줄은 모두 아는 대회 · 미리보기는 추가분 폴더를 만들지 않음

#### ListFile.ids 식별자 집합

**시그니처** `ids() -> set[str]`

**처리** 읽은 항목의 `id` 집합. `append`의 중복 확인이 쓴다.

**테스트 관점** [[#ListService.append]]의 테스트가 함께 본다

#### ListService.append 목록 파일에 더하기

**시그니처** `append(competition: Competition, base_date: date, reason: str) -> ListEntry | None`

**근거** [[CCR-UC-001#UC-S6]] 1 · 2 · 2a · 4 · 4a · [[CCR-SEQ-001#SEQ-5]]

**처리**
1. `entry_of`로 항목을 만든다.
2. if 식별자가 읽은 목록이나 이번 추가분에 있음 → `None`(로그).
3. if 쓰지 않는 실행 → 항목만 돌려준다.
4. 추가분에 쌓고 쌓인 전부를 `write_appends`로 통째로 바꿔 쓴다. 항목을 돌려준다.

**테스트 관점** 두 번 더하면 두 줄 · 같은 식별자는 두 번째에 `None` · 읽은 목록에 있으면 `None` · 임시 파일이 남지 않음 · 미리보기는 쓰지 않고 항목만

#### ListService.appended_count 이번 실행에 더한 항목 수

**시그니처** `appended_count() -> int`

**처리** 속성. 이번 실행에 추가분에 쌓은 항목의 수. `RunLine.loaded`와 같다.

**테스트 관점** 미리보기는 0

#### ListCrud.read 목록 파일 읽기

**시그니처** `read() -> list[ListEntry] | None`

**처리** if 파일이 없음 → `None`. 바이트로 읽고 줄마다(빈 줄은 건너뜀) UTF-8 · JSON 객체 · `ListEntry.from_dict`. 하나라도 실패하면 `ListReadFailed(몇 번째 줄)`. 열지 못해도 같다. 식별자가 겹친 줄은 그대로 돌려준다.

**테스트 관점** `load`의 테스트가 함께 본다

#### ListCrud.reset_appends 추가분 비우기

**시그니처** `reset_appends() -> None`

**처리** 목록 추가분(`competitions.jsonl`)을 빈 파일로 통째로 바꿔 쓴다([[#record._atomic_write]]와 같은 방법). 추가분 폴더가 데이터 폴더와 같으면 만들 때 거부한다.

**테스트 관점** [[#ListService.load]]의 테스트가 함께 본다

#### ListCrud.write_appends 목록 추가분 쓰기

**시그니처** `write_appends(lines: list[dict[str, Any]]) -> None`

**처리** 받은 줄 전부를 JSON Lines로 목록 추가분에 통째로 바꿔 쓴다.

**테스트 관점** [[#ListService.append]]의 테스트가 함께 본다

### 2.6 기록

#### HistoryRecord.of 처리 이력 기록 만들기

**시그니처** `of(entry: HistoryEntry, base_date: date, run_id: str) -> HistoryRecord`

**처리** 선별이 정한 값에 기준일과 실행 식별자를 붙인다. 기록 경계는 묶음을 모른다([[CCR-DOM-001]] 4.2 규칙 5).

**테스트 관점** [[#RecordService.append]]의 테스트가 함께 본다(날짜와 실행 식별자)

#### HistoryRecord.to_dict 처리 이력 한 줄

**시그니처** `to_dict() -> dict[str, Any]`

**처리** [[CCR-DOM-003#processed]]의 필드 아홉. 날짜는 ISO, 없으면 `null`.

**테스트 관점** [[#RecordService.append]]의 테스트가 함께 본다

#### HistoryRecord.from_dict 처리 이력 한 줄 읽기

**시그니처** `from_dict(data: dict[str, Any]) -> HistoryRecord`

**처리** if 필수 넷(`source` · `source_id` · `result` · `run_id`) 가운데 없거나 빈 것이 있음 → `ValueError`. 나머지는 없으면 빈 값이고, 날짜를 읽지 못하면 `None`.

**테스트 관점** [[#RecordService.load]]의 테스트가 함께 본다(필수 필드 없음)

#### SourceLine.to_dict 소스별 건수 한 칸

**시그니처** `to_dict() -> dict[str, Any]`

**처리** `collected` · `normalized` · `failure`.

**테스트 관점** [[#RecordService.write_run]]의 테스트가 함께 본다

#### RunWarning.to_dict 경고 한 칸

**시그니처** `to_dict() -> dict[str, Any]`

**처리** `kind`와, 있는 것만 `source` · `last_nonzero`(ISO) · `cause`. 빈 속성은 쓰지 않는다.

**테스트 관점** [[#RecordService.write_run]]의 테스트가 함께 본다(경고의 빈 속성은 없음)

#### RunLine.fail 실패로 바꾸기

**시그니처** `fail(reason: FailureReason) -> None`

**처리** 결과를 실패로 바꾸고 사유를 적는다. 결과 중단의 줄은 이 클래스가 만들지 않는다(마무리 단계).

**테스트 관점** [[#Pipeline._run]]의 테스트가 함께 본다(실패 사유)

#### RunLine.to_dict 실행 요약 한 줄

**시그니처** `to_dict() -> dict[str, Any]`

**처리** [[CCR-DOM-003#runs]]의 필드 열셋. 소스는 이름마다 `SourceLine.to_dict`, 경고는 `RunWarning.to_dict`의 목록이다.

**테스트 관점** [[#RecordService.write_run]]의 테스트가 함께 본다(줄의 필드 열셋)

#### RecordService.start 데이터 폴더 준비와 추가분 비우기

**시그니처** `start() -> None`

**근거** [[CCR-INFRA-001]] 6.2 · [[CCR-DOM-002]] 5장 결정 5 · [[CCR-SEQ-001#SEQ-1]]

**처리** `RecordCrud.prepare`(기본 브랜치 밖이면 origin/main의 세 파일을 꺼냄). 그다음 if 목록에 쓰는 실행 → 추가분 두 파일을 빈 파일로 바꿔 쓴다 · else 아무것도 하지 않는다. `Pipeline`이 `ListService.load`보다 먼저 부르므로 목록 파일도 꺼내진 뒤에 읽힌다.

**테스트 관점** 미리보기는 추가분 폴더를 만들지 않음 · 브랜치 실행은 main 판을 꺼냄

#### RecordService.load 기록 파일 읽기

**시그니처** `load() -> State`

**근거** [[CCR-UC-001#UC-S4]] 2 · 2a · 2b · [[CCR-SEQ-001#SEQ-3]]

**처리**
1. `read_history` → `read_runs`. 데이터 폴더는 `start`가 이미 준비했다.
2. if `HistoryReadFailed` → `history_error`에 사유를 담고 돌려준다(로그).
3. 처리 이력(없으면 빈 것과 `history_exists=False`) · 실행 요약. 읽히지 않는 줄이 있으면 로그.

**출력** `State`

**테스트 관점** 첫 실행 · 깨진 줄 · 필수 필드 없음 · 읽히지 않는 실행 요약 줄 세기

#### State.keep_count 지금 남김 기록의 수

**시그니처** `keep_count() -> int`

**처리** 속성. 읽은 처리 이력에서 결과가 남김인 기록의 수.

**테스트 관점** [[#RecordService.history_shrank]]의 테스트가 함께 본다

#### State.last_keep_count 마지막으로 적힌 남김 수

**시그니처** `last_keep_count() -> int | None`

**처리** 실행 요약 줄을 뒤에서부터 보며 정수인 `keep_count`의 첫 값. 없으면 `None`. 불리언은 정수로 치지 않는다.

**테스트 관점** [[#RecordService.history_shrank]]의 테스트가 함께 본다

#### RecordService.history_shrank 남김 기록이 줄었나

**시그니처** `history_shrank(state: State) -> bool`

**근거** [[CCR-UC-001#UC-S4]] 2c · 2a2

**처리** 마지막으로 적힌 `keep_count`(뒤에서부터 첫 정수)를 찾는다. if 없음 → 거짓 · else 지금 남김 수(처리 이력 파일이 없으면 0) < 그 값 → 참(로그).

**테스트 관점** 줄어듦 · 파일이 없는데 적힌 수가 있음 · 첫 실행

#### RecordService.append 처리 이력 적기

**시그니처** `append(entries: list[HistoryEntry]) -> None`

**근거** [[CCR-UC-001#UC-S4]] 6 · [[CCR-UC-001#UC-S5]] 5 · [[CCR-UC-001#UC-S6]] 4

**처리** if 쓰지 않는 실행 · 빈 목록 → 아무것도 하지 않음. 값마다 `HistoryRecord.of(값, 기준일, 실행 식별자)`를 쌓고, 쌓인 전부를 `write_history_appends`로 통째로 바꿔 쓴다.

**테스트 관점** 두 번 적으면 두 줄 · 날짜와 실행 식별자 · 임시 파일이 남지 않음 · 미리보기는 쓰지 않음

#### RecordService.appended_count 이번 실행에 적은 줄 수

**시그니처** `appended_count() -> int`

**처리** 속성. 이번 실행에 쌓은 처리 이력 줄의 수.

**테스트 관점** 미리보기는 아무것도 적지 않음(`test_preview_writes_nothing`)

#### RecordService.zero_count_warnings 소스 0건 경고

**시그니처** `zero_count_warnings(results: list[SourceResult], state: State, days: int) -> list[RunWarning]`

**근거** [[CCR-UC-001#UC-S7]] 2 · 2a · 2b

**처리** 오류 없이 대회 0건을 낸 소스마다:
1. 실행 요약 줄에서 그 소스의 값이 있고 실패가 없는 줄만, 기준일마다 모은다(하루에 하나라도 1건 이상이면 건수를 낸 날).
2. if 오늘이 건수를 낸 날(같은 날 앞선 실행) → 경고 없음.
3. 오늘 앞의 날들을 최근부터 보며 0건인 날을 지나친 뒤, 건수를 낸 날이 이어진 수를 센다(기록이 없는 날은 끊지도 잇지도 않는다).
4. if 그 수 ≥ `days` → 경고(소스, 그 가운데 가장 최근 날) · else 없음.

**테스트 관점** 사흘 건수 뒤 0건 · 연속이 모자람 · 실패한 줄과 빈 날은 건너뛰고 같은 날은 합침 · 첫 실행 · 실패한 소스

#### RecordService.write_run 실행 요약 줄 쓰기

**시그니처** `write_run(line: RunLine) -> None`

**처리** if 쓰지 않는 실행 → 아무것도 하지 않음 · else `line.to_dict()`를 추가분 `runs.jsonl`에 한 줄로 바꿔 쓴다. `keep_count`는 `null`이다.

**테스트 관점** 줄의 필드 열셋 · `keep_count`가 비어 있음 · 경고의 빈 속성은 없음

#### RecordCrud.read_history 처리 이력 읽기

**시그니처** `read_history() -> list[HistoryRecord] | None`

**처리** if 파일이 없음 → `None`. 바이트로 읽고 줄마다(빈 줄은 건너뜀) UTF-8 · JSON 객체 · `HistoryRecord.from_dict`. 하나라도 실패하면 `HistoryReadFailed(몇 번째 줄)`. 열지 못해도 같다.

**테스트 관점** `load`의 테스트가 함께 본다

#### RecordCrud.read_runs 실행 요약 읽기

**시그니처** `read_runs() -> RunsFile`

**처리** if 파일이 없음 → 빈 것. 줄마다 UTF-8 · JSON을 읽고, 객체이며 `run_id` · `base_date`가 있으면 줄로, 아니면 `corrupt` +1. 파일을 열지 못하면 `HistoryReadFailed`.

**테스트 관점** 깨진 줄 둘을 세고 하나를 읽음

#### RecordCrud.prepare 데이터 폴더 준비

**시그니처** `prepare() -> None`

**처리** if main 판을 꺼내야 함 → [[#record.export_main_state]] · else 아무것도 하지 않는다([[CCR-DOM-002]] 5장 결정 5).

**테스트 관점** [[#record.export_main_state]]의 테스트가 함께 본다

#### RecordCrud.reset_appends 추가분 비우기

**시그니처** `reset_appends() -> None`

**처리** 추가분 두 파일을 빈 파일로 통째로 바꿔 쓴다([[#record._atomic_write]]).

**테스트 관점** [[#RecordService.start]]의 테스트가 함께 본다

#### RecordCrud.write_history_appends 처리 이력 추가분 쓰기

**시그니처** `write_history_appends(lines: list[dict[str, Any]]) -> None`

**처리** 받은 줄 전부를 JSON Lines로 처리 이력 추가분에 통째로 바꿔 쓴다.

**테스트 관점** [[#RecordService.append]]의 테스트가 함께 본다(두 번 적으면 두 줄 · 임시 파일이 남지 않음)

#### RecordCrud.write_run_append 실행 요약 추가분 쓰기

**시그니처** `write_run_append(line: dict[str, Any]) -> None`

**처리** 줄 하나를 실행 요약 추가분에 통째로 바꿔 쓴다.

**테스트 관점** [[#RecordService.write_run]]의 테스트가 함께 본다

#### record._atomic_write 통째로 바꿔 쓰기

**시그니처** `_atomic_write(path: Path, text: str) -> None`

**처리** 폴더를 만들고, 같은 폴더에 새 이름의 임시 파일을 만들어 쓰고 `fsync`한 뒤 `os.replace`로 바꾼다. 도중에 예외가 나면 임시 파일을 지우고 다시 낸다. `reset_appends` · `write_history_appends` · `write_run_append`가 쓴다([[CCR-INFRA-001]] 6.2).

**테스트 관점** 임시 파일이 남지 않음

#### record.export_main_state main 판 꺼내기

**시그니처** `export_main_state(repo_root: Path, dest: Path) -> Path`

**근거** [[CCR-UC-001#UC-A1]] 1b7 · [[CCR-INFRA-001]] 4.1 · [[CCR-SEQ-001#SEQ-8]]

**처리**
1. if 저장소가 얕게 받은 것 → `--depth=1`을 붙인다(개발자 PC의 저장소는 얕게 만들지 않는다).
2. `git fetch origin +refs/heads/main:refs/remotes/origin/main`. if 실패(git이 없거나 60초 안에 끝나지 않음 포함) → `HistoryReadFailed`.
3. 세 파일(`competitions.jsonl` · `processed.jsonl` · `runs.jsonl`)마다: 대상 파일을 지우고, if `origin/main:data/{파일}`이 있음 → `git show`로 꺼내 쓴다 · else 없는 채로 둔다.

**테스트 관점** 작업 트리에 다른 사본이 있어도 main 판을 읽음 · 목록 파일도 꺼냄 · 원격이 없으면 읽기 실패 · git이 없으면 읽기 실패

### 2.7 실행의 흐름

#### __main__.main 입구

**시그니처** `main(argv: list[str] | None = None) -> int`

**근거** [[CCR-INFRA-001]] 5.4 · 8.1 · [[CCR-SEQ-001#SEQ-1]] · [[CCR-SEQ-001#SEQ-10]]

**처리**
1. 인자를 읽는다. 하위 명령 없음 → 하루치 · `collect [--source 이름] [--show]` → 수집만.
2. 환경 변수를 모은다. if Actions 밖 → 저장소 루트 `.env`의 값을 없는 이름에만 더한다.
3. if Actions 안 → `register_actions_masks(비밀값)`. 어떤 출력보다 먼저.
4. `setup_logging(비밀값)` · 신호 처리기(SIGINT · SIGTERM). 처리기는 if 이미 멈춤 표시 → `Stopped`를 낸다 · else 멈춤 표시를 켠다.
5. `run_collect` 또는 `run_batch`.
6. if `RunModeError` → 2 · if `Stopped` → 로그를 비우고 판별 스레드를 기다리지 않고 130으로 끝낸다 · if 그 밖의 예외 → 스택을 로그에 남기고 1.

**출력** 종료 코드

**테스트 관점** Actions에서 `DRY_RUN`이 비면 2(실측) · 시크릿이 없어도 설정 누락으로 끝내지 않음

#### __main__.run_batch 하루치

**시그니처** `run_batch(env: dict[str, str], stop: threading.Event) -> int`

**처리** `RunContext` · `Settings` · `Secrets`를 만들고 서비스를 조립한다. 소스 여섯(Kaggle에 토큰), `ListService`(`ListCrud`에 데이터 폴더 · 추가분 폴더), `RecordCrud`(main 판을 꺼내야 하면 저장소 루트), `OpenAiJudge`(키가 있을 때만). 반드시 있어야 하는 시크릿은 없다([[CCR-UC-001#UC-A1]] 1d1). `Pipeline.run`의 결과가 성공이면 0 · else 1.

**테스트 관점** `Pipeline`의 테스트가 조립된 흐름을 본다

#### __main__.run_collect 수집만

**시그니처** `run_collect(env: dict[str, str], stop: threading.Event, only: str | None, show: bool) -> int`

**처리** 소스를 (이름이 주어지면 그 하나만) `CollectService`로 돌리고 소스마다 결과 한 줄, `--show`면 대회마다 한 줄(원천 ID · 접수 기간 · 대회명 · 링크)을 찍는다. OpenAI를 부르지 않고 파일에 아무것도 쓰지 않는다. 하나라도 성공하면 0. 사이트 개편을 가를 때 쓴다([[CCR-UC-001#UC-A3]]).

**테스트 관점** 실측으로 다섯 소스 성공 · Kaggle 설정 누락(2026-09-27) · 토큰을 넣고 여섯 소스 성공(2026-10-01)

#### __main__.sources_of 소스 여섯

**시그니처** `sources_of(secrets: Secrets) -> list[Source]`

**처리** 어댑터 여섯을 만든다. 이 차례가 수집 결과와 실행 요약의 소스 차례다. Kaggle에만 토큰을 준다.

**테스트 관점** 없음(조립만 한다)

#### Pipeline.run 한 실행

**시그니처** `run() -> RunLine`

**근거** [[CCR-UC-001#UC-A1]] · [[CCR-SEQ-001#SEQ-1]]

**처리** 시작 시각을 재고, 줄(실행 식별자 · 기준일 · 종류)을 만들고, 실행 정보를 로그에. if 버림 무시를 청했는데 쓰는 실행 → 무시한다고 로그. `RecordService.start` → `_run` → `_finish`.

**출력** `RunLine`

**예외** 신호 → `Stopped`(줄을 쓰지 않음)

**테스트 관점** 아래 `_run` · `_load` · `_finish`의 테스트 · 신호면 줄이 비어 있음

#### Pipeline._run 기본 흐름과 실패 건너뛰기

**시그니처** `_run(line: RunLine) -> tuple[State, list[SourceResult]]`

**근거** [[CCR-UC-001#UC-A1]] 1d1 · 2 ~ 7 · 2b · 5a · [[CCR-SEQ-001#SEQ-9]]

**처리** 단계 사이마다 멈춤 표시를 본다.
1. `collect_all` → 줄의 `sources`, `dropped.normalize`(소스 탈락의 합).
2. `ListService.load` → `RecordService.load`.
3. if 모든 소스가 실패 → `fail(all_sources_failed)`, 끝.
4. `drop_expired` → `dropped.expired`.
5. if 목록 파일 읽기 오류 → `fail(list_read_failed)`, 끝 · if 처리 이력 읽기 오류 → `fail(history_read_failed)`, 끝 · if `history_shrank` → `fail(history_shrank)`, 끝.
6. `build_known(목록 항목, 처리 이력)` → `bundle` → `split_known` → `dropped.known`.
7. `judge` → `dropped.discarded` · `judge_failed` · `deferred`. if 미룸 → 경고 `judge_deferred`(원인).
8. `_load(넣을 묶음)`.

실패 사유는 넷뿐이다. 반드시 있어야 하는 시크릿이 없어 설정 누락은 없다([[CCR-DOM-003#runs]]).

**테스트 관점** 정상 흐름의 건수 · 전 소스 실패 · 목록 파일 읽기 실패와 처리 이력 읽기 실패는 판별하지 않음 · 처리 이력 감소 · 실패한 소스가 있어도 성공 · 시크릿 없이도 수집함

#### Pipeline._load 목록 파일에 더하기

**시그니처** `_load(line: RunLine, bundles: list[Bundle]) -> None`

**근거** [[CCR-UC-001#UC-S6]] · [[CCR-UC-001#UC-A1]] 7 · 1b3 · [[CCR-SEQ-001#SEQ-5]]

**처리**
1. if 넣을 묶음이 없음 → 끝.
2. 묶음마다(멈춤 표시 확인) `ListService.append(대표, 기준일, 묶음의 판별 근거)`: if 항목 → 처리 결과 `loaded`, `loaded` +1 · if `None`(이미 있음) → 처리 결과 `known`, 로그. 어느 쪽이든 곧바로 `RecordService.append(entries_for(묶음, 남김))`.
3. 넣은(또는 미리보기라면 넣었을) 대회의 이름 · 출처 · 근거를 한 줄씩 로그.

넣는 일에는 실패가 없다. 노션 때의 컬럼 확인 · 행 생성 실패 · 오늘 마감 미적재는 없어졌다([[CCR-DOM-001#Warning]]).

**테스트 관점** 넣은 묶음마다 항목 한 줄과 남김 줄 · 이미 있는 식별자는 항목 없이 남김만 · OpenAI 키가 없으면 오늘 마감만 넣음 · 미리보기는 파일에 쓰지 않음

#### Pipeline._finish 실행 기록

**시그니처** `_finish(line: RunLine, state: State, results: list[SourceResult], started: float) -> None`

**근거** [[CCR-UC-001#UC-S7]] · [[CCR-SEQ-001#SEQ-6]]

**처리** 소스 0건 경고를 경고 목록 앞에 넣는다. if 실행 요약에 읽히지 않는 줄 → 경고 `summary_corrupt`. 소요 시간을 적고 `write_run`. 경고와 결과 요약을 로그에. if 성공이 아님 → 실패 로그.

**테스트 관점** 줄의 실행 식별자 · 기준일 · 소스 건수

### 2.8 마무리 단계

#### finish.finish 추가분 올리기

**시그니처** `finish(env: Mapping[str, str], git: Git) -> Outcome`

**근거** [[CCR-UC-001#UC-A1]] 9 · 9a · \*a2 · [[CCR-INFRA-001]] 8.2 · [[CCR-SEQ-001#SEQ-7]]

**입력** `RUN_ID` · `RUN_STARTED_AT` · `GITHUB_EVENT_NAME` · `APPEND_DIR`. `Git`(작업 폴더 · 원격 · 토큰)

**처리**
1. 기준일(`RUN_STARTED_AT`의 KST 날짜) · 종류를 구하고 `read_additions`. 형식이 맞지 않은 줄이 있으면 실패 표시. if 배치의 줄이 없음 → 중단으로 보고 실패 표시.
2. 다섯 번까지:
   1. `fresh_main`.
   2. if `runs.jsonl`에 이 실행 식별자의 줄이 있음 → 끝(표시에 따라 0 · 1). 앞선 push가 응답만 끊기고 들어간 것이다.
   3. 목록 추가분을 붙인다(`existing_ids`에 있는 식별자의 줄은 건너뛰고 로그). 처리 이력 추가분을 붙인다. 남김 줄을 센다.
   4. 붙일 줄 = 배치의 줄에 `keep_count`를 채운 것 · 없으면 `{run_id, base_date, kind, result: aborted, keep_count}`.
   5. 올리는 추가분을 로그에 찍고 `commit_and_push(실행 기록 {기준일} · {실행 식별자} · {결과})`. `data/status.json`은 읽지도 스테이징하지도 않는다.
   6. if 성공 → 끝(표시에 따라 0 · 1) · if `GitError` → 로그, 처음부터.
3. 다섯 번 모두 실패 → 1.

**출력** `Outcome(종료 코드, 설명)`

**테스트 관점** 목록 · 처리 이력과 줄을 붙이고 남김 수를 채움 · 이미 있는 식별자는 건너뜀 · 상태 파일은 건드리지 않음 · 작성자 봇 · 메시지 · 줄이 없으면 중단 줄과 1 · 형식이 틀린 줄은 빼고 1 · 이미 올린 실행은 다시 붙이지 않음 · 그사이 올라온 관리자 커밋 위에 다시 얹고 그 수정이 남음 · 빈 저장소의 첫 실행

#### finish.read_additions 추가분 읽기

**시그니처** `read_additions(append_dir: Path, run_id: str) -> Additions`

**처리** 목록 추가분의 줄마다: if JSON 객체이고 필수 여섯(`id` · `source` · `source_id` · `title` · `link` · `collected_on`)이 비어 있지 않음 → 붙일 줄 · else 로그와 거절 +1([[CCR-DOM-003#competitions]]). 처리 이력 추가분의 줄마다: if JSON 객체이고 필수 넷(`source` · `source_id` · `result` · `run_id`)이 비어 있지 않음 → 붙일 줄 · else 로그와 거절 +1. 실행 요약 추가분의 줄마다: if JSON 객체이고 `run_id` · `base_date` · `kind` · `result`가 있고 `run_id`가 이 실행 → 배치의 줄 · else 거절 +1.

**테스트 관점** `finish`의 테스트가 함께 본다

#### finish.base_date_of 마무리 단계의 기준일

**시그니처** `base_date_of(started_at: str | None) -> str`

**처리** `RUN_STARTED_AT`(ISO, `Z` 허용. 시간대가 없으면 UTC로 본다)을 KST 날짜로. 없으면 지금. 배치의 기준일과 같은 값이 된다([[CCR-UC-001]] 0.1).

**테스트 관점** KST 기준일

#### finish.has_run 이 실행의 줄이 있나

**시그니처** `has_run(runs_path: Path, run_id: str) -> bool`

**처리** 실행 요약 파일의 줄마다 JSON으로 읽어 `run_id`가 같은 줄이 있으면 참. 읽히지 않는 줄은 건너뛴다.

**테스트 관점** [[#finish.finish]]의 테스트가 함께 본다(이미 올린 실행은 다시 붙이지 않음)

#### finish.count_keep 남김 기록 세기

**시그니처** `count_keep(history_path: Path) -> int`

**처리** 처리 이력 파일에서 `result`가 `keep`인 줄의 수. 읽히지 않는 줄은 건너뛴다.

**테스트 관점** [[#finish.finish]]의 테스트가 함께 본다(남김 수를 채움)

#### finish.existing_ids 목록에 이미 있는 식별자

**시그니처** `existing_ids(list_path: Path) -> set[str]`

**처리** 목록 파일의 줄마다 JSON으로 읽어 `id`를 모은다. 읽히지 않는 줄과 `id`가 없는 줄은 건너뛴다. 파일이 없으면 빈 집합([[CCR-INFRA-001]] 8.2 3).

**테스트 관점** [[#finish.finish]]의 테스트가 함께 본다(이미 있는 식별자는 건너뜀)

#### Git.fresh_main main 최신 판 받기

**시그니처** `fresh_main() -> None`

**처리** if 작업 폴더에 저장소가 있음 → `fetch --depth=1 origin main` · `reset --hard FETCH_HEAD` · `clean -fdx` · else 폴더를 지우고 `clone --depth=1 --branch main`. 받는 명령에만 `http.extraheader`로 토큰을, 모든 명령에 느린 연결 끊기(`lowSpeedLimit` 1000 · `lowSpeedTime` 20)를 준다. 명령마다 60초 제한. 실패하면 `GitError`(git의 오류 문구만. 명령은 찍지 않는다).

**테스트 관점** 되풀이 때 최신 판으로 맞춰짐(`finish`의 경합 테스트)

#### Git.commit_and_push 커밋하고 올리기

**시그니처** `commit_and_push(message: str) -> None`

**처리** 세 경로(`data/competitions.jsonl` · `data/processed.jsonl` · `data/runs.jsonl`) 가운데 있는 것만 `add`한다(첫 실행에는 목록 파일과 처리 이력 파일이 없을 수 있다). 작성자 `github-actions[bot]`으로 커밋하고 `push origin HEAD:refs/heads/main`(토큰은 이 명령에만).

**테스트 관점** 빈 저장소의 첫 실행

#### finish.append_lines 파일 끝에 줄 붙이기

**시그니처** `append_lines(path: Path, lines: list[str]) -> None`

**처리** if 줄이 없음 → 아무것도 하지 않음. 폴더를 만들고, if 파일이 줄바꿈으로 끝나지 않음 → 줄바꿈을 먼저 붙인 뒤 줄마다 줄바꿈과 함께 붙인다.

**테스트 관점** 줄바꿈으로 끝나지 않는 파일

#### finish.main 마무리 단계 입구

**시그니처** `main() -> int`

**처리** 환경 변수 `RUN_ID` · `APPEND_DIR` · `RUNNER_TEMP` · `GITHUB_REPOSITORY` 가운데 없는 것이 있으면 1. 원격 주소와 `Git(RUNNER_TEMP/finish-main, 원격, GITHUB_TOKEN)`으로 [[#finish.finish]]를 부르고, 설명을 찍은 뒤 종료 코드를 돌려준다.

**테스트 관점** 없음. 흐름은 [[#finish.finish]]의 테스트가 본다

## 3. 미결사항

2026-10-01에 Kaggle의 필드 이름 · 연습용 표기 · 쪽 크기를 실측해 닫았다([[#kaggle.parse_page]] · [[#KaggleSource.collect]] · [[#http.new_client]]).

- [ ] 페이지의 순수 함수(`parseListFile` · `mergeChange` · `commitMessage` 등)를 이 문서에 둘지. 지금은 [[CCR-DOM-002]] 4.11의 시그니처만 있다
