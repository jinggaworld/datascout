import { useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ExternalLink, Download, FileText, Tag } from 'lucide-react'
import { searchDatasets, type DatasetResult, type FinalReport } from '../api'
import { ScoreBreakdown } from '../components/ScoreBreakdown'

export function DatasetPage() {
  const [searchParams] = useSearchParams()
  const datasetId = window.location.pathname.split('/').pop()

  // Search and find the dataset by ID
  const { data, isLoading } = useQuery({
    queryKey: ['search', 'detail'],
    queryFn: () => searchDatasets(datasetId || ''),
    enabled: !!datasetId,
  })

  const report: FinalReport | undefined = data?.report
  const dataset = report?.top_datasets?.find((d: DatasetResult) => d.id === datasetId)

  if (isLoading) {
    return (
      <div className="text-center py-16">
        <div className="inline-flex items-center gap-3 text-body">
          <div className="w-5 h-5 border-2 border-cta border-t-transparent rounded-full animate-spin" />
          Loading dataset...
        </div>
      </div>
    )
  }

  if (!dataset) {
    return (
      <div className="text-center py-16">
        <p className="text-muted">Dataset not found.</p>
        <Link to="/results" className="text-cta hover:underline mt-2 inline-block">
          ← Back to search
        </Link>
      </div>
    )
  }

  const citation = report?.citations?.find((c) => c.dataset_id === dataset.id)

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Back link */}
      <Link to="/results" className="inline-flex items-center gap-1 text-sm text-body hover:text-ink transition-colors">
        <ArrowLeft className="w-4 h-4" />
        Back to results
      </Link>

      {/* Header */}
      <div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-ink">{dataset.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-body">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-canvas rounded-full">
                <FileText className="w-3.5 h-3.5" />
                {dataset.source}
              </span>
              {dataset.rows && <span>{dataset.rows.toLocaleString()} rows</span>}
              {dataset.columns && <span>{dataset.columns} columns</span>}
              {dataset.file_format && <span className="font-mono text-xs">{dataset.file_format}</span>}
              {dataset.file_size_mb && <span>{dataset.file_size_mb.toFixed(1)} MB</span>}
            </div>
          </div>
          {dataset.readiness_score && (
            <div className="text-center px-4 py-2 bg-canvas rounded-card">
              <div className="text-3xl font-bold text-ink">{dataset.readiness_score.grade}</div>
              <div className="text-sm text-muted">{dataset.readiness_score.total.toFixed(0)}/100</div>
            </div>
          )}
        </div>
      </div>

      {/* Description */}
      <section>
        <h2 className="text-lg font-semibold text-ink mb-2">Description</h2>
        <p className="text-body leading-relaxed">{dataset.description || 'No description available.'}</p>
      </section>

      {/* Score Breakdown */}
      {dataset.readiness_score?.breakdown && (
        <section className="bg-card border border-hairline rounded-card p-6">
          <h2 className="text-lg font-semibold text-ink mb-4">Readiness Score Breakdown</h2>
          <ScoreBreakdown breakdown={dataset.readiness_score.breakdown} />
        </section>
      )}

      {/* License */}
      <section>
        <h2 className="text-lg font-semibold text-ink mb-2">License</h2>
        <div className="bg-card border border-hairline rounded-card p-4">
          <div className="flex items-center gap-2">
            <Tag className="w-4 h-4 text-cta" />
            <span className="font-medium">
              {dataset.license_status?.license_name || 'Unknown'}
            </span>
            {dataset.license_status?.license_type && (
              <span className="text-xs px-2 py-0.5 bg-canvas rounded-full text-muted">
                {dataset.license_status.license_type}
              </span>
            )}
          </div>
          {dataset.license_status?.needs_verification && (
            <p className="mt-2 text-sm text-yellow-700">
              ⚠️ License needs manual verification
            </p>
          )}
        </div>
      </section>

      {/* Tags */}
      {dataset.tags.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-ink mb-2">Tags</h2>
          <div className="flex flex-wrap gap-2">
            {dataset.tags.map((tag) => (
              <span key={tag} className="px-3 py-1 text-sm bg-canvas text-body rounded-full">
                {tag}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Citation */}
      {citation && (
        <section>
          <h2 className="text-lg font-semibold text-ink mb-2">Citation (APA)</h2>
          <pre className="bg-ink text-green-400 font-mono text-xs p-4 rounded-card overflow-x-auto">
            {citation.apa}
          </pre>
        </section>
      )}

      {/* Links */}
      <section className="flex flex-wrap gap-3">
        <a
          href={dataset.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2 bg-card border border-hairline rounded-button text-sm text-ink hover:border-cta transition-colors"
        >
          View Source <ExternalLink className="w-3.5 h-3.5" />
        </a>
        {dataset.download_url && (
          <a
            href={dataset.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 bg-cta text-white rounded-button text-sm hover:bg-cta-hover transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            Download Dataset
          </a>
        )}
      </section>

      {/* Proof */}
      <div className="text-center text-xs text-muted font-mono pt-4 border-t border-hairline">
        ID: {dataset.id} | Proof: {report?.hash_proof?.slice(0, 16)}...
      </div>
    </div>
  )
}
