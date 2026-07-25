"""
build_maps.py
─────────────
Two Folium map builders, generalized from orlando_gun_violence/04_analysis_maps.py:

  build_year_map(df, city_cfg, slug)  — one togglable layer per calendar year,
      light-to-dark ordinal blue ramp (see ordinal_ramp.py), for cities where
      users pick their own time period.

  build_era_map(df, city_cfg, slug)   — two togglable layers (pre/post a fixed
      cutoff date), diverging blue/red pair, for Milwaukee.

Run directly to (re)build maps for every city from already-processed data:
    python build_maps.py
"""

import folium

import cities
from ordinal_ramp import year_color_ramp

MILWAUKEE_PRE_COLOR  = "#2a78d6"   # diverging pair, validated in palette.md
MILWAUKEE_POST_COLOR = "#e34948"


# ═══════════════════════════════════════════════════════════════════════════════
# Shared map components (ported from orlando_gun_violence/04_analysis_maps.py)
# ═══════════════════════════════════════════════════════════════════════════════

def base_map(city_cfg):
    # prefer_canvas: cities like Milwaukee have thousands of markers in a
    # single layer — default SVG rendering chokes the browser at that count,
    # canvas rendering handles it fine.
    return folium.Map(
        location=[city_cfg["lat"], city_cfg["lon"]],
        zoom_start=city_cfg["zoom"],
        tiles="CartoDB positron",
        prefer_canvas=True,
    )


def add_title(m, html_text):
    html = f"""
    <div style="position:fixed;top:10px;left:50%;transform:translateX(-50%);
         background:white;padding:8px 18px;border-radius:6px;border:1px solid #aaa;
         z-index:1000;font-family:Arial,sans-serif;font-size:14px;text-align:center;
         white-space:nowrap;">
        {html_text}
    </div>"""
    m.get_root().html.add_child(folium.Element(html))


def add_legend(m, items):
    rows = "".join(
        f'<div><span style="color:{c};font-size:18px;line-height:1.3;">●</span>&nbsp;{label}</div>'
        for label, c in items
    )
    html = f"""
    <div style="position:fixed;bottom:30px;left:30px;background:white;
         padding:10px 14px;border-radius:6px;border:1px solid #aaa;
         z-index:1000;font-family:Arial,sans-serif;font-size:13px;
         max-height:70vh;overflow-y:auto;">{rows}</div>"""
    m.get_root().html.add_child(folium.Element(html))


def dot_layer(df, name, color, show=True):
    group = folium.FeatureGroup(name=name, show=show)
    for _, row in df.iterrows():
        popup = (
            f"<b>{row['date'].strftime('%b %d, %Y')}</b><br>"
            f"{row.get('address', '')}<br>"
            f"Killed: {row['killed']} &nbsp;|&nbsp; Injured: {row['injured']}"
        )
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=5,
            color=color,
            fill=True,
            fill_opacity=0.72,
            popup=folium.Popup(popup, max_width=280),
        ).add_to(group)
    return group


def save_map(m, slug, filename):
    out_dir = cities.maps_dir(slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / filename
    m.save(str(out))
    print(f"  Saved: {out}")


# ═══════════════════════════════════════════════════════════════════════════════
# Map builders
# ═══════════════════════════════════════════════════════════════════════════════

def build_year_map(df, city_cfg, slug):
    """One FeatureGroup layer per year, start_year..present, ordinal blue ramp."""
    start_year = city_cfg["start_year"]
    end_year = int(df["year"].max()) if not df.empty else start_year
    years = list(range(start_year, end_year + 1))
    colors = year_color_ramp(len(years))

    m = base_map(city_cfg)
    for year, color in zip(years, colors):
        year_df = df[df["year"] == year]
        dot_layer(year_df, str(year), color, show=True).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    add_title(m, f"{city_cfg['display_name']} Gun Violence — {start_year}–Present")
    add_legend(m, [(str(y), c) for y, c in zip(years, colors)])
    save_map(m, slug, "dot_by_year.html")


def build_era_map(df, city_cfg, slug):
    """Two FeatureGroup layers: pre/post a fixed intervention date."""
    era = city_cfg["era"]
    pre_df = df[(df["date"].dt.date >= era["pre_start"]) & (df["date"].dt.date <= era["pre_end"])]
    post_df = df[df["date"].dt.date >= era["post_start"]]

    m = base_map(city_cfg)
    dot_layer(pre_df, era["pre_label"], MILWAUKEE_PRE_COLOR, show=True).add_to(m)
    dot_layer(post_df, era["post_label"], MILWAUKEE_POST_COLOR, show=True).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    add_title(m, f"{city_cfg['display_name']} Gun Violence — Pre vs. Post Intervention")
    add_legend(m, [(era["pre_label"], MILWAUKEE_PRE_COLOR),
                   (era["post_label"], MILWAUKEE_POST_COLOR)])
    save_map(m, slug, "dot_by_era.html")


def build_map_for_city(slug):
    import pandas as pd

    path = cities.processed_csv(slug)
    if not path.exists():
        print(f"  Skipping {slug}: no processed data at {path}")
        return
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.dropna(subset=["lat", "lon"])
    df["year"] = df["date"].dt.year

    city_cfg = cities.CITIES[slug]
    print(f"{city_cfg['display_name']}: {len(df):,} mappable incidents")
    if city_cfg["mode"] == "era":
        build_era_map(df, city_cfg, slug)
    else:
        build_year_map(df, city_cfg, slug)


if __name__ == "__main__":
    import sys
    slugs = sys.argv[1:] or list(cities.CITIES)
    for slug in slugs:
        build_map_for_city(slug)
