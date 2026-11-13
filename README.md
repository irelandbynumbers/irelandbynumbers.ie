# Ireland by Numbers

Source for [irelandbynumbers.ie](https://irelandbynumbers.ie): Irish statistics, from open data.

Built with [Quarto](https://quarto.org). Every push to `main` builds the site and publishes it to the `gh-pages` branch, and every pull request is checked to make sure the site still builds. Preview locally with `quarto preview`.

## Layout

- `*.qmd`: the pages. A project goes in its own folder (for example `housing/index.qmd`); add the folder to `render:` in `_quarto.yml` and to the navbar.
- `figures/`: interactive figures the pages embed, as standalone HTML. For Plotly figures, run `python3 -I tools/slim_plotly.py figures/*.html` after adding one, so they share one copy of plotly.js in `figures/lib/`.
- `analysis/`: one folder per project, with the code and data behind its figures.
- `styles.css`: project tiles, headline number cards, text cards and a timeline, shared with [Fianaise](https://github.com/fianaise/fianaise.ie).

## Domains

`CNAME` points GitHub Pages at irelandbynumbers.ie. irelandbynumbers.org forwards to it from a separate repository, `irelandbynumbers/irelandbynumbers.org`, that holds only a redirect page (the same setup as fianaise.org).

DNS for irelandbynumbers.ie: four A records for `@` pointing to 185.199.108.153, 185.199.109.153, 185.199.110.153 and 185.199.111.153, and a CNAME for `www` pointing to irelandbynumbers.github.io.

Text and figures are CC BY 4.0. Code is MIT licensed (see `LICENSE-code`).
