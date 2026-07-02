# Plan 11: FRED + NOAA + OpenAQ APIs
**DataScout — CROO Agent Hackathon**

---

## Overview

Adapter untuk 3 sumber data spesifik: FRED (Federal Reserve — data ekonomi/finansial AS), NOAA (data iklim/cuaca global), dan OpenAQ (data kualitas udara global).

**Dependensi:** plan_4 (Core Data Models)

---

## 1. FRED API (Federal Reserve Economic Data)

```
Base URL: https://api.stlouisfed.org/fred/
Auth: API Key (free from fred.stlouisfed.org)

Search: /series/search?search_text=<query>&api_key=<key>&file_type=json
Series: /series?series_id=<id>&api_key=<key>&file_type=json
Categories: /category/series?category_id=<id>&api_key=<key>&file_type=json
```

### Implementation

```python
class FREDAdapter(BaseSearchAdapter):
    BASE_URL = "https://api.stlouisfed.org/fred"
    SOURCE_NAME = "fred"
    
    def __init__(self):
        self.api_key = settings.fred_api_key
    
    async def search(self, parsed_query, limit=20):
        params = {
            "search_text": " ".join(parsed_query.keywords[:3]),
            "api_key": self.api_key,
            "file_type": "json",
            "limit": limit,
            "sort_by": "search_rank",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/series/search", params=params)
            resp.raise_for_status()
            data = resp.json()
        
        series = data.get("seriess", [])
        return [self._parse_series(s) for s in series]
    
    def _parse_series(self, s: dict) -> DatasetResult:
        return DatasetResult(
            id=f"fred-{s['id']}",
            title=s.get("title", ""),
            description=s.get("notes", ""),
            source=self.SOURCE_NAME,
            source_url=f"https://fred.stlouisfed.org/series/{s['id']}",
            download_url=f"https://fred.stlouisfed.org/data/{s['id']}.txt",
            last_updated=s.get("last_updated"),
            tags=[s.get("frequency", ""), s.get("units", "")],
            domain="finance",
            region="US",
        )
```

---

## 2. NOAA Climate Data API

```
Base URL: https://www.ncdc.noaa.gov/cdo-web/api/v2/
Auth: API Key (free from ncdc.noaa.gov)

Datasets: /datasets?datasetId=<id>&limit=<n>
Stations: /stations?datasetId=<id>&limit=<n>
Data: /data?datasetId=<id>&startDate=<date>&endDate=<date>
```

### Implementation

```python
class NOAAAdapter(BaseSearchAdapter):
    BASE_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
    SOURCE_NAME = "noaa"
    
    def __init__(self):
        self.api_key = settings.noaa_api_key
        self.headers = {"token": self.api_key}
    
    async def search(self, parsed_query, limit=20):
        # Search datasets first
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/datasets",
                params={"limit": limit},
                headers=self.headers
            )
            resp.raise_for_status()
            data = resp.json()
        
        datasets = data.get("results", [])
        return [self._parse_dataset(d) for d in datasets]
```

---

## 3. OpenAQ API (Air Quality)

```
Base URL: https://api.openaq.org/v2/
Auth: None (public)

Locations: /locations?city=<city>&limit=<n>
Measurements: /measurements?location_id=<id>
Countries: /countries?limit=<n>
```

### Implementation

```python
class OpenAQAdapter(BaseSearchAdapter):
    BASE_URL = "https://api.openaq.org/v2"
    SOURCE_NAME = "openaq"
    
    async def search(self, parsed_query, limit=20):
        params = {
            "limit": limit,
            "order_by": "lastUpdated",
            "sort": "desc",
        }
        # Filter by country if specified
        if parsed_query.region:
            params["country"] = parsed_query.region
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/locations", params=params)
            resp.raise_for_status()
            data = resp.json()
        
        locations = data.get("results", [])
        return [self._parse_location(l) for l in locations]
```

---

## Implementation Steps

1. [ ] Create `src/adapters/fred.py`
2. [ ] Create `src/adapters/noaa.py`
3. [ ] Create `src/adapters/openaq.py`
4. [ ] Handle API key configuration
5. [ ] Test all three adapters
6. [ ] Write unit tests

## Acceptance Criteria

- [ ] FRED adapter works with API key
- [ ] NOAA adapter works with API key
- [ ] OpenAQ works without API key
- [ ] Graceful fallback if API keys missing
