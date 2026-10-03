import type { Severity } from '../../types'
import { SEVERITY_VAR } from '../../lib/scan'

/**
 * Minimal severity indicator: a solid marker plus a monospace label.
 * Colour is never the only signal — the word is always present.
 */
export function SeverityBadge({
  severity,
  className = '',
}: {
  severity: Severity
  className?: string
}) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <span
        aria-hidden="true"
        className="block h-2.5 w-2.5 shrink-0"
        style={{ backgroundColor: SEVERITY_VAR[severity] }}
      />
      <span className="tech-label" style={{ color: SEVERITY_VAR[severity] }}>
        {severity}
      </span>
    </span>
  )
}
