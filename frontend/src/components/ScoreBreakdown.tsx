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
  { key: 'freshness' as const, label: 'Freshness', color: '#533afd' },
  { key: 'size' as const, label: 'Size', color: '#665efd' },
  { key: 'documentation' as const, label: 'Documentation', color: '#9b6829' },
  { key: 'license' as const, label: 'License', color: '#ea2261' },
]

export function ScoreBreakdown({ breakdown }: ScoreBreakdownProps) {
  return (
    <div className="space-y-4">
      {BARS.map((bar) => {
        const value = breakdown[bar.key]
        const pct = Math.round(value * 100)
        return (
          <div key={bar.key} className="flex items-center gap-4">
            <span className="w-32 text-body-md text-ink-secondary shrink-0">{bar.label}</span>
            <div className="flex-1 h-2 bg-canvas-soft rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700 ease-out"
                style={{ width: `${pct}%`, backgroundColor: bar.color }}
              />
            </div>
            <span className="w-12 text-right text-body-tabular text-ink-mute shrink-0 tabular-nums">
              {pct}
            </span>
          </div>
        )
      })}
    </div>
  )
}
