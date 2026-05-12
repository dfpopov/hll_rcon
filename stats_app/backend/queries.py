"""SQL aggregation queries for stats_app.

Hand-written SQL (raw text()) for clarity and ability to use JSONB
operators that SQLAlchemy ORM doesn't express cleanly. Read-only.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session


# Whitelist mapping: API sort param → SQL expression.
# Prevents SQL injection through the sort query parameter.
SORT_COLUMNS = {
    "kills": "SUM(ps.kills)",
    "deaths": "SUM(ps.deaths)",
    "teamkills": "SUM(ps.teamkills)",
    "kd_ratio": "CAST(SUM(ps.kills) AS NUMERIC) / NULLIF(SUM(ps.deaths), 0)",
    "kpm": "AVG(ps.kills_per_minute)",
    "playtime": "SUM(ps.time_seconds)",
    "matches": "COUNT(DISTINCT ps.map_id)",
    "level": "MAX(ps.level)",
}


def top_players_count(db: Session) -> int:
    """Total number of distinct players in player_stats."""
    sql = text("SELECT COUNT(DISTINCT playersteamid_id) AS n FROM player_stats")
    return int(db.execute(sql).scalar() or 0)


def top_players(
    db: Session,
    sort: str = "kills",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
):
    """Aggregated all-time per-player stats with sortable ORDER BY.

    sort: must be a key in SORT_COLUMNS.
    order: 'desc' or 'asc'.
    """
    sort_expr = SORT_COLUMNS.get(sort, SORT_COLUMNS["kills"])
    order_dir = "ASC" if order.lower() == "asc" else "DESC"

    sql = text(f"""
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
        ORDER BY ({sort_expr}) {order_dir} NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    result = db.execute(sql, {"limit": limit, "offset": offset})
    return [dict(row._mapping) for row in result]
