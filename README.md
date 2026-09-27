# competition-crawler

AI·개발 대회를 매일 아침 여섯 곳에서 모아, 접수 중이고 관심 분야인 새 대회만 노션 `대회목록`에 한 행씩 넣는 배치입니다.

- 소스: event-us · DACON · Kaggle · wevity · AI팩토리 · 콘테스트코리아
- 매일 08:50 KST에 GitHub Actions가 돌립니다. 서버·DB가 없습니다.
- 마감이 지난 대회, 이미 노션이나 처리 이력에 있는 대회, OpenAI 판별로 관심 밖인 대회는 넣지 않습니다.
- 한 번 넣은 노션 행은 다시 건드리지 않습니다. 참가자가 지운 행은 되살아나지 않습니다.

명세는 [`docs/specs/`](docs/specs/README.md)에 있습니다. 동작의 근거는 모두 거기 있고, 이 문서는 준비와 운영 방법만 적습니다.

## 저장소

```
batch/             배치. collector/(본체) · tests/ · settings.toml · finish.py(마무리 단계)
data/              상태 파일. processed.jsonl(처리 이력) · runs.jsonl(실행 요약). 배치가 커밋한다
docs/specs/        명세 원본
.github/           workflows/daily.yml · dependabot.yml
.env.example       로컬 실행에 필요한 환경 변수의 이름
```

## 처음 준비

### 1. 노션 연결 둘

노션 개발자 포털에서 내부 연결(internal connection)을 둘 만듭니다. 둘 다 댓글 기능은 끄고, 사용자 정보는 No user information으로 둡니다.

| 연결 | 기능 | 토큰을 둘 곳 |
|---|---|---|
| 쓰기 연결 | Read content · Insert content · Update content | GitHub 환경 `notion-write` |
| 읽기 연결 | Read content | GitHub 환경 `notion-read`, 로컬 `.env` |

**두 연결 모두 `대회목록` DB 자체에만 연결합니다. DB를 품은 부모 페이지에 연결하지 않습니다.** 부모에 연결하면 그 아래 개인 페이지까지 토큰의 범위에 듭니다. DB를 전체 페이지로 연 뒤 `•••` → Add connections로 잇거나, 포털의 Content access에서 DB만 고릅니다. 연결한 뒤 부모 페이지를 그 토큰으로 조회해 `404 object_not_found`가 오는지 확인합니다.

배치는 `출처`(선택) · `수집일`(날짜) 컬럼이 없으면 처음 넣는 날 직접 만듭니다. `기타`(제목) · `링크` · `시작일` · `마감일` · `상태`(`시작 전` 선택지 포함)는 있어야 합니다.

### 2. GitHub 설정

**환경 두 개.** Settings → Environments에서 `notion-write`와 `notion-read`를 만들고, 각각 시크릿 `NOTION_TOKEN`에 그 연결의 토큰을 넣습니다. `notion-write`는 배포 브랜치를 `main`으로 제한하고 관리자 우회를 끕니다. 검토자와 대기 시간은 두지 않습니다.

**저장소 시크릿.**

| 이름 | 값 | 없으면 |
|---|---|---|
| `NOTION_DATA_SOURCE_ID` | `대회목록`의 데이터 소스 ID | 실행이 실패로 끝납니다(설정 누락) |
| `OPENAI_API_KEY` | 이 도구 전용 OpenAI 프로젝트의 키. 그 프로젝트에 지출 알림(월 1달러)과 하드 한도(예: 3달러)를 겁니다 | 오늘 마감인 대회만 넣고 나머지는 미룹니다(판별 미룸 경고) |
| `KAGGLE_API_TOKEN` | kaggle.com/settings/api의 Generate New Token | Kaggle만 건너뜁니다(설정 누락 표시) |

**저장소 변수(선택).** `OPENAI_MODEL`에 모델 이름을 넣으면 `batch/settings.toml`의 기본값(`gpt-6-luna`)을 덮습니다. 바꿀 때는 Structured Outputs와 `reasoning.effort: none`을 모두 받는 모델을 고릅니다.

**그 밖.**
- 기본 브랜치 `main`에 규칙셋으로 **강제 push 차단**과 **삭제 제한**을 겁니다. "풀 리퀘스트를 거쳐야만 병합"은 걸지 않습니다. 걸면 매일의 상태 커밋이 막힙니다.
- Actions → General에서 "Require actions to be pinned to a full-length commit SHA"를 켭니다.
- Code security에서 비밀값 스캔의 푸시 보호가 켜져 있는지 봅니다.
- 개인 알림 설정에서 Actions 알림을 **실패한 워크플로만** 받도록 켭니다. 오늘 마감인 대회를 넣지 못한 날은 실행이 실패로 끝나 메일이 옵니다.
- Actions 로그 보관 기간은 90일(상한) 그대로 둡니다.

## 운영

- **매일 08:50 KST**에 자동으로 돕니다. 노션에 새 행이 들어오고, `data/`에 `github-actions[bot]`의 커밋이 하나 생깁니다.
- **미리보기**: Actions → daily → Run workflow에서 `dry_run`을 켭니다. 노션과 상태 파일에 아무것도 쓰지 않고, 무엇이 들어갔을지를 로그에 남깁니다. `main`이 아닌 브랜치에서 누르면 늘 미리보기입니다.
- **판별 기준을 바꿀 때**: 미리보기에 `ignore_discards`를 켜면 처리 이력의 버림 기록을 없는 것으로 보고 판별합니다. 기준을 바꾼 뒤 `data/processed.jsonl`에서 결과가 `discard`인 줄만 지우고 커밋합니다. `keep` 줄은 지우지 않습니다. 남김 줄이 줄면 다음 실행이 판별 전에 멈춥니다(처리 이력 감소).
- **실패한 날**: Actions 로그와 `data/runs.jsonl`의 마지막 줄을 봅니다. 결과(`result`)와 실패 사유(`failure_reason`), 경고(`warnings`)가 있습니다. 원인을 고친 뒤 **새 수동 실행**으로 다시 돌립니다. Re-run은 워크플로 정의를 고친 뒤에는 멈춥니다.
- **실행이 아예 없는 날**: `runs.jsonl` 마지막 줄의 날짜가 오늘이 아니면 워크플로가 꺼졌는지 봅니다. 공개 저장소는 60일 활동이 없으면 예약 워크플로가 꺼집니다. `gh workflow enable daily.yml`로 다시 켭니다. 켜 두려고 빈 커밋을 만들지 않습니다.

`data/runs.jsonl` 한 줄의 경고 종류:

| 경고 | 뜻 |
|---|---|
| `zero_count` | 꾸준히 건수를 내던 소스가 오류 없이 0건을 냈습니다. 사이트 개편일 수 있습니다 |
| `judge_deferred` | 판별 실패가 절반을 넘어 미뤘습니다. 원인이 `missing_key`면 키, `call_failed`면 키 · 크레딧 · 지출 한도 · 모델 이름을 봅니다 |
| `create_all_failed` | 넣으려던 행이 모두 실패했습니다. 노션 연결이나 컬럼 이름 · `시작 전` 선택지를 봅니다 |
| `due_today_not_loaded` | 오늘 마감인 대회를 넣지 못했습니다. 실행이 실패로 끝납니다. 그날 안에 고쳐 다시 돌립니다 |
| `summary_corrupt` | `runs.jsonl`에 읽히지 않는 줄이 있습니다 |

## 로컬에서 돌리기

```bash
cp .env.example .env        # 읽기 연결의 노션 토큰 등을 채운다. .env는 커밋하지 않는다
cd batch
uv sync
uv run python -m collector                    # 하루치 미리보기. 로컬은 늘 노션에 쓰지 않는다
uv run python -m collector collect --show     # 수집만 해 본다. 노션 · OpenAI를 부르지 않는다
uv run pytest
```

로컬 실행은 상태 파일을 작업 트리가 아니라 `origin/main` 최신 판에서 꺼내 읽습니다. 그래서 `git fetch`가 되는 곳에서 돌립니다.
