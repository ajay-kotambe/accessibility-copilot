import type { ScanStatus, Severity } from '../types'

/* ============================================================
   Scan pipeline — driven exclusively by real backend status.
   Source of truth: backend/scanner/models.py Scan.STATUS_CHOICES
   ============================================================ */

export interface PipelineStep {
  key: string
  label: string
  /** Statuses in which this step is the one currently executing. */
  activeDuring: ScanStatus[]
}

export const PIPELINE_STEPS: PipelineStep[] = [
  {
    key: 'connect',
    label: 'Connecting to scanner',
    activeDuring: ['QUEUED', 'CONNECTING'],
  },
  {
    key: 'render',
    label: 'Loading and rendering website',
    activeDuring: ['LOADING'],
  },
  {
    key: 'analyse',
    label: 'Running accessibility tests',
    activeDuring: ['SCANNING'],
  },
  {
    key: 'report',
    label: 'Processing the report',
    activeDuring: ['PROCESSING'],
  },
]

/**
 * `pending-request` is a client-side lifecycle state, not a backend status.
 * POST /api/scans/ runs the scan synchronously, so while the request is
 * outstanding the stage is genuinely unknown — we report it as unknown
 * rather than guessing a step.
 */
export type ConsoleState = 'idle' | 'pending-request' | ScanStatus

export type StepState = 'pending' | 'active' | 'done' | 'failed'

export function stepStates(state: ConsoleState): StepState[] {
  if (state === 'idle') return PIPELINE_STEPS.map(() => 'pending')

  // Stage unknown while the synchronous POST is in flight: nothing is
  // marked active or complete, because nothing has been reported yet.
  if (state === 'pending-request') return PIPELINE_STEPS.map(() => 'pending')

  if (state === 'FAILED') return PIPELINE_STEPS.map(() => 'failed')

  if (state === 'COMPLETED') return PIPELINE_STEPS.map(() => 'done')

  const activeIndex = PIPELINE_STEPS.findIndex((s) => s.activeDuring.includes(state))
  if (activeIndex === -1) return PIPELINE_STEPS.map(() => 'pending')

  return PIPELINE_STEPS.map((_, i) => {
    if (i < activeIndex) return 'done'
    if (i === activeIndex) return 'active'
    return 'pending'
  })
}

export const STATE_LABEL: Record<ConsoleState, string> = {
  idle: 'READY',
  'pending-request': 'AWAITING SCANNER',
  QUEUED: 'QUEUED',
  CONNECTING: 'CONNECTING',
  LOADING: 'RENDERING',
  SCANNING: 'ANALYSING',
  PROCESSING: 'PROCESSING',
  COMPLETED: 'COMPLETE',
  FAILED: 'FAILED',
}

export const STATE_MESSAGE: Record<ConsoleState, string> = {
  idle: 'Waiting for a target...',
  'pending-request': 'Scan request in flight — stage reported on response.',
  QUEUED: 'Scan queued.',
  CONNECTING: 'Establishing connection to target host.',
  LOADING: 'Rendering the page in a headless browser.',
  SCANNING: 'Executing axe-core rules against the live DOM.',
  PROCESSING: 'Persisting findings and computing score.',
  COMPLETED: 'Scan finished.',
  FAILED: 'Scan halted.',
}

export function isTerminal(status: ScanStatus): boolean {
  return status === 'COMPLETED' || status === 'FAILED'
}

/* ============================================================
   Severity
   ============================================================ */

export const SEVERITY_ORDER: Severity[] = ['CRITICAL', 'SERIOUS', 'MODERATE', 'MINOR']

export const SEVERITY_WEIGHT: Record<Severity, number> = {
  CRITICAL: 10,
  SERIOUS: 7,
  MODERATE: 4,
  MINOR: 1,
}

/** Mirrors backend/scanner/services/scoring.py so the UI can label the maths. */
export const SEVERITY_VAR: Record<Severity, string> = {
  CRITICAL: 'var(--color-critical)',
  SERIOUS: 'var(--color-serious)',
  MODERATE: 'var(--color-moderate)',
  MINOR: 'var(--color-minor)',
}

export function severityRank(severity: Severity): number {
  const index = SEVERITY_ORDER.indexOf(severity)
  return index === -1 ? SEVERITY_ORDER.length : index
}

export function sortBySeverity<T extends { severity: Severity }>(issues: T[]): T[] {
  return [...issues].sort((a, b) => severityRank(a.severity) - severityRank(b.severity))
}

export function countBySeverity(issues: { severity: Severity }[]): Record<Severity, number> {
  const counts: Record<Severity, number> = { CRITICAL: 0, SERIOUS: 0, MODERATE: 0, MINOR: 0 }
  for (const issue of issues) {
    if (issue.severity in counts) counts[issue.severity] += 1
  }
  return counts
}

/** Matches calculate_score(): max(0, 100 - sum(weights)). */
export function predictScore(issues: { severity: Severity }[]): number {
  const total = issues.reduce((sum, i) => sum + (SEVERITY_WEIGHT[i.severity] ?? 1), 0)
  return Math.max(0, 100 - total)
}

export function scoreTone(score: number): 'good' | 'fair' | 'poor' {
  if (score >= 90) return 'good'
  if (score >= 70) return 'fair'
  return 'poor'
}
