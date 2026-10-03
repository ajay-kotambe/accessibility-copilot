import type { AIAnalysis, Issue } from '../types'
import { CodeBlock } from './ui/CodeBlock'
import { Button } from './ui/Button'
import { SeverityBadge } from './ui/SeverityBadge'

/**
 * Copilot output as a structured engineering brief:
 * RULE / WHY THIS MATTERS / SUGGESTED FIX / CORRECTED CODE.
 * All content originates from the backend AIAnalysis record.
 */
export function CopilotPanel({
  issue,
  analysis,
  busy,
  action,
  onAnalyze,
  onGenerateFix,
}: {
  issue: Issue | null
  analysis: AIAnalysis | null
  busy: boolean
  action: 'analyze' | 'fix' | null
  onAnalyze: (issue: Issue) => void
  onGenerateFix: (issue: Issue) => void
}) {
  if (!issue) {
    return (
      <div className="border border-dashed border-[var(--color-line-strong)] p-8">
        <p className="tech-label text-[var(--color-subtle)]">Copilot analysis</p>
        <p className="mt-4 max-w-sm text-sm leading-relaxed text-[var(--color-body)]">
          Select an issue to get an explanation of the failure, why it matters, and a focused
          correction you can copy into your codebase.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-5">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <p className="tech-label text-[var(--color-subtle)]">Copilot analysis</p>
          <SeverityBadge severity={issue.severity} />
        </div>
      </div>

      {/* dt/dd are direct children of dl: wrapping each pair in a div is valid
          HTML but axe's dlitem rule does not traverse the wrapper. */}
      <dl className="border-y border-[var(--color-line)]">
        <dt className="tech-label border-t border-[var(--color-line)] py-5 pl-4 text-[var(--color-subtle)] first:border-t-0 sm:pl-0">
          Rule
        </dt>
        <dd className="min-w-0 pb-5 pl-4 sm:pl-0">
          <span className="font-mono text-sm text-[var(--color-ink-fg)]">{issue.rule_id}</span>
          {issue.help_url && (
            <a
              href={issue.help_url}
              target="_blank"
              rel="noreferrer noopener"
              className="tech-label ml-4 text-[var(--color-primary-text)] underline underline-offset-4 hover:text-[var(--color-primary-dark)]"
            >
              Rule documentation ↗
            </a>
          )}
        </dd>

        {issue.selector && (
          <>
            <dt className="tech-label border-t border-[var(--color-line)] py-5 pl-4 text-[var(--color-subtle)] sm:pl-0">
              Selector
            </dt>
            <dd
              tabIndex={0}
              className="min-w-0 overflow-x-auto pb-5 pl-4 font-mono text-xs text-[var(--color-body)] sm:pl-0"
            >
              {issue.selector}
            </dd>
          </>
        )}

        {issue.html_snippet && (
          <>
            <dt className="tech-label border-t border-[var(--color-line)] py-5 pl-4 text-[var(--color-subtle)] sm:pl-0">
              Affected HTML
            </dt>
            <dd className="min-w-0 pb-5 pl-4 sm:pl-0">
              <CodeBlock code={issue.html_snippet} label="Snippet" language="html" copyable={false} />
            </dd>
          </>
        )}
      </dl>

      {!analysis && (
        <div className="mt-6 flex flex-wrap gap-3">
          <Button variant="primary" size="sm" disabled={busy} onClick={() => onAnalyze(issue)}>
            {busy && action === 'analyze' ? 'Analysing' : 'Explain issue'}
          </Button>
          <Button size="sm" disabled={busy} onClick={() => onGenerateFix(issue)}>
            {busy && action === 'fix' ? 'Generating' : 'Generate fix'}
          </Button>
        </div>
      )}

      {busy && !analysis && (
        <p role="status" aria-live="polite" className="mt-4 tech-label text-[var(--color-subtle)]">
          Requesting analysis…
        </p>
      )}

      {analysis && (
        <div className="mt-8 space-y-8">
          <Prose term="Why this matters" body={analysis.why_it_matters || analysis.explanation} />
          <Prose term="Suggested fix" body={analysis.suggested_fix} />
          {analysis.corrected_code && (
            <div>
              <p className="tech-label mb-3 text-[var(--color-subtle)]">Corrected code</p>
              <CodeBlock code={analysis.corrected_code} label="Patch" language="html" />
            </div>
          )}
          {analysis.developer_tip && (
            <Prose term="Developer tip" body={analysis.developer_tip} />
          )}

          <div className="border-t border-[var(--color-line)] pt-6">
            <Button size="sm" onClick={() => onGenerateFix(issue)} disabled={busy}>
              Regenerate fix
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function Prose({ term, body }: { term: string; body: string }) {
  if (!body.trim()) return null
  return (
    <div>
      <p className="tech-label mb-3 text-[var(--color-subtle)]">{term}</p>
      <p className="max-w-2xl text-[0.9375rem] leading-relaxed whitespace-pre-line text-[var(--color-body)]">
        {body}
      </p>
    </div>
  )
}
