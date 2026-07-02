import { Link } from 'react-router-dom'
import { Search } from 'lucide-react'

export function Header() {
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
        <nav className="flex items-center gap-8">
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
        </nav>
      </div>
    </header>
  )
}
