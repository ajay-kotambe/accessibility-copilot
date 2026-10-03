import { Link } from 'react-router-dom'
import type { Scan } from '../types'
import { duration, hostOf, pathOf, relativeDay } from '../lib/format'

/**
 * Technical history row: dividers, not cards.
 * Shared by the homepage section and the History page.
 */
export function ScanRow({ scan }: { scan: Scan }) {
  const complete = scan.status === 'COMPLETED'
  const failed = scan.status === 'FAILED'

  return (
    <li>
      <Link
        to={`/dashboard/${scan.id}`}
        className="grid grid-cols-1 items-baseline gap-x-6 gap-y-1.5 border-b border-[var(--color-line)] py-4 transition-colors duration-150 hover:bg-[var(--color-primary-soft)]/50 sm:grid-cols-[minmax(0,1fr)_6rem_5rem_6rem] sm:gap-4"
      >
        <span className="min-w-0">
          <span className="block truncate font-mono text-sm text-[var(--color-ink-fg)]">
            {hostOf(scan.url)}
            {pathOf(scan.url) && (
              <span className="text-[var(--color-subtle)]">{pathOf(scan.url)}</span>
            )}
          </span>
          {scan.error_message && failed && (
            <span className="mt-1 block truncate text-xs text-[var(--color-critical)]">
              {scan.error_message}
            </span>
          )}
        </span>

        <span className="tech-label text-[var(--color-subtle)]">{relativeDay(scan.started_at)}</span>

        <span className="font-mono text-sm tabular-nums text-[var(--color-ink-fg)]">
          {complete ? scan.score : '--'}
        </span>

        <span className="tech-label text-[var(--color-subtle)]">
          {failed
            ? 'Failed'
            : complete
              ? `${scan.issues.length} ${scan.issues.length === 1 ? 'issue' : 'issues'}`
              : duration(scan.started_at, scan.completed_at) === '--'
                ? scan.status
                : 'Pending'}
        </span>
      </Link>
    </li>
  )
}

export function ScanRowHeader() {
  return (
    <div
      aria-hidden="true"
      className="grid grid-cols-1 gap-x-6 gap-y-1 border-b border-[var(--color-line-strong)] pb-2.5 sm:grid-cols-[minmax(0,1fr)_6rem_5rem_6rem] sm:gap-4"
    >
      <span className="tech-label text-[var(--color-subtle)]">Target</span>
      <span className="tech-label text-[var(--color-subtle)]">Scanned</span>
      <span className="tech-label text-[var(--color-subtle)]">Score</span>
      <span className="tech-label text-[var(--color-subtle)]">Result</span>
    </div>
  )
}
