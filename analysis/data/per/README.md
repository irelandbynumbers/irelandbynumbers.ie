# Department budgets

- `databank_expenditure.csv`: voted spending by Vote, programme and subhead from
  2015, € thousand, from the Department of Public Expenditure, Infrastructure,
  Public Service Reform and Digitalisation's Databank (CC BY 4.0). Fetched by
  `analysis/ibn/per.py`. Past years are outturn and the latest year is the
  allocation for that year.
- `appropriation_accounts_<year>.csv`: the estimate provision (planned) and
  outturn (spent) for every subhead in the audited Appropriation Accounts,
  € thousand, read from the Comptroller and Auditor General's PDF by
  `analysis/public-finances/appropriation_accounts.py`. `page` is the page of the
  combined PDF each figure was read from, so any figure can be checked by eye.
  Each Vote's subheads add up exactly to its gross expenditure in the account.
