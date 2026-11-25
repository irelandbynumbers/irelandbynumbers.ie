"""The HSE's daily TrolleyGAR count of patients on trolleys at 8am.

The HSE page shows only the current day, with no history to download, so a
small GitHub Actions job (.github/workflows/trolleys.yml) saves each morning's
reading to analysis/data/hse/trolleygar.csv (national totals) and
trolleygar_hospitals.csv (by hospital). The CSO publishes the same daily
national count (table KTA02), but months later.

Each row records the date it was fetched and the weekday the page names
(`page_day`). The page gives no date, so charts use only rows where the two
agree.
"""
import datetime
import html
import os
import re
import urllib.request

import pandas as pd

PAGE = "https://uec.hse.ie/uec/TGAR.php"
DIR = os.path.join(os.path.dirname(__file__), "..", "data", "hse")
NATIONAL = os.path.join(DIR, "trolleygar.csv")
HOSPITALS = os.path.join(DIR, "trolleygar_hospitals.csv")
UA = {"User-Agent": "irelandbynumbers.ie data build"}


def _int(v):
    return int(v) if re.fullmatch(r"\d+", v or "") else None


def parse(page, today):
    """National and hospital counts from the page, dated `today`, or None if
    the page has no national total."""
    day = re.search(r"08:00\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)", page)
    page_day = day.group(1) if day else ""
    national, hospitals, region = None, [], None
    # The page's HTML leaves out some <tr> tags, so walk the cells in order:
    # a region heading, then each hospital's name cell followed by a spacer
    # cell and the ED, ward and total counts.
    cells = re.findall(r"<t[dh]([^>]*)>(.*?)</t[dh]>", page, flags=re.S)
    text = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for _, c in cells]
    for i, (attrs, raw) in enumerate(cells):
        if "hse-heading-xs" in raw and text[i].startswith("HSE "):
            region = text[i]
        elif text[i] == "National Total":
            n = [_int(v) for v in text[i + 1:i + 8] if v != ""]
            national = dict(date=today.isoformat(), page_day=page_day, ed_trolleys=n[0], ward_trolleys=n[1],
                            total=n[2])
        elif "padding-left:0.5ex" in raw and text[i]:
            v = text[i + 2:i + 5]
            hospitals.append(dict(date=today.isoformat(), region=region, hospital=text[i], ed_trolleys=_int(v[0]),
                                  ward_trolleys=_int(v[1]), total=_int(v[2])))
    if not national:
        return None
    return national, hospitals


def _append(path, rows):
    new = pd.DataFrame(rows)
    for c in ["ed_trolleys", "ward_trolleys", "total"]:
        new[c] = new[c].astype("Int64")
    if os.path.exists(path):
        old = pd.read_csv(path)
        new = pd.concat([old[~old.date.isin(new.date)], new])
    new.sort_values([c for c in ["date", "region", "hospital"] if c in new.columns]).to_csv(path, index=False)


def save_today(today=None):
    """Fetch the page and save today's reading. Returns True if saved."""
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    with urllib.request.urlopen(urllib.request.Request(PAGE, headers=UA), timeout=60) as r:
        page = r.read().decode("utf-8", errors="replace")
    got = parse(page, today)
    if not got:
        print("TrolleyGAR: no national total found on the page, nothing saved")
        return False
    os.makedirs(DIR, exist_ok=True)
    _append(NATIONAL, [got[0]])
    if got[1]:
        _append(HOSPITALS, got[1])
    print(f"TrolleyGAR: saved {today} (page says {got[0]['page_day'] or 'no day'}), "
          f"{got[0]['ed_trolleys']} on trolleys in emergency departments")
    return True


def fetch():
    """Saved national readings whose page weekday matches their date: date,
    ed_trolleys, ward_trolleys, total."""
    cols = ["date", "ed_trolleys", "ward_trolleys", "total"]
    if not os.path.exists(NATIONAL):
        return pd.DataFrame(columns=cols)
    d = pd.read_csv(NATIONAL, parse_dates=["date"])
    return d[d.page_day == d.date.dt.strftime("%A")][cols].reset_index(drop=True)


if __name__ == "__main__":
    save_today()
