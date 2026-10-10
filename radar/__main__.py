"""Command line.

    python -m radar update    fetch the feeds, sort new items, rebuild the site
    python -m radar build     rebuild the site from data/items.json (no network)
"""

import argparse
import datetime as dt
import sys

from . import classify, feeds, site, store


def update(today: dt.date) -> int:
    rules = classify.load_rules()
    found, problems = feeds.collect(feeds.load_feeds(), today)
    for p in problems:
        print(f"skipped feed - {p}", file=sys.stderr)
    new = []
    for item in found:
        if classify.is_about_ai(item, rules):
            category, hits = classify.classify(item, rules)
            new.append({"title": item.title, "link": item.link, "source": item.source,
                        "published": item.published, "category": category, "matched": hits})
    old = store.load()
    items = store.merge(old, new, today)
    store.save(items)
    weeks = site.build(items, rules, today)
    added = len({i["link"] for i in items} - {i["link"] for i in old})
    print(f"{len(found)} headlines read, {len(new)} about AI, {added} new. "
          f"{len(items)} items in {len(weeks)} weeks. {len(problems)} feed(s) skipped.")
    return 1 if problems and not found else 0  # only fail when nothing could be read


def main() -> None:
    ap = argparse.ArgumentParser(prog="radar", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["update", "build"])
    ap.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today(),
                    help="pretend it is this date (YYYY-MM-DD); used by tests")
    args = ap.parse_args()
    if args.command == "update":
        sys.exit(update(args.today))
    weeks = site.build(store.load(), classify.load_rules(), args.today)
    print(f"Site rebuilt: {len(weeks)} weeks.")


if __name__ == "__main__":
    main()
