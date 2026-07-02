import { Routes, Route } from 'react-router-dom'
import { Header } from './components/Header'
import { HomePage } from './pages/HomePage'
import { ResultsPage } from './pages/ResultsPage'
import { DatasetPage } from './pages/DatasetPage'

export default function App() {
  return (
    <div className="min-h-screen bg-canvas">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/dataset/:id" element={<DatasetPage />} />
        </Routes>
      </main>
    </div>
  )
}
