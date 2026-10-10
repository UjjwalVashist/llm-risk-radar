"""One-page awareness sheets: eight everyday rules for using AI tools safely (German and English).

Each rule names the OWASP LLM risk it protects against. The pages print on one A4 sheet.
"""

from html import escape

RULES = {
    "en": {
        "file": "safe-ai-en.html", "lang": "en", "other": ("safe-ai-de.html", "Deutsch"),
        "title": "Using AI safely",
        "sub": "Eight everyday rules for ChatGPT, Copilot, Claude and other AI assistants at work.",
        "do": "Do", "dont": "Don't", "risk": "Protects against",
        "foot": "Not sure? Ask your security team before you act. Based on the OWASP Top 10 for LLM Applications (2025).",
        "print": "Print this page", "back": "LLM Risk Radar",
        "rules": [
            ("Keep confidential data out", "LLM02 Sensitive Information Disclosure",
             "Use made-up or anonymised examples when you ask for help.",
             "Paste customer data, personal data, contracts or unpublished figures into a public AI tool."),
            ("Use approved tools only", "LLM03 Supply Chain",
             "Work with the AI tools, plugins and extensions your company has approved.",
             "Install an unknown AI plugin or browser extension because it looks useful."),
            ("Check before you trust", "LLM09 Misinformation",
             "Verify facts, figures and sources. AI can sound certain and still be wrong.",
             "Copy an AI answer into a report, an email to a customer or a decision without checking it."),
            ("Text the AI reads can attack it", "LLM01 Prompt Injection",
             "Be careful when an assistant summarises web pages, emails or files from outside.",
             "Assume a document is harmless. Hidden instructions in it can steer the AI."),
            ("Review code, commands and links", "LLM05 Improper Output Handling",
             "Read AI-written code and commands, and test them, before you run them.",
             "Run a command or click a link only because the AI suggested it."),
            ("Give AI agents small permissions", "LLM06 Excessive Agency",
             "Let an agent do only what the task needs, and confirm important steps yourself.",
             "Give an agent full access to your mailbox, files or systems “to be safe”."),
            ("No secrets in prompts", "LLM07 System Prompt Leakage",
             "Keep passwords, API keys and access tokens in the password manager.",
             "Write secrets into a prompt, a chat or the instructions of a custom assistant."),
            ("Report it, quickly", "All risks",
             "Tell your security team if data ended up in the wrong tool or an AI behaved strangely.",
             "Stay silent out of embarrassment. Fast reports limit the damage."),
        ],
    },
    "de": {
        "file": "safe-ai-de.html", "lang": "de", "other": ("safe-ai-en.html", "English"),
        "title": "KI sicher nutzen",
        "sub": "Acht Regeln für den Alltag mit ChatGPT, Copilot, Claude und anderen KI-Assistenten bei der Arbeit.",
        "do": "Richtig", "dont": "Falsch", "risk": "Schützt vor",
        "foot": "Unsicher? Fragen Sie zuerst Ihr Security-Team. Grundlage: OWASP Top 10 for LLM Applications (2025).",
        "print": "Seite drucken", "back": "LLM Risk Radar",
        "rules": [
            ("Vertrauliche Daten bleiben draußen", "LLM02 Sensitive Information Disclosure",
             "Nutzen Sie erfundene oder anonymisierte Beispiele, wenn Sie Hilfe brauchen.",
             "Kundendaten, persönliche Daten, Verträge oder unveröffentlichte Zahlen in ein öffentliches KI-Tool kopieren."),
            ("Nur freigegebene Tools nutzen", "LLM03 Supply Chain",
             "Arbeiten Sie mit den KI-Tools, Plugins und Erweiterungen, die Ihre Firma freigegeben hat.",
             "Ein unbekanntes KI-Plugin oder eine Browser-Erweiterung installieren, weil es praktisch aussieht."),
            ("Erst prüfen, dann vertrauen", "LLM09 Misinformation",
             "Prüfen Sie Fakten, Zahlen und Quellen. KI klingt oft sicher und liegt trotzdem falsch.",
             "Eine KI-Antwort ungeprüft in einen Bericht, eine Kunden-E-Mail oder eine Entscheidung übernehmen."),
            ("Texte können die KI angreifen", "LLM01 Prompt Injection",
             "Seien Sie vorsichtig, wenn ein Assistent Webseiten, E-Mails oder fremde Dateien zusammenfasst.",
             "Glauben, dass ein Dokument harmlos ist. Versteckte Anweisungen darin können die KI steuern."),
            ("Code, Befehle und Links prüfen", "LLM05 Improper Output Handling",
             "Lesen und testen Sie Code und Befehle von der KI, bevor Sie sie ausführen.",
             "Einen Befehl ausführen oder einen Link anklicken, nur weil die KI es vorschlägt."),
            ("KI-Agenten: wenig Rechte", "LLM06 Excessive Agency",
             "Ein Agent bekommt nur die Rechte, die er für die Aufgabe braucht. Wichtige Schritte bestätigen Sie selbst.",
             "Einem Agenten „zur Sicherheit“ vollen Zugriff auf Postfach, Dateien oder Systeme geben."),
            ("Keine Geheimnisse im Prompt", "LLM07 System Prompt Leakage",
             "Passwörter, API-Keys und Tokens gehören in den Passwort-Manager.",
             "Geheimnisse in einen Prompt, einen Chat oder die Anweisungen eines eigenen Assistenten schreiben."),
            ("Schnell melden", "Alle Risiken",
             "Informieren Sie Ihr Security-Team, wenn Daten im falschen Tool gelandet sind oder eine KI sich seltsam verhält.",
             "Aus Scham schweigen. Eine schnelle Meldung begrenzt den Schaden."),
        ],
    },
}

CSS = """
:root { color-scheme: light dark; --bg:#fcfcfb; --fg:#0b0b0b; --muted:#52514e; --line:#dddbd4; --card:#f3f2ee; --good:#006300; --bad:#b02a2a; --accent:#2a78d6; }
@media (prefers-color-scheme: dark) { :root { --bg:#1a1a19; --fg:#fff; --muted:#c3c2b7; --line:#3a3a36; --card:#232321; --good:#4cc94c; --bad:#f08080; --accent:#6da7ec; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif; }
main { max-width:900px; margin:0 auto; padding:24px 16px 32px; }
.top { display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; font-size:13px; margin-bottom:10px; }
a { color:var(--accent); } button { font:inherit; padding:4px 10px; border-radius:6px; border:1px solid var(--line); background:var(--card); color:var(--fg); cursor:pointer; }
h1 { font-size:30px; margin:0; letter-spacing:-.01em; } .sub { color:var(--muted); font-size:15px; margin:4px 0 16px; }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.rule { background:var(--card); border-radius:10px; padding:11px 13px; break-inside:avoid; }
.rule h2 { font-size:15px; margin:0 0 6px; } .num { color:var(--muted); font-weight:400; margin-right:4px; }
.rule p { margin:3px 0; } .do b { color:var(--good); } .dont b { color:var(--bad); }
.risk { color:var(--muted); font-size:11.5px; margin-top:6px !important; }
.foot { margin-top:14px; color:var(--muted); font-size:12.5px; border-top:1px solid var(--line); padding-top:10px; }
@media (max-width:640px) { .grid { grid-template-columns:1fr; } }
@page { size:A4; margin:12mm; }
@media print { :root { --bg:#fff; --fg:#000; --muted:#444; --card:#f3f2ee; --line:#ccc; --good:#006300; --bad:#b02a2a; }
  .top { display:none; } main { padding:0; max-width:none; } .grid { grid-template-columns:1fr 1fr; } }
"""


def render(lang: str) -> str:
    t = RULES[lang]
    cards = "".join(
        f'<div class="rule"><h2><span class="num">{n}</span>{escape(title)}</h2>'
        f'<p class="do"><b>✓ {t["do"]}:</b> {escape(do)}</p>'
        f'<p class="dont"><b>✕ {t["dont"]}:</b> {escape(dont)}</p>'
        f'<p class="risk">{t["risk"]}: {escape(risk)}</p></div>'
        for n, (title, risk, do, dont) in enumerate(t["rules"], start=1))
    return f"""<!doctype html>
<html lang="{t['lang']}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(t['title'])}</title><style>{CSS}</style></head><body><main>
<div class="top"><span><a href="index.html">← {t['back']}</a> · <a href="{t['other'][0]}">{t['other'][1]}</a></span>
<button onclick="window.print()">{t['print']}</button></div>
<h1>{escape(t['title'])}</h1><p class="sub">{escape(t['sub'])}</p>
<div class="grid">{cards}</div>
<p class="foot">{escape(t['foot'])}</p>
</main></body></html>"""


PAGES = {RULES[lang]["file"]: render(lang) for lang in RULES}
