"""Step 4 - Show that an index makes a visible difference on the big table.

    python index_demo.py

appearances has 1.6 million rows and its primary key is (game_id, player_id).
That index starts with game_id, so it does NOT help to find "all the games
of one player": PostgreSQL has to read the whole table (Seq Scan).
We measure the query with EXPLAIN ANALYZE before and after creating an
index on player_id. The index is kept: the app also uses it.
"""
from config import connect

QUERY = """
EXPLAIN ANALYZE
SELECT game_id, goals, assists, minutes_played
FROM appearances
WHERE player_id = 28003          -- Lionel Messi
"""


def show_plan(cur, title):
    cur.execute(QUERY)
    print(f"\n--- {title}")
    for (line,) in cur.fetchall():
        print("   ", line)


conn = connect()
conn.autocommit = True
cur = conn.cursor()

cur.execute("DROP INDEX IF EXISTS idx_appearances_player")
cur.execute("ANALYZE appearances")
show_plan(cur, "BEFORE: no index on player_id")

cur.execute("CREATE INDEX idx_appearances_player ON appearances (player_id)")
cur.execute("ANALYZE appearances")
show_plan(cur, "AFTER: CREATE INDEX idx_appearances_player ON appearances (player_id)")
conn.close()
