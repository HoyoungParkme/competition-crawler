/** 저장소 · 브랜치 · 데이터 파일 경로 · raw와 Contents API 주소, 상태 커밋의 작성자. 비밀값은 없다(CCR-INFRA-001 4.1). */

export const OWNER = 'HoyoungParkme'
export const REPO = 'competition-crawler'
export const BRANCH = 'main'

/** 상태 커밋의 작성자와 커미터. 저장소 주인의 noreply 주소다. 빼면 GitHub가 토큰 주인 계정의 기본
 * 이메일을 공개 커밋에 적는다(CCR-INFRA-001 8.11 · CCR-API-001 1.4). */
export const COMMIT_AUTHOR = {
  name: 'Hoyoung Park',
  email: '144880634+HoyoungParkme@users.noreply.github.com',
} as const
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
