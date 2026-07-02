import pytest
from src.models.query import (
    IntentType,
    LicenseFilter,
    ParsedQuery,
    TimeRange,
)
from src.groq.parser import QueryParser


class TestParsedQueryModels:
    """Test Pydantic models for query parsing."""

    def test_parsed_query_minimal(self):
        q = ParsedQuery(topic="housing prices", domain="finance")
        assert q.topic == "housing prices"
        assert q.domain == "finance"
        assert q.intent == IntentType.SEARCH
        assert q.license == LicenseFilter.ANY
        assert q.keywords == []
        assert q.region is None
        assert q.time_range is None

    def test_parsed_query_full(self):
        q = ParsedQuery(
            topic="e-commerce fraud",
            keywords=["fraud", "transaction", "ecommerce"],
            region="ID",
            time_range=TimeRange(start=2019, end=2024),
            min_rows=50000,
            format=["csv", "parquet"],
            license=LicenseFilter.COMMERCIAL_OK,
            domain="finance",
            intent=IntentType.SEARCH,
        )
        assert q.region == "ID"
        assert q.time_range.start == 2019
        assert q.time_range.end == 2024
        assert q.min_rows == 50000
        assert len(q.format) == 2
        assert q.license == LicenseFilter.COMMERCIAL_OK

    def test_time_range(self):
        tr = TimeRange(start=2020, end=2025)
        assert tr.start == 2020
        assert tr.end == 2025

    def test_intent_enum(self):
        assert IntentType.SEARCH == "search"
        assert IntentType.VERIFY == "verify"
        assert IntentType.COMPARE == "compare"

    def test_license_enum(self):
        assert LicenseFilter.ANY == "any"
        assert LicenseFilter.COMMERCIAL_OK == "commercial_ok"
        assert LicenseFilter.RESEARCH_ONLY == "research_only"

    def test_parsed_query_serialization(self):
        q = ParsedQuery(topic="test", domain="other")
        d = q.model_dump()
        assert "topic" in d
        assert "domain" in d
        assert "intent" in d

        # Round-trip
        q2 = ParsedQuery.model_validate(d)
        assert q2.topic == q.topic


class TestQueryParserStructured:
    """Test QueryParser structured input routing (no Groq API needed)."""

    def test_parse_structured_input(self):
        parser = QueryParser.__new__(QueryParser)  # Skip __init__ to avoid Groq client
        result = parser._parse_structured({
            "topic": "housing price",
            "region": "ID",
            "min_rows": 10000,
            "license": "commercial_ok",
            "domain": "finance",
        })
        assert result.topic == "housing price"
        assert result.region == "ID"
        assert result.min_rows == 10000
        assert result.license == LicenseFilter.COMMERCIAL_OK
        assert result.domain == "finance"
        assert result.intent == IntentType.SEARCH

    def test_parse_url_input(self):
        parser = QueryParser.__new__(QueryParser)
        result = parser._parse_url("https://huggingface.co/datasets/some-dataset")
        assert result.topic == "verification"
        assert result.intent == IntentType.VERIFY
        assert result.verify_url == "https://huggingface.co/datasets/some-dataset"
        assert result.domain == "other"

    def test_parse_structured_with_time_range(self):
        parser = QueryParser.__new__(QueryParser)
        result = parser._parse_structured({
            "topic": "climate data",
            "time_range": {"start": 2018, "end": 2024},
            "domain": "climate",
        })
        assert result.time_range is not None
        assert result.time_range.start == 2018
        assert result.time_range.end == 2024

    def test_parse_structured_defaults(self):
        parser = QueryParser.__new__(QueryParser)
        result = parser._parse_structured({"topic": "test"})
        assert result.keywords == []
        assert result.region is None
        assert result.license == LicenseFilter.ANY
        assert result.domain == "other"
        assert result.intent == IntentType.SEARCH


class TestQueryParserRouting:
    """Test input routing logic."""

    @pytest.mark.asyncio
    async def test_route_to_structured(self):
        parser = QueryParser.__new__(QueryParser)
        result = await parser.parse({"topic": "test", "domain": "finance"})
        assert result.topic == "test"
        assert result.domain == "finance"

    @pytest.mark.asyncio
    async def test_route_to_url(self):
        parser = QueryParser.__new__(QueryParser)
        result = await parser.parse({"url": "https://example.com/dataset"})
        assert result.intent == IntentType.VERIFY

    @pytest.mark.asyncio
    async def test_invalid_input(self):
        parser = QueryParser.__new__(QueryParser)
        with pytest.raises(ValueError, match="Invalid input"):
            await parser.parse({"random": "data"})


class TestYearRangeExtraction:
    """Test year range extraction from text."""

    def test_extract_year_range(self):
        parser = QueryParser.__new__(QueryParser)

        tr = parser._extract_year_range("data dari 2019-2024")
        assert tr is not None
        assert tr.start == 2019
        assert tr.end == 2024

    def test_extract_last_n_years(self):
        parser = QueryParser.__new__(QueryParser)
        import datetime
        now = datetime.datetime.now().year

        tr = parser._extract_year_range("5 tahun terakhir")
        assert tr is not None
        assert tr.end == now
        assert tr.start == now - 5

    def test_no_year_range(self):
        parser = QueryParser.__new__(QueryParser)
        tr = parser._extract_year_range("dataset cuaca global")
        assert tr is None
