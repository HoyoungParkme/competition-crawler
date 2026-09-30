import { afterEach, describe, expect, it, vi } from 'vitest'
import { decodeContent, encodeStatusFile, writeStatusFile } from '../../src/api/github'
import { COMMIT_AUTHOR } from '../../src/config'

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

describe('writeStatusFile', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  /** fetch를 가짜로 바꾸고, 보낸 본문을 돌려준다. 응답은 200과 새 판 */
  const stubFetch = () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        new Response(JSON.stringify({ content: { sha: 'new-sha' } }), { status: 200 }),
      )
    vi.stubGlobal('fetch', fetchMock)
    return () => JSON.parse(fetchMock.mock.calls[0]![1]!.body as string) as Record<string, unknown>
  }

  it("sends the repository owner's noreply address as author and committer", async () => {
    const sentBody = stubFetch()
    const sha = await writeStatusFile('token', {}, 'old-sha', 'status: 대회 1 → 진행 중')
    expect(sha).toBe('new-sha')
    const body = sentBody()
    expect(body).toMatchObject({
      message: 'status: 대회 1 → 진행 중',
      branch: 'main',
      sha: 'old-sha',
    })
    expect(body.author).toEqual(COMMIT_AUTHOR)
    expect(body.committer).toEqual(COMMIT_AUTHOR)
    expect(COMMIT_AUTHOR.email).toMatch(/^\d+\+HoyoungParkme@users\.noreply\.github\.com$/)
  })

  it('leaves sha out for a new file and still sends the author', async () => {
    const sentBody = stubFetch()
    await writeStatusFile('token', {}, null, 'status: 대회 1 지움')
    const body = sentBody()
    expect('sha' in body).toBe(false)
    expect(body.committer).toEqual(COMMIT_AUTHOR)
  })
})
