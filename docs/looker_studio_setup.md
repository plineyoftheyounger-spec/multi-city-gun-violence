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
2. Create four **Parameters** (data source Edit view > Add a Parameter, top
   right) — matching `explorer.html`'s model of picking exact dates rather
   than a cutoff + day counts:
   - `Pre Start` — Date
   - `Pre End` — Date
   - `Post Start` — Date
   - `Post End` — Date
3. Add these **Calculated Fields** on the data source:
   - `Fatal Flag` = `CASE WHEN Fatal Incident = "True" THEN 1 ELSE 0 END`
   - `Mass Shooting Flag` = `CASE WHEN Mass Shooting = "True" THEN 1 ELSE 0 END`
   - `Period` =
     ```
     CASE
       WHEN Date >= Pre Start AND Date <= Pre End THEN "Pre"
       WHEN Date >= Post Start AND Date <= Post End THEN "Post"
     END
     ```
     Rows outside both windows come back `NULL` — filter charts to
     `Period is not null` so they're excluded rather than shown as a blank
     category.

## 3. Add viewer-facing controls

These are what let a practitioner change the window **without edit access**
to the report — Looker Studio parameter controls are per-viewer, not saved
back to the report.

- **Insert > Control > Date Range Control**, one bound to the
  `Pre Start`/`Pre End` parameter pair and a second bound to
  `Post Start`/`Post End` — this is Looker's closest equivalent to the two
  sliders in `explorer.html` (drag both ends of a single range instead of
  two separate date pickers). If your Looker Studio version doesn't offer
  parameter-bound range controls, fall back to four individual **Date
  picker** controls, one per parameter.
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
https://<your-username>.github.io/multi-city-gun-violence/explorer.html?city=milwaukee&preStart=2024-03-01&preEnd=2024-08-31&postStart=2024-09-01&postEnd=2025-02-28&embed=1
```

- `embed=1` hides the sidebar controls so the iframe is just the map —
  useful since Looker already has its own filter controls around it.
- **This URL is static.** Looker's own Parameter/filter controls do *not*
  reach inside the iframe — changing the Pre/Post Date Range controls in
  Looker will not move the embedded map. If you want a specific combination visible,
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
