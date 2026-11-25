"""Step 3 - ETL: read the raw CSV files, clean them and insert them into the tables.

    python load.py           normal load (run create_schema.py first)
    python load.py --fail    rollback demo: a wrong row is inserted on purpose

* The WHOLE load is ONE transaction (`with conn:`): if anything fails,
  PostgreSQL rolls everything back and the tables stay empty.
* Python only reads and cleans row by row. It never filters by analysis,
  groups or computes results: that is done in SQL (queries.py).
* R1: empty fields ("") become NULL (None). No value is ever invented.
* Every cleaning rule has a counter: the number of rows it affected is
  printed at the end and copied to the report.
"""
import csv
import os
import sys
import time

import psycopg2
from psycopg2.extras import execute_values

from config import connect, data_dir

FOLDER = data_dir()
BATCH_SIZE = 10_000
rules = {}          # cleaning rule -> number of rows affected


def count(rule):
    rules[rule] = rules.get(rule, 0) + 1


# ---------------------------------------------------------------- helpers
def read_csv(file_name):
    """Yield every row of a CSV file as a dict {column: text}."""
    with open(os.path.join(FOLDER, file_name), encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f)


def text(value):
    """'' or spaces -> None (NULL). Otherwise the text without outer spaces."""
    value = (value or "").strip()
    return value if value else None


def integer(value):
    """'27' -> 27, '27.0' -> 27, '' -> None."""
    value = text(value)
    return int(float(value)) if value is not None else None


def decimal(value):
    value = text(value)
    return float(value) if value is not None else None


def day(value):
    """'1978-06-09 00:00:00' -> '1978-06-09' (PostgreSQL turns it into DATE)."""
    value = text(value)
    return value[:10] if value is not None else None


def insert(cur, table, columns, rows):
    """Insert an iterable of tuples in batches with execute_values (Practice 9)."""
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s"
    batch, total = [], 0
    for row in rows:
        batch.append(row)
        if len(batch) == BATCH_SIZE:
            execute_values(cur, sql, batch, page_size=BATCH_SIZE)
            total += len(batch)
            batch = []
    if batch:
        execute_values(cur, sql, batch, page_size=BATCH_SIZE)
        total += len(batch)
    print(f"  {table:18s} {total:>9,} rows inserted")
    return total


# ------------------------------------------------- one generator per table
competition_ids, league_ids, club_ids, player_ids, game_ids = set(), set(), set(), set(), set()


def competitions():
    for r in read_csv("competitions.csv"):
        competition_ids.add(r["competition_id"])
        if r["type"] == "domestic_league":
            league_ids.add(r["competition_id"])
        yield (r["competition_id"], r["name"], r["type"],
               text(r["country_name"]), text(r["confederation"]))


def clubs():
    for r in read_csv("clubs.csv"):
        competition = text(r["domestic_competition_id"])
        if competition is not None and competition not in competition_ids:
            count("R2 clubs: league code not in competitions.csv -> NULL")
            competition = None
        seats = integer(r["stadium_seats"])
        if seats == 0:
            count("R3 clubs: stadium_seats = 0 (unknown) -> NULL")
            seats = None
        age = decimal(r["average_age"])
        if age == 0:
            count("R4 clubs: average_age = 0 (empty squad) -> NULL")
            age = None
        club_ids.add(int(r["club_id"]))
        yield (int(r["club_id"]), r["name"], competition, integer(r["squad_size"]),
               age, decimal(r["foreigners_percentage"]),
               text(r["stadium_name"]), seats, int(r["last_season"]))


def players():
    for r in read_csv("players.csv"):
        position = text(r["position"])
        if position == "Missing":
            count("R5 players: position 'Missing' -> NULL")
            position = None
        height = integer(r["height_in_cm"])
        if height is not None and height < 150:
            count("R6 players: impossible height (< 150 cm) -> NULL")
            height = None
        club = integer(r["current_club_id"])
        if club is not None and club not in club_ids:
            count("R7 players: current club not in clubs.csv -> NULL")
            club = None
        player_ids.add(int(r["player_id"]))
        yield (int(r["player_id"]), text(r["name"]), day(r["date_of_birth"]),
               text(r["country_of_citizenship"]), position, text(r["sub_position"]),
               text(r["foot"]), height, club, int(r["last_season"]))


def games():
    for r in read_csv("games.csv"):
        if r["competition_id"] not in league_ids:
            count("R8 games: not a domestic league game (out of scope) -> discarded")
            continue
        game_ids.add(int(r["game_id"]))
        yield (int(r["game_id"]), r["competition_id"], int(r["season"]), text(r["round"]),
               day(r["date"]), int(r["home_club_id"]), int(r["away_club_id"]),
               int(r["home_club_goals"]), int(r["away_club_goals"]),
               integer(r["attendance"]), text(r["stadium"]), text(r["referee"]))


def appearances():
    for r in read_csv("appearances.csv"):
        if int(r["game_id"]) not in game_ids:
            count("R9 appearances: game not loaded (R8) -> discarded")
            continue
        if int(r["player_id"]) not in player_ids:
            count("R10 appearances: player not in players.csv -> discarded")
            continue
        yield (int(r["game_id"]), int(r["player_id"]), int(r["player_club_id"]),
               int(r["minutes_played"]), int(r["goals"]), int(r["assists"]),
               int(r["yellow_cards"]), int(r["red_cards"]))


def valuations():
    for r in read_csv("player_valuations.csv"):
        yield (int(r["player_id"]), day(r["date"]), int(float(r["market_value_in_eur"])))


# ------------------------------------------------------------------ main
def main(fail_on_purpose):
    start = time.time()
    conn = connect()
    try:
        with conn:                                  # BEGIN ... COMMIT / ROLLBACK
            with conn.cursor() as cur:
                insert(cur, "competitions",
                       ["competition_id", "name", "type", "country_name", "confederation"],
                       competitions())
                insert(cur, "clubs",
                       ["club_id", "name", "domestic_competition_id", "squad_size", "average_age",
                        "foreigners_percentage", "stadium_name", "stadium_seats", "last_season"],
                       clubs())
                insert(cur, "players",
                       ["player_id", "name", "date_of_birth", "country_of_citizenship", "position",
                        "sub_position", "foot", "height_cm", "current_club_id", "last_season"],
                       players())
                insert(cur, "games",
                       ["game_id", "competition_id", "season", "round", "game_date", "home_club_id",
                        "away_club_id", "home_goals", "away_goals", "attendance", "stadium", "referee"],
                       games())
                if fail_on_purpose:
                    print("  --fail: inserting an appearance of a game that does not exist...")
                    cur.execute("INSERT INTO appearances VALUES (-1, -1, -1, 90, 0, 0, 0, 0)")
                insert(cur, "appearances",
                       ["game_id", "player_id", "club_id", "minutes_played", "goals", "assists",
                        "yellow_cards", "red_cards"],
                       appearances())
                insert(cur, "player_valuations",
                       ["player_id", "valuation_date", "market_value_eur"],
                       valuations())
        print(f"COMMIT: load finished in {time.time() - start:.0f} s")
        # Fresh statistics for the query planner: without them the first queries
        # can choose a very bad plan (PostgreSQL still thinks the tables are empty).
        with conn:
            with conn.cursor() as cur:
                cur.execute("ANALYZE")
        print("ANALYZE: planner statistics updated")
    except psycopg2.Error as e:
        print("\nERROR -> ROLLBACK, nothing was loaded.")
        print("  ", type(e).__name__, ":", str(e).strip().splitlines()[0])

    # Show what is really in the database now (proves the commit or the rollback).
    with conn.cursor() as cur:
        for table in ["competitions", "clubs", "players", "games",
                      "appearances", "player_valuations"]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"  {table:18s} {cur.fetchone()[0]:>9,} rows in the database")
    conn.close()

    print("\nCleaning rules (rows affected):")
    for rule in sorted(rules):          # R2, R3, ... (R10 never happened: 0 rows)
        print(f"  {rules[rule]:>9,}  {rule}")


if __name__ == "__main__":
    main(fail_on_purpose="--fail" in sys.argv)
