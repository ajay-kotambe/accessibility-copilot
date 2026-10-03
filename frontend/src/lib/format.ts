export function hostOf(url: string): string {
  try {
    return new URL(url).host
  } catch {
    return url.replace(/^https?:\/\//, '').split('/')[0] || url
  }
}

export function pathOf(url: string): string {
  try {
    const { pathname } = new URL(url)
    return pathname === '/' ? '' : pathname
  } catch {
    return ''
  }
}

/** Short, human label such as "Today" / "Yesterday" / "12 Mar". */
export function relativeDay(iso: string | null): string {
  if (!iso) return 'Unknown'
  const then = new Date(iso)
  if (Number.isNaN(then.getTime())) return 'Unknown'

  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const startOfThen = new Date(then.getFullYear(), then.getMonth(), then.getDate())
  const days = Math.round((startOfToday.getTime() - startOfThen.getTime()) / 86_400_000)

  if (days <= 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`

  return then.toLocaleDateString(undefined, { day: '2-digit', month: 'short' })
}

export function clockTime(iso: string | null): string {
  if (!iso) return '--:--'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '--:--'
  return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

/** Elapsed run time between two timestamps, e.g. "4.2s". */
export function duration(startIso: string | null, endIso: string | null): string {
  if (!startIso || !endIso) return '--'
  const start = new Date(startIso).getTime()
  const end = new Date(endIso).getTime()
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return '--'
  const seconds = (end - start) / 1000
  return seconds < 10 ? `${seconds.toFixed(1)}s` : `${Math.round(seconds)}s`
}

/** Turns an axios/fetch failure into a readable, non-technical message. */
export function errorMessage(error: unknown, fallback = 'Something went wrong.'): string {
  if (axiosLike(error)) {
    const data = error.response?.data
    if (data && typeof data.error === 'string' && data.error) return data.error
    if (data && typeof data.detail === 'string' && data.detail) return data.detail
    if (error.response?.status) return `Request failed (HTTP ${error.response.status}).`
    if (error.code === 'ERR_NETWORK') {
      return 'Cannot reach the scanner API. Confirm the backend is running.'
    }
  }
  if (error instanceof Error && error.message) return error.message
  return fallback
}

function axiosLike(error: unknown): error is {
  response?: { status?: number; data?: { error?: string; detail?: string } }
  code?: string
} {
  return typeof error === 'object' && error !== null && 'response' in error
}
