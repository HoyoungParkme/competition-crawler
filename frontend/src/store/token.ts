/** 페이지 토큰. localStorage의 키 하나에만 둔다(CCR-INFRA-001 5.8 · CCR-DOM-002 TokenStore). */

const KEY = 'ccr.token'

export class TokenStore {
  /** localStorage에 닿지 못하는 브라우저면 null. 페이지는 읽기만 되는 상태로 돈다. */
  get(): string | null {
    try {
      const value = window.localStorage.getItem(KEY)
      return value && value.trim() !== '' ? value : null
    } catch {
      return null
    }
  }

  /** 조용히 실패할 수 있다. 그 뒤 has()가 거짓이다. */
  set(token: string): void {
    try {
      window.localStorage.setItem(KEY, token.trim())
    } catch {
      /* 사생활 보호 모드 등. 저장하지 못한 채로 둔다 */
    }
  }

  clear(): void {
    try {
      window.localStorage.removeItem(KEY)
    } catch {
      /* 위와 같다 */
    }
  }

  has(): boolean {
    return this.get() !== null
  }
}
