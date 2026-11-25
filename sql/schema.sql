-- =====================================================================
-- Step 2 - Physical schema of the "football" database (PostgreSQL)
-- Run with:  python create_schema.py
-- The script can be run many times: it drops the tables first, in the
-- reverse order (children before parents), and creates them again in
-- the normal order (parents before children).
-- =====================================================================

DROP TABLE IF EXISTS golden_boot;
DROP TABLE IF EXISTS player_valuations;
DROP TABLE IF EXISTS appearances;
DROP TABLE IF EXISTS games;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS clubs;
DROP TABLE IF EXISTS competitions;

-- ---------------------------------------------------------------------
-- COMPETITIONS: leagues, cups and international tournaments (catalogue)
-- ---------------------------------------------------------------------
CREATE TABLE competitions (
    competition_id   VARCHAR(4)  PRIMARY KEY,          -- 'ES1', 'GB1', 'CL'... (max 4 chars)
    name             VARCHAR(60) NOT NULL,
    type             VARCHAR(30) NOT NULL
        CHECK (type IN ('domestic_league', 'domestic_cup', 'international_cup',
                        'national_team_competition', 'other')),
    country_name     VARCHAR(40),                      -- NULL for international competitions
    confederation    VARCHAR(20)
);

-- ---------------------------------------------------------------------
-- CLUBS
-- ---------------------------------------------------------------------
CREATE TABLE clubs (
    club_id                  INTEGER     PRIMARY KEY,
    name                     VARCHAR(70) NOT NULL,
    domestic_competition_id  VARCHAR(4)  REFERENCES competitions (competition_id),
    squad_size               SMALLINT    CHECK (squad_size >= 0),
    average_age              NUMERIC(3,1) CHECK (average_age BETWEEN 15 AND 45),
    foreigners_percentage    NUMERIC(4,1) CHECK (foreigners_percentage BETWEEN 0 AND 100),
    stadium_name             VARCHAR(60),
    stadium_seats            INTEGER     CHECK (stadium_seats > 0),
    last_season              SMALLINT    NOT NULL CHECK (last_season BETWEEN 1990 AND 2100)
);

-- ---------------------------------------------------------------------
-- PLAYERS
-- ---------------------------------------------------------------------
CREATE TABLE players (
    player_id               INTEGER     PRIMARY KEY,
    name                    VARCHAR(50) NOT NULL,
    date_of_birth           DATE        CHECK (date_of_birth > DATE '1950-01-01'),
    country_of_citizenship  VARCHAR(40),
    position                VARCHAR(10)
        CHECK (position IN ('Goalkeeper', 'Defender', 'Midfield', 'Attack')),
    sub_position            VARCHAR(25),
    foot                    VARCHAR(5)  CHECK (foot IN ('left', 'right', 'both')),
    height_cm               SMALLINT    CHECK (height_cm BETWEEN 150 AND 220),
    current_club_id         INTEGER     REFERENCES clubs (club_id),
    last_season             SMALLINT    NOT NULL CHECK (last_season BETWEEN 1990 AND 2100)
);

-- ---------------------------------------------------------------------
-- GAMES: one row per match (only domestic league matches are loaded)
-- ---------------------------------------------------------------------
CREATE TABLE games (
    game_id         INTEGER     PRIMARY KEY,
    competition_id  VARCHAR(4)  NOT NULL REFERENCES competitions (competition_id),
    season          SMALLINT    NOT NULL CHECK (season BETWEEN 1990 AND 2100),
    round           VARCHAR(30),
    game_date       DATE        NOT NULL,
    home_club_id    INTEGER     NOT NULL REFERENCES clubs (club_id),
    away_club_id    INTEGER     NOT NULL REFERENCES clubs (club_id),
    home_goals      SMALLINT    NOT NULL CHECK (home_goals >= 0),
    away_goals      SMALLINT    NOT NULL CHECK (away_goals >= 0),
    attendance      INTEGER     CHECK (attendance >= 0),
    stadium         VARCHAR(60),
    referee         VARCHAR(50),
    CHECK (home_club_id <> away_club_id),              -- a club cannot play against itself
    UNIQUE (home_club_id, game_date),                  -- a club plays at most one league game a day
    UNIQUE (away_club_id, game_date)
);

-- ---------------------------------------------------------------------
-- APPEARANCES: a player plays in a game for a club (N:N player-game)
-- ---------------------------------------------------------------------
CREATE TABLE appearances (
    game_id         INTEGER  NOT NULL REFERENCES games (game_id),
    player_id       INTEGER  NOT NULL REFERENCES players (player_id),
    club_id         INTEGER  NOT NULL REFERENCES clubs (club_id),
    minutes_played  SMALLINT NOT NULL CHECK (minutes_played BETWEEN 0 AND 150),
    goals           SMALLINT NOT NULL CHECK (goals >= 0),
    assists         SMALLINT NOT NULL CHECK (assists >= 0),
    yellow_cards    SMALLINT NOT NULL CHECK (yellow_cards BETWEEN 0 AND 2),
    red_cards       SMALLINT NOT NULL CHECK (red_cards BETWEEN 0 AND 1),
    PRIMARY KEY (game_id, player_id)                   -- a player appears once per game
);

-- ---------------------------------------------------------------------
-- PLAYER_VALUATIONS: market value history (weak entity of players)
-- ---------------------------------------------------------------------
CREATE TABLE player_valuations (
    player_id         INTEGER NOT NULL REFERENCES players (player_id),
    valuation_date    DATE    NOT NULL,
    market_value_eur  INTEGER NOT NULL CHECK (market_value_eur >= 0),  -- max 200,000,000 fits in INTEGER
    PRIMARY KEY (player_id, valuation_date)
);

-- ---------------------------------------------------------------------
-- GOLDEN_BOOT: top scorer(s) of every league season.
-- Not loaded from a file: it is filled by query Q10 (INSERT inside a
-- transaction). Justified redundancy: a stored "award history".
-- ---------------------------------------------------------------------
CREATE TABLE golden_boot (
    competition_id  VARCHAR(4) NOT NULL REFERENCES competitions (competition_id),
    season          SMALLINT   NOT NULL,
    player_id       INTEGER    NOT NULL REFERENCES players (player_id),
    goals           SMALLINT   NOT NULL CHECK (goals > 0),
    PRIMARY KEY (competition_id, season, player_id)    -- ties: several winners per season
);
