#!/usr/bin/env python3
"""Trending personal-finance content scraper.

Pulls the day's top posts from finance-focused communities and writes:

- `scraper/output/trending-YYYY-MM-DD.csv`   — machine-readable
- `scraper/output/trending-YYYY-MM-DD.md`    — human-readable shortlist

Sources:
- Reddit (no auth required, uses public JSON endpoints)
- Hacker News Algolia API (no auth required)
- YouTube Data API v3 (optional — requires YOUTUBE_API_KEY env var)

Usage:
    python scraper/run.py                       # all sources
    python scraper/run.py --limit 10            # top N per source
    python scraper/run.py --skip-youtube        # skip YouTube
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

# Reddit blocks generic UAs. A modern browser UA is required.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

REDDIT_SUBS = [
    "personalfinance",
    "investing",
    "Money",
    "FinancialIndependence",
    "povertyfinance",
    "Frugal",
    "financialplanning",
]

YOUTUBE_QUERIES = [
    "personal finance tips",
    "money saving tips",
    "investing for beginners",
    "side hustle ideas",
    "budgeting tips",
]

HN_FINANCE_KEYWORDS = [
    "money",
    "investing",
    "personal finance",
    "side hustle",
    "savings",
]

GOOGLE_NEWS_QUERIES = [
    "personal finance tips",
    "money saving tips",
    "investing for beginners",
    "side hustle ideas",
    "budgeting tips",
    "retire early FIRE",
    "credit card tips",
    "high yield savings",
]


@dataclass
class TrendingItem:
    source: str
    title: str
    url: str
    score: int
    comments: int
    community: str
    published_utc: str
    hook_idea: str

    @classmethod
    def fields(cls) -> list[str]:
        return list(cls.__dataclass_fields__.keys())


def http_get_json(url: str, *, retries: int = 3, backoff: float = 1.5) -> dict | list | None:
    """Best-effort GET with retries; returns parsed JSON or None on failure."""
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_err = exc
            sleep_for = backoff ** attempt
            time.sleep(sleep_for)
    print(f"  ! GET {url} failed after {retries} retries: {last_err}", file=sys.stderr)
    return None


def hook_from_title(title: str) -> str:
    """Convert a generic post title into a Reel hook idea."""
    title = title.strip()
    if len(title) > 90:
        title = title[:87] + "..."
    lower = title.lower()
    if lower.startswith(("how ", "why ", "what ")):
        return title
    if "$" in title or any(ch.isdigit() for ch in title):
        return f"The truth about: {title}"
    if lower.startswith(("i ", "we ", "my ")):
        return f"What this person learned: {title}"
    return f"Did you know? {title}"


def scrape_reddit(limit: int) -> list[TrendingItem]:
    items: list[TrendingItem] = []
    for sub in REDDIT_SUBS:
        url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit={limit}"
        data = http_get_json(url)
        if not isinstance(data, dict):
            continue
        children = data.get("data", {}).get("children", [])
        for child in children:
            post = child.get("data", {})
            title = post.get("title", "").strip()
            if not title:
                continue
            permalink = post.get("permalink", "")
            score = int(post.get("score", 0) or 0)
            comments = int(post.get("num_comments", 0) or 0)
            created = float(post.get("created_utc", 0) or 0)
            items.append(
                TrendingItem(
                    source="reddit",
                    title=title,
                    url=f"https://www.reddit.com{permalink}",
                    score=score,
                    comments=comments,
                    community=f"r/{sub}",
                    published_utc=dt.datetime.fromtimestamp(created, tz=dt.timezone.utc).isoformat(),
                    hook_idea=hook_from_title(title),
                )
            )
        # be polite
        time.sleep(0.7)
    return items


def scrape_hackernews(limit: int) -> list[TrendingItem]:
    items: list[TrendingItem] = []
    for kw in HN_FINANCE_KEYWORDS:
        params = urlencode(
            {
                "query": kw,
                "tags": "story",
                "numericFilters": f"created_at_i>{int(time.time()) - 86400 * 7}",
                "hitsPerPage": limit,
            }
        )
        url = f"https://hn.algolia.com/api/v1/search?{params}"
        data = http_get_json(url)
        if not isinstance(data, dict):
            continue
        for hit in data.get("hits", []):
            title = (hit.get("title") or "").strip()
            if not title:
                continue
            items.append(
                TrendingItem(
                    source="hackernews",
                    title=title,
                    url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    score=int(hit.get("points", 0) or 0),
                    comments=int(hit.get("num_comments", 0) or 0),
                    community=f"hn:{kw}",
                    published_utc=hit.get("created_at", ""),
                    hook_idea=hook_from_title(title),
                )
            )
        time.sleep(0.4)
    return items


def http_get_text(url: str, *, retries: int = 3, backoff: float = 1.5) -> str | None:
    """Best-effort GET returning the response body as text."""
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
            with urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:
            last_err = exc
            time.sleep(backoff ** attempt)
    print(f"  ! GET {url} failed after {retries} retries: {last_err}", file=sys.stderr)
    return None


def scrape_google_news(limit: int) -> list[TrendingItem]:
    items: list[TrendingItem] = []
    for q in GOOGLE_NEWS_QUERIES:
        params = urlencode({"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})
        url = f"https://news.google.com/rss/search?{params}"
        xml = http_get_text(url)
        if not xml:
            continue
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            continue
        count = 0
        for item in root.iter("item"):
            if count >= limit:
                break
            title_el = item.find("title")
            link_el = item.find("link")
            pub_el = item.find("pubDate")
            source_el = item.find("source")
            title = (title_el.text or "").strip() if title_el is not None else ""
            if not title:
                continue
            # Google News titles are formatted: "Article title - Publisher". Strip publisher.
            clean = re.sub(r"\s*-\s*[^-]+$", "", title)
            community = (source_el.text or "").strip() if source_el is not None else f"news:{q}"
            items.append(
                TrendingItem(
                    source="google_news",
                    title=clean,
                    url=(link_el.text or "").strip() if link_el is not None else "",
                    score=0,  # Google News RSS doesn't expose engagement
                    comments=0,
                    community=community or f"news:{q}",
                    published_utc=(pub_el.text or "").strip() if pub_el is not None else "",
                    hook_idea=hook_from_title(clean),
                )
            )
            count += 1
        time.sleep(0.4)
    return items


def scrape_youtube(limit: int, api_key: str) -> list[TrendingItem]:
    items: list[TrendingItem] = []
    for q in YOUTUBE_QUERIES:
        params = urlencode(
            {
                "part": "snippet",
                "q": q,
                "type": "video",
                "videoDuration": "short",
                "order": "viewCount",
                "publishedAfter": (dt.datetime.utcnow() - dt.timedelta(days=7)).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "maxResults": limit,
                "key": api_key,
            }
        )
        url = f"https://www.googleapis.com/youtube/v3/search?{params}"
        data = http_get_json(url)
        if not isinstance(data, dict):
            continue
        for hit in data.get("items", []):
            snip = hit.get("snippet", {})
            vid = hit.get("id", {}).get("videoId")
            if not vid:
                continue
            title = (snip.get("title") or "").strip()
            items.append(
                TrendingItem(
                    source="youtube",
                    title=title,
                    url=f"https://www.youtube.com/watch?v={vid}",
                    score=0,  # search endpoint doesn't return views; would need /videos call
                    comments=0,
                    community=f"yt:{q}",
                    published_utc=snip.get("publishedAt", ""),
                    hook_idea=hook_from_title(title),
                )
            )
        time.sleep(0.4)
    return items


def dedupe(items: Iterable[TrendingItem]) -> list[TrendingItem]:
    seen: set[str] = set()
    out: list[TrendingItem] = []
    for item in items:
        key = item.title.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def write_csv(items: list[TrendingItem], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=TrendingItem.fields())
        writer.writeheader()
        for item in items:
            writer.writerow(asdict(item))


def write_markdown(items: list[TrendingItem], path: Path) -> None:
    by_source: dict[str, list[TrendingItem]] = {}
    for item in items:
        by_source.setdefault(item.source, []).append(item)

    today = dt.date.today().isoformat()
    lines: list[str] = [
        f"# Trending personal-finance content — {today}",
        "",
        f"Total items: **{len(items)}**",
        "",
        "Use the **Hook idea** column as a starting point for today's Reel script.",
        "Paste it into `docs/prompts.md` → Reel script prompt.",
        "",
    ]

    for source in sorted(by_source.keys()):
        bucket = by_source[source]
        bucket.sort(key=lambda x: x.score, reverse=True)
        top = bucket[:15]
        lines.append(f"## {source.title()} — top {len(top)}")
        lines.append("")
        lines.append("| Score | Community | Title | Hook idea | Link |")
        lines.append("|------:|-----------|-------|-----------|------|")
        for it in top:
            safe_title = it.title.replace("|", "\\|")
            safe_hook = it.hook_idea.replace("|", "\\|")
            lines.append(
                f"| {it.score} | {it.community} | {safe_title[:80]} | {safe_hook[:80]} | [open]({it.url}) |"
            )
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10, help="top N items per source")
    parser.add_argument("--skip-reddit", action="store_true")
    parser.add_argument("--skip-hn", action="store_true")
    parser.add_argument("--skip-google-news", action="store_true")
    parser.add_argument("--skip-youtube", action="store_true")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="output directory (default: scraper/output/)",
    )
    args = parser.parse_args()

    today = dt.date.today().isoformat()
    print(f"Scraping trending personal-finance content for {today}...\n")

    all_items: list[TrendingItem] = []

    if not args.skip_google_news:
        print("[google_news] pulling finance news from Google News RSS...")
        gn_items = scrape_google_news(args.limit)
        print(f"  -> {len(gn_items)} items")
        all_items.extend(gn_items)

    if not args.skip_reddit:
        print("[reddit] pulling top posts from finance subs (may be blocked from some IPs)...")
        reddit_items = scrape_reddit(args.limit)
        print(f"  -> {len(reddit_items)} items")
        all_items.extend(reddit_items)

    if not args.skip_hn:
        print("[hackernews] searching finance keywords...")
        hn_items = scrape_hackernews(args.limit)
        print(f"  -> {len(hn_items)} items")
        all_items.extend(hn_items)

    if not args.skip_youtube:
        yt_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
        if not yt_key:
            print("[youtube] skipped: set YOUTUBE_API_KEY env var to enable")
        else:
            print("[youtube] searching trending finance Shorts...")
            yt_items = scrape_youtube(args.limit, yt_key)
            print(f"  -> {len(yt_items)} items")
            all_items.extend(yt_items)

    all_items = dedupe(all_items)
    all_items.sort(key=lambda x: x.score, reverse=True)

    if not all_items:
        print("\nNo items scraped. Check your network connection or try again later.")
        return 1

    csv_path = args.out_dir / f"trending-{today}.csv"
    md_path = args.out_dir / f"trending-{today}.md"

    write_csv(all_items, csv_path)
    write_markdown(all_items, md_path)

    print(f"\nWrote {len(all_items)} items:")
    print(f"  - {csv_path}")
    print(f"  - {md_path}")
    print("\nTop 5 across all sources:")
    for it in all_items[:5]:
        print(f"  [{it.score:>5}] ({it.community}) {it.title[:80]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
