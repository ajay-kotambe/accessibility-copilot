import axios from 'axios'
import type { AIAnalysis, HealthResponse, Issue, Scan } from '../types'

/**
 * Defaults to a same-origin `/api` path so the Vite dev proxy (and any
 * reverse proxy in production) forwards to Django without needing CORS.
 * Set VITE_API_BASE_URL to point at an absolute URL instead.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export const api = axios.create({ baseURL: API_BASE_URL })

/** Message from a Django/DRF error response, with sensible fallbacks. */
export function apiErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === 'object' && error !== null) {
    const err = error as {
      response?: { status?: number; data?: { error?: string; detail?: string } }
      code?: string
    }
    const data = err.response?.data
    if (typeof data?.error === 'string' && data.error) return data.error
    if (typeof data?.detail === 'string' && data.detail) return data.detail
    if (err.response?.status === 400) return 'The scan request was rejected.'
    if (err.response?.status === 404) return 'That record no longer exists.'
    if (err.code === 'ERR_NETWORK') {
      return 'Cannot reach the scanner API. Confirm the backend is running.'
    }
  }
  return fallback
}

export const getHealth = async (): Promise<HealthResponse> => {
  const res = await api.get<HealthResponse>('/health/')
  return res.data
}

export const startScan = async (url: string): Promise<Scan> => {
  const res = await api.post<Scan>('/scans/', { url })
  return res.data
}

export const getScan = async (id: number): Promise<Scan> => {
  const res = await api.get<Scan>(`/scans/${id}/`)
  return res.data
}

export const getScanIssues = async (id: number): Promise<Issue[]> => {
  const res = await api.get<Issue[]>(`/scans/${id}/issues/`)
  return res.data
}

export const analyzeIssue = async (id: number): Promise<AIAnalysis> => {
  const res = await api.post<AIAnalysis>(`/issues/${id}/analyze/`)
  return res.data
}

export const generateFix = async (id: number): Promise<AIAnalysis> => {
  const res = await api.post<AIAnalysis>(`/issues/${id}/generate-fix/`)
  return res.data
}

export const getScanHistory = async (): Promise<Scan[]> => {
  const res = await api.get<Scan[]>('/scans/history/')
  return res.data
}
