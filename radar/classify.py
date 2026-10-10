"""Decide which items are about AI, and which OWASP LLM Top 10 risk each one belongs to.

The rules are plain keyword lists in config/owasp.toml - no AI model involved, so
every decision can be explained and tested.
"""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .feeds import ROOT, Item

OTHER = "OTHER"


@dataclass
class Category:
    id: str
    title: str
    plain: str
    keywords: list[str]


@dataclass
class Rules:
    categories: list[Category]
    ai_terms: list[str]


def load_rules(path: Path = ROOT / "config" / "owasp.toml") -> Rules:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return Rules([Category(**c) for c in data["category"]], data["filter"]["ai_terms"])


def has_term(term: str, text: str) -> bool:
    """Whole words only: "ai" must not match "email", "rag" must not match "storage"."""
    return re.search(rf"(?<![a-z0-9äöüß]){re.escape(term)}(?![a-z0-9äöüß])", text) is not None


def is_about_ai(item: Item, rules: Rules) -> bool:
    text = f"{item.title} {item.summary}".lower()
    return item.ai_only or any(has_term(t, text) for t in rules.ai_terms)


def classify(item: Item, rules: Rules) -> tuple[str, list[str]]:
    """Return (category id or OTHER, matched keywords). Title hits and phrases count double."""
    title, body = item.title.lower(), item.summary.lower()
    best, best_score, best_hits = OTHER, 0, []
    for cat in rules.categories:
        score, hits = 0, []
        for kw in cat.keywords:
            weight = 2 if (" " in kw or "-" in kw) else 1
            if has_term(kw, title):
                score += 2 * weight
                hits.append(kw)
            elif has_term(kw, body):
                score += weight
                hits.append(kw)
        if score > best_score:  # ties keep the earlier category
            best, best_score, best_hits = cat.id, score, hits
    return best, best_hits
