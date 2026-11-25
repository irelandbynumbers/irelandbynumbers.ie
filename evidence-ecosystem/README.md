# Evidence-policy ecosystem map

The page `index.qmd` draws an interactive network from the CSV files in this folder. Nothing needs to be rebuilt when the data changes; the page reads the files when it loads.

- `nodes.csv` lists every organisation and group. `role` is `hub` for a group circle, `member` for an organisation that sits on a group's ring (its `cluster` names the hub), or `node` for an organisation that stands on its own. `group` sets the colour and must be one of the keys in `GROUPS` in `ecosystem.js`. `description` is optional text shown in the details panel.
- `links.csv` lists the links. `type` is `funding`, `demand`, `supply` or `synthesis`. Set `both_ways` to `yes` for a link with arrows at both ends.
- `layout.csv` gives the position of each hub and stand-alone node on a 1300 by 1110 canvas, the radius of each hub's ring, and where its label sits (`above`, `below`, `left` or `right`). Members are spread evenly around their hub automatically.
- `stats.csv` holds figures to attach to any organisation or group. Each row has a `node_id` from `nodes.csv`, a `label`, a `value`, an optional `unit` and `year`, and a source. All rows for an organisation appear under "Figures" when it is selected.

`nodes.csv` and `links.csv` were exported from the Participatory System Mapper room for this map. PRSM's four link styles map to `funding`, `demand`, `supply` and `synthesis`, and pairs of links running both ways between the same two nodes are stored once with `both_ways` set to `yes`. Members are placed in the same order around each ring as in PRSM.
