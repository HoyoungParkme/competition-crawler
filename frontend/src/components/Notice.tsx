/** 알림 셋과 빈 상태(CCR-UI-001 UI-1 8 · 10 · 11 · 11.1 · 12 · 12.1 · 12.2)와 읽기 실패 알림. */

import type { SaveError } from '../store/status'

function Icon({ kind }: { kind: 'clock' | 'warn' | 'cross' }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      {kind === 'clock' && (
        <>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 2" />
        </>
      )}
      {kind === 'warn' && (
        <path d="M12 9v4m0 4h.01M10.3 3.9 2.6 17.2A2 2 0 0 0 4.3 20h15.4a2 2 0 0 0 1.7-2.8L13.7 3.9a2 2 0 0 0-3.4 0z" />
      )}
      {kind === 'cross' && (
        <>
          <circle cx="12" cy="12" r="9" />
          <path d="M15 9l-6 6m0-6 6 6" />
        </>
      )}
    </svg>
  )
}

/** 저장 중(8). 머리에 뜬다 */
export function SavingToast({ el }: { el: string }) {
  return (
    <span className="cc-toast" data-el={el} role="status">
      <Icon kind="clock" />
      저장 중…
    </span>
  )
}

/** 빈 상태(10). 목록 파일이 없거나 비었을 때 표 대신 */
export function EmptyState({ el }: { el: string }) {
  return (
    <div className="cc-empty" data-el={el}>
      아직 대회가 없습니다.
      <br />
      배치가 매일 08:50에 저장소에 목록을 올립니다. 첫 실행 뒤 다시 열어 주세요.
    </div>
  )
}

/** 저장 실패의 짧은 이유(CCR-API-001 2.3). 페이지 서버의 응답 코드로 가른다 */
export function saveFailureText(error: SaveError): string {
  const { status } = error
  if (status === null)
    return '저장하지 못했습니다. 페이지 서버에 닿지 못했거나 응답이 없었습니다. 값을 이전으로 되돌렸습니다.'
  if (status === 409 || status === 422)
    return `저장하지 못했습니다 (${status}). 다른 탭이나 브라우저가 먼저 썼거나 판이 맞지 않습니다. 값을 이전으로 되돌렸습니다.`
  if (status === 502)
    return `저장하지 못했습니다 (${status}). 페이지 서버·싱크독에 닿지 못했습니다. 값을 이전으로 되돌렸습니다.`
  if (status === 403)
    return `저장하지 못했습니다 (${status}). 이 주소로는 저장할 수 없습니다. http://localhost:8090 으로 열어 주세요. 값을 이전으로 되돌렸습니다.`
  return `저장하지 못했습니다 (${status}). 페이지 서버 쪽 오류입니다. 값을 이전으로 되돌렸습니다.`
}

/** 저장 실패(12). 값을 되돌린 뒤 뜬다 */
export function SaveFailedNotice({
  el,
  elRetry,
  error,
  onRetry,
}: {
  el: string
  elRetry: string
  error: SaveError
  onRetry: () => void
}) {
  return (
    <div className="cc-alert err" data-el={el} role="alert">
      <Icon kind="cross" />
      <span>{saveFailureText(error)}</span>
      <span className="sp" />
      <button className="cc-btn primary" type="button" data-el={elRetry} onClick={onRetry}>
        다시 시도
      </button>
    </div>
  )
}

/** 읽지 못했을 때(UC-A2 1b). 번호가 없는 알림이다 */
export function ReadErrorNotice({
  message,
  onRefresh,
}: {
  message: string
  onRefresh: () => void
}) {
  return (
    <div className="cc-alert err" role="alert">
      <Icon kind="cross" />
      <span>{message}. 저장소나 네트워크 문제일 수 있습니다.</span>
      <span className="sp" />
      <button className="cc-btn primary" type="button" onClick={onRefresh}>
        새로 고침
      </button>
    </div>
  )
}
