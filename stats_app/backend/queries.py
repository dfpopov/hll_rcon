"""SQL aggregation queries for stats_app.

Hand-written SQL (raw text()) for clarity and ability to use JSONB
operators that SQLAlchemy ORM doesn't express cleanly. Read-only.
"""
from typing import Optional, List
from sqlalchemy import text
from sqlalchemy.orm import Session

from weapon_classes import classify_weapon, all_class_names


# Whitelist mapping: API sort param → SQL expression.
SORT_COLUMNS = {
    "kills": "SUM(ps.kills)",
    "deaths": "SUM(ps.deaths)",
    "teamkills": "SUM(ps.teamkills)",
    "kd_ratio": "CAST(SUM(ps.kills) AS NUMERIC) / NULLIF(SUM(ps.deaths), 0)",
    "kpm": "AVG(ps.kills_per_minute)",
    "playtime": "SUM(ps.time_seconds)",
    "matches": "COUNT(DISTINCT ps.map_id)",
    "level": "MAX(ps.level)",
    "combat": "SUM(ps.combat)",
    "offense": "SUM(ps.offense)",
    "defense": "SUM(ps.defense)",
    "support": "SUM(ps.support)",
}

PERIOD_INTERVALS = {
    "7d": "7 days",
    "30d": "30 days",
    "90d": "90 days",
}

# Game mode → ILIKE pattern on map_name. Maps in HLL include the mode in their name.
GAME_MODES = {
    "warfare": "%warfare%",
    "offensive": "%offensive%",
    "skirmish": "%skirmish%",
}


def _build_filters(
    period: Optional[str],
    weapon: Optional[str],
    map_name: Optional[str],
    search: Optional[str] = None,
    game_mode: Optional[str] = None,
    weapon_class: Optional[str] = None,
    weapon_names_for_class: Optional[List[str]] = None,
) -> tuple[list[str], dict]:
    """Build WHERE clause parts and bound params from optional filters."""
    parts: list[str] = []
    params: dict = {}

    if period and period in PERIOD_INTERVALS:
        parts.append(f"m.start >= NOW() - INTERVAL '{PERIOD_INTERVALS[period]}'")

    if game_mode and game_mode.lower() in GAME_MODES:
        parts.append("m.map_name ILIKE :game_mode_pat")
        params["game_mode_pat"] = GAME_MODES[game_mode.lower()]

    if weapon:
        parts.append("ps.weapons ? :weapon")
        params["weapon"] = weapon

    # Weapon class: matches any weapon in the class. Uses ANY(:array) with jsonb ? operator.
    if weapon_class and weapon_names_for_class:
        parts.append("ps.weapons ?| :weapon_class_names")
        params["weapon_class_names"] = weapon_names_for_class

    if map_name:
        parts.append("m.map_name = :map_name")
        params["map_name"] = map_name

    if search:
        parts.append("ps.name ILIKE :search")
        params["search"] = f"%{search}%"

    return parts, params


def _expand_weapon_class(db: Session, weapon_class: Optional[str]) -> Optional[List[str]]:
    """Return all weapon names in the given class, or None if class is empty."""
    if not weapon_class:
        return None
    sql = text("""
        SELECT DISTINCT w
        FROM player_stats, jsonb_object_keys(weapons) AS w
        WHERE weapons IS NOT NULL
    """)
    all_weapons = [row[0] for row in db.execute(sql)]
    return [w for w in all_weapons if classify_weapon(w) == weapon_class]


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
    game_mode: Optional[str] = None,
    weapon_class: Optional[str] = None,
):
    sort_expr = SORT_COLUMNS.get(sort, SORT_COLUMNS["kills"])
    order_dir = "ASC" if order.lower() == "asc" else "DESC"

    class_weapons = _expand_weapon_class(db, weapon_class)
    where_parts, params = _build_filters(
        period, weapon, map_name, search, game_mode, weapon_class, class_weapons,
    )
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
            SUM(ps.time_seconds) AS total_seconds,
            SUM(ps.combat) AS combat,
            SUM(ps.offense) AS offense,
            SUM(ps.defense) AS defense,
            SUM(ps.support) AS support
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
    game_mode: Optional[str] = None,
    weapon_class: Optional[str] = None,
) -> int:
    class_weapons = _expand_weapon_class(db, weapon_class)
    where_parts, params = _build_filters(
        period, weapon, map_name, search, game_mode, weapon_class, class_weapons,
    )
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
    sql = text("SELECT DISTINCT map_name FROM map_history ORDER BY map_name")
    return [row[0] for row in db.execute(sql)]


def get_unique_weapons(db: Session) -> List[str]:
    sql = text("""
        SELECT DISTINCT w
        FROM player_stats, jsonb_object_keys(weapons) AS w
        WHERE weapons IS NOT NULL
        ORDER BY w
    """)
    return [row[0] for row in db.execute(sql)]


def get_weapon_classes_with_examples(db: Session) -> List[dict]:
    """Return weapon class list with example weapons per class for the UI."""
    weapons = get_unique_weapons(db)
    grouped: dict[str, list[str]] = {}
    for w in weapons:
        grouped.setdefault(classify_weapon(w), []).append(w)
    return [
        {"name": cn, "count": len(grouped.get(cn, [])), "examples": grouped.get(cn, [])[:5]}
        for cn in all_class_names() if cn in grouped
    ]
