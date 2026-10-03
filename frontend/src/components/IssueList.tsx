import type { Issue } from '../types'
import { sortBySeverity } from '../lib/scan'
import { SeverityBadge } from './ui/SeverityBadge'

/**
 * Technical issue rows with dividers rather than cards.
 * Rendered as a list; when selectable, each row is a real button so it
 * is reachable and operable by keyboard.
 */
export function IssueList({
  issues,
  selectedId,
  onSelect,
  limit,
}: {
  issues: Issue[]
  selectedId?: number | null
  onSelect?: (issue: Issue) => void
  limit?: number
}) {
  const sorted = sortBySeverity(issues)
  const shown = typeof limit === 'number' ? sorted.slice(0, limit) : sorted

  if (shown.length === 0) {
    return (
      <p className="border border-dashed border-[var(--color-line-strong)] p-6 text-sm text-[var(--color-body)]">
        No violations matched the enabled rule set.
      </p>
    )
  }

  return (
    <ul className="divide-y divide-[var(--color-line)] border-y border-[var(--color-line)]">
      {shown.map((issue) => {
        const selected = issue.id === selectedId
        const body = (
          <>
            <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
              <SeverityBadge severity={issue.severity} />
              <span className="font-mono text-xs text-[var(--color-subtle)]">
                {issue.category || 'General'}
              </span>
            </div>
            <p className="mt-3 text-[0.9375rem] leading-snug text-[var(--color-ink-fg)]">
              {issue.rule_id}
            </p>
            <p className="mt-1.5 text-sm leading-relaxed text-[var(--color-body)]">
              {issue.description}
            </p>
            {issue.selector && (
              <p className="mt-3 truncate font-mono text-xs text-[var(--color-subtle)]">
                {issue.selector}
              </p>
            )}
          </>
        )

        if (!onSelect) {
          return (
            <li key={issue.id} className="py-5">
              {body}
            </li>
          )
        }

        return (
          <li key={issue.id}>
            <button
              type="button"
              onClick={() => onSelect(issue)}
              aria-current={selected ? 'true' : undefined}
              className={`block w-full px-3 py-5 text-left transition-colors duration-150 hover:bg-[var(--color-primary-soft)]/60 ${
                selected ? 'bg-[var(--color-primary-soft)]' : ''
              }`}
            >
              {body}
            </button>
          </li>
        )
      })}
    </ul>
  )
}
