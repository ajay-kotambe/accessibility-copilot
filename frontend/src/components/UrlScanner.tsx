import { useId, useState, type FormEvent } from 'react'
import { Button } from './ui/Button'

/**
 * Technical input group for the scan target.
 * Labeled as a real form field with a description and error wiring.
 */
export function UrlScanner({
  onSubmit,
  busy,
  error,
}: {
  onSubmit: (url: string) => void
  busy: boolean
  error?: string
}) {
  const inputId = useId()
  const hintId = useId()
  const errorId = useId()
  const [value, setValue] = useState('')

  const handle = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = value.trim()
    if (trimmed) onSubmit(trimmed)
  }

  return (
    <form onSubmit={handle} noValidate className="w-full">
      <label htmlFor={inputId} className="tech-label block text-[var(--color-ink-fg)]">
        Target URL
      </label>

      <div
        className={`mt-3 flex flex-col gap-0 border bg-[var(--color-surface)] sm:flex-row ${
          error
            ? 'border-[var(--color-critical)]'
            : 'border-[var(--color-line-strong)] focus-within:border-[var(--color-primary)]'
        }`}
      >
        <span className="hidden items-center border-r border-[var(--color-line)] bg-[var(--color-canvas)] px-3 sm:flex">
          <span className="font-mono text-xs text-[var(--color-subtle)]">https://</span>
        </span>

        <input
          id={inputId}
          name="url"
          type="url"
          inputMode="url"
          autoComplete="url"
          spellCheck={false}
          required
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="example.com"
          aria-describedby={error ? `${hintId} ${errorId}` : hintId}
          aria-invalid={error ? true : undefined}
          className="h-12 min-w-0 flex-1 border-0 bg-transparent px-3.5 font-mono text-sm text-[var(--color-ink-fg)] placeholder:text-[var(--color-subtle)]/70 focus:outline-none focus:ring-0 sm:h-13"
        />

        <Button
          type="submit"
          variant="primary"
          disabled={busy || value.trim().length === 0}
          className="h-12 shrink-0 border-t border-[var(--color-line)] px-6 sm:h-auto sm:border-t-0 sm:border-l"
        >
          {busy ? 'Scanning' : 'Scan website'}
          <span aria-hidden="true">→</span>
        </Button>
      </div>

      <p id={hintId} className="mt-3 text-xs leading-relaxed text-[var(--color-subtle)]">
        Public URLs only. Private networks and unsafe redirects are blocked before rendering.
      </p>

      {error && (
        <p id={errorId} role="alert" className="mt-3 flex items-start gap-2.5 text-sm text-[var(--color-critical)]">
          <span aria-hidden="true" className="mt-1.5 block h-1.5 w-1.5 shrink-0 bg-[var(--color-critical)]" />
          {error}
        </p>
      )}

      <ul className="mt-6 flex flex-wrap gap-x-6 gap-y-2">
        {['Axe-core rules', 'Deterministic scoring', 'On-demand AI fixes'].map((item) => (
          <li key={item} className="tech-label flex items-center gap-2 text-[var(--color-subtle)]">
            <span aria-hidden="true" className="text-[var(--color-primary-text)]">
              ✓
            </span>
            {item}
          </li>
        ))}
      </ul>
    </form>
  )
}
