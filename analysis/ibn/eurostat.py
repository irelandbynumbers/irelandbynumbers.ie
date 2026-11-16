"""Fetch datasets from Eurostat's dissemination API.

Works like ibn.cso: each selection is saved under analysis/data/eurostat/<name>.csv
the first time it is fetched, and fetched again only with refresh=True (or
analysis/build.py --refresh, which sets cso.REFRESH).

Eurostat data may be reused with acknowledgement of the source, under CC BY 4.0:
https://ec.europa.eu/eurostat/about-us/policies/copyright
"""
import itertools
import json
import os
import urllib.parse
import urllib.request
from datetime import date

import pandas as pd

from . import cso

API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{code}?{query}"
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "eurostat")
META = os.path.join(CACHE, "_dates.json")
_FETCHED = set()

# The EU 27 countries, by Eurostat's geo code (EL is Greece).
EU27 = ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "EL", "HU", "IE", "IT", "LV", "LT",
        "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"]
EU = "EU27_2020"
NAMES = {"EU27_2020": "EU average", "EL": "Greece", "CZ": "Czechia", "NL": "Netherlands", "DE": "Germany"}


def table_url(code):
    return f"https://ec.europa.eu/eurostat/databrowser/view/{code}/default/table?lang=en"


def fetch(code, name=None, refresh=None, **filters):
    """A Eurostat dataset as a long DataFrame: one column per dimension (its
    code), a `<dim>_label` column for each, `time` and `value`.

    `filters` select dimension values, for example geo=["IE", "EU27_2020"],
    unit="PC_ACT". `name` is the file the selection is saved as (default `code`).
    """
    refresh = cso.REFRESH if refresh is None else refresh
    name = name or code
    path = os.path.join(CACHE, f"{name}.csv")
    if (refresh and name not in _FETCHED) or not os.path.exists(path):
        query = urllib.parse.urlencode([(k, v) for k, vs in filters.items()
                                        for v in (vs if isinstance(vs, (list, tuple)) else [vs])] + [("lang", "en")])
        req = urllib.request.Request(API.format(code=code, query=query),
                                     headers={"User-Agent": "irelandbynumbers.ie data build"})
        with urllib.request.urlopen(req, timeout=180) as r:
            js = json.load(r)
        df = _to_frame(js)
        os.makedirs(CACHE, exist_ok=True)
        df.to_csv(path, index=False)
        _record_dates(name, code, js.get("updated", ""))
        _FETCHED.add(name)
    return pd.read_csv(path, low_memory=False, keep_default_na=False, na_values=[""])


def _to_frame(js):
    dims = js["id"]
    cats = []
    for d in dims:
        c = js["dimension"][d]["category"]
        order = sorted(c["index"], key=c["index"].get)
        cats.append([(k, c.get("label", {}).get(k, k)) for k in order])
    sizes = js["size"]
    values = js["value"]
    rows = []
    for i, combo in enumerate(itertools.product(*cats)):
        v = values.get(str(i)) if isinstance(values, dict) else values[i]
        if v is None:
            continue
        row = {}
        for d, (k, label) in zip(dims, combo):
            row[d] = k
            if d != "time":
                row[f"{d}_label"] = label
        row["value"] = v
        rows.append(row)
    assert len(list(itertools.product(*[range(s) for s in sizes]))) >= len(rows)
    df = pd.DataFrame(rows)
    return df.drop(columns=[c for c in ["freq", "freq_label"] if c in df.columns])


def dates(name):
    if not os.path.exists(META):
        return {}
    return json.load(open(META, encoding="utf-8")).get(name, {})


def _record_dates(name, code, updated):
    meta = json.load(open(META, encoding="utf-8")) if os.path.exists(META) else {}
    entry = meta.get(name, {})
    if updated:
        entry["updated"] = updated[:10]
    entry["checked"] = date.today().isoformat()
    meta[name] = entry
    with open(META, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(meta.items())), f, indent=1)
        f.write("\n")


def country(code):
    """A readable country name for a Eurostat geo code."""
    return NAMES.get(code)
