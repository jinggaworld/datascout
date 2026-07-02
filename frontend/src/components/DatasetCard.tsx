import { ExternalLink, FileText, Tag } from 'lucide-react'
import type { DatasetResult } from '../api'

interface DatasetCardProps {
  dataset: DatasetResult
  rank?: number
  onClick?: () => void
}

export function DatasetCard({ dataset, rank, onClick }: DatasetCardProps) {
  const score = dataset.readiness_score?.total ?? 0
  const grade = dataset.readiness_score?.grade ?? 'N/A'
  const license = dataset.license_status?.license_name ?? 'Unknown'

  return (
    <div
      onClick={onClick}
      className="bg-card rounded-card border border-hairline p-5 hover:border-cta hover:shadow-md transition-all cursor-pointer group"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {rank && (
              <span className="text-xs font-mono text-muted">#{rank}</span>
            )}
            <h3 className="font-semibold text-ink truncate group-hover:text-cta transition-colors">
              {dataset.title}
            </h3>
          </div>
          <p className="text-sm text-body line-clamp-2 mt-1">
            {dataset.description || 'No description available'}
          </p>
        </div>
        <ScoreBadge score={score} grade={grade} />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-muted">
        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-canvas rounded-full">
          <FileText className="w-3 h-3" />
          {dataset.source}
        </span>
        {dataset.rows && (
          <span>{dataset.rows.toLocaleString()} rows</span>
        )}
        {dataset.file_format && (
          <span className="font-mono">{dataset.file_format}</span>
        )}
        <span className="inline-flex items-center gap-1">
          <Tag className="w-3 h-3" />
          {license}
        </span>
        {dataset.last_updated && (
          <span>Updated {new Date(dataset.last_updated).toLocaleDateString()}</span>
        )}
      </div>

      {dataset.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {dataset.tags.slice(0, 5).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs bg-canvas text-body rounded-full"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="mt-3 flex items-center gap-3">
        <a
          href={dataset.source_url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-xs text-cta hover:underline flex items-center gap-1"
        >
          View Source <ExternalLink className="w-3 h-3" />
        </a>
        {dataset.download_url && (
          <a
            href={dataset.download_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-xs text-success hover:underline"
          >
            Download
          </a>
        )}
      </div>
    </div>
  )
}

function ScoreBadge({ score, grade }: { score: number; grade: string }) {
  const color =
    grade === 'A' ? 'bg-success/10 text-success' :
    grade === 'B' ? 'bg-blue-100 text-blue-700' :
    grade === 'C' ? 'bg-yellow-100 text-yellow-700' :
    'bg-red-100 text-red-700'

  return (
    <div className={`flex flex-col items-center px-3 py-1.5 rounded-lg ${color} shrink-0`}>
      <span className="text-lg font-bold leading-none">{grade}</span>
      <span className="text-xs mt-0.5">{score.toFixed(0)}</span>
    </div>
  )
}
