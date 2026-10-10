"""Fetch public RSS/Atom feeds and turn their entries into plain items."""

import datetime as dt
import html
import re
import ssl
import tomllib
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

import certifi
import feedparser

ROOT = Path(__file__).resolve().parent.parent
# Some sites refuse requests without a browser-style agent; the project name stays visible.
USER_AGENT = "Mozilla/5.0 (compatible; llm-risk-radar/1.0; weekly news digest)"


@dataclass
class Item:
    title: str
    link: str
    source: str
    published: str       # ISO date, e.g. 2026-10-09
    summary: str = ""    # used for sorting only, never shown
    ai_only: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def load_feeds(path: Path = ROOT / "config" / "feeds.toml") -> list[dict]:
    return tomllib.loads(path.read_text(encoding="utf-8"))["feed"]


def fetch(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()


def clean(text: str) -> str:
    """Feed summaries are HTML; keep the words only."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse(raw: bytes, source: str, ai_only: bool = False, today: dt.date | None = None) -> list[Item]:
    today = today or dt.date.today()
    items = []
    for e in feedparser.parse(raw).entries:
        stamp = e.get("published_parsed") or e.get("updated_parsed")
        published = dt.date(*stamp[:3]) if stamp else today
        title, link = clean(e.get("title", "")), (e.get("link") or "").strip()
        if title and link.startswith("http") and published <= today:
            items.append(Item(title, link, source, published.isoformat(),
                              clean(e.get("summary", ""))[:1500], ai_only))
    return items


def collect(feeds: list[dict], today: dt.date | None = None) -> tuple[list[Item], list[str]]:
    """Read every feed. A feed that fails is reported, not fatal."""
    items, problems = [], []
    for f in feeds:
        try:
            items += parse(fetch(f["url"]), f["name"], f.get("ai_only", False), today)
        except Exception as e:
            problems.append(f"{f['name']}: {e}")
    return items, problems
