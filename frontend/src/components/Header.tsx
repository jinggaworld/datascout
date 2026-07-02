import { Link } from 'react-router-dom'
import { Search } from 'lucide-react'

export function Header() {
  return (
    <header className="border-b border-hairline bg-white/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <img
            src="/logo.png"
            alt="DataScout"
            className="w-8 h-8 rounded-lg object-cover group-hover:scale-110 transition-transform"
          />
          <span className="text-lg font-semibold text-ink tracking-tight">
            DataScout
          </span>
        </Link>
        <nav className="flex items-center gap-6 text-sm text-body">
          <Link to="/" className="hover:text-ink transition-colors">Home</Link>
          <Link to="/results" className="hover:text-ink transition-colors flex items-center gap-1">
            <Search className="w-4 h-4" />
            Search
          </Link>
        </nav>
      </div>
    </header>
  )
}
