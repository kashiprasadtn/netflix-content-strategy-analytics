"""Netflix Content Strategy dashboard (Streamlit + Plotly).

Data source
-----------
By default the app reads the processed CSVs produced by notebooks/01_spark_etl.ipynb
(data/processed/titles.csv and data/processed/title_genres.csv), so it runs with no database.

To read from MySQL instead (after running sql/mysql_load.sql), set:
    NETFLIX_SOURCE=mysql  MYSQL_HOST=...  MYSQL_PORT=3306  MYSQL_USER=...  MYSQL_PASSWORD=...  MYSQL_DATABASE=netflix_db
Credentials are read from the environment only; nothing is hard-coded.

Run from the repository root:
    streamlit run app/app.py
"""
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RED, DARK, GREY = "#E50914", "#221F1F", "#9E9E9E"
AGE_ORDER = ["Very recent (0-2y)", "Recent (3-5y)", "Mature (6-10y)", "Older (11-20y)", "Legacy (20y+)"]

st.set_page_config(page_title="Netflix Content Strategy", page_icon="🎬", layout="wide")


@st.cache_data(ttl=600)
def load_data():
    if os.getenv("NETFLIX_SOURCE", "csv").lower() == "mysql":
        import mysql.connector  # optional dependency, only needed for the MySQL source
        cfg = {k: os.environ[f"MYSQL_{k.upper()}"] for k in ["host", "user", "password", "database"]}
        cfg["port"] = int(os.getenv("MYSQL_PORT", "3306"))
        conn = mysql.connector.connect(**cfg)
        try:
            titles = pd.read_sql("SELECT * FROM titles", conn)
            genres = pd.read_sql("SELECT * FROM title_genres", conn)
        finally:
            conn.close()
    else:
        titles = pd.read_csv(PROCESSED / "titles.csv")
        genres = pd.read_csv(PROCESSED / "title_genres.csv")
    return titles, genres


titles, genres = load_data()

# ---------------- Sidebar filters ----------------
st.sidebar.header("Filters")
types = st.sidebar.multiselect("Content type", ["Movie", "TV Show"], default=["Movie", "TV Show"])
yr_min, yr_max = int(titles.release_year.min()), int(titles.release_year.max())
years = st.sidebar.slider("Release year", yr_min, yr_max, (2008, yr_max))
top_countries = titles.loc[titles.primary_country != "Unknown", "primary_country"].value_counts().head(25).index.tolist()
countries = st.sidebar.multiselect("Primary country (top 25)", top_countries, default=[])
audiences = st.sidebar.multiselect("Audience", ["Kids & family", "Teens", "Adults", "Unrated"],
                                   default=["Kids & family", "Teens", "Adults", "Unrated"])

f = titles[titles.type.isin(types) & titles.release_year.between(*years) & titles.audience.isin(audiences)]
if countries:
    f = f[f.primary_country.isin(countries)]
fg = genres[genres.show_id.isin(f.show_id)]

st.title("Netflix Content Strategy Dashboard")
st.caption(f"Catalogue snapshot up to Sept 2021 · {len(f):,} of {len(titles):,} titles match the filters · "
           "title-level metrics use one row per title; genre metrics use title x genre rows")

if f.empty:
    st.warning("No titles match the current filters.")
    st.stop()

# ---------------- Executive summary ----------------
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Titles", f"{len(f):,}")
k2.metric("Movies / TV shows", f"{(f.type == 'Movie').sum():,} / {(f.type == 'TV Show').sum():,}")
k3.metric("Recent (≤ 5 yrs at snapshot)", f"{f.is_recent.mean():.0%}")
k4.metric("Added within 1 yr of release", f"{f.is_original_window.mean():.0%}")
k5.metric("Countries", f"{f.loc[f.primary_country != 'Unknown', 'primary_country'].nunique()}")

tab1, tab2, tab3, tab4 = st.tabs(["Portfolio", "Freshness", "Genres", "Geography & audience"])

with tab1:
    c1, c2 = st.columns(2)
    added = f.dropna(subset=["year_added"]).astype({"year_added": int})
    by_year = added[added.year_added >= 2015].groupby(["year_added", "type"]).size().reset_index(name="titles")
    c1.plotly_chart(px.bar(by_year, x="year_added", y="titles", color="type", color_discrete_map={"Movie": RED, "TV Show": DARK},
                           title="Titles added per year (2021 = Jan to Sep)"), width="stretch")
    rel = f.groupby(["release_year", "type"]).size().reset_index(name="titles")
    c2.plotly_chart(px.line(rel, x="release_year", y="titles", color="type", color_discrete_map={"Movie": RED, "TV Show": DARK},
                            title="Titles by release year"), width="stretch")

with tab2:
    c1, c2 = st.columns(2)
    age = f.content_age_group.value_counts().reindex(AGE_ORDER).fillna(0).reset_index()
    age.columns = ["Age group", "titles"]
    c1.plotly_chart(px.bar(age, x="Age group", y="titles", color_discrete_sequence=[RED], title="Content age at snapshot"), width="stretch")
    fr = (added[added.year_added >= 2015].groupby("year_added")
          .agg(within_1y=("is_original_window", "mean"), ten_plus=("add_lag_years", lambda s: (s >= 10).mean())).reset_index())
    fr = fr.melt(id_vars="year_added", var_name="measure", value_name="share")
    fr["measure"] = fr["measure"].map({"within_1y": "Added within 1 year of release", "ten_plus": "Added 10+ years after release"})
    c2.plotly_chart(px.line(fr, x="year_added", y="share", color="measure", markers=True, color_discrete_sequence=[RED, DARK],
                            title="Freshness of additions"), width="stretch")

with tab3:
    c1, c2 = st.columns(2)
    top_g = fg.groupby("genre").show_id.nunique().sort_values(ascending=False).head(15).reset_index(name="titles")
    c1.plotly_chart(px.bar(top_g.iloc[::-1], x="titles", y="genre", orientation="h", color_discrete_sequence=[RED],
                           title="Top 15 genres (distinct titles)"), width="stretch")
    gy = fg.dropna(subset=["year_added"])
    gy = gy[gy.genre.isin(top_g.genre.head(6)) & (gy.year_added >= 2015)]
    gy = gy.groupby(["year_added", "genre"]).show_id.nunique().reset_index(name="titles")
    c2.plotly_chart(px.line(gy, x="year_added", y="titles", color="genre", markers=True, title="Top 6 genres - titles added per year"),
                    width="stretch")

with tab4:
    c1, c2 = st.columns(2)
    ctry = f[f.primary_country != "Unknown"].primary_country.value_counts().head(15).reset_index()
    ctry.columns = ["country", "titles"]
    c1.plotly_chart(px.bar(ctry.iloc[::-1], x="titles", y="country", orientation="h", color_discrete_sequence=[DARK],
                           title="Top 15 primary production countries"), width="stretch")
    aud = f.groupby(["type", "audience"]).size().reset_index(name="titles")
    c2.plotly_chart(px.bar(aud, x="type", y="titles", color="audience", barmode="stack",
                           color_discrete_sequence=[RED, DARK, GREY, "#F5C518"], title="Audience mix by type"), width="stretch")

with st.expander("Data notes"):
    st.markdown(
        "- **Content age** is measured against the catalogue snapshot (latest `date_added`, 25 Sept 2021), "
        "so figures do not drift with the date the dashboard is opened.\n"
        "- 22 source rows had values shifted into the rating column; their rating is shown as *Unknown*.\n"
        "- 9.4% of titles have no country recorded and are excluded from country charts.")
