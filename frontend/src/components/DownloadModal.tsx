import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, X, FileText, Table, Loader2, AlertCircle, ExternalLink } from 'lucide-react'
import { getDatasetPreview, getDatasetDownloadUrl, type PreviewData } from '../api'

interface DownloadModalProps {
  datasetId: string
  datasetTitle: string
  sourceUrl: string
  isOpen: boolean
  onClose: () => void
}

export function DownloadModal({ datasetId, datasetTitle, sourceUrl, isOpen, onClose }: DownloadModalProps) {
  const [format, setFormat] = useState<'csv' | 'json'>('csv')

  const { data, isLoading, error } = useQuery<PreviewData>({
    queryKey: ['preview', datasetId],
    queryFn: () => getDatasetPreview(datasetId),
    enabled: isOpen,
    retry: 1,
    staleTime: 5 * 60 * 1000,
  })

  if (!isOpen) return null

  const handleDownload = () => {
    const url = getDatasetDownloadUrl(datasetId, format)
    const a = document.createElement('a')
    a.href = url
    a.download = `${datasetId}.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-ink/60 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-canvas rounded-2xl border border-hairline shadow-2xl w-[95vw] max-w-5xl max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 px-6 py-5 border-b border-hairline">
          <div className="flex-1 min-w-0">
            <h2 className="text-heading-lg text-ink truncate">{datasetTitle}</h2>
            <p className="text-body-sm text-ink-mute mt-1 font-mono">{datasetId}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-ink-mute hover:text-ink hover:bg-canvas-soft transition-colors shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto px-6 py-4">
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
              <p className="text-body-md text-ink-secondary">Fetching data from source...</p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <AlertCircle className="w-8 h-8 text-ruby" />
              <p className="text-body-md text-ink-secondary">Failed to fetch preview data</p>
              <p className="text-caption text-ink-mute">{String(error)}</p>
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-canvas-soft border border-hairline rounded-lg text-body-md text-primary hover:text-primary-deep transition-colors"
              >
                Open Source <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          )}

          {data && (
            <div className="space-y-4">
              {/* Stats bar */}
              <div className="flex items-center gap-4 text-body-sm text-ink-secondary">
                <span className="inline-flex items-center gap-1.5">
                  <Table className="w-4 h-4" />
                  {data.total_rows.toLocaleString()} rows
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <FileText className="w-4 h-4" />
                  {data.columns.length} columns
                </span>
                <span className="text-ink-mute">
                  Showing {data.rows.length} of {data.total_rows.toLocaleString()}
                </span>
              </div>

              {/* Column info */}
              <div className="flex flex-wrap gap-2">
                {data.columns.slice(0, 20).map((col) => (
                  <span
                    key={col.name}
                    className="inline-flex items-center gap-1 px-2 py-0.5 bg-canvas-soft border border-hairline rounded-pill text-micro-cap text-ink-secondary"
                  >
                    <span className="font-medium">{col.name}</span>
                    <span className="text-ink-mute">({col.type})</span>
                  </span>
                ))}
                {data.columns.length > 20 && (
                  <span className="text-micro-cap text-ink-mute">+{data.columns.length - 20} more</span>
                )}
              </div>

              {/* Data table */}
              {data.rows.length > 0 ? (
                <div className="border border-hairline rounded-xl overflow-hidden">
                  <div className="overflow-auto max-h-[400px]">
                    <table className="w-full text-left">
                      <thead className="sticky top-0 z-10 bg-canvas-soft border-b border-hairline">
                        <tr>
                          <th className="px-3 py-2.5 text-micro-cap uppercase tracking-wider text-ink-mute font-semibold whitespace-nowrap">
                            #
                          </th>
                          {data.columns.slice(0, 15).map((col) => (
                            <th
                              key={col.name}
                              className="px-3 py-2.5 text-micro-cap uppercase tracking-wider text-ink-mute font-semibold whitespace-nowrap"
                            >
                              {col.name}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {data.rows.slice(0, 50).map((row, i) => (
                          <tr key={i} className="border-b border-hairline/50 hover:bg-canvas-soft/50 transition-colors">
                            <td className="px-3 py-2 text-mono text-caption text-ink-mute tabular-nums">
                              {i + 1}
                            </td>
                            {data.columns.slice(0, 15).map((col) => (
                              <td key={col.name} className="px-3 py-2 text-caption text-ink-secondary max-w-[200px] truncate">
                                {formatCell(row[col.name])}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-ink-mute text-body-md">
                  No preview data available
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-4 px-6 py-4 border-t border-hairline bg-canvas-soft/50">
          <div className="flex items-center gap-3">
            <label className="text-body-sm text-ink-secondary font-medium">Format:</label>
            <div className="flex bg-canvas border border-hairline rounded-lg overflow-hidden">
              <button
                onClick={() => setFormat('csv')}
                className={`px-4 py-1.5 text-body-sm font-medium transition-colors ${
                  format === 'csv'
                    ? 'bg-primary text-on-primary'
                    : 'text-ink-secondary hover:text-ink'
                }`}
              >
                CSV
              </button>
              <button
                onClick={() => setFormat('json')}
                className={`px-4 py-1.5 text-body-sm font-medium transition-colors ${
                  format === 'json'
                    ? 'bg-primary text-on-primary'
                    : 'text-ink-secondary hover:text-ink'
                }`}
              >
                JSON
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <a
              href={sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-body-sm text-ink-secondary hover:text-ink border border-hairline rounded-lg transition-colors"
            >
              Source <ExternalLink className="w-3.5 h-3.5" />
            </a>
            <button
              onClick={handleDownload}
              disabled={!data || data.rows.length === 0}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary text-on-primary rounded-lg text-body-sm font-medium hover:bg-primary-press transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download className="w-4 h-4" />
              Download {format.toUpperCase()}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function formatCell(value: any): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
