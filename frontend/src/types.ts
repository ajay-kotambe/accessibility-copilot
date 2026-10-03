export type ScanStatus =
  | 'QUEUED'
  | 'CONNECTING'
  | 'LOADING'
  | 'SCANNING'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED'

export type Severity = 'CRITICAL' | 'SERIOUS' | 'MODERATE' | 'MINOR'

export interface AIAnalysis {
  explanation: string
  why_it_matters: string
  suggested_fix: string
  corrected_code: string
  developer_tip: string
}

export interface ScannedPage {
  id: number
  url: string
  title: string
}

export interface Issue {
  id: number
  rule_id: string
  severity: Severity
  category: string
  description: string
  selector: string
  html_snippet: string
  help_url: string
  impact: string
  ai_analysis: AIAnalysis | null
}

export interface Scan {
  id: number
  url: string
  status: ScanStatus
  score: number | null
  started_at: string | null
  completed_at: string | null
  error_message: string
  pages: ScannedPage[]
  issues: Issue[]
}

export interface HealthResponse {
  status: string
}
