import { useNavigate } from 'react-router-dom'
import { Globe, Zap, Shield, BarChart3 } from 'lucide-react'
import { SearchBar } from '../components/SearchBar'

export function HomePage() {
  const navigate = useNavigate()

  const handleSearch = (query: string) => {
    navigate(`/results?q=${encodeURIComponent(query)}`)
  }

  return (
    <div>
      {/* Hero with gradient mesh backdrop */}
      <section className="relative -mx-4 sm:-mx-6 lg:-mx-8 overflow-hidden">
        <div className="gradient-mesh-bg min-h-[480px] flex flex-col items-center justify-center px-6 py-24">
          <h1 className="text-display-xxl text-ink text-center max-w-3xl">
            Find the right dataset
            <br />
            <span className="text-primary">in seconds</span>
          </h1>
          <p className="mt-5 text-body-lg text-ink-secondary max-w-xl text-center">
            DataScout searches 10+ sources simultaneously, then ranks, scores,
            and reports the best datasets for your query.
          </p>
          <div className="mt-8 w-full max-w-2xl">
            <SearchBar onSearch={handleSearch} />
          </div>
          <p className="mt-4 text-caption text-ink-mute text-center">
            Try: "housing prices in Indonesia", "climate temperature data", "sentiment analysis reviews"
          </p>
        </div>
      </section>

      {/* Features on canvas-soft */}
      <section className="bg-canvas-soft -mx-4 sm:-mx-6 lg:-mx-8 px-6 py-16 mt-0">
        <div className="max-w-[1200px] mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              { icon: Globe, title: '10+ Sources', desc: 'Search HuggingFace, Kaggle, data.gov, World Bank, FRED, NOAA, OpenML, Zenodo, OpenAQ, arXiv simultaneously.' },
              { icon: Zap, title: 'Real-time Scoring', desc: 'Each dataset scored on completeness, freshness, size, documentation, and license clarity.' },
              { icon: Shield, title: 'License Detection', desc: 'Automatically identifies CC-BY, MIT, Apache, and other licenses. Flags unknown for manual review.' },
              { icon: BarChart3, title: 'Smart Ranking', desc: 'Relevance ranking considers keyword match, freshness, size, documentation quality, and source diversity.' },
            ].map((f) => (
              <div
                key={f.title}
                className="bg-canvas rounded-lg border border-hairline p-8 hover:shadow-card transition-shadow"
              >
                <div className="w-10 h-10 rounded-lg bg-primary/5 flex items-center justify-center mb-4">
                  <f.icon className="w-5 h-5 text-primary" />
                </div>
                <h3 className="text-heading-lg text-ink">{f.title}</h3>
                <p className="mt-2 text-body-md text-ink-secondary leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Cream band — how it works */}
      <section className="bg-canvas-cream -mx-4 sm:-mx-6 lg:-mx-8 px-6 py-16">
        <div className="max-w-[1200px] mx-auto">
          <h2 className="text-display-lg text-ink text-center mb-12">How it works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { step: '01', title: 'Ask', desc: 'Type a natural language query like "find climate datasets for Southeast Asia".' },
              { step: '02', title: 'Search', desc: 'DataScout queries 10+ dataset sources in parallel, deduplicates, and ranks results.' },
              { step: '03', title: 'Report', desc: 'Get a ranked report with readiness scores, license status, citations, and download links.' },
            ].map((s) => (
              <div key={s.step} className="text-center">
                <span className="text-display-xl text-primary/20 font-mono tabular-nums">{s.step}</span>
                <h3 className="text-heading-lg text-ink mt-2">{s.title}</h3>
                <p className="mt-2 text-body-md text-ink-secondary">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
