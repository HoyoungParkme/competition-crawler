import { describe, expect, it } from 'vitest'
import type { ListEntry, Row } from '../../src/domain/types'
import { isExpired, kstToday, sortByDeadline } from '../../src/pages/CompetitionList'

const entry = (id: string, deadline: string | null, title = `대회 ${id}`): ListEntry => ({
  id,
  source: 'DACON',
  source_id: id,
  title,
  link: 'https://example.com',
  start_date: null,
  deadline,
  collected_on: '2026-09-29',
  reason: '',
})

const row = (e: ListEntry): Row => ({
  entry: e,
  status: { status: 'not_started', hidden: false, updated_at: '' },
  expired: false,
})

const TODAY = '2026-09-30'

describe('sortByDeadline', () => {
  it('sorts ascending, puts null last and breaks ties by title', () => {
    const rows = [
      row(entry('c', null)),
      row(entry('b', '2026-10-06', '나')),
      row(entry('a', '2026-10-06', '가')),
      row(entry('d', '2026-10-01')),
    ]
    expect(sortByDeadline(rows).map((r) => r.entry.id)).toEqual(['d', 'a', 'b', 'c'])
    expect(rows[0]!.entry.id).toBe('c') // 원본은 그대로
  })
})

describe('isExpired', () => {
  it('is true only when the deadline is before today', () => {
    expect(isExpired(entry('a', '2026-09-29'), TODAY)).toBe(true)
    expect(isExpired(entry('a', '2026-09-30'), TODAY)).toBe(false)
    expect(isExpired(entry('a', null), TODAY)).toBe(false)
  })
})

describe('kstToday', () => {
  it('is the KST date of the moment', () => {
    expect(kstToday(new Date('2026-09-29T15:30:00Z'))).toBe('2026-09-30')
    expect(kstToday(new Date('2026-09-29T14:30:00Z'))).toBe('2026-09-29')
  })
})
