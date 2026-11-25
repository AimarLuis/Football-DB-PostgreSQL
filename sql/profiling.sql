-- =====================================================================
-- Step 1b - Data profile, written in SQL over the staging schema "raw"
-- (every column is TEXT, exactly as in the CSV files).
-- Run them all with:  python run_profile.py   (or one by one in pgAdmin)
-- Each block starts with "-- P<n>: title" and ends with a semicolon.
-- x::int means CAST(x AS INTEGER): the raw columns are text, so numbers
-- must be converted before MIN / MAX / comparisons.
-- =====================================================================

-- P1: Row count of every file
SELECT 'appearances' AS file, COUNT(*) AS n_rows FROM raw.appearances
UNION ALL SELECT 'club_games', COUNT(*) FROM raw.club_games
UNION ALL SELECT 'clubs', COUNT(*) FROM raw.clubs
UNION ALL SELECT 'competitions', COUNT(*) FROM raw.competitions
UNION ALL SELECT 'countries', COUNT(*) FROM raw.countries
UNION ALL SELECT 'game_events', COUNT(*) FROM raw.game_events
UNION ALL SELECT 'game_lineups', COUNT(*) FROM raw.game_lineups
UNION ALL SELECT 'games', COUNT(*) FROM raw.games
UNION ALL SELECT 'national_teams', COUNT(*) FROM raw.national_teams
UNION ALL SELECT 'player_valuations', COUNT(*) FROM raw.player_valuations
UNION ALL SELECT 'players', COUNT(*) FROM raw.players
UNION ALL SELECT 'transfers', COUNT(*) FROM raw.transfers;

-- P2: Candidate keys: are they really unique? (n_rows = n_distinct -> unique)
SELECT 'competitions(competition_id)' AS candidate_key, COUNT(*) AS n_rows,
       COUNT(DISTINCT competition_id) AS n_distinct, COUNT(*) - COUNT(competition_id) AS n_null
FROM raw.competitions
UNION ALL SELECT 'clubs(club_id)', COUNT(*), COUNT(DISTINCT club_id), COUNT(*) - COUNT(club_id) FROM raw.clubs
UNION ALL SELECT 'players(player_id)', COUNT(*), COUNT(DISTINCT player_id), COUNT(*) - COUNT(player_id) FROM raw.players
UNION ALL SELECT 'games(game_id)', COUNT(*), COUNT(DISTINCT game_id), COUNT(*) - COUNT(game_id) FROM raw.games
UNION ALL SELECT 'appearances(appearance_id)', COUNT(*), COUNT(DISTINCT appearance_id), COUNT(*) - COUNT(appearance_id) FROM raw.appearances
UNION ALL SELECT 'appearances(game_id, player_id)', COUNT(*), COUNT(DISTINCT game_id || '_' || player_id), 0 FROM raw.appearances
UNION ALL SELECT 'player_valuations(player_id, date)', COUNT(*), COUNT(DISTINCT player_id || '_' || date), 0 FROM raw.player_valuations
UNION ALL SELECT 'players(name)  <- NOT a key', COUNT(*), COUNT(DISTINCT name), COUNT(*) - COUNT(name) FROM raw.players
UNION ALL SELECT 'club_games(game_id, club_id)', COUNT(*), COUNT(DISTINCT game_id || '_' || club_id), 0 FROM raw.club_games
UNION ALL SELECT 'game_lineups(game_lineups_id)', COUNT(*), COUNT(DISTINCT game_lineups_id), 0 FROM raw.game_lineups;

-- P3: appearance_id is just game_id + '_' + player_id (so it adds nothing)
SELECT COUNT(*) AS n_rows,
       SUM(CASE WHEN appearance_id = game_id || '_' || player_id THEN 1 ELSE 0 END) AS built_from_game_and_player
FROM raw.appearances;

-- P4: Competitions by type (only domestic leagues are kept, see rule R8 in load.py)
SELECT type, COUNT(*) AS n_competitions FROM raw.competitions GROUP BY type ORDER BY n_competitions DESC;

-- P5: Games by competition type (empty type = competition not in competitions.csv)
SELECT c.type AS competition_type, COUNT(*) AS n_games
FROM raw.games g LEFT JOIN raw.competitions c ON c.competition_id = g.competition_id
GROUP BY c.type ORDER BY n_games DESC;

-- P6: Orphan clubs in games: home or away club not described in clubs.csv
SELECT c.type AS competition_type,
       COUNT(*) AS n_games,
       SUM(CASE WHEN NOT EXISTS (SELECT 1 FROM raw.clubs k WHERE k.club_id = g.home_club_id)
                  OR NOT EXISTS (SELECT 1 FROM raw.clubs k WHERE k.club_id = g.away_club_id)
                THEN 1 ELSE 0 END) AS games_with_unknown_club
FROM raw.games g LEFT JOIN raw.competitions c ON c.competition_id = g.competition_id
GROUP BY c.type ORDER BY n_games DESC;

-- P7: Other orphan references (foreign keys that point to nothing)
SELECT 'clubs.domestic_competition_id not in competitions' AS check_name, COUNT(*) AS n_rows
FROM raw.clubs k WHERE NOT EXISTS (SELECT 1 FROM raw.competitions c WHERE c.competition_id = k.domestic_competition_id)
UNION ALL
SELECT 'players.current_club_id not in clubs', COUNT(*)
FROM raw.players p WHERE NOT EXISTS (SELECT 1 FROM raw.clubs k WHERE k.club_id = p.current_club_id)
UNION ALL
SELECT 'appearances.player_id not in players', COUNT(*)
FROM raw.appearances a WHERE NOT EXISTS (SELECT 1 FROM raw.players p WHERE p.player_id = a.player_id)
UNION ALL
SELECT 'appearances.game_id not in games', COUNT(*)
FROM raw.appearances a WHERE NOT EXISTS (SELECT 1 FROM raw.games g WHERE g.game_id = a.game_id)
UNION ALL
SELECT 'player_valuations.player_id not in players', COUNT(*)
FROM raw.player_valuations v WHERE NOT EXISTS (SELECT 1 FROM raw.players p WHERE p.player_id = v.player_id);

-- P8: Redundant columns in appearances: date and competition repeat the game's ones
SELECT COUNT(*) AS n_rows,
       SUM(CASE WHEN a.date = g.date AND a.competition_id = g.competition_id THEN 1 ELSE 0 END) AS same_as_game,
       SUM(CASE WHEN a.player_club_id IN (g.home_club_id, g.away_club_id) THEN 1 ELSE 0 END) AS club_is_home_or_away
FROM raw.appearances a JOIN raw.games g ON g.game_id = a.game_id;

-- P9: club_games is games written twice (one row per club and game)
SELECT (SELECT COUNT(*) FROM raw.club_games) AS club_games_rows,
       (SELECT COUNT(*) * 2 FROM raw.games) AS games_rows_x2;

-- P10: Ranges of dates and numbers in games
SELECT MIN(date) AS first_date, MAX(date) AS last_date,
       MIN(season::int) AS first_season, MAX(season::int) AS last_season,
       MIN(home_club_goals::int) AS min_home_goals, MAX(home_club_goals::int) AS max_home_goals,
       MAX(away_club_goals::int) AS max_away_goals,
       MIN(attendance::int) AS min_attendance, MAX(attendance::int) AS max_attendance,
       SUM(CASE WHEN home_club_id = away_club_id THEN 1 ELSE 0 END) AS club_against_itself
FROM raw.games;

-- P11: Games per season (2024 and 2025 grow because new leagues were added)
SELECT season, COUNT(*) AS n_games FROM raw.games GROUP BY season ORDER BY season;

-- P12: Ranges in appearances
SELECT MIN(date) AS first_date, MAX(date) AS last_date,
       MIN(minutes_played::int) AS min_minutes, MAX(minutes_played::int) AS max_minutes,
       MAX(goals::int) AS max_goals, MAX(assists::int) AS max_assists,
       MAX(yellow_cards::int) AS max_yellow, MAX(red_cards::int) AS max_red
FROM raw.appearances;

-- P13: Ranges and formats in players (a date "1987-06-24 00:00:00" has 19 characters)
SELECT MIN(date_of_birth) AS oldest_birth, MAX(date_of_birth) AS youngest_birth,
       SUM(CASE WHEN LENGTH(date_of_birth) <> 19 THEN 1 ELSE 0 END) AS birth_other_format,
       MIN(height_in_cm::int) AS min_height, MAX(height_in_cm::int) AS max_height,
       SUM(CASE WHEN height_in_cm::int < 150 THEN 1 ELSE 0 END) AS height_below_150,
       MIN(last_season::int) AS min_last_season, MAX(last_season::int) AS max_last_season
FROM raw.players;

-- P14: Codes without a meaning: values of players.position and players.foot (empty = NULL)
SELECT 'position' AS column_name, position AS value, COUNT(*) AS n_rows
FROM raw.players GROUP BY position
UNION ALL
SELECT 'foot', foot, COUNT(*) FROM raw.players GROUP BY foot
ORDER BY column_name, n_rows DESC;

-- P15: Ranges in player_valuations
SELECT MIN(date) AS first_date, MAX(date) AS last_date,
       MIN(market_value_in_eur::numeric) AS min_value, MAX(market_value_in_eur::numeric) AS max_value,
       SUM(CASE WHEN market_value_in_eur::numeric = 0 THEN 1 ELSE 0 END) AS value_zero
FROM raw.player_valuations;

-- P16: Ranges and odd values in clubs
SELECT MIN(stadium_seats::int) AS min_seats, MAX(stadium_seats::int) AS max_seats,
       SUM(CASE WHEN stadium_seats::int = 0 THEN 1 ELSE 0 END) AS seats_zero,
       MIN(average_age::numeric) AS min_avg_age, MAX(average_age::numeric) AS max_avg_age,
       SUM(CASE WHEN average_age::numeric = 0 THEN 1 ELSE 0 END) AS avg_age_zero,
       SUM(CASE WHEN squad_size::int = 0 THEN 1 ELSE 0 END) AS squad_size_zero,
       COUNT(total_market_value) AS total_market_value_filled,
       MIN(last_season::int) AS min_last_season, MAX(last_season::int) AS max_last_season
FROM raw.clubs;

-- P17: Money stored as text with symbols in clubs.net_transfer_record (sample)
SELECT net_transfer_record, COUNT(*) AS n_rows
FROM raw.clubs GROUP BY net_transfer_record ORDER BY n_rows DESC LIMIT 5;

-- P18: players.market_value_in_eur equals the player's last valuation? (derived column)
WITH ordered AS (
    SELECT player_id, market_value_in_eur AS value,
           ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY date DESC) AS rn
    FROM raw.player_valuations)
SELECT COUNT(*) AS players,
       COUNT(p.market_value_in_eur) AS with_value,
       SUM(CASE WHEN p.market_value_in_eur::numeric = o.value::numeric THEN 1 ELSE 0 END) AS equal_to_last_valuation
FROM raw.players p LEFT JOIN ordered o ON o.player_id = p.player_id AND o.rn = 1;

-- P19: Unexpected: transfers dated in the future (planned loan returns / contract ends)
SELECT COUNT(*) AS n_transfers,
       SUM(CASE WHEN transfer_date > '2026-07-01' THEN 1 ELSE 0 END) AS dated_after_dataset_end,
       MAX(transfer_date) AS max_transfer_date
FROM raw.transfers;

-- P20: Candidate UNIQUE rule: does a club ever play two games on the same day?
SELECT COUNT(*) AS club_days_with_two_games
FROM (SELECT club_id, date
      FROM (SELECT home_club_id AS club_id, date FROM raw.games
            UNION ALL
            SELECT away_club_id, date FROM raw.games) AS club_games
      GROUP BY club_id, date
      HAVING COUNT(*) > 1) AS repeated;

-- P21: Maximum text lengths (to size the VARCHAR columns)
SELECT 'players.name' AS column_name, MAX(LENGTH(name)) AS max_length FROM raw.players
UNION ALL SELECT 'players.country_of_citizenship', MAX(LENGTH(country_of_citizenship)) FROM raw.players
UNION ALL SELECT 'players.sub_position', MAX(LENGTH(sub_position)) FROM raw.players
UNION ALL SELECT 'clubs.name', MAX(LENGTH(name)) FROM raw.clubs
UNION ALL SELECT 'clubs.stadium_name', MAX(LENGTH(stadium_name)) FROM raw.clubs
UNION ALL SELECT 'competitions.competition_id', MAX(LENGTH(competition_id)) FROM raw.competitions
UNION ALL SELECT 'competitions.name', MAX(LENGTH(name)) FROM raw.competitions
UNION ALL SELECT 'competitions.country_name', MAX(LENGTH(country_name)) FROM raw.competitions
UNION ALL SELECT 'games.round', MAX(LENGTH(round)) FROM raw.games
UNION ALL SELECT 'games.stadium', MAX(LENGTH(stadium)) FROM raw.games
UNION ALL SELECT 'games.referee', MAX(LENGTH(referee)) FROM raw.games;
