"""Department budgets from the Department of Public Expenditure's Databank, and
the audited Appropriation Accounts.

The Databank (databank.per.gov.ie) publishes voted spending for every Vote,
programme and subhead each year since 1994, as one open data file. For past
years the figures are the outturn, and for the current year they are the
allocation in the Revised Estimates. It is published under CC BY 4.0 and is
also listed on data.gov.ie. Rows from 2015 on are saved to
analysis/data/per/databank_expenditure.csv. Pass refresh=True (or run
analysis/build.py --refresh) to fetch it again.

The Databank's web server sends its security certificate without the
intermediate certificate that links it to a trusted root, so a download that
checks certificates properly fails. The missing GoDaddy intermediate is kept in
certs/ and added to the trusted roots for this one download. It is checked
against the root like any other certificate, so verification stays on.

The Appropriation Accounts are read once a year from the Comptroller and
Auditor General's PDF by analysis/public-finances/appropriation_accounts.py.
"""
import io
import json
import os
import ssl
import urllib.request
from datetime import date

import pandas as pd

DATABANK = "https://databank.per.gov.ie/Expenditure.aspx?rep=OpenDataSourceCSV"
DATABANK_PAGE = "https://data.gov.ie/dataset/voted-public-expenditure"
ACCOUNTS_PAGE = "https://www.audit.gov.ie/en/publications/appropriation-accounts/appropriation-accounts-{year}/"
HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "..", "data", "per")
META = os.path.join(CACHE, "_dates.json")
INTERMEDIATE = os.path.join(HERE, "certs", "godaddy-g2-intermediate.pem")
FIRST_YEAR = 2015


def _context():
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(INTERMEDIATE)
    return ctx


def databank(refresh=None):
    """Voted spending by Vote, programme and subhead, € thousand. Columns: year,
    vote (as numbered that year in the Databank), vote_name, level_2 to level_5
    (the Databank's levels below the Vote), type ("Program" for spending,
    "A In A" for appropriations-in-aid) and value."""
    from . import cso   # follows the same --refresh switch as the CSO tables
    refresh = cso.REFRESH if refresh is None else refresh
    path = os.path.join(CACHE, "databank_expenditure.csv")
    if refresh or not os.path.exists(path):
        try:
            req = urllib.request.Request(DATABANK, headers={"User-Agent": "irelandbynumbers.ie data build"})
            with urllib.request.urlopen(req, timeout=300, context=_context()) as r:
                raw = r.read()
            df = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig", dtype=str)
            df = df[pd.to_numeric(df.Year) >= FIRST_YEAR]
            value = pd.to_numeric(df.Amount_Value.str.replace(",", "").str.replace(r"^\((.*)\)$", r"-\1", regex=True))
            out = pd.DataFrame({
                "year": df.Year.astype(int),
                "vote": df.Level_1.str.extract(r"^V(\d+[a-z]?) ")[0],
                "vote_name": df.Level_1.str.replace(r"^V\d+[a-z]? - ", "", regex=True).str.replace(r"\s*\(Net\)\s*$", "", regex=True).str.strip(),
                **{f"level_{i}": df[f"Level_{i}"].str.strip() for i in range(2, 6)},
                "type": df.Type.str.replace("A IN A", "A In A"), "value": value})
            os.makedirs(CACHE, exist_ok=True)
            out.to_csv(path, index=False)
            _record("databank")
        except OSError as e:
            if not os.path.exists(path):
                raise
            print(f"could not fetch the Databank, so using the saved copy: {e}")
    return pd.read_csv(path, dtype={"vote": str})


def accounts(year):
    """Estimate provision and outturn for every subhead in the Appropriation Accounts, € thousand."""
    return pd.read_csv(os.path.join(CACHE, f"appropriation_accounts_{year}.csv"))


def dates(key):
    if not os.path.exists(META):
        return {}
    return json.load(open(META, encoding="utf-8")).get(key, {})


def _record(key):
    meta = json.load(open(META, encoding="utf-8")) if os.path.exists(META) else {}
    meta.setdefault(key, {})["checked"] = date.today().isoformat()
    with open(META, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(meta.items())), f, indent=1)
        f.write("\n")


def databank_source():
    from .chart import Source
    return Source("Department of Public Expenditure, Infrastructure, Public Service Reform and Digitalisation",
                  "Databank, voted public expenditure", DATABANK_PAGE, code="databank")


def accounts_source(year):
    from .chart import Source
    return Source("Comptroller and Auditor General", f"Appropriation Accounts {year}", ACCOUNTS_PAGE.format(year=year),
                  licence="Public sector information", licence_url="", code=f"accounts-{year}")
