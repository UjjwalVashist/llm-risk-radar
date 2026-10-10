"""Tests run without the internet: feeds come from small recorded samples."""

import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from radar import __main__ as cli  # noqa: E402
from radar import classify, feeds, onepager, site, store  # noqa: E402
from radar.feeds import Item  # noqa: E402

RULES = classify.load_rules()
TODAY = dt.date(2026, 10, 10)

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Sample</title>
<item><title>New prompt injection attack hits AI email assistants</title><link>https://example.com/a</link>
  <pubDate>Thu, 08 Oct 2026 10:00:00 GMT</pubDate><description>&lt;p&gt;Hidden &lt;b&gt;instructions&lt;/b&gt; in an email.&lt;/p&gt;</description></item>
<item><title>Patch Tuesday fixes 80 Windows flaws</title><link>https://example.com/b</link>
  <pubDate>Wed, 07 Oct 2026 10:00:00 GMT</pubDate><description>Nothing about that topic here.</description></item>
<item><title>KI-Agenten an die kurze Leine nehmen</title><link>https://example.com/c</link>
  <pubDate>Fri, 09 Oct 2026 10:00:00 GMT</pubDate><description>Berechtigungen begrenzen.</description></item>
<item><title>From the future</title><link>https://example.com/d</link><pubDate>Fri, 09 Oct 2099 10:00:00 GMT</pubDate></item>
<item><title>No link</title><pubDate>Fri, 09 Oct 2026 10:00:00 GMT</pubDate></item>
<item><title>&lt;script&gt;alert(1)&lt;/script&gt; LLM chatbot leaks data</title><link>https://example.com/e</link>
  <pubDate>Mon, 05 Oct 2026 10:00:00 GMT</pubDate><description>data leak of personal data</description></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Sample</title>
<entry><title>Markdown image exfiltration in a coding assistant</title><link href="https://example.org/x"/>
  <updated>2026-10-06T08:00:00Z</updated><summary>exfiltration via markdown image</summary></entry></feed>"""


def item(title, summary="", ai_only=False):
    return Item(title, "https://example.com/x", "Test", "2026-10-08", summary, ai_only)


# ---------- reading feeds ----------

def test_rss_is_parsed_cleaned_and_filtered():
    items = feeds.parse(RSS, "Sample", today=TODAY)
    assert [i.link[-1] for i in items] == ["a", "b", "c", "e"]  # future item and item without link dropped
    assert items[0].summary == "Hidden instructions in an email."  # HTML removed
    assert items[0].published == "2026-10-08"


def test_atom_is_parsed_too():
    (entry,) = feeds.parse(ATOM, "Sample", today=TODAY)
    assert entry.link == "https://example.org/x" and entry.published == "2026-10-06"


def test_a_failing_feed_is_reported_and_the_rest_still_load(monkeypatch):
    def fetch(url, timeout=25):
        if "bad" in url:
            raise OSError("boom")
        return RSS
    monkeypatch.setattr(feeds, "fetch", fetch)
    items, problems = feeds.collect([{"name": "Good", "url": "https://good"}, {"name": "Bad", "url": "https://bad"}], TODAY)
    assert len(items) == 4 and problems == ["Bad: boom"]


# ---------- sorting ----------

@pytest.mark.parametrize("term, text, found", [
    ("ai", "new ai tool", True), ("ai", "email said maintain", False),
    ("rag", "attacks on rag pipelines", True), ("rag", "cloud storage outage", False),
    ("ki", "neue ki-regeln", True), ("agent", "user agents", False), ("agents", "ai agents", True),
])
def test_only_whole_words_match(term, text, found):
    assert classify.has_term(term, text) is found


def test_general_news_is_dropped_unless_about_ai():
    assert classify.is_about_ai(item("Patch Tuesday fixes 80 Windows flaws"), RULES) is False
    assert classify.is_about_ai(item("Neue Regeln für Künstliche Intelligenz"), RULES) is True
    assert classify.is_about_ai(item("Anything at all", ai_only=True), RULES) is True


@pytest.mark.parametrize("title, summary, expected", [
    ("New prompt injection attack hits AI email assistants", "", "LLM01"),
    ("LLM chatbot leaks data", "data leak of personal data", "LLM02"),
    ("Malicious package on PyPI targets AI developers", "", "LLM03"),
    ("Researchers show data poisoning of training data", "", "LLM04"),
    ("AI coding tool flaw allows remote code execution", "", "LLM05"),
    ("KI-Agenten an die kurze Leine nehmen", "Berechtigungen begrenzen.", "LLM06"),
    ("Leaked system prompt reveals chatbot rules", "", "LLM07"),
    ("Vector database flaw exposes RAG documents", "", "LLM08"),
    ("Deepfake voice cloning scam costs firm millions", "", "LLM09"),
    ("Denial of wallet: attackers burn through LLM budgets", "", "LLM10"),
    ("AI startup raises funding for security platform", "", classify.OTHER),
])
def test_headlines_go_to_the_right_risk(title, summary, expected):
    assert classify.classify(item(title, summary), RULES)[0] == expected


def test_title_counts_more_than_summary():
    # summary mentions agents twice, but the title is about prompt injection
    got, hits = classify.classify(item("Prompt injection found in chatbot", "agents and autonomous agent tools"), RULES)
    assert got == "LLM01" and "prompt injection" in hits


def test_every_category_has_an_id_title_and_keywords():
    assert [c.id for c in RULES.categories] == [f"LLM{n:02d}" for n in range(1, 11)]
    assert all(c.title and c.plain and len(c.keywords) >= 5 for c in RULES.categories)
    assert all(k == k.lower() for c in RULES.categories for k in c.keywords)


# ---------- storing ----------

def test_merge_keeps_one_per_link_drops_old_and_sorts_newest_first():
    old = [{"link": "a", "title": "old a", "published": "2026-10-01"},
           {"link": "z", "title": "ancient", "published": "2025-01-01"}]
    new = [{"link": "a", "title": "new a", "published": "2026-10-01"},
           {"link": "b", "title": "b", "published": "2026-10-09"}]
    merged = store.merge(old, new, TODAY)
    assert [i["link"] for i in merged] == ["b", "a"] and merged[1]["title"] == "old a"


def test_week_numbers_follow_the_iso_calendar():
    assert store.week_of("2026-10-10") == "2026-W41" and store.week_of("2027-01-01") == "2026-W53"


# ---------- the site ----------

def sample_items():
    out = []
    for i in feeds.parse(RSS, "Sample", today=TODAY):
        if classify.is_about_ai(i, RULES):
            out.append({"title": i.title, "link": i.link, "source": i.source, "published": i.published,
                        "category": classify.classify(i, RULES)[0], "matched": []})
    return out


def test_site_is_built_with_a_page_per_week(tmp_path):
    weeks = site.build(sample_items(), RULES, TODAY, tmp_path)
    assert weeks == ["2026-W41"]
    for name in ("index.html", "archive.html", "risks.html", "style.css", "safe-ai-de.html", "safe-ai-en.html", "weeks/2026-W41.html"):
        assert (tmp_path / name).is_file()
    index = (tmp_path / "index.html").read_text()
    assert "LLM01 Prompt Injection" in index and "Patch Tuesday" not in index


def test_html_in_feed_titles_is_removed_when_reading(tmp_path):
    site.build(sample_items(), RULES, TODAY, tmp_path)
    index = (tmp_path / "index.html").read_text()
    assert "<script>" not in index.split("</nav>")[1] and "alert(1) LLM chatbot leaks data" in index


def test_the_page_builder_escapes_whatever_it_is_given(tmp_path):
    evil = [{"title": '<img src=x onerror=alert(1)> & "quotes"', "link": 'https://example.com/"><script>x</script>',
             "source": "<b>Src</b>", "published": "2026-10-08", "category": "LLM01", "matched": []}]
    site.build(evil, RULES, TODAY, tmp_path)
    index = (tmp_path / "index.html").read_text()
    assert "<img src=x" not in index and "<script>x</script>" not in index and "<b>Src</b>" not in index
    assert "&lt;img src=x onerror=alert(1)&gt; &amp; &quot;quotes&quot;" in index


def test_empty_site_still_builds(tmp_path):
    assert site.build([], RULES, TODAY, tmp_path) == []
    assert "No items yet" in (tmp_path / "index.html").read_text()


def test_one_pagers_have_eight_rules_in_both_languages():
    for lang in ("de", "en"):
        assert len(onepager.RULES[lang]["rules"]) == 8
        assert onepager.render(lang).count('class="rule"') == 8
    assert [r[1] for r in onepager.RULES["de"]["rules"]][:7] == [r[1] for r in onepager.RULES["en"]["rules"]][:7]


# ---------- everything together ----------

def test_update_runs_end_to_end(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(feeds, "fetch", lambda url, timeout=25: RSS)
    monkeypatch.setattr(feeds, "load_feeds", lambda: [{"name": "Sample", "url": "https://sample"}])
    monkeypatch.setattr(store, "DATA", tmp_path / "data" / "items.json")
    monkeypatch.setattr(site, "DOCS", tmp_path / "docs")
    assert cli.update(TODAY) == 0
    assert "4 headlines read, 3 about AI, 3 new" in capsys.readouterr().out
    assert cli.update(TODAY) == 0  # running again adds nothing
    assert "0 new" in capsys.readouterr().out
    assert len(store.load()) == 3
