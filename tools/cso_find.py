"""Find CSO tables by keyword, or list what is inside a table.

Almost all CSO statistics are published as PxStat tables (data.cso.ie). This
searches the catalogue of current tables by title, and describes a table's
dimensions, so you can choose the code to use in a chart script.

Usage:
    python3 tools/cso_find.py search "dwelling completions" "consumer price"
    python3 tools/cso_find.py describe PEA01
"""
import io
import json
import sys
import urllib.request

import pandas as pd

API = "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "irelandbynumbers.ie data build"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def catalogue():
    items = json.loads(get(f"{API}.ReadCollection")).get("link", {}).get("item", [])
    return pd.DataFrame([{"code": it.get("extension", {}).get("matrix"), "title": it.get("label", ""),
                          "updated": it.get("updated", "")} for it in items])


def search(terms):
    cat = catalogue()
    for term in terms:
        words = term.lower().split()
        hit = cat[cat["title"].str.lower().apply(lambda t: all(w in t for w in words))]
        print(f"\n## {term} ({len(hit)} tables)")
        for _, r in hit.iterrows():
            print(f"{r['code']:10} {r['title']}  (updated {str(r['updated'])[:10]})")


def describe(codes):
    for code in codes:
        df = pd.read_csv(io.BytesIO(get(f"{API}.ReadDataset/{code}/CSV/1.0/en")), encoding="utf-8-sig")
        print(f"\n## {code}, {len(df):,} rows")
        for c in df.columns:
            if c == "VALUE":
                continue
            vals = df[c].dropna().unique()
            more = f" ... and {len(vals) - 20} more" if len(vals) > 20 else ""
            print(f"  {c} ({len(vals)} values): {list(vals[:20])}{more}")


if __name__ == "__main__":
    {"search": search, "describe": describe}[sys.argv[1]](sys.argv[2:])
