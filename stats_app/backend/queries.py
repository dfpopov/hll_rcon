"""SQL aggregation queries for stats_app.

Hand-written SQL (raw) for clarity and ability to leverage JSONB operators
that SQLAlchemy ORM doesn't express cleanly. All queries are read-only.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session


def top_kills(db: Session, limit: int = 50):
    """Top players ranked by total kills across all matches.

    Returns list of dicts with steam_id, name, level, kills, deaths,
    kd_ratio, kpm, matches_played.
    """
    sql = text("""
        SELECT
            s.steam_id_64 AS steam_id,
            MAX(ps.name) AS name,
            MAX(ps.level) AS level,
            SUM(ps.kills) AS kills,
            SUM(ps.deaths) AS deaths,
            SUM(ps.teamkills) AS teamkills,
            ROUND(
                CAST(SUM(ps.kills) AS NUMERIC) /
                NULLIF(SUM(ps.deaths), 0),
                2
            ) AS kd_ratio,
            ROUND(CAST(AVG(ps.kills_per_minute) AS NUMERIC), 2) AS kpm,
            COUNT(DISTINCT ps.map_id) AS matches_played,
            SUM(ps.time_seconds) AS total_seconds
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        GROUP BY s.steam_id_64
        ORDER BY kills DESC NULLS LAST
        LIMIT :limit
    """)
    result = db.execute(sql, {"limit": limit})
    return [dict(row._mapping) for row in result]
