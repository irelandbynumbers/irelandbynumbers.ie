"""Voter turnout from International IDEA's Voter Turnout Database.

The whole database is downloaded as one Excel file and saved to
analysis/data/idea/voter_turnout.csv. Pass refresh=True (or run
analysis/build.py --refresh) to fetch it again.

The database is published by International IDEA under the Creative Commons
Attribution-NonCommercial-ShareAlike 3.0 licence (CC BY-NC-SA 3.0), so charts
built from it carry that licence.
"""
import io
import os
import urllib.request

import pandas as pd

EXPORT = "https://www.idea.int/data-tools/export?type=region_only&themeId=293&world=all&loc=home"
PAGE = "https://www.idea.int/data-tools/data/voter-turnout-database"
LICENCE = ("CC BY-NC-SA 3.0", "https://creativecommons.org/licenses/by-nc-sa/3.0/")
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "idea", "voter_turnout.csv")
UA = {"User-Agent": "irelandbynumbers.ie data build"}


def _pct(s):
    return pd.to_numeric(s.astype(str).str.replace("%", "", regex=False).str.strip(), errors="coerce")


def _num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce")


def fetch(refresh=None):
    """Every election in the database: country, iso2, election_type, date,
    year, turnout (votes as a share of registered voters, %), vap_turnout
    (votes as a share of the voting-age population, %), total_vote,
    registration and compulsory_voting (Yes or No)."""
    from . import cso   # follows the same --refresh switch as the CSO tables
    refresh = cso.REFRESH if refresh is None else refresh
    if refresh or not os.path.exists(CACHE):
        with urllib.request.urlopen(urllib.request.Request(EXPORT, headers=UA), timeout=180) as r:
            raw = r.read()
        df = pd.read_excel(io.BytesIO(raw), sheet_name="All")
        out = pd.DataFrame({
            "country": df.Country, "iso2": df.ISO2, "election_type": df["Election Type"],
            "date": pd.to_datetime(df.Year, errors="coerce").dt.date,
            "turnout": _pct(df["Voter Turnout"]), "vap_turnout": _pct(df["VAP Turnout"]),
            "total_vote": _num(df["Total vote"]), "registration": _num(df.Registration),
            "compulsory_voting": df["Compulsory voting"]})
        out["year"] = pd.to_datetime(out.date).dt.year
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        out.to_csv(CACHE, index=False)
    return pd.read_csv(CACHE)


def source():
    from .chart import Source
    return Source("International IDEA", "Voter Turnout Database", PAGE, licence=LICENCE[0], licence_url=LICENCE[1])
