# competition-crawler

AI·개발 대회를 매일 아침 여섯 곳에서 모아, 접수 중이고 관심 분야인 새 대회만 목록 파일에 더하는 배치입니다. 목록은 이 저장소의 GitHub Pages 페이지에서 봅니다.

- 소스: event-us · DACON · Kaggle · wevity · AI팩토리 · 콘테스트코리아
- 매일 08:50 KST에 GitHub Actions가 돌립니다. 서버·DB가 없습니다.
- 마감이 지난 대회, 이미 목록이나 처리 이력에 있는 대회, OpenAI 판별로 관심 밖인 대회는 넣지 않습니다.
- 한 번 더한 항목은 배치가 다시 건드리지 않습니다. 페이지에서 지운 대회는 되살아나지 않습니다.

명세는 [`docs/specs/`](docs/specs/README.md)에 있습니다. 동작의 근거는 모두 거기 있고, 이 문서는 준비와 운영 방법만 적습니다.

## 저장소

```
batch/             배치. collector/(본체) · tests/ · settings.toml · finish.py(마무리 단계)
data/              competitions.jsonl(목록) · processed.jsonl(처리 이력) · runs.jsonl(실행 요약)는 배치가 커밋한다
                   status.json(진행 상태 · 지움)은 페이지만 쓴다
frontend/          대회 목록 페이지(React + Vite). 준비 중
docs/specs/        명세 원본
.github/           workflows/daily.yml · dependabot.yml
.env.example       로컬 실행에 필요한 환경 변수의 이름
```

## 처음 준비

### 1. GitHub 설정

**저장소 시크릿.** 환경(environment)은 두지 않습니다. 반드시 있어야 하는 시크릿은 없습니다.

| 이름 | 값 | 없으면 |
|---|---|---|
| `OPENAI_API_KEY` | 이 도구 전용 OpenAI 프로젝트의 키. 그 프로젝트에 지출 알림(월 1달러)과 하드 한도(예: 3달러)를 겁니다 | 오늘 마감인 대회만 넣고 나머지는 미룹니다(판별 미룸 경고) |
| `KAGGLE_API_TOKEN` | kaggle.com/settings/api의 Generate New Token | Kaggle만 건너뜁니다(설정 누락 표시) |

**저장소 변수(선택).** `OPENAI_MODEL`에 모델 이름을 넣으면 `batch/settings.toml`의 기본값(`gpt-6-luna`)을 덮습니다. 바꿀 때는 Structured Outputs와 `reasoning.effort: none`을 모두 받는 모델을 고릅니다.

**그 밖.**
- 기본 브랜치 `main`에 규칙셋으로 **강제 push 차단**과 **삭제 제한**을 겁니다. "풀 리퀘스트를 거쳐야만 병합"은 걸지 않습니다. 걸면 매일의 상태 커밋과 페이지의 상태 저장이 막힙니다.
- Actions → General에서 "Require actions to be pinned to a full-length commit SHA"를 켭니다.
- Code security에서 비밀값 스캔의 푸시 보호가 켜져 있는지 봅니다.
- 개인 알림 설정에서 Actions 알림을 **실패한 워크플로만** 받도록 켭니다.
- Actions 로그 보관 기간은 90일(상한) 그대로 둡니다.

### 2. 페이지 토큰

페이지에서 진행 상태를 바꾸거나 대회를 지우면 페이지가 `data/status.json`을 이 저장소에 커밋합니다. 그러려면 이 저장소의 Contents 읽기·쓰기 권한만 있는 **fine-grained 토큰**을 만들어 페이지의 설정에 한 번 넣습니다. 토큰은 브라우저(localStorage)에만 남고 저장소·Actions·로그에는 두지 않습니다. 보기만 할 때는 토큰이 필요 없습니다.

## 운영

- **매일 08:50 KST**에 자동으로 돕니다. 목록 파일에 새 줄이 들어오고 `data/`에 `github-actions[bot]`의 커밋이 하나 생깁니다. 페이지는 그 파일을 읽어 보여 줍니다.
- **미리보기**: Actions → daily → Run workflow에서 `dry_run`을 켭니다. 목록과 상태 파일에 아무것도 쓰지 않고, 무엇이 들어갔을지를 로그에 남깁니다. `main`이 아닌 브랜치에서 누르면 늘 미리보기입니다.
- **판별 기준을 바꿀 때**: 미리보기에 `ignore_discards`를 켜면 처리 이력의 버림 기록을 없는 것으로 보고 판별합니다. 기준을 바꾼 뒤 `data/processed.jsonl`에서 결과가 `discard`인 줄만 지우고 커밋합니다. `keep` 줄은 지우지 않습니다. 남김 줄이 줄면 다음 실행이 판별 전에 멈춥니다(처리 이력 감소).
- **실패한 날**: Actions 로그와 `data/runs.jsonl`의 마지막 줄을 봅니다. 결과(`result`)와 실패 사유(`failure_reason`), 경고(`warnings`)가 있습니다. 원인을 고친 뒤 **새 수동 실행**으로 다시 돌립니다. Re-run은 워크플로 정의를 고친 뒤에는 멈춥니다.
- **실행이 아예 없는 날**: `runs.jsonl` 마지막 줄의 날짜가 오늘이 아니면 워크플로가 꺼졌는지 봅니다. 공개 저장소는 60일 활동이 없으면 예약 워크플로가 꺼집니다. `gh workflow enable daily.yml`로 다시 켭니다. 켜 두려고 빈 커밋을 만들지 않습니다.

`data/runs.jsonl` 한 줄의 실패 사유: `all_sources_failed`(여섯 소스 모두 실패) · `list_read_failed`(목록 파일을 읽지 못함) · `history_read_failed`(처리 이력을 읽지 못함) · `history_shrank`(남김 줄이 줄었음). 뒤의 셋은 `data/`의 파일을 사람이 고친 뒤 다시 돌립니다.

경고 종류:

| 경고 | 뜻 |
|---|---|
| `zero_count` | 꾸준히 건수를 내던 소스가 오류 없이 0건을 냈습니다. 사이트 개편일 수 있습니다 |
| `judge_deferred` | 판별 실패가 절반을 넘어 미뤘습니다. 원인이 `missing_key`면 키, `call_failed`면 키 · 크레딧 · 지출 한도 · 모델 이름을 봅니다 |
| `summary_corrupt` | `runs.jsonl`에 읽히지 않는 줄이 있습니다 |

## 로컬에서 돌리기

```bash
cp .env.example .env        # OpenAI 키 등을 채운다. 비워 둬도 돈다. .env는 커밋하지 않는다
cd batch
uv sync
uv run python -m collector                    # 하루치 미리보기. 로컬은 늘 목록에 쓰지 않는다
uv run python -m collector collect --show     # 수집만 해 본다. OpenAI를 부르지 않는다
uv run pytest
uv run ruff format --check && uv run ruff check
```

로컬 실행은 데이터 파일을 작업 트리가 아니라 `origin/main` 최신 판에서 꺼내 읽습니다. 그래서 `git fetch`가 되는 곳에서 돌립니다.
