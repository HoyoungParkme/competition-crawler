/** 노트북 페이지 서버에서 목록 파일과 상태 파일을 읽는다(CCR-API-001 GET /data/… · 1.4 · 2.3). */

import { FETCH_TIMEOUT_MS, LIST_PATH, STATUS_PATH, dataUrl } from '../config'
import { isStatusValue, type ListEntry, type Status, type StatusFile } from '../domain/types'

/** 두 번 받아도 읽지 못했다(CCR-UC-001 UC-A2 1b). */
export class DataReadError extends Error {
  constructor(
    public readonly file: string,
    public readonly status: number | null,
  ) {
    super(status === null ? `${file}을 받지 못했다` : `${file}을 받지 못했다 (${status})`)
    this.name = 'DataReadError'
  }
}

const REQUIRED: readonly (keyof ListEntry)[] = [
  'id',
  'source',
  'source_id',
  'title',
  'link',
  'collected_on',
]

function asDate(value: unknown): string | null {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : null
}

function toEntry(data: unknown): ListEntry | null {
  if (typeof data !== 'object' || data === null || Array.isArray(data)) return null
  const record = data as Record<string, unknown>
  for (const name of REQUIRED) {
    const value = record[name]
    if (typeof value !== 'string' || value === '') return null
  }
  return {
    id: record.id as string,
    source: record.source as string,
    source_id: record.source_id as string,
    title: record.title as string,
    link: record.link as string,
    start_date: asDate(record.start_date),
    deadline: asDate(record.deadline),
    collected_on: record.collected_on as string,
    reason: typeof record.reason === 'string' ? record.reason : '',
  }
}

/** 목록 파일(JSON Lines)을 항목으로. 읽히지 않는 줄은 건너뛰고, 식별자가 겹치면 앞의 것을 쓴다. */
export function parseListFile(text: string): ListEntry[] {
  const seen = new Set<string>()
  const out: ListEntry[] = []
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    let data: unknown
    try {
      data = JSON.parse(line)
    } catch {
      continue
    }
    const entry = toEntry(data)
    if (entry === null || seen.has(entry.id)) continue
    seen.add(entry.id)
    out.push(entry)
  }
  return out
}

function toStatus(value: unknown): Status | null {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return null
  const record = value as Record<string, unknown>
  if (!isStatusValue(record.status) || typeof record.hidden !== 'boolean') return null
  return {
    status: record.status,
    hidden: record.hidden,
    starred: typeof record.starred === 'boolean' ? record.starred : false,
    updated_at: typeof record.updated_at === 'string' ? record.updated_at : '',
  }
}

/** 상태 파일을 객체로. 객체가 아니면 DataReadError, 모양이 다른 값은 뺀다(CCR-DOM-003 status). */
export function parseStatusFile(text: string): StatusFile {
  if (text.trim() === '') return {}
  let data: unknown
  try {
    data = JSON.parse(text)
  } catch {
    throw new DataReadError(STATUS_PATH, null)
  }
  if (typeof data !== 'object' || data === null || Array.isArray(data)) {
    throw new DataReadError(STATUS_PATH, null)
  }
  const out: StatusFile = {}
  for (const [id, value] of Object.entries(data as Record<string, unknown>)) {
    const status = toStatus(value)
    if (status !== null) out[id] = status
  }
  return out
}

/** 데이터 파일 하나. 404면 null. 5xx · 연결 오류 · 시간 초과면 한 번 다시 받는다. */
async function fetchData(file: string): Promise<string | null> {
  let lastStatus: number | null = null
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const response = await fetch(dataUrl(file), {
        signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
        cache: 'no-store',
      })
      if (response.status === 404) return null
      if (response.ok) return await response.text()
      lastStatus = response.status
      if (response.status < 500) break
    } catch {
      lastStatus = null
    }
  }
  throw new DataReadError(file, lastStatus)
}

/** 목록 파일을 읽는다. 없으면(404) 빈 목록(첫 실행 전, UI-1 10). */
export async function readListFile(): Promise<ListEntry[]> {
  const text = await fetchData(LIST_PATH)
  return text === null ? [] : parseListFile(text)
}

/** 상태 파일을 읽는다. 없으면 빈 객체. 표시용이고 쓰기의 기준이 아니다(CCR-INFRA-001 6.4). */
export async function readStatusFile(): Promise<StatusFile> {
  const text = await fetchData(STATUS_PATH)
  return text === null ? {} : parseStatusFile(text)
}
