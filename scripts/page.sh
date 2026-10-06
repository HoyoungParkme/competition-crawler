#!/usr/bin/env bash
# 노트북 페이지 띄우기·배포 — CCR-INFRA-001 8.11. crontab이 @reboot와 5분마다 부른다(sudo 없이).
#
#   1) 원본 main을 받아, 이 스크립트가 main의 것과 다르면 main의 것으로 넘긴다(실행기와 같다).
#   2) main의 frontend/ 트리나 batch/page_server.py가 지난 빌드와 다르면 npm ci && npm run build로
#      다시 빌드하고 서버를 다시 띄운다. 빌드가 실패하면 이전 빌드를 그대로 내고 윈도 알림을 한 번
#      띄운다(같은 판은 다시 빌드하지 않는다).
#   3) 서버가 죽었거나 설정(원본·토큰)이 바뀌었으면 다시 띄운다. 원본에 닿지 못해도 지난 빌드로 띄운다.
#
# 사용: scripts/page.sh
# 설정: ~/.config/ccr/batch.env (권한 600) — CCR_REMOTE · CCR_TOKEN · NODE_BIN(선택)
# 기록: ~/.local/state/ccr/page.log · 빌드는 ~/.local/share/ccr/releases/ (최근 셋)
set -euo pipefail

STATE="${CCR_STATE_DIR:-$HOME/.local/state/ccr}"
SHARE="${CCR_SHARE_DIR:-$HOME/.local/share/ccr}"
CONF="${CCR_BATCH_CONF:-$HOME/.config/ccr/batch.env}"
PORT="${PAGE_PORT:-8090}"
say() { echo "$(date '+%F %T') page: $*"; }
notify() { "$(dirname "$0")/notify.sh" "$1" "$2" || true; }

mkdir -p "$STATE" "$SHARE/releases"
if [ "${CCR_PAGE_STAGE:-1}" = 1 ]; then
  exec 9>"$STATE/page.lock"
  flock -n 9 || exit 0  # 앞의 확인이 아직 돈다
fi
if [ ! -r "$CONF" ]; then say "설정 파일이 없다 — $CONF"; exit 3; fi
# 내보내지 않는다 — 서버에 넘길 것만 골라 넘긴다(CCR-INFRA-001 5장)
. "$CONF"
export -n CCR_REMOTE CCR_TOKEN OPENAI_API_KEY KAGGLE_API_TOKEN OPENAI_MODEL 2>/dev/null || true
if [ -z "${CCR_REMOTE:-}" ]; then say "설정 파일에 CCR_REMOTE가 없다 — $CONF"; exit 3; fi

# page.log가 10MB를 넘으면 하나만 남기고 돌린다
if [ -f "$STATE/page.log" ] && [ "$(stat -c %s "$STATE/page.log")" -gt 10485760 ]; then
  mv -f "$STATE/page.log" "$STATE/page.log.1"
fi

restart=0
src="$SHARE/src.git"
[ -f "$src/HEAD" ] || git init --quiet --bare "$src"
auth=()
if [ -n "${CCR_TOKEN:-}" ]; then
  auth=(-c "http.extraheader=AUTHORIZATION: basic $(printf 'x-access-token:%s' "$CCR_TOKEN" | base64 -w0)")
fi
if GIT_TERMINAL_PROMPT=0 timeout 60 git -C "$src" "${auth[@]}" fetch --quiet --no-tags --depth=1 \
    "$CCR_REMOTE" +refs/heads/main:refs/heads/main 2>"$STATE/page.fetch.err"; then
  # 늘 main의 page.sh로 돈다 — 작업 사본에서 고치는 중인 것이 섞이지 않는다
  if [ "${CCR_PAGE_STAGE:-1}" = 1 ] && git -C "$src" cat-file -e main:scripts/page.sh 2>/dev/null; then
    git -C "$src" show main:scripts/page.sh > "$SHARE/page-main.sh"
    git -C "$src" show main:scripts/notify.sh > "$SHARE/notify.sh" 2>/dev/null && chmod +x "$SHARE/notify.sh"
    if ! cmp -s "$0" "$SHARE/page-main.sh"; then
      export CCR_PAGE_STAGE=2
      exec bash "$SHARE/page-main.sh"
    fi
  fi
  want="$(git -C "$src" rev-parse main:frontend):$(git -C "$src" rev-parse main:batch/page_server.py)"
  have="$(cat "$SHARE/current/.version" 2>/dev/null || true)"
  failed="$(cat "$SHARE/failed.version" 2>/dev/null || true)"
  if [ "$want" != "$have" ] && [ "$want" != "$failed" ]; then
    say "새 판을 빌드한다 — $want"
    tmp="$(mktemp -d "${TMPDIR:-/tmp}/ccr-page.XXXXXX")"
    trap 'rm -rf "$tmp"' EXIT
    git -C "$src" archive main frontend batch/page_server.py | tar -x -C "$tmp"
    node_bin="${NODE_BIN:-$(ls -d "$HOME"/.nvm/versions/node/*/bin 2>/dev/null | sort -V | tail -n1)}"
    if [ -n "$node_bin" ]; then export PATH="${node_bin%/node}:$PATH"; fi
    if (cd "$tmp/frontend" && npm ci --no-audit --no-fund --loglevel=error && npm run build); then
      rel="$SHARE/releases/$(date +%Y%m%d%H%M%S)"
      mkdir -p "$rel"
      cp -r "$tmp/frontend/dist" "$rel/dist"
      cp "$tmp/batch/page_server.py" "$rel/page_server.py"
      echo "$want" > "$rel/.version"
      ln -sfn "$rel" "$SHARE/current.new" && mv -T "$SHARE/current.new" "$SHARE/current"
      rm -f "$SHARE/failed.version"
      ls -1d "$SHARE"/releases/*/ | sort | head -n -3 | while read -r old; do rm -rf "$old"; done
      restart=1
      say "빌드했다 — $rel"
    else
      echo "$want" > "$SHARE/failed.version"
      say "빌드 실패 — 이전 빌드를 그대로 낸다"
      notify "CCR 페이지 빌드 실패" "이전 빌드를 그대로 냅니다. 로그: $STATE/page.log"
    fi
  fi
else
  say "원본을 받지 못했다 — 지난 빌드로 띄운다: $(tail -n1 "$STATE/page.fetch.err")"
fi

if [ ! -f "$SHARE/current/page_server.py" ]; then
  say "아직 빌드가 없다 — 띄우지 않는다"
  exit 1
fi

# 원본·토큰이 바뀌면(토큰 재발급 등) 서버를 다시 띄운다. 값 대신 해시만 남긴다
conf_sum="$(printf '%s\n%s\n' "$CCR_REMOTE" "${CCR_TOKEN:-}" | sha256sum | cut -c1-16)"
if [ "$conf_sum" != "$(cat "$STATE/page.conf.sum" 2>/dev/null || true)" ]; then restart=1; fi

pid="$(cat "$STATE/page.pid" 2>/dev/null || true)"
running=0
if [ -n "$pid" ] && grep -q page_server.py "/proc/$pid/cmdline" 2>/dev/null; then running=1; fi
if [ "$running" = 1 ] && [ "$restart" = 1 ]; then
  kill "$pid" 2>/dev/null || true
  for _ in 1 2 3 4 5; do grep -q page_server.py "/proc/$pid/cmdline" 2>/dev/null || break; sleep 1; done
  running=0
fi
if [ "$running" = 0 ]; then
  # 서버에는 원본·토큰과 자리만 넘긴다. 잠금(9)은 넘기지 않는다 — 넘기면 다음 확인이 늘 멈춘다
  (
    export CCR_REMOTE CCR_TOKEN="${CCR_TOKEN:-}" PAGE_PORT="$PORT" PAGE_DIST="$SHARE/current/dist" \
      PAGE_MIRROR="$SHARE/page.git"
    exec setsid nohup python3 "$SHARE/current/page_server.py" >>"$STATE/page.log" 2>&1 </dev/null 9>&-
  ) &
  echo $! > "$STATE/page.pid"
  echo "$conf_sum" > "$STATE/page.conf.sum"
  say "띄웠다 — http://localhost:$PORT (pid $!)"
fi
exit 0
