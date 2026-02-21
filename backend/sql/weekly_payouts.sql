CREATE TABLE IF NOT EXISTS weekly_payouts (
  payout_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  season_key    TEXT    NOT NULL,
  week_num      INTEGER NOT NULL,
  player_id     INTEGER NOT NULL,
  amount        REAL    NOT NULL,
  payout_type   TEXT    NOT NULL,
  note          TEXT,
  created_at    TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_weekly_payouts_season_week
ON weekly_payouts(season_key, week_num);

CREATE INDEX IF NOT EXISTS idx_weekly_payouts_season_player
ON weekly_payouts(season_key, player_id);