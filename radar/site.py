"""Build the static website in docs/ from the stored items.

The site looks and works like a small threat-intelligence product: a sidebar, a
dashboard with charts for the last complete week, a filterable headline feed,
one page per risk and per week, and an RSS feed. Everything is plain HTML, CSS and
a little JavaScript (Chart.js for the charts), written by Python.
"""

import datetime as dt
import json
import re
from collections import Counter, defaultdict
from email.utils import format_datetime
from html import escape
from pathlib import Path

from .classify import OTHER, Rules
from .feeds import ROOT
from .onepager import PAGES as ONEPAGERS
from .store import week_of

DOCS = ROOT / "docs"
SITE_URL = "https://ujjwalvashist.github.io/llm-risk-radar/"
REPO_URL = "https://github.com/UjjwalVashist/llm-risk-radar"
CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"
OTHER_TITLE = "Other AI security news"
OTHER_PLAIN = "About AI and security, but not clearly one of the ten OWASP risks."
CVE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I)
# Words that make a headline urgent for a security team: something is being exploited or needs a patch now.
URGENT = re.compile(r"\b(zero[- ]day|0-day|actively exploited|exploited in the wild|in the wild|critical|"
                    r"emergency patch|patch now|under attack|kritische?n?|ausgenutzt)\b", re.I)
TREND_WEEKS = 12
# One colour per risk, used in charts, tags and tiles (OTHER last, in grey).
COLORS = ["#2563eb", "#7c3aed", "#db2777", "#ea580c", "#ca8a04", "#16a34a", "#0891b2", "#4f46e5", "#be123c", "#0d9488", "#94a3b8"]

CSS = """
:root { --bg:#f6f7f9; --panel:#fff; --fg:#0f172a; --muted:#64748b; --line:#e5e7eb; --soft:#f1f5f9; --side:#0b1220; --side-fg:#cbd5e1;
  --accent:#2563eb; --hot:#dc2626; --up:#dc2626; --down:#16a34a; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 Geist,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; display:flex; min-height:100vh; }
a { color:var(--accent); text-decoration:none; } a:hover { text-decoration:underline; }
.mono { font-family:"Geist Mono",ui-monospace,monospace; }
aside { width:236px; flex:none; background:var(--side); color:var(--side-fg); display:flex; flex-direction:column; padding:18px 14px; position:sticky; top:0; height:100vh; }
.brand { display:flex; align-items:center; gap:10px; color:#fff; font-weight:600; font-size:15px; padding:2px 8px 18px; }
.brand:hover { text-decoration:none; }
.logo { width:30px; height:30px; border-radius:8px; background:conic-gradient(from 200deg,#2563eb,#7c3aed,#db2777,#2563eb); display:grid; place-items:center; }
.logo i { width:12px; height:12px; border-radius:50%; background:var(--side); box-shadow:0 0 0 3px #fff; }
aside .label { font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:#64748b; padding:14px 10px 6px; }
aside nav { display:flex; flex-direction:column; gap:2px; }
aside nav a { display:flex; align-items:center; gap:10px; color:var(--side-fg); padding:8px 10px; border-radius:8px; font-size:13.5px; }
aside nav a:hover { background:#111a2e; color:#fff; text-decoration:none; }
aside nav a.on { background:#1e293b; color:#fff; }
aside nav em { margin-left:auto; font-style:normal; font-size:11px; background:#7f1d1d; color:#fecaca; border-radius:999px; padding:0 7px; }
.side-foot { margin-top:auto; font-size:12px; color:#64748b; padding:0 8px; }
.side-foot a { color:#cbd5e1; display:block; margin-bottom:8px; }
.live { display:flex; align-items:center; gap:8px; background:#111a2e; border:1px solid #1e293b; border-radius:10px; padding:9px 12px; margin-bottom:14px; font-size:12px; }
.live i { width:8px; height:8px; border-radius:50%; background:#22c55e; box-shadow:0 0 0 3px rgb(34 197 94 / .2); }
.app { flex:1; min-width:0; display:flex; flex-direction:column; }
.topbar { height:58px; background:var(--panel); border-bottom:1px solid var(--line); display:flex; align-items:center; gap:12px; padding:0 24px; position:sticky; top:0; z-index:5; }
.crumbs { color:var(--muted); font-size:13px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; } .crumbs b { color:var(--fg); font-weight:500; }
.sp { flex:1; }
.pill { background:var(--soft); border-radius:999px; padding:4px 10px; font-size:12.5px; color:var(--muted); white-space:nowrap; }
.btn { border:1px solid var(--line); background:var(--panel); color:var(--fg); border-radius:8px; padding:7px 12px; font:inherit; font-size:13px; cursor:pointer; white-space:nowrap; }
.btn:hover { text-decoration:none; border-color:#cbd5e1; } .btn.dark { background:var(--fg); color:#fff; border-color:var(--fg); }
main { padding:24px; max-width:1360px; width:100%; }
.vh { display:flex; align-items:end; justify-content:space-between; gap:16px; margin-bottom:18px; flex-wrap:wrap; }
.vh h1 { font-size:22px; letter-spacing:-.02em; margin:0; } .vh p { margin:2px 0 0; color:var(--muted); font-size:13px; }
.grid { display:grid; gap:16px; margin-bottom:16px; }
.k4 { grid-template-columns:repeat(4,minmax(0,1fr)); } .c21 { grid-template-columns:minmax(0,2fr) minmax(0,1fr); }
.c3 { grid-template-columns:repeat(auto-fill,minmax(210px,1fr)); }
.card { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:16px 18px; min-width:0; }
.card h3 { margin:0; font-size:13.5px; font-weight:600; }
.ch { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; gap:8px; } .ch small { color:var(--muted); font-size:12px; }
.kpi .l { color:var(--muted); font-size:12.5px; }
.kpi .v { font-size:28px; font-weight:600; letter-spacing:-.02em; margin:4px 0 2px; display:flex; align-items:baseline; gap:8px; }
.kpi .f { font-size:12px; color:var(--muted); }
.delta { font-size:12px; font-weight:500; border-radius:6px; padding:1px 6px; }
.delta.up { color:#b91c1c; background:#fee2e2; } .delta.down { color:#15803d; background:#dcfce7; } .delta.flat { color:var(--muted); background:var(--soft); }
.alert { display:flex; gap:12px; align-items:center; background:#fef2f2; border:1px solid #fecaca; color:#7f1d1d; border-radius:12px; padding:12px 16px; margin-bottom:16px; }
.alert .sp { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.alert .ico { width:26px; height:26px; flex:none; border-radius:7px; background:#fee2e2; display:grid; place-items:center; font-weight:700; color:var(--hot); }
.chart { position:relative; height:260px; } .chart.small { height:200px; }
.mix { display:grid; grid-template-columns:150px minmax(0,1fr); gap:14px; align-items:center; }
.legend div { display:flex; align-items:center; gap:8px; padding:4px 0; font-size:12.5px; white-space:nowrap; overflow:hidden; }
.legend b { margin-left:auto; } .dot { width:9px; height:9px; border-radius:3px; flex:none; }
.tile { display:flex; flex-direction:column; gap:4px; color:inherit; border-top:3px solid var(--c); transition:box-shadow .15s; }
.tile:hover { text-decoration:none; box-shadow:0 6px 18px rgb(15 23 42 / .07); }
.tile .id { font:500 11.5px "Geist Mono",ui-monospace,monospace; color:var(--c); }
.tile b { font-size:13.5px; font-weight:600; min-height:38px; }
.tile .row { display:flex; justify-content:space-between; align-items:end; }
.tile .n { font-size:24px; font-weight:600; letter-spacing:-.02em; }
.spark { width:100px; height:30px; }
.spark path { fill:none; stroke:var(--c, var(--accent)); stroke-width:2; }
.spark .area { fill:var(--c, var(--accent)); opacity:.12; stroke:none; }
.toolbar { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:6px; }
.chip { border:1px solid var(--line); background:var(--panel); color:var(--muted); border-radius:999px; padding:4px 11px; font:inherit; font-size:12.5px; cursor:pointer; }
.chip[aria-pressed=true] { background:var(--fg); color:#fff; border-color:var(--fg); }
.chip.hotchip[aria-pressed=true] { background:var(--hot); border-color:var(--hot); }
.toolbar input { flex:1; min-width:200px; font:inherit; font-size:13px; border:1px solid var(--line); border-radius:8px; padding:7px 10px; }
ul.items { list-style:none; padding:0; margin:0; }
ul.items li { padding:12px 0; border-bottom:1px solid var(--soft); display:grid; grid-template-columns:4px minmax(0,1fr); gap:12px; }
ul.items li[hidden] { display:none; } ul.items li:last-child { border:0; }
ul.items .rail { border-radius:2px; background:var(--c); }
.headline { font-weight:500; color:var(--fg); } .headline:hover { color:var(--accent); }
.meta { color:var(--muted); font-size:12.5px; margin-top:4px; display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
.tag { font-size:11.5px; border-radius:6px; padding:1px 7px; background:var(--soft); color:#334155; white-space:nowrap; }
.tag.cat { background:color-mix(in srgb, var(--c) 12%, white); color:var(--c); font-weight:500; }
.tag.hot { background:#fee2e2; color:#b91c1c; font-weight:500; }
.why code { background:var(--soft); border-radius:4px; padding:0 4px; font-size:11.5px; color:#475569; }
.count { color:var(--muted); font-size:12.5px; padding-top:10px; }
.list li { display:flex; gap:10px; padding:9px 0; border-bottom:1px solid var(--soft); font-size:13px; align-items:baseline; }
ul.list { list-style:none; padding:0; margin:0; } .list li:last-child { border:0; } .list b { margin-left:auto; }
.bars { display:grid; grid-template-columns:minmax(0,1fr) 34px; gap:8px 10px; align-items:center; font-size:12.5px; }
.bars .b { height:8px; border-radius:4px; background:var(--c); min-width:3px; } .bars .lbl { grid-column:1/-1; display:flex; justify-content:space-between; margin-bottom:-4px; }
table { border-collapse:collapse; width:100%; font-size:12.5px; }
th { text-align:center; font-weight:500; color:var(--muted); font-size:11px; padding:6px 4px; white-space:nowrap; } th:first-child { text-align:left; }
td { padding:3px; } td.heat { text-align:center; border-radius:5px; height:28px; font-variant-numeric:tabular-nums; }
td.n { text-align:right; color:var(--muted); padding-right:6px; }
.scroll { overflow-x:auto; }
.risk-card { scroll-margin-top:80px; border-left:4px solid var(--c); }
.risk-card .id { font:500 12px "Geist Mono",monospace; color:var(--c); }
.risk-card h2 { margin:2px 0 6px; font-size:18px; } .risk-card p { margin:0 0 10px; color:#334155; }
.kw { display:flex; flex-wrap:wrap; gap:4px; margin:10px 0; }
.muted { color:var(--muted); } .small { font-size:12.5px; }
footer { color:var(--muted); font-size:12px; padding:8px 24px 24px; max-width:1360px; }
@media (max-width:1100px) { .k4 { grid-template-columns:repeat(2,minmax(0,1fr)); } .c21 { grid-template-columns:minmax(0,1fr); } }
@media (max-width:760px) { body { display:block; } aside { position:static; width:auto; height:auto; padding:12px; }
  aside nav { flex-direction:row; overflow-x:auto; } aside .label, .side-foot, .live { display:none; } .brand { padding-bottom:10px; }
  .topbar { padding:0 14px; } .pill { display:none; } main { padding:16px; } .mix { grid-template-columns:1fr; } }
"""

FILTER_JS = """<script>
(() => {
  const list = document.querySelectorAll("ul.items li[data-cat]"), q = document.getElementById("q");
  if (!q) return;
  let cat = "all", hot = false;
  function draw() {
    const term = q.value.trim().toLowerCase(); let n = 0;
    list.forEach(li => {
      const show = (cat === "all" || li.dataset.cat === cat) && (!hot || li.dataset.hot === "1") &&
                   (!term || li.textContent.toLowerCase().includes(term));
      li.hidden = !show; n += show;
    });
    document.getElementById("count").textContent = `${n} of ${list.length} headlines`;
  }
  document.querySelectorAll(".chip[data-cat]").forEach(b => b.onclick = () => {
    cat = b.dataset.cat;
    document.querySelectorAll(".chip[data-cat]").forEach(c => c.setAttribute("aria-pressed", c === b));
    draw();
  });
  const h = document.getElementById("hot");
  h.onclick = () => { hot = !hot; h.setAttribute("aria-pressed", hot); draw(); };
  q.oninput = draw; draw();
})();
</script>"""

CHARTS_JS = """<script>
(() => {
  const el = document.getElementById("chart-data");
  if (!el || !window.Chart) return;
  const D = JSON.parse(el.textContent);
  Chart.defaults.font.family = "Geist, -apple-system, sans-serif"; Chart.defaults.color = "#64748b";
  Chart.defaults.plugins.legend.display = false;
  new Chart(document.getElementById("cTrend"), {type:"bar", data:{labels:D.weeks, datasets:D.series.map(s => ({label:s.label, data:s.data, backgroundColor:s.color, stack:"s", borderRadius:2}))},
    options:{maintainAspectRatio:false, interaction:{mode:"index", intersect:false},
      plugins:{tooltip:{filter:i => i.raw > 0}}, scales:{x:{grid:{display:false}}, y:{grid:{color:"#f1f5f9"}, ticks:{precision:0}}}}});
  new Chart(document.getElementById("cMix"), {type:"doughnut", data:{labels:D.mix.map(m => m.label), datasets:[{data:D.mix.map(m => m.n), backgroundColor:D.mix.map(m => m.color), borderWidth:0}]},
    options:{maintainAspectRatio:false, cutout:"68%"}});
})();
</script>"""


def page(title: str, body: str, active: str, depth: int = 0, crumb: str = "", priority: int = 0,
         week: str = "", extra_js: str = "") -> str:
    up = "../" * depth
    nav = [("index.html", "overview", "Dashboard"), ("risks.html", "risks", "The ten risks"), ("archive.html", "archive", "All weeks")]
    nav_html = "".join(f'<a href="{up}{href}" class="{"on" if key == active else ""}">{label}'
                       f'{f"<em>{priority}</em>" if key == "overview" and priority else ""}</a>' for href, key, label in nav)
    guides = (f'<a href="{up}safe-ai-en.html">Using AI safely</a><a href="{up}safe-ai-de.html">KI sicher nutzen</a>'
              f'<a href="{up}feed.xml">RSS feed</a>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title><meta name="description" content="Weekly AI security news, sorted by the OWASP Top 10 for LLM Applications.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@500&display=swap" rel="stylesheet">
<link rel="alternate" type="application/rss+xml" title="LLM Risk Radar" href="{up}feed.xml">
<link rel="stylesheet" href="{up}style.css">{f'<script src="{CHART_JS}"></script>' if extra_js else ""}</head><body>
<aside><a class="brand" href="{up}index.html"><span class="logo"><i></i></span>LLM Risk Radar</a>
<div class="live"><i></i>Updated every Monday · 13 sources</div>
<nav>{nav_html}</nav><div class="label">Guides</div><nav>{guides}</nav>
<div class="side-foot"><a href="{REPO_URL}">Source code on GitHub ↗</a>Python · GitHub Actions · Pages</div></aside>
<div class="app"><div class="topbar"><div class="crumbs">Radar / <b>{escape(crumb or title)}</b></div><span class="sp"></span>
{f'<span class="pill">{escape(week)}</span>' if week else ""}<a class="btn" href="{up}feed.xml">Subscribe (RSS)</a></div>
<main>{body}</main>
<footer>Headlines link to their original publishers. Sorting uses transparent keyword rules, not an AI model, so some items land
in the wrong group – each headline shows the words that decided it. Categories: <a href="https://genai.owasp.org/llm-top-10/">OWASP Top 10 for LLM Applications (2025)</a>.</footer>
</div>{FILTER_JS}{extra_js}</body></html>"""


def week_label(week: str) -> str:
    year, num = week.split("-W")
    monday = dt.date.fromisocalendar(int(year), int(num), 1)
    return f"Week {int(num)}, {year} ({monday:%d %b} – {monday + dt.timedelta(days=6):%d %b})"


def week_before(week: str) -> str:
    year, num = week.split("-W")
    y, w, _ = (dt.date.fromisocalendar(int(year), int(num), 1) - dt.timedelta(days=7)).isocalendar()
    return f"{y}-W{w:02d}"


def last_weeks(latest: str, n: int) -> list[str]:
    out = [latest]
    for _ in range(n - 1):
        out.append(week_before(out[-1]))
    return out[::-1]


def signals(item: dict) -> tuple[list[str], bool]:
    """CVE IDs in the headline, and whether it reads as urgent (exploited, zero-day, critical)."""
    cves = sorted({c.upper() for c in CVE.findall(item["title"])})
    return cves, bool(cves) or bool(URGENT.search(item["title"]))


def delta(now: int, before: int) -> str:
    if now == before:
        return '<span class="delta flat">± 0</span>'
    return f'<span class="delta {"up" if now > before else "down"}">{"▲" if now > before else "▼"} {abs(now - before)}</span>'


def sparkline(values: list[int], color: str = "") -> str:
    """A tiny inline SVG trend line, oldest week left."""
    w, h, top = 100, 30, max(values + [1])
    pts = [(i * w / max(len(values) - 1, 1), h - 3 - (v / top) * (h - 6)) for i, v in enumerate(values)]
    line = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
    style = f' style="--c:{color}"' if color else ""
    return (f'<svg class="spark"{style} viewBox="0 0 {w} {h}" aria-label="Trend over {len(values)} weeks: {", ".join(map(str, values))}">'
            f'<path class="area" d="{line} L{w},{h} L0,{h} Z"/><path d="{line}"/></svg>')


class Catalog:
    """Titles, plain explanations and colours of the ten risks plus OTHER."""

    def __init__(self, rules: Rules):
        self.order = [c.id for c in rules.categories] + [OTHER]
        self.title = {c.id: c.title for c in rules.categories} | {OTHER: OTHER_TITLE}
        self.plain = {c.id: c.plain for c in rules.categories} | {OTHER: OTHER_PLAIN}
        self.color = dict(zip(self.order, COLORS))

    def full(self, cat: str) -> str:
        return f"{cat} {self.title[cat]}" if cat != OTHER else OTHER_TITLE


def item_html(i: dict, cat: Catalog) -> str:
    cves, hot = signals(i)
    tags = "".join(f'<a class="tag hot" href="https://nvd.nist.gov/vuln/detail/{c}">{c}</a>' for c in cves)
    if hot and not cves:
        tags += '<span class="tag hot">Priority</span>'
    why = (f'<span class="why">matched {" ".join(f"<code>{escape(m)}</code>" for m in i.get("matched", [])[:4])}</span>'
           if i.get("matched") else "")
    return (f'<li data-cat="{escape(i["category"])}" data-hot="{int(hot)}" style="--c:{cat.color[i["category"]]}"><span class="rail"></span><div>'
            f'<a class="headline" href="{escape(i["link"])}" rel="noopener">{escape(i["title"])}</a>'
            f'<div class="meta"><span class="tag cat">{escape(cat.full(i["category"]))}</span>{tags}'
            f'<span>{escape(i["source"])} · {dt.date.fromisoformat(i["published"]):%d %b}</span>{why}</div></div></li>')


def kpis(items: list[dict], before: list[dict]) -> str:
    counts = Counter(i["category"] for i in items)
    hot = sum(signals(i)[1] for i in items)
    matched = len(items) - counts[OTHER]
    return f"""<div class="grid k4">
<div class="card kpi"><div class="l">AI security headlines</div><div class="v">{len(items)}{delta(len(items), len(before))}</div><div class="f">vs. {len(before)} the week before</div></div>
<div class="card kpi"><div class="l">Matched to an OWASP risk</div><div class="v">{matched / max(len(items), 1):.0%}</div><div class="f">{matched} of {len(items)} headlines</div></div>
<div class="card kpi"><div class="l">Priority items</div><div class="v" style="color:{"var(--hot)" if hot else "inherit"}">{hot}</div><div class="f">CVE, zero-day or active exploit</div></div>
<div class="card kpi"><div class="l">Sources reporting</div><div class="v">{len({i["source"] for i in items})}</div><div class="f">of 13 public feeds</div></div></div>"""


def feed_card(items: list[dict], cat: Catalog) -> str:
    counts = Counter(i["category"] for i in items)
    chips = '<button class="chip" data-cat="all" aria-pressed="true">All</button>' + "".join(
        f'<button class="chip" data-cat="{c}" aria-pressed="false">{c if c != OTHER else "Other"}</button>' for c in cat.order if counts[c])
    rows = "".join(item_html(i, cat) for i in sorted(items, key=lambda i: (signals(i)[1], i["published"]), reverse=True))
    return (f'<div class="card"><div class="ch"><h3>Headlines</h3><small>priority first · newest first</small></div>'
            f'<div class="toolbar">{chips}<button class="chip hotchip" id="hot" aria-pressed="false">● Priority only</button></div>'
            f'<div class="toolbar"><input id="q" type="search" placeholder="Search headlines, sources, CVEs …" aria-label="Search"></div>'
            f'<ul class="items">{rows}</ul><div class="count" id="count"></div></div>')


def side_cards(items: list[dict], cat: Catalog) -> str:
    counts = Counter(i["category"] for i in items)
    top = max(counts.values(), default=1)
    bars = "".join(f'<div class="lbl"><span>{escape(cat.full(c))}</span><b>{counts[c]}</b></div>'
                   f'<div class="b" style="--c:{cat.color[c]};width:{100 * counts[c] / top:.0f}%"></div><span></span>'
                   for c in sorted(cat.order, key=lambda c: -counts[c]) if counts[c])
    sources = "".join(f'<li><span>{escape(s)}</span><b>{n}</b></li>' for s, n in Counter(i["source"] for i in items).most_common(6))
    return (f'<div style="display:flex;flex-direction:column;gap:16px"><div class="card"><div class="ch"><h3>Risk mix</h3></div><div class="bars">{bars}</div></div>'
            f'<div class="card"><div class="ch"><h3>Top sources</h3></div><ul class="list">{sources}</ul></div></div>')


def priority_alert(items: list[dict]) -> str:
    hot = [i for i in items if signals(i)[1]]
    if not hot:
        return ""
    first = hot[0]
    return (f'<div class="alert"><span class="ico">!</span><b style="white-space:nowrap">{len(hot)} priority item{"s" if len(hot) > 1 else ""}</b>'
            f'<span class="sp">{escape(first["title"])}</span><a class="btn" href="{escape(first["link"])}" rel="noopener">Read</a></div>')


def week_body(week: str, items: list[dict], rules: Rules, before: list[dict] | None = None) -> str:
    """KPIs, the headline feed and the risk mix of one week."""
    cat = Catalog(rules)
    return (priority_alert(items) + kpis(items, before or [])
            + f'<div class="grid c21">{feed_card(items, cat)}{side_cards(items, cat)}</div>')


def latest_links(items: list[dict], c: str, n: int = 3) -> str:
    hits = [i for i in items if i["category"] == c][:n]
    return "".join(f'<li><a href="{escape(i["link"])}" rel="noopener">{escape(i["title"])}</a><b class="small">{escape(i["source"])}</b></li>'
                   for i in hits) or '<li class="muted">No headlines yet.</li>'


def trend_values(by_week: dict, weeks_old_first: list[str], c: str) -> list[int]:
    return [sum(1 for i in by_week.get(w, []) if i["category"] == c) for w in weeks_old_first]


def feed_xml(items: list[dict], cat: Catalog, today: dt.date) -> str:
    """An RSS 2.0 feed of the newest headlines, so security teams can follow the radar in their reader."""
    entries = "".join(
        f"<item><title>{escape(i['title'])}</title><link>{escape(i['link'])}</link>"
        f"<guid isPermaLink=\"true\">{escape(i['link'])}</guid><category>{escape(cat.full(i['category']))}</category>"
        f"<pubDate>{format_datetime(dt.datetime.combine(dt.date.fromisoformat(i['published']), dt.time(8), dt.timezone.utc))}</pubDate>"
        f"<description>{escape(cat.full(i['category']))} · {escape(i['source'])}</description></item>"
        for i in items[:50])
    built = format_datetime(dt.datetime.combine(today, dt.time(6), dt.timezone.utc))
    return (f'<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0"><channel><title>LLM Risk Radar</title>'
            f"<link>{SITE_URL}</link><description>Weekly AI security news, sorted by the OWASP Top 10 for LLM Applications."
            f"</description><language>en</language><lastBuildDate>{built}</lastBuildDate>{entries}</channel></rss>\n")


def build(items: list[dict], rules: Rules, today: dt.date, out: Path | None = None) -> list[str]:
    """Write the whole site. Returns the weeks that have a page, newest first."""
    out = out or DOCS
    out.mkdir(exist_ok=True)
    (out / "weeks").mkdir(exist_ok=True)
    (out / "style.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")  # plain static files, no Jekyll build

    cat = Catalog(rules)
    by_week = defaultdict(list)
    for i in items:
        by_week[week_of(i["published"])].append(i)
    weeks = sorted(by_week, reverse=True)
    for w in weeks:
        body = (f'<div class="vh"><div><h1>{week_label(w)}</h1><p>{len(by_week[w])} headlines sorted into OWASP risks</p></div>'
                f'<a class="btn" href="../archive.html">All weeks</a></div>' + week_body(w, by_week[w], rules, by_week.get(week_before(w))))
        hot = sum(signals(i)[1] for i in by_week[w])
        (out / "weeks" / f"{w}.html").write_text(page(f"LLM Risk Radar – {w}", body, "archive", 1, w, hot, week_label(w)), encoding="utf-8")

    # The update runs on Monday morning, so the newest week has barely started: lead with the last complete one.
    complete = [w for w in weeks if dt.date.fromisocalendar(*map(int, w.split("-W")), 7) < today]
    latest = (complete or weeks or [None])[0]
    if latest:
        span = last_weeks(latest, TREND_WEEKS)
        this = by_week[latest]
        counts = Counter(i["category"] for i in this)
        data = {"weeks": [f"W{w.split('-W')[1]}" for w in span],
                "series": [{"label": cat.full(c), "color": cat.color[c], "data": trend_values(by_week, span, c)} for c in cat.order],
                "mix": [{"label": cat.full(c), "color": cat.color[c], "n": counts[c]} for c in cat.order if counts[c]]}
        legend = "".join(f'<div><i class="dot" style="background:{m["color"]}"></i>{escape(m["label"])}<b>{m["n"]}</b></div>' for m in data["mix"][:6])
        tiles = "".join(
            f'<a class="card tile" href="risks.html#{c}" style="--c:{cat.color[c]}"><span class="id">{c if c != OTHER else "OTHER"}</span>'
            f'<b>{escape(cat.title[c])}</b><div class="row"><span class="n">{counts[c]}</span>{sparkline(trend_values(by_week, span, c), cat.color[c])}</div></a>'
            for c in cat.order)
        index = (f'<div class="vh"><div><h1>AI security this week</h1><p>{week_label(latest)} · {len(this)} headlines from public sources, '
                 f'sorted into the OWASP Top 10 for LLM Applications</p></div><a class="btn dark" href="weeks/{latest}.html">Open week report</a></div>'
                 + priority_alert(this) + kpis(this, by_week.get(week_before(latest), []))
                 + f'<div class="grid c21"><div class="card"><div class="ch"><h3>Headlines per week, by risk</h3><small>last {TREND_WEEKS} weeks</small></div>'
                 f'<div class="chart"><canvas id="cTrend" aria-label="Stacked bar chart of headlines per week and risk"></canvas></div></div>'
                 f'<div class="card"><div class="ch"><h3>Risk mix</h3><small>{week_label(latest).split(" (")[0]}</small></div>'
                 f'<div class="mix"><div class="chart small"><canvas id="cMix" aria-label="Doughnut chart of this week\'s risk mix"></canvas></div><div class="legend">{legend}</div></div></div></div>'
                 f'<div class="ch" style="margin-top:8px"><h3>The ten risks</h3><small>this week · {TREND_WEEKS}-week trend</small></div>'
                 f'<div class="grid c3">{tiles}</div>'
                 f'<div class="grid c21">{feed_card(this, cat)}{side_cards(this, cat)}</div>'
                 f'<script type="application/json" id="chart-data">{json.dumps(data)}</script>'
                 f'<p class="muted small">Last update {today:%d %b %Y}.</p>')
        hot = sum(signals(i)[1] for i in this)
    else:
        index, hot = '<div class="vh"><div><h1>LLM Risk Radar</h1><p>No items yet.</p></div></div>', 0
    (out / "index.html").write_text(page("LLM Risk Radar – weekly AI security news", index, "overview", 0, "Dashboard", hot,
                                         week_label(latest) if latest else "", CHARTS_JS if latest else ""), encoding="utf-8")

    rows = "".join(
        f'<tr><td><a href="weeks/{w}.html">{week_label(w).split(" (")[0]}</a><div class="muted small">{week_label(w).split("(")[1].rstrip(")")}</div></td>'
        + "".join((lambda n, c: f'<td class="heat" style="background:{"color-mix(in srgb, " + cat.color[c] + f" {min(90, 15 + 12 * n)}%, white)" if n else "#f8fafc"};color:{"#fff" if n >= 5 else "#334155"}">{n or ""}</td>')(
            sum(1 for i in by_week[w] if i["category"] == c), c) for c in cat.order)
        + f'<td class="n"><b>{len(by_week[w])}</b></td><td class="n">{sum(signals(i)[1] for i in by_week[w]) or ""}</td></tr>' for w in weeks)
    head = "".join(f'<th>{c if c != OTHER else "Other"}</th>' for c in cat.order)
    archive = (f'<div class="vh"><div><h1>All weeks</h1><p>{len(weeks)} weeks · {len(items)} headlines · colour = number of headlines per risk</p></div></div>'
               f'<div class="card scroll"><table><thead><tr><th>Week</th>{head}<th class="n">All</th><th class="n">Priority</th></tr></thead><tbody>{rows}</tbody></table></div>')
    (out / "archive.html").write_text(page("LLM Risk Radar – all weeks", archive, "archive", 0, "All weeks"), encoding="utf-8")

    span = last_weeks(latest, TREND_WEEKS) if latest else []
    risks = ('<div class="vh"><div><h1>The ten risks</h1><p>OWASP Top 10 for LLM Applications (2025) in plain words, '
             'with the sorting keywords and the latest matching headlines</p></div></div>' + "".join(
                 f'<section class="card risk-card" id="{c.id}" style="--c:{cat.color[c.id]};margin-bottom:14px">'
                 f'<div class="ch"><div><span class="id">{c.id}</span><h2>{escape(c.title)}</h2></div>'
                 f'<div style="text-align:right">{sparkline(trend_values(by_week, span, c.id), cat.color[c.id]) if span else ""}'
                 f'<div class="muted small">{sum(1 for i in items if i["category"] == c.id)} headlines · {len(weeks)} weeks</div></div></div>'
                 f'<p>{escape(c.plain)}</p><div class="kw">{"".join(f"<span class=tag>{escape(k)}</span>" for k in c.keywords)}</div>'
                 f'<ul class="list">{latest_links(items, c.id)}</ul>'
                 f"</section>" for c in rules.categories))
    (out / "risks.html").write_text(page("LLM Risk Radar – the ten risks", risks, "risks", 0, "The ten risks"), encoding="utf-8")
    (out / "feed.xml").write_text(feed_xml(items, cat, today), encoding="utf-8")

    for name, html_text in ONEPAGERS.items():
        (out / name).write_text(html_text, encoding="utf-8")
    return weeks
