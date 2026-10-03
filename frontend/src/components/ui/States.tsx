import type { ReactNode } from 'react'
import { Button } from './Button'

export function EmptyState({
  title,
  description,
  action,
  compact = false,
}: {
  title: string
  description: string
  action?: ReactNode
  compact?: boolean
}) {
  return (
    <div
      className={`flex flex-col items-start gap-3 border border-dashed border-[var(--color-line-strong)] ${
        compact ? 'p-5' : 'p-8'
      }`}
    >
      <p className="tech-label text-[var(--color-subtle)]">{title}</p>
      <p className="max-w-md text-sm leading-relaxed text-[var(--color-body)]">{description}</p>
      {action && <div className="pt-1">{action}</div>}
    </div>
  )
}

export function ErrorState({
  title = 'Request failed',
  message,
  onRetry,
  compact = false,
}: {
  title?: string
  message: string
  onRetry?: () => void
  compact?: boolean
}) {
  return (
    <div
      role="alert"
      className={`border border-[var(--color-critical)]/35 bg-[var(--color-critical)]/[0.04] ${
        compact ? 'p-4' : 'p-6'
      }`}
    >
      <div className="flex items-center gap-2.5">
        <span aria-hidden="true" className="block h-2 w-2 bg-[var(--color-critical)]" />
        <p className="tech-label text-[var(--color-critical)]">{title}</p>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-[var(--color-ink-fg)]">{message}</p>
      {onRetry && (
        <div className="mt-4">
          <Button size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}
    </div>
  )
}

/** Neutral loading placeholder — no fake progress, just a pending shape. */
export function LoadingRows({ rows = 3, label = 'Loading' }: { rows?: number; label?: string }) {
  return (
    <div role="status" aria-live="polite" className="space-y-px">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 border-b border-[var(--color-line)] py-4">
          <span className="block h-2 w-2 shrink-0 bg-[var(--color-line-strong)] animate-ac-pulse" />
          <span className="block h-2.5 flex-1 bg-[var(--color-line)] animate-ac-pulse" style={{ animationDelay: `${i * 120}ms` }} />
          <span className="block h-2.5 w-16 bg-[var(--color-line)] animate-ac-pulse" style={{ animationDelay: `${i * 120}ms` }} />
        </div>
      ))}
    </div>
  )
}
