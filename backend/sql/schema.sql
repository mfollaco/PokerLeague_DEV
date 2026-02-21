PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS seasons (
  season_id TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS players (
  player_id INTEGER PRIMARY KEY,
  player_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS tournaments (
  tournament_id INTEGER PRIMARY KEY,
  season_id TEXT NOT NULL,
  tournament_date TEXT NOT NULL,
  source_file TEXT,
  created_ts TEXT DEFAULT (datetime('now')),
  UNIQUE(season_id, tournament_date),
  FOREIGN KEY (season_id) REFERENCES seasons(season_id)
);

CREATE TABLE IF NOT EXISTS weekly_points (
  weekly_points_id INTEGER PRIMARY KEY AUTOINCREMENT,
  season_id TEXT NOT NULL,
  week_num INTEGER NOT NULL,
  player_id INTEGER NOT NULL,
  finish_place INTEGER,
  points REAL NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (player_id) REFERENCES players(player_id)
);

CREATE INDEX IF NOT EXISTS idx_weekly_points_season_week
ON weekly_points(season_id, week_num);

CREATE INDEX IF NOT EXISTS idx_weekly_points_season_player
ON weekly_points(season_id, player_id);

CREATE TABLE IF NOT EXISTS season_totals (
  season_totals_id INTEGER PRIMARY KEY AUTOINCREMENT,
  season_id TEXT NOT NULL,
  player_id INTEGER NOT NULL,

  weeks_played INTEGER NOT NULL,
  total_points REAL NOT NULL,
  dropped_points REAL NOT NULL,
  net_points REAL NOT NULL,

  avg_finish REAL,
  wins INTEGER DEFAULT 0,

  created_at TEXT DEFAULT (datetime('now')),

  FOREIGN KEY (season_id) REFERENCES seasons(season_id),
  FOREIGN KEY (player_id) REFERENCES players(player_id)
);

CREATE INDEX IF NOT EXISTS idx_season_totals_season_player
ON season_totals(season_id, player_id);

CREATE TABLE IF NOT EXISTS raw_log_events (
  raw_event_id INTEGER PRIMARY KEY,
  tournament_id INTEGER NOT NULL,
  event_ts TEXT,
  event_type TEXT NOT NULL,
  player_name TEXT,
  eliminated_player_name TEXT,
  eliminator_player_name TEXT,
  position INTEGER,
  notes TEXT,
  FOREIGN KEY (tournament_id) REFERENCES tournaments(tournament_id)
);

CREATE TABLE IF NOT EXISTS weekly_payouts (
  payout_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  season_id     TEXT    NOT NULL,     -- matches seasons.season_id (ex: "spring_2026")
  week_num      INTEGER NOT NULL,     -- 1..N
  player_id     INTEGER NOT NULL,     -- matches players.player_id
  amount        REAL    NOT NULL,     -- positive dollars
  payout_type   TEXT    NOT NULL,     -- "1st", "2nd", "Bounty", etc.
  note          TEXT,
  created_at    TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (season_id) REFERENCES seasons(season_id),
  FOREIGN KEY (player_id) REFERENCES players(player_id)
);

CREATE INDEX IF NOT EXISTS idx_weekly_payouts_season_week
ON weekly_payouts(season_id, week_num);

CREATE INDEX IF NOT EXISTS idx_weekly_payouts_season_player
ON weekly_payouts(season_id, player_id);