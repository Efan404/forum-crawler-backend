from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from app import fetchers


@pytest.mark.asyncio
async def test_fetcher_normalizes_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    sample_entry = {
        "title": "Sample Post",
        "link": "https://example.com/post",
        "summary": "Interesting content",
        "id": "guid-123",
        "published_parsed": time.gmtime(0),
    }

    async def fake_fetch_and_parse(url: str):
        return SimpleNamespace(entries=[sample_entry])

    monkeypatch.setattr(fetchers, "_fetch_and_parse", fake_fetch_and_parse)

    results = await fetchers.fetch_v2ex_feed("https://example.com/rss")
    assert len(results) == 1
    entry = results[0]
    assert entry["uid"] == "guid-123"
    assert entry["link"] == "https://example.com/post"
    assert entry["published_at"].isoformat().startswith("1970-01-01T00:00:00")


def test_match_keywords_behavior() -> None:
    assert fetchers.match_keywords("Python FastAPI release", ["fastapi"])
    assert fetchers.match_keywords("All topics welcome", []) is True
    assert fetchers.match_keywords(None, ["python"]) is False
    assert fetchers.match_keywords("Rust updates", ["python"]) is False


@pytest.mark.asyncio
async def test_fetch_feed_unsupported_source() -> None:
    with pytest.raises(ValueError):
        await fetchers.fetch_feed("unknown", "https://example.com/rss")

