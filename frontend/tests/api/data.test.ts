import { describe, expect, it } from 'vitest'
import { DataReadError, parseListFile, parseStatusFile } from '../../src/api/data'

const line = (id: string, extra: Record<string, unknown> = {}) =>
  JSON.stringify({
    id,
    source: 'DACON',
    source_id: id.split(':')[1],
    title: `대회 ${id}`,
    link: `https://dacon.io/${id}`,
    start_date: null,
    deadline: '2026-10-06',
    collected_on: '2026-09-29',
    reason: 'AI',
    ...extra,
  })

describe('parseListFile', () => {
  it('reads one entry per line and skips broken lines', () => {
    const text = [line('DACON:1'), '{broken', '', line('DACON:2', { reason: undefined })].join('\n')
    const entries = parseListFile(text)
    expect(entries.map((e) => e.id)).toEqual(['DACON:1', 'DACON:2'])
    expect(entries[1]!.reason).toBe('')
    expect(entries[0]!.deadline).toBe('2026-10-06')
  })

  it('keeps the first entry when ids repeat', () => {
    const entries = parseListFile(line('DACON:1') + '\n' + line('DACON:1', { title: '뒤의 것' }))
    expect(entries).toHaveLength(1)
    expect(entries[0]!.title).toBe('대회 DACON:1')
  })

  it('skips lines missing a required field and treats bad dates as null', () => {
    const entries = parseListFile(
      [line('DACON:1', { link: '' }), line('DACON:2', { deadline: '10/06' })].join('\n'),
    )
    expect(entries.map((e) => e.id)).toEqual(['DACON:2'])
    expect(entries[0]!.deadline).toBeNull()
  })
})

describe('parseStatusFile', () => {
  it('reads statuses and drops values with a different shape', () => {
    const file = parseStatusFile(
      JSON.stringify({
        'DACON:1': { status: 'in_progress', hidden: false, updated_at: '2026-09-29T00:12:41Z' },
        'DACON:2': { status: 'unknown', hidden: false },
        'DACON:3': 'x',
        'DACON:4': { status: 'done', hidden: true },
      }),
    )
    expect(Object.keys(file)).toEqual(['DACON:1', 'DACON:4'])
    expect(file['DACON:4']).toEqual({ status: 'done', hidden: true, updated_at: '' })
  })

  it('throws DataReadError when the file is not an object', () => {
    expect(() => parseStatusFile('[]')).toThrow(DataReadError)
    expect(() => parseStatusFile('{broken')).toThrow(DataReadError)
    expect(parseStatusFile('')).toEqual({})
  })
})
