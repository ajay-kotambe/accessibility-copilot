import type { Issue, Severity } from '../types'
import { SEVERITY_ORDER, countBySeverity, scoreTone } from '../lib/scan'

/**
 * Minimal score readout — no donut chart.
 * Values always come from the backend scan record.
 */
export function ScorePanel({
  score,
  issues,
}: {
  score: number | null
  issues: Issue[]
}) {
  const counts = countBySeverity(issues)
  const tone = score === null ? 'fair' : scoreTone(score)
  const toneColor = { good: 'text-[var(--color-primary-text)]', fair: 'text-[var(--color-ink-fg)]', poor: 'text-[var(--color-critical)]' }[tone]

  return (
    <div>
      <p className="tech-label text-[var(--color-subtle)]">Accessibility score</p>

      <div className="mt-5 flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <span className={`font-mono text-6xl leading-none tracking-tight sm:text-7xl ${toneColor}`}>
          {score ?? '--'}
        </span>
        <span className="font-mono text-lg text-[var(--color-subtle)]">/ 100</span>
      </div>

      <ScoreBar score={score} />

      <p className="mt-6 text-sm text-[var(--color-body)]">
        {issues.length} {issues.length === 1 ? 'issue' : 'issues'} detected
      </p>

      <ul className="mt-5 divide-y divide-[var(--color-line)] border-y border-[var(--color-line)]">
        {SEVERITY_ORDER.map((severity: Severity) => (
          <li key={severity} className="flex items-center justify-between py-3">
            <SeverityCountLabel severity={severity} />
            <span className="font-mono text-sm tabular-nums text-[var(--color-ink-fg)]">
              {counts[severity]}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function ScoreBar({ score }: { score: number | null }) {
  const value = Math.max(0, Math.min(100, score ?? 0))
  const color = score === null ? 'bg-[var(--color-line-strong)]' : scoreTone(score) === 'poor' ? 'bg-[var(--color-critical)]' : 'bg-[var(--color-primary)]'

  return (
    <div
      className="mt-6 h-1 w-full bg-[var(--color-line)]"
      role="meter"
      aria-valuenow={score ?? undefined}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Accessibility score out of 100"
    >
      <div className={`h-full transition-[width] duration-500 ${color}`} style={{ width: `${value}%` }} />
    </div>
  )
}

function SeverityCountLabel({ severity }: { severity: Severity }) {
  const dot = {
    CRITICAL: 'bg-[var(--color-critical)]',
    SERIOUS: 'bg-[var(--color-serious)]',
    MODERATE: 'bg-[var(--color-moderate)]',
    MINOR: 'bg-[var(--color-minor)]',
  }[severity]

  return (
    <span className="flex items-center gap-2.5">
      <span aria-hidden="true" className={`h-2 w-2 shrink-0 ${dot}`} />
      <span className="tech-label text-[var(--color-body)]">{severity}</span>
    </span>
  )
}
