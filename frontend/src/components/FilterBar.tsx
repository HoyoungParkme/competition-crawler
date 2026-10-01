/** 거르기 줄(CCR-UI-001 UI-1 3 · 3.1 ~ 3.4). 값은 부모가 들고 브라우저에만 기억한다. */

import { SOURCE_NAMES, STATUS_LABEL, STATUS_VALUES, type StatusValue } from '../domain/types'

export interface Filters {
  source: string
  status: StatusValue | ''
  showAll: boolean
  starredOnly: boolean
}

export const DEFAULT_FILTERS: Filters = {
  source: '',
  status: '',
  showAll: false,
  starredOnly: false,
}

interface Props {
  filters: Filters
  onChange: (filters: Filters) => void
  el: string
  elSource: string
  elStatus: string
  elShowAll: string
  elStarredOnly: string
}

export function FilterBar(props: Props) {
  const { filters, onChange, el, elSource, elStatus, elShowAll, elStarredOnly } = props
  return (
    <div className="cc-bar" data-el={el}>
      <label>
        출처
        <select
          className="cc-sel"
          data-el={elSource}
          value={filters.source}
          onChange={(event) => onChange({ ...filters, source: event.target.value })}
        >
          <option value="">전체</option>
          {SOURCE_NAMES.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>
      <label>
        상태
        <select
          className="cc-sel"
          data-el={elStatus}
          value={filters.status}
          onChange={(event) =>
            onChange({ ...filters, status: event.target.value as StatusValue | '' })
          }
        >
          <option value="">전체</option>
          {STATUS_VALUES.map((value) => (
            <option key={value} value={value}>
              {STATUS_LABEL[value]}
            </option>
          ))}
        </select>
      </label>
      <label>
        <input
          type="checkbox"
          data-el={elShowAll}
          checked={filters.showAll}
          onChange={(event) => onChange({ ...filters, showAll: event.target.checked })}
        />
        마감 지남·지운 대회 보기
      </label>
      <label>
        <input
          type="checkbox"
          data-el={elStarredOnly}
          checked={filters.starredOnly}
          onChange={(event) => onChange({ ...filters, starredOnly: event.target.checked })}
        />
        별표만 보기
      </label>
    </div>
  )
}
