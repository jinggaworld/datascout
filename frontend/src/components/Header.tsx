import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, Wifi, WifiOff } from 'lucide-react'
import { getCapStatus, type CapStatus } from '../api'

export function Header() {
  const [capStatus, setCapStatus] = useState<CapStatus | null>(null)

  useEffect(() => {
    getCapStatus()
      .then(setCapStatus)
      .catch(() => setCapStatus(null))

    const interval = setInterval(() => {
      getCapStatus().then(setCapStatus).catch(() => {})
    }, 15000)
    return () => clearInterval(interval)
  }, [])

  const crooConnected = capStatus?.connection?.connected ?? false

  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-hairline">
      <div className="max-w-[1200px] mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <img
            src="/logo.png"
            alt="DataScout"
            className="w-8 h-8 object-cover group-hover:scale-110 transition-transform"
          />
          <span className="text-body-md font-semibold text-ink tracking-tight">
            DataScout
          </span>
        </Link>
        <nav className="flex items-center gap-6">
          <Link
            to="/"
            className="text-body-md text-ink-mute-2 hover:text-ink transition-colors"
          >
            Home
          </Link>
          <Link
            to="/results"
            className="text-body-md text-ink-mute-2 hover:text-ink transition-colors flex items-center gap-1.5"
          >
            <Search className="w-4 h-4" />
            Search
          </Link>

          {/* CROO Connection Status */}
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-pill text-micro-cap uppercase tracking-wider font-medium transition-colors ${
              crooConnected
                ? 'bg-green-50 text-green-700 border border-green-200'
                : 'bg-gray-50 text-gray-500 border border-gray-200'
            }`}
          >
            {crooConnected ? (
              <>
                <Wifi className="w-3 h-3" />
                <span>CROO Live</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3 h-3" />
                <span>Local Mode</span>
              </>
            )}
          </div>
        </nav>
      </div>
    </header>
  )
}
