import { describe, expect, it } from 'vitest'
import { GitHubError, type StatusVersion } from '../../src/api/github'
import type { StatusFile } from '../../src/domain/types'
import {
  commitMessage,
  mergeChange,
  nowIso,
  StatusStore,
  type Change,
  type GitHubApi,
  type SaveState,
} from '../../src/store/status'
import { TokenStore } from '../../src/store/token'

const NOW = '2026-09-30T01:00:00Z'

const change = (partial: Partial<Change>): Change => ({
  kind: 'status',
  id: 'DACON:1',
  title: '대회 1',
  value: 'in_progress',
  before: undefined,
  at: NOW,
  ...partial,
})

describe('mergeChange', () => {
  it('changes only that competition and stamps updated_at', () => {
    const file: StatusFile = {
      'DACON:1': { status: 'not_started', hidden: false, updated_at: 'old' },
      'DACON:2': { status: 'done', hidden: false, updated_at: 'keep' },
    }
    const merged = mergeChange(file, change({}), NOW)
    expect(merged['DACON:1']).toEqual({ status: 'in_progress', hidden: false, updated_at: NOW })
    expect(merged['DACON:2']).toEqual(file['DACON:2'])
    expect(file['DACON:1']!.status).toBe('not_started') // 원본은 그대로
  })

  it('hides and restores without touching the status value', () => {
    const hidden = mergeChange({}, change({ kind: 'hide' }), NOW)
    expect(hidden['DACON:1']).toEqual({ status: 'not_started', hidden: true, updated_at: NOW })
    const restored = mergeChange(hidden, change({ kind: 'restore' }), NOW)
    expect(restored['DACON:1']!.hidden).toBe(false)
    expect(Object.keys(restored)).toEqual(['DACON:1']) // 키를 지우지 않는다
  })
})

describe('commitMessage', () => {
  it('has three shapes and truncates the title at 60 characters', () => {
    expect(commitMessage(change({}))).toBe('status: 대회 1 → 진행 중')
    expect(commitMessage(change({ kind: 'hide' }))).toBe('status: 대회 1 지움')
    expect(commitMessage(change({ kind: 'restore' }))).toBe('status: 대회 1 되살림')
    const long = commitMessage(change({ kind: 'hide', title: '가'.repeat(70) }))
    expect(long).toBe(`status: ${'가'.repeat(60)} 지움`)
  })
})

describe('nowIso', () => {
  it('is UTC to the second', () => {
    expect(nowIso(new Date('2026-09-29T00:12:41.789Z'))).toBe('2026-09-29T00:12:41Z')
  })
})

class MemoryTokens extends TokenStore {
  private value: string | null = 'token'
  override get() {
    return this.value
  }
  override set(token: string) {
    this.value = token
  }
  override clear() {
    this.value = null
  }
}

/** 판(sha)을 흉내 내는 가짜 GitHub. 같은 sha로 두 번 쓰면 409 */
class FakeGitHub implements GitHubApi {
  file: StatusFile = {}
  sha: string | null = null
  writes: string[] = []
  failNext: GitHubError | null = null
  reads = 0
  async readStatusVersion(): Promise<StatusVersion> {
    this.reads += 1
    return { sha: this.sha, file: { ...this.file } }
  }
  async writeStatusFile(_token: string, file: StatusFile, sha: string | null, message: string) {
    if (this.failNext) {
      const error = this.failNext
      this.failNext = null
      throw error
    }
    if (sha !== this.sha) throw new GitHubError(409)
    this.file = file
    this.sha = `sha-${this.writes.length + 1}`
    this.writes.push(message)
    return this.sha
  }
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0))

describe('StatusStore', () => {
  it('changes the screen first, then commits one request at a time', async () => {
    const github = new FakeGitHub()
    const states: SaveState[] = []
    const files: StatusFile[] = []
    const store = new StatusStore(github, new MemoryTokens(), (file, state) => {
      files.push(file)
      states.push(state)
    })
    store.load({})
    store.setStatus('DACON:1', '대회 1', 'in_progress')
    store.hide('DACON:2', '대회 2')
    expect(files[0]!['DACON:1']!.status).toBe('in_progress') // 응답 전에 화면이 바뀌었다
    expect(states[0]).toEqual({ saving: true, error: null })
    await flush()
    await flush()
    expect(github.writes).toEqual(['status: 대회 1 → 진행 중', 'status: 대회 2 지움'])
    expect(github.file['DACON:2']!.hidden).toBe(true)
    expect(states.at(-1)).toEqual({ saving: false, error: null })
  })

  it('re-reads the version and writes once more when the sha is stale', async () => {
    const github = new FakeGitHub()
    github.sha = 'other-device'
    github.file = { 'DACON:9': { status: 'done', hidden: false, updated_at: 'x' } }
    github.failNext = new GitHubError(409)
    const states: SaveState[] = []
    const store = new StatusStore(github, new MemoryTokens(), (_file, state) => states.push(state))
    store.load({})
    store.setStatus('DACON:1', '대회 1', 'submitted')
    await flush()
    await flush()
    expect(github.reads).toBe(2)
    expect(github.writes).toEqual(['status: 대회 1 → 제출'])
    expect(github.file['DACON:9']!.status).toBe('done') // 다른 기기의 값은 남는다
    expect(states.at(-1)!.error).toBeNull()
  })

  it('reverts to the previous value and drops the queue when the commit fails', async () => {
    const github = new FakeGitHub()
    github.failNext = new GitHubError(401)
    let last: { file: StatusFile; state: SaveState } | null = null
    const store = new StatusStore(github, new MemoryTokens(), (file, state) => {
      last = { file, state }
    })
    store.load({ 'DACON:1': { status: 'not_started', hidden: false, updated_at: 'before' } })
    store.setStatus('DACON:1', '대회 1', 'done')
    store.hide('DACON:2', '대회 2')
    await flush()
    await flush()
    const { file, state } = last!
    expect(file['DACON:1']).toEqual({ status: 'not_started', hidden: false, updated_at: 'before' })
    expect(file['DACON:2']).toBeUndefined()
    expect(state.saving).toBe(false)
    expect(state.error!.status).toBe(401)
    expect(state.error!.change.kind).toBe('status')
    expect(github.writes).toEqual([])

    store.retry()
    await flush()
    await flush()
    expect(github.writes).toEqual(['status: 대회 1 → 완료'])
    expect(last!.state).toEqual({ saving: false, error: null })
  })

  it('gives up after a second version mismatch', async () => {
    const github = new FakeGitHub()
    github.sha = 'a'
    const original = github.writeStatusFile.bind(github)
    github.writeStatusFile = async (...args) => {
      github.sha = `moved-${github.reads}` // 읽을 때마다 판이 또 바뀐다
      return original(...args)
    }
    let last: SaveState | null = null
    const store = new StatusStore(github, new MemoryTokens(), (_file, state) => {
      last = state
    })
    store.load({})
    store.setStatus('DACON:1', '대회 1', 'done')
    await flush()
    await flush()
    expect(last!.error!.status).toBe(409)
    expect(github.reads).toBe(2)
  })
})
