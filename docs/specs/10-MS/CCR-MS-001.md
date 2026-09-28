---
doc_id: CCR-MS-001
type: MS
title: MINISPEC — 대회 수집 배치
status: draft
upstream: [CCR-DOM-002, CCR-DOM-003, CCR-SEQ-001, CCR-API-001, CCR-UC-001]
---

# MINISPEC — 대회 수집 배치

## 0. 이 문서가 다루는 것

클래스 명세([[CCR-DOM-002]])의 메서드와 모듈 함수 하나하나가 무엇을 받아 무엇을 하는지다. 시간순 흐름은 [[CCR-SEQ-001]], 타입은 [[CCR-DOM-002]] 2.4, 줄 형식은 [[CCR-DOM-003]]에서만 찾는다.

- 항목 ID는 `클래스.메서드` 또는 `접두어.함수`다. 접두어는 모듈이 있는 곳이다. 파일 이름과 같으면 그 파일(`matching` · `eventus` · `dacon` · `kaggle` · `wevity` · `aifactory` · `contestkorea` · `openai_judge` · `settings` · `logging` · `dates` · `text` · `http` · `robots` · `finish`), 그 밖은 경계 이름이다. `screen` = `domains/screen/service.py`, `notion` = `domains/notion/service.py`, `record` = `domains/record/crud.py`, `__main__` = `collector/__main__.py`.
- 처리가 몇 줄이면 간략형(시그니처 · 처리 · 테스트 관점)으로 쓴다.
- 날짜는 모두 KST 날짜(`date`)다. 기준일은 `RunContext.base_date` 하나다.
- 테스트 관점은 `batch/tests/`에 있는 테스트가 확인하는 것이다. 테스트가 아니라 손으로 재 본 것은 (실측)이라 적는다.

## 1. 함수 목록

| 모듈 | 함수 |
|---|---|
| core · shared | [[#RunContext.from_env]] · [[#Settings.load]] · [[#Secrets.from_env]] · [[#settings.read_dotenv]] · [[#logging.secret_variants]] · [[#logging.register_actions_masks]] · [[#SecretFilter.filter]] · [[#dates.parse_to_kst_date]] · [[#dates.kst_date_of]] · [[#dates.kst_midnight_utc]] · [[#text.clean_text]] · [[#text.html_text]] |
| infra | [[#SourceHttp.fetch]] · [[#http.parse_retry_after]] · [[#robots.ensure_allowed]] · [[#NotionHttp.read]] · [[#NotionHttp.write]] |
| 수집 | [[#CollectService.collect_all]] · [[#CollectService._collect_one]] · [[#eventus.build_query]] · [[#eventus.normalize]] · [[#EventUsSource.collect]] · [[#dacon.normalize]] · [[#DaconSource.collect]] · [[#kaggle.normalize]] · [[#kaggle.is_practice]] · [[#KaggleSource.collect]] · [[#wevity.parse_list]] · [[#wevity.parse_detail_end]] · [[#wevity.deadline_of]] · [[#WevitySource.collect]] · [[#WevitySource._calibrate]] · [[#aifactory.extract_payload]] · [[#aifactory.parse_tasks]] · [[#aifactory.group_tasks]] · [[#aifactory.competition_name]] · [[#aifactory.to_competition]] · [[#contestkorea.parse_list]] · [[#contestkorea.resolve_dates]] · [[#ContestKoreaSource.collect]] |
| 선별 | [[#matching.normalize_title]] · [[#matching.extract_marks]] · [[#matching.normalize_link]] · [[#matching.similarity]] · [[#matching.judge_pair]] · [[#matching.group]] · [[#matching.representative_order]] · [[#ScreenService.drop_expired]] · [[#ScreenService.bundle]] · [[#ScreenService.build_known]] · [[#ScreenService.split_known]] · [[#ScreenService._matches]] · [[#ScreenService._record_known]] · [[#screen.entries_for]] · [[#ScreenService.judge]] · [[#ScreenService._ask_all]] · [[#OpenAiJudge.judge]] · [[#openai_judge.build_input]] |
| 노션 | [[#NotionService.read_rows]] · [[#notion.row_of]] · [[#NotionService.check_columns]] · [[#notion.check_schema]] · [[#NotionService.create_row]] · [[#notion.properties_of]] · [[#NotionCrud.query_pages]] |
| 기록 | [[#RecordService.start]] · [[#RecordService.load]] · [[#RecordService.history_shrank]] · [[#RecordService.append]] · [[#RecordService.zero_count_warnings]] · [[#RecordService.write_run]] · [[#RecordCrud.read_history]] · [[#RecordCrud.read_runs]] · [[#record._atomic_write]] · [[#record.export_main_state]] |
| 실행의 흐름 | [[#__main__.main]] · [[#__main__.run_batch]] · [[#__main__.run_collect]] · [[#Pipeline.run]] · [[#Pipeline._run]] · [[#Pipeline._load]] · [[#Pipeline._finish]] |
| 마무리 단계 | [[#finish.finish]] · [[#finish.read_additions]] · [[#Git.fresh_main]] · [[#Git.commit_and_push]] · [[#finish.append_lines]] |

## 2. 함수

### 2.1 core · shared

#### RunContext.from_env 실행 문맥 만들기

**시그니처** `RunContext.from_env(env: Mapping[str, str], *, now: datetime | None = None) -> RunContext`

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

**시그니처** `Settings.load(env: Mapping[str, str], path: Path | None = None) -> Settings`

**처리**
1. `batch/settings.toml`(또는 `path`)을 읽어 `source` · `notion` · `judge` · `warning` 표를 타입에 맞춰 옮긴다.
2. 판별 모델 = `OPENAI_MODEL`(앞뒤 공백을 뗀 값) if 비어 있지 않음 · else `settings.toml`의 기본값.

**테스트 관점** 쪽 상한 20 · 예산 120 · 쓰기 타임아웃 70 · 동시 4 · 0건 연속 3일 · `OPENAI_MODEL`이 덮고 공백은 무시

#### Secrets.from_env 비밀값 읽기

**시그니처** `Secrets.from_env(env) -> Secrets` · `Secrets.values() -> list[str]`

**처리** 네 이름(`NOTION_TOKEN` · `NOTION_DATA_SOURCE_ID` · `OPENAI_API_KEY` · `KAGGLE_API_TOKEN`)을 읽고 앞뒤 공백을 뗀다. 빈 문자열은 `None`이다. 등록되지 않은 시크릿은 빈 문자열로 들어오기 때문이다([[CCR-INFRA-001]] 5장). `values()`는 있는 값만.

**테스트 관점** 빈 값 · 공백만 있는 값이 `None`

#### settings.read_dotenv 로컬 .env 읽기

**시그니처** `read_dotenv(path: Path) -> dict[str, str]`

**처리** 파일이 없으면 빈 것. 줄마다 `#`로 시작하거나 `=`가 없는 줄은 건너뛰고, `export ` 머리를 떼고, 값의 짝이 맞는 따옴표를 뗀다. 로컬 실행에서만 부르고 이미 있는 환경 변수가 이긴다([[#__main__.main]]).

**테스트 관점** 주석 · 따옴표 · `export` · 빈 값 · 깨진 줄

#### logging.secret_variants 가릴 문자열

**시그니처** `secret_variants(values: Iterable[str]) -> list[str]`

**처리**
1. 값마다 그대로 넣는다.
2. if 32자리 16진 → 하이픈을 넣은 UUID 꼴도 · else if UUID 꼴 → 하이픈을 뺀 소문자 꼴도. 노션은 오류 메시지에 ID를 하이픈 꼴로 싣는다([[CCR-INFRA-001]] 5.4).
3. 겹친 것을 빼고 긴 것부터 둔다. 짧은 값이 긴 값의 일부를 먼저 지우지 않게.

**테스트 관점** 노션 ID의 두 꼴이 모두 나온다

#### logging.register_actions_masks Actions에 가릴 값 알리기

**시그니처** `register_actions_masks(values, emit=None) -> None`

**처리** `secret_variants`의 값마다 `::add-mask::값`을 표준 출력에 찍는다. 어떤 로그보다 먼저 부른다. Actions 안에서만 부른다.

**테스트 관점** 변형마다 한 줄

#### SecretFilter.filter 로그 가리기

**시그니처** `SecretFilter(values).filter(record: LogRecord) -> bool`

**처리**
1. 메시지를 완성한 뒤(`getMessage`) 변형마다 `***`로 바꾸고 `args`를 비운다.
2. if 예외가 붙음 → 예외 원문을 미리 만들어(`exc_text`) 같이 가린다. 포매터는 이미 만든 원문을 다시 만들지 않는다.
3. 늘 참을 돌려준다(기록은 버리지 않는다).

**테스트 관점** 메시지와 예외 원문 모두에서 UUID 꼴이 사라진다

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

**시그니처** `clean_text(value) -> str`

**근거** [[CCR-UC-001#UC-S2]] 4

**처리** `None`은 빈 문자열. 앞과 뒤에서 공백(줄바꿈 · NBSP 포함)이나 서식 문자(유니코드 범주 `Cf`: BOM · 폭 없는 공백 등)인 글자를 뗀다. 가운데는 건드리지 않는다. JSON 소스의 대회명과 판정의 정규화 첫머리에 쓴다.

**테스트 관점** 앞의 BOM 셋과 뒤의 폭 없는 공백이 빠지고 가운데 NBSP는 남는다

#### text.html_text HTML 글자 다듬기

**시그니처** `html_text(value) -> str`

**처리** 이어진 공백을 하나로 모은 뒤 `clean_text`. 브라우저가 보여 주는 글자와 같다. HTML 소스(wevity · 콘테스트코리아)의 대회명에 쓴다.

**테스트 관점** 줄바꿈 · 탭 · NBSP가 공백 하나로

### 2.2 infra

#### SourceHttp.fetch 소스에 요청

**시그니처** `fetch(method, url, *, parse, params=None, json=None, headers=None, follow_redirects=False, accept_client_errors=False) -> T`

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

#### http.parse_retry_after Retry-After 읽기

**시그니처** `parse_retry_after(value: str | None, now=None) -> float | None`

**처리** if 비었음 → `None` · if 숫자 → 그 초(음수는 0) · else if HTTP 날짜 → 지금부터의 초 · else `None`.

**테스트 관점** 초 · 날짜 · 읽지 못하는 값

#### robots.ensure_allowed robots.txt 확인

**시그니처** `ensure_allowed(http: SourceHttp, origin: str, paths: Iterable[str]) -> None`

**근거** [[CCR-API-001]] 1.2 · [[CCR-UC-001#UC-S1]] 2

**처리**
1. `origin/robots.txt`를 `fetch`한다. 리디렉션은 다섯 번까지 따라가고(RFC 9309), 429를 뺀 4xx는 받아들인다. 429는 다른 요청처럼 다시 보내고 끝내 받지 못하면 실패다.
2. if 429를 뺀 4xx → 제한 없음. 끝.
3. 표준 라이브러리 `robotparser`로 읽고, 경로마다 에이전트 `competition-crawler`로 허용되는지 본다. 막힌 경로가 있으면 `RobotsDisallowed(경로)`.
4. 5xx · 연결 오류로 끝내 받지 못하면 `fetch`의 `HttpFailure`가 그대로 나간다(목록을 요청하지 않는다).

**테스트 관점** 허용 · 막힘 · 에이전트 이름 규칙 · 404는 제한 없음 · 503은 실패

#### NotionHttp.read 노션 읽기 요청

**시그니처** `read(method: str, path: str, json=None) -> dict`

**근거** [[CCR-API-001]] 2.3 · [[CCR-INFRA-001]] 8.5

**처리** 최대 1 + 3번.
1. 앞 요청과 1/3초 간격(읽기 · 쓰기 합쳐 초당 3회). 멈춤 표시면 `Stopped`.
2. 헤더 `Authorization: Bearer` · `Notion-Version: 2025-09-03` · User-Agent로 보낸다. 타임아웃 20초.
3. if 연결 오류 · 타임아웃 → 1 · 2 · 4초 쉬고 다시.
4. if 200 → JSON 객체면 돌려준다 · 아니면 쉬고 다시.
5. if 429 · 529 → `Retry-After`가 60초보다 길면 곧바로 `NotionFailure` · 있으면 그만큼 · 없으면 간격만큼 기다려 다시.
6. if 5xx → 쉬고 다시 · else(그 밖의 4xx) → `NotionFailure(status)`. 다시 보내지 않는다.
7. 다 쓰면 `NotionFailure(마지막 사유)`.

**예외** 끝내 실패 · 4xx → `NotionFailure`

**테스트 관점** 헤더 · 429 뒤 502 뒤 성공 · 404는 한 번만 · `Retry-After: 90`은 기다리지 않음 · 초당 3회 간격

#### NotionHttp.write 노션 쓰기 요청

**시그니처** `write(method: str, path: str, json) -> WriteResponse`

**근거** [[CCR-API-001]] 2.3 · [[CCR-UC-001#UC-S6]] 2a · 2c · 2d

**처리** 최대 1 + 3번. 간격과 헤더는 `read`와 같고 타임아웃은 70초다.
1. if 연결을 맺기 전 오류(연결 거부 · 연결 타임아웃 · 풀 타임아웃) → 요청이 닿지 않았다. 쉬고 다시.
2. if 그 밖의 연결 오류(읽기 타임아웃 · 끊김) → `NotionFailure(maybe_written=True)`. 다시 보내지 않는다.
3. if 200 → `WriteResponse(본문)`.
4. if 429 · 529 → `read`와 같이 기다려 다시.
5. if 503 이고 본문에 `additional_data.committed_resource_id` → `WriteResponse(committed_id=그 id)`.
6. else → `NotionFailure(status, maybe_written = 5xx인가)`. 다시 보내지 않는다.

**테스트 관점** 연결 거부 · 529 뒤 성공 · 500 · 502 · 503 · 409 · 400은 한 번만(5xx는 `maybe_written`) · 읽기 타임아웃은 한 번만 · 503과 새 행 id는 성공

### 2.3 수집

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

**시그니처** `build_query(base_date: date, page: int) -> dict`

**처리** [[CCR-API-001#POST/api.event-us.kr/api/v1/engine/search]]의 본문을 만든다. 쪽 크기 100. `all` 조건 넷(대회/공모전 · 진행 중 · 공개 · 무시되지 않음)과, `any` 조건(접수마감일이 기준일 KST 자정 이후 · 또는 접수마감일이 없고 행사 종료일이 기준일 이후이거나 없음). 접수마감일 오름차순.

**테스트 관점** 쪽 · 조건 · 기준일 자정이 UTC 전날 15시

#### eventus.normalize event-us 공고 하나

**시그니처** `normalize(item: dict) -> Competition | None`

**처리** 필드마다 `raw` 값을 읽는다. if `id` · 대회명 · `subdomain` 가운데 하나라도 없음 → `None`(탈락). 링크 `https://event-us.kr/{subdomain}/event/{id}`, 접수시작일 · 마감일은 UTC 시각을 KST 날짜로, 부가 정보는 분야 둘과 태그.

**테스트 관점** 저장한 쪽 40건이 모두 맞춰지고 135608의 날짜가 9/17 · 9/23 · `subdomain`이 없으면 탈락

#### EventUsSource.collect event-us 수집

**시그니처** `collect(http, base_date, page_cap) -> Collected`

**처리** 1쪽부터 `total_pages`까지 `POST`한다. if 쪽 번호 > 상한 → `page_cap_hit`으로 멈춤. 레코드마다 `normalize`, `None`이면 탈락.

**테스트 관점** 두 쪽을 차례로 읽음 · 상한에 닿으면 멈춤

#### dacon.normalize DACON 대회 하나

**시그니처** `normalize(item: dict) -> Competition | None` · `link_for(cpt_id, is_landing) -> str`

**처리** if `cpt_id` · `name`이 없음 → `None`. 링크는 `is_landing_cpt == 1`이면 `/competition/{id}/overview`, 아니면 `/competitions/official/{id}/overview/description`. 날짜는 `period_start` · `period_end`(시간대 없음 → KST). 부가 정보는 `keyword`를 `|`로 나눈 것.

**테스트 관점** 236746의 링크 · 날짜 · 키워드

#### DaconSource.collect DACON 수집

**시그니처** `collect(http, base_date, page_cap) -> Collected`

**처리** `offset` 0부터 상한까지 `GET ?offset=N&range=`. if 빈 쪽 → 멈춤. 쪽마다 맞춘 뒤, if 그 쪽에 접수마감일 ≥ 기준일인 대회가 없음 → 멈춤(종료일이 늦은 차례라 뒤쪽도 끝났다). 상한까지 가면 `page_cap_hit`.

**테스트 관점** 둘째 쪽에 접수 중인 대회가 없어 두 쪽에서 멈춤

#### kaggle.normalize Kaggle 대회 하나

**시그니처** `normalize(item: dict) -> Competition | None`

**처리** `ref`(전체 URL)의 마지막 조각이 원천 ID(slug). if slug · `title`이 없음 → `None`. 링크 `https://www.kaggle.com/competitions/{slug}`, 접수시작일 `enabledDate`, 접수마감일 `newEntrantDeadline` · 없으면 `deadline`(UTC → KST). 부가 정보는 `category`와 태그 이름. `practice = is_practice(category)`.

**테스트 관점** 새 참가 마감일을 쓰고 UTC 23:59가 KST 다음 날 · 연습용 표기 셋

#### kaggle.is_practice 상시 연습용 대회인가

**시그니처** `is_practice(category) -> bool`

**처리** 공백을 빼고 소문자로 바꾼 값이 `gettingstarted` · `playground` 가운데 하나인가. 상위 문서의 두 표기(`Getting Started` · `gettingStarted`)를 모두 맞게 견준다.

**테스트 관점** `Getting Started` · `gettingStarted` · `Playground`

#### KaggleSource.collect Kaggle 수집

**시그니처** `collect(http, base_date, page_cap) -> Collected`

**처리** 쪽마다 `POST ListCompetitions`(일반 탭 · 마감 늦은 차례 · 쪽 크기 100 · `pageToken`)에 `Authorization: Bearer 토큰`. if 다음 쪽 토큰이 없음 · 빈 쪽 · 그 쪽이 모두 마감됨 → 멈춤. 토큰이 없으면 `CollectService`가 부르지 않는다(`missing_config`).

**테스트 관점** Bearer 헤더 · 마감된 쪽에서 멈춤. 실측 전이다(3장)

#### wevity.parse_list wevity 목록 한 쪽

**시그니처** `parse_list(response) -> list[WevityItem]`

**처리** `ul.list`가 없으면 `FormatError`. 머리 줄(`li.top`)을 뺀 `li`마다 `div.tit a`의 `href`에서 `ix`, 제목(배지 `span.stat`를 뺀 글자 · `html_text`), 분야(`div.sub-tit`의 `:` 뒤를 쉼표로), 주최(`div.organ`), 날수(`div.day`의 `D-N` · `D+N`), 상태(`span.dday`)를 읽는다.

**테스트 관점** 저장한 쪽 15건 · 첫 공고의 제목에서 배지가 빠짐 · `D-5` · `마감임박`

#### wevity.parse_detail_end wevity 상세의 접수마감일

**시그니처** `parse_detail_end(response) -> date`

**처리** 글자에서 `접수기간` 뒤의 첫 `YYYY-MM-DD ~ YYYY-MM-DD`를 찾아 뒤 날짜. 못 찾으면 `FormatError`.

**테스트 관점** 110675 → 2026-10-07

#### wevity.deadline_of 날수로 접수마감일

**시그니처** `deadline_of(item, base_date, offset) -> date | None`

**처리** if 날수가 없음 → `None` · if `D-N` → 기준일 + N + 보정값 · else(`D+N`, 마감 뒤) → 기준일 − N + 보정값. 마감 뒤인 공고는 마감 판정에서 버려진다.

**테스트 관점** 보정값 0 · −1 · `D+3`

#### WevitySource.collect wevity 수집

**시그니처** `collect(http, base_date, page_cap) -> Collected`

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

**시그니처** `_calibrate(http, items, base_date) -> tuple[int, str]`

**근거** [[CCR-API-001#GET/www.wevity.com/?c=find&gbn=view]]

**처리**
1. 상태가 `접수중` · `마감임박`이고 `D-N`이며 `ix`가 있는 첫 공고를 고른다. if 없음 → (−1, 사유).
2. 상세 `?c=find&s=1&gbn=view&ix=…`를 받는다. 목록 요청과 달리 이 요청은 리디렉션(`gbn=viewok`로의 302)을 따라간다. if 실패 · 날짜를 못 읽음 → (−1, 사유).
3. 보정값 = (상세의 마감일 − 기준일) − N. if 0 · −1이 아님 → (−1, 사유) · else (보정값, 설명).

**테스트 관점** 저녁처럼 맞으면 0 · 아침처럼 목록이 하루 많으면 −1 · 상세 404면 −1 · 2026-09-28 09:02에 −1(실측)

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

#### aifactory.group_tasks 같은 대회의 과제 합치기

**시그니처** `group_tasks(tasks) -> list[list[Task]]`

**처리** 페이지 이름과 접수시작일이 같은 과제끼리 모은다. id 차례.

**테스트 관점** 112건 → 88개

#### aifactory.competition_name 대회명 정하기

**시그니처** `competition_name(page, tasks, start) -> str`

**근거** [[CCR-API-001#GET/aifactory.space/ko/competition]] 대회명

**처리** 앞에서 정해지면 뒤는 보지 않는다.
1. if 페이지 이름에 연도(20으로 시작하는 네 자리)가 있고 그 연도가 접수시작일의 해나 다음 해 → 페이지 이름.
2. if 과제가 하나 → 그 과제명.
3. 과제명들의 공통 앞부분을 정리한다(앞뒤 공백 · 끝의 `_ - : ·` · 짝이 맞지 않는 여는 괄호부터 끝까지를 뗀다). if 10자 이상 → 그것.
4. 머리 꼬리표(`[…]` · `(…)`) 하나를 뗀 과제명으로 3을 다시. if 10자 이상 → 그것.
5. 가장 작은 id의 과제명. 다만 그것이 주제 번호(`주제 1` · `문제1` · `[분야1]` · `track` 등)로 시작하고 페이지 이름이 있으면 페이지 이름.

**테스트 관점** 9304 · 9235 · 9159 · 6684 · 2367의 이름 · 기관명 페이지는 이름이 되지 않음 · 공통 앞부분의 끝 구분 기호 떼기 · 꼬리표를 떼고 다시 보기 · 주제 번호면 페이지 이름

#### aifactory.to_competition 과제 묶음을 대회로

**시그니처** `to_competition(group) -> Competition | None`

**처리** 이름 있는 과제만 쓴다. if 없음 → `None`. 원천 ID는 가장 작은 id, 링크 `https://aifactory.space/competitions/{id}`, 접수시작일은 가장 이른 값, 마감일은 가장 늦은 값. if 시작일 > 마감일 → 시작일을 비운다. 부가 정보는 페이지 이름과 과제명들.

**테스트 관점** 다섯 대회의 날짜와 링크

#### contestkorea.parse_list 콘테스트코리아 목록 한 쪽

**시그니처** `parse_list(response) -> list[CkItem]`

**처리** `div.list_style_2`가 없으면 `FormatError`. `div.list_style_2 > ul > li`마다 `div.title > a`의 `str_no`, 대회명(`span.txt` · `html_text`), 분야(`span.category`), 주최 · 대상(`ul.host`), 접수 기간(`span.step-1`의 `MM.DD~MM.DD`), 날수(`span.day`의 `D-N`).

**테스트 관점** 저장한 쪽 12건 · 첫 공고의 접수 기간 8/18 ~ 9/27 · D-0

#### contestkorea.resolve_dates 접수 날짜의 연도 정하기

**시그니처** `resolve_dates(base_date, period, days) -> tuple[date | None, date | None]`

**근거** [[CCR-API-001#GET/www.contestkorea.com/sub/list.php]]

**처리**
1. if 날수가 없음 → (None, None). 연도를 정할 수 없다.
2. 어림 = 기준일 + N. if 접수 기간이 없음 → (None, 어림).
3. 마감일 = 찍힌 `MM.DD`를 어림의 전 · 같은 · 다음 해로 놓아 어림에 가장 가까운 날. 날수가 하루 어긋나도 찍힌 날짜를 쓴다.
4. 시작일 = 마감일의 해에 찍힌 시작 `MM.DD`. if 그것이 마감일보다 뒤 → 한 해 앞.

**테스트 관점** 오늘 마감 · 날수가 하루 어긋남 · 해를 넘기는 접수 기간 · 날수 없음

#### ContestKoreaSource.collect 콘테스트코리아 수집

**시그니처** `collect(http, base_date, page_cap) -> Collected`

**처리** 분야 둘(`030310001` · `031410001`)을 차례로, 접수 마감이 이른 차례의 쪽(12건)을 읽는다. 쪽 상한은 합산이다. `str_no`로 합치고 분야를 더한다. if 12건보다 적은 쪽 → 그 분야를 멈춤. 링크 `/sub/view.php?int_gbn=1&str_no={str_no}`, 날짜는 `resolve_dates`, 부가 정보는 분야 · 주최 · 대상.

**테스트 관점** 두 분야의 쪽 요청 차례 · 합쳐서 12건 · 링크와 마감일

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
2. if 한쪽이 노션 행이고 두 링크(정규화)가 같음 → 둘 다 연도가 있는데 겹치지 않거나 둘 다 회차가 있는데 겹치지 않으면 다름(2단계) · else 같음(1단계, 확실). 이 경우 3단계는 보지 않는다.
3. 2단계: if 둘 다 연도가 있음 → 맞대 봄 표시, 겹치지 않으면 다름. 회차도 같다.
4. 3단계: if `a.start`와 `b.deadline`이 있음 → 맞대 봄, `a.start > b.deadline`이면 다름. 반대 방향도 같다. if 두 마감일이 있음 → 맞대 봄, 180일 넘게 떨어지면 다름.
5. if 한쪽 정규화 대회명이 비었음 → 판단하지 않음.
6. 4단계: if 정규화 대회명이 같음 → 같음(4단계, 확실 = 맞대 봤는가).
7. 5단계: 유사도 ≥ 0.90 → 같음(5단계, 유사도, 확실 = 맞대 봤는가) · else 판단하지 않음(유사도).

연도 · 회차가 "다르다"는 두 집합이 겹치지 않는 것이다. `2025-2026`과 `2026`은 다르지 않다.

**출력** `PairResult`

**테스트 관점** 2단계로 가르는 PRD 예 · 작년 공고를 3단계로 가름 · 마감 180일 · 마감 연장은 같음(4단계 · 확실) · 1단계는 날짜가 바뀌어도 같음 · 노션 링크가 같아도 연도가 다르면 다름 · 이름만으로 같으면 확실하지 않음 · 문턱 미만은 판단하지 않음 · PRD의 0.82 짝은 판단하지 않음 · 0.90 경계

#### matching.group 후보끼리 묶기

**시그니처** `group(competitions, keys) -> list[list[int]]`

**근거** [[CCR-UC-001#UC-S4]] 4 · 4b

**처리**
1. 모든 짝에 `judge_pair`. 같음은 (단계, −유사도, 앞선 쪽의 (우선순위 · 원천 ID · 대회명), 뒤쪽의 같은 것)로 차례를 매기고, 같음인 짝의 집합을 따로 둔다.
2. 같음을 그 차례로 보며 두 묶음을 합친다. if 두 묶음을 가로지르는 짝 가운데 같음이 아닌 것(다름 · 판단하지 않음)이 하나라도 있음 → 합치지 않는다(먼저 본 짝 쪽 묶음에 남는다). 같다는 짝을 사슬로만 잇지 않는다([[CCR-DOM-002]] 5장 결정 7).
3. 묶음마다 구성원 번호 목록.

**테스트 관점** 연도 없는 공고가 두 해의 공고를 잇지 못함 · A~B · B~C가 같아도 A–C가 판단하지 않음이면 C는 따로 · 이름 틀이 비슷한 공모전 셋은 묶이지 않음 · 소스가 다른 같은 공고는 묶임

#### matching.representative_order 대표를 고르는 차례

**시그니처** `representative_order(c) -> tuple[int, int, str]`

**처리** (−채워진 접수 날짜 수, 소스 우선순위, 원천 ID). 가장 작은 것이 대표다([[CCR-UC-001#UC-S4]] 4a).

**테스트 관점** 날짜가 더 채워진 event-us가 DACON보다 먼저

#### ScreenService.drop_expired 마감 지난 대회 버리기

**시그니처** `drop_expired(competitions) -> tuple[list[Competition], int]`

**근거** [[CCR-UC-001#UC-S3]]

**처리** if 상시 연습용 → 버림 · else if 접수마감일 < 기준일 → 버림 · else 남김(오늘 마감 · 마감일 없음 포함). 버린 수를 함께 돌려준다.

**테스트 관점** 어제 마감 · 오늘 마감 · 마감 모름 · 연습용

#### ScreenService.bundle 묶음 만들기

**시그니처** `bundle(competitions) -> list[Bundle]`

**처리** 대회마다 `key_of_competition`, `group`으로 묶고, 묶음마다 `representative_order`가 가장 작은 구성원을 대표로, 구성원의 판정 값(`keys`)을 함께 싣는다. 묶음 수와 여럿인 묶음 수를 로그에.

**테스트 관점** 대표 고르기

#### ScreenService.build_known 아는 대회 모으기

**시그니처** `build_known(rows: list[NotionRow], history: list[HistoryRecord]) -> KnownSet`

**근거** [[CCR-UC-001#UC-S4]] 3 · [[CCR-UC-001#UC-A1]] 1b6

**처리**
1. 노션 행마다 `Known(notion, key_of_notion, keep)`.
2. 처리 이력 기록마다 `(출처, 원천 ID)`를 `history_ids`에 넣는다. if 버림을 없는 것으로 봄 이고 버림 → 넣지 않음 · else `Known(history, key_of_history, 그 결과)`.
3. 넣을 때 색인 셋(`by_id` · `by_link`(노션 행만) · `by_title`)을 채운다.

**테스트 관점** 버림 무시면 버림 기록과 같은 공고가 아는 대회가 아님

#### ScreenService.split_known 아는 대회로 빠진 묶음 빼기

**시그니처** `split_known(bundles, known: KnownSet) -> tuple[list[Bundle], int]`

**근거** [[CCR-UC-001#UC-S4]] 5 · 6 · 7

**처리** 묶음마다 `_matches`. if 짝이 없음 → 모르는 묶음 · else 처리 결과 `known`, 짝을 싣고 `_record_known`.

**출력** (모르는 묶음, 아는 대회로 빠진 묶음의 수)

**테스트 관점** 원천 ID가 같은 기록 · 노션 행이 버림 기록을 이겨 남김으로 적힘 · 이름만 같으면 빼되 적지 않음 · 작년 기록은 올해 공고를 막지 않음

#### ScreenService._matches 묶음과 같은 아는 대회 찾기

**시그니처** `_matches(bundle, known) -> list[tuple[Known, PairResult]]`

**처리**
1. 후보 좁히기. 구성원마다 `by_id`(같은 출처 · 원천 ID) · `by_link`(같은 링크) · `by_title`(같은 정규화 대회명)과, 모든 아는 대회 가운데 유사도 0.90에 닿을 수 있는 것(`similarity`의 1 · 2와 같은 거르기).
2. 후보마다 모든 구성원과 `judge_pair`.
3. if 1단계로 같은 구성원이 있음 → 짝(그 결과). 다른 구성원의 2 · 3단계는 보지 않는다.
4. else if 다름인 구성원이 있음 → 건너뜀.
5. else if 같음인 구성원이 있음 → 짝(확실한 것 · 앞선 단계 · 높은 유사도 차례로 가장 좋은 결과).

**테스트 관점** `split_known`의 테스트가 함께 본다. 기록 5,000줄 · 후보 600건에 2초 안팎(실측)

#### ScreenService._record_known 아는 대회로 빠진 묶음 적기

**시그니처** `_record_known(bundle, matches, known) -> None`

**근거** [[CCR-UC-001#UC-S4]] 6 · [[CCR-DOM-002]] 5장 결정 2

**처리**
1. 1단계가 아닌 짝이면 무엇과 같았는지(단계 · 유사도)를 로그에.
2. 확실한 짝만 모은다. if 없음 → 적지 않음(이름만으로 같음).
3. 결과 = 남김 if 확실한 짝 가운데 남김(노션 행 · 남김 기록)이 있음 · else 버림.
4. `history_ids`에 없는 구성원만 `entries_for(묶음, 결과, 그 구성원)`으로 `RecordService.append`.

**테스트 관점** 자기 기록이 없는 구성원만 적고 날짜는 대표의 것으로 채움 · 노션 행과 버림 기록이 함께면 남김

#### screen.entries_for 처리 이력에 적을 값

**시그니처** `entries_for(bundle, result, members=None) -> list[HistoryEntry]`

**처리** 구성원(또는 주어진 구성원)마다 한 줄. 같은 (출처, 원천 ID)는 한 번만. 접수시작일 · 마감일이 없으면 대표의 값으로 채운다([[CCR-UC-001]] 0.1).

**테스트 관점** 대표의 날짜로 채우기

#### ScreenService.judge 관심 분야 판별

**시그니처** `judge(bundles) -> JudgeOutcome`

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

**시그니처** `_ask_all(bundles, outcome) -> list[Bundle]`

**처리**
1. 스레드 넷(설정값)에 묶음마다 `ask`를 맡긴다. `ask`: if 멈춤 표시 → `Stopped` · if 치명 오류 표시 → 묻지 않고 실패 · else `judge.judge(대표)`. `JudgeError(fatal)`이면 치명 오류 표시를 켠다. 그 밖의 예외도 그 묶음의 실패다.
2. 끝나는 차례대로 받는다. if 실패 → 실패 목록 · else if 남김 → 근거를 싣고 넣을 묶음에 · else(버림) → 처리 결과 `discarded`, 버림 수 +1, `append(entries_for(묶음, 버림))`. 결과와 근거를 로그에.
3. 예외(신호 등)가 나면 기다리지 않고 풀을 닫는다(`cancel_futures`).

**출력** 판별 실패 묶음

**테스트 관점** `judge`의 테스트가 함께 본다

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

**시그니처** `build_input(competition) -> str`

**처리** `대회명: …` · `출처: …` · (있으면) `부가 정보: …`를 줄로. 부가 정보는 쉼표로 잇고 800자에서 자른다.

**테스트 관점** 긴 부가 정보가 잘림

### 2.5 노션

#### NotionService.read_rows 노션 행 읽기

**시그니처** `read_rows() -> list[NotionRow]`

**근거** [[CCR-UC-001#UC-S4]] 1 · 1a · [[CCR-API-001#POST/api.notion.com/v1/data_sources/{id}/query]]

**처리** `NotionCrud.query_pages`로 모든 행을 받아 `row_of`. if `NotionFailure` → `NotionReadFailed`.

**예외** 끝내 실패 · incomplete → `NotionReadFailed`

**테스트 관점** 커서를 따라 두 쪽 · incomplete는 읽기 실패

#### notion.row_of 행 하나 읽기

**시그니처** `row_of(page: dict) -> NotionRow`

**처리** `기타`의 `title` 조각들의 `plain_text`를 잇는다. `링크`는 `url`. `시작일` · `마감일`은 `date.start`를 KST 날짜로. 컬럼이 없으면 빈 값.

**테스트 관점** 조각 잇기 · UTC 시각이 붙은 날짜 · 빈 속성

#### NotionService.check_columns 컬럼 확인

**시그니처** `check_columns() -> SchemaCheck`

**근거** [[CCR-UC-001#UC-S6]] 1 · 1a · 1b · [[CCR-API-001]] 1.4

**처리**
1. `get_data_source`. if 실패 → `ok=False`(스키마를 읽지 못함).
2. `check_schema(properties)`. if 문제 → `ok=False`.
3. if 만들 컬럼이 없음 → `ok=True`.
4. if 쓰지 않는 실행 → 만들지 않고 `ok=True`(로그).
5. `add_properties`(없는 것만: `출처` select · `수집일` date). if 실패 → `ok=False` · else `ok=True`, 만든 것.

**테스트 관점** 없는 컬럼만 보냄 · 미리보기는 보내지 않음 · 스키마를 읽지 못하면 막되 예외를 내지 않음

#### notion.check_schema 스키마 맞춰 보기

**시그니처** `check_schema(properties: dict) -> tuple[list[str], str | None]`

**처리** 일곱 컬럼마다: if 없음 → `출처` · `수집일`이면 만들 목록에 · 아니면 문제 · if 종류가 다름 → 문제. 그다음 `상태`의 선택지에 `시작 전`이 없으면 문제.

**테스트 관점** 문제 없음 · 둘만 없음 · 링크 없음 · 종류 다름 · 선택지 없음

#### NotionService.create_row 행 만들기

**시그니처** `create_row(competition, base_date) -> CreateOutcome`

**근거** [[CCR-UC-001#UC-S6]] 2 · 3 · 2a · 2c · 2d · [[CCR-API-001#POST/api.notion.com/v1/pages]]

**처리** `create_page(properties_of(대회, 기준일))`. if `NotionFailure` → `created=False`(사유) · if 503이 새 행 id를 줌 → `created=True`, `via_committed` · else `created=True`, 행 id.

**테스트 관점** 성공 · 503과 새 행 id · 400

#### notion.properties_of 행 값

**시그니처** `properties_of(competition, base_date) -> dict`

**처리** [[CCR-API-001]] 4.2 그대로. `기타` 대회명(2,000자에서 자름) · `링크` · `시작일` · `마감일`(모르면 `{"date": null}`) · `상태` `시작 전` · `출처` 소스 이름 · `수집일` 기준일. `결과날`은 보내지 않는다.

**테스트 관점** 일곱 컬럼의 모양 · 2,000자 자르기

#### NotionCrud.query_pages 모든 행 받기

**시그니처** `query_pages() -> list[dict]`

**처리** `page_size` 100으로 `POST query`. if `request_status.type == incomplete` → `NotionFailure` · if `results`가 배열이 아님 → `NotionFailure`. `has_more`이고 `next_cursor`가 있는 동안 `start_cursor`로 넘긴다. 거르거나 정렬하지 않는다.

**테스트 관점** 첫 요청에 커서 없음 · 둘째에 커서

### 2.6 기록

#### RecordService.start 추가분 비우기

**시그니처** `start() -> None`

**처리** if 노션에 쓰는 실행 → 추가분 두 파일을 빈 파일로 바꿔 쓴다 · else 아무것도 하지 않는다.

**테스트 관점** 미리보기는 추가분 폴더를 만들지 않음

#### RecordService.load 상태 파일 읽기

**시그니처** `load() -> State`

**근거** [[CCR-UC-001#UC-S4]] 2 · 2a · 2b · [[CCR-SEQ-001#SEQ-3]]

**처리**
1. `RecordCrud.prepare`(기본 브랜치 밖이면 origin/main의 두 파일을 꺼냄) → `read_history` → `read_runs`.
2. if `HistoryReadFailed` → `history_error`에 사유를 담고 돌려준다(로그).
3. 처리 이력(없으면 빈 것과 `history_exists=False`) · 실행 요약. 읽히지 않는 줄이 있으면 로그.

**출력** `State`

**테스트 관점** 첫 실행 · 깨진 줄 · 필수 필드 없음 · 읽히지 않는 실행 요약 줄 세기

#### RecordService.history_shrank 남김 기록이 줄었나

**시그니처** `history_shrank(state) -> bool`

**근거** [[CCR-UC-001#UC-S4]] 2c · 2a2

**처리** 마지막으로 적힌 `keep_count`(뒤에서부터 첫 정수)를 찾는다. if 없음 → 거짓 · else 지금 남김 수(처리 이력 파일이 없으면 0) < 그 값 → 참(로그).

**테스트 관점** 줄어듦 · 파일이 없는데 적힌 수가 있음 · 첫 실행

#### RecordService.append 처리 이력 적기

**시그니처** `append(entries: list[HistoryEntry]) -> None`

**근거** [[CCR-UC-001#UC-S4]] 6 · [[CCR-UC-001#UC-S5]] 5 · [[CCR-UC-001#UC-S6]] 4

**처리** if 쓰지 않는 실행 · 빈 목록 → 아무것도 하지 않음. 값마다 `HistoryRecord.of(값, 기준일, 실행 식별자)`를 쌓고, 쌓인 전부를 `write_history_appends`로 통째로 바꿔 쓴다.

**테스트 관점** 두 번 적으면 두 줄 · 날짜와 실행 식별자 · 임시 파일이 남지 않음 · 미리보기는 쓰지 않음

#### RecordService.zero_count_warnings 소스 0건 경고

**시그니처** `zero_count_warnings(results, state, days) -> list[RunWarning]`

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

**테스트 관점** 줄의 필드 열넷 · `keep_count`가 비어 있음 · 경고의 빈 속성은 없음

#### RecordCrud.read_history 처리 이력 읽기

**시그니처** `read_history() -> list[HistoryRecord] | None`

**처리** if 파일이 없음 → `None`. 바이트로 읽고 줄마다(빈 줄은 건너뜀) UTF-8 · JSON 객체 · `HistoryRecord.from_dict`. 하나라도 실패하면 `HistoryReadFailed(몇 번째 줄)`. 열지 못해도 같다.

**테스트 관점** `load`의 테스트가 함께 본다

#### RecordCrud.read_runs 실행 요약 읽기

**시그니처** `read_runs() -> RunsFile`

**처리** if 파일이 없음 → 빈 것. 줄마다 UTF-8 · JSON을 읽고, 객체이며 `run_id` · `base_date`가 있으면 줄로, 아니면 `corrupt` +1. 파일을 열지 못하면 `HistoryReadFailed`.

**테스트 관점** 깨진 줄 둘을 세고 하나를 읽음

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
3. 두 파일마다: 대상 파일을 지우고, if `origin/main:data/{파일}`이 있음 → `git show`로 꺼내 쓴다 · else 없는 채로 둔다.

**테스트 관점** 작업 트리에 다른 사본이 있어도 main 판을 읽음 · 원격이 없으면 읽기 실패 · git이 없으면 읽기 실패

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

**테스트 관점** 로컬에서 노션 설정 없이 돌리면 설정 누락으로 1(실측) · Actions에서 `DRY_RUN`이 비면 2(실측)

#### __main__.run_batch 하루치

**시그니처** `run_batch(env, stop) -> int`

**처리** `RunContext` · `Settings` · `Secrets`를 만들고 서비스를 조립한다. 소스 여섯(Kaggle에 토큰), `NotionService`(토큰과 대상 DB 식별자가 모두 있을 때만, 아니면 없음), `RecordCrud`(main 판을 꺼내야 하면 저장소 루트), `OpenAiJudge`(키가 있을 때만). `Pipeline.run`의 결과가 성공이면 0 · else 1.

**테스트 관점** `Pipeline`의 테스트가 조립된 흐름을 본다

#### __main__.run_collect 수집만

**시그니처** `run_collect(env, stop, only, show) -> int`

**처리** 소스를 (이름이 주어지면 그 하나만) `CollectService`로 돌리고 소스마다 결과 한 줄, `--show`면 대회마다 한 줄(원천 ID · 접수 기간 · 대회명 · 링크)을 찍는다. 노션 · OpenAI를 부르지 않고 아무것도 쓰지 않는다. 하나라도 성공하면 0. 사이트 개편을 가를 때 쓴다([[CCR-UC-001#UC-A3]]).

**테스트 관점** 실측으로 다섯 소스 성공 · Kaggle 설정 누락(2026-09-27)

#### Pipeline.run 한 실행

**시그니처** `run() -> RunLine`

**근거** [[CCR-UC-001#UC-A1]] · [[CCR-SEQ-001#SEQ-1]]

**처리** 시작 시각을 재고, 줄(실행 식별자 · 기준일 · 종류)을 만들고, 실행 정보를 로그에. if 버림 무시를 청했는데 쓰는 실행 → 무시한다고 로그. `RecordService.start` → `_run` → `_finish`.

**출력** `RunLine`

**예외** 신호 → `Stopped`(줄을 쓰지 않음)

**테스트 관점** 아래 `_run` · `_load` · `_finish`의 테스트 · 신호면 줄이 비어 있음

#### Pipeline._run 기본 흐름과 실패 건너뛰기

**시그니처** `_run(line) -> tuple[State, list[SourceResult]]`

**근거** [[CCR-UC-001#UC-A1]] 1d1 · 2 ~ 7 · 2b · 5a · [[CCR-SEQ-001#SEQ-9]]

**처리** 단계 사이마다 멈춤 표시를 본다.
1. if 노션 서비스가 없음 → `fail(missing_config)`, 끝.
2. `collect_all` → 줄의 `sources`, `dropped.normalize`(소스 탈락의 합).
3. `RecordService.load`.
4. if 모든 소스가 실패 → `fail(all_sources_failed)`, 끝.
5. `drop_expired` → `dropped.expired`.
6. `read_rows`. if `NotionReadFailed` → `fail(notion_read_failed)`, 끝.
7. if 처리 이력 읽기 오류 → `fail(history_read_failed)`, 끝 · if `history_shrank` → `fail(history_shrank)`, 끝.
8. `build_known` → `bundle` → `split_known` → `dropped.known`.
9. `judge` → `dropped.discarded` · `judge_failed` · `deferred`. if 미룸 → 경고 `judge_deferred`(원인).
10. `_load(넣을 묶음)`.

**테스트 관점** 정상 흐름의 건수 · 설정 누락은 수집하지 않음 · 전 소스 실패 · 노션 읽기 실패와 처리 이력 읽기 실패는 판별하지 않음 · 처리 이력 감소 · 실패한 소스가 있어도 성공

#### Pipeline._load 노션에 넣기

**시그니처** `_load(line, bundles) -> None`

**근거** [[CCR-UC-001#UC-S6]] · [[CCR-UC-001#UC-A1]] 7a · [[CCR-SEQ-001#SEQ-5]]

**처리**
1. if 넣을 묶음이 없음 → 끝.
2. `check_columns`.
3. if 쓰지 않는 실행 → 컬럼 문제가 있으면 로그, 넣었을 대회를 한 줄씩 로그, 끝.
4. if 컬럼 문제 → 묶음 모두 `create_failed`, 오늘 마감 묶음이 있으면 표시 · else 묶음마다(멈춤 표시 확인) `create_row(대표)`: if 만듦 → 처리 결과 `loaded`, `append(entries_for(묶음, 남김))`, `loaded` +1, 로그(503이 알려 준 것인지) · else `create_failed` +1, 로그, if 묶음의 접수마감일 = 기준일 → 표시.
5. if `loaded` = 0 이고 `create_failed` > 0 → 경고 `create_all_failed`.
6. if 표시 → 경고 `due_today_not_loaded`, `fail(due_today_not_loaded)`.

**테스트 관점** 오늘 마감 행 실패는 실패 · 컬럼 문제는 모두 실패와 전면 실패 경고 · OpenAI 키가 없으면 오늘 마감만 넣음 · 미리보기는 행을 만들지 않음

#### Pipeline._finish 실행 기록

**시그니처** `_finish(line, state, results, started) -> None`

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
   3. 처리 이력 추가분을 붙인다. 남김 줄을 센다.
   4. 붙일 줄 = 배치의 줄에 `keep_count`를 채운 것 · 없으면 `{run_id, base_date, kind, result: aborted, keep_count}`.
   5. 올리는 추가분을 로그에 찍고 `commit_and_push(실행 기록 {기준일} · {실행 식별자} · {결과})`.
   6. if 성공 → 끝(표시에 따라 0 · 1) · if `GitError` → 로그, 처음부터.
3. 다섯 번 모두 실패 → 1.

**출력** `Outcome(종료 코드, 설명)`

**테스트 관점** 처리 이력과 줄을 붙이고 남김 수를 채움 · 작성자 봇 · 메시지 · 줄이 없으면 중단 줄과 1 · 형식이 틀린 줄은 빼고 1 · 이미 올린 실행은 다시 붙이지 않음 · 그사이 올라온 관리자 커밋 위에 다시 얹고 그 수정이 남음 · 빈 저장소의 첫 실행

#### finish.read_additions 추가분 읽기

**시그니처** `read_additions(append_dir: Path, run_id: str) -> Additions`

**처리** 처리 이력 추가분의 줄마다: if JSON 객체이고 필수 넷(`source` · `source_id` · `result` · `run_id`)이 비어 있지 않음 → 붙일 줄 · else 로그와 거절 +1. 실행 요약 추가분의 줄마다: if JSON 객체이고 `run_id` · `base_date` · `kind` · `result`가 있고 `run_id`가 이 실행 → 배치의 줄 · else 거절 +1.

**테스트 관점** `finish`의 테스트가 함께 본다

#### Git.fresh_main main 최신 판 받기

**시그니처** `fresh_main() -> None`

**처리** if 작업 폴더에 저장소가 있음 → `fetch --depth=1 origin main` · `reset --hard FETCH_HEAD` · `clean -fdx` · else 폴더를 지우고 `clone --depth=1 --branch main`. 받는 명령에만 `http.extraheader`로 토큰을, 모든 명령에 느린 연결 끊기(`lowSpeedLimit` 1000 · `lowSpeedTime` 20)를 준다. 명령마다 60초 제한. 실패하면 `GitError`(git의 오류 문구만. 명령은 찍지 않는다).

**테스트 관점** 되풀이 때 최신 판으로 맞춰짐(`finish`의 경합 테스트)

#### Git.commit_and_push 커밋하고 올리기

**시그니처** `commit_and_push(message: str) -> None`

**처리** 두 경로 가운데 있는 것만 `add`한다(첫 실행에는 처리 이력 파일이 없을 수 있다). 작성자 `github-actions[bot]`으로 커밋하고 `push origin HEAD:refs/heads/main`(토큰은 이 명령에만).

**테스트 관점** 빈 저장소의 첫 실행

#### finish.append_lines 파일 끝에 줄 붙이기

**시그니처** `append_lines(path: Path, lines: list[str]) -> None`

**처리** if 줄이 없음 → 아무것도 하지 않음. 폴더를 만들고, if 파일이 줄바꿈으로 끝나지 않음 → 줄바꿈을 먼저 붙인 뒤 줄마다 줄바꿈과 함께 붙인다.

**테스트 관점** 줄바꿈으로 끝나지 않는 파일

## 3. 미결사항

- [ ] Kaggle의 필드 이름 · 연습용 표기 · 쪽 크기는 실측 전이다([[#kaggle.normalize]] · [[#KaggleSource.collect]])
