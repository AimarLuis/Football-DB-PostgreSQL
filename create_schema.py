"""Step 2 - Create every table of the model by running sql/schema.sql.

    python create_schema.py

The load (load.py) never creates tables: it only inserts rows into these.
"""
import os

import psycopg2

from config import DB_NAME, HERE, connect

# 1) Create the database "football" if it does not exist yet.
#    CREATE DATABASE cannot run inside a transaction -> autocommit.
admin = connect("postgres")
admin.autocommit = True
with admin.cursor() as cur:
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    if cur.fetchone() is None:
        cur.execute(f"CREATE DATABASE {DB_NAME}")
        print("Database", DB_NAME, "created")
admin.close()

# 2) Run the DDL script.
with open(os.path.join(HERE, "sql", "schema.sql"), encoding="utf-8") as f:
    ddl = f.read()

conn = connect()
try:
    with conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
    print("Schema created: competitions, clubs, players, games, appearances,"
          " player_valuations, golden_boot")
except psycopg2.Error as e:
    print("Error creating the schema:", e)
finally:
    conn.close()
