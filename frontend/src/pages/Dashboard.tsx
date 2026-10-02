import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getScan, getScanIssues, analyzeIssue, generateFix } from '../services/api'

function Dashboard() {
  const { scanId } = useParams()
  const [scan, setScan] = useState<any>(null)
  const [issues, setIssues] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
  const [ai, setAi] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    if (!scanId) return
    const s = await getScan(Number(scanId))
    setScan(s)
    const i = await getScanIssues(Number(scanId))
    setIssues(i)
  }

  useEffect(() => {
    fetchData()
  }, [scanId])

  const askCopilot = async (id: number) => {
    setLoading(true)
    const res = await analyzeIssue(id)
    setAi(res)
    setLoading(false)
  }

  const genFix = async (id: number) => {
    setLoading(true)
    const res = await generateFix(id)
    setAi(res)
    setLoading(false)
  }

  return (
    <main className="min-h-screen p-6">
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
      {scan && (
        <div className="mb-6">
          <p>URL: {scan.url}</p>
          <p>Status: {scan.status}</p>
          <p>Score: {scan.score ?? '-'}</p>
        </div>
      )}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <h2 className="text-xl mb-2">Issues</h2>
          {issues.map((iss) => (
            <button
              key={iss.id}
              onClick={() => {
                setSelected(iss)
                setAi(null)
              }}
              className="block border p-2 mb-2 w-full text-left"
            >
              <span className="font-bold">{iss.severity}</span> {iss.rule_id} - {iss.description}
            </button>
          ))}
        </div>
        <div>
          {selected && (
            <div className="border p-4">
              <h3 className="font-bold">{selected.rule_id}</h3>
              <p>{selected.severity}</p>
              <p>{selected.description}</p>
              <p className="mt-2 font-semibold">Selector</p>
              <pre className="bg-gray-100 p-2">{selected.selector}</pre>
              <p className="mt-2 font-semibold">HTML</p>
              <pre className="bg-gray-100 p-2 overflow-x-auto">{selected.html_snippet}</pre>
              <div className="flex gap-2 mt-4">
                <button onClick={() => askCopilot(selected.id)} disabled={loading} className="bg-primary text-white px-4 py-2">
                  Ask Copilot
                </button>
                <button onClick={() => genFix(selected.id)} disabled={loading} className="border px-4 py-2">
                  Generate Fix
                </button>
              </div>
              {ai && (
                <div className="mt-4">
                  <h4 className="font-bold">Explanation</h4>
                  <p>{ai.explanation}</p>
                  <h4 className="font-bold mt-2">Why it matters</h4>
                  <p>{ai.why_it_matters}</p>
                  <h4 className="font-bold mt-2">Suggested fix</h4>
                  <p>{ai.suggested_fix}</p>
                  <h4 className="font-bold mt-2">Corrected code</h4>
                  <pre className="bg-gray-100 p-2 overflow-x-auto">{ai.corrected_code}</pre>
                  <button
                    onClick={() => navigator.clipboard.writeText(ai.corrected_code)}
                    className="border px-2 py-1 mt-2"
                  >
                    Copy code
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  )
}

export default Dashboard
