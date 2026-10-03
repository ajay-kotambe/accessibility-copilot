import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ScanConsole } from '../components/ScanConsole'
import { ScorePanel } from '../components/ScorePanel'
import { IssueList } from '../components/IssueList'
import { CopilotPanel } from '../components/CopilotPanel'
import { Container, Divider } from '../components/ui/Layout'
import { Button } from '../components/ui/Button'
import { ErrorState, LoadingRows } from '../components/ui/States'
import { apiErrorMessage, analyzeIssue, generateFix, getScan, getScanIssues } from '../services/api'
import type { AIAnalysis, Issue, Scan } from '../types'
import { isTerminal, sortBySeverity } from '../lib/scan'
import { clockTime, duration, hostOf, pathOf } from '../lib/format'

export default function Dashboard() {
  const { scanId } = useParams<{ scanId: string }>()
  const id = Number(scanId)

  const [scan, setScan] = useState<Scan | null>(null)
  const [issues, setIssues] = useState<Issue[]>([])
  const [selected, setSelected] = useState<Issue | null>(null)
  const [analysis, setAnalysis] = useState<AIAnalysis | null>(null)
  const [aiBusy, setAiBusy] = useState(false)
  const [aiAction, setAiAction] = useState<'analyze' | 'fix' | null>(null)
  const [aiError, setAiError] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [filter, setFilter] = useState<string>('ALL')

  const requestId = useRef(0)

  const load = useCallback(
    async (options: { showSpinner?: boolean } = {}) => {
      if (!Number.isFinite(id)) {
        setLoadError('That scan id is not valid.')
        setLoading(false)
        return
      }

      if (options.showSpinner) setLoading(true)

      const current = ++requestId.current
      try {
        const next = await getScan(id)
        if (current !== requestId.current) return
        setScan(next)
        setLoadError('')
        setLoading(false)

        // Only re-fetch the issue list once the scan has settled.
        if (isTerminal(next.status)) {
          const rows = await getScanIssues(id)
          if (current !== requestId.current) return
          setIssues(rows)
        }
      } catch (e) {
        if (current !== requestId.current) return
        setLoadError(apiErrorMessage(e, 'Could not load this scan.'))
        setLoading(false)
      }
    },
    [id],
  )

  // Initial load. `load` performs no synchronous setState, so this does not
  // cause a cascading render.
  useEffect(() => {
    // Polling scan status from the API is an external-system synchronisation.
    // oxlint-disable-next-line react/set-state-in-effect
    void load()
  }, [load])

  useEffect(() => {
    if (!scan || isTerminal(scan.status)) return
    const timer = window.setInterval(() => void load(), 2000)
    return () => window.clearInterval(timer)
  }, [scan, load])

  const select = (issue: Issue) => {
    setSelected(issue)
    setAnalysis(issue.ai_analysis)
    setAiError('')
  }

  const runCopilot = async (issue: Issue, kind: 'analyze' | 'fix') => {
    setAiBusy(true)
    setAiAction(kind)
    setAiError('')
    try {
      const result = kind === 'analyze' ? await analyzeIssue(issue.id) : await generateFix(issue.id)
      setAnalysis(result)
    } catch (e) {
      setAiError(apiErrorMessage(e, 'The assistant could not be reached.'))
    } finally {
      setAiBusy(false)
      setAiAction(null)
    }
  }

  if (loadError && !scan) {
    return (
      <Container className="py-24">
        <ErrorState title="Scan unavailable" message={loadError} onRetry={() => load({ showSpinner: true })} />
        <div className="mt-6">
          <Link to="/" className="tech-label text-[var(--color-primary-text)] underline underline-offset-4">
            ← Back to scanner
          </Link>
        </div>
      </Container>
    )
  }

  if (loading && !scan) {
    return (
      <Container className="py-24">
        <p role="status" className="tech-label mb-8 text-[var(--color-subtle)]">Loading report…</p>
        <LoadingRows rows={5} />
      </Container>
    )
  }

  if (!scan) return null

  const running = !isTerminal(scan.status)
  const visible = filter === 'ALL' ? issues : issues.filter((i) => i.severity === filter)

  return (
    <>
      {/* Report header */}
      <section className="border-b border-[var(--color-line)]">
        <Container className="py-10 lg:py-14">
          <nav aria-label="Breadcrumb" className="mb-8">
            <Link to="/" className="tech-label text-[var(--color-subtle)] transition-colors hover:text-[var(--color-primary-text)]">
              ← Scanner
            </Link>
          </nav>

          <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_20rem] lg:gap-16">
            <div className="min-w-0">
              <p className="tech-label text-[var(--color-primary-text)]">
                Scan #{scan.id}
                {scan.status === 'COMPLETED' && ' · Completed'}
                {scan.status === 'FAILED' && ' · Failed'}
              </p>

              <h1 className="editorial mt-5 break-words text-3xl sm:text-4xl">
                {hostOf(scan.url)}
                {pathOf(scan.url) && (
                  <span className="text-[var(--color-subtle)]">{pathOf(scan.url)}</span>
                )}
              </h1>

              <a
                href={scan.url}
                target="_blank"
                rel="noreferrer noopener"
                className="mt-3 block truncate py-1.5 font-mono text-xs text-[var(--color-subtle)] underline underline-offset-4 hover:text-[var(--color-primary-text)]"
              >
                {scan.url}
              </a>

              <Divider className="my-8" />

              <dl className="grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
                <Meta label="Status" value={scan.status} />
                <Meta label="Started" value={clockTime(scan.started_at)} />
                <Meta label="Duration" value={duration(scan.started_at, scan.completed_at)} />
                <Meta label="Pages" value={String(scan.pages.length)} />
              </dl>

              {scan.pages[0]?.title && (
                <p className="mt-6 text-sm text-[var(--color-body)]">
                  <span className="tech-label mr-2 text-[var(--color-subtle)]">Title</span>
                  {scan.pages[0].title}
                </p>
              )}
            </div>

            <div>
              {scan.status === 'FAILED' ? (
                <ErrorState title="Scan failed" message={scan.error_message || 'The scan did not complete.'} compact />
              ) : running ? (
                <div className="border border-[var(--color-line)] p-6">
                  <p className="tech-label text-[var(--color-subtle)]">Score</p>
                  <p role="status" className="mt-4 text-sm leading-relaxed text-[var(--color-body)]">
                    The report is generated once the scan completes. Current status:{' '}
                    <span className="font-mono">{scan.status}</span>.
                  </p>
                </div>
              ) : (
                <ScorePanel score={scan.score} issues={issues} />
              )}
            </div>
          </div>
        </Container>
      </section>

      {/* Live pipeline while running */}
      {running && (
        <section aria-label="Scan progress" className="border-b border-[var(--color-line)]">
          <Container className="py-10">
            <ScanConsole state={scan.status} target={scan.url} />
          </Container>
        </section>
      )}

      {/* Findings + copilot */}
      {scan.status === 'FAILED' ? (
        <Container className="py-16">
          <Link to="/">
            <Button variant="primary" size="sm">Scan another URL</Button>
          </Link>
        </Container>
      ) : (
        <section aria-label="Findings and analysis" className="border-b border-[var(--color-line)]">
          <Container className="py-14 lg:py-20">
            <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:gap-16">
              <div className="min-w-0">
                <div className="flex flex-wrap items-baseline justify-between gap-4 pb-6">
                  <h2 className="editorial text-2xl">Issues</h2>
                  <p className="tech-label text-[var(--color-subtle)]">
                    {issues.length} {issues.length === 1 ? 'finding' : 'findings'}
                  </p>
                </div>

                {running ? (
                  <LoadingRows rows={4} label="Waiting for findings" />
                ) : (
                  <>
                    <SeverityFilter
                      issues={issues}
                      active={filter}
                      onChange={(next) => {
                        setFilter(next)
                        if (next !== 'ALL') {
                          const first = sortBySeverity(issues).find((i) => i.severity === next)
                          if (first) select(first)
                        }
                      }}
                    />
                    <div className="mt-6">
                      <IssueList
                        issues={visible}
                        selectedId={selected?.id}
                        onSelect={select}
                      />
                    </div>
                  </>
                )}
              </div>

              <div className="min-w-0 lg:border-l lg:border-[var(--color-line)] lg:pl-16">
                <CopilotPanel
                  issue={selected}
                  analysis={analysis}
                  busy={aiBusy}
                  action={aiAction}
                  onAnalyze={(i) => runCopilot(i, 'analyze')}
                  onGenerateFix={(i) => runCopilot(i, 'fix')}
                />
                {aiError && (
                  <div className="mt-6">
                    <ErrorState message={aiError} onRetry={() => selected && runCopilot(selected, aiAction ?? 'analyze')} compact />
                  </div>
                )}
              </div>
            </div>
          </Container>
        </section>
      )}

      <Container className="py-12">
        <Link to="/">
          <Button size="sm">← New scan</Button>
        </Link>
      </Container>
    </>
  )
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="tech-label text-[var(--color-subtle)]">{label}</dt>
      <dd className="mt-2 font-mono text-sm text-[var(--color-ink-fg)]">{value}</dd>
    </div>
  )
}

function SeverityFilter({
  issues,
  active,
  onChange,
}: {
  issues: Issue[]
  active: string
  onChange: (next: string) => void
}) {
  const options = ['ALL', 'CRITICAL', 'SERIOUS', 'MODERATE', 'MINOR'] as const
  const counts = {
    ALL: issues.length,
    CRITICAL: issues.filter((i) => i.severity === 'CRITICAL').length,
    SERIOUS: issues.filter((i) => i.severity === 'SERIOUS').length,
    MODERATE: issues.filter((i) => i.severity === 'MODERATE').length,
    MINOR: issues.filter((i) => i.severity === 'MINOR').length,
  }

  return (
    <div role="group" aria-label="Filter issues by severity" className="flex flex-wrap gap-2">
      {options.map((option) => {
        const selected = active === option
        return (
          <button
            key={option}
            type="button"
            onClick={() => onChange(option)}
            aria-pressed={selected}
            className={`tech-label flex items-center gap-2 border px-3 py-2 transition-colors duration-150 ${
              selected
                ? 'border-[var(--color-ink-fg)] bg-[var(--color-ink-fg)] text-white'
                : 'border-[var(--color-line-strong)] text-[var(--color-body)] hover:border-[var(--color-ink-fg)]'
            }`}
          >
            {option !== 'ALL' && (
              <span aria-hidden="true" className="inline-block h-1.5 w-1.5" style={{ backgroundColor: `var(--color-${option.toLowerCase()})` }} />
            )}
            {option}
            <span className={`tabular-nums ${selected ? 'opacity-70' : 'text-[var(--color-subtle)]'}`}>
              {counts[option]}
            </span>
          </button>
        )
      })}
    </div>
  )
}
