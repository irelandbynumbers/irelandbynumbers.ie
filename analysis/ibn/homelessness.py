"""Monthly homelessness figures from the Department of Housing, Local
Government and Heritage, published as one CSV per month on data.gov.ie.

The monthly files are combined into analysis/data/housing/homelessness.csv,
one row per region and month. Pass refresh=True to look for new months.
"""
import io
import json
import os
import re
import urllib.request
from datetime import date

import pandas as pd

SEARCH = "https://data.gov.ie/api/3/action/package_search?q=name:{q}*&rows=100&start={start}"
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "housing", "homelessness.csv")
PAGE = "https://data.gov.ie/organization/department-of-housing-local-government-and-heritage"
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
UA = {"User-Agent": "irelandbynumbers.ie data build"}


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def _reports():
    """{(year, month): csv url} for every monthly report listed on data.gov.ie."""
    found = {}
    for q in ("homelessness-report", "homlessness-report"):   # some months are published with this spelling
        for start in (0, 100, 200):
            res = json.loads(_get(SEARCH.format(q=q, start=start)))["result"]["results"]
            for p in res:
                m = re.fullmatch(r"hom(?:e)?lessness-report-([a-z]+)-(\d{4})", p["name"])
                csv = [r["url"] for r in p["resources"] if r["url"].lower().endswith(".csv")]
                if m and m.group(1) in MONTHS and csv:
                    found[(int(m.group(2)), MONTHS.index(m.group(1)) + 1)] = csv[0]
    return found


def fetch(refresh=None):
    from . import cso   # follows the same --refresh switch as the CSO tables
    refresh = cso.REFRESH if refresh is None else refresh
    if refresh or not os.path.exists(CACHE):
        frames = []
        for (year, month), url in sorted(_reports().items()):
            df = pd.read_csv(io.BytesIO(_get(url)), thousands=",")
            df.columns = [c.strip() for c in df.columns]
            # One month names the column "Number of Child Dependants in Families".
            df = df.rename(columns={"Number of Child Dependants in Families": "Number of Dependants in Families"})
            df = df[df.Region.notna() & (df.Region.str.strip().str.lower() != "total")]
            df.insert(0, "month", f"{year}-{month:02d}")
            frames.append(df)
        out = pd.concat(frames, ignore_index=True)
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        out.to_csv(CACHE, index=False)
        with open(CACHE.replace(".csv", "_checked.txt"), "w") as f:
            f.write(date.today().isoformat() + "\n")
    return pd.read_csv(CACHE)
