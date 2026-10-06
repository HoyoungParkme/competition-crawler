/** CCR-UI-001#UI-2 설정 대화상자.
 *
 * 저장소에 쓸 GitHub 토큰을 넣거나 지운다(CCR-UC-001 UC-H2 · CCR-SEQ-001 SEQ-12). 저장 전에 반드시
 * 판 읽기로 검증하고, 값은 입력 칸에만 있다. 저장한 뒤 다시 보여 주지 않는다.
 */

import { useEffect, useState } from 'react'
import { GitHubError, readStatusVersion } from '../api/github'
import { OWNER, REPO } from '../config'
import type { TokenStore } from '../store/token'

interface Props {
  open: boolean
  tokens: TokenStore
  onClose: () => void
}

/** 401 · 403과 그 밖의 거절 코드를 사람 말로(CCR-API-001 2.3). 판 읽기의 404는 파일이 없다는 뜻이라 여기 오지 않는다 */
export function tokenProblem(status: number): string {
  if (status === 401) return '토큰이 틀렸거나 만료됐습니다 (401). 값을 다시 확인해 주세요.'
  if (status === 403)
    return '권한이 모자랍니다 (403). Contents 읽기·쓰기 권한이 있는지, 요청 한도에 닿지 않았는지 봐 주세요.'
  return `확인하지 못했습니다 (${status}). 잠시 뒤 다시 시도해 주세요.`
}

export function SettingsDialog({ open, tokens, onClose }: Props) {
  // 열릴 때마다 새로 마운트해 입력 칸과 알림이 비워진 채 시작한다
  return open ? <DialogBody tokens={tokens} onClose={onClose} /> : null
}

function DialogBody({ tokens, onClose }: Omit<Props, 'open'>) {
  const [value, setValue] = useState('')
  const [checking, setChecking] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)
  const [has, setHas] = useState(() => tokens.has())

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const onSave = async () => {
    const token = value.trim()
    if (token === '') {
      setProblem('토큰을 붙여 넣어 주세요.')
      return
    }
    setChecking(true)
    setProblem(null)
    try {
      await readStatusVersion(token) // 판 읽기로 검증한다. 404(파일 없음)도 통과다
      tokens.set(token)
      if (!tokens.has()) {
        setProblem('이 브라우저에서는 저장소(localStorage)에 쓸 수 없습니다. 읽기만 됩니다.')
        return
      }
      setValue('')
      onClose()
    } catch (error) {
      setProblem(
        error instanceof GitHubError
          ? tokenProblem(error.status)
          : '확인하지 못했습니다. 연결을 확인하고 다시 시도해 주세요.',
      )
    } finally {
      setChecking(false)
    }
  }

  const onClear = () => {
    tokens.clear()
    setHas(false)
    setValue('')
    setProblem(null)
  }

  return (
    <div className="cc-dim" data-el="0" onMouseDown={onClose}>
      <div
        className="cc-dlg"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cc-dlg-title"
        data-el="20"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="cc-dlg-head">
          <h2 id="cc-dlg-title" data-el="20.1">
            설정 — 저장소 토큰
          </h2>
          <div className="cc-grow" />
          <span className={`cc-ok${has ? '' : ' none'}`} data-el="20.6">
            {has ? (
              <>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M5 12l4 4 10-10" />
                </svg>
                토큰 있음 · 쓰기 가능
              </>
            ) : (
              '토큰 없음 · 읽기만'
            )}
          </span>
        </div>
        <p>
          상태를 바꾸거나 대회를 지우면 이 페이지가 저장소의 <code>data/status.json</code>에
          커밋합니다. 그러려면 GitHub 토큰이 필요하고, 토큰은 이 브라우저에만 저장됩니다.
        </p>
        <ol data-el="20.2">
          <li>
            GitHub → Settings → Developer settings → <strong>Fine-grained tokens</strong> → Generate
            new token
          </li>
          <li>
            Repository access: <strong>Only select repositories</strong> → {OWNER}/{REPO}
          </li>
          <li>
            Permissions → Repository → <strong>Contents: Read and write</strong>. 그 밖은 두지 않음.
            만료 기한을 둠
          </li>
        </ol>
        <label className="cc-lbl">
          토큰
          <input
            autoFocus
            className="cc-in"
            type="password"
            placeholder="github_pat_…"
            data-el="20.3"
            autoComplete="off"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') void onSave()
            }}
          />
          {problem && <span className="cc-problem">{problem}</span>}
        </label>
        <div className="cc-dlg-actions">
          {has && (
            <button className="cc-btn danger" type="button" data-el="20.5" onClick={onClear}>
              이 브라우저에서 토큰 지우기
            </button>
          )}
          <div className="cc-grow" />
          <button className="cc-btn ghost" type="button" data-el="20.7" onClick={onClose}>
            닫기
          </button>
          <button
            className="cc-btn primary"
            type="button"
            data-el="20.4"
            disabled={checking}
            onClick={() => void onSave()}
          >
            {checking ? '확인 중…' : '확인하고 저장'}
          </button>
        </div>
      </div>
    </div>
  )
}
