# Project B · Football Data in PostgreSQL

Information Technology (4th year) · Telmo Lopez and Aimar Luis · 25 November 2026

Real data from Transfermarkt (Kaggle dataset
[davidcariboo/player-scores](https://www.kaggle.com/datasets/davidcariboo/player-scores),
licence **CC0: Public Domain**, version 679) turned into a relational database in
PostgreSQL, loaded with Python in one transaction, analysed with 10 SQL queries and
explored in a Streamlit app. The report is `report/report.pdf`.

## The pipeline in one picture

```
Kaggle CSV files ──download_data.py──► kagglehub cache (not in the repo)
        │
        ├─ load_raw.py ──► schema "raw" (all TEXT) ── run_profile.py + sql/profiling.sql ──► output/profile_results.md
        │
        └─ load.py (ONE transaction, cleaning rules R1-R10)
                     ▼
   sql/schema.sql ──► competitions, clubs, players, games, appearances, player_valuations
   (create_schema.py)                     │
                                          ├─ index_demo.py   (EXPLAIN ANALYZE before/after an index)
                                          ├─ queries.py      (the 10 queries, single source)
                                          │    ├─ run_queries.py ──► output/queries_results.md (+ Q10 fills golden_boot)
                                          │    └─ app.py (Streamlit: charts + filters as SQL parameters)
                                          └─ check_constraints.py + sql/check_constraints.sql
```

## How to run it (from zero)

Requirements: Python 3.10+, PostgreSQL running on `localhost:5432` (user `postgres`).

```powershell
pip install -r requirements.txt
```

1. Create `password.txt` next to this file with the PostgreSQL password in one line
   (it is in `.gitignore`, it is never committed).
2. Run the steps in order:

| Step | Command | What it does | Time |
|---|---|---|---|
| 0 | `python download_data.py` | Downloads the 12 CSV files (234 MB zip) to the kagglehub cache | ~2 min |
| 1 | `python load_raw.py` | Copies every CSV, untouched, to schema `raw` (all TEXT) | ~1 min |
| 1 | `python run_profile.py` | Runs `sql/profiling.sql` → `output/profile_results.md` | ~3 min |
| 2 | `python create_schema.py` | Creates database `football` and runs `sql/schema.sql` | 1 s |
| 3 | `python load.py --fail` | **Rollback demo**: a wrong row → error → every table still has 0 rows | 20 s |
| 3 | `python load.py` | The real load, one transaction, prints the cleaning rules, then `ANALYZE` | ~4 min |
| 4 | `python index_demo.py` | `EXPLAIN ANALYZE` without and with an index on `appearances(player_id)` | 2 s |
| 5 | `python run_queries.py` | Q10 (INSERT in a transaction) + the 10 queries → `output/queries_results.md` | 10 s |
| 6 | `python check_constraints.py` | Lists every constraint after the load + integrity checks | 2 s |
| 7 | `streamlit run app.py` | Opens the app in the browser | — |

`load.py` only inserts: if the tables are not empty it fails on the primary key and
rolls back. To load again, run `create_schema.py` first.

## Files

| File | Role |
|---|---|
| `config.py` | Connection settings and dataset path (the only place that reads the password) |
| `download_data.py` | Step 0: get the raw data |
| `load_raw.py`, `run_profile.py`, `sql/profiling.sql` | Step 1: staging copy and profiling queries |
| `sql/schema.sql`, `create_schema.py` | Step 2: physical schema (PK, FK, NOT NULL, UNIQUE, CHECK) |
| `load.py` | Step 3: ETL in one transaction, cleaning rules with counters |
| `index_demo.py` | Step 4: the index that makes a visible difference |
| `queries.py`, `run_queries.py` | Step 5: the 10 queries (question, author, SQL, why) |
| `sql/check_constraints.sql`, `check_constraints.py` | Step 6: verification after loading |
| `app.py` | Step 7: Streamlit visualization |
| `report/report.pdf` | The report |
| `EFFORT_LOG.md` | What each member did |
| `CLAUDE.md` | Context file read by the AI coding agent (see section 7 of the report) |

## Rules we follow from the brief

* **All analysis is SQL.** No pandas/NumPy. Python reads files, cleans formats row by
  row, sends queries with parameters and passes rows to the charts.
* **One transaction** for the whole load (`with conn:` in psycopg2), rollback demonstrated.
* **Missing values stay NULL**; nothing is invented.
* **No SQL injection**: every user value is a `%(name)s` parameter; the user never types SQL.
