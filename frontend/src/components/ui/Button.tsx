import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'outline' | 'ghost' | 'danger'
type Size = 'sm' | 'md'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  children: ReactNode
}

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-[var(--color-primary-dark)] text-white border-0 hover:bg-[var(--color-primary-deep)]',
  outline:
    'bg-transparent text-[var(--color-ink-fg)] border border-[var(--color-line-strong)] hover:border-[var(--color-primary)] hover:text-[var(--color-primary-text)]',
  ghost:
    'bg-transparent text-[var(--color-body)] border border-transparent hover:text-[var(--color-ink-fg)] hover:border-[var(--color-line)]',
  danger:
    'bg-transparent text-[var(--color-critical)] border border-[var(--color-critical)] hover:bg-[var(--color-critical)] hover:text-white',
}

const SIZES: Record<Size, string> = {
  sm: 'h-8 px-3 text-[0.75rem]',
  md: 'h-11 px-5 text-[0.8125rem]',
}

export function Button({
  variant = 'outline',
  size = 'md',
  className = '',
  children,
  ...rest
}: Props) {
  return (
    <button
      {...rest}
      className={`tech-label inline-flex items-center justify-center gap-2 whitespace-nowrap transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-45 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
    >
      {children}
    </button>
  )
}
