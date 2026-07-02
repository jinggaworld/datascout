interface ScoreBreakdownProps {
  breakdown: {
    completeness: number
    freshness: number
    size: number
    documentation: number
    license: number
  }
}

const BARS = [
  { key: 'completeness' as const, label: 'Completeness', color: '#1f8a65' },
  { key: 'freshness' as const, label: 'Freshness', color: '#3b82f6' },
  { key: 'size' as const, label: 'Size', color: '#8b5cf6' },
  { key: 'documentation' as const, label: 'Documentation', color: '#f59e0b' },
  { key: 'license' as const, label: 'License', color: '#f54e00' },
]

export function ScoreBreakdown({ breakdown }: ScoreBreakdownProps) {
  return (
    <div className="space-y-3">
      {BARS.map((bar) => {
        const value = breakdown[bar.key]
        const pct = Math.round(value * 100)
        return (
          <div key={bar.key} className="flex items-center gap-3">
            <span className="w-28 text-sm text-body shrink-0">{bar.label}</span>
            <div className="flex-1 h-3 bg-canvas rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${pct}%`, backgroundColor: bar.color }}
              />
            </div>
            <span className="w-10 text-right text-sm font-mono text-muted shrink-0">
              {pct}
            </span>
          </div>
        )
      })}
    </div>
  )
}
