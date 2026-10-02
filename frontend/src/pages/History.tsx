import { useEffect, useState } from 'react'
import { getScanHistory } from '../services/api'
import { Link } from 'react-router-dom'

function History() {
  const [scans, setScans] = useState<any[]>([])

  useEffect(() => {
    getScanHistory().then(setScans)
  }, [])

  return (
    <main className="min-h-screen p-6">
      <h1 className="text-2xl font-bold mb-4">Scan History</h1>
      <ul>
        {scans.map((s) => (
          <li key={s.id} className="border p-2 mb-2">
            <Link to={`/dashboard/${s.id}`}>
              {s.url} - Score: {s.score ?? '-'} - {s.status}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  )
}

export default History
