"""Step 7 - Visualization layer (Streamlit + Plotly Express).

    streamlit run app.py

Rules followed (brief, "Visualization layer"):
* Every chart is fed by one of the 10 queries of queries.py, run in PostgreSQL.
* Every filter value travels to SQL as a PARAMETER (%(name)s), never pasted
  into the SQL text -> no SQL injection. The user never types SQL.
* Python does not filter, group or compute: it only sends the query and hands
  the returned rows to the chart.
* Bad input (empty search, nothing selected, no rows, database down) shows a
  message instead of crashing.
"""
from decimal import Decimal

import plotly.express as px
import psycopg2
import psycopg2.extras
import streamlit as st

from config import connect
from queries import LEAGUES, PLAYER_SEARCH, QUERIES, SEASONS

st.set_page_config(page_title="Football Data Explorer", layout="wide")
NO_DATA = "No data for this selection."


# ------------------------------------------------------------------ database
@st.cache_resource
def get_connection():
    """One connection reused between clicks (Streamlit reruns this file on every click)."""
    conn = connect()
    conn.autocommit = True      # read-only app: a failed query never leaves the connection blocked
    return conn


def run(sql, params=None):
    """Send one query with its parameters. Returns a list of dicts ([] on error)."""
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    except psycopg2.Error as e:
        get_connection.clear()  # next click opens a new connection (e.g. after the server restarts)
        st.error(f"Database error: {e}")
        return []


def as_columns(rows):
    """Rows -> columns, the format Plotly reads: [{'a': 1}, {'a': 2}] -> {'a': [1, 2]}.
    NUMERIC values arrive as Decimal; they are given to Plotly as float (same value)."""
    columns = {}
    for row in rows:
        for key, value in row.items():
            if isinstance(value, Decimal):
                value = float(value)
            columns.setdefault(key, []).append(value)
    return columns


def query_info(qid):
    """Small box under each chart: which query feeds it and who wrote it."""
    q = QUERIES[qid]
    with st.expander(f"{qid} · {q['title']} · author: {q['author']}"):
        st.write(q["question"])
        st.code(q["sql"].strip(), language="sql")


# ------------------------------------------------------------------ sidebar
st.sidebar.title("Football Data Explorer")
st.sidebar.caption("Transfermarkt data (Kaggle, CC0) · PostgreSQL · Project B")

leagues = run(LEAGUES)
if not leagues:
    st.warning("Cannot read the leagues. Is PostgreSQL running and the data loaded?")
    st.stop()
league_names = {r["competition_id"]: r["label"] for r in leagues}
league_codes = list(league_names)
competition = st.sidebar.selectbox("League", league_codes, index=league_codes.index("ES1"),
                                   format_func=lambda code: league_names[code])
seasons = [r["season"] for r in run(SEASONS, {"competition": competition})]
season = st.sidebar.selectbox("Season", seasons)
st.sidebar.caption("Season 2024 = 2024/25.")

tab_season, tab_leagues, tab_players, tab_awards = st.tabs(
    ["League season", "Compare leagues", "Players", "Golden Boot"])

# ------------------------------------------------------------ tab 1: season
with tab_season:
    st.header(f"{league_names[competition]} · {season}")

    st.subheader("League table")
    rows = run(QUERIES["Q1"]["sql"], {"competition": competition, "season": season})
    if rows:
        st.plotly_chart(px.bar(as_columns(rows), x="club", y="points"), use_container_width=True)
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info(NO_DATA)
    query_info("Q1")

    st.subheader("Top scorers")
    min_goals = st.slider("Minimum goals", min_value=1, max_value=30, value=10)
    rows = run(QUERIES["Q2"]["sql"], {"competition": competition, "season": season, "min_goals": min_goals})
    if rows:
        st.plotly_chart(px.bar(as_columns(rows), x="player", y="goals", color="goals_per_90",
                               hover_data=["club", "assists", "minutes"]), use_container_width=True)
    else:
        st.info(NO_DATA)
    query_info("Q2")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Clubs above the league's average attendance")
        rows = run(QUERIES["Q7"]["sql"], {"competition": competition, "season": season})
        if rows:
            st.plotly_chart(px.bar(as_columns(rows), x="club", y=["avg_attendance", "stadium_seats"],
                                   barmode="group"), use_container_width=True)
        else:
            st.info(NO_DATA)
        query_info("Q7")
    with col2:
        st.subheader("Young players with most minutes")
        max_age = st.slider("Younger than (years)", min_value=16, max_value=25, value=21)
        rows = run(QUERIES["Q8"]["sql"], {"competition": competition, "season": season, "max_age": max_age})
        if rows:
            st.plotly_chart(px.bar(as_columns(rows), x="player", y="minutes",
                                   hover_data=["club", "age_in_season", "goals"]), use_container_width=True)
        else:
            st.info(NO_DATA)
        query_info("Q8")

# ----------------------------------------------------------- tab 2: leagues
with tab_leagues:
    st.subheader("Home advantage by league")
    season_from, season_to = st.slider("Seasons", min_value=2012, max_value=2025, value=(2012, 2025))
    rows = run(QUERIES["Q4"]["sql"], {"season_from": season_from, "season_to": season_to})
    if rows:
        st.plotly_chart(px.bar(as_columns(rows), x="league", y=["home_win_pct", "draw_pct", "away_win_pct"]),
                        use_container_width=True)
    else:
        st.info(NO_DATA)
    query_info("Q4")

    st.subheader("Goals per game over the seasons")
    chosen = st.multiselect("Leagues to compare", league_codes, default=["ES1", "GB1", "IT1", "L1", "FR1"],
                            format_func=lambda code: league_names[code])
    if not chosen:
        st.info("Choose at least one league.")
    else:
        rows = run(QUERIES["Q6"]["sql"], {"competitions": chosen})   # a Python list -> ANY(%s)
        if rows:
            st.plotly_chart(px.line(as_columns(rows), x="season", y="goals_per_game", color="league",
                                    markers=True), use_container_width=True)
        else:
            st.info(NO_DATA)
    query_info("Q6")

# ----------------------------------------------------------- tab 3: players
with tab_players:
    st.subheader("Market value history of a player")
    text = st.text_input("Search a player by name (at least 3 letters)", value="Mbapp").strip()
    if len(text) < 3:
        st.info("Type at least 3 letters.")
    else:
        found = run(PLAYER_SEARCH, {"pattern": f"%{text}%"})     # the text is a parameter, never SQL
        if not found:
            st.info("No player with valuations matches that name.")
        else:
            player_names = {r["player_id"]: f"{r['name']} (born {r['date_of_birth']})" for r in found}
            player_id = st.selectbox("Player", list(player_names), format_func=lambda pid: player_names[pid])
            rows = run(QUERIES["Q3"]["sql"], {"player_id": player_id})
            if rows:
                st.plotly_chart(px.line(as_columns(rows), x="valuation_date", y="market_value_eur",
                                        markers=True, hover_data=["change_eur"]), use_container_width=True)
            else:
                st.info(NO_DATA)
    query_info("Q3")

    st.subheader(f"Most valuable active players by position · {league_names[competition]}")
    top_n = st.number_input("Players per position", min_value=1, max_value=10, value=3)
    rows = run(QUERIES["Q5"]["sql"], {"competition": competition, "top_n": top_n})
    if rows:
        st.plotly_chart(px.bar(as_columns(rows), x="player", y="market_value_eur", color="position",
                               hover_data=["club", "position_rank"]), use_container_width=True)
    else:
        st.info(NO_DATA)
    query_info("Q5")

    st.subheader(f"Biggest goal improvement vs the previous season · {season}")
    rows = run(QUERIES["Q9"]["sql"], {"competition": competition, "season": season})
    if rows:
        st.plotly_chart(px.bar(as_columns(rows), x="player", y=["previous_goals", "goals"], barmode="group"),
                        use_container_width=True)
    else:
        st.info(NO_DATA)
    query_info("Q9")

# ------------------------------------------------------------ tab 4: awards
with tab_awards:
    st.subheader(f"Golden Boot winners · {league_names[competition]}")
    st.caption("Table golden_boot is filled by Q10 (DELETE + INSERT in one transaction, run by run_queries.py).")
    rows = run(QUERIES["Q10"]["sql"], {"competition": competition})
    if rows:
        st.plotly_chart(px.bar(as_columns(rows), x="season", y="goals", hover_data=["winners"]),
                        use_container_width=True)
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info(NO_DATA)
    query_info("Q10")
