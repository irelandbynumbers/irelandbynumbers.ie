"""List the hand-checked data sources in analysis/manual_sources.yml that are
due, as Markdown for a GitHub issue. Prints nothing when none are due.

Usage: python3 tools/check_manual_sources.py [YYYY-MM-DD]
"""
import datetime
import os
import sys

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def due(items, today):
    out = []
    for item in items:
        last = item.get("last_checked")
        if last in (None, "never"):
            out.append((item, "Not downloaded yet"))
            continue
        last = last if isinstance(last, datetime.date) else datetime.date.fromisoformat(str(last))
        months = (today.year - last.year) * 12 + today.month - last.month - (today.day < last.day)
        if months >= int(item["every_months"]):
            out.append((item, f"Last checked {last:%-d %B %Y}"))
    return out


def main(argv):
    today = datetime.date.fromisoformat(argv[0]) if argv else datetime.date.today()
    with open(os.path.join(ROOT, "analysis", "manual_sources.yml"), encoding="utf-8") as f:
        items = yaml.safe_load(f)
    rows = due(items, today)
    if not rows:
        return
    print("These data sources can't be fetched automatically, and are due to be checked or downloaded by hand.\n")
    for item, status in rows:
        print(f"- [ ] **{item['name']}** ({status}). {item['what']} [Link]({item['url']}). {item['when']}")
        print(f"  Used in: {item['used_in']}")
    print("\nWhen an item is done, set its `last_checked` date in `analysis/manual_sources.yml`. "
          "This issue is updated every Friday and closes once nothing is due.")


if __name__ == "__main__":
    main(sys.argv[1:])
