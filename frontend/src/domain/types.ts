/** 페이지가 읽고 쓰는 두 개념. 필드는 ERD(CCR-DOM-003 competitions · status)를 그대로 따른다. */

/** 목록 파일 한 줄(CCR-DOM-003 competitions). 배치의 ListEntry와 같은 필드다(CCR-DOM-002 5장 결정 9). */
export interface ListEntry {
  id: string
  source: string
  source_id: string
  title: string
  link: string
  start_date: string | null
  deadline: string | null
  collected_on: string
  reason: string
}

export type StatusValue = 'not_started' | 'in_progress' | 'submitted' | 'done'

export const STATUS_VALUES: readonly StatusValue[] = [
  'not_started',
  'in_progress',
  'submitted',
  'done',
]

/** 화면에 보이는 이름(CCR-API-001 4.2). */
export const STATUS_LABEL: Record<StatusValue, string> = {
  not_started: '시작 전',
  in_progress: '진행 중',
  submitted: '제출',
  done: '완료',
}

/** 상태 파일의 값 하나(CCR-DOM-003 status). */
export interface Status {
  status: StatusValue
  hidden: boolean
  updated_at: string
}

/** 상태 파일 전체. 키는 목록 항목의 id다. */
export type StatusFile = Record<string, Status>

export const DEFAULT_STATUS: Status = { status: 'not_started', hidden: false, updated_at: '' }

/** 소스 이름 여섯. 거르기(3.1)의 선택지이고 칩(7.3)의 값이다. */
export const SOURCE_NAMES: readonly string[] = [
  'event-us',
  'DACON',
  'Kaggle',
  'wevity',
  'AI팩토리',
  '콘테스트코리아',
]

/** 표의 한 줄. 목록 항목에 상태와 마감 지남을 합친 것. */
export interface Row {
  entry: ListEntry
  status: Status
  expired: boolean
}

export function isStatusValue(value: unknown): value is StatusValue {
  return typeof value === 'string' && (STATUS_VALUES as readonly string[]).includes(value)
}
