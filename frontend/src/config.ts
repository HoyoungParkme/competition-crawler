/** 데이터 파일 경로, 노트북 페이지 서버의 주소(같은 출처), 상태 커밋의 작성자. 비밀값은 없다(CCR-INFRA-001 4.1 · 8.11). */

/** 상태 커밋의 작성자와 커미터. 저장소 주인의 noreply 주소다(CCR-INFRA-001 8.11 · CCR-API-001 1.4). */
export const COMMIT_AUTHOR = {
  name: 'Hoyoung Park',
  email: '144880634+HoyoungParkme@users.noreply.github.com',
} as const
export const LIST_PATH = 'data/competitions.jsonl'
export const STATUS_PATH = 'data/status.json'

/** 상태 파일의 판 읽기·쓰기. 페이지 서버가 GitHub Contents API와 같은 모양으로 받는다(CCR-API-001 3.3) */
export const CONTENTS_URL = `/api/contents/${STATUS_PATH}`

/** 브라우저 fetch의 시간 한도(ms). CCR-INFRA-001 8.5 */
export const FETCH_TIMEOUT_MS = 20_000

/** 페이지 서버가 원본 main에서 바로 내는 데이터 파일 주소. 브라우저 캐시를 피하는 쿼리를 붙인다(CCR-API-001 1.4). */
export function dataUrl(file: string, now: number = Date.now()): string {
  return `/${file}?t=${now}`
}
