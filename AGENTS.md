# AGENTS.md

이 저장소에서 일하는 코딩 에이전트를 위한 안내입니다. 사람을 위한 안내는 [README.md](README.md)입니다.

## 명세가 먼저다

- 명세는 싱크독이 관리하고 `docs/specs/`에 커밋됩니다. 코드는 명세를 따릅니다. 명세와 다르게 고쳐야 하면 코드부터 고치지 말고 명세를 고칠지 사람에게 묻습니다.
- 읽는 차례: RFQ → PRD → SCN → UC → INFRA → DOM(도메인 모델) → API → DOM(클래스 명세 · ERD) → SEQ → MS → CODE.
- 판정 규칙의 수치(유사도 0.90 · 마감일 180일 · 판별 실패 절반)는 규칙이라 코드에 있습니다. 바꾸려면 PRD부터 고칩니다. 조정값은 `batch/settings.toml`에 있습니다.
- 명세 문서의 `status`는 사람이 웹에서만 바꿉니다.

## 구조

`batch/collector/`는 도메인 폴더 넷과 계층 파일로 나뉩니다. 확정본은 클래스 명세(CCR-DOM-002)의 「폴더 구조」 절입니다.

| 폴더 | 하는 일 |
|---|---|
| `domains/collect` | 여섯 소스에서 목록을 받아 공통 형식으로 맞춘다. `adapters/`에 소스마다 하나 |
| `domains/screen` | 마감 판정 · 같은 대회 묶기 · 아는 대회 가르기 · 관심 분야 판별 |
| `domains/list` | 목록 파일(`data/competitions.jsonl`) 읽기와 더하기. 항목을 고치거나 지우는 길은 없고, 페이지가 쓰는 `status.json`은 열지 않는다 |
| `domains/record` | 처리 이력과 실행 요약. 읽기와 덧붙이기만 한다 |
| `run/pipeline.py` | 하루치 흐름(UC-A1). 네 경계를 차례로 부르고, 목록에 항목 하나를 더할 때마다 기록 경계에 남김을 적는다 |
| `infra/` | 소스에 거는 요청(재시도 · 시간 예산 · 요청 간격) · robots.txt |
| `core/` · `shared/` | 설정 · 로그 가리기 · KST 날짜 · 글자 다듬기 |

의존은 한 방향입니다. 선별 → 수집 · 목록 · 기록, 목록 · 기록 → 수집. 경계 사이에서 `_`로 시작하는 이름을 불러오지 않습니다. `batch/finish.py`는 표준 라이브러리만 쓰고 `collector`를 불러오지 않습니다. 페이지(`frontend/`)는 배치 코드를 쓰지 않고 `data/`의 파일만 읽습니다.

## 지킬 것

- **비밀값을 저장소 파일 · 로그 · 대화에 남기지 않습니다.** 비밀값은 노트북의 `~/.config/ccr/batch.env`(600)에만 둡니다. 저장소는 비공개지만 원본·백업·이력에 남으니 섞이면 그 값을 바꿉니다. `data/*.jsonl`에는 정해진 값만 쓰고 예외 메시지 · URL · 응답 본문을 넣지 않습니다.
- 페이지는 토큰을 갖지 않습니다. 노트북 페이지 서버가 `batch.env`의 싱크독 토큰으로 원본에 쓰고, 127.0.0.1에서 Host · Origin을 확인합니다(CCR-INFRA-001 5.8).
- 대회 소스에 요청할 때는 robots.txt를 지키고, 같은 소스 안에서 요청 사이 1초를 둡니다. 개발 중 실측도 같습니다.
- 커밋 메시지에 에이전트 표시(Co-Authored-By · Claude-Session · "Generated with …")를 넣지 않습니다. 작성자는 사람의 계정입니다.
- 의존성은 lock 파일(`batch/uv.lock` · `frontend/package-lock.json`)로 고정합니다. 실행기는 `uv sync --frozen`으로만 받습니다.

## 코드 규약(SYNC-STD-004)

- 공개 함수의 docstring 첫 줄은 클래스 명세 항목 ID 하나입니다(`CCR-MS-001#ListService.append`). 싱크독 `tools/check_code.py --specs docs/specs --backend <collector와 finish.py를 모은 폴더>`가 시그니처까지 대조합니다. 새 함수는 MS 문서에 항목을 먼저 두고 만듭니다.
- `uv run ruff format` · `uv run ruff check`가 0건이어야 합니다. 설정은 `batch/pyproject.toml`에 있습니다(줄 길이 100 · E F I UP B). 한글은 두 칸으로 셉니다.
- 커밋은 `spec(DOC): …` · `fix(#이슈): …` · `code(카드): 함수 — 요약`. 카드마다 브랜치 하나 — 끝나면 `--no-ff`로 `main`에 합쳐 원본(싱크독 서버 저장소)에 push합니다. 서버 저장소라 PR이 없습니다. 이력을 다시 쓰지 않습니다.

## 확인

```bash
cd batch
uv sync
uv run pytest                                 # 네트워크를 쓰지 않는다
uv run ruff format --check && uv run ruff check
uv run python -m collector collect --show     # 실제 소스에 수집만(OpenAI 없음)
uv run python -m collector                    # 하루치 미리보기. 실행기 밖은 목록에 쓰지 않는다

cd ../frontend
npm ci
npm test && npm run lint && npm run build     # vitest · eslint · prettier · tsc + vite
```

페이지의 와이어프레임 번호는 싱크독 `tools/check_ui.py --specs docs/specs --frontend frontend/src`로 대조합니다. 화면 컴포넌트의 파일 첫 주석은 `CCR-UI-001#UI-N`이고, 요소마다 `data-el`에 UI 명세의 번호를 붙입니다.

테스트 픽스처(`batch/tests/fixtures/`)는 실측 응답을 줄인 것입니다. 개인 연락처가 든 필드는 넣지 않습니다.
