import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { startScan } from '../services/api'

function Home() {
  const [url, setUrl] = useState('http://localhost:8001')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleScan = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await startScan(url)
      navigate(`/dashboard/${data.id}`)
    } catch (e: any) {
      setError(e?.response?.data?.error || 'Scan failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-white text-gray-900">
      <section className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-4xl font-bold mb-4">AI-ASSISTED ACCESSIBILITY ENGINEERING</h1>
        <p className="text-2xl mb-4">Scan. Understand. Fix.</p>
        <p className="text-xl mb-8">Build for everyone.</p>
        <p className="mb-8 max-w-2xl">
          Find real accessibility barriers in your website, understand why they matter, and get practical fixes with an AI
          engineering assistant.
        </p>
        <div className="flex gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            className="flex-1 border px-4 py-2"
            aria-label="Website URL"
          />
          <button
            onClick={handleScan}
            disabled={loading}
            className="bg-primary text-white px-6 py-2 disabled:opacity-50"
          >
            {loading ? 'Scanning...' : 'Scan website →'}
          </button>
        </div>
        {error && <p className="text-red-600 mt-4">{error}</p>}
      </section>
    </main>
  )
}

export default Home
