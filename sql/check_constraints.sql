-- =====================================================================
-- Step 6 - After the load: are all the constraints still there, and
-- does the data really respect them? (open this file in pgAdmin too)
-- information_schema is the standard SQL catalogue: tables that describe
-- the tables. PostgreSQL shows NOT NULL as a CHECK named "..._not_null".
-- =====================================================================

-- C1: every constraint of every table (with the condition of the CHECKs)
SELECT tc.table_name, tc.constraint_type, tc.constraint_name, cc.check_clause
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.check_constraints cc
       ON cc.constraint_schema = tc.constraint_schema
      AND cc.constraint_name   = tc.constraint_name
WHERE tc.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name;

-- C2: number of constraints of each kind per table
SELECT table_name, constraint_type, COUNT(*) AS n_constraints
FROM information_schema.table_constraints
WHERE table_schema = 'public'
GROUP BY table_name, constraint_type
ORDER BY table_name, constraint_type;

-- C3: rows per table after the load
SELECT 'competitions' AS table_name, COUNT(*) AS n_rows FROM competitions
UNION ALL SELECT 'clubs', COUNT(*) FROM clubs
UNION ALL SELECT 'players', COUNT(*) FROM players
UNION ALL SELECT 'games', COUNT(*) FROM games
UNION ALL SELECT 'appearances', COUNT(*) FROM appearances
UNION ALL SELECT 'player_valuations', COUNT(*) FROM player_valuations
UNION ALL SELECT 'golden_boot', COUNT(*) FROM golden_boot;

-- C4: rule that a simple FK cannot express (cross-table): the club of an
--     appearance must be the home or the away club of that game. Expected: 0
SELECT COUNT(*) AS appearances_with_wrong_club
FROM appearances a
JOIN games g ON g.game_id = a.game_id
WHERE a.club_id NOT IN (g.home_club_id, g.away_club_id);
