#!/usr/bin/env bash
# 노트북 실행기 — CCR-INFRA-001 8.1. 하루치 대회를 모아 원본(싱크독 서버 저장소)의 main에 한 커밋으로 올린다.
#
#   crontab이 08:50~23:50 매시 50분에 부른다. 그날(KST) 예약 실행 줄이 runs.jsonl에 있으면 건너뛴다 —
#   하루 한 번이고, 노트북이 꺼져 있던 날은 켜진 뒤 첫 50분에 돈다([[CCR-INFRA-001#C2]]).
#   늘 원본에서 새로 받은 main의 실행기가 돈다. cron이 부른 작업 사본의 실행기는 main을 받아 넘기기만 한다.
#
# 사용: scripts/daily.sh                                          예약 실행(crontab)
#       scripts/daily.sh --manual [--dry-run] [--ignore-discards]  손 실행
# 설정: ~/.config/ccr/batch.env (권한 600) — CCR_REMOTE · CCR_TOKEN · OPENAI_API_KEY · KAGGLE_API_TOKEN
#       · OPENAI_MODEL(선택) · UV_BIN(선택)
# 기록: ~/.local/state/ccr/logs/{run_id}.log (90일) · 한 줄 기록은 이 스크립트의 출력(crontab이 cron.log로)
set -euo pipefail

STATE="${CCR_STATE_DIR:-$HOME/.local/state/ccr}"
CONF="${CCR_BATCH_CONF:-$HOME/.config/ccr/batch.env}"
LOG_DAYS=90
say() { echo "$(date '+%F %T') $*"; }
notify() { "$(dirname "$0")/notify.sh" "CCR 일배치 실패" "$1" || true; }
# 설정을 읽는다. 내보내지 않는다 — 비밀값은 그것을 쓰는 단계에만 넘긴다(CCR-INFRA-001 5장)
load_conf() {
  if [ ! -r "$CONF" ]; then
    say "실패: 설정 파일이 없다 — $CONF"
    notify "설정 파일이 없다 — $CONF"
    return 1
  fi
  . "$CONF"
  export -n CCR_REMOTE CCR_TOKEN OPENAI_API_KEY KAGGLE_API_TOKEN OPENAI_MODEL 2>/dev/null || true
  if [ -z "${CCR_REMOTE:-}" ] || [ -z "${CCR_TOKEN:-}" ]; then
    say "실패: 설정 파일에 CCR_REMOTE·CCR_TOKEN이 없다 — $CONF"
    notify "설정 파일에 CCR_REMOTE·CCR_TOKEN이 없다 — $CONF"
    return 1
  fi
}

if [ "${CCR_STAGE:-1}" = 1 ]; then
  # ── 1단계: 줄 서기 · 설정 · main 받기 → main의 실행기로 넘긴다 ──
  RUN_KIND=schedule DRY_RUN=false IGNORE_DISCARDS=false
  for arg in "$@"; do
    case "$arg" in
      --manual) RUN_KIND=manual ;;
      --dry-run) DRY_RUN=true ;;
      --ignore-discards) IGNORE_DISCARDS=true ;;
      *) echo "모르는 인자: $arg" >&2; exit 2 ;;
    esac
  done
  if [ "$RUN_KIND" = schedule ] && [ "$DRY_RUN" = true ]; then
    echo "--dry-run은 --manual과 함께만 쓴다" >&2; exit 2
  fi
  mkdir -p "$STATE/logs"
  # 한 번에 하나 — 돌고 있으면 끝날 때까지 기다린다(최대 15분, CCR-INFRA-001 C11)
  exec 9>"$STATE/batch.lock"
  if ! flock -w 900 9; then
    say "건너뜀: 다른 실행이 15분 넘게 돌고 있다 — 시작하지 못하고 끝낸다"
    exit 0
  fi
  load_conf || exit 3

  RUN_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  RUN_ID="local-$(date -u -d "$RUN_STARTED_AT" +%Y%m%dT%H%M%S)"
  WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ccr-run.XXXXXX")"
  trap 'rm -rf "$WORK_DIR"' EXIT
  # 토큰은 명령 줄 설정으로만 — 디스크(.git/config)·로그에 남기지 않는다(CCR-INFRA-001 5.5)
  auth="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$CCR_TOKEN" | base64 -w0)"
  if ! GIT_TERMINAL_PROMPT=0 timeout 120 git -c credential.helper= -c http.extraheader="$auth" \
      clone --quiet --depth=1 --branch main --no-tags "$CCR_REMOTE" "$WORK_DIR/code" 2>"$WORK_DIR/clone.err"; then
    say "실패: 원본을 받지 못했다 — $(tail -n1 "$WORK_DIR/clone.err")"
    notify "원본을 받지 못했다(싱크독이 꺼져 있나) — 다음 50분에 다시 돈다"
    exit 1
  fi
  next="$WORK_DIR/code/scripts/daily.sh"
  [ -f "$next" ] || { say "실패: main에 scripts/daily.sh가 없다"; exit 1; }
  trap - EXIT  # 작업 폴더는 2단계가 지운다
  export CCR_STAGE=2 RUN_KIND DRY_RUN IGNORE_DISCARDS RUN_STARTED_AT RUN_ID WORK_DIR
  exec bash "$next"
fi

# ── 2단계: 받은 main의 실행기 — 오늘 것 확인 · 의존성 · 배치 · 마무리 · 기록 ──
trap 'rm -rf "$WORK_DIR"' EXIT
cancelled=0
trap 'cancelled=1' INT TERM  # 끊어도 마무리까지는 간다(CCR-INFRA-001 8.1)
load_conf || exit 3
cd "$WORK_DIR/code"

if [ "$RUN_KIND" = schedule ]; then
  today="$(TZ=Asia/Seoul date -d "$RUN_STARTED_AT" +%F)"
  if python3 - "$today" <<'PY'
import json, sys
from pathlib import Path

today, path = sys.argv[1], Path("data/runs.jsonl")
for raw in path.read_text(encoding="utf-8").splitlines() if path.is_file() else []:
    try:
        line = json.loads(raw)
    except ValueError:
        continue  # 읽히지 않는 줄은 건너뛴다(CCR-UC-001 UC-S7 2c)
    if isinstance(line, dict) and line.get("base_date") == today and line.get("kind") == "schedule":
        sys.exit(0)
sys.exit(1)
PY
  then
    say "건너뜀: 오늘($today) 예약 실행이 이미 있다"
    exit 0
  fi
fi

find "$STATE/logs" -name '*.log' -type f -mtime +"$LOG_DAYS" -delete 2>/dev/null || true
LOG="$STATE/logs/$RUN_ID.log"
say "시작 $RUN_ID ($RUN_KIND, 미리보기 $DRY_RUN) — 로그 $LOG"
exec 3>&1 >>"$LOG" 2>&1
say "시작 $RUN_ID · 종류 $RUN_KIND · 미리보기 $DRY_RUN · 버림 무시 $IGNORE_DISCARDS · main $(git rev-parse --short HEAD)"

UV="${UV_BIN:-$(command -v uv || echo "$HOME/.local/bin/uv")}"
batch_rc=0
if ! (cd batch && "$UV" sync --frozen --no-dev --quiet); then
  say "의존성을 받지 못했다 — 배치를 건너뛰고 마무리가 중단 줄을 쓴다"
  batch_rc=1
else
  # 비밀값은 이 단계에만. 토큰은 넘기지 않는다(CCR-INFRA-001 5장)
  (
    export BATCH_RUNNER=laptop APPEND_DIR="$WORK_DIR/append"
    export OPENAI_API_KEY="${OPENAI_API_KEY:-}" KAGGLE_API_TOKEN="${KAGGLE_API_TOKEN:-}"
    if [ -n "${OPENAI_MODEL:-}" ]; then export OPENAI_MODEL; fi
    cd batch
    exec timeout -s TERM -k 10s 8m .venv/bin/python -m collector
  ) &
  child=$!
  # 끊기(Ctrl-C · SIGTERM)는 배치에 넘긴다 — 첫 신호에 새 요청을 멈추고, 두 번째에 하던 호출도 끊는다
  trap 'cancelled=1; kill -INT "$child" 2>/dev/null || true' INT TERM
  while :; do
    rc=0
    wait "$child" || rc=$?
    kill -0 "$child" 2>/dev/null || { batch_rc=$rc; break; }  # 신호로 깨어났으면 다시 기다린다
  done
  trap 'cancelled=1' INT TERM  # 마무리는 끊지 않는다 — 3분 한도가 있다
fi
say "배치 끝 — 종료 코드 $batch_rc$([ "$cancelled" = 1 ] && echo ' (끊음)')"

finish_rc=0
if [ "$DRY_RUN" = false ]; then
  # 앞 단계가 실패하거나 끊겨도 돈다. 토큰은 이 단계에만(CCR-INFRA-001 8.2)
  (
    export APPEND_DIR="$WORK_DIR/append" REMOTE_URL="$CCR_REMOTE" PUSH_TOKEN="$CCR_TOKEN"
    exec timeout -s TERM -k 10s 3m python3 batch/finish.py
  ) || finish_rc=$?
  say "마무리 끝 — 종료 코드 $finish_rc"
fi

summary="$RUN_ID — 배치 $batch_rc · 마무리 $finish_rc"
[ "$cancelled" = 1 ] && summary="$summary · 사람이 끊음"
echo "$(date '+%F %T') 끝 $summary" >&3
if [ "$batch_rc" != 0 ] || [ "$finish_rc" != 0 ]; then
  [ "$cancelled" = 1 ] || notify "$summary. 로그: $LOG"  # 사람이 끊은 실행은 알리지 않는다
  exit 1
fi
exit 0
