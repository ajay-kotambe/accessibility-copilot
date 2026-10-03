import type { ReactNode } from 'react'

export function TechLabel({
  children,
  className = '',
  tone = 'default',
}: {
  children: ReactNode
  className?: string
  tone?: 'default' | 'subtle' | 'primary' | 'dark'
}) {
  const tones = {
    default: 'text-[var(--color-ink-fg)]',
    subtle: 'text-[var(--color-subtle)]',
    primary: 'text-[var(--color-primary-text)]',
    dark: 'text-[var(--color-ink-muted)]',
  } as const

  return <span className={`tech-label ${tones[tone]} ${className}`}>{children}</span>
}
