from __future__ import annotations

import asyncio
import calendar
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping

import feedparser
import httpx

USER_AGENT = "TechForumMonitor/0.1 (+https://example.com)"


def _entry_to_dict(entry: Mapping[str, Any], source: str) -> Dict[str, Any]:
    link = entry.get("link") or entry.get("id") or ""
    uid = entry.get("id") or entry.get("guid") or link or f"{source}:{entry.get('title', '')}"
    summary = entry.get("summary")
    if not summary and entry.get("content"):
        content_list = entry["content"]
        if isinstance(content_list, list) and content_list:
            summary = content_list[0].get("value")

    published_struct = (
        entry.get("published_parsed") or entry.get("updated_parsed") or entry.get("created_parsed")
    )
    if published_struct:
        published_at = datetime.fromtimestamp(
            calendar.timegm(published_struct), tz=timezone.utc
        )
    else:
        published_at = datetime.now(timezone.utc)

    return {
        "title": entry.get("title") or "",
        "link": link,
        "summary": summary,
        "uid": uid,
        "published_at": published_at,
    }


async def _fetch_and_parse(feed_url: str) -> feedparser.FeedParserDict:
    async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": USER_AGENT}) as client:
        response = await client.get(feed_url)
        response.raise_for_status()
        body = response.text
    return await asyncio.to_thread(feedparser.parse, body)


async def _fetch_generic_feed(feed_url: str, source: str) -> List[Dict[str, Any]]:
    parsed = await _fetch_and_parse(feed_url)
    entries = parsed.entries if hasattr(parsed, "entries") else []
    return [_entry_to_dict(entry, source) for entry in entries]


async def fetch_v2ex_feed(feed_url: str) -> List[Dict[str, Any]]:
    return await _fetch_generic_feed(feed_url, "v2ex")


async def fetch_nodeseek_feed(feed_url: str) -> List[Dict[str, Any]]:
    return await _fetch_generic_feed(feed_url, "nodeseek")


async def fetch_linux_do_feed(feed_url: str) -> List[Dict[str, Any]]:
    return await _fetch_generic_feed(feed_url, "linux.do")


async def fetch_feed(source: str, feed_url: str) -> List[Dict[str, Any]]:
    fetchers = {
        "v2ex": fetch_v2ex_feed,
        "nodeseek": fetch_nodeseek_feed,
        "linux.do": fetch_linux_do_feed,
    }
    try:
        fetcher = fetchers[source.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported source: {source}") from exc
    return await fetcher(feed_url)


def match_keywords(text: str | None, keywords: List[str]) -> bool:
    if not keywords:
        return True
    if not text:
        return False
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)

