"""Turn the area names CSO tables use into the 26 counties on the map.

Many tables list local authorities rather than counties: Dublin as four
councils, and Cork and Galway as a city and a county council. `county()`
maps each of these to its county, so counts can be added up by county.
"""
import re

COUNCILS = {
    "Dublin City": "Dublin", "Dún Laoghaire Rathdown": "Dublin", "Dún Laoghaire-Rathdown": "Dublin",
    "Fingal": "Dublin", "South Dublin": "Dublin",
    "Cork City": "Cork", "Cork County": "Cork",
    "Galway City": "Galway", "Galway County": "Galway",
    "Limerick City": "Limerick", "Limerick County": "Limerick", "Limerick City & County": "Limerick",
    "Waterford City": "Waterford", "Waterford County": "Waterford", "Waterford City & County": "Waterford",
}


def county(name):
    """The county an area belongs to, or None for the State or a region."""
    n = re.sub(r"\s+", " ", str(name)).strip()
    n = re.sub(r"^Co\. ", "", n)
    n = re.sub(r" Council$", "", n)
    if n in COUNCILS:
        return COUNCILS[n]
    n = re.sub(r" (County|City)$", "", n)
    if n in COUNCILS:
        return COUNCILS[n]
    from .figures import COUNTIES
    return n if n in COUNTIES else None


def add_up(df, area_col, value_cols, by=()):
    """Sum `value_cols` by county (and any `by` columns), dropping areas that are not a county."""
    d = df.copy()
    d["county"] = d[area_col].map(county)
    d = d.dropna(subset=["county"])
    out = d.groupby([*by, "county"], as_index=False)[list(value_cols)].sum()
    from .figures import COUNTIES
    missing = set(COUNTIES) - set(out.county)
    assert not missing, f"no figures for {sorted(missing)}"
    return out


SUMMED_NOTE = ("Figures for Dublin add together its four council areas, and figures for Cork and Galway add together "
               "their city and county council areas, to match the county map.")
