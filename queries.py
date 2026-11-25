"""The 10 SQL queries of the project (single source: used by run_queries.py
for the report and by app.py for the charts).

Every value chosen by the user travels as a PARAMETER (%(name)s): psycopg2
sends it as data, never as SQL text -> no SQL injection.

Note on seasons: season 2024 means the 2024/25 season (European leagues).
"""

# Helper queries for the app filters (not part of the 10).
LEAGUES = """
SELECT competition_id, country_name || ' - ' || name AS label
FROM competitions
WHERE type = 'domestic_league'
  AND competition_id IN (SELECT competition_id FROM games)
ORDER BY country_name;
"""

SEASONS = """
SELECT DISTINCT season FROM games
WHERE competition_id = %(competition)s
ORDER BY season DESC;
"""

PLAYER_SEARCH = """
SELECT p.player_id, p.name, p.date_of_birth
FROM players p
JOIN player_valuations v ON v.player_id = p.player_id
WHERE LOWER(p.name) LIKE LOWER(%(pattern)s)     -- case-insensitive search
GROUP BY p.player_id, p.name, p.date_of_birth
ORDER BY MAX(v.market_value_eur) DESC      -- best-known players first
LIMIT 50;
"""

QUERIES = {}

# ---------------------------------------------------------------- Q1
QUERIES["Q1"] = dict(
    author="Aimar Luis",
    title="League table",
    constructs="CTE (WITH), UNION ALL, JOIN, GROUP BY, CASE",
    question="What is the final table (points, wins, draws, losses, goals) of a league in a season?",
    why='It rebuilds the official standings only from match results (LaLiga 2024/25: Barcelona 88 points, Real Madrid 84), which also validates that the games table was loaded completely and correctly.',
    params={"competition": "ES1", "season": 2024},
    sql="""
WITH results AS (                       -- one row per club and game
    SELECT home_club_id AS club_id, home_goals AS goals_for, away_goals AS goals_against
    FROM games
    WHERE competition_id = %(competition)s AND season = %(season)s
    UNION ALL
    SELECT away_club_id, away_goals, home_goals
    FROM games
    WHERE competition_id = %(competition)s AND season = %(season)s
)
SELECT c.name                                                       AS club,
       COUNT(*)                                                     AS played,
       SUM(CASE WHEN r.goals_for > r.goals_against THEN 1 ELSE 0 END) AS won,
       SUM(CASE WHEN r.goals_for = r.goals_against THEN 1 ELSE 0 END) AS drawn,
       SUM(CASE WHEN r.goals_for < r.goals_against THEN 1 ELSE 0 END) AS lost,
       SUM(r.goals_for)                                             AS goals_for,
       SUM(r.goals_against)                                         AS goals_against,
       SUM(r.goals_for - r.goals_against)                           AS goal_difference,
       SUM(CASE WHEN r.goals_for > r.goals_against THEN 3
                WHEN r.goals_for = r.goals_against THEN 1
                ELSE 0 END)                                         AS points
FROM results r
JOIN clubs c ON c.club_id = r.club_id
GROUP BY c.club_id, c.name
ORDER BY points DESC, goal_difference DESC, goals_for DESC;
""")

# ---------------------------------------------------------------- Q2
QUERIES["Q2"] = dict(
    author="Telmo Lopez",
    title="Top scorers",
    constructs="JOIN of 4 tables, GROUP BY with HAVING",
    question="Who scored at least N goals in a league season, and how efficient were they (goals per 90 minutes)?",
    why='It ranks strikers not only by goals but by goals per 90 minutes, so a super-sub such as Sorloth (1.15) stands out next to the top scorer Mbappe (0.96).',
    params={"competition": "ES1", "season": 2024, "min_goals": 10},
    sql="""
SELECT p.name                                                         AS player,
       c.name                                                         AS club,
       SUM(a.goals)                                                   AS goals,
       SUM(a.assists)                                                 AS assists,
       COUNT(*)                                                       AS games,
       SUM(a.minutes_played)                                          AS minutes,
       ROUND(SUM(a.goals) * 90.0 / SUM(a.minutes_played), 2)          AS goals_per_90
FROM appearances a
JOIN games   g ON g.game_id   = a.game_id
JOIN players p ON p.player_id = a.player_id
JOIN clubs   c ON c.club_id   = a.club_id
WHERE g.competition_id = %(competition)s AND g.season = %(season)s
GROUP BY p.player_id, p.name, c.name
HAVING SUM(a.goals) >= %(min_goals)s
   AND SUM(a.minutes_played) > 0               -- avoids dividing by zero above
ORDER BY goals DESC, minutes ASC;
""")

# ---------------------------------------------------------------- Q3
QUERIES["Q3"] = dict(
    author="Aimar Luis",
    title="Market value history of a player",
    constructs="Window function LAG",
    question="How has the market value of a player changed over time, and how much did it change at each valuation?",
    why="LAG turns a list of valuations into increments, showing exactly when a player's value exploded (Mbappe: +55 M EUR in one valuation in 2017).",
    params={"player_id": 342229},
    sql="""
SELECT v.valuation_date,
       v.market_value_eur,
       v.market_value_eur
         - LAG(v.market_value_eur) OVER (ORDER BY v.valuation_date) AS change_eur
FROM player_valuations v
WHERE v.player_id = %(player_id)s
ORDER BY v.valuation_date;
""")

# ---------------------------------------------------------------- Q4
QUERIES["Q4"] = dict(
    author="Telmo Lopez",
    title="Home advantage by league",
    constructs="JOIN, GROUP BY with HAVING, CASE",
    question="In which leagues does the home team win most often (home win / draw / away win %), between two seasons?",
    why='It measures home advantage with the same rule in every league, so leagues can be compared (Norway and Brazil above 49 % home wins vs about 46 % in Spain).',
    params={"season_from": 2012, "season_to": 2025},
    sql="""
SELECT co.country_name || ' - ' || co.name AS league,
       COUNT(*) AS games,
       ROUND(100.0 * SUM(CASE WHEN g.home_goals > g.away_goals THEN 1 ELSE 0 END) / COUNT(*), 1) AS home_win_pct,
       ROUND(100.0 * SUM(CASE WHEN g.home_goals = g.away_goals THEN 1 ELSE 0 END) / COUNT(*), 1) AS draw_pct,
       ROUND(100.0 * SUM(CASE WHEN g.home_goals < g.away_goals THEN 1 ELSE 0 END) / COUNT(*), 1) AS away_win_pct
FROM games g
JOIN competitions co ON co.competition_id = g.competition_id
WHERE g.season BETWEEN %(season_from)s AND %(season_to)s
GROUP BY co.competition_id, co.country_name, co.name
HAVING COUNT(*) >= 200                       -- leagues with too few games are not comparable
ORDER BY home_win_pct DESC;
""")

# ---------------------------------------------------------------- Q5
QUERIES["Q5"] = dict(
    author="Aimar Luis",
    title="Most valuable players by position",
    constructs="Two CTEs, window functions ROW_NUMBER and RANK, subquery, JOIN",
    question="Who are the N most valuable active players of each position in a league, using each player's latest valuation?",
    why="It answers a scouting question ('who are the most valuable players per position right now?') and shows ties correctly thanks to RANK (three defenders share 3rd place).",
    params={"competition": "GB1", "top_n": 3},
    sql="""
WITH latest AS (                -- latest valuation of every player
    SELECT player_id, market_value_eur, valuation_date,
           ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY valuation_date DESC) AS rn
    FROM player_valuations
),
ranked AS (                     -- rank players inside their position
    SELECT p.position, p.name AS player, c.name AS club,
           l.market_value_eur, l.valuation_date,
           RANK() OVER (PARTITION BY p.position ORDER BY l.market_value_eur DESC) AS position_rank
    FROM latest l
    JOIN players p ON p.player_id = l.player_id
    JOIN clubs   c ON c.club_id   = p.current_club_id
    WHERE l.rn = 1
      AND p.position IS NOT NULL
      AND c.domestic_competition_id = %(competition)s
      AND p.last_season = (SELECT MAX(last_season) FROM players)   -- still active
)
SELECT position, position_rank, player, club, market_value_eur, valuation_date
FROM ranked
WHERE position_rank <= %(top_n)s
ORDER BY position, position_rank;
""")

# ---------------------------------------------------------------- Q6
QUERIES["Q6"] = dict(
    author="Telmo Lopez",
    title="Goals per game over the seasons",
    constructs="JOIN, GROUP BY, AVG, list parameter with ANY",
    question="How has the average number of goals per game evolved season by season in the selected leagues?",
    why='It shows whether football is becoming more or less offensive over time and how leagues differ, using more than 60,000 games.',
    params={"competitions": ["ES1", "GB1", "IT1", "L1", "FR1"]},
    sql="""
SELECT g.season,
       co.country_name || ' - ' || co.name     AS league,
       ROUND(AVG(g.home_goals + g.away_goals), 2) AS goals_per_game,
       COUNT(*)                                 AS games
FROM games g
JOIN competitions co ON co.competition_id = g.competition_id
WHERE g.competition_id = ANY(%(competitions)s)
GROUP BY g.season, co.country_name, co.name
ORDER BY league, g.season;
""")

# ---------------------------------------------------------------- Q7
QUERIES["Q7"] = dict(
    author="Telmo Lopez",
    title="Clubs above the league's average attendance",
    constructs="JOIN, GROUP BY with HAVING, subquery",
    question="Which clubs had a higher average home attendance than the average of their league in a season?",
    why='It separates the clubs that fill big stadiums from the rest of the league and puts the attendance next to the stadium capacity.',
    params={"competition": "L1", "season": 2024},
    sql="""
SELECT c.name                        AS club,
       ROUND(AVG(g.attendance))::int AS avg_attendance,   -- ::int = CAST(... AS INTEGER)
       c.stadium_seats,
       COUNT(*)                 AS home_games_with_attendance
FROM games g
JOIN clubs c ON c.club_id = g.home_club_id
WHERE g.competition_id = %(competition)s AND g.season = %(season)s
  AND g.attendance IS NOT NULL
GROUP BY c.club_id, c.name, c.stadium_seats
HAVING AVG(g.attendance) > (SELECT AVG(g2.attendance)          -- league average
                            FROM games g2
                            WHERE g2.competition_id = %(competition)s
                              AND g2.season = %(season)s)
ORDER BY avg_attendance DESC;
""")

# ---------------------------------------------------------------- Q8
QUERIES["Q8"] = dict(
    author="Telmo Lopez",
    title="Young players with most minutes",
    constructs="JOIN of 4 tables, date function EXTRACT, GROUP BY",
    question="Which players younger than a given age played the most minutes in a league season?",
    why='It identifies the young players who already have a key role in their team (LaLiga 2024/25: Lamine Yamal and Cubarsi, both 17, with more than 2,600 minutes).',
    params={"competition": "ES1", "season": 2024, "max_age": 21},
    sql="""
SELECT p.name                         AS player,
       c.name                         AS club,
       %(season)s - EXTRACT(YEAR FROM p.date_of_birth)::int AS age_in_season,  -- age in the season's year
       COUNT(*)                       AS games,
       SUM(a.minutes_played)          AS minutes,
       SUM(a.goals)                   AS goals,
       SUM(a.assists)                 AS assists
FROM appearances a
JOIN games   g ON g.game_id   = a.game_id
JOIN players p ON p.player_id = a.player_id
JOIN clubs   c ON c.club_id   = a.club_id
WHERE g.competition_id = %(competition)s AND g.season = %(season)s
  AND %(season)s - EXTRACT(YEAR FROM p.date_of_birth) < %(max_age)s
GROUP BY p.player_id, p.name, c.name, p.date_of_birth
ORDER BY minutes DESC
LIMIT 15;
""")

# ---------------------------------------------------------------- Q9
QUERIES["Q9"] = dict(
    author="Aimar Luis",
    title="Biggest goal improvement from the previous season",
    constructs="Two chained CTEs, window function LAG with PARTITION BY, JOIN",
    question="Which players improved their league goals the most compared with the previous season?",
    why='It finds the breakout players of a season by comparing each player with himself in the previous season, which a single GROUP BY cannot do.',
    params={"competition": "ES1", "season": 2024},
    sql="""
WITH season_goals AS (          -- goals of every player in every season of the league
    SELECT a.player_id, g.season, SUM(a.goals) AS goals
    FROM appearances a
    JOIN games g ON g.game_id = a.game_id
    WHERE g.competition_id = %(competition)s
    GROUP BY a.player_id, g.season
),
with_previous AS (              -- previous row of the same player
    SELECT player_id, season, goals,
           LAG(goals)  OVER (PARTITION BY player_id ORDER BY season) AS previous_goals,
           LAG(season) OVER (PARTITION BY player_id ORDER BY season) AS previous_season
    FROM season_goals
)
SELECT p.name                       AS player,
       w.previous_goals,
       w.goals,
       w.goals - w.previous_goals   AS improvement
FROM with_previous w
JOIN players p ON p.player_id = w.player_id
WHERE w.season = %(season)s
  AND w.previous_season = w.season - 1        -- consecutive seasons only
ORDER BY improvement DESC, w.goals DESC
LIMIT 10;
""")

# ---------------------------------------------------------------- Q10
QUERIES["Q10"] = dict(
    author="Aimar Luis",
    title="Golden Boot winners (INSERT inside a transaction)",
    constructs="DELETE + INSERT ... SELECT inside one transaction, CTE, window function RANK",
    question="Who was the top scorer (Golden Boot) of every league season? The winners are stored in table golden_boot.",
    why='Storing the award history once (DELETE + INSERT in one transaction, all or nothing) lets the app read it instantly; the winners match the real Pichichi list (Messi 46 in 2012/13, Ronaldo 48 in 2014/15).',
    params={"competition": "ES1"},
    # Part 1: run once by run_queries.py inside ONE transaction (BEGIN ... COMMIT).
    dml="""
BEGIN;
DELETE FROM golden_boot;        -- the script can be run again: start from an empty table
INSERT INTO golden_boot (competition_id, season, player_id, goals)
WITH scorer_goals AS (
    SELECT g.competition_id, g.season, a.player_id, SUM(a.goals) AS goals
    FROM appearances a
    JOIN games g ON g.game_id = a.game_id
    GROUP BY g.competition_id, g.season, a.player_id
),
ranked AS (
    SELECT competition_id, season, player_id, goals,
           RANK() OVER (PARTITION BY competition_id, season ORDER BY goals DESC) AS rnk
    FROM scorer_goals
)
SELECT competition_id, season, player_id, goals
FROM ranked
WHERE rnk = 1 AND goals > 0;    -- RANK keeps ties: two players can share the award
COMMIT;
""",
    # Part 2: what the app shows.
    sql="""
SELECT gb.season,
       STRING_AGG(p.name, ' / ') AS winners,    -- joins the names of tied winners
       MAX(gb.goals)                            AS goals
FROM golden_boot gb
JOIN players p ON p.player_id = gb.player_id
WHERE gb.competition_id = %(competition)s
GROUP BY gb.season
ORDER BY gb.season;
""")
