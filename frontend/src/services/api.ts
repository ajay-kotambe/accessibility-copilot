import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
})

export interface ScanCreateResponse {
  id: number
  url: string
  status: string
  score: number | null
}

export const startScan = async (url: string) => {
  const res = await api.post('/scans/', { url })
  return res.data
}

export const getScan = async (id: number) => {
  const res = await api.get(`/scans/${id}/`)
  return res.data
}

export const getScanIssues = async (id: number) => {
  const res = await api.get(`/scans/${id}/issues/`)
  return res.data
}

export const analyzeIssue = async (id: number) => {
  const res = await api.post(`/issues/${id}/analyze/`)
  return res.data
}

export const generateFix = async (id: number) => {
  const res = await api.post(`/issues/${id}/generate-fix/`)
  return res.data
}

export const getScanHistory = async () => {
  const res = await api.get('/scans/history/')
  return res.data
}
