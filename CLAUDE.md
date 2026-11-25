# Project B · Football Data in PostgreSQL

Context file for the AI coding agent (Claude Code) used in this project. It reads this
file at the start of every session. See the AI adoption report (section 7 of
`report/report.pdf`) for what the agent was used for.

- Team: Telmo Lopez and Aimar Luis. Information Technology (4th year), delivery 25 Nov 2026.
- Dataset: Kaggle `davidcariboo/player-scores`, **version 679** (CC0), downloaded by
  `download_data.py` to the kagglehub cache. Raw data is never committed.
- Database: local PostgreSQL, database `football`, user `postgres`; the password is in
  `password.txt` (in `.gitignore`, never committed, never written by the agent).

## Run order
`download_data.py` → `load_raw.py` → `run_profile.py` → `create_schema.py` →
`load.py --fail` (rollback demo) → `load.py` → `index_demo.py` → `run_queries.py` →
`check_constraints.py` → `streamlit run app.py`. Details and timings in `README.md`.

## Rules (from the brief)
- All analysis in SQL. No pandas/NumPy; Python only reads files, cleans formats row by
  row, sends queries and passes rows to the charts.
- The whole load is one transaction; missing values stay NULL; every cleaning rule has a counter.
- Every user value reaches SQL as a `%(name)s` parameter (no SQL injection).
- `queries.py` is the only copy of the 10 queries (used by `run_queries.py` and `app.py`).
  Authors: Aimar Luis Q1 Q3 Q5 Q9 Q10, Telmo Lopez Q2 Q4 Q6 Q7 Q8.
- Use only the SQL and Python seen in the course (SQL I-III, Python + PostgreSQL);
  `x::int` is written as a short form of `CAST(x AS INTEGER)`.

## What the team must be able to defend
The model and its exceptions, the schema and its constraints, the ETL transaction and the
cleaning rules, and the 10 queries.
