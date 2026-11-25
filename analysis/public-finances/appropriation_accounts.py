"""Read planned and actual spending for every subhead from the Appropriation Accounts.

The Comptroller and Auditor General publishes the audited Appropriation Accounts
each autumn, as one PDF for all Votes. Each account compares the amount the Dáil
provided for each subhead (the estimate provision, including any supplementary
estimate) with what was actually spent (the outturn). This script reads those
tables and saves them to analysis/data/per/appropriation_accounts_<year>.csv,
which the public finances charts read. It is run by hand once a year, when the
new accounts are out, because it needs pdfplumber, which the site build does not:

    pip install pdfplumber
    python3 analysis/public-finances/appropriation_accounts.py 2025 <url of the combined PDF>

The combined PDF is listed on https://www.audit.gov.ie/en/publications/appropriation-accounts/.
Every Vote's subheads must add up to the gross expenditure printed in its
account, or the script stops, so a change in the layout cannot slip through.
"""
import os
import re
import sys
import tempfile
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "per")
NUM = r"(?:\(?\d[\d,]*\)?|—|–)"
THREE = re.compile(rf"^(.*?)\s*({NUM})\s+({NUM})\s+({NUM})(?:\s+[a-z])?$")
TWO = re.compile(rf"^(.*?)\s*({NUM})\s+({NUM})()(?:\s+[a-z])?$")   # a new Vote, with no figures for the year before
CODE = re.compile(r"^([A-Z](?:\.(?:\d+|[a-z]{1,3}))?)\s+(.*)$")
SKIP = re.compile(r"^((Original|Supplementary|Deferred surrender|Virement|Further revised|Revised) \(?[\d,]+\)?$|"
                  r"Estimate|€000|Service\b|provision|\d{4}( \d{4})?$)")
STOP = re.compile(r"^(Significant variations|Note |Deduct|Net expenditure|Surplus|Expenditure variances|Programme [A-Z]\b)")


def _num(s):
    if s in ("—", "–", ""):
        return 0
    v = int(s.strip("()").replace(",", ""))
    return -v if s.startswith("(") else v


def _lines(pdf_path):
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return [[(l["x0"], l["text"].strip()) for l in page.extract_text_lines() if l["text"].strip()] for page in pdf.pages]


def _parse_vote(pages, row):
    """Subheads and the gross expenditure line of one Vote, from its pages of (x, text) lines."""
    subs, gross, group, code_x = [], None, "", None
    for n, lines in pages:
        texts = [t for _, t in lines]
        if not any(t.startswith("Estimate") for t in texts[:8]) and not any(t.startswith("Programme ") for t in texts[:4]):
            continue
        cur, last = None, None   # a subhead waiting for its figures; the subhead just completed
        prev_heading = False
        for k, (x, t) in enumerate(lines):
            if t.startswith("Gross expenditure") and gross is None:
                for t2 in [t] + texts[k + 1:k + 6]:
                    m = row.match(t2)
                    if m and m.group(1) in ("", "Gross expenditure"):
                        gross = (_num(m.group(2)), _num(m.group(3)))
                        break
                cur = last = None
                continue
            if STOP.match(t):
                cur = last = None
                continue
            m = CODE.match(t)
            if m and not SKIP.match(t):
                code_x, prev_heading = x, False
                mt = row.match(m.group(2))
                if mt and mt.group(1) and cur is not None:
                    # These figures close the subhead above, whose estimate was broken down over several lines.
                    cur.update(estimate=_num(mt.group(2)), outturn=_num(mt.group(3)))
                    subs.append(cur)
                    cur, last = dict(code=m.group(1), name=mt.group(1), page=n, x=x, group=group), None
                elif mt and mt.group(1):
                    last = dict(code=m.group(1), name=mt.group(1), estimate=_num(mt.group(2)), outturn=_num(mt.group(3)),
                                page=n, x=x, group=group)
                    subs.append(last)
                    cur = None
                else:
                    cur, last = dict(code=m.group(1), name=m.group(2), page=n, x=x, group=group), None
                continue
            if SKIP.match(t):
                continue
            mt = row.match(t)
            if mt and not mt.group(1) and cur is not None:
                cur.update(estimate=_num(mt.group(2)), outturn=_num(mt.group(3)))
                subs.append(cur)
                cur, last = None, cur
                continue
            if mt and cur is not None and x > cur["x"] + 15:
                # The end of a long name, with the figures on the same line.
                cur.update(name=cur["name"] + " " + mt.group(1), estimate=_num(mt.group(2)), outturn=_num(mt.group(3)))
                subs.append(cur)
                cur, last = None, cur
                continue
            if mt:
                cur = last = None
                continue
            # A name that runs onto the next line is indented further than the subhead code.
            target = cur or last
            if target is not None and x > target["x"] + 15:
                target["name"] += " " + t
                continue
            cur = last = None
            # A heading over a group of subheads starts where the codes do.
            if code_x is not None and abs(x - code_x) < 4 and not re.search(r"\d", t):
                group = (group + " " + t) if prev_heading else t
                prev_heading = True
                continue
            prev_heading = False
    return subs, gross


def _clean(subs):
    """Keep one row per subhead. Single letters are programme totals when the programme has
    lettered subheads (A.1, A.2), and subheads under the appropriations-in-aid letter are receipts."""
    lettered = {s["code"].split(".")[0] for s in subs if "." in s["code"]}
    named = {s["code"] for s in subs if "." not in s["code"] and "ppropriations-in-aid" not in s["name"]}
    aia = {s["code"] for s in subs if "." not in s["code"] and "ppropriations-in-aid" in s["name"]} - named
    programmes = {}
    keep = {}
    for s in subs:
        c = s["code"]
        if "." not in c and c in lettered:
            programmes.setdefault(c, s["name"])
            continue
        if c.split(".")[0] in aia or "ppropriations-in-aid" in s["name"]:
            continue
        # A subhead can appear twice, for example in a note on lottery funding. Keep the full line.
        if c not in keep or abs(s["estimate"]) + abs(s["outturn"]) > abs(keep[c]["estimate"]) + abs(keep[c]["outturn"]):
            keep[c] = s
    return list(keep.values()), programmes


def _tidy(name):
    name = re.sub(r"\s+", " ", name).replace(" (continued)", "").strip()
    name = re.sub(r"(\w)- (\w)", lambda m: m.group(1) + ("-" if m.group(2).isupper() else "") + m.group(2), name)
    name = re.sub(r"\s+[a-c]$", "", name)          # footnote letters
    return name.replace(" ,", ",")


def parse(pdf_path, year):
    pages = _lines(pdf_path)
    starts = [(i, int(p[1][1].split()[1]), " ".join(t for _, t in p[2:]))
              for i, p in enumerate(pages)
              if len(p) >= 3 and p[0][1] == f"Appropriation Account {year}" and re.fullmatch(r"Vote \d+", p[1][1]) and len(p) <= 6]
    rows, problems = [], []
    for (a, vote, vname), (b, _, _) in zip(starts, starts[1:] + [(len(pages), None, None)]):
        chunk = [(n + 1, pages[n]) for n in range(a, b)]
        subs, gross = _parse_vote(chunk, THREE)
        if gross is None:
            subs, gross = _parse_vote(chunk, TWO)
        subs, programmes = _clean(subs)
        est, out = sum(s["estimate"] for s in subs), sum(s["outturn"] for s in subs)
        if gross != (est, out):
            problems.append(f"Vote {vote} {vname}: subheads add up to {est:,} and {out:,}, account says {gross}")
        for s in subs:
            letter = s["code"].split(".")[0]
            rows.append(dict(year=year, vote=vote, vote_name=vname, programme=letter if programmes else "",
                             programme_name=_tidy(programmes.get(letter, "") if programmes
                                                    else s.get("group") or ("Administration" if s["code"].startswith("A.") else "")), subhead=s["code"], subhead_name=_tidy(s["name"]),
                             estimate_thousand=s["estimate"], outturn_thousand=s["outturn"], page=s["page"]))
    if problems:
        raise SystemExit("These Votes do not add up, so the layout needs checking:\n" + "\n".join(problems))
    return pd.DataFrame(rows)


def main(argv):
    year, url = int(argv[0]), argv[1]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "accounts.pdf")
        req = urllib.request.Request(url, headers={"User-Agent": "irelandbynumbers.ie data build"})
        with urllib.request.urlopen(req, timeout=600) as r, open(path, "wb") as f:
            f.write(r.read())
        df = parse(path, year)
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, f"appropriation_accounts_{year}.csv")
    df.to_csv(out, index=False)
    print(f"wrote {out}: {len(df)} subheads in {df.vote.nunique()} Votes, "
          f"€{df.outturn_thousand.sum() / 1e6:.1f} billion spent of €{df.estimate_thousand.sum() / 1e6:.1f} billion provided")


if __name__ == "__main__":
    main(sys.argv[1:])
