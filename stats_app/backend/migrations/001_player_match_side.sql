-- Materialized view: dominant side per (player, match) derived from KILL log lines.
--
-- For each (player1_steamid, map_id) pair, picks the side under which the
-- player accumulated the most kills in that match (handles rare team-switch
-- cases). Players with no KILL events for a match are absent — those matches
-- pre-date log_lines capture and the side cannot be inferred.
--
-- Apply:
--   psql -f 001_player_match_side.sql
-- Refresh after new matches (cron / post-match hook):
--   REFRESH MATERIALIZED VIEW CONCURRENTLY player_match_side;

DROP MATERIALIZED VIEW IF EXISTS player_match_side;

CREATE MATERIALIZED VIEW player_match_side AS
WITH side_kills AS (
    SELECT
        ll.player1_steamid                                       AS player_id,
        mh.id                                                    AS match_id,
        (regexp_matches(ll.raw, 'KILL: [^(]+\(([^/]+)/'))[1]    AS side,
        COUNT(*)                                                 AS kills
    FROM log_lines ll
    JOIN map_history mh
      ON ll.event_time BETWEEN mh.start AND mh.end
    WHERE ll.type = 'KILL'
      AND ll.player1_steamid IS NOT NULL
    GROUP BY ll.player1_steamid, mh.id, side
),
ranked AS (
    SELECT
        player_id, match_id, side, kills,
        ROW_NUMBER() OVER (
            PARTITION BY player_id, match_id
            ORDER BY kills DESC
        ) AS rn
    FROM side_kills
)
SELECT player_id, match_id, side, kills
FROM ranked
WHERE rn = 1;

-- PK-style unique index (required by REFRESH ... CONCURRENTLY)
CREATE UNIQUE INDEX idx_player_match_side_pk
    ON player_match_side (player_id, match_id);

-- Side filter lookups
CREATE INDEX idx_player_match_side_side
    ON player_match_side (side);

ANALYZE player_match_side;
