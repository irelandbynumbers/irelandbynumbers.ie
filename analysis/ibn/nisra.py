"""Fetch tables from the Northern Ireland Statistics and Research Agency's
(NISRA) data portal, which runs the same PxStat software as the CSO.

Every table is saved under analysis/data/nisra/<CODE>.csv the first time it is
fetched, so the site builds from a fixed copy and every change to the data
shows up in the repository's history. Pass refresh=True (or run
analysis/build.py --refresh) to fetch the latest release again.

NISRA data is published under the Open Government Licence v3.0:
https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
"""
import io
import json
import os
import urllib.request
from datetime import date

import pandas as pd

API = "https://ws-data.nisra.gov.uk/public/api.restful/PxStat.Data.Cube_API.ReadDataset/{code}/CSV/1.0/en"
META_API = "https://ws-data.nisra.gov.uk/public/api.restful/PxStat.Data.Cube_API.ReadMetadata/{code}/JSON-stat/2.0/en"
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "nisra")
# When each saved table was last updated by NISRA, and when it was last
# fetched here: {"PEA01": {"updated": "2026-08-24", "checked": "2026-11-13"}}.
META = os.path.join(CACHE, "_dates.json")
from . import cso   # shares the --refresh setting
_FETCHED = set()   # tables already fetched in this run, so a refresh downloads each once


def table_url(code):
    """The table's page on data.nisra.gov.uk, for people to follow from a chart."""
    return f"https://data.nisra.gov.uk/table/{code}"


def fetch(code, refresh=None, where=None):
    """A NISRA table as a DataFrame, with the label columns PxStat gives each dimension.

    PxStat's CSV has a code column and a label column for each dimension (for
    example "C02199V02655" and "Sex"); this keeps the labels, the unit and the value.

    `where` keeps only some rows of a large table before it is saved, as a dict
    of column label to the values to keep, for example
    {"Statistic Label": ["Consumer Price Index"], "Detailed Sub Indices": ["All Items"]}.
    Change it and run with refresh=True to save the new selection.
    """
    refresh = cso.REFRESH if refresh is None else refresh
    path = os.path.join(CACHE, f"{code}.csv")
    if (refresh and code not in _FETCHED) or not os.path.exists(path):
        req = urllib.request.Request(API.format(code=code), headers={"User-Agent": "irelandbynumbers.ie data build"})
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read()
        df = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig", low_memory=False)
        for col, values in (where or {}).items():
            df = df[df[col].isin(values)]
        os.makedirs(CACHE, exist_ok=True)
        df.to_csv(path, index=False)
        _record_dates(code)
        _FETCHED.add(code)
    df = pd.read_csv(path, low_memory=False)
    keep = [c for c in df.columns if not _is_code_column(c)]
    return df[keep]


def dates(code):
    """When NISRA last updated a table, and when it was last fetched, as
    ISO dates in a dict ({} if not recorded)."""
    if not os.path.exists(META):
        return {}
    return json.load(open(META, encoding="utf-8")).get(code, {})


def _record_dates(code):
    meta = json.load(open(META, encoding="utf-8")) if os.path.exists(META) else {}
    entry = meta.get(code, {})
    try:
        req = urllib.request.Request(META_API.format(code=code), headers={"User-Agent": "irelandbynumbers.ie data build"})
        with urllib.request.urlopen(req, timeout=60) as r:
            updated = json.load(r).get("updated", "")
        if updated:
            entry["updated"] = updated[:10]
    except OSError as e:  # the dates are useful but not essential, so carry on
        print(f"could not read NISRA's update date for {code}: {e}")
    entry["checked"] = date.today().isoformat()
    meta[code] = entry
    with open(META, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(meta.items())), f, indent=1)
        f.write("\n")


def _is_code_column(col):
    # Dimension code columns look like "C02199V02655", "TLIST(A1)" or "STATISTIC".
    return col == "STATISTIC" or col.startswith("TLIST(") or (col[:1] == "C" and "V" in col and col[1:2].isdigit())
