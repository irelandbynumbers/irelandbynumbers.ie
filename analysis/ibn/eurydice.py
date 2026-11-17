"""Tables from Eurydice's Key data on early childhood education and care in
Europe 2025, from the open data workbook published with the report.

The workbook is saved to analysis/data/eurydice/kd_ecec_2025.xlsx the first
time it is used. Eurydice is part of the European Commission's Education,
Audiovisual and Culture Executive Agency, and its publications may be reused
with acknowledgement under the Commission's reuse policy (CC BY 4.0).
"""
import os
import urllib.request

import pandas as pd

WORKBOOK = "https://eurydice.eacea.ec.europa.eu/sites/default/files/2025-01/Open_Data_KD_ECEC_2025_0.xlsx"
PAGE = "https://eurydice.eacea.ec.europa.eu/publications/key-data-early-childhood-education-and-care-europe-2025"
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "eurydice", "kd_ecec_2025.xlsx")
UA = {"User-Agent": "irelandbynumbers.ie data build"}


def _workbook(refresh=None):
    from . import cso   # follows the same --refresh switch as the CSO tables
    refresh = cso.REFRESH if refresh is None else refresh
    if refresh or not os.path.exists(CACHE):
        with urllib.request.urlopen(urllib.request.Request(WORKBOOK, headers=UA), timeout=180) as r:
            raw = r.read()
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, "wb") as f:
            f.write(raw)
    return CACHE


def table(sheet, columns):
    """The country rows of one sheet, with the given column names for the
    value columns (left to right, after the country). Rows start at the first
    country (Belgium's French Community, or the EU-27 where a sheet has one)
    and stop at the first blank country. Belgium's three communities are kept
    as given."""
    raw = pd.read_excel(_workbook(), sheet_name=sheet, header=None)
    first = raw.index[raw[0].isin(["EU-27", "Belgium (French Community)", "Belgium"])][0]
    rows = []
    for r in raw.loc[first:].itertuples(index=False):
        name = r[0]
        if not isinstance(name, str) or not name.strip() or name.strip() in ("x", "Explanatory notes:", "Explanatory note:"):
            break
        rows.append([name.strip(), *list(r[1:1 + len(columns)])])
    return pd.DataFrame(rows, columns=["country", *columns])


def source(title):
    from .chart import Source
    return Source("Eurydice (European Commission)", f"Key data on early childhood education and care in Europe 2025, {title}",
                  PAGE)
