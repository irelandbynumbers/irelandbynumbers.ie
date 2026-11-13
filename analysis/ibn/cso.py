"""Fetch tables from the Central Statistics Office's PxStat service.

Every table is saved under analysis/data/cso/<CODE>.csv the first time it is
fetched, so the site builds from a fixed copy and every change to the data
shows up in the repository's history. Pass refresh=True (or run
analysis/build.py --refresh) to fetch the latest release again.

CSO data is published under CC BY 4.0: https://www.cso.ie/en/aboutus/lgdp/csodatapolicies/
"""
import io
import os
import urllib.request

import pandas as pd

API = "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/{code}/CSV/1.0/en"
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "cso")
REFRESH = False


def table_url(code):
    """The table's page on data.cso.ie, for people to follow from a chart."""
    return f"https://data.cso.ie/table/{code}"


def fetch(code, refresh=None):
    """A CSO table as a DataFrame, with the label columns PxStat gives each dimension.

    PxStat's CSV has a code column and a label column for each dimension (for
    example "C02199V02655" and "Sex"); this keeps the labels, the unit and the value.
    """
    refresh = REFRESH if refresh is None else refresh
    path = os.path.join(CACHE, f"{code}.csv")
    if refresh or not os.path.exists(path):
        req = urllib.request.Request(API.format(code=code), headers={"User-Agent": "irelandbynumbers.ie data build"})
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read()
        df = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")
        os.makedirs(CACHE, exist_ok=True)
        df.to_csv(path, index=False)
    df = pd.read_csv(path)
    keep = [c for c in df.columns if not _is_code_column(c)]
    return df[keep]


def _is_code_column(col):
    # Dimension code columns look like "C02199V02655", "TLIST(A1)" or "STATISTIC".
    return col == "STATISTIC" or col.startswith("TLIST(") or (col[:1] == "C" and "V" in col and col[1:2].isdigit())
