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
      className="bg-canvas rounded-lg border border-hairline p-6 hover:shadow-card-hover hover:border-primary/20 transition-all cursor-pointer group"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {rank && (
              <span className="text-mono text-caption text-ink-mute tabular-nums">#{rank}</span>
            )}
            <h3 className="text-heading-md text-ink truncate group-hover:text-primary transition-colors">
              {dataset.title}
            </h3>
          </div>
          <p className="text-body-md text-ink-secondary line-clamp-2 mt-1">
            {dataset.description || 'No description available'}
          </p>
        </div>
        <ScoreBadge score={score} grade={grade} />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 text-caption text-ink-mute">
        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-canvas-soft rounded-pill">
          <FileText className="w-3 h-3" />
          {dataset.source}
        </span>
        {dataset.rows && (
          <span className="tabular-nums">{dataset.rows.toLocaleString()} rows</span>
        )}
        {dataset.file_format && (
          <span className="font-mono text-micro">{dataset.file_format}</span>
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
        <div className="mt-3 flex flex-wrap gap-1.5">
          {dataset.tags.slice(0, 5).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-micro-cap uppercase tracking-wider bg-primary-subdued text-primary-deep rounded-pill"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="mt-4 flex items-center gap-3">
        <a
          href={dataset.source_url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-caption text-primary hover:text-primary-deep flex items-center gap-1 transition-colors"
        >
          View Source <ExternalLink className="w-3 h-3" />
        </a>
        {dataset.download_url && (
          <a
            href={dataset.download_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-caption text-success hover:text-success/80 transition-colors"
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
    grade === 'A' ? 'bg-success/10 text-success border-success/20' :
    grade === 'B' ? 'bg-primary/5 text-primary border-primary/10' :
    grade === 'C' ? 'bg-lemon/10 text-lemon border-lemon/20' :
    'bg-ruby/10 text-ruby border-ruby/20'

  return (
    <div className={`flex flex-col items-center px-3 py-2 rounded-lg border shrink-0 ${color}`}>
      <span className="text-display-md leading-none tabular-nums">{grade}</span>
      <span className="text-micro text-ink-mute mt-1 tabular-nums">{score.toFixed(0)}/100</span>
    </div>
  )
}
