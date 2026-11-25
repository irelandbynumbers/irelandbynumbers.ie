# HSE TrolleyGAR daily counts

Saved each morning by `.github/workflows/trolleys.yml` from the HSE's
TrolleyGAR page (https://uec.hse.ie/uec/TGAR.php), which shows only the
current day. Started on 25 November 2026.

- `trolleygar.csv`: national totals. `date` is the day the page was saved;
  `page_day` is the weekday the page names. The page gives no date, so charts
  use only rows where the two agree.
- `trolleygar_hospitals.csv`: the same counts by hospital.

`ed_trolleys` is admitted patients waiting on trolleys in emergency
departments at 8am, the same measure as CSO table KTA02.
