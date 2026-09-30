import { describe, expect, it } from 'vitest'
import { decodeContent, encodeStatusFile } from '../../src/api/github'

describe('encodeStatusFile', () => {
  it('sorts keys, indents two spaces, ends with a newline and encodes UTF-8', () => {
    const encoded = encodeStatusFile({
      'event-us:2': { status: 'not_started', hidden: true, updated_at: '2026-09-29T00:13:07Z' },
      'AI팩토리:1': { status: 'in_progress', hidden: false, updated_at: '2026-09-29T00:12:41Z' },
    })
    const text = decodeContent(encoded)
    expect(text).toBe(
      '{\n' +
        '  "AI팩토리:1": {\n    "status": "in_progress",\n    "hidden": false,\n    "updated_at": "2026-09-29T00:12:41Z"\n  },\n' +
        '  "event-us:2": {\n    "status": "not_started",\n    "hidden": true,\n    "updated_at": "2026-09-29T00:13:07Z"\n  }\n' +
        '}\n',
    )
  })

  it('produces the same bytes for the same content', () => {
    const a = encodeStatusFile({
      b: { status: 'done', hidden: false, updated_at: 'x' },
      a: { status: 'done', hidden: false, updated_at: 'y' },
    })
    const b = encodeStatusFile({
      a: { status: 'done', hidden: false, updated_at: 'y' },
      b: { status: 'done', hidden: false, updated_at: 'x' },
    })
    expect(a).toBe(b)
  })
})

describe('decodeContent', () => {
  it('strips the newlines GitHub inserts every 76 characters', () => {
    const encoded = encodeStatusFile({
      'AI팩토리:9304': { status: 'submitted', hidden: false, updated_at: '2026-09-29T00:12:41Z' },
    })
    const wrapped = encoded.replace(/(.{76})/g, '$1\n')
    expect(decodeContent(wrapped)).toBe(decodeContent(encoded))
    expect(JSON.parse(decodeContent(wrapped))).toEqual({
      'AI팩토리:9304': { status: 'submitted', hidden: false, updated_at: '2026-09-29T00:12:41Z' },
    })
  })
})
