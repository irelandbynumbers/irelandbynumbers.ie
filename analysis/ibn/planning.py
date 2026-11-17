"""Planning applications that mention a data centre, from the Department of
Housing, Local Government and Heritage's national register of planning
applications (open data under CC BY 4.0).

The register is built from the planning returns that each council sends to the
Department. The matching applications are saved to
analysis/data/housing/planning_data_centres.csv. Pass refresh=True (or run
analysis/build.py --refresh) to fetch them again.

Only the planning authority, application number and dates, location,
description and decision are kept. Applicants' names are not saved.
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import date

import pandas as pd

API = ("https://services.arcgis.com/NzlPQPKn5QF9v2US/arcgis/rest/services/"
       "IrishPlanningApplications/FeatureServer/0/query")
PAGE = "https://data.gov.ie/dataset/planning-application-points"
CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "housing", "planning_data_centres.csv")
WHERE = ("UPPER(DevelopmentDescription) LIKE '%DATA CENTRE%' OR UPPER(DevelopmentDescription) LIKE '%DATA CENTER%' "
         "OR UPPER(DevelopmentDescription) LIKE '%DATA HALL%'")
FIELDS = ["PlanningAuthority", "ApplicationNumber", "ReceivedDate", "DecisionDate", "Decision", "ApplicationType",
          "DevelopmentAddress", "DevelopmentDescription", "ITMEasting", "ITMNorthing", "FloorArea"]
UA = {"User-Agent": "irelandbynumbers.ie data build"}


def _query(params):
    url = API + "?" + urllib.parse.urlencode(dict(params, f="json"))
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return json.loads(r.read())


def fetch(refresh=None):
    from . import cso   # follows the same --refresh switch as the CSO tables
    refresh = cso.REFRESH if refresh is None else refresh
    if refresh or not os.path.exists(CACHE):
        rows, offset = [], 0
        while True:
            d = _query(dict(where=WHERE, outFields=",".join(FIELDS), orderByFields="OBJECTID",
                            resultOffset=offset, resultRecordCount=2000))
            rows += [f["attributes"] for f in d["features"]]
            if not d.get("exceededTransferLimit"):
                break
            offset += len(d["features"])
        df = pd.DataFrame(rows, columns=FIELDS)
        for c in ("ReceivedDate", "DecisionDate"):
            df[c] = pd.to_datetime(df[c], unit="ms").dt.date
        df = df.drop_duplicates(["PlanningAuthority", "ApplicationNumber"]).sort_values(["PlanningAuthority", "ReceivedDate"])
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        df.to_csv(CACHE, index=False)
        with open(CACHE.replace(".csv", "_checked.txt"), "w") as f:
            f.write(date.today().isoformat() + "\n")
    return pd.read_csv(CACHE, parse_dates=["ReceivedDate", "DecisionDate"])


def county(authority):
    """The county a planning authority covers: 'South Dublin County Council' -> 'Dublin'."""
    a = authority.replace(" City and County Council", "").replace(" County Council", "").replace(" City Council", "")
    return {"South Dublin": "Dublin", "Fingal": "Dublin", "Dun Laoghaire Rathdown": "Dublin"}.get(a, a)
