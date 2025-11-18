"""Enhanced fetchers tests including error handling."""
from __future__ import annotations

import time
from types import SimpleNamespace

import httpx
import pytest

from app import fetchers


@pytest.mark.asyncio
async def test_fetch_feed_with_all_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that all supported sources can be fetched."""
    sample_entry = {
        "title": "Test Post",
        "link": "https://example.com/post",
        "summary": "Test content",
        "id": "test-guid",
        "published_parsed": time.gmtime(0),
    }

    async def fake_fetch_and_parse(url: str):
        return SimpleNamespace(entries=[sample_entry])

    monkeypatch.setattr(fetchers, "_fetch_and_parse", fake_fetch_and_parse)

    # Test v2ex
    results = await fetchers.fetch_v2ex_feed("https://v2ex.com/rss")
    assert len(results) == 1
    assert results[0]["title"] == "Test Post"

    # Test nodeseek
    results = await fetchers.fetch_nodeseek_feed("https://nodeseek.com/rss")
    assert len(results) == 1
    assert results[0]["title"] == "Test Post"

    # Test linux.do
    results = await fetchers.fetch_linux_do_feed("https://linux.do/rss")
    assert len(results) == 1
    assert results[0]["title"] == "Test Post"


@pytest.mark.asyncio
async def test_fetch_feed_factory_function(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the fetch_feed factory function with different sources."""
    sample_entry = {
        "title": "Factory Test",
        "link": "https://example.com/post",
        "summary": "Content",
        "id": "factory-guid",
        "published_parsed": time.gmtime(0),
    }

    async def fake_fetch_and_parse(url: str):
        return SimpleNamespace(entries=[sample_entry])

    monkeypatch.setattr(fetchers, "_fetch_and_parse", fake_fetch_and_parse)

    # Test all sources via factory
    for source in ["v2ex", "nodeseek", "linux.do"]:
        results = await fetchers.fetch_feed(source, f"https://{source}.com/rss")
        assert len(results) == 1
        assert results[0]["title"] == "Factory Test"


@pytest.mark.asyncio
async def test_fetch_feed_with_missing_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of entries with missing fields."""
    # Entry with minimal fields
    minimal_entry = {
        "title": "Minimal Post",
        # No link, id, summary, or published_parsed
    }

    async def fake_fetch_and_parse(url: str):
        return SimpleNamespace(entries=[minimal_entry])

    monkeypatch.setattr(fetchers, "_fetch_and_parse", fake_fetch_and_parse)

    results = await fetchers.fetch_v2ex_feed("https://example.com/rss")
    assert len(results) == 1
    assert results[0]["title"] == "Minimal Post"
    assert results[0]["link"] == ""
    assert results[0]["summary"] is None
    # UID should be generated from source and title
    assert "v2ex" in results[0]["uid"]
    # published_at should default to current time
    assert results[0]["published_at"] is not None


@pytest.mark.asyncio
async def test_fetch_feed_with_content_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of entries with content field instead of summary."""
    entry_with_content = {
        "title": "Content Field Post",
        "link": "https://example.com/post",
        "content": [{"value": "Content from content field"}],
        "id": "content-guid",
        "published_parsed": time.gmtime(0),
    }

    async def fake_fetch_and_parse(url: str):
        return SimpleNamespace(entries=[entry_with_content])

    monkeypatch.setattr(fetchers, "_fetch_and_parse", fake_fetch_and_parse)

    results = await fetchers.fetch_v2ex_feed("https://example.com/rss")
    assert len(results) == 1
    assert results[0]["summary"] == "Content from content field"


@pytest.mark.asyncio
async def test_fetch_feed_with_alternative_date_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test handling of entries with alternative date fields."""
    # Entry with updated_parsed instead of published_parsed
    entry_updated = {
        "title": "Updated Post",
        "link": "https://example.com/post",
        "id": "updated-guid",
        "updated_parsed": time.gmtime(1000000),
    }

    async def fake_fetch_and_parse(url: str):
        return SimpleNamespace(entries=[entry_updated])

    monkeypatch.setattr(fetchers, "_fetch_and_parse", fake_fetch_and_parse)

    results = await fetchers.fetch_v2ex_feed("https://example.com/rss")
    assert len(results) == 1
    assert results[0]["published_at"] is not None


@pytest.mark.asyncio
async def test_fetch_feed_with_empty_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of feed with no entries."""

    async def fake_fetch_and_parse(url: str):
        return SimpleNamespace(entries=[])

    monkeypatch.setattr(fetchers, "_fetch_and_parse", fake_fetch_and_parse)

    results = await fetchers.fetch_v2ex_feed("https://example.com/rss")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_fetch_feed_with_multiple_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of feed with multiple entries."""
    entries = [
        {
            "title": f"Post {i}",
            "link": f"https://example.com/post{i}",
            "id": f"guid-{i}",
            "published_parsed": time.gmtime(i * 1000),
        }
        for i in range(10)
    ]

    async def fake_fetch_and_parse(url: str):
        return SimpleNamespace(entries=entries)

    monkeypatch.setattr(fetchers, "_fetch_and_parse", fake_fetch_and_parse)

    results = await fetchers.fetch_v2ex_feed("https://example.com/rss")
    assert len(results) == 10
    for i, result in enumerate(results):
        assert result["title"] == f"Post {i}"
        assert result["uid"] == f"guid-{i}"


def test_match_keywords_edge_cases() -> None:
    """Test keyword matching with various edge cases."""
    # Test with special characters
    assert fetchers.match_keywords("C++ programming", ["c++"]) is True

    # Test with numbers
    assert fetchers.match_keywords("Python 3.11 release", ["3.11"]) is True

    # Test with partial word match
    assert fetchers.match_keywords("FastAPI framework", ["fast"]) is True

    # Test multiple keywords with OR logic
    assert fetchers.match_keywords("Django tutorial", ["django", "flask"]) is True
    assert fetchers.match_keywords("Flask tutorial", ["django", "flask"]) is True

    # Test case sensitivity
    assert fetchers.match_keywords("UPPERCASE TEXT", ["uppercase"]) is True
    assert fetchers.match_keywords("lowercase text", ["LOWERCASE"]) is True

    # Test with whitespace
    assert fetchers.match_keywords("  Python  ", ["python"]) is True

    # Test with only whitespace
    assert fetchers.match_keywords("   ", ["python"]) is False


@pytest.mark.asyncio
async def test_fetch_feed_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of network errors during fetch."""

    async def fake_fetch_and_parse_error(url: str):
        raise httpx.HTTPError("Network error")

    monkeypatch.setattr(fetchers, "_fetch_and_parse", fake_fetch_and_parse_error)

    with pytest.raises(httpx.HTTPError):
        await fetchers.fetch_v2ex_feed("https://example.com/rss")


@pytest.mark.asyncio
async def test_fetch_feed_case_insensitive_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that source matching is case insensitive."""
    from app.fetchers import fetch_feed

    async def fake_v2ex_feed(url: str):
        return []

    async def fake_nodeseek_feed(url: str):
        return []

    async def fake_linux_do_feed(url: str):
        return []

    monkeypatch.setattr(fetchers, "fetch_v2ex_feed", fake_v2ex_feed)
    monkeypatch.setattr(fetchers, "fetch_nodeseek_feed", fake_nodeseek_feed)
    monkeypatch.setattr(fetchers, "fetch_linux_do_feed", fake_linux_do_feed)

    # These should not raise errors
    result = await fetch_feed("V2EX", "https://example.com/rss")
    assert result == []

    result = await fetch_feed("NodeSeek", "https://example.com/rss")
    assert result == []

    result = await fetch_feed("LINUX.DO", "https://example.com/rss")
    assert result == []


def test_match_keywords_with_unicode() -> None:
    """Test keyword matching with unicode characters."""
    # Test Chinese characters
    assert fetchers.match_keywords("Python 编程教程", ["python"]) is True
    assert fetchers.match_keywords("编程语言 Python", ["python"]) is True

    # Test with emoji
    assert fetchers.match_keywords("🐍 Python programming", ["python"]) is True
