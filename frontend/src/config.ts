/** 저장소 · 브랜치 · 데이터 파일 경로 · raw와 Contents API 주소. 비밀값은 없다(CCR-INFRA-001 4.1). */

export const OWNER = 'HoyoungParkme'
export const REPO = 'competition-crawler'
export const BRANCH = 'main'
export const LIST_PATH = 'data/competitions.jsonl'
export const STATUS_PATH = 'data/status.json'

export const RAW_BASE = `https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}`
export const API_BASE = `https://api.github.com/repos/${OWNER}/${REPO}`
export const CONTENTS_URL = `${API_BASE}/contents/${STATUS_PATH}`

/** 브라우저 fetch의 시간 한도(ms). CCR-INFRA-001 8.5 */
export const FETCH_TIMEOUT_MS = 20_000

/** 캐시를 피하는 쿼리를 붙인 raw 주소(CCR-API-001 1.4). */
export function rawUrl(file: string, now: number = Date.now()): string {
  return `${RAW_BASE}/${file}?t=${now}`
}
