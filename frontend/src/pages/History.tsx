import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ScanRow, ScanRowHeader } from '../components/ScanRow'
import { Container, Divider } from '../components/ui/Layout'
import { Button } from '../components/ui/Button'
import { EmptyState, ErrorState, LoadingRows } from '../components/ui/States'
import { apiErrorMessage, getScanHistory } from '../services/api'
import type { Scan } from '../types'

export default function History() {
  const [scans, setScans] = useState<Scan[]>([])
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState('')

  const fetchHistory = useCallback(async () => {
    try {
      const rows = await getScanHistory()
      setScans(rows)
      setError('')
      setState('ready')
    } catch (e) {
      setError(apiErrorMessage(e, 'Could not load scan history.'))
      setState('error')
    }
  }, [])

  const load = useCallback(() => {
    setState('loading')
    void fetchHistory()
  }, [fetchHistory])

  useEffect(() => {
    // Fetching from the scanner API is an external-system synchronisation,
    // which is exactly what an effect is for.
    // oxlint-disable-next-line react/set-state-in-effect
    void fetchHistory()
  }, [fetchHistory])

  const completed = scans.filter((s) => s.status === 'COMPLETED').length
  const scores = scans.filter((s) => s.status === 'COMPLETED' && s.score !== null)
  const average = scores.length
    ? Math.round(scores.reduce((sum, s) => sum + (s.score ?? 0), 0) / scores.length)
    : null

  return (
    <section className="border-b border-[var(--color-line)]">
      <Container className="py-14 lg:py-20">
        <nav aria-label="Breadcrumb" className="mb-8">
          <Link to="/" className="tech-label text-[var(--color-subtle)] transition-colors hover:text-[var(--color-primary-text)]">
            ← Scanner
          </Link>
        </nav>

        <h1 className="editorial text-4xl sm:text-5xl">Scan history</h1>
        <p className="mt-5 max-w-xl leading-relaxed text-[var(--color-body)]">
          Every scan recorded on this instance, newest first. Open a report to review its findings
          or ask Copilot for a correction.
        </p>

        {state === 'ready' && scans.length > 0 && (
          <>
            <Divider className="my-10" />
            <dl className="grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
              <Stat label="Scans" value={String(scans.length)} />
              <Stat label="Completed" value={String(completed)} />
              <Stat label="Average score" value={average === null ? '--' : String(average)} />
              <Stat
                label="Failed"
                value={String(scans.filter((s) => s.status === 'FAILED').length)}
              />
            </dl>
            <Divider className="my-10" />
          </>
        )}

        <div className="mt-2">
          {state === 'loading' && <LoadingRows rows={6} label="Loading scan history" />}
          {state === 'error' && <ErrorState message={error} onRetry={load} />}
          {state === 'ready' && scans.length === 0 && (
            <EmptyState
              title="No scans recorded yet"
              description="Run your first scan and it will appear here with its score and issue count."
              action={
                <Link to="/">
                  <Button variant="primary" size="sm">Open scanner</Button>
                </Link>
              }
            />
          )}
          {state === 'ready' && scans.length > 0 && (
            <>
              <ScanRowHeader />
              <ul className="list-none">
                {scans.map((scan) => (
                  <ScanRow key={scan.id} scan={scan} />
                ))}
              </ul>
            </>
          )}
        </div>
      </Container>
    </section>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="tech-label text-[var(--color-subtle)]">{label}</dt>
      <dd className="mt-2 font-mono text-2xl tabular-nums text-[var(--color-ink-fg)]">{value}</dd>
    </div>
  )
}
