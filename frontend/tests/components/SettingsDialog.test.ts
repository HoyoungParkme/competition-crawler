import { describe, expect, it } from 'vitest'
import { daysUntil, dueLabel } from '../../src/components/CompetitionTable'
import { saveFailureText } from '../../src/components/Notice'
import { tokenProblem } from '../../src/components/SettingsDialog'

describe('tokenProblem', () => {
  it('explains 401, 403 and 404 in plain words with the code', () => {
    expect(tokenProblem(401)).toContain('401')
    expect(tokenProblem(403)).toContain('Contents')
    expect(tokenProblem(404)).toContain('저장소에 닿지')
    expect(tokenProblem(500)).toContain('500')
  })
})

describe('dueLabel', () => {
  it('shows MM-DD with D-n, marks a week as soon and past deadlines as 지남', () => {
    expect(daysUntil('2026-10-07', '2026-09-30')).toBe(7)
    expect(dueLabel('2026-10-07', '2026-09-30')).toEqual({ text: '10-07 (D-7)', soon: true })
    expect(dueLabel('2026-10-08', '2026-09-30')).toEqual({ text: '10-08 (D-8)', soon: false })
    expect(dueLabel('2026-09-30', '2026-09-30')).toEqual({ text: '09-30 (D-0)', soon: true })
    expect(dueLabel('2026-09-18', '2026-09-30')).toEqual({ text: '09-18 지남', soon: false })
    expect(dueLabel(null, '2026-09-30')).toEqual({ text: '—', soon: false })
  })
})

describe('saveFailureText', () => {
  const change = { kind: 'status' as const, id: 'x', title: 'x', before: undefined, at: '' }
  it('names the code and the reason', () => {
    expect(saveFailureText({ status: 401, rateLimited: false, change })).toContain('(401)')
    expect(saveFailureText({ status: 403, rateLimited: true, change })).toContain('한도')
    expect(saveFailureText({ status: null, rateLimited: false, change })).toContain('연결')
    expect(saveFailureText({ status: 409, rateLimited: false, change })).toContain('다른 기기')
  })
})
