# Looker Studio setup

This is the second half of the pre/post dashboard, alongside `explorer.html`
(the interactive Leaflet map). Looker Studio is the report others — the
professor, other practitioners — can open and drive without needing edit
access to this repo or any code skills. It's slower to update than the map
(a manual CSV re-import for now) but gets you shared, no-code control.

## 1. Get the data into a Google Sheet

Run (or wait for the monthly auto-update to run) `looker_export.py`, which
writes `output/looker_export.csv` — one row per incident, all 6 cities,
columns: `Incident ID, Date, Year, Month, City, State, Address, Killed,
Injured, Total Victims, Fatal Incident, Mass Shooting, Latitude, Longitude`.

1. Create a new Google Sheet (or reuse one you control access to).
2. File > Import > Upload > select `output/looker_export.csv` > **Replace
   current sheet**.
3. Repeat this import each time the underlying data refreshes. There's no
   API push yet — see "Later: automating the sync" at the bottom.

**Gotcha:** `Fatal Incident` and `Mass Shooting` come in as the text `True`/
`False`, not native booleans — Sheets/Looker won't `SUM()` them directly.
Section 3 below adds calculated fields that convert them to 0/1 first.

## 2. Connect Looker Studio and set up the pre/post split

1. In Looker Studio, **Create > Data source > Google Sheets**, pick the
   sheet, confirm the header row.
2. Create three **Parameters** (data source Edit view > Add a Parameter,
   top right):
   - `Cutoff Date` — Date, default e.g. `2024-09-01`
   - `Pre Window Days` — Number, default `180`
   - `Post Window Days` — Number, default `180`
3. Add these **Calculated Fields** on the data source:
   - `Fatal Flag` = `CASE WHEN Fatal Incident = "True" THEN 1 ELSE 0 END`
   - `Mass Shooting Flag` = `CASE WHEN Mass Shooting = "True" THEN 1 ELSE 0 END`
   - `Period` =
     ```
     CASE
       WHEN Date >= DATE_ADD(Cutoff Date, Pre Window Days * -1)
            AND Date < Cutoff Date THEN "Pre"
       WHEN Date >= Cutoff Date
            AND Date <= DATE_ADD(Cutoff Date, Post Window Days) THEN "Post"
     END
     ```
     Rows outside both windows come back `NULL` — filter charts to
     `Period is not null` so they're excluded rather than shown as a blank
     category.

## 3. Add viewer-facing controls

These are what let a practitioner change the window **without edit access**
to the report — Looker Studio parameter controls are per-viewer, not saved
back to the report.

- **Insert > Control > Date picker** bound to `Cutoff Date`.
- **Insert > Control > Input box / Slider** bound to `Pre Window Days` and
  `Post Window Days` (a slider with a sane range, e.g. 30–730, reads easier
  than free-text for most people).
- **Insert > Control > Drop-down list** on the `City` dimension, "(All)"
  included, for area selection.

## 4. Charts

- **Scorecards** (one row): `Count of Incident ID`, `SUM(Killed)`,
  `SUM(Injured)`, `SUM(Mass Shooting Flag)` — each with a filter chip
  `Period = Pre` duplicated next to one filtered `Period = Post`, so a
  viewer sees both numbers side by side.
- **Bar chart**: dimension `Period`, metrics `Count of Incident ID`,
  `SUM(Killed)`, `SUM(Injured)`. Style tab > set the two series colors to
  `#2a78d6` (Pre) and `#e34948` (Post) — matches the map's palette so the two
  views read as one system.
- **Table**: `Period` × the same four metrics, for the exact numbers behind
  the bar chart.
- **Time series** (optional): `Date` on the x-axis, `Count of Incident ID`,
  colored/broken down by `Period`, filtered to `Period is not null`. This is
  the closest Looker gets to a "before/after" trend line — it can't draw a
  vertical line at the cutoff itself without a more advanced blended-source
  trick, so the color break is doing that job instead.

## 5. Embedding the Leaflet map

Looker Studio's map visualization can't render thousands of individual dots
or a fatal/injury glyph distinction — that's what `explorer.html` is for.
Add it via **Insert > Embed URL**, pointing at a specific, shareable view:

```
https://<your-username>.github.io/multi-city-gun-violence/explorer.html?city=milwaukee&cutoff=2024-09-01&pre=180&post=180&embed=1
```

- `embed=1` hides the sidebar controls so the iframe is just the map —
  useful since Looker already has its own filter controls around it.
- **This URL is static.** Looker's own Parameter/filter controls do *not*
  reach inside the iframe — changing the Cutoff Date control in Looker will
  not move the embedded map. If you want a specific combination visible,
  set it in the URL's query string; if you want viewers to explore freely,
  drop `embed=1` and link to the full `explorer.html` instead of embedding it.
- This requires a public HTTPS URL, which means **GitHub Pages needs to be
  turned on for this repo** (Settings > Pages > Deploy from branch > main).
  It isn't enabled yet — right now the site only works from a local checkout.

## Later: automating the sync

Right now step 1 is a manual CSV re-import. If that becomes annoying, the
next step is a service account (Google Cloud project, Sheets API enabled,
a JSON key downloaded, the sheet shared with the service account's email)
and a `gspread`-based push added to `auto_update_all.py`, right alongside
the `export_explorer_data()` / `export_looker_csv()` calls it already makes.
Not built yet — ask if you want it wired up.
