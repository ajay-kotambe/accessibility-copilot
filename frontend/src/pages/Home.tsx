import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ScanConsole } from '../components/ScanConsole'
import { UrlScanner } from '../components/UrlScanner'
import { Container, SectionHeading, Divider } from '../components/ui/Layout'
import { ScorePanel } from '../components/ScorePanel'
import { IssueList } from '../components/IssueList'
import { CopilotPanel } from '../components/CopilotPanel'
import { ScanRow, ScanRowHeader } from '../components/ScanRow'
import { EmptyState, ErrorState } from '../components/ui/States'
import { Button } from '../components/ui/Button'
import { apiErrorMessage, analyzeIssue, generateFix, getScanHistory, startScan } from '../services/api'
import type { AIAnalysis, Issue, Scan } from '../types'
import type { ConsoleState } from '../lib/scan'
import { sortBySeverity } from '../lib/scan'
import { hostOf } from '../lib/format'

export default function Home() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<Scan | null>(null)
  const navigate = useNavigate()

  const handleScan = async (url: string) => {
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const scan = await startScan(url)
      setResult(scan)
      if (scan.status === 'FAILED') {
        setError(scan.error_message || 'The scan could not be completed.')
      } else {
        navigate(`/dashboard/${scan.id}`)
      }
    } catch (e) {
      setError(apiErrorMessage(e, 'The scan could not be started.'))
    } finally {
      setBusy(false)
    }
  }

  const consoleState = busy ? 'pending-request' : result ? result.status : 'idle'

  return (
    <>
      <Hero consoleState={consoleState} busy={busy} error={error} onSubmit={handleScan} target={result?.url} />

      <Features />
      <HowItWorks />
      <ScoreSection />
      <IssueSection />
      <CopilotSection />
      <HistorySection />
    </>
  )
}

/* ============================================================
   HERO
   ============================================================ */

function Hero({
  consoleState,
  busy,
  error,
  onSubmit,
  target,
}: {
  consoleState: ConsoleState
  busy: boolean
  error: string
  onSubmit: (url: string) => void
  target?: string
}) {
  return (
    <section className="relative overflow-hidden border-b border-[var(--color-line)]">
      <div aria-hidden="true" className="bg-grid absolute inset-0" />
      <Container className="relative py-16 sm:py-20 lg:py-28">
        <div className="grid items-start gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.85fr)] lg:gap-16">
          <div className="animate-ac-fade-up">
            <p className="tech-label flex items-center gap-2.5 text-[var(--color-primary-text)]">
              <span aria-hidden="true">✣</span>
              AI-assisted accessibility engineering
            </p>

            <h1 className="editorial mt-8 text-[3.25rem] sm:text-[4.5rem] lg:text-[5.25rem]">
              <span className="block">Scan.</span>
              <span className="block">Understand.</span>
              <span className="block">Fix.</span>
              <span className="mt-3 block text-[1.5rem] font-normal tracking-[-0.02em] text-[var(--color-body)] sm:text-[1.75rem]">
                Build for everyone.
              </span>
            </h1>

            <p className="mt-8 max-w-lg text-[1.0625rem] leading-relaxed text-[var(--color-body)]">
              Find real accessibility barriers in your website, understand why they matter, and get
              practical fixes with an AI engineering assistant.
            </p>

            <div id="scanner" className="mt-10 scroll-mt-20">
              <UrlScanner onSubmit={onSubmit} busy={busy} error={error} />
            </div>
          </div>

          <div className="animate-ac-fade-up lg:sticky lg:top-20">
            <ScanConsole state={consoleState} target={target} />
          </div>
        </div>
      </Container>
    </section>
  )
}

/* ============================================================
   FEATURES
   ============================================================ */

const FEATURES = [
  {
    index: '01',
    title: 'Deterministic detection',
    body: 'Findings come from axe-core and custom rules — not generated guesses. The same page produces the same report.',
  },
  {
    index: '02',
    title: 'Context that teaches',
    body: 'See the rule, selector, affected HTML, severity, and why the issue matters before you touch a line of code.',
  },
  {
    index: '03',
    title: 'Fix on demand',
    body: 'Ask Copilot when you need help, then copy a focused correction. Nothing is applied to your codebase automatically.',
  },
]

function Features() {
  return (
    <section aria-labelledby="features-heading" className="border-b border-[var(--color-line)]">
      <Container className="py-20 lg:py-28">
        <h2 id="features-heading" className="sr-only">
          Product capabilities
        </h2>
        <ul className="grid gap-px border border-[var(--color-line)] bg-[var(--color-line)] md:grid-cols-3">
          {FEATURES.map((feature) => (
            <li key={feature.index} className="bg-[var(--color-canvas)] p-8 lg:p-10">
              <p className="font-mono text-sm text-[var(--color-primary-text)]">{feature.index}</p>
              <h3 className="mt-6 text-lg font-semibold tracking-[-0.01em] text-[var(--color-ink-fg)]">
                {feature.title}
              </h3>
              <p className="mt-4 text-sm leading-relaxed text-[var(--color-body)]">{feature.body}</p>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  )
}

/* ============================================================
   HOW IT WORKS
   ============================================================ */

const STEPS = [
  { index: '01', title: 'Enter URL', body: 'Paste a public URL into the scanner.' },
  { index: '02', title: 'Render with Playwright', body: 'A headless Chromium instance loads the real page.' },
  { index: '03', title: 'Run axe-core', body: 'WCAG rules execute against the live DOM.' },
  { index: '04', title: 'Analyse issues', body: 'Violations are graded and scored by severity weight.' },
  { index: '05', title: 'Ask Copilot', body: 'Request an explanation and a focused correction.' },
  { index: '06', title: 'Fix + rescan', body: 'Apply the patch, then verify the score moved.' },
]

function HowItWorks() {
  return (
    <section id="how-it-works" aria-labelledby="how-heading" className="scroll-mt-16 border-b border-[var(--color-line)]">
      <Container className="py-20 lg:py-28">
        <SectionHeading
          index="Pipeline"
          title="How it works"
          lede="One pass from URL to patch. Every stage is reported by the scanner — nothing is simulated."
        />

        <ol className="mt-14 border-t border-[var(--color-line)] lg:mt-20">
          {STEPS.map((step, i) => (
            <li key={step.index}>
              <div className="grid gap-3 border-b border-[var(--color-line)] py-7 sm:grid-cols-[4rem_1fr] sm:gap-8 lg:grid-cols-[4rem_16rem_1fr]">
                <span className="font-mono text-sm text-[var(--color-primary-text)]">{step.index}</span>
                <h3 className="text-base font-semibold tracking-[-0.01em] text-[var(--color-ink-fg)]">
                  {step.title}
                </h3>
                <p className="text-sm leading-relaxed text-[var(--color-body)]">{step.body}</p>
              </div>
              {i < STEPS.length - 1 && (
                <span aria-hidden="true" className="sr-only">
                  then
                </span>
              )}
            </li>
          ))}
        </ol>
      </Container>
    </section>
  )
}

/* ============================================================
   SCORE + ISSUE — driven by the most recent real scan
   ============================================================ */

function useLatestScan() {
  const [scan, setScan] = useState<Scan | null>(null)
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState('')

  // No synchronous setState before the first await, so mounting does not
  // trigger a cascading render.
  const fetchLatest = useCallback(async () => {
    try {
      const scans = await getScanHistory()
      setScan(scans[0] ?? null)
      setState('ready')
    } catch (e) {
      setError(apiErrorMessage(e, 'Could not load scan data.'))
      setState('error')
    }
  }, [])

  const reload = useCallback(() => {
    setState('loading')
    void fetchLatest()
  }, [fetchLatest])

  useEffect(() => {
    // Fetching scan records is an external-system synchronisation.
    // oxlint-disable-next-line react/set-state-in-effect
    void fetchLatest()
  }, [fetchLatest])

  return { scan, state, error, reload }
}

function ScoreSection() {
  const { scan, state, error, reload } = useLatestScan()

  return (
    <section aria-labelledby="score-heading" className="border-b border-[var(--color-line)]">
      <Container className="py-20 lg:py-28">
        <div className="grid gap-12 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1fr)] lg:gap-20">
          <SectionHeading
            index="Report"
            title="A score you can act on"
            lede="Weighted by severity, so two serious barriers cost more than four minor ones. The score is computed on the server from the recorded findings."
          />

          <div className="lg:pt-2">
            {state === 'loading' && <p role="status" className="tech-label text-[var(--color-subtle)]">Loading latest scan…</p>}
            {state === 'error' && <ErrorState message={error} onRetry={reload} compact />}
            {state === 'ready' && !scan && (
              <EmptyState
                title="No scan data yet"
                description="Run your first scan and the deterministic score breakdown will appear here."
                action={
                  <a href="#scanner">
                    <Button size="sm" variant="primary">Open scanner</Button>
                  </a>
                }
              />
            )}
            {state === 'ready' && scan && (
              <div>
                <p className="tech-label mb-6 text-[var(--color-subtle)]">
                  Latest scan · {hostOf(scan.url)}
                </p>
                {scan.status === 'FAILED' ? (
                  <ErrorState title="Scan failed" message={scan.error_message || 'The scan did not complete.'} compact />
                ) : (
                  <ScorePanel score={scan.score} issues={scan.issues} />
                )}
                <Link
                  to={`/dashboard/${scan.id}`}
                  className="tech-label mt-6 inline-block py-2 text-[var(--color-primary-text)] underline underline-offset-4 hover:text-[var(--color-primary-dark)]"
                >
                  Open full report →
                </Link>
              </div>
            )}
          </div>
        </div>
      </Container>
    </section>
  )
}

function IssueSection() {
  const { scan, state, reload } = useLatestScan()

  return (
    <section aria-labelledby="issues-heading" className="border-b border-[var(--color-line)]">
      <Container className="py-20 lg:py-28">
        <SectionHeading
          index="Findings"
          title="Every issue, with its evidence"
          lede="Rule identifier, affected selector, and the exact HTML that triggered the violation."
        />

        <div className="mt-14 lg:mt-16">
          {state === 'loading' && <p role="status" className="tech-label text-[var(--color-subtle)]">Loading findings…</p>}
          {state === 'ready' && (!scan || scan.issues.length === 0) && (
            <EmptyState
              title={scan ? 'No violations detected' : 'No scan data yet'}
              description={
                scan
                  ? 'The enabled rule set found no violations on the last scanned page.'
                  : 'Run a scan to populate real findings here.'
              }
              action={
                <a href="#scanner">
                  <Button size="sm">Open scanner</Button>
                </a>
              }
            />
          )}
          {state === 'ready' && scan && scan.issues.length > 0 && (
            <>
              <IssueList issues={scan.issues} limit={3} />
              <Link
                to={`/dashboard/${scan.id}`}
                className="tech-label mt-6 inline-block py-2 text-[var(--color-primary-text)] underline underline-offset-4 hover:text-[var(--color-primary-dark)]"
              >
                View all {scan.issues.length} issues →
              </Link>
            </>
          )}
          {state === 'error' && <Button size="sm" onClick={reload}>Retry</Button>}
        </div>
      </Container>
    </section>
  )
}

/* ============================================================
   COPILOT — preview of the engineering brief format
   ============================================================ */

function CopilotSection() {
  const { scan, state, reload } = useLatestScan()
  const [result, setResult] = useState<{ issueId: number; analysis: AIAnalysis } | null>(null)
  const [busy, setBusy] = useState(false)
  const [action, setAction] = useState<'analyze' | 'fix' | null>(null)
  const [aiError, setAiError] = useState('')

  const issue = scan && scan.issues.length > 0 ? sortBySeverity(scan.issues)[0] : null

  // Derived during render: prefer a freshly fetched brief, fall back to the
  // analysis the backend already cached on the issue record.
  const analysis =
    result && issue && result.issueId === issue.id ? result.analysis : (issue?.ai_analysis ?? null)

  const run = async (target: Issue, kind: 'analyze' | 'fix') => {
    setBusy(true)
    setAction(kind)
    setAiError('')
    try {
      const data = kind === 'analyze' ? await analyzeIssue(target.id) : await generateFix(target.id)
      setResult({ issueId: target.id, analysis: data })
    } catch (e) {
      setAiError(apiErrorMessage(e, 'The assistant could not be reached.'))
    } finally {
      setBusy(false)
      setAction(null)
    }
  }

  return (
    <section aria-labelledby="copilot-heading" className="border-b border-[var(--color-line)]">
      <Container className="py-20 lg:py-28">
        <div className="grid gap-12 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1fr)] lg:gap-20">
          <div>
            <SectionHeading
              index="Copilot"
              title="An engineering assistant, not a chat window"
              lede="Pick any finding and Copilot returns a structured brief: why the rule failed, what to change, and a copyable correction."
            />
            <Divider className="my-8" />
            <p className="text-sm leading-relaxed text-[var(--color-body)]">
              Output is cached against the issue, so re-opening a report does not re-bill the analysis.
            </p>
          </div>

          <div>
            {state === 'loading' && (
              <p role="status" className="tech-label text-[var(--color-subtle)]">Loading latest finding…</p>
            )}
            {state === 'error' && <Button size="sm" onClick={reload}>Retry</Button>}
            {state === 'ready' && !issue && (
              <EmptyState
                title="No findings to analyse"
                description="Once a scan records a violation, its Copilot brief appears here."
                compact
              />
            )}
            {state === 'ready' && issue && (
              <>
                <CopilotPanel
                  issue={issue}
                  analysis={analysis}
                  busy={busy}
                  action={action}
                  onAnalyze={(i) => run(i, 'analyze')}
                  onGenerateFix={(i) => run(i, 'fix')}
                />
                {aiError && <div className="mt-6"><ErrorState message={aiError} compact /></div>}
              </>
            )}
          </div>
        </div>
      </Container>
    </section>
  )
}

/* ============================================================
   HISTORY
   ============================================================ */

function HistorySection() {
  const [scans, setScans] = useState<Scan[]>([])
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState('')

  const fetchHistory = useCallback(async () => {
    try {
      const rows = await getScanHistory()
      setScans(rows)
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
    // Fetching scan records is an external-system synchronisation.
    // oxlint-disable-next-line react/set-state-in-effect
    void fetchHistory()
  }, [fetchHistory])

  return (
    <section aria-labelledby="history-heading" className="border-b border-[var(--color-line)]">
      <Container className="py-20 lg:py-28">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <SectionHeading index="Archive" title="Scan history" />
          <Link
            to="/history"
            className="tech-label py-2 text-[var(--color-primary-text)] underline underline-offset-4 hover:text-[var(--color-primary-dark)]"
          >
            View all →
          </Link>
        </div>

        <div className="mt-12">
          {state === 'loading' && (
            <p role="status" className="tech-label text-[var(--color-subtle)]">Loading history…</p>
          )}
          {state === 'error' && <ErrorState message={error} onRetry={load} compact />}
          {state === 'ready' && scans.length === 0 && (
            <EmptyState
              title="No scans recorded"
              description="Completed scans appear here with their score and issue count."
              compact
            />
          )}
          {state === 'ready' && scans.length > 0 && (
            <>
              <ScanRowHeader />
              <ul className="list-none">
                {scans.slice(0, 4).map((scan) => (
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
