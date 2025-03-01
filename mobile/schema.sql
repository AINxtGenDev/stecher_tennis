-- schema.sql (updated with blocking period columns and new-player flag)
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    available INTEGER NOT NULL DEFAULT 1,
    rank INTEGER NOT NULL,
    unavailable_since DATETIME,
    block_challenger_until DATETIME,
    block_opponent_until DATETIME,
    is_new INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenger_id INTEGER NOT NULL,
    opponent_id INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    deadline DATETIME NOT NULL,
    resolved_at DATETIME,
    resolved INTEGER NOT NULL DEFAULT 0,
    result TEXT,  -- 'challenger_wins', 'opponent_wins', or 'not_happened'
    FOREIGN KEY (challenger_id) REFERENCES players(id),
    FOREIGN KEY (opponent_id) REFERENCES players(id)
);
