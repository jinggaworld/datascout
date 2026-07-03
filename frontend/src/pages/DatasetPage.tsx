import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ExternalLink, Download, FileText, Tag } from 'lucide-react'
import { searchDatasets, type DatasetResult, type FinalReport } from '../api'
import { ScoreBreakdown } from '../components/ScoreBreakdown'
import { stripHtml } from '../utils/html'

export function DatasetPage() {
  const datasetId = window.location.pathname.split('/').pop()

  const { data, isLoading } = useQuery({
    queryKey: ['search', 'detail'],
    queryFn: () => searchDatasets(datasetId || ''),
    enabled: !!datasetId,
  })

  const report: FinalReport | undefined = data?.report
  const dataset = report?.top_datasets?.find((d: DatasetResult) => d.id === datasetId)

  if (isLoading) {
    return (
      <div className="text-center py-20">
        <div className="inline-flex items-center gap-3 text-ink-secondary">
          <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-body-md">Loading dataset...</span>
        </div>
      </div>
    )
  }

  if (!dataset) {
    return (
      <div className="text-center py-20">
        <p className="text-body-lg text-ink-mute">Dataset not found.</p>
        <Link to="/results" className="text-body-md text-primary hover:text-primary-deep mt-3 inline-block transition-colors">
          Back to search
        </Link>
      </div>
    )
  }

  const citation = report?.citations?.find((c) => c.dataset_id === dataset.id)

  return (
    <div className="max-w-4xl mx-auto space-y-10">
      {/* Back link */}
      <Link to="/results" className="inline-flex items-center gap-1.5 text-body-md text-ink-mute hover:text-ink transition-colors">
        <ArrowLeft className="w-4 h-4" />
        Back to results
      </Link>

      {/* Header */}
      <div>
        <div className="flex items-start justify-between gap-6">
          <div>
            <h1 className="text-display-lg text-ink">{dataset.title}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-body-md text-ink-secondary">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 bg-canvas-soft rounded-pill">
                <FileText className="w-3.5 h-3.5" />
                {dataset.source}
              </span>
              {dataset.rows && <span className="tabular-nums">{dataset.rows.toLocaleString()} rows</span>}
              {dataset.columns && <span className="tabular-nums">{dataset.columns} columns</span>}
              {dataset.file_format && <span className="font-mono text-micro">{dataset.file_format}</span>}
              {dataset.file_size_mb && <span className="tabular-nums">{dataset.file_size_mb.toFixed(1)} MB</span>}
            </div>
          </div>
          {dataset.readiness_score && (
            <div className="text-center px-5 py-3 bg-canvas-soft border border-hairline rounded-lg shrink-0">
              <div className="text-display-lg text-ink tabular-nums">{dataset.readiness_score.grade}</div>
              <div className="text-micro text-ink-mute mt-0.5 tabular-nums">{dataset.readiness_score.total.toFixed(0)}/100</div>
            </div>
          )}
        </div>
      </div>

      {/* Description */}
      <section>
        <h2 className="text-heading-lg text-ink mb-3">Description</h2>
        <p className="text-body-md text-ink-secondary leading-relaxed">{stripHtml(dataset.description) || 'No description available.'}</p>
      </section>

      {/* Score Breakdown */}
      {dataset.readiness_score?.breakdown && (
        <section className="bg-canvas border border-hairline rounded-lg p-8">
          <h2 className="text-heading-lg text-ink mb-5">Readiness Score Breakdown</h2>
          <ScoreBreakdown breakdown={dataset.readiness_score.breakdown} />
        </section>
      )}

      {/* License */}
      <section>
        <h2 className="text-heading-lg text-ink mb-3">License</h2>
        <div className="bg-canvas border border-hairline rounded-lg p-5">
          <div className="flex items-center gap-2">
            <Tag className="w-4 h-4 text-primary" />
            <span className="text-body-md font-medium text-ink">
              {dataset.license_status?.license_name || 'Unknown'}
            </span>
            {dataset.license_status?.license_type && (
              <span className="text-micro-cap uppercase tracking-wider px-2 py-0.5 bg-primary-subdued text-primary-deep rounded-pill">
                {dataset.license_status.license_type}
              </span>
            )}
          </div>
          {dataset.license_status?.needs_verification && (
            <p className="mt-3 text-body-md text-lemon">
              License needs manual verification
            </p>
          )}
        </div>
      </section>

      {/* Tags */}
      {dataset.tags.length > 0 && (
        <section>
          <h2 className="text-heading-lg text-ink mb-3">Tags</h2>
          <div className="flex flex-wrap gap-2">
            {dataset.tags.map((tag) => (
              <span key={tag} className="px-3 py-1 text-micro-cap uppercase tracking-wider bg-primary-subdued text-primary-deep rounded-pill">
                {tag}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Citation */}
      {citation && (
        <section>
          <h2 className="text-heading-lg text-ink mb-3">Citation (APA)</h2>
          <pre className="bg-brand-dark text-primary-soft font-mono text-micro p-5 rounded-lg overflow-x-auto leading-relaxed">
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
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-canvas border border-hairline rounded-pill text-body-md text-ink hover:border-primary hover:text-primary transition-all"
        >
          View Source <ExternalLink className="w-3.5 h-3.5" />
        </a>
        {dataset.download_url && (
          <a
            href={dataset.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary text-on-primary rounded-pill text-body-md hover:bg-primary-press transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            Download Dataset
          </a>
        )}
      </section>

      {/* Proof */}
      <div className="text-center text-micro text-ink-mute font-mono pt-6 border-t border-hairline">
        ID: {dataset.id} | Proof: {report?.hash_proof?.slice(0, 16)}...
      </div>
    </div>
  )
}
