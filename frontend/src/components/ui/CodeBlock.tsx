import { useEffect, useRef, useState } from 'react'

export function CodeBlock({
  code,
  label,
  language,
  copyable = true,
}: {
  code: string
  label?: string
  language?: string
  copyable?: boolean
}) {
  return (
    <div data-surface="dark" className="bg-[var(--color-ink)]">
      <div className="flex items-center justify-between gap-4 border-b border-[var(--color-ink-line)] px-4 py-2.5">
        <span className="tech-label text-[var(--color-ink-muted)]">
          {label ?? 'Code'}
          {language && <span className="ml-2 text-[var(--color-ink-dim)]">{language}</span>}
        </span>
        {copyable && <CopyToClipboard text={code} />}
      </div>
      <pre
        tabIndex={0}
        role="region"
        aria-label={`${label ?? 'Code'}${language ? ` (${language})` : ''}, scrollable`}
        className="overflow-x-auto px-4 py-4"
      >
        <code className="font-mono text-[0.8125rem] leading-relaxed whitespace-pre text-[var(--color-ink-text)]">
          {code}
        </code>
      </pre>
    </div>
  )
}

export function CopyToClipboard({
  text,
  className = '',
}: {
  text: string
  className?: string
}) {
  const [copied, setCopied] = useState(false)
  const [failed, setFailed] = useState(false)
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => () => window.clearTimeout(timer.current), [])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setFailed(false)
      setCopied(true)
      timer.current = window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setFailed(true)
    }
  }

  return (
    <button
      type="button"
      onClick={copy}
      className={`tech-label shrink-0 py-2 text-[var(--color-ink-muted)] transition-colors duration-150 hover:text-[var(--color-ink-text)] ${className}`}
    >
      <span aria-live="polite">{copied ? 'Copied' : failed ? 'Copy failed' : 'Copy code'}</span>
    </button>
  )
}
