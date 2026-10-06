#!/usr/bin/env bash
# 윈도 알림 — CCR-INFRA-001 8.7. 실행기·페이지가 실패했을 때만 부른다. 성공은 조용하다.
#
#   WSL에서 윈도의 powershell.exe로 토스트를 띄운다. 스크립트는 UTF-16LE base64(-EncodedCommand)로
#   넘겨 한글이 깨지지 않게 한다. powershell이 없거나 실패해도 0으로 끝난다 — 알림이 안 떠도
#   실행 기록(로그·runs.jsonl)은 남는다.
#
# 사용: scripts/notify.sh 제목 본문
set -uo pipefail

title="${1:-CCR}"
body="${2:-}"
ps_exe=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe
[ -x "$ps_exe" ] || { echo "알림 없음: powershell.exe가 없다 — $title: $body" >&2; exit 0; }

xml_escape() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' -e "s/'/\&apos;/g" -e 's/"/\&quot;/g' <<<"$1"; }

script=$(cat <<PS
\$ErrorActionPreference = 'Stop'
\$ProgressPreference = 'SilentlyContinue'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
\$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
\$xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>$(xml_escape "$title")</text><text>$(xml_escape "$body")</text></binding></visual></toast>")
\$appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier(\$appId).Show([Windows.UI.Notifications.ToastNotification]::new(\$xml))
PS
)
encoded=$(printf '%s' "$script" | iconv -f UTF-8 -t UTF-16LE | base64 -w0)
"$ps_exe" -NoProfile -NonInteractive -EncodedCommand "$encoded" >/dev/null 2>&1 \
  || echo "알림 실패: powershell — $title: $body" >&2
exit 0
