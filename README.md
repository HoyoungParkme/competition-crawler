# competition-crawler

AI·개발 대회를 매일 아침 여섯 곳에서 모아, 접수 중이고 관심 분야인 새 대회만 목록 파일에 더하는 배치입니다. 노트북에서 돕니다. 원본 저장소는 노트북의 싱크독 서버 저장소(`http://localhost:8000/git/CCR.git`)이고, GitHub 저장소는 2026-10-06부터 보관만 합니다.

- 소스: event-us · DACON · Kaggle · wevity · AI팩토리 · 콘테스트코리아
- 매일 08:50 KST에 노트북의 cron이 돌립니다. 노트북이 꺼져 있던 날은 켜진 뒤 첫 매시 50분에 한 번 돕니다. 서버·DB가 없습니다.
- 마감이 지난 대회, 이미 목록이나 처리 이력에 있는 대회, OpenAI 판별로 관심 밖인 대회는 넣지 않습니다.
- 한 번 더한 항목은 배치가 다시 건드리지 않습니다. 페이지에서 지운 대회는 되살아나지 않습니다.

명세는 [`docs/specs/`](docs/specs/README.md)에 있습니다. 동작의 근거는 모두 거기 있고, 이 문서는 준비와 운영 방법만 적습니다.

## 저장소

```
batch/             배치. collector/(본체) · tests/ · settings.toml · finish.py(마무리 단계)
data/              competitions.jsonl(목록) · processed.jsonl(처리 이력) · runs.jsonl(실행 요약)는 배치가 커밋한다
                   status.json(진행 상태 · 지움)은 페이지만 쓴다
frontend/          대회 목록 페이지(React + Vite + TypeScript). src/ · tests/(vitest)
docs/specs/        명세 원본
scripts/           daily.sh(노트북 실행기) · notify.sh(윈도 알림)
.env.example       개발 PC 미리보기에 쓰는 환경 변수의 이름
```

## 처음 준비 (노트북)

### 1. 설정 파일

`~/.config/ccr/batch.env`(권한 600, 저장소 밖, 노트북에만)에 둡니다. 값은 대화·로그·저장소 파일에 남기지 않고 편집기로 직접 넣습니다.

| 이름 | 값 | 없으면 |
|---|---|---|
| `CCR_REMOTE` | `http://localhost:8000/git/CCR.git` — 싱크독 git 입구 | 돌지 않습니다 |
| `CCR_TOKEN` | 싱크독 개인 토큰(UI-13에서 발급, 이 프로젝트 주인의 것) | 돌지 않습니다 |
| `OPENAI_API_KEY` | 이 도구 전용 OpenAI 프로젝트의 키. 그 프로젝트에 지출 알림(월 1달러)과 하드 한도(예: 3달러)를 겁니다 | 오늘 마감인 대회만 넣고 나머지는 미룹니다(판별 미룸 경고) |
| `KAGGLE_API_TOKEN` | kaggle.com/settings/api의 Generate New Token | Kaggle만 건너뜁니다(설정 누락 표시) |
| `OPENAI_MODEL`(선택) | 모델 이름. `batch/settings.toml`의 기본값(`gpt-6-luna`)을 덮습니다. 바꿀 때는 Structured Outputs와 `reasoning.effort: none`을 모두 받는 모델을 고릅니다 | 기본값 |
| `UV_BIN`(선택) | uv 경로. cron의 PATH에는 `~/.local/bin`이 없습니다 | `~/.local/bin/uv` |

### 2. crontab

```
# CCR 노트북 일배치 — 08:50~23:50 매시 50분, 그날 예약 실행이 있으면 건너뛴다 (CCR-INFRA-001 C2·8.1)
50 8-23 * * * $HOME/dev/personal/competition-crawler/scripts/daily.sh >> $HOME/.local/state/ccr/cron.log 2>&1
```

노트북 시계는 KST입니다(`timedatectl`). cron은 WSL이 켜져 있을 때만 돕니다. cron이 부르는 것은 작업 사본의 실행기지만, 실행기는 원본 `main`을 새로 받아 그 안의 실행기와 코드로 돕니다. 작업 사본에서 고치는 중인 것은 섞이지 않습니다.

## 운영

- **매일 08:50 KST**에 자동으로 돕니다. 목록 파일에 새 줄이 들어오고 원본 `main`에 `ccr-batch`의 커밋 `실행 기록 …`이 하나 생깁니다. 싱크독은 그 커밋을 읽지만 데이터만 바뀐 커밋이라 명세 판·코드 그래프는 만들지 않습니다.
- **기록**: 실행마다 `~/.local/state/ccr/logs/{run_id}.log`(90일 뒤 지움), 한 줄씩 `~/.local/state/ccr/cron.log`(시작·끝·건너뜀), 그리고 `data/runs.jsonl`.
- **실패 알림**: 배치나 마무리 단계가 실패하면 윈도 알림 「CCR 일배치 실패」가 뜹니다. 성공은 조용합니다.
- **미리보기**: `scripts/daily.sh --manual --dry-run`. 목록과 상태 파일에 아무것도 쓰지 않고, 무엇이 들어갔을지를 로그에 남깁니다.
- **손 실행**: `scripts/daily.sh --manual`. 예약 실행과 같은 줄에 서고(한 번에 하나), 그날 예약 실행 여부와 상관없이 돕니다.
- **판별 기준을 바꿀 때**: 작업 사본에서 고친 코드로 `cd batch && IGNORE_DISCARDS=true uv run python -m collector`(늘 미리보기)를 돌려 봅니다. 처리 이력의 버림 기록을 없는 것으로 보고 판별합니다. 기준을 바꾼 뒤 `data/processed.jsonl`에서 결과가 `discard`인 줄만 지우고, 코드와 함께 `main`에 한 커밋으로 합쳐 원본에 push합니다. `keep` 줄은 지우지 않습니다. 남김 줄이 줄면 다음 실행이 판별 전에 멈춥니다(처리 이력 감소).
- **실패한 날**: 그 실행의 로그와 `data/runs.jsonl`의 마지막 줄을 봅니다. 결과(`result`)와 실패 사유(`failure_reason`), 경고(`warnings`)가 있습니다. 원인을 고친 뒤 `scripts/daily.sh --manual`로 다시 돌립니다.
- **실행이 아예 없는 날**: `runs.jsonl` 마지막 줄의 날짜가 오늘이 아니면 노트북이 23:50까지 꺼져 있었거나 cron·싱크독이 돌지 않은 날입니다. `cron.log`를 보고 `scripts/daily.sh --manual`로 돌립니다.

`data/runs.jsonl` 한 줄의 실패 사유: `all_sources_failed`(여섯 소스 모두 실패) · `list_read_failed`(목록 파일을 읽지 못함) · `history_read_failed`(처리 이력을 읽지 못함) · `history_shrank`(남김 줄이 줄었음). 뒤의 셋은 `data/`의 파일을 사람이 고친 뒤 다시 돌립니다.

경고 종류:

| 경고 | 뜻 |
|---|---|
| `zero_count` | 꾸준히 건수를 내던 소스가 오류 없이 0건을 냈습니다. 사이트 개편일 수 있습니다 |
| `judge_deferred` | 판별 실패가 절반을 넘어 미뤘습니다. 원인이 `missing_key`면 키, `call_failed`면 키 · 크레딧 · 지출 한도 · 모델 이름을 봅니다 |
| `summary_corrupt` | `runs.jsonl`에 읽히지 않는 줄이 있습니다 |

## 개발 PC에서 돌리기

```bash
cp .env.example .env        # OpenAI 키 등을 채운다. 비워 둬도 돈다. .env는 커밋하지 않는다
cd batch
uv sync
uv run python -m collector                    # 하루치 미리보기. 실행기 밖은 늘 목록에 쓰지 않는다
uv run python -m collector collect --show     # 수집만 해 본다. OpenAI를 부르지 않는다
uv run pytest
uv run ruff format --check && uv run ruff check
```

실행기 밖의 실행은 데이터 파일을 작업 트리가 아니라 `origin/main`(싱크독 원본) 최신 판에서 꺼내 읽습니다. 그래서 `git fetch`가 되는 곳에서 돌립니다.

## 대회 목록 페이지

노트북 페이지 서버로 옮기는 중입니다(카드 E2). 그 전까지 GitHub Pages 페이지는 없습니다.

```bash
cd frontend
npm ci
npm test && npm run lint && npm run build
```
