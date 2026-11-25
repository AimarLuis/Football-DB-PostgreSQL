"""Step 6 - Run sql/check_constraints.sql and print the results.

    python check_constraints.py
"""
import os

from config import HERE, connect

with open(os.path.join(HERE, "sql", "check_constraints.sql"), encoding="utf-8") as f:
    blocks = [b.strip() for b in f.read().split(";") if "SELECT" in b]

conn = connect()
with conn.cursor() as cur:
    for block in blocks:
        title = [line for line in block.splitlines() if line.startswith("-- C")][0]
        cur.execute(block)
        rows = cur.fetchall()
        print(f"\n{title}   ({len(rows)} rows)")
        print("   ", " | ".join(d[0] for d in cur.description))
        for row in rows:
            print("   ", " | ".join("" if v is None else str(v) for v in row))
conn.close()
