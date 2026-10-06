/** GitHub Contents API로 상태 파일의 판을 읽고 쓴다(CCR-API-001 GET · PUT contents/data/status.json). */

import { BRANCH, COMMIT_AUTHOR, CONTENTS_URL, FETCH_TIMEOUT_MS } from '../config'
import type { StatusFile } from '../domain/types'
import { parseStatusFile } from './data'

/** 200 · 201이 아닌 응답. 가르는 일은 StatusStore가 한다(CCR-API-001 2.3). */
export class GitHubError extends Error {
  constructor(
    public readonly status: number,
    public readonly rateLimited: boolean = false,
  ) {
    super(`GitHub 응답 ${status}`)
    this.name = 'GitHubError'
  }
}

export interface StatusVersion {
  sha: string | null
  file: StatusFile
}

/** 토큰은 Authorization 헤더에만 싣는다. 주소 · 콘솔 · 오류 메시지에 두지 않는다(CCR-INFRA-001 5.8). */
function headers(token: string): HeadersInit {
  return {
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    Authorization: `Bearer ${token}`,
  }
}

function errorOf(response: Response): GitHubError {
  const rateLimited =
    response.status === 403 && response.headers.get('x-ratelimit-remaining') === '0'
  return new GitHubError(response.status, rateLimited)
}

/** 상태 파일을 쓰는 모양. 키 정렬 · 두 칸 들여쓰기 · 끝 줄바꿈 · UTF-8 Base64(CCR-DOM-003 status). */
export function encodeStatusFile(file: StatusFile): string {
  const sorted: StatusFile = {}
  for (const key of Object.keys(file).sort()) sorted[key] = file[key]!
  const text = JSON.stringify(sorted, null, 2) + '\n'
  const bytes = new TextEncoder().encode(text)
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary)
}

/** Contents API의 content(76자마다 줄바꿈이 섞인 Base64)를 UTF-8 글자로. */
export function decodeContent(base64: string): string {
  const binary = atob(base64.replace(/\s+/g, ''))
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0))
  return new TextDecoder().decode(bytes)
}

/** 최신 판(sha)과 내용. 404면 파일이 아직 없는 것이다({sha: null, file: {}}). */
export async function readStatusVersion(token: string): Promise<StatusVersion> {
  const response = await fetch(`${CONTENTS_URL}?ref=${BRANCH}`, {
    headers: headers(token),
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
    cache: 'no-store',
  })
  if (response.status === 404) return { sha: null, file: {} }
  if (!response.ok) throw errorOf(response)
  const body = (await response.json()) as { sha: string; content: string }
  return { sha: body.sha, file: parseStatusFile(decodeContent(body.content)) }
}

/** 파일 전체를 한 커밋으로 올린다. sha가 null이면 새 파일. 돌려주는 값은 새 판(content.sha).
 * 작성자와 커미터는 저장소 주인의 noreply 주소다. 커미터를 빼면 토큰 주인 계정의 기본 이메일이
 * 공개 커밋에 남는다(CCR-API-001 1.4). */
export async function writeStatusFile(
  token: string,
  file: StatusFile,
  sha: string | null,
  message: string,
): Promise<string> {
  const payload: Record<string, unknown> = {
    message,
    content: encodeStatusFile(file),
    branch: BRANCH,
    author: COMMIT_AUTHOR,
    committer: COMMIT_AUTHOR,
  }
  if (sha !== null) payload.sha = sha
  const response = await fetch(CONTENTS_URL, {
    method: 'PUT',
    headers: { ...headers(token), 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
  })
  if (response.status !== 200 && response.status !== 201) throw errorOf(response)
  const body = (await response.json()) as { content: { sha: string } }
  return body.content.sha
}
