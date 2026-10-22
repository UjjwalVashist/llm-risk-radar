"""Build the static website in docs/ from the stored items."""

import datetime as dt
import hashlib
import math
import re
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
RADAR_WEEKS = 4   # rings on the radar, this week in the centre
TREND_WEEKS = 12  # columns in the heat grid
ARIA_CURRENT, CUR, OTHER_ROW = ' aria-current="page"', ' class="cur"', ' class="other"'

FONTS = ("https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800"
         "&family=IBM+Plex+Mono:wght@400;500&display=swap")

CSS = """
/* Layout: a masthead like a weekly advisory, the radar as the hero, then a risk-by-week heat grid and the headlines. */
:root {
  color-scheme: light;
  --bg:#f1f3f6; --surface:#ffffff; --ink:#0f1b2d; --muted:#556175; --line:#d6dce5;
  --scope:#1d4e89; --signal:#c8641a; --signal-soft:#fbe9d9;
  --display:"Archivo","Helvetica Neue",Arial,sans-serif; --body:"Archivo",-apple-system,"Segoe UI",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  color-scheme: dark; --bg:#0b1320; --surface:#111c2e; --ink:#e7ecf3; --muted:#97a3b6; --line:#24324a;
  --scope:#7fb0ec; --signal:#f29a4a; --signal-soft:#3a2716; } }
:root[data-theme="dark"] {
  color-scheme: dark; --bg:#0b1320; --surface:#111c2e; --ink:#e7ecf3; --muted:#97a3b6; --line:#24324a;
  --scope:#7fb0ec; --signal:#f29a4a; --signal-soft:#3a2716; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.55 var(--body); font-stretch:100%; }
a { color:var(--scope); text-underline-offset:3px; }
a:focus-visible { outline:2px solid var(--signal); outline-offset:2px; border-radius:2px; }
.wrap { max-width:1080px; margin:0 auto; padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); }
.mono { font-family:var(--mono); }
.muted { color:var(--muted); } .small { font-size:14px; }

/* masthead */
.mast { border-bottom:1px solid var(--line); background:var(--surface); }
.mast .wrap { display:flex; flex-wrap:wrap; align-items:baseline; justify-content:space-between; gap:8px 24px; padding-block:18px 0; }
.brand { font-family:var(--display); font-stretch:125%; font-weight:800; font-size:22px; letter-spacing:.02em; text-transform:uppercase; color:var(--ink); text-decoration:none; }
.brand span { color:var(--signal); }
.issue { font-family:var(--mono); font-size:13px; color:var(--muted); }
nav { flex-basis:100%; display:flex; gap:4px 22px; flex-wrap:wrap; font-size:14px; }
nav a { color:var(--muted); text-decoration:none; padding:10px 0 12px; border-bottom:2px solid transparent; }
nav a:hover { color:var(--ink); }
nav a[aria-current] { color:var(--ink); border-bottom-color:var(--signal); font-weight:600; }

main { padding-block:36px 64px; }
h1, h2 { font-family:var(--display); text-wrap:balance; margin:0; }
h1 { font-stretch:112%; font-weight:750; font-size:clamp(28px, 4.2vw, 42px); line-height:1.08; letter-spacing:-.01em; }
h2 { font-stretch:118%; font-weight:700; font-size:15px; text-transform:uppercase; letter-spacing:.08em; }
.eyebrow { font-family:var(--mono); font-size:12px; letter-spacing:.1em; text-transform:uppercase; color:var(--signal); margin:0 0 10px; }
section { margin-top:56px; }
.sec-head { display:flex; flex-wrap:wrap; align-items:baseline; justify-content:space-between; gap:6px 16px; padding-bottom:10px; border-bottom:2px solid var(--ink); margin-bottom:18px; }

/* hero: radar + brief */
.hero { display:grid; grid-template-columns:minmax(0, 420px) minmax(0, 1fr); gap:24px 48px; align-items:center; margin:0; }
.radar { width:100%; max-width:420px; height:auto; display:block; }
.radar .ring { fill:none; stroke:var(--line); }
.radar .spoke { stroke:var(--line); }
.radar .sector { fill:var(--scope); }
.radar .lbl { font:500 11px var(--mono); fill:var(--muted); }
.radar .lbl.hot { fill:var(--ink); }
.radar .ringlbl { font:10px var(--mono); fill:var(--muted); }
.radar .dot { fill:var(--scope); stroke:var(--surface); stroke-width:1.5; }
.radar .dot.now { fill:var(--signal); }
.radar a:hover .dot, .radar a:focus .dot { stroke:var(--ink); stroke-width:2; }
.radar .sweep { fill:url(#sweep); transform-origin:200px 200px; animation:sweep 9s linear infinite; }
@keyframes sweep { to { transform:rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .radar .sweep { animation:none; } }
.legend { display:flex; flex-wrap:wrap; gap:6px 16px; font:12px var(--mono); color:var(--muted); margin-top:8px; }
.legend i { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; vertical-align:0; background:var(--scope); }
.legend i.now { background:var(--signal); }
.lede { font-size:18px; color:var(--muted); max-width:52ch; margin:14px 0 0; }
.stats { display:flex; flex-wrap:wrap; gap:14px 36px; margin:26px 0 0; padding:0; }
.stats div { display:flex; flex-direction:column; }
.stats dt { order:2; font-size:13px; color:var(--muted); }
.stats dd { order:1; margin:0; font:500 30px/1.1 var(--mono); font-variant-numeric:tabular-nums; }
.cover { margin-top:26px; max-width:460px; }
.cover .track { display:flex; height:8px; background:var(--line); border-radius:4px; overflow:hidden; }
.cover .fill { background:var(--scope); }
.cover p { font-size:13px; color:var(--muted); margin:8px 0 0; }

/* heat grid */
.grid-scroll { overflow-x:auto; }
table.heat { border-collapse:separate; border-spacing:3px; font:13px var(--mono); font-variant-numeric:tabular-nums; min-width:640px; width:100%; }
.heat th { font-weight:500; color:var(--muted); text-align:center; padding:2px 0 6px; }
.heat th.cur { color:var(--signal); }
.heat th[scope=row] { text-align:left; padding:0 12px 0 0; white-space:nowrap; font-family:var(--body); font-size:14px; position:sticky; left:0; background:var(--bg); }
.heat th[scope=row] a { color:var(--ink); text-decoration:none; }
.heat th[scope=row] a:hover { text-decoration:underline; }
.heat th[scope=row] b { font:500 12px var(--mono); color:var(--muted); margin-right:8px; }
.heat td { height:30px; min-width:30px; text-align:center; border-radius:3px; background:color-mix(in srgb, var(--line) 45%, transparent); }
.heat td.v { background:color-mix(in srgb, var(--scope) var(--t), transparent); }
.heat td.v.hi { color:var(--bg); }
.heat td.cur { box-shadow:inset 0 0 0 1.5px var(--signal); }
.heat td.sum { background:none; color:var(--ink); font-weight:500; text-align:right; padding-left:10px; }
.heat tr.other th, .heat tr.other td.sum { color:var(--muted); }

/* headlines */
.groups { display:grid; gap:32px; }
.risk-head { display:grid; grid-template-columns:auto 1fr auto; align-items:baseline; gap:4px 14px; }
.rid { font:500 13px var(--mono); color:var(--signal); background:var(--signal-soft); padding:2px 7px; border-radius:3px; }
.risk-head h3 { font-family:var(--display); font-stretch:110%; font-size:19px; font-weight:700; margin:0; }
.risk-head .n { font:13px var(--mono); color:var(--muted); }
.plain { grid-column:2 / -1; color:var(--muted); font-size:14px; margin:0; max-width:68ch; }
.group.other .rid { color:var(--muted); background:color-mix(in srgb, var(--line) 60%, transparent); }
ol.items { list-style:none; padding:0; margin:12px 0 0; background:var(--surface); border:1px solid var(--line); border-radius:6px; }
ol.items li { padding:14px 18px; border-top:1px solid var(--line); display:grid; gap:6px; }
ol.items li:first-child { border-top:0; }
.hl { font-size:16.5px; font-weight:550; line-height:1.4; color:var(--ink); text-decoration:none; }
.hl:hover { color:var(--scope); text-decoration:underline; }
mark { background:var(--signal-soft); color:inherit; box-shadow:inset 0 -2px 0 var(--signal); padding:0 1px; }
.meta { display:flex; flex-wrap:wrap; align-items:center; gap:4px 14px; font:12.5px var(--mono); color:var(--muted); }
.kw { display:inline-flex; gap:6px; flex-wrap:wrap; }
.kw span { border:1px solid var(--line); border-radius:3px; padding:0 6px; color:var(--ink); }
.kw span::before { content:"\\2316  "; color:var(--signal); }

/* archive and risks */
ul.weeks { list-style:none; padding:0; margin:0; display:grid; gap:2px; }
ul.weeks li { display:grid; grid-template-columns:minmax(0, 1fr) 160px 3ch; gap:16px; align-items:center; padding:10px 0; border-bottom:1px solid var(--line); }
ul.weeks .bar { height:8px; background:var(--scope); border-radius:0 3px 3px 0; min-width:2px; }
ul.weeks .c { font:13px var(--mono); text-align:right; color:var(--muted); }
.risks { display:grid; grid-template-columns:repeat(auto-fill, minmax(300px, 1fr)); gap:16px; }
.risk { background:var(--surface); border:1px solid var(--line); border-radius:6px; padding:18px 20px; display:grid; gap:8px; align-content:start; scroll-margin-top:16px; }
.risk:target { border-color:var(--signal); }
.risk h3 { font-family:var(--display); font-stretch:110%; font-size:18px; margin:0; display:flex; gap:10px; align-items:baseline; }
.risk p { margin:0; }
.risk .kw { font:12px var(--mono); margin-top:4px; }
.risk .kw span::before { content:none; }

footer { border-top:1px solid var(--line); color:var(--muted); font-size:13px; }
footer .wrap { padding-block:20px 32px; max-width:1080px; }
footer p { margin:0; max-width:80ch; }

@media (max-width: 760px) {
  .hero { grid-template-columns:minmax(0, 1fr); }
  .radar { max-width:360px; margin:0 auto; }
  ul.weeks li { grid-template-columns:minmax(0, 1fr) 80px 3ch; }
  table.heat { min-width:0; }
  .heat tr:not(.other) th[scope=row] .t { display:none; }
  .heat td { min-width:24px; font-size:12px; }
}
"""

NAV = [("index.html", "This week"), ("archive.html", "All weeks"), ("risks.html", "The ten risks"),
       ("safe-ai-en.html", "Using AI safely"), ("safe-ai-de.html", "KI sicher nutzen")]


def page(title: str, body: str, depth: int = 0, current: str = "", issue: str = "") -> str:
    up = "../" * depth
    links = "".join(f'<a href="{up}{href}"{ARIA_CURRENT if href == current else ""}>{label}</a>'
                    for href, label in NAV)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}"><link rel="stylesheet" href="{up}style.css"></head><body>
<header class="mast"><div class="wrap"><a class="brand" href="{up}index.html">LLM Risk <span>Radar</span></a>
<span class="issue">{escape(issue)}</span>
<nav>{links}</nav></div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap"><p>Headlines link to their original publishers. Sorting is done by keyword rules, not by an AI model,
so some items land in the wrong group. Risk categories: <a href="https://genai.owasp.org/llm-top-10/">OWASP Top 10 for
LLM Applications (2025)</a>.</p></div></footer>
</body></html>"""


def monday(week: str) -> dt.date:
    year, num = week.split("-W")
    return dt.date.fromisocalendar(int(year), int(num), 1)


def week_label(week: str) -> str:
    start = monday(week)
    return f"Week {start.isocalendar()[1]}, {start.year} ({start:%d %b} – {start + dt.timedelta(days=6):%d %b})"


def weeks_back(week: str, n: int) -> list[str]:
    """The n ISO weeks ending with `week`, oldest first, including weeks with no items."""
    start = monday(week)
    return [week_of((start - dt.timedelta(weeks=k)).isoformat()) for k in range(n - 1, -1, -1)]


def highlight(title: str, keywords: list[str]) -> str:
    """Escape a headline and wrap the keywords that sorted it in <mark>."""
    terms = sorted({k for k in keywords if k}, key=len, reverse=True)
    if not terms:
        return escape(title)
    pattern = re.compile(r"(?<!\w)(" + "|".join(re.escape(t) for t in terms) + r")(?!\w)", re.IGNORECASE)
    out, pos = [], 0
    for m in pattern.finditer(title):
        out += [escape(title[pos:m.start()]), f"<mark>{escape(m.group(0))}</mark>"]
        pos = m.end()
    return "".join(out) + escape(title[pos:])


def spot(link: str) -> tuple[float, float]:
    """A stable pseudo-random place (0..1, 0..1) for an item inside its radar cell."""
    h = hashlib.sha1(link.encode()).digest()
    return h[0] / 255, h[1] / 255


def radar_svg(week: str, by_week: dict, ids: list[str]) -> str:
    """Ten sectors (one per OWASP risk), rings for the last weeks with this week in the centre."""
    cx = cy = 200
    bands = [(22, 62), (62, 98), (98, 128), (128, 152)][:RADAR_WEEKS]
    span = 360 / len(ids)
    weeks = list(reversed(weeks_back(week, RADAR_WEEKS)))  # this week first
    counts = Counter(i["category"] for w in weeks for i in by_week.get(w, []))
    top = max((counts[c] for c in ids), default=0) or 1

    def xy(r: float, deg: float) -> tuple[float, float]:
        a = math.radians(deg - 90)
        return cx + r * math.cos(a), cy + r * math.sin(a)

    def wedge(r0: float, r1: float, a0: float, a1: float) -> str:
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = xy(r1, a0), xy(r1, a1), xy(r0, a1), xy(r0, a0)
        return (f"M{x0:.1f},{y0:.1f} A{r1},{r1} 0 0 1 {x1:.1f},{y1:.1f} "
                f"L{x2:.1f},{y2:.1f} A{r0},{r0} 0 0 0 {x3:.1f},{y3:.1f}Z")

    parts = ['<defs><linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">'
             '<stop offset="0" stop-color="var(--scope)" stop-opacity="0"/>'
             '<stop offset="1" stop-color="var(--scope)" stop-opacity=".16"/></linearGradient></defs>']
    outer = bands[-1][1]
    for k, c in enumerate(ids):
        if counts[c]:
            parts.append(f'<path class="sector" fill-opacity="{.05 + .22 * counts[c] / top:.2f}" '
                         f'd="{wedge(bands[0][0], outer, k * span, (k + 1) * span)}"/>')
    parts.append(f'<path class="sweep" d="{wedge(0.01, outer, -40, 0)}"/>')
    for r in [bands[0][0]] + [b[1] for b in bands]:
        parts.append(f'<circle class="ring" cx="{cx}" cy="{cy}" r="{r}"/>')
    for k in range(len(ids)):
        (x0, y0), (x1, y1) = xy(bands[0][0], k * span), xy(outer, k * span)
        parts.append(f'<line class="spoke" x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}"/>')
    for k, c in enumerate(ids):
        x, y = xy(outer + 18, (k + .5) * span)
        parts.append(f'<text class="lbl{" hot" if counts[c] else ""}" x="{x:.1f}" y="{y:.1f}" '
                     f'text-anchor="middle" dominant-baseline="central">{escape(c)}</text>')
    for ring, w in enumerate(weeks):
        r0, r1 = bands[ring]
        for i in by_week.get(w, []):
            if i["category"] not in ids:
                continue
            k = ids.index(i["category"])
            u, v = spot(i["link"])
            x, y = xy(r0 + 5 + v * (r1 - r0 - 10), k * span + 5 + u * (span - 10))
            cls = "dot now" if ring == 0 else "dot"
            opacity = "" if ring == 0 else f' fill-opacity="{1 - .2 * ring:.1f}"'
            parts.append(f'<a href="{escape(i["link"])}" rel="noopener"><circle class="{cls}"{opacity} cx="{x:.1f}" '
                         f'cy="{y:.1f}" r="{4.5 if ring == 0 else 3.5}"><title>{escape(i["category"])}: '
                         f'{escape(i["title"])}</title></circle></a>')
    return (f'<svg class="radar" viewBox="0 0 400 400" role="img" aria-label="Headlines of the last {RADAR_WEEKS} '
            f'weeks by OWASP risk; this week in the centre">' + "".join(parts) + "</svg>")


def week_body(week: str, by_week: dict, rules: Rules, trend: str = "") -> str:
    items = by_week[week]
    counts = Counter(i["category"] for i in items)
    titles = {c.id: (c.title, c.plain) for c in rules.categories}
    titles[OTHER] = (OTHER_TITLE, OTHER_PLAIN)
    ids = [c.id for c in rules.categories]
    order = ids + [OTHER]
    matched = len(items) - counts[OTHER]
    sources = len({i["source"] for i in items})
    leader = max(ids, key=lambda c: counts[c]) if matched else None
    if leader:
        headline = f"{len(items)} headlines. Most about {titles[leader][0]}."
    else:
        headline = f"{len(items)} headline{'s' if len(items) != 1 else ''}, none matched to an OWASP risk."
    share = round(100 * matched / len(items)) if items else 0
    recent = sum(len(by_week.get(w, [])) for w in weeks_back(week, RADAR_WEEKS))
    others = sum(1 for w in weeks_back(week, RADAR_WEEKS) for i in by_week.get(w, []) if i["category"] == OTHER)

    hero = f"""<div class="hero"><div>{radar_svg(week, by_week, ids)}
<div class="legend"><span><i class="now"></i>this week</span><span><i></i>previous {RADAR_WEEKS - 1} weeks</span>
<span>{others} of {recent} in "Other", not plotted</span></div></div>
<div><p class="eyebrow">{escape(week_label(week))}</p><h1>{escape(headline)}</h1>
<p class="lede">AI security news from public sources, sorted into the OWASP Top 10 for LLM Applications by keyword rules.</p>
<dl class="stats"><div><dt>headlines</dt><dd>{len(items)}</dd></div><div><dt>matched to a risk</dt><dd>{matched}</dd></div>
<div><dt>sources</dt><dd>{sources}</dd></div></dl>
<div class="cover"><div class="track"><div class="fill" style="width:{share}%"></div></div>
<p>The rules matched {share}% of this week's headlines. The rest sit under "Other".</p></div></div></div>"""

    groups = ""
    for c in order:
        group = [i for i in items if i["category"] == c]
        if not group:
            continue
        rows = ""
        for i in group:
            kws = i.get("matched") or []
            chips = ('<span class="kw">' + "".join(f"<span>{escape(k)}</span>" for k in kws) + "</span>") if kws else ""
            rows += (f'<li><a class="hl" href="{escape(i["link"])}" rel="noopener">{highlight(i["title"], kws)}</a>'
                     f'<div class="meta"><span>{escape(i["source"])}</span>'
                     f'<span>{dt.date.fromisoformat(i["published"]):%d %b %Y}</span>{chips}</div></li>')
        label = "Other" if c == OTHER else c
        name = titles[c][0]
        groups += (f'<div class="group{" other" if c == OTHER else ""}" id="{escape(c)}">'
                   f'<div class="risk-head"><span class="rid">{escape(label)}</span><h3>{escape(name)}</h3>'
                   f'<span class="n">{len(group)}</span><p class="plain">{escape(titles[c][1])}</p></div>'
                   f'<ol class="items">{rows}</ol></div>')
    return (hero + trend + f'<section><div class="sec-head"><h2>Headlines by risk</h2>'
            f'<span class="muted small">Highlighted words are the keywords that sorted each headline.</span></div>'
            f'<div class="groups">{groups}</div></section>')


def heat_grid(latest: str, by_week: dict, rules: Rules, up: str = "") -> str:
    """Risks down, weeks across; each cell is shaded by its number of headlines."""
    weeks = weeks_back(latest, TREND_WEEKS)
    rows_spec = [(c.id, c.id, c.title) for c in rules.categories] + [(OTHER, "", OTHER_TITLE)]
    cell = {(w, c): sum(1 for i in by_week.get(w, []) if i["category"] == c) for w in weeks for c, _, _ in rows_spec}
    top = max((v for (w, c), v in cell.items() if c != OTHER), default=0) or 1
    head = "".join(f'<th scope="col"{CUR if w == latest else ""}>'
                   + (f'<a href="{up}weeks/{w}.html">W{int(w[-2:])}</a>' if by_week.get(w) else f"W{int(w[-2:])}")
                   + "</th>" for w in weeks)
    body = ""
    for c, label, title in rows_spec:
        tds = ""
        for w in weeks:
            v = cell[(w, c)]
            cur = " cur" if w == latest else ""
            if v:
                t = min(v / top, 1)
                tds += (f'<td class="v{" hi" if t > .5 else ""}{cur}" style="--t:{18 + 72 * t:.0f}%" '
                        f'title="{escape(title)}, {w}: {v}">{v}</td>')
            else:
                tds += f'<td class="{cur.strip()}"></td>' if cur else "<td></td>"
        total = sum(cell[(w, c)] for w in weeks)
        name = f'<b>{label}</b><span class="t">{escape(title)}</span>' if label else escape(title)
        body += (f'<tr{OTHER_ROW if c == OTHER else ""}><th scope="row">'
                 f'<a href="{up}risks.html#{c}" title="{escape((label + " " + title).strip())}">{name}</a></th>'
                 f'{tds}<td class="sum">{total}</td></tr>')
    return (f'<section><div class="sec-head"><h2>Risk activity, last {TREND_WEEKS} weeks</h2>'
            f'<span class="muted small">Headlines per risk and week. Darker means more.</span></div>'
            f'<div class="grid-scroll"><table class="heat"><thead><tr><th></th>{head}<th class="sum">All</th></tr></thead>'
            f"<tbody>{body}</tbody></table></div></section>")


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
    issue = f"Updated {today:%d %b %Y}"
    for w in weeks:
        body = week_body(w, by_week, rules, heat_grid(w, by_week, rules, up="../"))
        (out / "weeks" / f"{w}.html").write_text(
            page(f"LLM Risk Radar – {w}", body, depth=1, current="archive.html", issue=issue), encoding="utf-8")

    latest = weeks[0] if weeks else None
    if latest:
        index = week_body(latest, by_week, rules, heat_grid(latest, by_week, rules))
    else:
        index = ('<h1>LLM Risk Radar</h1><p class="lede">A weekly digest of AI security news from public sources, '
                 "sorted by the OWASP Top 10 for LLM Applications. Updated automatically every Monday.</p><p>No items yet.</p>")
    (out / "index.html").write_text(page("LLM Risk Radar", index, current="index.html", issue=issue), encoding="utf-8")

    top = max((len(by_week[w]) for w in weeks), default=1)
    archive = ('<p class="eyebrow">Archive</p><h1>All weeks</h1><section style="margin-top:28px"><ul class="weeks">'
               + "".join(f'<li><a href="weeks/{w}.html">{week_label(w)}</a>'
                         f'<div class="bar" style="width:{100 * len(by_week[w]) / top:.0f}%"></div>'
                         f'<span class="c">{len(by_week[w])}</span></li>' for w in weeks) + "</ul></section>")
    (out / "archive.html").write_text(page("LLM Risk Radar – all weeks", archive, current="archive.html", issue=issue),
                                      encoding="utf-8")

    totals = Counter(i["category"] for i in items)
    risks = ('<p class="eyebrow">OWASP Top 10 for LLM Applications (2025)</p><h1>The ten risks</h1>'
             '<p class="lede">Each risk in plain words, with the keywords this site uses to sort headlines.</p>'
             '<section style="margin-top:32px"><div class="risks">' + "".join(
                 f'<article class="risk" id="{c.id}"><h3><span class="rid">{c.id}</span>{escape(c.title)}</h3>'
                 f"<p>{escape(c.plain)}</p>"
                 f'<p class="muted small mono">{totals[c.id]} headline{"s" if totals[c.id] != 1 else ""} stored</p>'
                 f'<div class="kw">' + "".join(f"<span>{escape(k)}</span>" for k in c.keywords) + "</div></article>"
                 for c in rules.categories)
             + f'<article class="risk" id="{OTHER}"><h3><span class="rid">Other</span>{OTHER_TITLE}</h3>'
             f'<p>{OTHER_PLAIN}</p><p class="muted small mono">{totals[OTHER]} headlines stored</p></article>'
             "</div></section>")
    (out / "risks.html").write_text(page("LLM Risk Radar – the ten risks", risks, current="risks.html", issue=issue),
                                    encoding="utf-8")

    for name, html_text in ONEPAGERS.items():
        (out / name).write_text(html_text, encoding="utf-8")
    return weeks
