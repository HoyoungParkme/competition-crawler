import { describe, expect, it } from 'vitest'
import { pageOfRow, paginate } from '../../src/components/Pager'

const items = Array.from({ length: 45 }, (_, index) => index + 1)

describe('paginate', () => {
  it('cuts the first page and counts rows from 1', () => {
    expect(paginate(items, 1, 20)).toEqual({
      items: items.slice(0, 20),
      page: 1,
      pages: 3,
      from: 1,
      to: 20,
    })
  })

  it('gives the last page only the rows that are left', () => {
    const view = paginate(items, 3, 20)
    expect(view.items).toEqual([41, 42, 43, 44, 45])
    expect([view.from, view.to]).toEqual([41, 45])
  })

  it('clamps a page past the end to the last page', () => {
    // 지우기로 줄이 줄어 지금 쪽이 비면 마지막 쪽을 보인다(UI-001 UI-1 규칙)
    expect(paginate(items, 9, 20).page).toBe(3)
  })

  it('clamps a page below 1 to the first page', () => {
    expect(paginate(items, 0, 20).page).toBe(1)
    expect(paginate(items, -2, 20).page).toBe(1)
  })

  it('keeps one empty page for an empty list', () => {
    expect(paginate([], 1, 20)).toEqual({ items: [], page: 1, pages: 1, from: 0, to: 0 })
  })
})

describe('pageOfRow', () => {
  it('returns the 1-based page that holds a 0-based row', () => {
    expect(pageOfRow(0, 20)).toBe(1)
    expect(pageOfRow(19, 20)).toBe(1)
    expect(pageOfRow(20, 20)).toBe(2)
    // 2쪽(21번째부터)을 보다 10개로 바꾸면 21번째가 든 3쪽
    expect(pageOfRow(20, 10)).toBe(3)
  })

  it('treats a negative row as the first page', () => {
    expect(pageOfRow(-1, 20)).toBe(1)
  })
})
