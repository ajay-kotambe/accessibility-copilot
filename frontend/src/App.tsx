import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import History from './pages/History'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard/:scanId" element={<Dashboard />} />
        <Route path="/history" element={<History />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
