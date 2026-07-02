import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, Clock, Database } from 'lucide-react'
import { searchDatasets, type DatasetResult } from '../api'
import { SearchBar } from '../components/SearchBar'
import { DatasetCard } from '../components/DatasetCard'

export function ResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const query = searchParams.get('q') || ''
  const [sortBy, setSortBy] = useState<'score' | 'rows' | 'freshness'>('score')
  const [filterSource, setFilterSource] = useState<string>('all')

  const { data, isLoading, error } = useQuery({
    queryKey: ['search', query],
    queryFn: () => searchDatasets(query),
    enabled: !!query,
  })

  const handleSearch = (q: string) => {
    setSearchParams({ q })
  }

  const sources = data?.report?.top_datasets
    ? [...new Set(data.report.top_datasets.map((d: DatasetResult) => d.source))]
    : []

  let datasets = data?.report?.top_datasets || []
  if (filterSource !== 'all') {
    datasets = datasets.filter((d: DatasetResult) => d.source === filterSource)
  }
  datasets = [...datasets].sort((a: DatasetResult, b: DatasetResult) => {
    if (sortBy === 'rows') return (b.rows || 0) - (a.rows || 0)
    if (sortBy === 'freshness') return (b.last_updated || '').localeCompare(a.last_updated || '')
    return (b.readiness_score?.total || 0) - (a.readiness_score?.total || 0)
  })

  return (
    <div className="space-y-6">
      {/* Search bar */}
      <div className="py-6">
        <SearchBar onSearch={handleSearch} defaultValue={query} compact />
      </div>

      {/* Error */}
      {error && (
        <div className="bg-ruby/5 border border-ruby/20 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-ruby shrink-0" />
          <p className="text-body-md text-ruby">{(error as Error).message}</p>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="text-center py-20">
          <div className="inline-flex items-center gap-3 text-ink-secondary">
            <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-body-md">Searching 10 sources simultaneously...</span>
          </div>
        </div>
      )}

      {/* Results */}
      {data && !isLoading && (
        <>
          {/* Stats bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 text-body-md text-ink-mute">
            <div className="flex items-center gap-5">
              <span className="flex items-center gap-1.5">
                <Database className="w-4 h-4" />
                <span className="tabular-nums">{data.report.total_results_found}</span> datasets found
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="w-4 h-4" />
                <span className="tabular-nums">{data.elapsed_ms}</span>ms
              </span>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                className="px-3 py-1.5 border border-hairline-input rounded-sm text-body-md bg-white text-ink focus:outline-none focus:border-primary"
              >
                <option value="score">By Score</option>
                <option value="rows">By Size</option>
                <option value="freshness">By Freshness</option>
              </select>
              {sources.length > 1 && (
                <select
                  value={filterSource}
                  onChange={(e) => setFilterSource(e.target.value)}
                  className="px-3 py-1.5 border border-hairline-input rounded-sm text-body-md bg-white text-ink focus:outline-none focus:border-primary"
                >
                  <option value="all">All Sources</option>
                  {sources.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              )}
            </div>
          </div>

          {/* Summary */}
          <p className="text-body-md text-ink-secondary bg-canvas-soft border border-hairline rounded-lg p-5">
            {data.report.summary}
          </p>

          {/* Dataset grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {datasets.map((d: DatasetResult, i: number) => (
              <DatasetCard key={d.id} dataset={d} rank={i + 1} />
            ))}
          </div>

          {datasets.length === 0 && (
            <div className="text-center py-20 text-ink-mute">
              <p className="text-body-lg">No datasets match your filters.</p>
            </div>
          )}

          {/* Hash proof */}
          {data.report.hash_proof && (
            <div className="text-center text-micro text-ink-mute font-mono pt-6">
              Proof: {data.report.hash_proof.slice(0, 16)}...
            </div>
          )}
        </>
      )}
    </div>
  )
}
