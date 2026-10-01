---
doc_id: CCR-SEQ-001
type: SEQ
title: 시퀀스 — 대회 수집 배치
status: approved
upstream: [CCR-UC-001, CCR-DOM-002, CCR-DOM-003, CCR-API-001, CCR-INFRA-001, CCR-UI-001]
---

# SEQUENCE — 대회 수집 배치

## 0. 이 문서가 다루는 것

유스케이스([[CCR-UC-001]])의 흐름을 클래스 명세([[CCR-DOM-002]])의 객체 사이 메시지로 옮긴다. 한 실행이 시간순으로 무엇을 부르는지, 실패하면 어디서 갈라지는지를 본다. 함수 안의 처리는 [[CCR-MS-001]]이 맡는다.

배치의 시퀀스(SEQ-1 ~ SEQ-10)는 스케줄러(GitHub Actions)나 관리자의 수동 실행에서 시작한다. 대회 목록 페이지의 시퀀스(SEQ-11 · SEQ-12)는 참가자가 브라우저에서 시작한다. 2026-09-29에 노션을 페이지로 바꾸면서 노션 생명선을 지우고 목록 서비스와 페이지의 생명선을 더했다.

### 0.1 생명선

| 생명선 | 약어 | 실체 | 종류 | 정의한 곳 |
|---|---|---|---|---|
| 스케줄러 | GH | GitHub Actions. 예약 · 수동 실행과 신호 | 외부 | [[CCR-INFRA-001]] 8.1 |
| 워크플로 | WF | `.github/workflows/daily.yml`의 스텝 | 실행 환경 | [[CCR-INFRA-001]] 8.1 |
| 입구 | M | `collector/__main__.py` | Boundary | [[CCR-DOM-002]] 4.7 |
| 실행의 흐름 | P | `Pipeline` | Control | [[CCR-DOM-002#Pipeline]] |
| 수집 | CS | `CollectService` | Control | [[CCR-DOM-002#CollectService]] |
| 소스 어댑터 | SA | `Source` 구현 여섯 | Boundary | [[CCR-DOM-002#Source]] |
| 소스 요청 | H | `SourceHttp` · `ensure_allowed` | infra | [[CCR-DOM-002]] 4.8 |
| 대회 소스 | SRC | event-us · DACON · Kaggle · wevity · AI팩토리 · 콘테스트코리아 | 외부 | [[CCR-API-001]] 3.1 |
| 선별 | SS | `ScreenService`와 `matching` | Control | [[CCR-DOM-002#ScreenService]] |
| 판별 | J | `OpenAiJudge` | Boundary | [[CCR-DOM-002#OpenAiJudge]] |
| OpenAI | AI | Responses API | 외부 | [[CCR-API-001#POST/api.openai.com/v1/responses]] |
| 목록 | LS | `ListService` → `ListCrud` | Control | [[CCR-DOM-002#ListService]] |
| 기록 | RS | `RecordService` → `RecordCrud` | Control | [[CCR-DOM-002#RecordService]] |
| 데이터 파일 | FS | `data/competitions.jsonl` · `data/processed.jsonl` · `data/runs.jsonl`과 추가분 `$RUNNER_TEMP/append/` | 파일 | [[CCR-DOM-003]] |
| 마무리 단계 | F | `batch/finish.py` | Control | [[CCR-DOM-002]] 4.10 |
| 기본 브랜치 | G | 원격 저장소의 `main` | 외부 | [[CCR-INFRA-001]] 8.2 |
| 참가자 | U | 브라우저 앞의 사람 | 액터 | [[CCR-UC-001]] 1장 |
| 화면 | UI | `CompetitionList` · `SettingsDialog` | Boundary | [[CCR-DOM-002#CompetitionList]] · [[CCR-DOM-002#SettingsDialog]] |
| 상태 저장 | ST | `StatusStore` | Control | [[CCR-DOM-002#StatusStore]] |
| 저장소 파일 | RF | `api/data.ts` · `api/github.ts` | Boundary | [[CCR-DOM-002#RepoFiles]] |
| 토큰 보관 | TK | `TokenStore`(localStorage) | store | [[CCR-DOM-002#TokenStore]] |
| GitHub | GHB | `raw.githubusercontent.com` · Contents API | 외부 | [[CCR-API-001]] 3.3 |

## SEQ-1 하루치를 돌린다

[[CCR-UC-001#UC-A1]] 기본 흐름 1 ~ 10. 워크플로의 일곱 스텝([[CCR-INFRA-001]] 8.1의 다섯 차례. 코드 받기에 정의 확인이, 환경에 의존성 설치가 붙는다)과 배치 안의 흐름을 한 그림에 둔다. 각 단계의 안은 SEQ-2 ~ SEQ-7이다.

```mermaid
sequenceDiagram
    autonumber
    participant GH as 스케줄러
    participant WF as 워크플로
    participant M as 입구
    participant P as Pipeline
    participant CS as CollectService
    participant SS as ScreenService
    participant LS as ListService
    participant RS as RecordService
    participant F as finish.py
    GH->>WF: 08:50 KST 예약(또는 수동)
    WF->>WF: 시작 시각 · 실행 식별자 · 추가분 폴더를 잡 환경에
    WF->>WF: main 최신 커밋 받기 · .github/ 바뀜 확인 · uv sync
    WF->>M: exec python -m collector (시크릿은 이 스텝에만)
    M->>M: 가릴 값 알리기 · 로그 · 신호 처리기
    M->>P: run()
    P->>RS: start() — 데이터 폴더 꺼내기 · 추가분 비우기
    P->>CS: collect_all(기준일)
    CS-->>P: 소스별 결과 여섯
    P->>LS: load() — 목록 파일
    P->>RS: load() — 처리 이력 · 실행 요약
    P->>SS: drop_expired(대회)
    P->>SS: build_known · bundle · split_known
    P->>SS: judge(모르는 묶음)
    SS-->>P: 넣을 묶음 · 건수
    P->>LS: append(대표) × 묶음
    P->>RS: append(남김) × 묶음
    P->>RS: zero_count_warnings · write_run(줄)
    P-->>M: RunLine
    M-->>WF: 종료 코드(성공 0 · 실패 1)
    WF->>F: 마무리(always · main · 쓰는 실행)
    F-->>WF: 올렸으면 0
```

**읽을 때 볼 것**
- 기준일은 1단계가 잡 환경에 남긴 `RUN_STARTED_AT`에서 배치와 마무리 단계가 각자 구한다. 배치가 어디서 멈추든 같은 날짜다([[CCR-INFRA-001#C13]]).
- 파일 쓰기(두 `append` · `write_run`)는 추가분 폴더에만 한다. 커밋은 마무리 단계가 세 파일을 한 번에 한다([[CCR-UC-001#UC-A1]] 9). 배치는 GitHub에 HTTP 요청을 보내지 않는다.
- 마무리 단계는 배치 스텝이 실패하거나 끊겨도 돈다(`if: always()`). 목록에 쓰지 않는 실행과 기본 브랜치가 아닌 실행에서는 돌지 않는다.
- 반드시 있어야 하는 시크릿은 없다. OpenAI 키와 Kaggle 토큰이 배치 스텝의 환경 변수로 들어갈 뿐이다([[CCR-UC-001#UC-A1]] 1d1).
- 배치가 스스로 실패로 판단해 끝나면(종료 코드 1) 줄이 남고 실패 사유가 줄에 있다. 예상하지 못한 오류로 멈춰도 종료 코드는 1이지만 줄이 없어, 마무리 단계가 중단 줄을 쓴다(SEQ-10).

## SEQ-2 소스 하나를 수집한다

[[CCR-UC-001#UC-S1]] · [[CCR-UC-001#UC-S2]]. `CollectService`가 소스마다 스레드 하나로 돌리는 것 가운데 하나다.

```mermaid
sequenceDiagram
    autonumber
    participant CS as CollectService
    participant SA as 소스 어댑터
    participant H as SourceHttp
    participant SRC as 대회 소스
    CS->>SA: missing_config()
    alt 자격증명 없음(Kaggle 토큰)
        CS-->>CS: SourceResult.failed(missing_config)
    else
        CS->>H: 새로 만든다(기한 = 지금 + 120초)
        CS->>H: ensure_allowed(origin, 경로)
        H->>SRC: GET /robots.txt
        SRC-->>H: 200 · 429를 뺀 4xx(제한 없음)
        CS->>SA: collect(http, 기준일, 쪽 상한 20)
        loop 쪽마다(상한 · 멈춤 조건까지)
            SA->>H: fetch(목록 요청, parse)
            H->>H: 요청 간격 1초 · 남은 예산 확인
            H->>SRC: 목록 요청
            SRC-->>H: 응답
            opt 연결 오류 · 429 · 5xx · 틀이 다름
                H->>H: 2초 · 4초 뒤 다시(Retry-After ≤ 30초)
            end
            H-->>SA: 읽은 레코드
            SA->>SA: 공통 형식으로 맞춤(대회명 · 원천 ID · 링크 · 날짜 · 부가 정보)
        end
        SA-->>CS: Collected(대회 · 수집 · 탈락)
        CS-->>CS: SourceResult
    end
```

**읽을 때 볼 것**
- 소스의 실패는 밖으로 새지 않는다. robots 금지 → `robots`, 예산 초과 · 연결 → `connection`, 3xx · 4xx · 끝내 5xx → `http_status`, 틀이 다르거나 파서의 예외 → `format`([[CCR-API-001]] 2.1).
- 어느 소스도 쪽마다 1초를 쉬고, 여섯 소스는 동시에 돈다. 본문을 받는 동안에도 기한을 보므로, 가장 느린 소스도 예산 120초에 요청 한 단계의 타임아웃(최대 20초)을 더한 것보다 오래 돌지 않는다([[CCR-INFRA-001]] 8.5).
- wevity는 분야마다 쪽의 마지막 공고가 `마감`이면 그 분야를 멈춘다. 첫 쪽 위쪽 홍보 칸에 남은 마감 공고로는 멈추지 않는다([[CCR-DOM-002]] 5장 결정 8).
- wevity는 다섯 분야를 다 읽은 뒤 접수 중인 첫 공고의 상세 한 쪽을 더 받아 날수 보정값(0 · −1)을 잰다. 상세는 같은 사이트의 `gbn=viewok`로 302를 보내므로 이 요청은 리디렉션을 따라간다. 목록 요청은 따라가지 않는다(robots.txt는 따라간다). 재지 못하면 −1이다([[CCR-API-001#GET/www.wevity.com/?c=find&gbn=view]]).
- AI팩토리는 한 쪽을 받아 과제를 대회로 합친다. 수집 건수는 합치기 전 과제의 수다.
- Kaggle은 `page`를 1부터 올려 빈 쪽이 올 때까지 받는다. 한 쪽은 20건으로 정해져 있다. 응답이 심은 쿠키는 다음 요청에 싣지 않는다. 쿠키가 실리면 토큰이 있어도 401이다([[CCR-API-001]] 1.1 · 2026-10-01 실측).

## SEQ-3 이미 아는 대회를 가른다

[[CCR-UC-001#UC-S3]] · [[CCR-UC-001#UC-S4]] 1 ~ 7 · 1a · 1b · 2a · 2b · 2c.

```mermaid
sequenceDiagram
    autonumber
    participant P as Pipeline
    participant LS as ListService
    participant RS as RecordService
    participant FS as 데이터 파일
    participant SS as ScreenService
    P->>LS: load()
    LS->>FS: competitions.jsonl 읽기(없으면 빈 목록)
    LS-->>P: ListFile(항목 · 있었는지 · 읽기 오류)
    P->>RS: load()
    RS->>FS: processed.jsonl · runs.jsonl 읽기
    RS-->>P: State(이력 · 실행 요약 · 읽기 오류)
    P->>SS: drop_expired(대회) → 후보 · 마감 지남 수
    alt 목록 파일 읽기 오류
        P-->>P: 실패(목록 파일 읽기 실패)
    else 처리 이력 읽기 오류
        P-->>P: 실패(처리 이력 읽기 실패)
    else 남김 기록이 적힌 수보다 적다
        P->>RS: history_shrank(State)
        P-->>P: 실패(처리 이력 감소)
    end
    P->>SS: build_known(목록 항목, 처리 이력)
    P->>SS: bundle(후보)
    SS->>SS: 짝마다 judge_pair · 강한 짝부터 합치기(합친 묶음의 모든 짝이 같을 때만)
    P->>SS: split_known(묶음, 아는 대회)
    loop 묶음마다
        SS->>SS: 후보가 될 아는 대회만 골라 judge_pair
        opt 확실하게 같았다
            SS->>RS: append(자기 기록이 없는 구성원 · 견준 쪽의 결과)
            RS->>FS: 추가분 processed.jsonl 통째로 바꿔 쓰기
        end
    end
    SS-->>P: 모르는 묶음 · 아는 대회 수
```

**읽을 때 볼 것**
- 목록 파일을 먼저 읽고 처리 이력의 문제를 본다. 어느 쪽이든 실패면 판별도 적재도 하지 않고 SEQ-6으로 간다([[CCR-UC-001#UC-A1]] 5a). 데이터 폴더는 SEQ-1의 `start()`가 이미 꺼내 두었다(기본 브랜치 밖이면 origin/main의 세 파일).
- 목록 항목은 참가자가 페이지에서 지워도 남아 있어 지운 대회도 아는 대회다. 판정 1단계는 출처 · 원천 ID로 보고, 링크는 예비다([[CCR-DOM-001#ListEntry]]).
- 묶기는 합친 묶음 안의 모든 짝이 같다고 나올 때만 합친다. 다르다고 나온 짝은 물론, 판단하지 않은 짝(유사도 0.90 미만)이 하나라도 있으면 합치지 않는다([[CCR-DOM-002]] 5장 결정 7).
- 아는 대회는 1단계로 같은 구성원이 하나라도 있거나, 구성원 하나 이상과 같고 어느 구성원과도 다르지 않은 것이다. 묶을 때와 달리 모든 구성원과 같을 필요는 없다. 이름만으로 같았으면(연도 · 날짜를 맞대 보지 못함) 빼기만 하고 적지 않는다.
- 결과가 다른 둘과 함께 확실하게 같으면 남김으로 적는다([[CCR-DOM-002]] 5장 결정 2).
- 목록에 쓰지 않는 실행이면 `append`는 아무것도 하지 않는다.

## SEQ-4 관심 분야를 판별한다

[[CCR-UC-001#UC-S5]] 1 ~ 6 · 1a · 1b · 2a · 2b · 2c.

```mermaid
sequenceDiagram
    autonumber
    participant P as Pipeline
    participant SS as ScreenService
    participant J as OpenAiJudge
    participant AI as OpenAI
    participant RS as RecordService
    P->>SS: judge(모르는 묶음)
    alt OpenAI 키 없음
        SS-->>SS: 모든 묶음 판별 실패(원인 missing_key)
    else
        par 동시에 넷
            SS->>J: judge(대표)
            J->>AI: POST /v1/responses(기준 · 대회명 · 출처 · 부가 정보)
            alt 408 · 409 · 일반 429 · 5xx · 연결 오류
                J->>AI: 두 번까지 다시
            else 401 · 403 · 404 · 지출 한도 429
                J-->>SS: JudgeError(fatal) → 남은 묶음은 묻지 않음
            else 400 · incomplete · 거절 · 스키마 불일치
                J-->>SS: JudgeError → 이 묶음만 판별 실패
            end
            AI-->>J: decision · reason
            J-->>SS: Answer
        end
        loop 받는 차례대로(한 흐름)
            alt 버림
                SS->>RS: append(대표와 구성원, 버림)
            else 남김
                SS-->>SS: 넣을 묶음에 더함
            end
        end
    end
    alt 판별 실패 ≤ 절반
        SS-->>SS: 실패한 묶음을 남김으로
    else 판별 실패 > 절반
        SS-->>SS: 오늘 마감인 묶음만 남김, 나머지는 미룸(적지 않음)
    end
    SS-->>P: JudgeOutcome(넣을 묶음 · 버림 · 판별 실패 · 미룸 · 원인)
```

**읽을 때 볼 것**
- 판별 스레드는 답만 돌려주고, 처리 이력은 받는 쪽 한 흐름이 적는다([[CCR-INFRA-001]] 6.2).
- 오늘 마감인지는 묶음의 접수마감일(구성원 가운데 가장 늦은 값)로 가른다([[CCR-DOM-002]] 5장 결정 1).
- 미룬 묶음이 있으면 `Pipeline`이 판별 미룸 경고를 붙인다. 결과는 성공이다.
- 넣을 묶음은 접수마감일이 이른 차례로 돌려준다.

## SEQ-5 목록 파일에 더한다

[[CCR-UC-001#UC-S6]] 1 ~ 4 · 2a · 2b · 4a · [[CCR-UC-001#UC-A1]] 7.

```mermaid
sequenceDiagram
    autonumber
    participant P as Pipeline
    participant LS as ListService
    participant FS as 데이터 파일
    participant RS as RecordService
    loop 넣을 묶음마다(마감이 이른 차례)
        P->>LS: append(대표, 기준일, 판별 근거)
        LS->>LS: entry_of → 항목. 식별자가 이미 있나(읽은 목록 · 이번 추가분)
        alt 이미 있다
            LS-->>P: None(로그에 남김)
        else 목록에 쓰는 실행
            LS->>FS: 추가분 competitions.jsonl 통째로 바꿔 쓰기
            LS-->>P: 항목
        else 미리보기
            LS-->>P: 항목(쓰지 않음)
        end
        P->>RS: append(대표와 구성원, 남김)
        RS->>FS: 추가분 processed.jsonl 통째로 바꿔 쓰기
        P->>P: 더했으면 loaded +1
    end
```

**읽을 때 볼 것**
- 항목을 더한 그 자리에서 곧바로 처리 이력에 적는다. 모두 넣은 뒤에 한꺼번에 적지 않는다([[CCR-UC-001#UC-S6]] 4). 두 추가분은 한 커밋으로 올라간다(SEQ-7).
- 넣는 일에는 실패가 없다. 노션 때의 컬럼 확인 · 행 생성 실패 · 오늘 마감 미적재는 파일에 더하는 방식에서 일어날 수 없어 없어졌다([[CCR-DOM-001#Warning]]). 파일 쓰기가 실패하면 예상하지 못한 오류로 멈추고(SEQ-10) 마무리 단계가 반영된 데까지 올린다([[CCR-UC-001#UC-S6]] 2b).
- 식별자가 이미 목록에 있는 묶음은 SEQ-3이 걸렀어야 하는 경우다. 항목을 더하지 않고 처리 이력에만 적는다([[CCR-UC-001#UC-S6]] 2a).
- 미리보기는 항목을 만들기만 하고 쓰지 않는다. `Pipeline`이 넣었을 대회와 판별 근거를 로그에 남긴다([[CCR-UC-001#UC-A1]] 1b3).
- 기존 항목을 고치거나 지우는 메시지는 이 그림에 없다. 코드에도 없다. 상태 파일은 열지도 않는다.

## SEQ-6 실행 기록을 남긴다

[[CCR-UC-001#UC-S7]] 1 ~ 8 · 2a · 2b · 2c · 8a. 실패로 건너뛴 실행도 여기를 지난다.

```mermaid
sequenceDiagram
    autonumber
    participant P as Pipeline
    participant RS as RecordService
    participant FS as 데이터 파일
    P->>RS: zero_count_warnings(소스별 결과, State, 3일)
    RS->>RS: 기준일마다 모으기 · 0건 앞의 연속 일수 세기
    RS-->>P: 소스 0건 경고
    opt 실행 요약에 읽히지 않는 줄
        P-->>P: 경고 summary_corrupt
    end
    P->>P: 소요 시간
    P->>RS: write_run(RunLine)
    alt 목록에 쓰는 실행
        RS->>FS: 추가분 runs.jsonl에 이 실행의 줄(keep_count는 비움)
    else 미리보기
        RS-->>P: 쓰지 않음
    end
    P->>P: 경고 · 결과를 로그에
```

**읽을 때 볼 것**
- 경고 셋(소스 0건 · 판별 미룸 · 요약 파일 손상)은 어느 것도 결과를 바꾸지 않는다([[CCR-UC-001#UC-S7]] 3). 그날 조치할 고장(오늘 마감을 넣지 못함)은 커밋 실패로만 일어나고 Actions 실패로 드러난다([[CCR-UC-001#UC-A1]] 9a5).
- 줄에는 정해진 값만 들어간다. 원문 실패 사유와 판별 근거는 로그에만 간다([[CCR-DOM-003#runs]]).
- `keep_count`는 SEQ-7이 채운다.

## SEQ-7 마무리 단계가 올린다

[[CCR-UC-001#UC-A1]] 9 · 9a · \*a2 · [[CCR-INFRA-001]] 8.2.

```mermaid
sequenceDiagram
    autonumber
    participant WF as 워크플로
    participant F as finish.py
    participant FS as 추가분
    participant G as main
    WF->>F: python3 batch/finish.py (토큰은 이 스텝에만)
    F->>FS: 추가분 세 파일 읽기 · 형식 확인
    loop 다섯 번까지
        F->>G: 얕게 받기(되풀이면 fetch · reset)
        alt runs.jsonl에 이 실행의 줄이 있다
            F-->>WF: 앞선 올리기가 들어갔다. 끝
        end
        F->>F: 목록 추가분을 끝에 붙이기(이미 있는 식별자는 건너뜀)
        F->>F: 처리 이력 추가분을 끝에 붙이기
        F->>F: 남김 줄 세기 → keep_count
        alt 배치의 줄이 있다
            F->>F: 그 줄에 keep_count를 채워 붙이기
        else 없다(배치가 멈춤)
            F->>F: 중단 줄 붙이기 · 실패로 끝내기로 표시
        end
        F->>G: 세 경로만 커밋(github-actions[bot]) · push
        alt push 성공
            F-->>WF: 끝(표시에 따라 0 · 1)
        else 거절 · 끊김
            F->>F: 처음부터 다시
        end
    end
    F-->>WF: 끝내 실패(1)
```

**읽을 때 볼 것**
- 텍스트 병합이나 rebase에 맡기지 않고 최신 판 위에 다시 얹는다. 그사이 관리자가 버림 줄을 지운 커밋이 남는다. 페이지가 그사이 올린 상태 파일 커밋도 받은 `main`에 이미 들어 있어 부딪히지 않는다. `data/status.json`은 읽지도 스테이징하지도 않는다([[CCR-INFRA-001]] 8.2).
- 남김 줄 수는 얹은 뒤에 센다. 배치가 세면 올리다 빠진 줄만큼 커진다.
- 형식이 맞지 않는 추가분 줄은 붙이지 않고, 올린 뒤 실패로 끝낸다.
- 토큰은 받기와 push 명령에만 명령 줄 설정으로 준다. 명령을 로그에 찍지 않는다.

## SEQ-8 미리보기로 돌린다

[[CCR-UC-001#UC-A1]] 1b · 1b5 · 1b6 · 1b7. 수동 실행에서 `dry_run`을 켜거나, 기본 브랜치가 아닌 곳이나 개발자 PC에서 돌 때다.

```mermaid
sequenceDiagram
    autonumber
    participant WF as 워크플로
    participant M as 입구
    participant P as Pipeline
    participant LS as ListService
    participant RS as RecordService
    participant G as main
    WF->>M: DRY_RUN=true
    M->>M: RunContext — 쓰지 않음 · 버림 무시 여부
    M->>P: run()
    P->>RS: start()
    alt 기본 브랜치 밖 · 개발자 PC
        RS->>G: git fetch origin main
        RS->>RS: origin/main의 세 파일을 임시 폴더로
    end
    P->>LS: load()
    P->>RS: load()
    P->>P: 판별까지 평소대로, 넣었을 대회와 판별 근거를 로그에
    P->>LS: append
    LS-->>P: 항목(쓰지 않음)
    P->>RS: append · write_run
    RS-->>P: 쓰지 않음
    M-->>WF: 종료 코드
    Note over WF: 마무리 단계는 돌지 않는다
```

**읽을 때 볼 것**
- 판별 모델은 실제로 부른다. 무엇이 들어갈지 보려면 판별 결과가 필요하다. 이 호출도 비용에 들어간다([[CCR-UC-001#UC-A1]] 1b4).
- 버림 기록을 없는 것으로 보라는 입력(`ignore_discards`)은 이 모드에서만 먹는다. 쓰는 실행에서는 무시하고 로그에 적는다.
- origin/main을 받지 못하면 처리 이력 읽기 실패로 끝난다. 브랜치의 오래된 사본으로 돌지 않는다. 목록 파일도 같은 사본에서 읽는다([[CCR-DOM-002]] 5장 결정 5).
- 시크릿 없이도 돈다. OpenAI 키가 없으면 판별 미룸이 될 뿐이다.
- Actions 안에서 `DRY_RUN`이 `true`도 `false`도 아니면 입구가 아무것도 하지 않고 종료 코드 2로 끝난다.

## SEQ-9 실패로 기록 단계로 건너뛴다

[[CCR-UC-001#UC-A1]] 1d1 · 1d2 · 1d3 · 2b · 5a.

```mermaid
sequenceDiagram
    autonumber
    participant P as Pipeline
    participant CS as CollectService
    participant LS as ListService
    participant RS as RecordService
    P->>CS: collect_all
    alt 여섯 소스 모두 실패
        P-->>P: 실패(all_sources_failed)
    else
        P->>LS: load
        P->>RS: load
        alt 목록 파일 읽기 실패
            P-->>P: 실패(list_read_failed)
        else 처리 이력 읽기 실패 · 감소
            P-->>P: 실패(history_read_failed · history_shrank)
        end
    end
    P->>RS: SEQ-6(줄 남기기)
    Note over P: 종료 코드 1. 마무리 단계가 줄을 올린다
```

**읽을 때 볼 것**
- 반드시 있어야 하는 시크릿이 없어 설정 누락은 실패 사유가 아니다. Kaggle 토큰만 없으면 Kaggle에 설정 누락 표시만 남고(SEQ-2), OpenAI 키만 없으면 판별 미룸이다(SEQ-4).
- 실패 사유는 넷 가운데 먼저 걸린 하나만 적는다([[CCR-DOM-003#runs]]).

## SEQ-10 신호로 멈춘다

[[CCR-UC-001#UC-A1]] \*a · \*a2. 스텝 시간 한도(8분) · 수동 취소 · 예상하지 못한 오류다.

```mermaid
sequenceDiagram
    autonumber
    participant GH as 스케줄러
    participant M as 입구
    participant P as Pipeline
    participant F as finish.py
    GH->>M: SIGINT(시간 한도 · 취소)
    M->>M: 멈춤 표시
    P->>P: 다음 확인 지점에서 Stopped
    M->>M: 판별 스레드를 기다리지 않고 종료 코드 130
    opt 7.5초 뒤 SIGTERM
        GH->>M: 두 번째 신호 → 막힌 호출도 끊는다
    end
    GH->>F: 마무리 단계(always)
    F->>F: 배치의 줄이 없다 → 중단 줄(SEQ-7)
```

**읽을 때 볼 것**
- 배치는 신호를 받으면 줄을 쓰지 않는다. 끊긴 실행의 줄은 마무리 단계가 중단으로 쓴다.
- 목록과 처리 이력은 묶음마다 추가분에 반영돼 있어 넣은 데까지는 올라간다. 끊기는 순간 막 더한 항목 하나가 처리 이력에서 빠질 수 있다. 다음 실행이 목록 항목으로 그 대회를 알아보므로 다시 들어오지는 않는다([[CCR-INFRA-001]] 8.5).
- 예상하지 못한 오류(파이썬 예외)도 줄을 남기지 않고 종료 코드 1로 끝나, 마무리 단계가 중단으로 쓴다.

## SEQ-11 페이지를 열고 상태를 바꾼다

[[CCR-UC-001#UC-A2]] 1 ~ 6 · 1b · 4b · [[CCR-UC-001#UC-H1]] 1 ~ 5 · 1a · 1b · 1c · 4a · 4b · 4c. 화면은 [[CCR-UI-001#UI-1]]이다.

```mermaid
sequenceDiagram
    autonumber
    participant U as 참가자
    participant UI as CompetitionList
    participant RF as api/data · github
    participant GHB as GitHub
    participant TK as TokenStore
    participant ST as StatusStore
    U->>UI: 페이지를 연다(또는 새로 고침 2)
    UI->>TK: get()
    UI->>RF: readListFile()
    RF->>GHB: GET raw …/data/competitions.jsonl?t=…
    alt 토큰 있음
        UI->>RF: readStatusVersion(token)
        RF->>GHB: GET contents/data/status.json?ref=main(캐시 없음)
        opt 401 · 403 · 5xx · 연결 오류
            UI->>RF: readStatusFile()
            RF->>GHB: GET raw …/status.json?t=…
        end
    else 토큰 없음
        UI->>RF: readStatusFile()
        RF->>GHB: GET raw …/status.json?t=…(CDN이 5분까지 캐시)
    end
    alt raw 404
        GHB-->>RF: 목록은 빈 목록 · 상태는 빈 객체
    else raw 5xx · 연결 오류
        RF->>GHB: 한 번 다시
        RF-->>UI: DataReadError → 읽지 못했다는 알림
    end
    GHB-->>RF: 파일 내용
    RF-->>UI: 항목 · 상태 파일
    UI->>UI: Row로 합쳐 마감일 순 정렬 · 마감 지남 · 지움은 접힌 구역(9)
    U->>UI: 상태 셀렉트(7.4) · 지우기(7.5) · 별표(7.7) · 되살리기(9.1)
    UI->>TK: has()
    alt 토큰 없음
        UI-->>U: 토큰 없음(11). 값은 그대로
    else
        UI->>ST: setStatus · hide · restore · star · unstar(id, 대회명)
        ST-->>UI: onChange(얹은 파일, 저장 중) — 화면 먼저
        ST->>ST: 큐. 앞 커밋이 끝날 때까지 기다림
        ST->>RF: readStatusVersion(token)
        RF->>GHB: GET contents/data/status.json?ref=main
        GHB-->>RF: sha · 내용(404면 sha 없음)
        ST->>ST: mergeChange — 이번 바꿈만 얹음
        ST->>RF: writeStatusFile(token, 파일, sha, 메시지)
        RF->>GHB: PUT contents/data/status.json(Base64 · sha · status: … → …)
        alt 200 · 201
            GHB-->>RF: content.sha
            ST-->>UI: onChange(파일, 저장 끝)
        else 409 · 422(판 어긋남)
            ST->>RF: 다시 읽고 한 번 더 쓴다
            ST-->>UI: 그래도 실패면 되돌리고 저장 실패(12)
        else 401 · 403 · 404 · 5xx · 연결 오류
            ST-->>UI: 값 되돌리고 저장 실패(12)
        end
    end
```

**읽을 때 볼 것**
- 목록 파일은 raw로 읽는다. 상태 파일은 토큰이 있으면 Contents API로 읽고, 없거나 실패하면 raw로 읽는다. raw는 CDN이 5분 캐시하고 `?t=`로도 피하지 못해, 방금 바꾼 상태가 새로 고친 뒤 옛 값으로 보이기 때문이다. 쓰기의 기준은 늘 커밋 직전에 다시 읽은 판이다([[CCR-INFRA-001]] 6.4).
- GitHub에 쓰는 길은 `StatusStore` 하나이고 한 번에 요청 하나다. 같은 판으로 두 번 보내면 둘째가 409로 거절되기 때문이다([[CCR-DOM-002]] 5장 결정 10 · [[CCR-API-001]] 1.4).
- 판이 어긋나면 한 번만 다시 쓴다. 5xx · 연결 오류는 스스로 되풀이하지 않고 「다시 시도」(12.2)를 기다린다([[CCR-API-001]] 2.3).
- 배치가 같은 때 커밋해도 부딪히지 않는다. 파일이 다르고, Contents API는 파일 단위의 판으로 견준다([[CCR-UC-001#UC-H1]] 4c).
- 토큰은 `Authorization` 헤더에만 실린다. raw 읽기에는 보내지 않는다([[CCR-INFRA-001]] 5.8).

## SEQ-12 토큰을 넣는다

[[CCR-UC-001#UC-H2]] 1 ~ 6 · 3a · 4a · 4b. 화면은 [[CCR-UI-001#UI-2]]다.

```mermaid
sequenceDiagram
    autonumber
    participant U as 참가자
    participant UI as SettingsDialog
    participant RF as api/github
    participant GHB as GitHub
    participant TK as TokenStore
    U->>UI: 설정(6) · 설정 열기(11.1 · 12.1)
    UI->>TK: has()
    UI-->>U: 토큰 있음 · 없음(20.6). 값은 보이지 않음
    U->>UI: 토큰 붙여 넣기(20.3) · 확인하고 저장(20.4)
    UI->>RF: readStatusVersion(입력한 토큰)
    RF->>GHB: GET contents/data/status.json?ref=main
    alt 200 · 404(파일 없음)
        GHB-->>RF: 판 · 내용
        UI->>TK: set(토큰)
        UI-->>U: 닫힘. 쓰기 권한은 SEQ-11의 첫 저장에서 드러난다
    else 401 · 403
        RF-->>UI: GitHubError(status)
        UI-->>U: 이유를 칸 아래에. 저장하지 않음
    end
    opt 토큰 지우기(20.5)
        U->>UI: 지우기
        UI->>TK: clear()
        UI-->>U: 읽기만 되는 상태
    end
```

**읽을 때 볼 것**
- 저장 전에 반드시 판 읽기로 검증한다. 검증에 실패한 값은 저장하지 않는다([[CCR-UC-001#UC-H2]] 4 · 4a).
- 404는 상태 파일이 아직 없다는 뜻뿐이다. 이 저장소는 공개이고 fine-grained 토큰은 늘 모든 공개 저장소를 읽을 수 있어, 판 읽기로는 쓰기 권한을 가르지 못한다. 쓰기 권한이 모자란 토큰은 저장된 뒤 SEQ-11의 첫 쓰기가 거절되어(403 · 404) 드러나고, 값이 되돌아가며 저장 실패(12)가 뜬다([[CCR-UC-001#UC-H2]] 4b · [[CCR-API-001]] 2.3).
- 토큰은 `localStorage`에만 둔다. 서버가 없어 다른 곳으로 가지 않는다. 지우기는 브라우저에서만 지우고, GitHub 쪽 폐기는 참가자가 한다([[CCR-UC-001#UC-H2]] 3a).

## 1. 대응표

| 시퀀스 | 유스케이스 | 주요 함수 |
|---|---|---|
| SEQ-1 | [[CCR-UC-001#UC-A1]] 1 ~ 10 | [[CCR-MS-001#Pipeline.run]] · [[CCR-MS-001#__main__.main]] · [[CCR-MS-001#__main__.run_batch]] |
| SEQ-2 | [[CCR-UC-001#UC-S1]] · [[CCR-UC-001#UC-S2]] | [[CCR-MS-001#CollectService.collect_all]] · [[CCR-MS-001#CollectService._collect_one]] · [[CCR-MS-001#SourceHttp.fetch]] · [[CCR-MS-001#robots.ensure_allowed]] · 어댑터 함수 |
| SEQ-3 | [[CCR-UC-001#UC-S3]] · [[CCR-UC-001#UC-S4]] | [[CCR-MS-001#ScreenService.drop_expired]] · [[CCR-MS-001#ListService.load]] · [[CCR-MS-001#RecordService.load]] · [[CCR-MS-001#RecordService.history_shrank]] · [[CCR-MS-001#ScreenService.build_known]] · [[CCR-MS-001#ScreenService.bundle]] · [[CCR-MS-001#ScreenService.split_known]] · [[CCR-MS-001#matching.judge_pair]] · [[CCR-MS-001#matching.group]] |
| SEQ-4 | [[CCR-UC-001#UC-S5]] | [[CCR-MS-001#ScreenService.judge]] · [[CCR-MS-001#ScreenService._ask_all]] · [[CCR-MS-001#OpenAiJudge.judge]] |
| SEQ-5 | [[CCR-UC-001#UC-S6]] | [[CCR-MS-001#Pipeline._load]] · [[CCR-MS-001#ListService.append]] · [[CCR-MS-001#list.entry_of]] · [[CCR-MS-001#RecordService.append]] |
| SEQ-6 | [[CCR-UC-001#UC-S7]] | [[CCR-MS-001#Pipeline._finish]] · [[CCR-MS-001#RecordService.zero_count_warnings]] · [[CCR-MS-001#RecordService.write_run]] |
| SEQ-7 | [[CCR-UC-001#UC-A1]] 9 · \*a2 | [[CCR-MS-001#finish.finish]] · [[CCR-MS-001#finish.read_additions]] · [[CCR-MS-001#Git.fresh_main]] · [[CCR-MS-001#Git.commit_and_push]] |
| SEQ-8 | [[CCR-UC-001#UC-A1]] 1b | [[CCR-MS-001#RunContext.from_env]] · [[CCR-MS-001#record.export_main_state]] · [[CCR-MS-001#ListService.load]] |
| SEQ-9 | [[CCR-UC-001#UC-A1]] 1d · 2b · 5a | [[CCR-MS-001#Pipeline._run]] |
| SEQ-10 | [[CCR-UC-001#UC-A1]] \*a | [[CCR-MS-001#__main__.main]] · [[CCR-MS-001#finish.finish]] |
| SEQ-11 | [[CCR-UC-001#UC-A2]] · [[CCR-UC-001#UC-H1]] | [[CCR-DOM-002#CompetitionList]] · [[CCR-DOM-002#StatusStore]] · [[CCR-DOM-002#RepoFiles]] |
| SEQ-12 | [[CCR-UC-001#UC-H2]] | [[CCR-DOM-002#SettingsDialog]] · [[CCR-DOM-002#TokenStore]] · [[CCR-DOM-002#RepoFiles]] |

## 2. 되먹일 것

시퀀스를 그리며 코드와 실측에서 찾은 것 가운데 상위 문서를 고쳐야 하는 것이다. 이 문서는 상위 문서를 고치지 않는다. 1 ~ 6은 2026-09-28에 상위 문서에 반영했다. 7은 2026-09-29에 찾았고 2026-09-30에 반영했다([[CCR-INFRA-001]] v7 · [[CCR-DOM-003]] v4).

1. **[[CCR-API-001]] wevity 상세 요청.** `gbn=view`가 같은 사이트의 `gbn=viewok`로 302를 보낸다(2026-09-27 실측). 날수 맞춰 보기의 상세 요청은 리디렉션을 따라가도록 구현했다(SEQ-2). 엔드포인트 절과 1.2의 리디렉션 규칙에 이 예외를 적는다.
2. **[[CCR-PRD-001]] 5.2 · [[CCR-UC-001#UC-S4]] 같은 대회 판정.** 실측 후보 321건에서 판정표가 틀박이 이름의 서로 다른 대회를 이었다(가장 큰 묶음 스무 건). 사용자가 문턱 0.90 · 모든 짝 규칙으로 정했다(2026-09-28, [[CCR-DOM-002]] 5장 결정 7).
3. **[[CCR-DOM-001]] 6장 미결 셋이 풀렸다.** 묶음의 접수마감일(가장 늦은 값), 결과가 다른 둘과 함께 같을 때(남김), HTML 파서(selectolax). [[CCR-DOM-002]] 5장 결정 1 · 2 · 3. 도메인 모델의 미결을 닫는다. [[CCR-INFRA-001]] 9장의 파서 미결도 같다.
4. **[[CCR-UC-001#UC-S2]] 4 · [[CCR-API-001]] 1.2 대회명 다듬기.** event-us · 콘테스트코리아가 대회명 앞에 BOM(U+FEFF)을 붙여 주는 일이 있다. 앞뒤를 다듬을 때 공백과 함께 보이지 않는 서식 문자도 뗀다고, HTML 소스는 브라우저가 보여 주는 대로 이어진 공백을 하나로 모은다고 적는다.
5. **[[CCR-INFRA-001]] 8.1 코드 받기 스텝.** 다른 브랜치의 미리보기가 main 최신 판의 상태 파일을 읽는 일은 워크플로 스텝이 아니라 배치(기록 경계)가 git으로 한다(SEQ-8). 개발자 PC와 같은 길이다. 스텝 표의 문장을 이에 맞춘다.
6. **[[CCR-INFRA-001]] 8.1 종료 코드.** 쓰기 여부 값이 깨졌으면 2, 신호로 멈추면 130이다. 8.6 표의 "쓰기 여부 값이 true · false가 아님" 행에 종료 코드를 적는다.
7. **[[CCR-INFRA-001]] 8.2 목록 추가분의 필수 필드.** 8.2는 식별자 · 대회명 · 링크 · 출처 · 수집일 다섯을 부르는데, ERD([[CCR-DOM-003#competitions]])는 `id` · `source` · `source_id` · `title` · `link` · `collected_on` 여섯이다. 식별자가 출처와 원천 ID를 품으므로 뜻은 같지만, 마무리 단계가 따르는 것은 ERD다. INFRA의 문장을 "ERD의 필수 필드"로 고치면 두 문서가 어긋나지 않는다.

## 3. 미결사항

2026-10-01에 SEQ-2의 Kaggle 목록 요청을 실측했다. 다른 소스와 같은 모양이라 그림은 그대로 두고 읽을 때 볼 것에 한 줄을 더했다.

- [ ] SEQ-11의 브라우저 쓰기와 SEQ-12는 실측 전이다. 2026-09-30에 페이지의 실제 저장 코드를 브라우저 밖에서 돌려, 상태 파일을 만들고(판 없이 쓰기) 고치는(판 위에 쓰기) 흐름까지 보았다([[CCR-CODE-001]] 4장). 같은 날 raw 캐시를 재어 상태 파일의 표시용 읽기를 토큰이 있으면 Contents API로 바꿨다([[CCR-INFRA-001]] 6.4). 페이지 토큰을 넣은 뒤 브라우저에서 Contents API의 409 · 422 응답과, 쓰기 권한이 모자란 토큰의 첫 쓰기가 403인지 404인지 실제로 보고 다시 그린다
