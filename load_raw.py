"""Step 1a - Copy every raw CSV, untouched, into a staging schema called "raw".

    python load_raw.py

Why: the brief says "all analysis is done in SQL". To profile the files with SQL
we first need them inside PostgreSQL. Every column is TEXT, so nothing is
converted or rejected: we see the data exactly as it comes in the file.

The "raw" schema is only a profiling area. It is NOT part of the model:
the real tables are created by sql/schema.sql in the "public" schema.
"""
import csv
import os

from config import connect, data_dir

folder = data_dir()
conn = connect()
with conn:                                   # one transaction: commit at the end
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA IF EXISTS raw CASCADE")
        cur.execute("CREATE SCHEMA raw")
        for file_name in sorted(os.listdir(folder)):
            table = "raw." + file_name.replace(".csv", "")
            path = os.path.join(folder, file_name)
            with open(path, encoding="utf-8") as f:
                header = next(csv.reader(f))          # first line of the file = column names
            columns = ", ".join(f'"{c}" TEXT' for c in header)
            cur.execute(f"CREATE TABLE {table} ({columns})")
            with open(path, encoding="utf-8") as f:
                # COPY ... CSV HEADER: the fastest way to bring a file in (Practice 9).
                cur.copy_expert(f"COPY {table} FROM STDIN WITH (FORMAT csv, HEADER true)", f)
            print(f"{table:28s} loaded")
conn.close()
