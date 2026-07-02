import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle, Clock, Database, Filter } from 'lucide-react'
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

  // Get unique sources for filter
  const sources = data?.report?.top_datasets
    ? [...new Set(data.report.top_datasets.map((d: DatasetResult) => d.source))]
    : []

  // Filter and sort datasets
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
        <div className="bg-error/10 border border-error/30 rounded-card p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-error shrink-0" />
          <p className="text-sm text-error">{(error as Error).message}</p>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="text-center py-16">
          <div className="inline-flex items-center gap-3 text-body">
            <div className="w-5 h-5 border-2 border-cta border-t-transparent rounded-full animate-spin" />
            Searching 10 sources simultaneously...
          </div>
        </div>
      )}

      {/* Results */}
      {data && !isLoading && (
        <>
          {/* Stats bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 text-sm text-body">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <Database className="w-4 h-4" />
                {data.report.total_results_found} datasets found
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                {data.elapsed_ms}ms
              </span>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                className="px-2 py-1 border border-hairline rounded-button text-xs bg-white"
              >
                <option value="score">By Score</option>
                <option value="rows">By Size</option>
                <option value="freshness">By Freshness</option>
              </select>
              {sources.length > 1 && (
                <select
                  value={filterSource}
                  onChange={(e) => setFilterSource(e.target.value)}
                  className="px-2 py-1 border border-hairline rounded-button text-xs bg-white"
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
          <p className="text-sm text-body bg-card border border-hairline rounded-card p-4">
            {data.report.summary}
          </p>

          {/* Dataset grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {datasets.map((d: DatasetResult, i: number) => (
              <DatasetCard key={d.id} dataset={d} rank={i + 1} />
            ))}
          </div>

          {datasets.length === 0 && (
            <div className="text-center py-16 text-muted">
              No datasets match your filters.
            </div>
          )}

          {/* Hash proof */}
          {data.report.hash_proof && (
            <div className="text-center text-xs text-muted font-mono mt-8">
              Proof: {data.report.hash_proof.slice(0, 16)}...
            </div>
          )}
        </>
      )}
    </div>
  )
}
