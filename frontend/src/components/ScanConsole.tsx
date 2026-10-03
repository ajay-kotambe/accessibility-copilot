import type { ConsoleState, StepState } from '../lib/scan'
import { PIPELINE_STEPS, STATE_LABEL, STATE_MESSAGE, stepStates } from '../lib/scan'
import { DarkPanel, PanelHeader } from './ui/Panel'
import { hostOf } from '../lib/format'

/**
 * Dark technical monitoring panel.
 *
 * Every state shown here is derived from the real backend scan status
 * (or, while the synchronous POST is outstanding, from the honest fact
 * that the stage is not yet known). There are no timers and no
 * simulated progress.
 */
export function ScanConsole({
  state,
  target,
  detail,
}: {
  state: ConsoleState
  target?: string
  detail?: string
}) {
  const states = stepStates(state)
  const failed = state === 'FAILED'
  const complete = state === 'COMPLETED'
  const inFlight = state === 'pending-request'

  const indicator = failed ? 'critical' : complete ? 'primary' : inFlight ? 'primary' : state === 'idle' ? 'idle' : 'primary'

  return (
    <DarkPanel className="flex h-full flex-col">
      <PanelHeader
        title="Scan pipeline"
        meta={<StatusDot tone={indicator} />}
      />

      <div className="flex flex-1 flex-col px-5 py-6 sm:px-6">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          <p
            className={`font-mono text-2xl tracking-tight ${
              failed ? 'text-[var(--color-ink-text)]' : 'text-white'
            }`}
          >
            {STATE_LABEL[state]}
          </p>
          {target && (
            <p className="max-w-full truncate font-mono text-xs text-[var(--color-ink-muted)]">
              {hostOf(target)}
            </p>
          )}
        </div>

        <p aria-live="polite" className="mt-3 text-sm leading-relaxed text-[var(--color-ink-muted)]">
          {detail && failed ? detail : STATE_MESSAGE[state]}
        </p>

        {inFlight && (
          <div className="mt-5 h-px w-full overflow-hidden bg-[var(--color-ink-line)]" aria-hidden="true">
            <div className="h-full w-1/4 bg-[var(--color-primary)] animate-ac-sweep" />
          </div>
        )}

        <ol className="mt-7 space-y-0">
          {PIPELINE_STEPS.map((step, i) => (
            <PipelineRow key={step.key} index={i + 1} label={step.label} state={states[i]} />
          ))}
        </ol>

        <div className="mt-auto border-t border-[var(--color-ink-line)] pt-5">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3">
            <SpecRow label="axe-core" value="Deterministic" />
            <SpecRow label="Playwright" value="Browser engine" />
          </dl>
        </div>
      </div>
    </DarkPanel>
  )
}

function PipelineRow({
  index,
  label,
  state,
}: {
  index: number
  label: string
  state: StepState
}) {
  const text = {
    pending: 'text-[var(--color-ink-muted)]',
    active: 'text-white',
    done: 'text-[var(--color-ink-text)]',
    failed: 'text-[var(--color-ink-muted)] line-through decoration-[var(--color-ink-line)]',
  }[state]

  return (
    <li className="flex items-center gap-3 border-b border-[var(--color-ink-line)] py-2.5 last:border-b-0">
      <StepMarker state={state} />
      <span className={`tech-label flex-1 ${text}`}>
        <span className="mr-2 text-[var(--color-ink-dim)]">{String(index).padStart(2, '0')}</span>
        {label}
      </span>
      <span className="tech-label sr-only">{describe(state)}</span>
    </li>
  )
}

function StepMarker({ state }: { state: StepState }) {
  if (state === 'done') {
    return (
      <span aria-hidden="true" className="grid h-3.5 w-3.5 shrink-0 place-items-center border border-[var(--color-primary)] text-[8px] leading-none text-[var(--color-primary)]">
        ✓
      </span>
    )
  }
  if (state === 'active') {
    return (
      <span aria-hidden="true" className="h-3.5 w-3.5 shrink-0 border border-[var(--color-primary)] bg-[var(--color-primary)] animate-ac-pulse" />
    )
  }
  if (state === 'failed') {
    return (
      <span aria-hidden="true" className="h-3.5 w-3.5 shrink-0 border border-[var(--color-critical)]" />
    )
  }
  return (
    <span aria-hidden="true" className="h-3.5 w-3.5 shrink-0 border border-[var(--color-ink-line)]" />
  )
}

function SpecRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="tech-label text-[var(--color-ink-muted)]">{label}</dt>
      <dd className="mt-1.5 font-mono text-xs text-[var(--color-ink-text)]">{value}</dd>
    </div>
  )
}

export function StatusDot({
  tone,
  label,
}: {
  tone: 'idle' | 'primary' | 'critical'
  label?: string
}) {
  const color = {
    idle: 'bg-[var(--color-ink-muted)]',
    primary: 'bg-[var(--color-primary)]',
    critical: 'bg-[var(--color-critical)]',
  }[tone]

  const pulse = tone !== 'idle'

  return (
    <span className="inline-flex items-center gap-2">
      <span
        aria-hidden="true"
        className={`block h-1.5 w-1.5 rounded-full ${color} ${pulse ? 'animate-ac-pulse' : ''}`}
      />
      {label && (
        <span className="tech-label text-[var(--color-ink-muted)]">
          <span aria-live="polite">{label}</span>
        </span>
      )}
    </span>
  )
}

function describe(state: StepState): string {
  return { pending: 'Pending', active: 'In progress', done: 'Complete', failed: 'Not completed' }[state]
}
