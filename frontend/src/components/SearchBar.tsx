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
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-mute" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search datasets... (e.g., 'housing prices in Indonesia')"
            className={`w-full pl-11 pr-4 border border-hairline-input bg-white text-ink rounded-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all font-sans placeholder:text-ink-mute/50 ${
              compact ? 'py-2 text-body-md' : 'py-3 text-body-lg'
            }`}
          />
        </div>
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className={`bg-primary text-on-primary rounded-pill font-medium hover:bg-primary-press disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 shrink-0 ${
            compact ? 'px-4 py-2 text-button-sm' : 'px-6 py-3 text-button-md'
          }`}
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Searching
            </>
          ) : (
            <>
              <Search className="w-4 h-4" />
              Search
            </>
          )}
        </button>
      </div>
    </form>
  )
}
