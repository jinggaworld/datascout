import { useState } from 'react'
import { Search, Loader2 } from 'lucide-react'

interface SearchBarProps {
  onSearch: (query: string) => void
  isLoading?: boolean
  defaultValue?: string
  compact?: boolean
}

export function SearchBar({ onSearch, isLoading, defaultValue = '', compact = false }: SearchBarProps) {
  const [query, setQuery] = useState(defaultValue)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) onSearch(query.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search datasets... (e.g., 'housing prices in Indonesia')"
          className={`w-full pl-12 pr-4 border border-hairline bg-white text-ink rounded-card focus:outline-none focus:border-cta focus:ring-1 focus:ring-cta/20 transition-all font-sans placeholder:text-muted/60 ${
            compact ? 'py-2.5 text-sm' : 'py-4 text-base'
          }`}
        />
      </div>
      <button
        type="submit"
        disabled={isLoading || !query.trim()}
        className={`mt-3 w-full bg-cta text-white rounded-button font-medium hover:bg-cta-hover disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 ${
          compact ? 'py-2 text-sm' : 'py-3 text-base'
        }`}
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Searching...
          </>
        ) : (
          <>
            <Search className="w-4 h-4" />
            Search Datasets
          </>
        )}
      </button>
    </form>
  )
}
