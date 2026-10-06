/** 상태 파일에 쓰는 유일한 길(CCR-DOM-002 StatusStore · CCR-UC-001 UC-H1 · CCR-SEQ-001 SEQ-11).
 *
 * 화면을 먼저 바꾸고 커밋한다. 한 번에 요청 하나. 커밋마다 판 읽기부터 하고 이번 바꿈만 얹는다.
 * 판이 어긋나면(409 · 422) 한 번만 다시 쓴다. 그래도 실패하거나 다른 오류면 되돌리고 알린다.
 */

import {
  GitHubError,
  readStatusVersion as defaultRead,
  writeStatusFile as defaultWrite,
  type StatusVersion,
} from '../api/github'
import {
  DEFAULT_STATUS,
  STATUS_LABEL,
  type Status,
  type StatusFile,
  type StatusValue,
} from '../domain/types'
import type { TokenStore } from './token'

export type ChangeKind = 'status' | 'hide' | 'restore' | 'star' | 'unstar'

export interface Change {
  kind: ChangeKind
  id: string
  title: string
  value?: StatusValue
  /** 바꾸기 전 값. 없었으면 undefined. 되돌릴 때 쓴다 */
  before: Status | undefined
  /** 바꾼 시각(UTC, 초 단위). updated_at에 적는다 */
  at: string
}

export interface SaveError {
  status: number | null
  rateLimited: boolean
  /** 되돌린 바꿈. 화면이 「다시 시도」(12.2)를 보인다 */
  change: Change
}

export interface SaveState {
  saving: boolean
  error: SaveError | null
}

/** 페이지가 쓰는 두 요청. 테스트에서 바꿔 끼운다 */
export interface GitHubApi {
  readStatusVersion(token: string): Promise<StatusVersion>
  writeStatusFile(
    token: string,
    file: StatusFile,
    sha: string | null,
    message: string,
  ): Promise<string>
}

export const defaultGitHub: GitHubApi = {
  readStatusVersion: defaultRead,
  writeStatusFile: defaultWrite,
}

const TITLE_MAX = 60

/** 지금 시각을 UTC 초 단위로(CCR-DOM-003 status.updated_at). */
export function nowIso(date: Date = new Date()): string {
  return date.toISOString().replace(/\.\d{3}Z$/, 'Z')
}

/** 바꿈의 종류마다 바뀌는 필드 */
function changedFields(change: Change, current: Status): Partial<Status> {
  switch (change.kind) {
    case 'status':
      return { status: change.value ?? current.status }
    case 'hide':
      return { hidden: true }
    case 'restore':
      return { hidden: false }
    case 'star':
      return { starred: true }
    case 'unstar':
      return { starred: false }
  }
}

/** 이번 바꿈만 그 대회의 값에 얹는다. 다른 대회의 값은 그대로다. 되살리기는 hidden=false로 둔다 */
export function mergeChange(file: StatusFile, change: Change, now: string): StatusFile {
  const current = file[change.id] ?? DEFAULT_STATUS
  const next: Status = { ...current, ...changedFields(change, current), updated_at: now }
  return { ...file, [change.id]: next }
}

/** `status: <대회명> → <상태>` · `지움` · `되살림` · `별표` · `별표 뗌`. 대회명은 60자 */
export function commitMessage(change: Change): string {
  const title = change.title.length > TITLE_MAX ? change.title.slice(0, TITLE_MAX) : change.title
  if (change.kind === 'hide') return `status: ${title} 지움`
  if (change.kind === 'restore') return `status: ${title} 되살림`
  if (change.kind === 'star') return `status: ${title} 별표`
  if (change.kind === 'unstar') return `status: ${title} 별표 뗌`
  return `status: ${title} → ${STATUS_LABEL[change.value ?? 'not_started']}`
}

function isVersionMismatch(error: unknown): boolean {
  return error instanceof GitHubError && (error.status === 409 || error.status === 422)
}

export class StatusStore {
  private file: StatusFile = {}
  private queue: Change[] = []
  private busy = false
  private lastFailed: Change | null = null

  constructor(
    private readonly github: GitHubApi,
    private readonly tokens: TokenStore,
    private readonly onChange: (file: StatusFile, save: SaveState) => void,
  ) {}

  /** raw로 읽은 상태 파일을 화면의 기준으로 둔다. 쓰기의 기준은 커밋마다 새로 읽는다 */
  load(file: StatusFile): void {
    this.file = file
  }

  setStatus(id: string, title: string, value: StatusValue): void {
    this.enqueue({ kind: 'status', id, title, value, before: this.file[id], at: nowIso() })
  }

  hide(id: string, title: string): void {
    this.enqueue({ kind: 'hide', id, title, before: this.file[id], at: nowIso() })
  }

  restore(id: string, title: string): void {
    this.enqueue({ kind: 'restore', id, title, before: this.file[id], at: nowIso() })
  }

  star(id: string, title: string): void {
    this.enqueue({ kind: 'star', id, title, before: this.file[id], at: nowIso() })
  }

  unstar(id: string, title: string): void {
    this.enqueue({ kind: 'unstar', id, title, before: this.file[id], at: nowIso() })
  }

  /** 마지막으로 실패한 바꿈을 다시 보낸다(UI-1 12.2). 최신 판을 다시 읽어 같은 바꿈을 얹는다 */
  retry(): void {
    const change = this.lastFailed
    if (change === null) return
    this.lastFailed = null
    this.enqueue({ ...change, before: this.file[change.id], at: nowIso() })
  }

  private enqueue(change: Change): void {
    this.file = mergeChange(this.file, change, change.at)
    this.onChange(this.file, { saving: true, error: null })
    this.queue.push(change)
    if (!this.busy) void this.drain()
  }

  private async drain(): Promise<void> {
    this.busy = true
    try {
      while (this.queue.length > 0) {
        const change = this.queue.shift()!
        try {
          await this.commit(change)
        } catch (error) {
          this.revert(change, error)
          return
        }
      }
      this.onChange(this.file, { saving: false, error: null })
    } finally {
      this.busy = false
    }
  }

  private async commit(change: Change): Promise<void> {
    const token = this.tokens.get()
    if (token === null) throw new GitHubError(401)
    const message = commitMessage(change)
    // 응답의 새 판(content.sha)은 기억해 둘 곳이 없다. 다음 커밋도 판 읽기부터 하고, 판은 로그에 찍지 않는다
    try {
      await this.write(token, change, message)
    } catch (error) {
      if (!isVersionMismatch(error)) throw error
      // 판이 어긋났다. 최신 판을 다시 읽고 한 번 더 쓴다(UC-H1 4a). 다시 실패하면 그대로 던진다
      await this.write(token, change, message)
    }
  }

  private async write(token: string, change: Change, message: string): Promise<string> {
    const version = await this.github.readStatusVersion(token)
    const merged = mergeChange(version.file, change, change.at)
    return this.github.writeStatusFile(token, merged, version.sha, message)
  }

  /** 바꾸기 전 값으로 되돌린다. 큐에 남은 바꿈도 버리고 되돌린 뒤 함께 알린다 */
  private revert(change: Change, error: unknown): void {
    const dropped = [change, ...this.queue.splice(0)]
    for (const item of dropped.reverse()) {
      const file = { ...this.file }
      if (item.before === undefined) delete file[item.id]
      else file[item.id] = item.before
      this.file = file
    }
    this.lastFailed = change
    const status = error instanceof GitHubError ? error.status : null
    const rateLimited = error instanceof GitHubError && error.rateLimited
    this.onChange(this.file, { saving: false, error: { status, rateLimited, change } })
  }
}
