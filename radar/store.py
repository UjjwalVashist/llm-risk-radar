"""Keep what was collected in data/items.json, so the archive survives feeds dropping old entries."""

import datetime as dt
import json
from pathlib import Path

from .feeds import ROOT

DATA = ROOT / "data" / "items.json"
KEEP_DAYS = 180


def load(path: Path | None = None) -> list[dict]:
    path = path or DATA
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def merge(old: list[dict], new: list[dict], today: dt.date) -> list[dict]:
    """Add new items (one per link), drop items older than KEEP_DAYS, newest first."""
    by_link = {i["link"]: i for i in old}
    for i in new:
        by_link.setdefault(i["link"], i)
    cutoff = (today - dt.timedelta(days=KEEP_DAYS)).isoformat()
    kept = [i for i in by_link.values() if i["published"] >= cutoff]
    return sorted(kept, key=lambda i: (i["published"], i["title"]), reverse=True)


def save(items: list[dict], path: Path | None = None) -> None:
    path = path or DATA
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def week_of(date_iso: str) -> str:
    y, w, _ = dt.date.fromisoformat(date_iso).isocalendar()
    return f"{y}-W{w:02d}"
