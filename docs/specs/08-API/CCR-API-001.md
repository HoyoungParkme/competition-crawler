---
doc_id: CCR-API-001
type: API
title: 대회 수집 배치 API 명세 REST
status: draft
upstream: [CCR-RFQ-001, CCR-PRD-001, CCR-UC-001, CCR-INFRA-001, CCR-DOM-001, CCR-UI-001]
---

# API 명세 REST — 대회 수집 배치

## 0. 이 문서가 다루는 것

배치와 대회 목록 페이지가 부르는 바깥 엔드포인트를 적는다. 배치는 대회 소스 여섯(event-us · DACON · Kaggle · wevity · AI팩토리 · 콘테스트코리아)과 관련도 판별에 쓰는 OpenAI를 부르고, 페이지는 저장소 파일을 읽고 쓰는 GitHub를 부른다. 배치도 페이지도 서버가 없어 자기 엔드포인트가 없다([[CCR-INFRA-001#C1]] · [[CCR-INFRA-001#C14]]). 2026-09-29까지 있던 노션 항목 넷은 노션을 쓰지 않기로 하면서 지웠다.

항목 하나가 엔드포인트 하나다. 헤딩은 `메서드/호스트/경로`다. 호스트가 여럿이라 경로만으로는 가를 수 없어 호스트를 넣는다. 항목 ID는 50자까지라 긴 경로는 줄여 적는다. Kaggle의 서비스 이름과 GitHub의 `{owner}/{repo}`는 `…`로 줄였다. 온전한 경로는 그 항목의 yaml에 있다. 블록마다 한 줄 요약, 유스케이스와 도메인 개념, 받은 값을 공통 형식으로 옮기는 법, 그 엔드포인트의 yaml을 둔다. yaml은 OpenAPI의 모양을 빌리되 배치가 보내고 읽는 것만 적는다. 응답에는 쓰지 않는 필드가 훨씬 많다.

확인한 방법은 셋이다.
- **실측:** 소스 다섯은 2026-09-23에 직접 불러 봤다. wevity · 콘테스트코리아는 2026-09-27에 다시 불렀고, wevity는 2026-09-28 아침에 한 번 더 불렀다. Kaggle은 2026-10-01에 사용자의 토큰으로 불렀다.
- **공식 클라이언트 코드:** Kaggle의 엔드포인트와 요청 모양은 공식 클라이언트(`kagglesdk`) 코드에서 찾았다. 쪽 넘김은 코드와 달라 실측을 따랐다(3.1 Kaggle).
- **공식 문서:** OpenAI와 GitHub는 공식 문서로 확인했다. GitHub Contents API는 2026-09-29에 이 저장소의 파일 하나를 읽어 응답 모양을 봤다.

event-us와 DACON의 JSON API는 사이트가 스스로 쓰는 것이라 공개 문서가 없다. wevity · AI팩토리 · 콘테스트코리아는 페이지를 읽는다. 어느 것이든 예고 없이 바뀔 수 있다([[CCR-PRD-001#R9]]).

이 문서가 닫는 상위 미결은 아래와 같다.

| 미결 | 정한 것 | 자리 |
|---|---|---|
| AI팩토리 과제를 대회로 합치는 법과 대회명([[CCR-PRD-001]] 6장 · [[CCR-DOM-001]] 6장) | 페이지 이름과 접수시작일로 합치고, 대회명은 네 차례로 정한다 | 3.1 AI팩토리 |
| 소스마다 채우는 날짜와 부가 정보(같은 두 곳) | 소스별 필드. Kaggle은 2026-10-01 실측으로 확정했다 | 4.1 |
| Kaggle 호출 방식([[CCR-INFRA-001]] 3장) | 공식 API의 대회 목록을 일반 탭만 `page`로 넘겨 받는다. 커뮤니티 탭은 받지 않는다 | 3.1 Kaggle |
| 페이지가 저장소를 읽고 쓰는 모양([[CCR-INFRA-001]] 8.11) | 목록 파일은 raw로 읽는다. 상태 파일은 토큰이 있으면 Contents API로, 없으면 raw로 읽는다. 쓰기 직전의 판 읽기와 쓰기는 Contents API로 한다 | 1.4 · 3.3 |
| 판이 어긋난 쓰기를 어떻게 다시 보낼지([[CCR-UC-001#UC-H1]] 4a) | 최신 판을 다시 읽고 이번 바꿈만 얹어 한 번 더 쓴다 | 2.3 |

여기서 정하지 않는 것도 있다. 클래스와 메서드는 클래스 명세가, 데이터 파일 한 줄의 필드 이름과 형식은 ERD([[CCR-DOM-003]])가 정한다. 타임아웃 · 재시도 횟수 · 시간 예산의 수치는 [[CCR-INFRA-001]] 8.5가 정했다. 이 문서는 어느 응답을 다시 보낼지를 가른다(2장).

## 1. 규칙

### 1.1 모든 요청

- **User-Agent**는 `competition-crawler/0.1 (+https://github.com/HoyoungParkme/competition-crawler)`다. 앞은 이름과 버전이고, 괄호 안은 연락처 삼아 적은 저장소 주소다. 누가 보냈는지 알 수 있게 한다([[CCR-PRD-001#N4]]). 2026-09-23 실측은 모두 이 문자열로 했고 소스 다섯이 200을 줬다.
- **요청 간격**은 같은 소스 안에서 요청 사이 1초다. `robots.txt` 요청도 센다([[CCR-INFRA-001]] 8.5).
- **쿠키**는 남기지 않는다. 응답이 심은 쿠키를 다음 요청에 싣지 않는다. Kaggle은 응답마다 익명 세션 쿠키(`ka_sessionid`)를 심는데, 그 쿠키가 실린 요청은 토큰이 있어도 401로 거절한다. `robots.txt`의 404 응답도 이 쿠키를 심는다(2026-10-01 실측). 같은 날 나머지 다섯 소스도 쿠키 없이 불러 예약 실행과 같은 건수를 받았다.
- **비밀값**은 환경 변수로만 받는다([[CCR-INFRA-001]] 5장). 요청 헤더와 요청 객체는 로그에 찍지 않는다([[CCR-UC-001#UC-S7]] 7 · [[CCR-INFRA-001]] 5.4).
- **시간대.** 시간대가 붙은 시각은 KST로 바꾼 뒤 날짜만 쓴다. 시간대 표기가 없는 값은 KST로 보고 바꾸지 않는다([[CCR-UC-001#UC-S2]] 2 · 2b). 기준일 00:00 KST는 UTC로 전날 15:00이다. 기준일이 2026-09-23이면 `2026-09-22T15:00:00+00:00`이다.
- **빈 값.** 알 수 없는 날짜는 빈 값으로 둔다. 파일에는 빈 문자열이 아니라 `null`로 적는다([[CCR-DOM-003]]).
- **페이지의 요청**은 브라우저의 `fetch`다. User-Agent는 브라우저가 보내고, 배치의 것을 흉내 내지 않는다. `Authorization` 헤더는 `api.github.com`에만 보내고 raw 읽기에는 보내지 않는다. 토큰은 주소·콘솔에 싣지 않는다([[CCR-INFRA-001]] 5.8).

### 1.2 대회 소스

**robots.txt.** 소스가 요청하는 호스트마다 실행에 한 번 받는다([[CCR-UC-001#UC-S1]] 2). robots.txt는 호스트마다 따로 두는 것이라(RFC 9309) 요청하는 호스트의 것을 본다. event-us는 `api.event-us.kr`, DACON은 `app.dacon.io`의 것이다. 배치는 상세 링크를 만들기만 하고 열지 않으므로, 상세 링크의 호스트(`event-us.kr` · `dacon.io`)의 robots.txt는 보지 않는다. robots.txt의 리디렉션은 RFC 9309대로 다섯 번까지 따라간다.

| robots.txt 응답 | 처리 |
|---|---|
| 200 | 목록 경로가 막혀 있으면 요청하지 않고 실패(수집 금지)로 둔다([[CCR-UC-001#UC-S1]] 2c) |
| 4xx | 제한이 없는 것으로 본다 |
| 5xx · 연결 오류 | 다시 받아 본다. 그래도 받지 못하면 목록을 요청하지 않는다. RFC 9309는 robots.txt에 닿지 못하면 모두 막힌 것으로 보라고 한다. 실패의 종류는 다른 요청과 같이 5xx면 응답 코드, 연결 오류면 연결이다(2.1) |

2026-09-23에는 여섯 호스트 모두 목록 경로를 막지 않았다. `www.wevity.com`과 `www.contestkorea.com`은 200(`User-agent: *`에 `Allow: /`)이었고, `api.event-us.kr` · `app.dacon.io` · `api.kaggle.com` · `aifactory.space`는 404였다.

**링크 정규형.** 판정 1단계는 출처·원천 ID로 견주고, 링크는 소스가 개편해 원천 ID가 바뀐 공고를 잇는 예비다([[CCR-UC-001#UC-S4]] 판정 1단계). 링크는 목록 항목과 처리 이력에 그대로 남으므로, 같은 공고는 어느 목록에서 받든 늘 같은 링크여야 한다. 목록의 링크에는 분야 · 쪽 번호가 붙어 있어 그대로 쓰지 않고 아래 모양으로 만든다. 모두 2026-09-23에 200으로 열렸다.

| 소스 | 상세 링크 |
|---|---|
| event-us | `https://event-us.kr/{subdomain}/event/{id}` |
| DACON | `https://dacon.io/competitions/official/{cpt_id}/overview/description`. `is_landing_cpt`가 1이면 `https://dacon.io/competition/{cpt_id}/overview` |
| Kaggle | `https://www.kaggle.com/competitions/{slug}` |
| wevity | `https://www.wevity.com/?c=find&s=1&gbn=view&ix={ix}` |
| AI팩토리 | `https://aifactory.space/competitions/{과제 id}` |
| 콘테스트코리아 | `https://www.contestkorea.com/sub/view.php?int_gbn=1&str_no={str_no}` |

원천 ID를 읽지 못하면 위 모양으로 링크를 만들 수 없다. wevity · 콘테스트코리아는 목록의 링크를 절대 주소로 바꿔 상세 링크로 쓰고, 그것을 원천 ID로도 쓴다([[CCR-UC-001#UC-S2]] 1c). 나머지 넷은 링크를 원천 ID로만 만들므로 그 항목을 버린다([[CCR-UC-001#UC-S2]] 1b).

**쪽 넘김.** 소스마다 멈추는 때가 다르다. 어느 소스든 쪽 상한은 20이다([[CCR-UC-001#UC-S1]] 3a · [[CCR-INFRA-001]] 8.5). 상한에 닿으면 그때까지 받은 목록을 실패 표시 없이 돌려주고 로그에 남긴다([[CCR-DOM-001#SourceResult]]).

| 소스 | 한 쪽 | 멈추는 때 | 실측 쪽 수 |
|---|---|---|---|
| event-us | 100건 | `meta.page.total_pages`까지 읽었을 때 | 1쪽(09-23) |
| DACON | 15건 | 접수 중인 대회가 하나도 없는 쪽을 읽었을 때 | 2쪽(09-23) |
| Kaggle | 20건. 바꿀 수 없다 | 빈 쪽을 받았거나, 한 쪽의 대회가 모두 마감됐을 때 | 2쪽과 빈 쪽 하나(10-01) |
| wevity | 15건 | 분야마다, 마지막 항목의 상태가 `마감`이거나 항목이 없는 쪽을 읽었을 때. 쪽 상한 20은 다섯 분야를 합친 것이다 | 다섯 분야 합쳐 11쪽(09-27 · 09-28). 상세 1쪽은 따로다 |
| AI팩토리 | 전부 | 목록이 한 페이지에 다 있다 | 1쪽(09-23) |
| 콘테스트코리아 | 12건 | 분야마다, 12건보다 적은 쪽을 읽었을 때. 빈 쪽도 여기 든다. 쪽 상한 20은 두 분야를 합친 것이다 | 두 분야 합쳐 13쪽(09-27) |

**여러 분야를 받는 소스.** wevity와 콘테스트코리아는 분야를 3.1의 표에 적은 차례로 읽는다. 쪽 상한에 닿으면 남은 분야는 읽지 않는다. wevity의 날수 맞춰 보기(상세 1쪽)는 상한에 세지 않고, 상한에 닿아도 한다. 수집 건수는 원천 ID로 합친 뒤의 건수다([[CCR-DOM-001#SourceResult]]).

**리디렉션.** 목록 요청은 리디렉션을 따라가지 않는다. 3xx가 오면 실패(응답 코드)로 둔다. 목록 주소가 바뀐 것이라 사람이 알아채야 한다. wevity의 날수 맞춰 보기(상세 한 쪽)만은 같은 사이트 안의 리디렉션을 따라간다. 상세 주소가 늘 `gbn=viewok`로 302를 보내기 때문이다([[#GET/www.wevity.com/?c=find&gbn=view]]).

**응답이 예상과 다를 때.** 목록의 틀을 찾지 못하면 그 소스를 실패(형식)로 둔다. JSON이 아니거나, 목록 배열이나 목록 요소가 없는 경우다. 틀은 있는데 항목이 0개면 실패가 아니라 0건이다([[CCR-UC-001#UC-S1]] 2b). 항목 하나에서 대회명이나 링크를 채우지 못하면 그 항목만 버린다([[CCR-UC-001#UC-S2]] 1b). 날짜 하나를 읽지 못하면 그 날짜만 비운다([[CCR-UC-001#UC-S2]] 2a).

**대회명.** 앞뒤의 공백과 보이지 않는 서식 문자만 뗀다. event-us · 콘테스트코리아는 대회명 앞에 BOM(U+FEFF)을 붙여 주는 일이 있다(2026-09-27). HTML에서 읽는 wevity · 콘테스트코리아는 브라우저가 보여 주는 대로 이어진 공백을 하나로 모은 뒤 다듬는다. JSON으로 받는 소스는 가운데 공백을 건드리지 않는다([[CCR-UC-001#UC-S2]] 4).

**부가 정보**는 소스가 준 분야 · 태그 · 키워드 · 주최 · 대상 같은 짧은 낱말을 모은 것이다. AI팩토리는 페이지 이름과 과제명이다. 판별 요청에 쓴다([[CCR-UC-001#UC-S5]] 1). 상위 문서도 이에 맞췄다([[CCR-DOM-001#Competition]]).

### 1.3 판별(OpenAI)

- **공식 SDK의 Responses API를 쓴다**([[CCR-INFRA-001]] 3장). `responses.parse`에 4.3과 같은 모양의 응답 모델을 넘긴다. SDK가 그 모델로 엄격한 JSON 스키마를 만들어 `text.format`으로 보내고, 답을 그 모델로 읽는다. 3.2의 yaml은 실제로 보내지는 모양이다.
- **SDK의 자동 재시도는 끈다.** 기본으로 2회 다시 보내는데 지출 한도 429까지 다시 보낸다. `max_retries=0`으로 두고 2.2대로 직접 다시 보낸다. 요청 타임아웃은 [[CCR-INFRA-001]] 8.5대로 준다.
- **`reasoning.effort`는 `none`으로 둔다.** 분류라 추론이 필요 없다. 두 후보 모델의 기본값은 `medium`이다. 그대로 두면 추론 토큰이 출력 토큰으로 과금돼 [[CCR-INFRA-001]] 8.9의 호출당 비용 가정이 깨진다.
- **`max_output_tokens`는 300으로 둔다.** 답이 `decision`과 한 줄 근거뿐이라 넉넉하다. 넘치면 잘려 판별 실패가 된다(2.2).
- **`store`는 `false`로 둔다.** 기본값이 true라 그대로 두면 응답이 OpenAI 쪽에 저장된다. 판별에는 저장이 필요 없다.
- **모델**은 설정값이다([[CCR-INFRA-001]] 4.1). 바꿀 때는 Structured Outputs와 `reasoning.effort: none`을 모두 받는 모델에서 고른다. 상위 모델인 `gpt-6-astra`는 `none`을 받지 않아, 그 모델로 바꾸면 요청마다 400이 온다(2.2). 2026-09-23의 공식 가격표로 후보는 둘이다.

| 모델 | 100만 토큰당 입력 · 출력 | 비고 |
|---|---|---|
| `gpt-6-luna` | 0.10달러 · 0.50달러 | 2026-09-22에 나왔다 |
| `gpt-5.6-luna` | 0.20달러 · 1.20달러 | [[CCR-INFRA-001]] 8.9의 비용 예시 |

기본값은 싼 쪽인 `gpt-6-luna`로 했다(`batch/settings.toml`). 저장소 변수 `OPENAI_MODEL`이 있으면 그것을 쓴다.

### 1.4 저장소 파일 — 페이지가 읽고 쓰는 법

페이지는 서버 없이 GitHub의 공개 파일 주소와 REST API만 쓴다([[CCR-INFRA-001]] 8.11). 저장소는 `HoyoungParkme/competition-crawler`, 브랜치는 `main`이고, 둘 다 페이지 설정 파일의 상수다([[CCR-INFRA-001]] 4.1).

- **읽는 길은 둘이다.** 목록 파일은 `raw.githubusercontent.com`에서 인증 없이 받는다([[#GET/raw.githubusercontent.com/…/data/{file}]]). 상태 파일은 토큰이 있으면 Contents API로 읽고([[#GET/api.github.com/…/contents/data/status.json]]), 토큰이 없거나 API로 읽지 못하면 raw로 받는다. 쓰기 직전에도 Contents API로 다시 읽어 판(`sha`)을 얻는다. raw는 CDN이 5분 캐시하므로 쓰기의 기준으로 쓰지 않고, 사용자가 방금 바꾼 상태를 보여 주는 데도 쓰지 않는다([[CCR-INFRA-001]] 6.4).
- **캐시를 피하는 쿼리.** raw 주소에는 `?t=<현재 시각 ms>`를 붙인다. 같은 주소가 반복되지 않아 브라우저 캐시를 피한다. CDN 캐시는 피하지 못한다. 응답은 `cache-control: max-age=300`이고, 2026-09-30 실측에서 새 커밋이 raw에 보이기까지 58초 · 267초가 걸렸으며 쿼리를 붙인 주소와 붙이지 않은 주소가 같은 때 바뀌었다([[CCR-INFRA-001]] 6.4).
- **API 헤더.** `Accept: application/vnd.github+json` · `X-GitHub-Api-Version: 2022-11-28` · `Authorization: Bearer <페이지 토큰>`. 토큰은 fine-grained personal access token이고 이 저장소의 Contents 읽기·쓰기만 있다([[CCR-INFRA-001]] 5.8).
- **쓰기는 파일 하나를 한 커밋으로 올린다**([[#PUT/api.github.com/…/contents/data/status.json]]). 본문에 새 내용(UTF-8 JSON을 Base64로), 읽어 둔 `sha`, 커밋 메시지, `branch: main`, 커밋 작성자(`author`·`committer`)를 넣는다. 파일이 아직 없으면 `sha` 없이 보내 만든다.
- **커밋 작성자.** `author`와 `committer`에 같은 값, 저장소 주인의 이름과 noreply 주소(`<id>+<login>@users.noreply.github.com`)를 넣는다. 페이지 설정 파일의 상수다([[CCR-INFRA-001]] 4.1 · 8.11). GitHub 문서대로 `committer`를 빼면 인증한 사용자(토큰 주인)가, `author`를 빼면 `committer`가 그 자리에 들어간다. 인증한 사용자의 정보에는 계정의 기본 이메일이 쓰여, 이메일 비공개 설정이 꺼진 계정이면 개인 주소가 공개 커밋에 남는다. 그래서 둘 다 보낸다. 둘 다 `name`과 `email`이 있어야 하고, 빠지면 422다.
- **커밋 메시지**는 페이지가 만든다. 상태를 바꾸면 `status: <대회명> → <상태 이름>`, 지우면 `status: <대회명> 지움`, 되살리면 `status: <대회명> 되살림`, 별표를 붙이면 `status: <대회명> 별표`, 떼면 `status: <대회명> 별표 뗌`이다. 대회명은 60자에서 자른다.
- **한 번에 요청 하나.** 앞 쓰기의 응답이 오기 전에 다음 바꿈이 생기면 줄 세워 차례로 보낸다. 같은 `sha`로 두 번 보내면 둘째가 409로 거절되기 때문이다. 화면은 먼저 바뀐다([[CCR-UC-001#UC-H1]] 2).
- **판이 어긋나면**(409 · 422) 최신 판을 다시 읽고, 이번 바꿈만 그 위에 얹어 한 번 더 쓴다. 다른 기기가 바꾼 다른 대회의 값은 남는다(2.3).
- **크기.** Contents API의 `GET`은 1MB까지 내용을 돌려준다. 상태 파일은 항목 하나가 100바이트 안팎이라 수천 건이어도 그 안이다. 목록 파일은 raw로만 읽으므로 이 한도와 상관없다.
- **한도.** 인증한 요청은 시간당 5,000회다. 페이지를 열고 새로 고칠 때의 읽기와 사람이 누르는 쓰기를 합쳐도 닿지 않는다. raw 읽기는 별도이고 한도가 공개되지 않았다.
- **목록 파일 읽기.** 줄마다 JSON으로 읽는다. 읽히지 않는 줄은 건너뛴다. 식별자가 같은 줄이 여럿이면 앞의 것을 쓴다. 상태 파일에 있고 목록에 없는 식별자는 무시한다([[CCR-INFRA-001]] 6.2).
- **필드 이름**은 ERD가 정한다([[CCR-DOM-003]]). 4.2에 페이지가 읽고 쓰는 값만 적는다.

## 2. 에러

### 2.1 대회 소스

실패하면 그 소스는 빈 목록과 실패 표시를 돌려준다([[CCR-UC-001#UC-S1]] 2a). 실패의 종류는 [[CCR-DOM-001#SourceResult]]의 다섯 가운데 하나다. 다시 보내는 횟수와 기다림은 [[CCR-INFRA-001]] 8.5를 따른다.

| 상황 | 실패의 종류 | 다시 보내나 |
|---|---|---|
| 연결 오류 · 타임아웃 | 연결 | 보낸다 |
| 소스의 시간 예산을 넘김 | 연결 | 보내지 않는다([[CCR-UC-001#UC-S1]] \*a) |
| 429 · 5xx | 응답 코드 | 보낸다. `Retry-After`가 상한이나 남은 예산보다 길면 보내지 않는다([[CCR-UC-001#UC-S1]] 2a1) |
| 3xx | 응답 코드 | 보내지 않는다. 리디렉션을 따라가지 않는다(1.2) |
| 그 밖의 4xx(401 · 403 · 404 등) | 응답 코드 | 보내지 않는다 |
| 응답이 예상과 다름(1.2) | 형식 | 보낸다 |
| robots.txt가 목록 경로를 막음 | 수집 금지 | 요청하지 않는다 |
| robots.txt를 끝내 받지 못함 | 5xx면 응답 코드, 연결 오류면 연결 | 목록을 요청하지 않는다(1.2) |
| Kaggle 토큰이 설정에 없음 | 설정 누락 | 요청하지 않는다([[CCR-UC-001#UC-S1]] 1a) |

wevity의 날수 맞춰 보기(상세 페이지 한 쪽)는 실패해도 소스를 실패로 두지 않는다. 보정값을 −1로 둔다(3.1).

### 2.2 판별(OpenAI)

다시 물어도 같은 답이 올 오류면 그 묶음을 판별 실패로 두고, 아직 묻지 않은 묶음도 묻지 않는다([[CCR-UC-001#UC-S5]] 2a1). 다시 묻는 횟수는 [[CCR-INFRA-001]] 8.5를 따른다.

| 응답 | 처리 |
|---|---|
| 200, `status`가 `completed`이고 답이 스키마에 맞음 | 판별 결과 |
| 200, `status`가 `completed`가 아님(`incomplete` · `failed`) | 그 묶음만 판별 실패. 다시 묻지 않는다. `incomplete`는 `max_output_tokens`에 닿아 잘렸거나 내용 필터에 걸린 것이다 |
| 200, 거절이거나 답이 스키마에 맞지 않음 | 그 묶음만 판별 실패. 다시 묻지 않는다([[CCR-UC-001#UC-S5]] 2a) |
| 401 · 403 · 404 | 같은 답. 남은 묶음도 묻지 않는다. 키 · 권한 · 모델 이름의 문제다 |
| 408 · 409 | 다시 묻는다 |
| 429, `error.code`가 `credit_balance_exhausted` · `organization_spend_limit_exceeded` · `project_spend_limit_exceeded` · `organization_usage_limit_exceeded`이거나 `error.type`이 `insufficient_quota` | 같은 답. 남은 묶음도 묻지 않는다 |
| 그 밖의 429(속도 제한 · `slow_down`) | 다시 묻는다 |
| 400 등 그 밖의 4xx | 그 묶음만 판별 실패. 다시 묻지 않는다 |
| 5xx(`503 server_is_overloaded` 포함) · 연결 오류 · 타임아웃 | 다시 묻는다 |

- **400을 그 묶음만의 실패로 두는 이유.** 400은 한 묶음의 입력 탓일 수 있다. 같은 답으로 보고 모두 멈추면, 그 묶음 하나 때문에 날마다 판별 전체가 미뤄진다. 설정 탓의 400이면(모델이 `reasoning.effort: none`을 받지 않는 경우 등) 모든 묶음이 같은 400으로 실패해 판별 미룸이 된다([[CCR-UC-001#UC-S5]] 2c).
- **거절 · 잘림을 다시 묻지 않는 이유.** 같은 입력이면 같은 답이 올 가능성이 높다. [[CCR-INFRA-001]] 8.5도 다시 묻는 경우에 넣지 않았다.

### 2.3 저장소(페이지)

읽기는 다시 보내도 결과가 같다. 쓰기는 GitHub가 `sha`로 판을 견주므로 같은 요청을 두 번 보내도 둘째는 409로 거절될 뿐 두 번 들어가지 않는다. 그래서 응답 없이 끊긴 쓰기는 「다시 시도」로 최신 판을 다시 읽고 같은 바꿈을 다시 보내면 된다. 이미 들어갔으면 다시 읽은 판에 그 값이 있어 같은 값을 다시 쓰는 것이 된다. 페이지는 스스로 되풀이하지 않고, 판이 어긋난 경우 한 번만 다시 쓴다([[CCR-INFRA-001]] 8.5).

| 요청 | 응답 | 처리 |
|---|---|---|
| raw 읽기 | 200 | 표시한다 |
| raw 읽기 | 404 | 목록 파일이면 빈 목록(첫 실행 전, [[CCR-UI-001#UI-1]] 10). 상태 파일이면 빈 객체로 본다 |
| raw 읽기 | 5xx · 연결 오류 · 타임아웃 | 한 번 다시 받는다. 그래도 실패하면 읽지 못했다고 알린다([[CCR-UC-001#UC-A2]] 1b) |
| 표시용 판 읽기(토큰이 있을 때) | 200 | 내용을 표시한다 |
| 표시용 판 읽기(토큰이 있을 때) | 404 | 상태 파일이 아직 없다. 빈 객체로 본다 |
| 표시용 판 읽기(토큰이 있을 때) | 401 · 403 · 5xx · 연결 오류 · 타임아웃 | 다시 보내지 않고 상태 파일을 raw로 읽는다. 토큰 문제는 저장할 때 드러난다 |
| 판 읽기 | 200 | `sha`와 내용을 쓰기의 기준으로 삼는다 |
| 판 읽기 | 404 | 상태 파일이 아직 없다. `sha` 없이 새 파일로 쓴다 |
| 판 읽기 · 쓰기 | 401 · 403 | 토큰이 없거나 틀리거나 권한이 모자란다. 값을 되돌리고 토큰을 다시 넣으라고 알린다([[CCR-UC-001#UC-H1]] 4b2 · [[CCR-UI-001#UI-1]] 12). 403에 `x-ratelimit-remaining: 0`이 있으면 한도다. 같은 알림에 그 사실을 적는다 |
| 쓰기 | 404 | 토큰이 이 저장소에 쓸 수 없다. 공개 저장소라 판 읽기는 되는 토큰이다. 401 · 403과 같이 값을 되돌리고 알린다([[CCR-UC-001#UC-H2]] 4b) |
| 쓰기 | 200 · 201 | 성공. 응답의 `content.sha`는 기억하지 않는다. 다음 쓰기도 판 읽기부터 한다 |
| 쓰기 | 409 | 판이 어긋났다. 최신 판을 다시 읽고 이번 바꿈만 얹어 한 번 더 쓴다. 다시 409면 값을 되돌리고 알린다([[CCR-UC-001#UC-H1]] 4a) |
| 쓰기 | 422 | `sha`가 맞지 않으면 409와 같다. 본문이 잘못됐다는 뜻이면(빈 내용 · Base64 아님) 값을 되돌리고 알린다. 페이지 코드의 문제다 |
| 쓰기 | 5xx · 연결 오류 · 타임아웃 | 커밋이 들어갔을 수 있다. 스스로 다시 보내지 않고 값을 되돌리고 알린다. 사용자가 「다시 시도」를 누르면 최신 판을 읽어 같은 바꿈을 다시 보낸다 |

토큰 검증([[CCR-UC-001#UC-H2]] 4)은 판 읽기와 같은 요청이다. 200이나 404(상태 파일이 아직 없음)면 저장하고, 401 · 403이면 저장하지 않고 이유를 보인다. 이 저장소는 공개이고 fine-grained 토큰은 늘 모든 공개 저장소를 읽을 수 있으므로, 404는 파일이 없다는 뜻뿐이고 이 요청으로는 쓰기 권한을 가르지 못한다. 쓰기 권한이 모자란 토큰은 첫 쓰기가 거절되어(403 · 404) 드러난다([[CCR-UC-001#UC-H2]] 4b).

## 3. 엔드포인트

### 3.1 대회 소스 — 수집 경계

#### POST/api.event-us.kr/api/v1/engine/search event-us 공고 검색

행사유형이 대회/공모전인 공고 가운데 접수 중인 것과, 접수마감일을 모르지만 행사가 끝나지 않은 것을 받는다.

유스케이스 [[CCR-UC-001#UC-S1]] · [[CCR-UC-001#UC-S2]] · 개념 [[CCR-DOM-001#Source]] · [[CCR-DOM-001#Competition]] · 경계 수집

**조회 조건.** 분야(`category`)는 걸지 않는다([[CCR-PRD-001#R1]]). 고정으로 거는 조건은 넷이다. 뒤의 셋은 사이트의 검색 화면이 늘 거는 조건과 같다(2026-09-16에 받은 사이트 스크립트).
- 행사유형 `대회/공모전`
- 상태 `Start`. `Temp`는 공개 전 임시 글이라 사이트 검색에도 나오지 않는다. 2026-09-23에 접수 중인 44건 가운데 4건이 `Temp`였다. 목록 클릭 수(`click_count`)가 모두 0이었고, 제목이 "wwww"인 시험 글도 있었다. 실제 대회 공고로 보이는 것도 하나 있었지만(`국민안전 LBS 솔루션 대상`) 사이트 검색을 따라 받지 않는다
- 공개 `open`
- 숨김 아님(`is_ignore`가 `false`)

여기에 날짜 조건을 함께 건다. 접수마감일이 기준일 이후인 것과, 접수마감일이 없으면서 행사 종료일(`close_date`)이 기준일 이후이거나 비어 있는 것이다.
- **날짜 조건을 두는 이유.** 이 조건이 없으면 지난 대회까지 2,168건, 22쪽이 나와 쪽 상한을 넘는다.
- **상위 문서와의 관계.** [[CCR-PRD-001#R1]]은 분야로 좁히지 말고 전부 가져와 뒤에서 거르라고 한다. 날짜 조건은 뒤의 마감 판정([[CCR-UC-001#UC-S3]])이 버릴 공고를 미리 빼는 것이라 결과가 같다. 다른 것은 접수마감일이 없는데 행사까지 끝난 공고뿐이다. [[CCR-PRD-001#R3]]은 마감일을 모르는 대회를 남기라고 하지만, 이런 공고는 지금 열려 있는 대회가 아니다. 2026-09-23에는 15건이었고 가장 늦은 행사 종료일이 2026-08-31이었다. 마감일도 행사 종료일도 없는 공고는 그대로 받는다. 상위 문서도 이에 맞췄다([[CCR-PRD-001#R3]]).
- `close_date`는 이 걸러 내기에만 쓴다. 접수마감일로 쓰지 않는다([[CCR-PRD-001#R2]]).
- 필터의 중첩은 5단까지다. 넘으면 400이 온다.

**실측(2026-09-23).** 40건, 1쪽이었다. 인증은 필요 없고, `Content-Type`과 User-Agent만 보내도 200이었다.

**공통 형식으로 옮기기.** 값은 모두 `{"raw": …}` 안에 있다.

| 대회 속성 | 필드 |
|---|---|
| 원천 ID | `id` |
| 대회명 | `title` |
| 상세 링크 | `subdomain`과 `id`로 만든다(1.2) |
| 접수시작일 | `register_start_date`. UTC 시각이라 KST로 바꾼다 |
| 접수마감일 | `register_due_date`. UTC 시각이라 KST로 바꾼다. 없으면 비운다 |
| 부가 정보 | `category` · `category2` · `tags` |

```yaml
/api/v1/engine/search:
  post:
    servers: [{url: "https://api.event-us.kr"}]
    requestBody:
      content:
        application/json:
          example:
            query: ""
            page: {current: 1, size: 100}
            filters:
              all:
                - {event_type: ["대회/공모전"]}
                - {state: "Start"}
                - {disclosure_status: "open"}
                - {is_ignore: "false"}
              any:
                - {register_due_date: {from: "2026-09-22T15:00:00+00:00"}}   # 기준일 00:00 KST
                - all:
                    - {none: {register_due_date: {from: "1900-01-01T00:00:00+00:00"}}}   # 접수마감일이 없다
                    - any:
                        - {close_date: {from: "2026-09-22T15:00:00+00:00"}}
                        - {none: {close_date: {from: "1900-01-01T00:00:00+00:00"}}}
            sort: [{register_due_date: asc}]
    responses:
      "200":
        content:
          application/json:
            schema:
              type: object
              properties:
                meta:
                  type: object
                  properties:
                    page: {type: object, properties: {current: {type: integer}, total_pages: {type: integer}, total_results: {type: integer}, size: {type: integer}}}
                results:
                  type: array
                  items:
                    type: object
                    properties:
                      id: {type: object, properties: {raw: {type: string, example: "135608"}}}
                      title: {type: object, properties: {raw: {type: string, example: "2026 울진군 창업아이디어톤 참여자 모집"}}}
                      subdomain: {type: object, properties: {raw: {type: string, example: "intween"}}}
                      register_start_date: {type: object, properties: {raw: {type: string, nullable: true, example: "2026-09-16T15:00:00+00:00"}}}
                      register_due_date: {type: object, properties: {raw: {type: string, nullable: true, example: "2026-09-23T07:00:00+00:00"}}}
                      close_date: {type: object, properties: {raw: {type: string, nullable: true, example: "2026-09-29T15:00:00+00:00"}}}
                      category: {type: object, properties: {raw: {type: string, example: "창업"}}}
                      category2: {type: object, properties: {raw: {type: string, nullable: true, example: "창업 지원"}}}
                      tags: {type: object, properties: {raw: {type: array, items: {type: string}}}}
      "400":
        description: '요청이 틀렸다. 본문 {"errors": ["Filters cannot have more than 5 levels of nesting"]}'
```

#### GET/app.dacon.io/api/v1/competition/list DACON 대회 목록

DACON의 대회 목록을 15건씩 받는다. 사이트의 대회 목록 스크립트가 부르는 JSON API다.

유스케이스 [[CCR-UC-001#UC-S1]] · [[CCR-UC-001#UC-S2]] · 개념 [[CCR-DOM-001#Source]] · [[CCR-DOM-001#Competition]] · 경계 수집

**조회 조건.** `offset`은 0부터 세는 쪽 번호다. `range`는 사이트 스크립트의 기본값인 빈 값으로 보낸다. 2026-09-23에 `ongoing` · `open`을 넣으면 오류가 왔고, `1`을 넣으면 한 건만 왔다.
- 목록은 종료일이 늦은 차례로 나온다. 2026-09-23에 0쪽은 그 차례 그대로였고, 세 쪽 45건 가운데 이웃한 두 대회의 차례가 바뀐 곳이 세 군데 있었다.
- 접수 중인 대회(`period_end`가 기준일 이후)가 하나도 없는 쪽을 읽으면 멈춘다.

**쓰지 않는 길.**
- 대회 목록 페이지의 서버 렌더링 페이로드(약 770KB)에도 같은 값이 있다. 하지만 JS 함수와 변수 치환으로 되어 있어 JSON으로 바로 읽히지 않는다.
- `newapi.dacon.io`의 대회 목록은 옛 대회까지 한 번에 약 21MB로 준다. 해커톤 목록(`/competition/list/hackathon`)은 교육용 캠프 목록이다.

**실측(2026-09-23).** 한 쪽은 약 10KB였다. 접수 중인 3건이 모두 0쪽에 있었고, 1 · 2쪽은 모두 끝난 대회였다.

**공통 형식으로 옮기기.**

| 대회 속성 | 필드 |
|---|---|
| 원천 ID | `cpt_id` |
| 대회명 | `name` |
| 상세 링크 | `cpt_id`와 `is_landing_cpt`로 만든다(1.2) |
| 접수시작일 | `period_start`. 시간대 표기가 없어 KST로 본다 |
| 접수마감일 | `period_end`. 목록이 주는 날짜는 대회 기간뿐이라 이것을 접수 기간으로 쓴다 |
| 부가 정보 | `keyword`를 `\|`로 나눠 앞뒤 공백을 떼고, 빈 낱말은 버린다 |

```yaml
/api/v1/competition/list:
  get:
    servers: [{url: "https://app.dacon.io"}]
    parameters:
      - {name: offset, in: query, required: true, schema: {type: integer, minimum: 0}, description: "쪽 번호. 한 쪽 15건"}
      - {name: range, in: query, required: true, schema: {type: string, enum: [""]}}
    responses:
      "200":
        content:
          application/json:
            schema:
              type: object
              properties:
                message: {type: string, example: "ok"}
                data:
                  type: array
                  items:
                    type: object
                    properties:
                      cpt_id: {type: integer, example: 236749}
                      name: {type: string, example: "딥보이스 범죄 대응을 위한 AI 탐지 모델 경진대회"}
                      keyword: {type: string, example: "알고리즘 | 코드 제출 평가 | 오디오 | 딥보이스"}
                      period_start: {type: string, example: "2026-08-26 10:00:00"}
                      period_end: {type: string, example: "2026-09-30 10:00:00"}
                      is_landing_cpt: {type: integer, enum: [0, 1]}
```

#### POST/api.kaggle.com/v1/…/ListCompetitions Kaggle 대회 목록

Kaggle 공식 API로 대회 목록을 받는다. 공식 클라이언트(`kagglesdk`)가 쓰는 엔드포인트다.

유스케이스 [[CCR-UC-001#UC-S1]] · [[CCR-UC-001#UC-S2]] · [[CCR-UC-001#UC-S3]] · 개념 [[CCR-DOM-001#Source]] · [[CCR-DOM-001#Competition]] · 경계 수집

**인증.** 새 API 토큰을 `Authorization: Bearer <KAGGLE_API_TOKEN>`으로 보낸다([[CCR-INFRA-001]] 5.2). 토큰이 없거나 틀리면 401이다.

**조회 조건.** 목록 탭은 일반, 분야는 전체, 정렬은 마감이 늦은 차례다. 열거값은 이름 문자열로 보낸다. 상태로 거르는 파라미터는 없다. 일반 탭은 `deadline`이 지나지 않은 대회만 주지만, 새 참가 마감(`newEntrantDeadline`)이 지난 대회는 섞여 오므로 배치가 거른다.
- **쪽 넘김.** 한 쪽은 20건으로 정해져 있다. `pageSize`는 10을 보내도 100을 보내도 20건이 왔다. `nextPageToken`은 마지막 쪽이 아니어도 오지 않는다. 그래서 쪽은 `page`(1부터)로 넘긴다. `page`를 빼면 1쪽이고, 마지막 쪽 다음은 빈 객체 `{}`가 온다. 빈 쪽을 받으면 멈춘다. 마감이 늦은 차례라, 한 쪽의 대회가 모두 마감됐으면(`deadline`이 기준일보다 이르면) 뒤쪽도 마감된 것이라 거기서도 멈춘다.
- **연습용 대회.** 분야는 하나만 걸 수 있어 연습용만 요청에서 뺄 수 없다. `category`의 실제 값은 `Getting Started` · `Featured` · `Playground` · `Research`였다(일반 탭, 2026-10-01). `Getting Started` · `Playground`면 연습용으로 보고 마감 판정에서 버린다([[CCR-UC-001#UC-S3]] 2b). `Getting Started`는 마감이 모두 2030년으로 잡혀 있었다. 공백을 빼고 소문자로 바꿔 `gettingstarted` · `playground`와 견주므로 [[CCR-RFQ-001#Q4]]의 표기 `gettingStarted`도 맞는다.
- **커뮤니티 대회는 받지 않는다.** 일반 탭에는 커뮤니티 탭(`COMPETITION_LIST_TAB_COMMUNITY`)의 대회가 없다. 커뮤니티 탭은 2026-10-01에 15쪽 300건을 받아도 끝나지 않았고, 300건 모두 분류가 `Community`, 상금이 `Kudos`(상금 없음)였다. 앞쪽은 마감이 2100년 같은 먼 미래로 잡힌 상시 대회가 채우고, 2030년보다 이른 마감은 89건이었으며 대개 수업 과제였다. 받으면 연습용처럼 걸러야 할 것이 수백 건이고 쪽 상한(20)에도 닿는다.

**실측(2026-10-01).** 사용자의 새 토큰으로 일반 탭을 불러 200을 받았다. 21건, 2쪽(20건 · 1건)이었고 3쪽은 빈 객체였다. 필드 이름은 공식 클라이언트 코드와 같았다.
- `ref`와 `url`은 같은 전체 주소(`https://www.kaggle.com/competitions/{slug}`)다.
- 날짜는 UTC의 `YYYY-MM-DDTHH:MM:SSZ`다. 밀리초가 붙은 값(`2026-11-12T23:59:00.807Z`)도 섞여 온다. `enabledDate`는 대개 밀리초가 붙는다.
- `newEntrantDeadline`은 21건 가운데 8건에만 있었다.
- 연습용 13건(`Getting Started` 11 · `Playground` 2)과 새 참가 마감이 지난 1건을 빼면 남는 것은 7건이었다.
- 응답에는 토큰 주인이 참가했는지를 뜻하는 `userHasEntered`도 온다. 테스트에 저장한 응답에서는 지웠다.
- `api.kaggle.com/robots.txt`는 404라 제한이 없다.

**공통 형식으로 옮기기.**

| 대회 속성 | 필드 |
|---|---|
| 원천 ID | `ref`의 마지막 조각(slug). 끝의 `/`는 뗀다. `ref`가 주소 모양이든 slug 모양이든 마지막 조각은 같다 |
| 대회명 | `title`. 영문 원문 그대로다([[CCR-PRD-001#R2]]) |
| 상세 링크 | slug로 만든다(1.2) |
| 접수시작일 | `enabledDate`. UTC 시각이라 KST로 바꾼다 |
| 접수마감일 | `newEntrantDeadline`. 새로 참가할 수 있는 마지막 때라 접수 기준에 맞는다([[CCR-PRD-001#R2]]). 없으면 `deadline`을 쓴다. 둘 다 UTC라 KST로 바꾼다 |
| 부가 정보 | `category` · `tags`의 `name` |

```yaml
/v1/competitions.CompetitionApiService/ListCompetitions:
  post:
    servers: [{url: "https://api.kaggle.com"}]
    security: [{bearer: []}]
    requestBody:
      content:
        application/json:
          example:
            group: "COMPETITION_LIST_TAB_GENERAL"
            category: "HOST_SEGMENT_UNSPECIFIED"
            sortBy: "COMPETITION_SORT_BY_LATEST_DEADLINE"
            search: ""
            page: 1              # 다음 쪽은 2, 3, …. pageSize · pageToken은 효과가 없다
    responses:
      "200":
        content:
          application/json:
            schema:
              type: object
              properties:
                competitions:
                  type: array
                  items:
                    type: object
                    properties:
                      ref: {type: string, example: "https://www.kaggle.com/competitions/rsna-knee-abnormality-detection"}
                      title: {type: string}
                      category: {type: string, example: "Featured"}
                      enabledDate: {type: string, format: date-time}
                      newEntrantDeadline: {type: string, format: date-time}
                      deadline: {type: string, format: date-time}
                      tags: {type: array, items: {type: object, properties: {name: {type: string}}}}
              # 마지막 쪽 다음은 빈 객체 {}다. nextPageToken은 오지 않는다
      "401":
        description: '토큰이 없거나 틀렸다. 익명 세션 쿠키가 함께 실려도 401이다. 본문 {"error": {"code": 401, "message": "Unauthenticated"}}'
```

#### GET/www.wevity.com/?c=find wevity 공모전 목록

wevity에서 IT에 가까운 네 분야와 기획/아이디어 분야의 공모전 목록을 받는다. HTML 페이지를 읽는다.

유스케이스 [[CCR-UC-001#UC-S1]] · [[CCR-UC-001#UC-S2]] · 개념 [[CCR-DOM-001#Source]] · [[CCR-DOM-001#Competition]] · 경계 수집

**조회 조건.** 아래 다섯 분야를 받는다. 네 분야는 2026-09-23에, 기획/아이디어는 2026-09-27에 사용자가 정했다. 분야(`cidx`)마다 따로 받고, `ix`가 같은 공고는 하나로 합친다. 한 공고가 여러 분야에 걸리기 때문이다.

| 분야 | `cidx` | 2026-09-23 접수 중 |
|---|---|---|
| 웹/모바일/IT | 20 | 21건 |
| 게임/소프트웨어 | 21 | 10건 |
| 과학/공학 | 22 | 14건 |
| 논문/리포트 | 3 | 30건 |
| 기획/아이디어 | 1 | 76건 |

- **분야를 고르는 이유.** 분야 없이 받으면 접수 중인 공모전이 약 825건, 55쪽이라 쪽 상한과 시간 예산을 넘는다. [[CCR-RFQ-001#Q2]]는 분야로 좁히지 않는다고 했으므로 이것은 그 원칙의 예외다.
- **기획/아이디어를 넣은 이유.** 2026-09-23에 이 분야의 접수 중 76건 가운데, 제목에 AI · 데이터 · 디지털 같은 말이 든 7건에서 6건이 네 분야 어디에도 걸리지 않았고 event-us에도 없었다. `2026 AI 활용 아이디어 공모전`, `2026년 충청남도 데이터 분석 아이디어 공모전` 같은 것이다. 관심 밖의 기획 공모전이 함께 들어오지만 판별이 거른다([[CCR-PRD-001#R4]]).
- **그래도 놓치는 것.** 다섯 분야 밖에만 걸린 공고다. 대개 영상 · 디자인 · 문학 공모전이라 판별에서도 버릴 것들이다.
- **실측(2026-09-27).** 다섯 분야를 합쳐 11쪽이었고, `ix`로 합친 접수 중 공고는 139건이었다. 기획/아이디어가 74건, 5쪽이다.
- **멈추는 때.** 목록 위쪽에는 홍보 칸이 있고, 그 아래 일반 목록은 접수 중인 것 뒤에 마감된 것이 이어진다. 마지막 항목의 상태가 `마감`이거나 항목이 없는 쪽까지 읽고 멈춘다. 웹/모바일/IT는 2026-09-23에 2쪽에서 접수 중 6건과 마감 9건이 함께 있었다. 쪽 상한 20은 다섯 분야를 합친 것이다.
- **`마감`이 하나라도 보이면 멈추지 않는 이유.** 홍보 칸에는 마감된 공고가 남기도 한다. 2026-09-28 09:03에는 전날 마감된 공고 하나(`마감 D+0`)가 웹/모바일/IT · 게임/소프트웨어 · 과학/공학 · 논문/리포트의 첫 쪽 위쪽에 있었다. 마감 항목이 하나라도 보이면 멈추던 처음 규칙으로는 웹/모바일/IT와 논문/리포트의 2쪽에 남은 접수 중 공고 22건을 놓쳤다. 홍보 칸은 첫 쪽 위쪽에만 있어 쪽의 끝으로 가르면 걸리지 않는다. 모두 마감인 쪽까지 읽는 방법은 분야마다 한 쪽씩 늘어(그날 11쪽 → 16쪽) 쪽 상한에 가까워지므로 쓰지 않는다.

**페이지에서 읽을 곳.** 본문 목록 `ul.list`의 `li`만 읽는다. 첫 `li.top`은 머리글이다. 목록 위의 슬라이드와 광고 배너에도 `ix=` 링크가 있으니 읽지 않는다. 항목마다 읽는 곳은 아래와 같다.
- `div.tit > a`: 링크의 `ix`와 제목. 제목에서 `span.stat` 배지(`SPECIAL` · `IDEA` 등)는 뺀다
- `div.sub-tit`: "분야 : …"
- `div.organ`: 주최
- `div.day`: 날수("D-14" · "D+419")와 `span.dday`의 상태(접수중 · 마감임박 · 접수예정 · 마감)

**날짜.** 목록에는 마감까지의 날수만 있고 접수시작일은 없다. 이 날수는 같은 날에도 하루 바뀐다. 2026-09-23에 웹/모바일/IT 첫 쪽의 15건은 10:06에 받았을 때 모두 17:17보다 하루 많았다(`D-15` → `D-14`). 상세 페이지의 접수 기간과 맞은 것은 저녁 값이다. 배치가 도는 아침에는 날수가 하루 많게 나온다는 뜻이다. 그래서 실행마다 한 번 맞춰 본다([[#GET/www.wevity.com/?c=find&gbn=view]]).
- **보정값**은 상세 페이지 하나로 잰 날수의 차이다. 0이나 −1이다.
- "D-N"(접수중 · 마감임박 · 접수예정): 접수마감일은 기준일 + N + 보정값이다. 접수예정도 N은 마감까지의 날수다. 17:17의 "D-63 접수예정"은 접수 기간이 09-24~11-25인 공고였다.
- 마감 당일은 "D-0"(마감임박)으로 적힌다(2026-09-27 저녁). N이 0인 "D-N"이다.
- "D+N"(마감): 접수마감일은 기준일 − N + 보정값이다. 마감 판정이 버린다([[CCR-UC-001#UC-S3]] 2).
- 둘 다 아니면 접수마감일을 비운다.

**공통 형식으로 옮기기.**

| 대회 속성 | 값 |
|---|---|
| 원천 ID | `ix` |
| 대회명 | 제목(배지 제외) |
| 상세 링크 | `ix`로 만든다(1.2) |
| 접수시작일 | 없음 |
| 접수마감일 | 기준일 + N + 보정값. 마감됐으면 기준일 − N + 보정값 |
| 부가 정보 | 분야 목록 · 주최 |

```yaml
/:
  get:
    servers: [{url: "https://www.wevity.com"}]
    parameters:
      - {name: c, in: query, schema: {type: string, enum: [find]}}
      - {name: s, in: query, schema: {type: string, enum: ["1"]}}
      - {name: gub, in: query, schema: {type: string, enum: ["1"]}}
      - {name: cidx, in: query, schema: {type: integer, enum: [20, 21, 22, 3, 1]}}
      - {name: gp, in: query, schema: {type: integer, minimum: 1}, description: "쪽 번호. 한 쪽 15건"}
    responses:
      "200":
        description: "HTML(UTF-8). ul.list > li 가 공고 하나다"
        content:
          text/html:
            example: |
              <li class='bg'>
                <div class="tit">
                  <a href="?c=find&s=1&gub=1&cidx=20&gbn=view&gp=1&ix=110675">[과학기술정보통신부] 제3회 미래융합인재 발굴 소프트웨어 챌린지 <span class='stat spec'>SPECIAL</span> <span class='stat idea'>IDEA</span></a>
                  <div class="sub-tit">분야 : 기획/아이디어, 웹/모바일/IT, 게임/소프트웨어, 과학/공학, 기타</div>
                </div>
                <div class="organ">과학기술정보통신부</div>
                <div class="day"> D-14 <span class="dday ing">접수중</span> </div>
              </li>
```

#### GET/www.wevity.com/?c=find&gbn=view wevity 공모전 상세 — 날수 맞춰 보기

공고 하나의 상세 페이지에서 접수 기간을 읽어, 목록의 날수가 오늘 하루 어긋났는지 잰다.

유스케이스 [[CCR-UC-001#UC-S1]] · [[CCR-UC-001#UC-S2]] · 개념 [[CCR-DOM-001#Competition]] · 경계 수집

**언제.** 실행마다 한 번, 다섯 분야의 목록을 다 읽은 뒤 부른다. 처음 나온, 상태가 접수중이나 마감임박인 공고를 고른다.

**리디렉션.** 이 주소는 같은 사이트의 `gbn=viewok`로 302를 보낸다(2026-09-27). 이 요청만은 목록과 달리 리디렉션을 따라간다(1.2). robots.txt에서도 `gbn=view` · `gbn=viewok` 두 경로를 확인한다.

**읽을 곳.** `접수기간` 칸의 "YYYY-MM-DD ~ YYYY-MM-DD"에서 뒤 날짜를 읽는다. 보정값은 (뒤 날짜 − 기준일) − N이다. N은 그 공고의 목록 날수다.

**실패하면.** 상세 페이지를 받지 못하거나, 날짜를 읽지 못하거나, 보정값이 0 · −1이 아니면 보정값을 −1로 두고 로그에 남긴다. 10:06의 관찰로는 배치가 도는 아침에 −1이 맞다. 틀리더라도 접수마감일이 하루 이르게 잡힐 뿐 늦게 잡히지 않는다. 늦게 잡히면 참가자가 페이지를 믿다가 마감을 놓친다. 이 실패로 소스를 실패로 두지는 않는다.

**실측.** 2026-09-23 18:47에 `ix=110675`의 접수기간은 `2026-09-01 ~ 2026-10-07`이었고, 목록과 상세 모두 `D-14`였다. 2026-09-27 20:46의 목록에서는 같은 공고가 `D-10`이었다. 저녁에는 두 번 모두 보정값이 0이다. 2026-09-28 09:02에는 `ix=110678`이 목록에서 `D-1`, 상세의 접수마감일이 2026-09-28(기준일)이라 보정값이 −1이었다. 아침에는 날수가 하루 많다는 2026-09-23 10:06의 관찰과 같다.

```yaml
/:
  get:
    servers: [{url: "https://www.wevity.com"}]
    parameters:
      - {name: c, in: query, schema: {type: string, enum: [find]}}
      - {name: s, in: query, schema: {type: string, enum: ["1"]}}
      - {name: gbn, in: query, schema: {type: string, enum: [view]}}
      - {name: ix, in: query, schema: {type: integer}, example: 110675}
    responses:
      "200":
        description: "HTML(UTF-8). 접수기간 칸에 날짜 둘과 날수가 있다. 아래는 그 칸의 태그를 걷어 낸 글자다"
        content:
          text/html:
            example: |
              접수기간  2026-09-01 ~ 2026-10-07  D-14
```

#### GET/aifactory.space/ko/competition AI팩토리 경진대회 목록

AI팩토리의 경진대회 과제 목록을 받아 같은 대회의 과제를 대회 하나로 합친다.

유스케이스 [[CCR-UC-001#UC-S1]] · [[CCR-UC-001#UC-S2]] · 개념 [[CCR-DOM-001#Source]] · [[CCR-DOM-001#Competition]] · 경계 수집

**페이지에서 읽을 곳.** Next.js가 그린 페이지다(약 630KB). 보이는 마크업에는 과제 기간과 상태만 있고, 접수 기간은 스크립트 안의 페이로드에만 있다. 그래서 페이로드를 읽는다.
- 값은 `<script>self.__next_f.push([1,"…"])</script>` 조각들에 JSON 문자열로 들어 있다. 조각의 문자열을 차례로 이어 붙인 뒤 줄마다 `키:값`으로 읽는다.
- 과제는 `id` · `name` · `page` · `startDate` · `endDate`를 가진 객체다. 2026-09-23에는 112건이었다. `id`는 문자열로 오므로 정수로 바꿔 견준다.
- `page`는 소속 페이지다. `{"name": …}`이거나, 그런 객체가 있는 다른 줄을 가리키는 `"$키"`다. 페이지에는 이름만 있고 식별자는 없다.
- 날짜는 UTC 시각이다. 옛 과제에는 `participationStartDate` · `participationDeadline`이 없는 것이 많다(112건 가운데 85건 · 59건). 2024년 이후 시작한 25건은 모두 있다.
- `1970-01-01T00:00:00.000Z`는 값이 없는 것으로 보고 `endDate`를 쓴다. 옛 과제 3건의 `participationDeadline`이 이 값이었다.

**실측(2026-09-23).** 접수 중인 과제는 2건이었다. 둘 다 `2026 국립공원 위성 모니터링 AI 챌린지`의 주제 3 · 4다.

**같은 대회로 합치기**([[CCR-PRD-001#R2]] · [[CCR-UC-001#UC-S2]] 1d).
- **합치는 기준:** 페이지 이름이 같고 접수시작일(KST)이 같은 과제는 한 대회다. 접수시작일이 없는 과제는 `startDate`로 대신한다.
- **이 기준인 이유:** 페이지 이름은 대개 주최 기관이나 시리즈의 이름이다. 페이지 48개 가운데 연도가 든 이름은 `2026 국립공원 위성 모니터링 AI 챌린지` 하나였고, 나머지는 `과학기술정보통신부` · `마이크로소프트` · `ETRI 네트워크 해커톤` 같은 이름이었다. 한 페이지에 해가 다른 대회가 함께 걸려 있어 이름만으로 합치면 다른 대회가 섞인다. 과제가 여럿인 최근 대회들은 모두 과제의 접수를 같은 날 열었다.
- **실측 예:** 국립공원 과제 4건은 모두 07-31에 접수를 열어 한 대회가 된다. `마이크로소프트` 페이지의 2024년 12월 대회와 2025년 3월 대회는 따로 남는다. `Norma` 페이지의 `제1회 퀀텀AI 경진대회`와 `The 2nd Global Quantum AI Competition - 2026`도 따로 남는다.

**대회명**은 아래 차례로 정한다. 앞에서 정해지면 뒤는 보지 않는다.
1. 페이지 이름에 연도(`20`으로 시작하는 네 자리)가 있고 그 연도가 대회 접수시작일의 연도나 그다음 해면 페이지 이름. 대회 전용 페이지로 본다. 국립공원이 여기 든다. 과제명이 "주제 1: …"이라 과제명으로는 대회 이름을 얻지 못한다. 연도를 견주는 것은 같은 페이지에 다음 해 대회가 걸려도 옛 이름을 붙이지 않기 위해서다.
2. 과제가 하나면 과제명.
3. 과제명들의 공통 앞부분을 정리한 뒤의 길이가 10자 이상이면 그것. 정리는 앞뒤 공백과 끝에 남은 구분 기호(`_` · `-` · `:`)를 떼고, 짝이 맞지 않는 여는 괄호는 그 괄호부터 끝까지 떼는 것이다. 머리의 꼬리표(`[Track 1]` · `(문제1)`)가 과제마다 달라 공통 앞부분이 짧으면, 꼬리표를 뗀 과제명으로 다시 본다. `과학기술정보통신부` 페이지의 두 과제는 `2026 AI Co-Scientist Challenge Korea (AI 연구동료 경진대회)`가 된다.
4. 그래도 정해지지 않으면 가장 작은 id 과제의 과제명. `ETRI 네트워크 해커톤` 페이지의 2025년 과제 셋은 `2025 네트워크 AI 해커톤 참가자 접수`가 된다. 다만 그 과제명이 `주제 1:` · `(문제1)` · `[분야1]`처럼 주제 번호로 시작하면 주제 하나의 이름이라 페이지 이름을 쓴다.

**한계.** 이 차례가 주는 것은 대회 이름에 가깝지만 늘 대회 이름은 아니다. 2와 4는 과제명을, 4의 예외는 기관 이름일 수 있는 페이지 이름을 준다([[CCR-PRD-001#R2]] · [[CCR-UC-001#UC-S2]] 1d1). 과제가 목록에서 빠지거나 더해지면 대회명이 바뀔 수 있다. 가장 작은 id의 과제가 빠지면 원천 ID와 대회명이 함께 바뀌어, 예전 기록과 이름으로도 이어지지 않을 수 있다([[CCR-PRD-001]] 5.1). 목록은 2017년 과제까지 남기고 있어 드문 일로 본다. 한 기관이 같은 날 접수를 여는 서로 다른 대회가 한 대회로 합쳐지는 것도 한계다.

**원천 ID와 상세 링크.** 원천 ID는 합친 과제 id 가운데 가장 작은 값이고([[CCR-PRD-001]] 5.1), 상세 링크는 그 과제의 주소다.
- 처음 상위 문서는 대회 하나만 보여 주는 페이지가 있으면 그 주소를 쓰라고 했다. 그런 페이지는 있다. 과제 상세에 소속 페이지 링크가 있고, 국립공원이면 `/ko/page/knps`다.
- 그래도 늘 과제의 주소를 쓴다. 이유는 둘이다.
  - 페이지 주소는 목록에 없다. 얻으려면 과제 상세를 대회마다 한 번 더 받아야 한다.
  - 지금은 대회 하나만 걸린 페이지라도, 다음 해 대회가 같은 페이지에 걸리면 여러 대회가 걸린 페이지가 된다. 그때 이미 들어간 목록 항목의 링크는 고칠 수 없다([[CCR-PRD-001#R6]]). 과제의 주소는 다른 대회와 겹치지 않는다.
- 원천 ID 과제가 다른 과제보다 먼저 끝나면 링크가 끝난 과제를 가리킨다. 2026-09-23의 국립공원이 그렇다. 9304는 09-11에 접수를 닫았고, 9306 · 9307이 접수 중이다. 과제 상세에서 소속 페이지로 건너갈 수 있어 받아들인다.
- 상위 문서도 이에 맞췄다([[CCR-PRD-001#R2]] · [[CCR-UC-001#UC-S2]] 1d2).

**공통 형식으로 옮기기.**

| 대회 속성 | 값 |
|---|---|
| 원천 ID | 합친 과제 `id` 가운데 가장 작은 값 |
| 대회명 | 위 차례 |
| 상세 링크 | 원천 ID 과제의 주소(1.2) |
| 접수시작일 | 과제마다 `participationStartDate`, 없으면 `startDate`. 그 가운데 가장 이른 것. UTC라 KST로 바꾼다. 접수마감일보다 뒤면 비운다 |
| 접수마감일 | 과제마다 `participationDeadline`, 없으면 `endDate`. 그 가운데 가장 늦은 것. UTC라 KST로 바꾼다 |
| 부가 정보 | 페이지 이름 · 과제명들 |

```yaml
/ko/competition:
  get:
    servers: [{url: "https://aifactory.space"}]
    responses:
      "200":
        description: "HTML(UTF-8, 약 630KB). 값은 self.__next_f.push 조각의 JSON 문자열에 있다. 아래는 조각을 이어 붙인 뒤의 두 줄이고, 쓰지 않는 필드는 뺐다"
        content:
          text/html:
            example: |
              20:{"name":"2026 국립공원 위성 모니터링 AI 챌린지"}
              1f:{"id":"9306","type":1,"endDate":"2026-10-06T05:00:00.000Z","startDate":"2026-09-14T01:00:00.000Z","name":"주제 3: 국립공원 내 시설물 변화 탐지","page":"$20","totalReward":"600만원","participationStartDate":"2026-07-31T01:00:00.000Z","participationDeadline":"2026-10-06T05:00:00.000Z"}
```

#### GET/www.contestkorea.com/sub/list.php 콘테스트코리아 공모전 목록

콘테스트코리아에서 학문·과학·IT와 아이디어·건축·창업, 두 분야의 접수 중인 공모전을 받는다. HTML 페이지를 읽는다.

유스케이스 [[CCR-UC-001#UC-S1]] · [[CCR-UC-001#UC-S2]] · 개념 [[CCR-DOM-001#Source]] · [[CCR-DOM-001#Competition]] · 경계 수집

**조회 조건.** 분야 코드 `030310001`(학문·과학·IT)과 `031410001`(아이디어·건축·창업)마다 "접수중" 정렬(`Txt_sortkey=a.str_aedate`, `Txt_sortword=asc`)을 걸어 따로 받고, `str_no`가 같은 공고는 하나로 합친다. 분야를 고르는 것은 wevity와 같은 이유의 예외다. 학문·과학·IT는 2026-09-23에, 아이디어·건축·창업은 2026-09-27에 사용자가 정했다.
- 이 정렬은 접수 중인 공모전만 마감이 가까운 차례로 보여 준다. 접수예정인 공모전이 여기 나오는지는 확인하지 못했다. 나오지 않으면 접수가 열린 날부터 받는다.
- 기본 정렬은 등록 차례라 접수 중인 것과 끝난 것이 섞인다.
- `030510001`(IT•소프트웨어•게임)은 분야 메뉴에 없는 옛 코드이고, 본문 목록이 비어 있었다.

**실측.** 2026-09-23에 학문·과학·IT는 64건, 6쪽이었다. 분야 없이 받으면 40쪽을 넘었다. 2026-09-27에는 학문·과학·IT 61건 6쪽, 아이디어·건축·창업 80건 7쪽이었고, 합친 공고는 136건이었다.

**아이디어·건축·창업을 넣은 이유.** 2026-09-23에 전 분야의 접수 중 480건(앞 40쪽)에서 제목에 AI · 데이터 같은 말이 든 56건 가운데 41건이 학문·과학·IT 밖이었다. 대부분 AI 영상 · 숏폼 공모전이라 판별에서 버려질 것이지만, 아이디어·건축·창업에는 데이터 분석 · AI 활용 아이디어 공모전과 해커톤이 있었다. 창업 · 건축 공모전이 함께 들어오지만 판별이 거른다([[CCR-PRD-001#R4]]).

**페이지에서 읽을 곳.** 본문 목록 `div.list_style_2 > ul > li`만 읽는다. 목록 밖에도 `str_no=` 링크가 40건 넘게 있다(위쪽 슬라이드, `list_style_1` 목록, 주간 인기 탭). 읽지 않는다. 항목마다 읽는 곳은 아래와 같다.
- `div.title > a`: 링크의 `str_no`
- `span.category`: 분야. 여러 개일 수 있다
- `span.txt`: 제목. HTML 엔티티를 푼다
- `ul.host`: 주최 · 대상
- `div.date`: `span.step-1`의 "접수 MM.DD~MM.DD", `span.step-3`의 발표일. 발표일이 없는 공고도 많다
- `div.d-day`: `span.day`의 "D-N", `span.condition`의 상태(접수중 · 마감임박)

**날짜.** 목록의 날짜에는 연도가 없다.
- **접수마감일:** "접수 MM.DD~MM.DD"의 뒤 날짜다. 연도는 기준일 + N에 가장 가까운 날이 되는 해로 정한다. "D-0"이면 N은 0이다. "D-N"을 읽지 못하면 연도를 정할 수 없어 두 날짜를 모두 비운다(1.2). 날수만으로 세지 않는 것은 wevity처럼 날수가 하루 어긋날 수 있어서다. 2026-09-23(겹친 것을 뺀 503건)과 2026-09-27(136건) 실측에서는 모두 기준일 + N이 뒤 날짜와 같았다.
- **접수시작일:** 앞 날짜에 접수마감일의 연도를 붙인다. 그 날이 접수마감일보다 뒤면 한 해 전으로 본다. "05.16~01.16"에 "D-115"면 마감이 2027-01-16이고 시작은 2026-05-16이다.
- 발표일은 쓰지 않는다. 목록 항목에 `결과날`을 두지 않기로 했다([[CCR-PRD-001#R6]]). 5장에 남긴다.

**공통 형식으로 옮기기.**

| 대회 속성 | 값 |
|---|---|
| 원천 ID | `str_no` |
| 대회명 | `span.txt` |
| 상세 링크 | `str_no`로 만든다(1.2) |
| 접수시작일 | 위 규칙 |
| 접수마감일 | 위 규칙 |
| 부가 정보 | 분야들 · 주최 · 대상 |

```yaml
/sub/list.php:
  get:
    servers: [{url: "https://www.contestkorea.com"}]
    parameters:
      - {name: displayrow, in: query, schema: {type: integer, enum: [12]}}
      - {name: int_gbn, in: query, schema: {type: integer, enum: [1]}}
      - {name: Txt_bcode, in: query, schema: {type: string, enum: ["030310001", "031410001"]}}
      - {name: Txt_sortkey, in: query, schema: {type: string, enum: [a.str_aedate]}}
      - {name: Txt_sortword, in: query, schema: {type: string, enum: [asc]}}
      - {name: page, in: query, schema: {type: integer, minimum: 1}}
    responses:
      "200":
        description: "HTML(UTF-8). div.list_style_2 > ul > li 가 공고 하나다"
        content:
          text/html:
            example: |
              <li class="imminent">
                <div class="title"><a href="view.php?int_gbn=1&Txt_bcode=030310001&str_no=202609230054">
                  <span class="category">학문•과학•IT</span> <span class="txt">2027 전국 대학생 자작 미래자동차 경진대회</span></a></div>
                <ul class="host"><li class="icon_1"><strong>주최</strong> . 영남대학교</li><li class="icon_2"><strong>대상</strong> . 대학생 </li></ul>
                <div class="date"><div class="date-detail">
                  <span class="step-1"><em>접수</em> 09.23~10.28 </span><span class="step-2"><em>심사</em> 09.23~11.04 </span><span class="step-3"><em>발표</em> 11.09 </span></div></div>
                <div class="d-day orange"><span class="day">D-35</span><span class="condition">접수중</span></div>
              </li>
```

### 3.2 판별 — 선별 경계

#### POST/api.openai.com/v1/responses 관련도 판별

묶음의 대표 하나를 보내 관심 분야인지(남김 · 버림)와 한 줄 근거를 받는다.

유스케이스 [[CCR-UC-001#UC-S5]] · 개념 [[CCR-DOM-001#Bundle]] · 경계 선별

**요청.**
- `instructions`에는 판별 기준을 담는다. 기준 문구는 코드에 둔다([[CCR-PRD-001#R4]] · [[CCR-DOM-001]] 4.3).
- `input`에는 대표의 대회명 · 출처 · 부가 정보를 담는다([[CCR-UC-001#UC-S5]] 1). 출처를 넣는 것은 이 문서가 더했고, 상위 문서도 이에 맞췄다.
- 답의 모양은 엄격한 JSON 스키마로 강제한다. 스키마는 4.3이다.
- 동시에 보내는 수는 [[CCR-INFRA-001]] 8.5를 따른다.

**응답 읽기.** 답은 `output` 가운데 `type`이 `message`인 항목의 `content`에 있다. `output_text`면 답이고, `refusal`이면 거절이다.
- `output_parsed`는 SDK가 최종 메시지의 `output_text`를 응답 모델로 읽은 값이다.
- 아래 셋 가운데 하나면 판별 실패다([[CCR-UC-001#UC-S5]] 2a).
  - `responses.parse`가 검증 예외를 낸다. 답이 스키마에 맞지 않거나 잘려 JSON이 깨진 것이다.
  - 응답의 `status`가 `completed`가 아니다(`incomplete` · `failed`). SDK는 `status`를 보지 않으므로 배치가 본다.
  - `output_parsed`가 비었다. 거절이거나 최종 메시지가 없는 것이다.

**판별 결과로 옮기기.** `decision`이 `keep`이면 남김, `discard`면 버림이다. `reason`은 로그에 남기고, 남긴 대회는 목록 항목의 판별 근거로도 들어간다([[CCR-UC-001#UC-S5]] 4 · [[CCR-UC-001#UC-S6]]). 자유 문장이지만 대회명과 분류 이유뿐이라 비밀값이 섞일 자리가 없다([[CCR-INFRA-001]] 5.4).

```yaml
/v1/responses:
  post:
    servers: [{url: "https://api.openai.com"}]
    security: [{bearer: []}]                 # OPENAI_API_KEY
    requestBody:
      content:
        application/json:
          example:
            model: "<판별 모델 이름>"            # settings.toml 기본값, 저장소 변수 OPENAI_MODEL이 덮는다
            instructions: "<판별 기준>"
            input: "대회명: 2026 국립공원 위성 모니터링 AI 챌린지\n출처: AI팩토리\n부가 정보: 2026 국립공원 위성 모니터링 AI 챌린지, 주제 1: 구상나무 고사 탐지 및 분포 분석, 주제 2: 산사태 붕괴지 탐지 및 위험도 분석, 주제 3: 국립공원 내 시설물 변화 탐지, 주제 4: 해안 쓰레기 탐지 및 규모 추정"
            text:
              format:
                type: json_schema
                name: relevance
                strict: true
                schema: {$ref: "#/components/schemas/Relevance"}   # SDK가 응답 모델로 만든다. 4.3과 같다
            reasoning: {effort: none}
            max_output_tokens: 300
            store: false
    responses:
      "200":
        content:
          application/json:
            schema:
              type: object
              properties:
                status: {type: string, enum: [completed, incomplete, failed]}
                incomplete_details: {type: object, nullable: true, properties: {reason: {type: string, example: max_output_tokens}}}
                output:
                  type: array
                  items:
                    type: object
                    properties:
                      type: {type: string, example: message}
                      content:
                        type: array
                        items:
                          oneOf:
                            - {type: object, properties: {type: {enum: [output_text]}, text: {type: string}}}
                            - {type: object, properties: {type: {enum: [refusal]}, refusal: {type: string}}}
      "429":
        description: "error.code로 가른다. 지출 한도 · 크레딧 소진은 다시 묻지 않는다(2.2)"
```

### 3.3 저장소 — 목록 경계(페이지)

세 엔드포인트 모두 페이지만 부른다. 배치는 git으로 저장소를 읽고 마무리 단계가 push하므로 REST API를 부르지 않는다([[CCR-INFRA-001]] 8.2). `{owner}/{repo}`는 `HoyoungParkme/competition-crawler`이고 항목 ID에서는 `…`로 줄였다.

#### GET/raw.githubusercontent.com/…/data/{file} 목록·상태 파일 읽기

기본 브랜치의 목록 파일과, 토큰이 없을 때의 상태 파일을 인증 없이 받아 화면에 보여 준다.

유스케이스 [[CCR-UC-001#UC-A2]] 1 · 개념 [[CCR-DOM-001#ListEntry]] · [[CCR-DOM-001#Status]] · 경계 목록 · 화면 [[CCR-UI-001#UI-1]]

**요청.** 페이지를 열 때와 새로 고침(2)을 누를 때 목록 파일을 받는다. 상태 파일은 토큰이 없거나 표시용 판 읽기가 실패했을 때만 여기서 받는다(1.4). 주소에 `?t=<현재 시각 ms>`를 붙여 브라우저 캐시를 피한다. CDN 캐시(5분)는 피하지 못한다(1.4). `Authorization`을 보내지 않는다.

**응답 읽기.** 목록 파일은 JSON Lines라 줄마다 읽고, 상태 파일은 JSON 객체 하나다(4.2). 파일이 없으면 404가 온다. 응답의 `Content-Type`은 `text/plain`이라 페이지가 직접 파싱한다.

```yaml
/{owner}/{repo}/main/data/{file}:
  get:
    servers: [{url: "https://raw.githubusercontent.com"}]
    parameters:
      - {name: file, in: path, required: true, schema: {type: string, enum: [competitions.jsonl, status.json]}}
      - {name: t, in: query, schema: {type: integer}, description: "현재 시각(ms). 브라우저 캐시를 피하는 값. CDN 캐시는 피하지 못한다"}
    responses:
      "200":
        description: "파일 내용 그대로. competitions.jsonl은 한 줄이 목록 항목 하나, status.json은 객체 하나(4.2)"
        content:
          text/plain:
            example: |
              {"id":"AI팩토리:9304","source":"AI팩토리","source_id":"9304","title":"2026 국립공원 위성 모니터링 AI 챌린지","link":"https://aifactory.space/competitions/9304","start_date":"2026-07-31","deadline":"2026-10-06","collected_on":"2026-09-29","reason":"위성 영상 AI 분석 경진대회"}
      "404":
        description: "파일이 없다. 목록 파일이면 첫 실행 전, 상태 파일이면 아직 아무것도 바꾸지 않은 것이다"
```

#### GET/api.github.com/…/contents/data/status.json 상태 파일의 판 읽기

쓰기 직전에 상태 파일의 최신 판(`sha`)과 내용을 읽는다. 토큰이 있으면 화면에 보일 상태 파일도 이 요청으로 읽고, 토큰을 넣을 때의 검증에도 같은 요청을 쓴다.

유스케이스 [[CCR-UC-001#UC-A2]] 1 · [[CCR-UC-001#UC-H1]] 3 · 4a · [[CCR-UC-001#UC-H2]] 4 · 개념 [[CCR-DOM-001#Status]] · 경계 목록 · 화면 [[CCR-UI-001#UI-1]] · [[CCR-UI-001#UI-2]]

**요청.** `ref=main`을 붙이고 1.4의 헤더 셋을 보낸다. 캐시되지 않는다.

**응답 읽기.** `sha`가 판이고, `content`는 Base64로 인코딩된 파일 내용이다(`encoding`이 `base64`). 줄바꿈이 섞인 Base64라 디코딩 전에 공백을 뗀다. 디코딩한 UTF-8을 JSON으로 읽는다. 404면 파일이 아직 없는 것이다(2.3).

```yaml
/repos/{owner}/{repo}/contents/data/status.json:
  get:
    servers: [{url: "https://api.github.com"}]
    security: [{bearer: []}]                 # 페이지 토큰
    parameters:
      - {name: ref, in: query, required: true, schema: {type: string, enum: [main]}}
      - {name: Accept, in: header, required: true, schema: {type: string, enum: ["application/vnd.github+json"]}}
      - {name: X-GitHub-Api-Version, in: header, required: true, schema: {type: string, enum: ["2022-11-28"]}}
    responses:
      "200":
        content:
          application/json:
            schema:
              type: object
              properties:
                sha: {type: string, example: "3d21e0e4a7f0c2b3c1e6a8f9d4b2c1a0e5f6d7c8"}
                size: {type: integer}
                encoding: {type: string, enum: [base64]}
                content: {type: string, description: "Base64. 76자마다 줄바꿈이 있다"}
      "401":
        description: "토큰이 없거나 틀렸다"
      "403":
        description: "권한이 모자라거나 한도에 닿았다. 한도면 x-ratelimit-remaining 헤더가 0이다"
      "404":
        description: "파일이 없다. 공개 저장소라 토큰이 이 저장소를 고르지 않았어도 읽기는 되므로 다른 뜻은 없다"
```

#### PUT/api.github.com/…/contents/data/status.json 상태 파일 쓰기

상태 파일 전체를 새 내용으로 바꿔 `main`에 한 커밋으로 올린다.

유스케이스 [[CCR-UC-001#UC-H1]] 4 · 개념 [[CCR-DOM-001#Status]] · 경계 목록 · 화면 [[CCR-UI-001#UI-1]]

**요청.** 읽어 둔 내용에 이번 바꿈을 얹어 만든 객체를 JSON 문자열로 만들고(키는 식별자 순으로 정렬, 두 칸 들여쓰기, 끝에 줄바꿈), UTF-8 바이트를 Base64로 넣는다. `sha`는 읽어 둔 판이다. 파일이 없으면 `sha`를 빼 새로 만든다. `branch`는 `main`이다. 커밋 메시지는 1.4의 꼴이다. `author`와 `committer`는 저장소 주인의 이름과 noreply 주소다(1.4).

**응답 읽기.** 201(새 파일)이나 200(고침)이 오면 성공이다. 응답의 `content.sha`는 기억하지 않는다. 다음 쓰기도 판 읽기부터 하기 때문이다([[CCR-DOM-002#StatusStore]]). `commit.sha`는 로그에도 남기지 않는다. 409 · 422 · 401 · 403 · 404 · 5xx는 2.3대로 다룬다.

```yaml
/repos/{owner}/{repo}/contents/data/status.json:
  put:
    servers: [{url: "https://api.github.com"}]
    security: [{bearer: []}]                 # 페이지 토큰
    parameters:
      - {name: Accept, in: header, required: true, schema: {type: string, enum: ["application/vnd.github+json"]}}
      - {name: X-GitHub-Api-Version, in: header, required: true, schema: {type: string, enum: ["2022-11-28"]}}
    requestBody:
      content:
        application/json:
          example:
            message: "status: 2026 국립공원 위성 모니터링 AI 챌린지 → 진행 중"
            content: "<UTF-8 JSON의 Base64>"
            sha: "3d21e0e4a7f0c2b3c1e6a8f9d4b2c1a0e5f6d7c8"   # 파일이 없으면 뺀다
            branch: "main"
            author: {name: "<저장소 주인 이름>", email: "<id>+<login>@users.noreply.github.com"}   # 페이지 설정 파일의 상수(1.4)
            committer: {name: "<저장소 주인 이름>", email: "<id>+<login>@users.noreply.github.com"}   # author와 같다
    responses:
      "200":
        description: "고쳤다. content.sha가 새 판이다"
        content:
          application/json:
            schema:
              type: object
              properties:
                content: {type: object, properties: {sha: {type: string}}}
                commit: {type: object, properties: {sha: {type: string}}}
      "201":
        description: "새로 만들었다. 모양은 200과 같다"
      "409":
        description: "sha가 최신 판이 아니다. 최신 판을 다시 읽고 한 번 더 쓴다(2.3)"
      "422":
        description: "sha가 없거나 맞지 않거나, 본문이 잘못됐다(2.3)"
```

## 4. 스키마

### 4.1 대회의 공통 형식

소스 여섯이 채우는 값을 한데 모았다. 속성의 뜻은 [[CCR-DOM-001#Competition]]을 따른다.

| 속성 | event-us | DACON | Kaggle | wevity | AI팩토리 | 콘테스트코리아 |
|---|---|---|---|---|---|---|
| 원천 ID | `id` | `cpt_id` | `ref`의 slug | `ix` | 가장 작은 과제 `id` | `str_no` |
| 대회명 | `title` | `name` | `title` | 제목(배지 제외) | 3.1의 차례 | `span.txt` |
| 접수시작일 | `register_start_date` | `period_start` | `enabledDate` | 없음 | 가장 이른 접수 시작 | "접수 MM.DD" |
| 접수마감일 | `register_due_date` | `period_end` | `newEntrantDeadline`, 없으면 `deadline` | 기준일 ± N + 보정값 | 가장 늦은 접수 마감 | 접수 기간의 뒤 날짜 |
| 시간대 | UTC | 표기 없음(KST) | UTC | 기준일로 셈 | UTC | 연도만 기준일로 정함 |
| 부가 정보 | 분야 · 태그 | 키워드 | 분야 · 태그 | 분야 · 주최 | 페이지 · 과제명 | 분야 · 주최 · 대상 |

### 4.2 목록 항목과 상태 파일의 값

필드 이름과 형식은 ERD가 정한다([[CCR-DOM-003]]). 여기는 페이지가 읽고 쓰는 값만 적는다. 값은 모두 [[CCR-DOM-001#ListEntry]] · [[CCR-DOM-001#Status]]의 속성이다.

**목록 파일 한 줄(페이지가 읽는다).** 값은 묶음의 대표에서 온다([[CCR-PRD-001#R6]]).

| 속성 | 페이지가 |
|---|---|
| 식별자 | 상태 파일의 키로 쓴다. `<출처>:<원천 ID>` 꼴이다 |
| 대회명 | 대회명 링크의 글([[CCR-UI-001#UI-1]] 7.2) |
| 링크 | 새 창으로 여는 주소 |
| 접수시작일 · 접수마감일 | 정렬과 마감 표시(7.1). 접수마감일이 `null`이면 맨 뒤다 |
| 출처 | 칩(7.3)과 거르기(3.1) |
| 수집일 | 수집일 열. 오늘이면 새로 들어온 대회다 |
| 판별 근거 | 대회명 아래 회색 글(7.6) |

**상태 파일(페이지가 읽고 쓴다).** 식별자를 키로 한 객체 하나다. 값이 없는 대회는 `시작 전`이고 감추지 않았고 별표가 없는 것이다.

```json
{
  "AI팩토리:9304": {"status": "in_progress", "hidden": false, "starred": true, "updated_at": "2026-10-01T00:12:41Z"},
  "event-us:135608": {"status": "skipped", "hidden": true, "starred": false, "updated_at": "2026-10-01T00:13:07Z"}
}
```

| 값 | 뜻 |
|---|---|
| `status` | `not_started` · `in_progress` · `submitted` · `done` · `skipped`. 화면에는 `시작 전` · `진행 중` · `제출` · `완료` · `미참`으로 보인다 |
| `hidden` | 지웠으면 `true`. 되살리면 `false`로 둔다. 키를 지우지 않는다 |
| `starred` | 별표를 붙였으면 `true`. 2026-10-01에 더한 필드라 그 전에 쓴 항목에는 없고, 없거나 불 값이 아니면 `false`로 본다 |
| `updated_at` | 마지막으로 바꾼 시각. UTC, 초 단위 |

`결과날`은 두지 않는다([[CCR-PRD-001#R6]]).

### 4.3 판별 스키마

```json
{
  "components": {
    "schemas": {
      "Relevance": {
        "type": "object",
        "properties": {
          "decision": {"type": "string", "enum": ["keep", "discard"]},
          "reason": {"type": "string"}
        },
        "required": ["decision", "reason"],
        "additionalProperties": false
      }
    }
  }
}
```

엄격한 스키마는 모든 필드를 `required`에 넣고 `additionalProperties: false`를 두어야 받는다.

## 5. 미결사항

2026-10-01에 Kaggle 실측 항목을 닫았다. 쪽 넘김 · `category` 값 · 커뮤니티 탭은 3.1 Kaggle에, 쿠키는 1.1에 적었다.

- [ ] 콘테스트코리아는 목록에 발표일을 준다. 이 소스만이라도 `결과날`을 채울지 정한다([[CCR-PRD-001]] 6장)
- [ ] Kaggle 새 토큰의 만료와 범위. 설정 화면에서 만든 토큰은 공식 문서가 다루지 않는다([[CCR-INFRA-001]] 5.2)
- [ ] **[[CCR-RFQ-001]]은 사람이 쓴 문서라 맞추지 않았다.** 2026-09-29의 v9는 노션을 페이지로 바꾼 것만 고쳤다. 이 문서와 다른 곳은 여전히 셋이다. Q2(분야로 좁히지 않는다 — wevity · 콘테스트코리아는 분야로 좁힌다), Q4(DACON은 서버 렌더링 페이로드가 아니라 JSON API, AI팩토리는 보이는 마크업이 아니라 페이지 안의 페이로드, Kaggle의 `category` 값은 `gettingStarted`가 아니라 `Getting Started`), 6장(`결과날` — 콘테스트코리아에는 발표일이 있다). 나머지 상위 문서는 맞췄다([[CCR-PRD-001]] · [[CCR-SCN-001]] · [[CCR-UC-001]] · [[CCR-INFRA-001]] · [[CCR-DOM-001]] · [[CCR-UI-001]])
