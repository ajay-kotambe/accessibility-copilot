import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { getHealth } from '../services/api'

const LINKS = [
  { to: '/#how-it-works', label: 'How it works', hash: 'how-it-works' },
  { to: '/#scanner', label: 'Scanner', hash: 'scanner' },
  { to: '/history', label: 'History', hash: null },
]

type Health = 'checking' | 'ready' | 'offline'

export function Nav() {
  const [health, setHealth] = useState<Health>('checking')
  const { pathname, hash } = useLocation()

  useEffect(() => {
    let cancelled = false
    getHealth()
      .then((res) => {
        if (!cancelled) setHealth(res.status === 'ok' ? 'ready' : 'offline')
      })
      .catch(() => {
        if (!cancelled) setHealth('offline')
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--color-line)] bg-[var(--color-canvas)]/90 backdrop-blur-sm">
<nav
        aria-label="Primary"
        className="mx-auto flex h-14 w-full max-w-[1240px] items-center justify-between gap-2 px-4 sm:gap-6 sm:px-8 lg:px-10"
      >
        <Link
          to="/"
          className="tech-label flex shrink-0 items-center gap-2 py-2 text-[var(--color-ink-fg)] transition-colors hover:text-[var(--color-primary-text)]"
        >
          <span aria-hidden="true" className="text-[var(--color-primary-text)]">
            ✣
          </span>
          <span className="hidden sm:inline">Accessibility</span>
          <span className="sm:hidden">A11y</span>
          <span className="hidden font-normal text-[var(--color-subtle)] sm:inline">Copilot</span>
        </Link>

        <div className="flex min-w-0 items-center gap-2 sm:gap-8">
          <ul className="flex min-w-0 items-center gap-2 sm:gap-7">
            {LINKS.map((link) => (
              <li key={link.to} className="shrink-0">
                <NavLink
                  to={link.to}
                  className={`tech-label block whitespace-nowrap py-2 text-[0.625rem] tracking-[0.08em] transition-colors duration-150 sm:text-[0.6875rem] sm:tracking-[0.14em] ${
                    isActive(pathname, hash, link.hash)
                      ? 'text-[var(--color-primary-text)]'
                      : 'text-[var(--color-body)] hover:text-[var(--color-ink-fg)]'
                  }`}
                >
                  {link.label}
                </NavLink>
              </li>
            ))}
          </ul>

          <SystemStatus health={health} />
        </div>
      </nav>
    </header>
  )
}

function SystemStatus({ health }: { health: Health }) {
  const config = {
    checking: { text: 'Checking', color: 'bg-[var(--color-subtle)]', label: 'Checking system status' },
    ready: { text: 'System ready', color: 'bg-[var(--color-primary)]', label: 'System ready' },
    offline: { text: 'API offline', color: 'bg-[var(--color-critical)]', label: 'Scanner API unreachable' },
  }[health]

  return (
    <p className="tech-label flex items-center gap-2 text-[var(--color-subtle)]">
      <span className="sr-only" aria-live="polite">
        {config.label}
      </span>
      <span
        aria-hidden="true"
        className={`h-1.5 w-1.5 rounded-full ${config.color} ${
          health === 'checking' ? 'animate-ac-pulse' : ''
        }`}
      />
      <span aria-hidden="true" className="hidden md:inline">
        {config.text}
      </span>
    </p>
  )
}

function isActive(pathname: string, hash: string, linkHash: string | null): boolean {
  if (linkHash) return hash === `#${linkHash}`
  return pathname.startsWith('/history') || pathname.startsWith('/dashboard')
}
