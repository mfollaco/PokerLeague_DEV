import sqlite3

DB_PATH = "backend/db/pokerleague.sqlite"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Rebuild eliminations deterministically from raw_log_events
    cur.execute("DELETE FROM eliminations;")

    # For 'Eliminated' events in raw_log_events:
    # - player_name is the eliminated player (victim)
    # - eliminator_player_name is the killer
    # - eliminated_player_name is often blank, so we fall back to player_name.
    cur.execute("""
        INSERT INTO eliminations (
            tournament_id,
            event_ts,
            seq_in_tournament,
            eliminator_player_name,
            eliminated_player_name,
            raw_event_id,
            source_event_type,
            notes
        )
        SELECT
            r.tournament_id,
            r.event_ts,
            ROW_NUMBER() OVER (
                PARTITION BY r.tournament_id
                ORDER BY r.raw_event_id
            ) AS seq_in_tournament,
            r.eliminator_player_name,
            COALESCE(NULLIF(r.eliminated_player_name, ''), r.player_name) AS eliminated_player_name,
            r.raw_event_id,
            r.event_type AS source_event_type,
            r.notes
        FROM raw_log_events r
        WHERE r.event_type = 'Eliminated'
        AND r.eliminator_player_name IS NOT NULL
        AND r.eliminator_player_name <> ''
        AND COALESCE(NULLIF(r.eliminated_player_name, ''), r.player_name) IS NOT NULL
        AND COALESCE(NULLIF(r.eliminated_player_name, ''), r.player_name) <> '';
    """)

    conn.commit()

    # quick sanity
    rows = cur.execute("""
        SELECT tournament_id, COUNT(*) AS elim_events
        FROM eliminations
        GROUP BY tournament_id
        ORDER BY tournament_id;
    """).fetchall()

    print("✅ eliminations rebuilt:")
    for tid, n in rows:
        print(f"  tournament_id={tid} rows={n}")

    conn.close()

if __name__ == "__main__":
    main()