/** 목록 표(CCR-UI-001 UI-1 7 · 7.1 ~ 7.7)와 접힌 구역(9 · 9.1). 값과 콜백만 받고 요청하지 않는다. */

import type { ReactNode } from 'react'
import { STATUS_LABEL, STATUS_VALUES, type Row, type StatusValue } from '../domain/types'

interface Props {
  /** 지금 쪽의 줄. 펼쳐 있으면 접힌 줄도 섞인다 */
  rows: Row[]
  expiredCount: number
  hiddenCount: number
  foldOpen: boolean
  /** 표와 접힌 구역 사이에 둘 쪽 나누기 줄(13) */
  pager?: ReactNode
  today: string
  onToggleFold: () => void
  onStatus: (id: string, title: string, value: StatusValue) => void
  onHide: (id: string, title: string) => void
  onRestore: (id: string, title: string) => void
  onStar: (id: string, title: string, starred: boolean) => void
  el: string
  elDue: string
  elTitle: string
  elSource: string
  elStatus: string
  elHide: string
  elReason: string
  elStar: string
  elFold: string
  elRestore: string
}

/** 두 날짜(YYYY-MM-DD)의 차이(일). deadline − today */
export function daysUntil(deadline: string, today: string): number {
  const ms = Date.parse(`${deadline}T00:00:00Z`) - Date.parse(`${today}T00:00:00Z`)
  return Math.round(ms / 86_400_000)
}

/** 마감 칸(7.1). `MM-DD (D-n)`. 7일 안이면 강조. 없으면 `—` */
export function dueLabel(deadline: string | null, today: string): { text: string; soon: boolean } {
  if (deadline === null) return { text: '—', soon: false }
  const days = daysUntil(deadline, today)
  const mmdd = deadline.slice(5)
  if (days < 0) return { text: `${mmdd} 지남`, soon: false }
  const suffix = days === 0 ? 'D-0' : `D-${days}`
  return { text: `${mmdd} (${suffix})`, soon: days <= 7 }
}

/** 별표(7.7)의 그림. 붙였으면 채운 별, 아니면 빈 별 */
function StarIcon({ filled }: { filled: boolean }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      aria-hidden="true"
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinejoin="round"
    >
      <path d="M12 3.5l2.6 5.3 5.9.9-4.25 4.15 1 5.85L12 16.9l-5.25 2.8 1-5.85L3.5 9.7l5.9-.9z" />
    </svg>
  )
}

export function CompetitionTable(props: Props) {
  const {
    rows,
    expiredCount,
    hiddenCount,
    foldOpen,
    today,
    onToggleFold,
    onStatus,
    onHide,
    onRestore,
    onStar,
  } = props

  const renderRow = (row: Row) => {
    const { entry, status } = row
    const isFolded = row.expired || status.hidden
    const rowClass = [isFolded && 'folded', status.status === 'skipped' && 'skipped']
      .filter(Boolean)
      .join(' ')
    const due = dueLabel(entry.deadline, today)
    return (
      <tr key={entry.id} className={rowClass || undefined}>
        <td className={`cc-due${due.soon && !isFolded ? ' soon' : ''}`} data-el={props.elDue}>
          {due.text}
        </td>
        <td>
          <div className="cc-titlecell">
            <button
              className="cc-star"
              type="button"
              data-el={props.elStar}
              aria-pressed={status.starred}
              aria-label={status.starred ? '별표 떼기' : '별표 붙이기'}
              title={status.starred ? '별표 떼기' : '별표 붙이기'}
              onClick={() => onStar(entry.id, entry.title, !status.starred)}
            >
              <StarIcon filled={status.starred} />
            </button>
            <div>
              <a
                href={entry.link}
                target="_blank"
                rel="noopener noreferrer"
                className={status.hidden ? 'cc-title hidden' : 'cc-title'}
                data-el={props.elTitle}
              >
                {entry.title}
              </a>
              {entry.reason && (
                <div className="cc-note" data-el={props.elReason}>
                  {entry.reason}
                </div>
              )}
            </div>
          </div>
        </td>
        <td>
          <span className="cc-src" data-el={props.elSource}>
            {entry.source}
          </span>
          {status.hidden && <span className="cc-tag"> · 지움</span>}
        </td>
        <td className="cc-due">{entry.collected_on.slice(5)}</td>
        <td>
          {status.hidden ? null : (
            <select
              className={`cc-state ${status.status}`}
              data-el={props.elStatus}
              value={status.status}
              onChange={(event) =>
                onStatus(entry.id, entry.title, event.target.value as StatusValue)
              }
            >
              {STATUS_VALUES.map((value) => (
                <option key={value} value={value}>
                  {STATUS_LABEL[value]}
                </option>
              ))}
            </select>
          )}
        </td>
        <td>
          {status.hidden ? (
            <button
              className="cc-btn"
              type="button"
              data-el={props.elRestore}
              onClick={() => onRestore(entry.id, entry.title)}
            >
              되살리기
            </button>
          ) : (
            <button
              className="cc-btn ghost"
              type="button"
              data-el={props.elHide}
              onClick={() => onHide(entry.id, entry.title)}
            >
              지우기
            </button>
          )}
        </td>
      </tr>
    )
  }

  return (
    <>
      <div className="cc-tblwrap">
        <table className="cc-tbl" data-el={props.el}>
          <thead>
            <tr>
              <th style={{ width: 132 }}>마감</th>
              <th>대회명</th>
              <th style={{ width: 136 }}>출처</th>
              <th style={{ width: 84 }}>수집일</th>
              <th style={{ width: 116 }}>상태</th>
              <th style={{ width: 108 }}></th>
            </tr>
          </thead>
          <tbody>
            {rows.map(renderRow)}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="cc-note">
                  거른 조건에 맞는 열린 대회가 없습니다
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {props.pager}
      <button
        type="button"
        className={`cc-fold${foldOpen ? ' open' : ''}`}
        data-el={props.elFold}
        onClick={onToggleFold}
        aria-expanded={foldOpen}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M9 6l6 6-6 6" />
        </svg>
        <span>
          마감 지난 대회 {expiredCount} · 지운 대회 {hiddenCount} —{' '}
          {foldOpen ? '펼쳐 있음. 누르면 접힌다' : '접혀 있음. 펼치면 표 끝에 이어진다'}
        </span>
      </button>
    </>
  )
}
