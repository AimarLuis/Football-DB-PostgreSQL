"""Step 1b - Run every query of sql/profiling.sql and write the results to
output/profile_results.md (summarised in section 2 of the report).

    python run_profile.py

Python only sends the SQL and writes the returned rows as Markdown tables.
The nulls per column are also counted in SQL: for every column of the
modelled files one line "COUNT(*) - COUNT(column)" is added to a query.
"""
import os

from config import HERE, connect

MODELLED_FILES = ["competitions", "clubs", "players", "games",
                  "appearances", "player_valuations"]


def markdown_table(cur):
    """The rows of the last query as a Markdown table."""
    columns = [d[0] for d in cur.description]
    lines = ["| " + " | ".join(columns) + " |",
             "|" + "---|" * len(columns)]
    for row in cur.fetchall():
        lines.append("| " + " | ".join("" if v is None else str(v) for v in row) + " |")
    return "\n".join(lines)


with open(os.path.join(HERE, "sql", "profiling.sql"), encoding="utf-8") as f:
    blocks = [b.strip() for b in f.read().split(";") if "-- P" in b]

out = ["# Data profile (results of sql/profiling.sql)\n"]
conn = connect()
with conn.cursor() as cur:
    for block in blocks:
        title = [line for line in block.splitlines() if line.startswith("-- P")][0]
        cur.execute(block)
        out += [f"## {title[3:]}\n", "```sql\n" + block + "\n```\n", markdown_table(cur), ""]
        print("done:", title[3:])

    # Nulls per column (an empty field in the CSV arrives as NULL with COPY ... CSV).
    out.append("## Nulls per column (modelled files)\n")
    for table in MODELLED_FILES:
        cur.execute("SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'raw' AND table_name = %s ORDER BY ordinal_position",
                    (table,))
        columns = [r[0] for r in cur.fetchall()]
        # One row per column: SELECT 'name', COUNT(*) - COUNT("name"), ... UNION ALL ...
        parts = [f"""SELECT '{c}' AS column_name,
                            COUNT(*) - COUNT("{c}") AS nulls,
                            ROUND(100.0 * (COUNT(*) - COUNT("{c}")) / COUNT(*), 1) AS pct_nulls
                     FROM raw.{table}""" for c in columns]
        cur.execute(" UNION ALL ".join(parts))
        out += [f"### {table}\n", markdown_table(cur), ""]
        print("done: nulls of", table)
conn.close()

os.makedirs(os.path.join(HERE, "output"), exist_ok=True)
with open(os.path.join(HERE, "output", "profile_results.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Written output/profile_results.md")
