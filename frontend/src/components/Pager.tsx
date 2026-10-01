/** 쪽 나누기 줄(CCR-UI-001 UI-1 13 · 13.1 ~ 13.5). 값과 콜백만 받고, 몇 쪽인지는 부모가 정한다. */

/** 한 번에 볼 개수(13.2)로 고를 수 있는 값과 기본값 */
export const PAGE_SIZES = [10, 20, 50, 100] as const
export const DEFAULT_PAGE_SIZE = 20

export interface PageOf<T> {
  items: T[]
  page: number
  pages: number
  from: number
  to: number
}

/** 순수 함수. 1부터 세는 쪽 번호를 1 ~ 마지막 쪽으로 맞추고 그 쪽의 줄을 자른다.
 * from · to는 1부터 센 줄 번호이고, 줄이 없으면 둘 다 0이다 */
export function paginate<T>(items: T[], page: number, size: number): PageOf<T> {
  const pages = Math.max(1, Math.ceil(items.length / size))
  const current = Math.min(Math.max(1, Math.floor(page)), pages)
  const start = (current - 1) * size
  const slice = items.slice(start, start + size)
  return {
    items: slice,
    page: current,
    pages,
    from: slice.length > 0 ? start + 1 : 0,
    to: start + slice.length,
  }
}

/** 순수 함수. 0부터 센 줄 번호가 든 쪽(1부터). 개수를 바꾸거나 접힌 줄로 넘어갈 때 쓴다 */
export function pageOfRow(index: number, size: number): number {
  return Math.floor(Math.max(0, index) / size) + 1
}

interface Props {
  total: number
  view: PageOf<unknown>
  pageSize: number
  onPage: (page: number) => void
  onPageSize: (size: number) => void
  el: string
  elRange: string
  elSize: string
  elPrev: string
  elPageNo: string
  elNext: string
}

export function Pager(props: Props) {
  const { total, view, pageSize, onPage, onPageSize } = props
  return (
    <nav className="cc-pager" data-el={props.el} aria-label="쪽 나누기">
      <span className="cc-range" data-el={props.elRange}>
        {total}개 중 {view.from}–{view.to}
      </span>
      <div className="cc-grow" />
      <label className="cc-size">
        한 번에
        <select
          className="cc-sel"
          data-el={props.elSize}
          value={pageSize}
          onChange={(event) => onPageSize(Number(event.target.value))}
        >
          {PAGE_SIZES.map((size) => (
            <option key={size} value={size}>
              {size}개
            </option>
          ))}
        </select>
      </label>
      <div className="cc-steps">
        <button
          className="cc-btn"
          type="button"
          data-el={props.elPrev}
          disabled={view.page <= 1}
          onClick={() => onPage(view.page - 1)}
        >
          이전
        </button>
        <span className="cc-pageno" data-el={props.elPageNo} aria-live="polite">
          {view.page} / {view.pages}
        </span>
        <button
          className="cc-btn"
          type="button"
          data-el={props.elNext}
          disabled={view.page >= view.pages}
          onClick={() => onPage(view.page + 1)}
        >
          다음
        </button>
      </div>
    </nav>
  )
}
