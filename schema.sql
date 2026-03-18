-- schema.sql
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS challenges;
DROP VIEW IF EXISTS completed_challenges_view;

CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    privilege_level TEXT NOT NULL DEFAULT 'player',
    -- NEW: This flag determines if a user appears in the pyramid. Default is 1 (true).
    is_ranked_player INTEGER NOT NULL DEFAULT 1,
    available INTEGER NOT NULL DEFAULT 1,
    rank INTEGER NOT NULL,
    unavailable_since DATETIME,
    unavailability_reason TEXT,
    block_challenger_until DATETIME,
    block_opponent_until DATETIME,
    is_new INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenger_id INTEGER NOT NULL,
    opponent_id INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    deadline DATETIME NOT NULL,
    resolved_at DATETIME,
    resolved INTEGER NOT NULL DEFAULT 0,
    result TEXT,
    score_details TEXT,
    scheduled_play_date DATETIME,
    FOREIGN KEY (challenger_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (opponent_id) REFERENCES players(id) ON DELETE CASCADE
);

CREATE VIEW completed_challenges_view AS
SELECT
    c.id,
    c.challenger_id,
    c.opponent_id,
    p1.name as challenger_name,
    p2.name as opponent_name,
    c.timestamp,
    c.deadline,
    c.resolved_at,
    c.result,
    c.score_details,
    c.scheduled_play_date
FROM challenges c
JOIN players p1 ON c.challenger_id = p1.id
JOIN players p2 ON c.opponent_id = p2.id
WHERE c.resolved = 1
ORDER BY c.resolved_at DESC;

CREATE TABLE app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_players_rank ON players(rank);
CREATE INDEX IF NOT EXISTS idx_challenges_resolved ON challenges(resolved);
CREATE INDEX IF NOT EXISTS idx_challenges_deadline ON challenges(deadline);