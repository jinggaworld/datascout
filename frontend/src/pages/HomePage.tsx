import { useNavigate } from 'react-router-dom'
import { Search, Zap, Shield, BarChart3, Globe } from 'lucide-react'
import { SearchBar } from '../components/SearchBar'

export function HomePage() {
  const navigate = useNavigate()

  const handleSearch = (query: string) => {
    navigate(`/results?q=${encodeURIComponent(query)}`)
  }

  return (
    <div className="space-y-section">
      {/* Hero */}
      <section className="text-center pt-16 pb-8">
        <h1 className="text-4xl sm:text-5xl font-bold text-ink tracking-tight leading-tight">
          Find the right dataset
          <br />
          <span className="text-cta">in seconds</span>
        </h1>
        <p className="mt-4 text-lg text-body max-w-xl mx-auto">
          DataScout searches 10+ sources simultaneously — HuggingFace, Kaggle, data.gov, World Bank, and more — then ranks, scores, and reports the best datasets for your query.
        </p>
        <div className="mt-8">
          <SearchBar onSearch={handleSearch} />
        </div>
        <p className="mt-3 text-sm text-muted">
          Try: "housing prices in Indonesia", "climate temperature data", "sentiment analysis reviews"
        </p>
      </section>

      {/* Features */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { icon: Globe, title: '10+ Sources', desc: 'Search HuggingFace, Kaggle, data.gov, World Bank, FRED, NOAA, OpenML, Zenodo, OpenAQ, arXiv simultaneously' },
          { icon: Zap, title: 'Real-time Scoring', desc: 'Each dataset scored on completeness, freshness, size, documentation, and license clarity' },
          { icon: Shield, title: 'License Detection', desc: 'Automatically identifies CC-BY, MIT, Apache, and other licenses — flags unknown for manual review' },
          { icon: BarChart3, title: 'Smart Ranking', desc: 'Relevance ranking considers keyword match, freshness, size, documentation quality, and source diversity' },
        ].map((f) => (
          <div key={f.title} className="bg-card rounded-card border border-hairline p-5 hover:border-cta/30 transition-colors">
            <f.icon className="w-8 h-8 text-cta mb-3" />
            <h3 className="font-semibold text-ink">{f.title}</h3>
            <p className="mt-1 text-sm text-body">{f.desc}</p>
          </div>
        ))}
      </section>
    </div>
  )
}
