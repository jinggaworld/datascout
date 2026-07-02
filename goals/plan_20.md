# Plan 20: Frontend UI
**DataScout — CROO Agent Hackathon**

---

## Overview

Frontend web interface menggunakan React + Tailwind CSS dengan design system Cursor-style dari `goals/design.md`. Warm cream canvas, orange CTAs, JetBrains Mono untuk code surfaces.

**Dependensi:** plan_19 (Report Generator)

---

## Tech Stack

```
Framework: React 18 + Vite
Styling: Tailwind CSS
State: React Query (TanStack Query)
HTTP: Fetch API / Axios
Charts: Recharts
Fonts: Inter (substitute for CursorGothic) + JetBrains Mono
```

---

## Design System (from design.md)

```
Colors:
  Primary (CTA): #f54e00 (Cursor Orange)
  Canvas: #f7f7f4 (warm cream)
  Ink: #26251e (warm near-black)
  Body: #5a5852
  Card: #ffffff
  Hairline: #e6e5e0
  Success: #1f8a65
  Error: #cf2d56

Typography:
  Display: Inter 400, -1.5% letter-spacing
  Body: Inter 400, 16px
  Code: JetBrains Mono 13px

Spacing:
  Section: 80px
  Card: 24px padding
  Border-radius: 8px (buttons), 12px (cards)
```

---

## Pages & Components

### 1. Home Page (`/`)
- Hero section with search input
- Feature cards (How it Works)
- Recent searches (if cached)

### 2. Search Results Page (`/results`)
- Query summary bar
- Filter sidebar
- Dataset cards grid
- Sorting options

### 3. Dataset Detail Page (`/dataset/:id`)
- Full metadata display
- Preview table (sample rows)
- Readiness score breakdown
- License info
- Download link + manifest

### 4. Comparison Page (`/compare`)
- Side-by-side dataset comparison
- Feature matrix table

---

## Key Components

### SearchBar
```tsx
export function SearchBar() {
  return (
    <div className="w-full max-w-2xl mx-auto">
      <input
        type="text"
        placeholder="Search datasets... (e.g., 'housing prices in Indonesia')"
        className="w-full px-4 py-3 rounded-lg border border-[#e6e5e0] bg-white text-[#26251e] font-[Inter] text-base focus:outline-none focus:border-[#f54e00]"
      />
      <button className="mt-3 px-6 py-2 bg-[#f54e00] text-white rounded-lg font-[Inter] text-sm font-medium hover:bg-[#d04200] transition-colors">
        Search
      </button>
    </div>
  );
}
```

### DatasetCard
```tsx
export function DatasetCard({ dataset }: { dataset: DatasetResult }) {
  return (
    <div className="bg-white rounded-xl border border-[#e6e5e0] p-6 hover:border-[#f54e00] transition-colors">
      <div className="flex items-start justify-between">
        <h3 className="font-[Inter] text-lg font-semibold text-[#26251e]">
          {dataset.title}
        </h3>
        <span className="px-2 py-1 bg-[#f7f7f4] rounded-full text-xs font-[Inter] text-[#5a5852]">
          {dataset.source}
        </span>
      </div>
      <p className="mt-2 text-sm text-[#5a5852] line-clamp-2">
        {dataset.description}
      </p>
      <div className="mt-4 flex items-center gap-4 text-xs text-[#807d72]">
        <span>Score: {dataset.readiness_score?.total || 'N/A'}/100</span>
        <span>License: {dataset.license_status?.license_name || 'Unknown'}</span>
      </div>
    </div>
  );
}
```

### ScoreBreakdown
```tsx
export function ScoreBreakdown({ score }: { score: ReadinessScore }) {
  const bars = [
    { label: 'Completeness', value: score.breakdown.completeness, color: '#9fc9a2' },
    { label: 'Freshness', value: score.breakdown.freshness, color: '#9fbbe0' },
    { label: 'Size', value: score.breakdown.size, color: '#c0a8dd' },
    { label: 'Documentation', value: score.breakdown.documentation, color: '#dfa88f' },
    { label: 'License', value: score.breakdown.license, color: '#c08532' },
  ];

  return (
    <div className="space-y-2">
      {bars.map(bar => (
        <div key={bar.label} className="flex items-center gap-3">
          <span className="w-24 text-xs text-[#807d72]">{bar.label}</span>
          <div className="flex-1 h-2 bg-[#f7f7f4] rounded-full">
            <div
              className="h-full rounded-full"
              style={{ width: `${bar.value * 100}%`, backgroundColor: bar.color }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## API Integration

```typescript
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function searchDatasets(query: string) {
  const res = await fetch(`${API_BASE}/api/v1/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  return res.json();
}

export async function getDataset(id: string) {
  const res = await fetch(`${API_BASE}/api/v1/dataset/${id}`);
  return res.json();
}
```

---

## Responsive Breakpoints

| Breakpoint | Width | Changes |
|---|---|---|
| Mobile | < 640px | Hero 32px, 1-column grid, hamburger nav |
| Tablet | 640-1024px | Hero 56px, 2-column grid |
| Desktop | > 1024px | Full hero, 3-column grid, sidebar filters |

---

## Implementation Steps

1. [ ] Setup React + Vite project in `frontend/`
2. [ ] Configure Tailwind CSS with design tokens
3. [ ] Create layout components (Header, Footer, Container)
4. [ ] Build SearchBar component
5. [ ] Build DatasetCard component
6. [ ] Build SearchResults page
7. [ ] Build DatasetDetail page
8. [ ] Build ScoreBreakdown visualization
9. [ ] Build Comparison page
10. [ ] Add React Query for API calls
11. [ ] Add loading states & error handling
12. [ ] Add responsive design
13. [ ] Test all pages

## Acceptance Criteria

- [ ] Home page loads with search bar
- [ ] Search triggers backend API call
- [ ] Results display as cards with scores
- [ ] Clicking dataset shows detail page
- [ ] Score breakdown shows all 5 components
- [ ] Responsive on mobile, tablet, desktop
- [ ] Design matches design.md tokens
- [ ] Loading states work
- [ ] Error states work
