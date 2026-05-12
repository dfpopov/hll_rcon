"""SQL aggregation queries for stats_app.

Hand-written SQL (raw text()) for clarity and ability to use JSONB
operators that SQLAlchemy ORM doesn't express cleanly. Read-only.
"""
from typing import Optional, List
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

# Period → PostgreSQL INTERVAL literal. None disables the filter.
PERIOD_INTERVALS = {
    "7d": "7 days",
    "30d": "30 days",
    "90d": "90 days",
}


def _build_filters(
    period: Optional[str],
    weapon: Optional[str],
    map_name: Optional[str],
    search: Optional[str] = None,
) -> tuple[list[str], dict]:
    """Build WHERE clause parts and bound params from optional filters."""
    parts: list[str] = []
    params: dict = {}

    if period and period in PERIOD_INTERVALS:
        # PostgreSQL doesn't bind INTERVAL — embed safely via dict lookup (no user input).
        parts.append(f"m.start >= NOW() - INTERVAL '{PERIOD_INTERVALS[period]}'")

    if weapon:
        parts.append("ps.weapons ? :weapon")
        params["weapon"] = weapon

    if map_name:
        parts.append("m.map_name = :map_name")
        params["map_name"] = map_name

    if search:
        # ILIKE = case-insensitive LIKE. Adds % wildcards for "contains" match.
        parts.append("ps.name ILIKE :search")
        params["search"] = f"%{search}%"

    return parts, params


def top_players(
    db: Session,
    sort: str = "kills",
    order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    min_matches: int = 50,
    period: Optional[str] = None,
    weapon: Optional[str] = None,
    map_name: Optional[str] = None,
    search: Optional[str] = None,
):
    """Aggregated all-time per-player stats with sortable ORDER BY + filters."""
    sort_expr = SORT_COLUMNS.get(sort, SORT_COLUMNS["kills"])
    order_dir = "ASC" if order.lower() == "asc" else "DESC"

    where_parts, params = _build_filters(period, weapon, map_name, search)
    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    params.update({"limit": limit, "offset": offset, "min_matches": min_matches})

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
        JOIN map_history m ON m.id = ps.map_id
        {where_clause}
        GROUP BY s.steam_id_64
        HAVING COUNT(DISTINCT ps.map_id) >= :min_matches
        ORDER BY ({sort_expr}) {order_dir} NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    result = db.execute(sql, params)
    return [dict(row._mapping) for row in result]


def top_players_count(
    db: Session,
    min_matches: int = 50,
    period: Optional[str] = None,
    weapon: Optional[str] = None,
    map_name: Optional[str] = None,
    search: Optional[str] = None,
) -> int:
    """Count players matching filters (for pagination total)."""
    where_parts, params = _build_filters(period, weapon, map_name, search)
    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    params["min_matches"] = min_matches

    sql = text(f"""
        SELECT COUNT(*) FROM (
            SELECT ps.playersteamid_id
            FROM player_stats ps
            JOIN map_history m ON m.id = ps.map_id
            {where_clause}
            GROUP BY ps.playersteamid_id
            HAVING COUNT(DISTINCT ps.map_id) >= :min_matches
        ) AS filtered
    """)
    return int(db.execute(sql, params).scalar() or 0)


def get_unique_maps(db: Session) -> List[str]:
    """Distinct map_name values (lots of formats: 'Stalingrad Warfare', etc.)."""
    sql = text("SELECT DISTINCT map_name FROM map_history ORDER BY map_name")
    return [row[0] for row in db.execute(sql)]


def get_unique_weapons(db: Session) -> List[str]:
    """All unique weapon names appearing as JSONB keys in player_stats.weapons."""
    sql = text("""
        SELECT DISTINCT w
        FROM player_stats, jsonb_object_keys(weapons) AS w
        WHERE weapons IS NOT NULL
        ORDER BY w
    """)
    return [row[0] for row in db.execute(sql)]
