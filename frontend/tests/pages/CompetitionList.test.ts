import { describe, expect, it, vi } from 'vitest'
import { GitHubError, type StatusVersion } from '../../src/api/github'
import type { ListEntry, Row, StatusFile } from '../../src/domain/types'
import {
  isExpired,
  kstToday,
  readStatusForView,
  sortByDeadline,
} from '../../src/pages/CompetitionList'

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

describe('readStatusForView', () => {
  const apiFile: StatusFile = {
    'DACON:1': { status: 'in_progress', hidden: false, updated_at: 'from-api' },
  }
  const rawFile: StatusFile = {
    'DACON:1': { status: 'not_started', hidden: false, updated_at: 'from-raw' },
  }
  const readRaw = () => Promise.resolve(rawFile)

  it('reads raw when there is no token', async () => {
    const readVersion = vi.fn<(token: string) => Promise<StatusVersion>>()
    expect(await readStatusForView(null, readVersion, readRaw)).toEqual(rawFile)
    expect(readVersion).not.toHaveBeenCalled()
  })

  it('reads the Contents API when there is a token, because raw is cached for minutes', async () => {
    const readVersion = vi.fn((_token: string) => Promise.resolve({ sha: 'abc', file: apiFile }))
    expect(await readStatusForView('token', readVersion, readRaw)).toEqual(apiFile)
    expect(readVersion).toHaveBeenCalledWith('token')
  })

  it('falls back to raw when the Contents API read fails', async () => {
    const readVersion = () => Promise.reject(new GitHubError(401))
    expect(await readStatusForView('expired-token', readVersion, readRaw)).toEqual(rawFile)
  })
})
