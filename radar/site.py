"""Build the static website in docs/ from the stored items."""

import datetime as dt
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

from .classify import OTHER, Rules
from .feeds import ROOT
from .onepager import PAGES as ONEPAGERS
from .store import week_of

DOCS = ROOT / "docs"
OTHER_TITLE = "Other AI security news"
OTHER_PLAIN = "About AI and security, but not clearly one of the ten OWASP risks."

CSS = """
:root { color-scheme: light dark; --bg:#fcfcfb; --fg:#0b0b0b; --muted:#52514e; --line:#e2e0da; --card:#f3f2ee; --accent:#2a78d6; --bar:#86b6ef; }
@media (prefers-color-scheme: dark) { :root { --bg:#1a1a19; --fg:#fff; --muted:#c3c2b7; --line:#33332f; --card:#232321; --accent:#6da7ec; --bar:#256abf; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif; }
main { max-width:860px; margin:0 auto; padding:32px 16px 64px; }
a { color:var(--accent); }
h1 { font-size:30px; margin:0 0 6px; letter-spacing:-.01em; }
h2 { font-size:20px; margin:40px 0 10px; }
h3 { font-size:16px; margin:26px 0 2px; }
.muted { color:var(--muted); } .small { font-size:14px; }
nav { display:flex; gap:16px; flex-wrap:wrap; margin:14px 0 26px; font-size:15px; }
.tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:18px 0; }
.tile { background:var(--card); border-radius:10px; padding:14px 16px; }
.tile b { display:block; font-size:28px; line-height:1.15; }
.bars { display:grid; grid-template-columns:minmax(120px,max-content) 1fr max-content; gap:6px 10px; align-items:center; font-size:14px; margin:12px 0; }
.bar { height:14px; border-radius:0 4px 4px 0; background:var(--bar); min-width:2px; }
ul.items { list-style:none; padding:0; margin:8px 0 0; }
ul.items li { padding:9px 0; border-bottom:1px solid var(--line); }
ul.items .meta { color:var(--muted); font-size:13px; }
.plain { color:var(--muted); font-size:14px; margin:0 0 4px; }
table { border-collapse:collapse; width:100%; font-size:14px; }
th, td { text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); }
td.n { text-align:right; font-variant-numeric:tabular-nums; }
footer { margin-top:48px; padding-top:16px; border-top:1px solid var(--line); color:var(--muted); font-size:13px; }
"""


def page(title: str, body: str, depth: int = 0) -> str:
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title><link rel="stylesheet" href="{up}style.css"></head><body><main>
<nav><a href="{up}index.html"><b>LLM Risk Radar</b></a><a href="{up}archive.html">All weeks</a>
<a href="{up}risks.html">The ten risks</a><a href="{up}safe-ai-en.html">Using AI safely</a><a href="{up}safe-ai-de.html">KI sicher nutzen</a></nav>
{body}
<footer>Headlines link to their original publishers. Sorting is done by keyword rules, not by an AI model, so some
items land in the wrong group. Risk categories: <a href="https://genai.owasp.org/llm-top-10/">OWASP Top 10 for LLM Applications (2025)</a>.</footer>
</main></body></html>"""


def week_label(week: str) -> str:
    year, num = week.split("-W")
    monday = dt.date.fromisocalendar(int(year), int(num), 1)
    return f"Week {int(num)}, {year} ({monday:%d %b} – {monday + dt.timedelta(days=6):%d %b})"


def week_body(week: str, items: list[dict], rules: Rules) -> str:
    counts = Counter(i["category"] for i in items)
    titles = {c.id: (f"{c.id} {c.title}", c.plain) for c in rules.categories}
    titles[OTHER] = (OTHER_TITLE, OTHER_PLAIN)
    order = [c.id for c in rules.categories] + [OTHER]
    top = max(counts.values(), default=1)
    bars = "".join(f'<span>{escape(titles[c][0])}</span><div class="bar" title="{counts[c]} items" '
                   f'style="width:{100 * counts[c] / top:.0f}%"></div><span>{counts[c]}</span>'
                   for c in order if counts[c])
    groups = ""
    for c in order:
        group = [i for i in items if i["category"] == c]
        if not group:
            continue
        rows = "".join(f'<li><a href="{escape(i["link"])}" rel="noopener">{escape(i["title"])}</a>'
                       f'<div class="meta">{escape(i["source"])} · {dt.date.fromisoformat(i["published"]):%d %b %Y}</div></li>'
                       for i in group)
        groups += f'<h3>{escape(titles[c][0])}</h3><p class="plain">{escape(titles[c][1])}</p><ul class="items">{rows}</ul>'
    sources = len({i["source"] for i in items})
    return f"""<div class="tiles"><div class="tile"><b>{len(items)}</b>AI security headlines</div>
<div class="tile"><b>{len(items) - counts[OTHER]}</b>matched to an OWASP risk</div>
<div class="tile"><b>{sources}</b>sources</div></div>
<div class="bars">{bars}</div>{groups}"""


def build(items: list[dict], rules: Rules, today: dt.date, out: Path | None = None) -> list[str]:
    """Write the whole site. Returns the weeks that have a page, newest first."""
    out = out or DOCS
    out.mkdir(exist_ok=True)
    (out / "weeks").mkdir(exist_ok=True)
    (out / "style.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")  # plain static files, no Jekyll build

    by_week = defaultdict(list)
    for i in items:
        by_week[week_of(i["published"])].append(i)
    weeks = sorted(by_week, reverse=True)
    for w in weeks:
        body = f"<h1>{week_label(w)}</h1>" + week_body(w, by_week[w], rules)
        (out / "weeks" / f"{w}.html").write_text(page(f"LLM Risk Radar – {w}", body, depth=1), encoding="utf-8")

    latest = weeks[0] if weeks else None
    intro = ("<h1>LLM Risk Radar</h1><p class=\"muted\">A weekly digest of AI security news from public sources, "
             "sorted by the OWASP Top 10 for LLM Applications. Updated automatically every Monday.</p>")
    if latest:
        trend_weeks = weeks[:8]
        ids = [c.id for c in rules.categories]
        head = "".join(f"<th>{c}</th>" for c in ids)
        rows = "".join(
            f'<tr><td><a href="weeks/{w}.html">{w}</a></td>'
            + "".join(f'<td class="n">{sum(1 for i in by_week[w] if i["category"] == c) or ""}</td>' for c in ids)
            + f'<td class="n">{len(by_week[w])}</td></tr>' for w in trend_weeks)
        index = (intro + f"<h2>{week_label(latest)}</h2>" + week_body(latest, by_week[latest], rules)
                 + f'<h2>Trend</h2><p class="muted small">Headlines per risk and week.</p><div style="overflow-x:auto">'
                 f"<table><thead><tr><th>Week</th>{head}<th>All</th></tr></thead><tbody>{rows}</tbody></table></div>"
                 f'<p class="muted small">Last update: {today:%d %b %Y}.</p>')
    else:
        index = intro + "<p>No items yet.</p>"
    (out / "index.html").write_text(page("LLM Risk Radar", index), encoding="utf-8")

    archive = "<h1>All weeks</h1><ul class=\"items\">" + "".join(
        f'<li><a href="weeks/{w}.html">{week_label(w)}</a><div class="meta">{len(by_week[w])} headlines</div></li>'
        for w in weeks) + "</ul>"
    (out / "archive.html").write_text(page("LLM Risk Radar – all weeks", archive), encoding="utf-8")

    risks = ("<h1>The ten risks</h1><p class=\"muted\">The OWASP Top 10 for LLM Applications (2025) in plain words, "
             "with the keywords this site uses to sort headlines.</p>" + "".join(
                 f"<h3>{c.id} {escape(c.title)}</h3><p>{escape(c.plain)}</p>"
                 f'<p class="muted small">Keywords: {escape(", ".join(c.keywords))}</p>' for c in rules.categories))
    (out / "risks.html").write_text(page("LLM Risk Radar – the ten risks", risks), encoding="utf-8")

    for name, html_text in ONEPAGERS.items():
        (out / name).write_text(html_text, encoding="utf-8")
    return weeks
