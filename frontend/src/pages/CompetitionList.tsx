/** CCR-UI-001#UI-1 대회 목록.
 *
 * 두 파일을 읽어 Row로 합쳐 그린다(CCR-UC-001 UC-A2 · CCR-SEQ-001 SEQ-11). 데이터를 읽는 곳은 이
 * 컴포넌트뿐이고, 자식에게는 값과 콜백만 내려 준다. 쓰는 조작 셋은 모두 StatusStore로 간다.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { DataReadError, readListFile, readStatusFile } from '../api/data'
import { readStatusVersion, type StatusVersion } from '../api/github'
import { CompetitionTable } from '../components/CompetitionTable'
import { DEFAULT_FILTERS, FilterBar, type Filters } from '../components/FilterBar'
import {
  EmptyState,
  NoTokenNotice,
  ReadErrorNotice,
  SaveFailedNotice,
  SavingToast,
} from '../components/Notice'
import { DEFAULT_PAGE_SIZE, PAGE_SIZES, Pager, pageOfRow, paginate } from '../components/Pager'
import { SettingsDialog } from '../components/SettingsDialog'
import { BRANCH, OWNER, REPO } from '../config'
import {
  DEFAULT_STATUS,
  type ListEntry,
  type Row,
  type StatusFile,
  type StatusValue,
} from '../domain/types'
import { defaultGitHub, StatusStore, type SaveState } from '../store/status'
import { TokenStore } from '../store/token'

const FILTERS_KEY = 'ccr.filters'
const PAGE_SIZE_KEY = 'ccr.pageSize'

/** 브라우저의 KST 날짜(YYYY-MM-DD). 마감 지남과 D-n의 기준이다 */
export function kstToday(now: Date = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now)
}

/** 접수마감일이 오늘보다 이르면 마감 지남. 마감일이 없으면 지나지 않은 것이다 */
export function isExpired(entry: ListEntry, today: string): boolean {
  return entry.deadline !== null && entry.deadline < today
}

/** 화면에 보일 상태 파일. 토큰이 있으면 Contents API의 판 읽기로 받는다. raw는 CDN이 5분 캐시해
 * 방금 바꾼 값이 옛 값으로 보이기 때문이다(CCR-INFRA-001 6.4). 판 읽기가 실패하면 raw로 받고,
 * 토큰 문제는 저장할 때 드러난다 */
export async function readStatusForView(
  token: string | null,
  readVersion: (token: string) => Promise<StatusVersion> = readStatusVersion,
  readRaw: () => Promise<StatusFile> = readStatusFile,
): Promise<StatusFile> {
  if (token === null) return readRaw()
  try {
    return (await readVersion(token)).file
  } catch {
    return readRaw()
  }
}

/** 접수마감일 오름차순. 없으면 맨 뒤. 같은 마감일이면 대회명 순. 원본은 바꾸지 않는다 */
export function sortByDeadline(rows: Row[]): Row[] {
  return [...rows].sort((a, b) => {
    const da = a.entry.deadline
    const db = b.entry.deadline
    if (da === null && db !== null) return 1
    if (da !== null && db === null) return -1
    if (da !== null && db !== null && da !== db) return da < db ? -1 : 1
    return a.entry.title.localeCompare(b.entry.title, 'ko')
  })
}

function readFilters(): Filters {
  try {
    const raw = window.localStorage.getItem(FILTERS_KEY)
    if (!raw) return DEFAULT_FILTERS
    const data = JSON.parse(raw) as Partial<Filters>
    return { ...DEFAULT_FILTERS, ...data }
  } catch {
    return DEFAULT_FILTERS
  }
}

function writeFilters(filters: Filters): void {
  try {
    window.localStorage.setItem(FILTERS_KEY, JSON.stringify(filters))
  } catch {
    /* 브라우저에만 기억한다. 못 하면 그만이다 */
  }
}

/** 한 번에 볼 개수(13.2). 고를 수 있는 값이 아니면 기본값이다 */
function readPageSize(): number {
  try {
    const size = Number(window.localStorage.getItem(PAGE_SIZE_KEY))
    return (PAGE_SIZES as readonly number[]).includes(size) ? size : DEFAULT_PAGE_SIZE
  } catch {
    return DEFAULT_PAGE_SIZE
  }
}

function writePageSize(size: number): void {
  try {
    window.localStorage.setItem(PAGE_SIZE_KEY, String(size))
  } catch {
    /* 브라우저에만 기억한다. 못 하면 그만이다 */
  }
}

/** 두 파일을 함께 받는다(SEQ-11 2 · 3). 목록 파일은 raw, 상태 파일은 토큰이 있으면 판 읽기다 */
function readFiles(token: string | null): Promise<[ListEntry[], StatusFile]> {
  return Promise.all([readListFile(), readStatusForView(token)])
}

function formatTime(date: Date): string {
  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Seoul',
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date)
}

export function CompetitionList() {
  const tokens = useMemo(() => new TokenStore(), [])
  const [entries, setEntries] = useState<ListEntry[]>([])
  const [statusFile, setStatusFile] = useState<StatusFile>({})
  const [loading, setLoading] = useState(true)
  const [readError, setReadError] = useState<string | null>(null)
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null)
  const [filters, setFilters] = useState<Filters>(readFilters)
  const [foldOpen, setFoldOpen] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(readPageSize)
  const tableTop = useRef<HTMLDivElement>(null)
  const [save, setSave] = useState<SaveState>({ saving: false, error: null })
  const [noToken, setNoToken] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [hasToken, setHasToken] = useState(() => tokens.has())
  const today = useMemo(() => kstToday(), [])

  const storeRef = useRef<StatusStore | null>(null)
  if (storeRef.current === null) {
    storeRef.current = new StatusStore(defaultGitHub, tokens, (file, state) => {
      setStatusFile(file)
      setSave(state)
    })
  }
  const store = storeRef.current

  /** 두 파일을 읽는다. 상태는 응답이 온 뒤에만 바꾼다 */
  /** 읽은 두 파일을 화면에 올린다. 응답 콜백에서만 부른다 */
  const applyFiles = useCallback(
    ([list, status]: [ListEntry[], StatusFile]) => {
      setEntries(list)
      setStatusFile(status)
      store.load(status)
      setReadError(null)
      setUpdatedAt(new Date())
      setLoading(false)
    },
    [store],
  )
  const applyError = useCallback((error: unknown) => {
    setReadError(error instanceof DataReadError ? error.message : '파일을 읽지 못했습니다')
    setLoading(false)
  }, [])

  /** 새로 고침(2). 읽는 동안을 표시하고 두 파일을 다시 읽는다 */
  const refresh = () => {
    setLoading(true)
    readFiles(tokens.get()).then(applyFiles, applyError)
  }

  useEffect(() => {
    readFiles(tokens.get()).then(applyFiles, applyError)
  }, [applyFiles, applyError, tokens])

  useEffect(() => {
    writeFilters(filters)
  }, [filters])

  useEffect(() => {
    writePageSize(pageSize)
  }, [pageSize])

  const { active, folded } = useMemo(() => {
    const all: Row[] = entries.map((entry) => ({
      entry,
      status: statusFile[entry.id] ?? DEFAULT_STATUS,
      expired: isExpired(entry, today),
    }))
    const filtered = all.filter(
      (row) =>
        (filters.source === '' || row.entry.source === filters.source) &&
        (filters.status === '' || row.status.status === filters.status) &&
        (!filters.starredOnly || row.status.starred),
    )
    const sorted = sortByDeadline(filtered)
    return {
      active: sorted.filter((row) => !row.expired && !row.status.hidden),
      folded: sorted.filter((row) => row.expired || row.status.hidden),
    }
  }, [entries, statusFile, filters, today])

  /** 쪽 나누기(13). 펼쳐 있으면 접힌 줄이 열린 줄 뒤에 이어진다 */
  const open = foldOpen || filters.showAll
  const shown = useMemo(() => (open ? [...active, ...folded] : active), [open, active, folded])
  const view = paginate(shown, page, pageSize)

  /** 거르기를 바꾸면 첫 쪽으로 */
  const changeFilters = (next: Filters) => {
    setFilters(next)
    setPage(1)
  }
  /** 개수를 바꾸면 보던 첫 줄이 든 쪽으로 */
  const changePageSize = (size: number) => {
    setPage(pageOfRow(view.from - 1, size))
    setPageSize(size)
  }
  /** 이전 · 다음(13.3 · 13.5). 표 머리가 화면 위로 지나갔으면 표 머리로 올린다 */
  const goToPage = (next: number) => {
    setPage(next)
    const top = tableTop.current
    if (top && top.getBoundingClientRect().top < 0) top.scrollIntoView({ block: 'start' })
  }
  /** 접힌 구역(9)을 펼치면 접힌 줄이 시작하는 쪽으로 */
  const toggleFold = () => {
    if (!open && folded.length > 0) setPage(pageOfRow(active.length, pageSize))
    setFoldOpen((value) => !value)
  }

  const requireToken = (action: () => void) => {
    if (!tokens.has()) {
      setNoToken(true)
      return
    }
    setNoToken(false)
    action()
  }
  const onStatus = (id: string, title: string, value: StatusValue) =>
    requireToken(() => store.setStatus(id, title, value))
  const onHide = (id: string, title: string) => requireToken(() => store.hide(id, title))
  const onRestore = (id: string, title: string) => requireToken(() => store.restore(id, title))
  const onStar = (id: string, title: string, starred: boolean) =>
    requireToken(() => (starred ? store.star(id, title) : store.unstar(id, title)))

  const openSettings = () => setDialogOpen(true)
  const closeSettings = useCallback(() => {
    setDialogOpen(false)
    const has = tokens.has()
    setHasToken(has)
    if (has) setNoToken(false)
  }, [tokens])

  const empty = !loading && readError === null && entries.length === 0

  return (
    <>
      <div className="cc-page" data-el="0" inert={dialogOpen || undefined}>
        <header className="cc-top" data-el="1">
          <div className="cc-titles">
            <h1 data-el="1.1">대회 목록</h1>
            <span className="cc-sub" data-el="1.2">
              마감일 순 ·{' '}
              {updatedAt ? `${formatTime(updatedAt)} 갱신` : loading ? '읽는 중' : '갱신 안 됨'} ·
              열린 대회 {active.length}
            </span>
          </div>
          <div className="cc-grow" />
          {save.saving && <SavingToast el="8" />}
          <button
            className="cc-btn ghost"
            data-el="2"
            type="button"
            onClick={refresh}
            disabled={loading}
          >
            새로 고침
          </button>
          <button
            className={`cc-btn${hasToken ? '' : ' dot'}`}
            data-el="6"
            type="button"
            aria-label="설정"
            title={hasToken ? '설정' : '설정 — 토큰이 없어 읽기만 됩니다'}
            onClick={openSettings}
          >
            설정
          </button>
        </header>

        {readError !== null && <ReadErrorNotice message={readError} onRefresh={refresh} />}
        {noToken && <NoTokenNotice el="11" elOpen="11.1" onOpenSettings={openSettings} />}
        {save.error !== null && (
          <SaveFailedNotice
            el="12"
            elOpen="12.1"
            elRetry="12.2"
            error={save.error}
            onOpenSettings={openSettings}
            onRetry={() => store.retry()}
          />
        )}

        <FilterBar
          filters={filters}
          onChange={changeFilters}
          el="3"
          elSource="3.1"
          elStatus="3.2"
          elShowAll="3.3"
          elStarredOnly="3.4"
        />

        <div ref={tableTop} />
        {empty ? (
          <EmptyState el="10" />
        ) : (
          <CompetitionTable
            rows={view.items}
            expiredCount={folded.filter((row) => row.expired && !row.status.hidden).length}
            hiddenCount={folded.filter((row) => row.status.hidden).length}
            foldOpen={open}
            pager={
              shown.length > 0 && (
                <Pager
                  total={shown.length}
                  view={view}
                  pageSize={pageSize}
                  onPage={goToPage}
                  onPageSize={changePageSize}
                  el="13"
                  elRange="13.1"
                  elSize="13.2"
                  elPrev="13.3"
                  elPageNo="13.4"
                  elNext="13.5"
                />
              )
            }
            today={today}
            onToggleFold={toggleFold}
            onStatus={onStatus}
            onHide={onHide}
            onRestore={onRestore}
            onStar={onStar}
            el="7"
            elDue="7.1"
            elTitle="7.2"
            elSource="7.3"
            elStatus="7.4"
            elHide="7.5"
            elReason="7.6"
            elStar="7.7"
            elFold="9"
            elRestore="9.1"
          />
        )}

        <div className="cc-grow" />
        <div className="cc-foot" data-el="1.3">
          <span>목록은 배치가 매일 08:50에 올리고, 상태는 이 페이지가 저장소에 저장한다</span>
          <span>
            {OWNER}/{REPO} · {BRANCH}
          </span>
        </div>
      </div>
      <SettingsDialog open={dialogOpen} tokens={tokens} onClose={closeSettings} />
    </>
  )
}
