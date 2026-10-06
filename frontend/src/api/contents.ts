/** 노트북 페이지 서버로 상태 파일의 판을 읽고 쓴다(CCR-API-001 GET · PUT /api/contents/data/status.json).
 * GitHub Contents API와 같은 모양이다 — 판(sha)이 맞을 때만 쓰고, 어긋나면 409. 브라우저는 토큰을 갖지 않는다. */

import { COMMIT_AUTHOR, CONTENTS_URL, FETCH_TIMEOUT_MS } from '../config'
import type { StatusFile } from '../domain/types'
import { parseStatusFile } from './data'

/** 200 · 201이 아닌 응답. 가르는 일은 StatusStore가 한다(CCR-API-001 2.3). */
export class ContentsError extends Error {
  constructor(public readonly status: number) {
    super(`페이지 서버 응답 ${status}`)
    this.name = 'ContentsError'
  }
}

export interface StatusVersion {
  sha: string | null
  file: StatusFile
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

/** content(Base64)를 UTF-8 글자로. 줄바꿈이 섞여 있어도 읽는다. */
export function decodeContent(base64: string): string {
  const binary = atob(base64.replace(/\s+/g, ''))
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0))
  return new TextDecoder().decode(bytes)
}

/** 최신 판(sha)과 내용. 404면 파일이 아직 없는 것이다({sha: null, file: {}}). */
export async function readStatusVersion(): Promise<StatusVersion> {
  const response = await fetch(CONTENTS_URL, {
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
    cache: 'no-store',
  })
  if (response.status === 404) return { sha: null, file: {} }
  if (!response.ok) throw new ContentsError(response.status)
  const body = (await response.json()) as { sha: string; content: string }
  return { sha: body.sha, file: parseStatusFile(decodeContent(body.content)) }
}

/** 파일 전체를 한 커밋으로 올린다. sha가 null이면 새 파일. 돌려주는 값은 새 판(content.sha).
 * 작성자와 커미터는 저장소 주인의 noreply 주소다(CCR-API-001 1.4). */
export async function writeStatusFile(
  file: StatusFile,
  sha: string | null,
  message: string,
): Promise<string> {
  const payload: Record<string, unknown> = {
    message,
    content: encodeStatusFile(file),
    author: COMMIT_AUTHOR,
    committer: COMMIT_AUTHOR,
  }
  if (sha !== null) payload.sha = sha
  const response = await fetch(CONTENTS_URL, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
  })
  if (response.status !== 200 && response.status !== 201) throw new ContentsError(response.status)
  const body = (await response.json()) as { content: { sha: string } }
  return body.content.sha
}
