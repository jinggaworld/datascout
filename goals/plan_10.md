# Plan 10: World Bank + Eurostat + WHO APIs
**DataScout — CROO Agent Hackathon**

---

## Overview

Adapter untuk 3 sumber data internasional: World Bank (ekonomi/pembangunan global), Eurostat (statistik Uni Eropa), dan WHO (data kesehatan global). Semua gratis, tanpa API key.

**Dependensi:** plan_4 (Core Data Models)

---

## 1. World Bank Open Data API

```
Base URL: https://api.worldbank.org/v2/
Search: /indicator?format=json&per_page=20&source=<n>&q=<query>
Indicators: /indicator/<code>?format=json
Countries: /country?format=json
```

### Implementation

```python
class WorldBankAdapter(BaseSearchAdapter):
    BASE_URL = "https://api.worldbank.org/v2"
    SOURCE_NAME = "worldbank"
    
    async def search(self, parsed_query, limit=20):
        params = {
            "format": "json",
            "per_page": limit,
            "q": " ".join(parsed_query.keywords[:2]),
            "source": "2",  # World Development Indicators
        }
        # Filter by region if specified
        if parsed_query.region:
            country_map = {"ID": "IDN", "US": "USA", "EU": "EUU"}
            country = country_map.get(parsed_query.region, parsed_query.region)
            params["country"] = country
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/indicator", params=params)
            resp.raise_for_status()
            data = resp.json()
        
        # World Bank returns array: [metadata, data]
        indicators = data[1] if len(data) > 1 else []
        return [self._parse_indicator(i) for i in indicators]
```

---

## 2. Eurostat API

```
Base URL: https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/
Search: /data/<dataset>?format=JSON&lang=en
Bulk: /bulk/<dataset>
Catalog: /dataflow/ESTAT?format=JSON
```

### Implementation

```python
class EurostatAdapter(BaseSearchAdapter):
    BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0"
    SOURCE_NAME = "eurostat"
    
    async def search(self, parsed_query, limit=20):
        # Eurostat uses dataset codes, search catalog first
        catalog_url = f"{self.BASE_URL}/dataflow/ESTAT"
        async with httpx.AsyncClient() as client:
            resp = await client.get(catalog_url, params={"format": "JSON"})
            resp.raise_for_status()
            dataflows = resp.json()
        
        # Filter by keyword match in dataset titles
        keywords = [k.lower() for k in parsed_query.keywords]
        matched = []
        for df in dataflows.get("dataflows", []):
            title = df.get("Name", {}).get("en", "").lower()
            if any(k in title for k in keywords):
                matched.append(df)
        
        return [self._parse_dataflow(m) for m in matched[:limit]]
```

---

## 3. WHO GHO OData API

```
Base URL: https://ghoapi.azureedge.net/api/
Indicators: /Indicator?$filter=contains(IndicatorName,'<query>')
Data: /<indicator_code>?$filter=SpatialDim eq 'COUNTRY'
```

### Implementation

```python
class WHOAdapter(BaseSearchAdapter):
    BASE_URL = "https://ghoapi.azureedge.net/api"
    SOURCE_NAME = "who"
    
    async def search(self, parsed_query, limit=20):
        search_term = parsed_query.keywords[0] if parsed_query.keywords else parsed_query.topic
        url = f"{self.BASE_URL}/Indicator"
        params = {
            "$filter": f"contains(IndicatorName,'{search_term}')",
            "$top": limit,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        
        indicators = data.get("value", [])
        return [self._parse_indicator(i) for i in indicators]
```

---

## Implementation Steps

1. [ ] Create `src/adapters/worldbank.py`
2. [ ] Create `src/adapters/eurostat.py`
3. [ ] Create `src/adapters/who.py`
4. [ ] Handle each API's unique response structure
5. [ ] Map World Bank regions to DataScout region codes
6. [ ] Test all three adapters
7. [ ] Write unit tests

## Acceptance Criteria

- [ ] All 3 adapters return DatasetResult lists
- [ ] World Bank filters by country correctly
- [ ] Eurostat catalog search works
- [ ] WHO indicator search works
- [ ] No API keys required for any
