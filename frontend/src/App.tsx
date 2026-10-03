import { useEffect } from 'react'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import { Nav } from './components/Nav'
import { Footer } from './components/Footer'
import { Container } from './components/ui/Layout'
import { Button } from './components/ui/Button'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import History from './pages/History'

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="tech-label skip-link focus-visible:border focus-visible:border-[var(--color-primary)] focus-visible:bg-[var(--color-surface)] focus-visible:px-4 focus-visible:py-3 focus-visible:text-[var(--color-primary-text)]"
      >
        Skip to main content
      </a>

      <Nav />

      <main id="main" tabIndex={-1} className="flex-1 focus:outline-none">
        <ScrollManager />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard/:scanId" element={<Dashboard />} />
          <Route path="/history" element={<History />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>

      <Footer />
    </div>
  )
}

/** Restores scroll on navigation and honours in-page hash links. */
function ScrollManager() {
  const { pathname, hash } = useLocation()

  useEffect(() => {
    if (hash) {
      const id = hash.slice(1)
      // Wait a frame so the target section is mounted before scrolling.
      const frame = requestAnimationFrame(() => {
        const el = document.getElementById(id)
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' })
          return
        }
        window.scrollTo({ top: 0 })
      })
      return () => cancelAnimationFrame(frame)
    }

    window.scrollTo({ top: 0 })
  }, [pathname, hash])

  return null
}

function NotFound() {
  return (
    <Container className="py-28">
      <p className="tech-label text-[var(--color-primary-text)]">404</p>
      <h1 className="editorial mt-6 text-4xl sm:text-5xl">Page not found</h1>
      <p className="mt-5 max-w-md leading-relaxed text-[var(--color-body)]">
        That route does not exist in this application.
      </p>
      <div className="mt-8">
        <Link to="/">
          <Button variant="primary" size="sm">Back to scanner</Button>
        </Link>
      </div>
    </Container>
  )
}
