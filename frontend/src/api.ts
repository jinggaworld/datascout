const API_BASE = import.meta.env.VITE_API_URL || ''

export interface DatasetResult {
  id: string
  title: string
  description: string
  source: string
  source_url: string
  download_url: string | null
  rows: number | null
  columns: number | null
  file_size_mb: number | null
  file_format: string | null
  last_updated: string | null
  relevance_score: number
  readiness_score: {
    total: number
    grade: string
    breakdown: {
      completeness: number
      freshness: number
      size: number
      documentation: number
      license: number
    }
  } | null
  license_status: {
    detected: boolean
    license_type: string
    license_name: string | null
    needs_verification: boolean
  }
  tags: string[]
  domain: string
  region: string | null
  merged_from: string[]
}

export interface FinalReport {
  query: {
    topic: string
    keywords: string[]
    domain: string
    region: string | null
  }
  timestamp: string
  total_sources_searched: number
  total_results_found: number
  deduped_results: number
  top_datasets: DatasetResult[]
  summary: string
  domain_distribution: Record<string, number>
  source_distribution: Record<string, number>
  citations: { dataset_id: string; apa: string; bibtex: string }[]
  hash_proof: string
}

export interface SearchResponse {
  status: string
  elapsed_ms: number
  report: FinalReport
  markdown: string
}

export interface CapStatus {
  connection: {
    connected: boolean
    agent_id: string
    wallet: string
    ws_url: string
    api_url: string
    has_sdk_key: boolean
  }
  orders: {
    total_orders: number
    by_status: Record<string, number>
  }
  version: string
}

export interface NegotiationResult {
  status: string
  parsed_query: {
    topic: string
    domain: string
    region: string | null
  }
  negotiation: {
    base_price_usdc: number
    source_count: number
    source_cost_usdc: number
    extras_cost_usdc: number
    total_price_usdc: number
    estimated_search_time_sec: number
    description: string
  }
}

export async function searchDatasets(query: string): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/api/v1/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Search failed' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getCapStatus(): Promise<CapStatus> {
  const res = await fetch(`${API_BASE}/api/v1/cap/status`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function negotiatePrice(query: string): Promise<NegotiationResult> {
  const res = await fetch(`${API_BASE}/api/v1/cap/negotiate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
