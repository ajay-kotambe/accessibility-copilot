import { Link } from 'react-router-dom'
import { Container } from './ui/Layout'

export function Footer() {
  return (
    <footer className="border-t border-[var(--color-line)]">
      <Container className="py-12">
        <div className="flex flex-col gap-8 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-sm">
            <p className="tech-label text-[var(--color-ink-fg)]">
              <span aria-hidden="true" className="mr-2 text-[var(--color-primary-text)]">
                ✣
              </span>
              Accessibility Copilot
            </p>
            <p className="mt-4 text-sm leading-relaxed text-[var(--color-body)]">
              Scan. Understand. Fix.
            </p>
          </div>

          <nav aria-label="Footer" className="flex flex-wrap gap-x-8">
            <Link
              to="/#scanner"
              className="tech-label py-2 text-[var(--color-subtle)] transition-colors hover:text-[var(--color-primary-text)]"
            >
              Scanner
            </Link>
            <Link
              to="/#how-it-works"
              className="tech-label py-2 text-[var(--color-subtle)] transition-colors hover:text-[var(--color-primary-text)]"
            >
              How it works
            </Link>
            <Link
              to="/history"
              className="tech-label py-2 text-[var(--color-subtle)] transition-colors hover:text-[var(--color-primary-text)]"
            >
              History
            </Link>
          </nav>
        </div>

        <div className="mt-10 border-t border-[var(--color-line)] pt-6">
          <p className="text-xs leading-relaxed text-[var(--color-subtle)]">
            Automated checks support — not replace — expert accessibility review. No code is executed
            automatically; AI output is copyable and reviewable only.
          </p>
        </div>
      </Container>
    </footer>
  )
}
