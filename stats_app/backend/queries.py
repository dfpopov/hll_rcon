"""SQL aggregation queries for stats_app.

Hand-written SQL (raw text()) for clarity and ability to use JSONB
operators that SQLAlchemy ORM doesn't express cleanly. Read-only.
"""
from typing import Optional, List
from sqlalchemy import text
from sqlalchemy.orm import Session

from weapon_classes import classify_weapon, all_class_names
from achievements import compute_achievements, compute_achievement_progress, ACHIEVEMENTS
from theater_classifier import FACTIONS, maps_for_faction
from playstyles import (
    classify_one as classify_playstyle_one,
    get_cached_stats_or_compute,
    players_with_playstyle,
    _aggregate_cache,
)


# Whitelist mapping: API sort param → SQL expression.
SORT_COLUMNS = {
    "kills": "SUM(ps.kills)",
    "deaths": "SUM(ps.deaths)",
    "teamkills": "SUM(ps.teamkills)",
    "deaths_by_tk": "SUM(ps.deaths_by_tk)",
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

# Recognised values for the `side` filter — binary sides from player_match_side
# MV plus 5 factions derived from (side, theater) via theater_classifier.
SIDES = {"Allies", "Axis"}
SIDES_OR_FACTIONS = SIDES | FACTIONS


def _build_filters(
    period: Optional[str],
    weapon: Optional[str],
    map_name: Optional[str],
    search: Optional[str] = None,
    game_mode: Optional[str] = None,
    weapon_class: Optional[str] = None,
    weapon_names_for_class: Optional[List[str]] = None,
    side: Optional[str] = None,
    db: Optional[Session] = None,
) -> tuple[list[str], list[str], dict]:
    """Build (extra_joins, where_parts, params) from optional filters.

    Returned extra_joins are appended to the FROM clause; where_parts go into
    WHERE. Side filter joins player_match_side (matches without log coverage
    are silently excluded — we can't infer their side). When `side` is a
    faction (US/GB/USSR/Wehrmacht/DAK), the underlying side is derived from
    theater_classifier.FACTION_FILTERS and an extra `m.map_name = ANY(:...)`
    pin is added.
    """
    parts: list[str] = []
    joins: list[str] = []
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
        # Match against ANY of the player's historical names (alt names),
        # not just the latest. EXISTS subquery limited to the same player.
        parts.append(
            "EXISTS (SELECT 1 FROM player_stats ps_alt "
            "WHERE ps_alt.playersteamid_id = ps.playersteamid_id "
            "AND ps_alt.name ILIKE :search)"
        )
        params["search"] = f"%{search}%"

    if side in SIDES:
        joins.append(
            "JOIN player_match_side pms "
            "ON pms.player_id = s.id AND pms.match_id = ps.map_id"
        )
        parts.append("pms.side = :side")
        params["side"] = side
    elif side in FACTIONS and db is not None:
        # Faction → underlying side + map theater restriction.
        side_value, faction_maps = maps_for_faction(side, db)
        if side_value and faction_maps:
            joins.append(
                "JOIN player_match_side pms "
                "ON pms.player_id = s.id AND pms.match_id = ps.map_id"
            )
            parts.append("pms.side = :side AND m.map_name = ANY(:faction_maps)")
            params["side"] = side_value
            params["faction_maps"] = faction_maps
        else:
            # Faction is recognised but no maps in DB match — return zero rows.
            parts.append("FALSE")

    return joins, parts, params


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
    side: Optional[str] = None,
):
    sort_expr = SORT_COLUMNS.get(sort, SORT_COLUMNS["kills"])
    order_dir = "ASC" if order.lower() == "asc" else "DESC"

    class_weapons = _expand_weapon_class(db, weapon_class)
    extra_joins, where_parts, params = _build_filters(
        period, weapon, map_name, search, game_mode, weapon_class, class_weapons, side, db,
    )
    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    extra_join_clause = "\n        ".join(extra_joins)

    params.update({"limit": limit, "offset": offset, "min_matches": min_matches})

    sql = text(f"""
        SELECT
            s.steam_id_64 AS steam_id,
            MAX(ps.name) AS name,
            MAX(ps.level) AS level,
            SUM(ps.kills) AS kills,
            SUM(ps.deaths) AS deaths,
            SUM(ps.teamkills) AS teamkills,
            SUM(ps.deaths_by_tk) AS deaths_by_tk,
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
            SUM(ps.support) AS support,
            MAX(si.profile->>'avatarmedium') AS avatar_url,
            MAX(si.country) AS country
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        JOIN map_history m ON m.id = ps.map_id
        LEFT JOIN steam_info si ON si.playersteamid_id = s.id
        {extra_join_clause}
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
    side: Optional[str] = None,
) -> int:
    class_weapons = _expand_weapon_class(db, weapon_class)
    extra_joins, where_parts, params = _build_filters(
        period, weapon, map_name, search, game_mode, weapon_class, class_weapons, side, db,
    )
    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    extra_join_clause = "\n            ".join(extra_joins)
    params["min_matches"] = min_matches

    # Side join needs s (steam_id_64 alias) for its ON clause — add LEFT JOIN even
    # when side is unused (cheap, on integer FK), keeps SQL shape stable.
    sql = text(f"""
        SELECT COUNT(*) FROM (
            SELECT ps.playersteamid_id
            FROM player_stats ps
            JOIN steam_id_64 s ON s.id = ps.playersteamid_id
            JOIN map_history m ON m.id = ps.map_id
            {extra_join_clause}
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
    """Weapons with > 0 total kills, sorted by usage descending.

    Filters out weapons that exist as jsonb keys but never accumulated kills
    (game data has ~100 such ghost entries). Sorting by usage puts common
    weapons at the top of the filter dropdown.
    """
    sql = text("""
        SELECT key AS w, SUM(value::int) AS total
        FROM player_stats, jsonb_each_text(weapons) AS kv(key, value)
        WHERE weapons IS NOT NULL
        GROUP BY key
        HAVING SUM(value::int) > 0
        ORDER BY total DESC
    """)
    return [row[0] for row in db.execute(sql)]


def _all_player_profiles(db: Session) -> List[dict]:
    """Fetch one aggregated profile per player. Used for achievement stats.
    Result is cached at the function level via lru_cache wrapper above the
    SQLAlchemy session boundary in caller — for simplicity here we just run it.
    """
    sql = text("""
        SELECT
            s.steam_id_64 AS steam_id,
            MAX(ps.name) AS name,
            MAX(ps.level) AS level,
            SUM(ps.kills) AS kills,
            SUM(ps.deaths) AS deaths,
            SUM(ps.teamkills) AS teamkills,
            SUM(ps.deaths_by_tk) AS deaths_by_tk,
            ROUND(CAST(SUM(ps.kills) AS NUMERIC) / NULLIF(SUM(ps.deaths), 0), 2) AS kd_ratio,
            COUNT(DISTINCT ps.map_id) AS matches_played,
            SUM(ps.time_seconds) AS total_seconds,
            SUM(ps.combat) AS combat,
            SUM(ps.offense) AS offense,
            SUM(ps.defense) AS defense,
            SUM(ps.support) AS support,
            MAX(ps.kills_streak) AS best_kills_streak,
            MAX(ps.longest_life_secs) AS longest_life_secs,
            MAX(si.profile->>'avatarmedium') AS avatar_url,
            MAX(si.country) AS country
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        LEFT JOIN steam_info si ON si.playersteamid_id = s.id
        GROUP BY s.steam_id_64
    """)
    return [dict(row._mapping) for row in db.execute(sql)]


def compute_achievement_stats(db: Session) -> List[dict]:
    """For each achievement, count how many players have earned it.

    Returns list of {id, title, icon, tier, earned_count, percentage,
    total_players}.
    """
    all_profiles = _all_player_profiles(db)
    total = len(all_profiles)
    counts: dict[str, int] = {}
    for p in all_profiles:
        for ach in compute_achievements(p):
            counts[ach["id"]] = counts.get(ach["id"], 0) + 1

    result = []
    for aid, title, icon, tier, description, _predicate in ACHIEVEMENTS:
        c = counts.get(aid, 0)
        result.append({
            "id": aid,
            "title": title,
            "icon": icon,
            "tier": tier,
            "description": description,
            "earned_count": c,
            "percentage": round(c / total * 100, 2) if total > 0 else 0.0,
            "total_players": total,
        })
    return result


def players_with_achievement(
    db: Session,
    achievement_id: str,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List players who earned a specific achievement.

    Sorted by relevant metric (e.g. kills for kill-based achievements).
    """
    # Map achievement_id → predicate + relevant sort key
    SORT_HINT = {
        "centurion":     "matches_played",
        "veteran":       "matches_played",
        "lifetime":      "matches_played",
        "sharpshooter":  "kd_ratio",
        "elite_sniper":  "kd_ratio",
        "centurion_k":   "kills",
        "killer_1k":     "kills",
        "killing_mach":  "kills",
        "reaper":        "kills",
        "unstoppable":   "best_kills_streak",
        "legendary_st":  "best_kills_streak",
        "god_mode":      "best_kills_streak",
        "marathon":      "total_seconds",
        "time_lord":     "total_seconds",
        "combat_master": "combat",
        "support_hero":  "support",
        "defender":      "defense",
        "attacker":      "offense",
        "elite":         "level",
        "legendary_lvl": "level",
        "mythic_lvl":    "level",
        "survivor":      "longest_life_secs",
        "tk_offender":   "teamkills",
        "clumsy":        "deaths_by_tk",
    }
    sort_key = SORT_HINT.get(achievement_id, "kills")

    pred = next((a[5] for a in ACHIEVEMENTS if a[0] == achievement_id), None)
    if pred is None:
        return {"count": 0, "total": 0, "results": []}

    all_profiles = _all_player_profiles(db)
    matching = [p for p in all_profiles if _safe_predicate(pred, p)]
    matching.sort(key=lambda p: (p.get(sort_key) or 0), reverse=True)
    paged = matching[offset:offset + limit]
    return {
        "count": len(paged),
        "total": len(matching),
        "limit": limit,
        "offset": offset,
        "sort_key": sort_key,
        "results": paged,
    }


def _safe_predicate(pred, profile) -> bool:
    try:
        return bool(pred(profile))
    except (TypeError, ValueError):
        return False


def head_to_head(db: Session, sid1: str, sid2: str) -> dict:
    """Direct PvP record between two players, derived from log_lines KILL events.

    Returns counts of kills in each direction plus the top weapon used.
    Useful for the Comparison page — "X killed Y 47 times with M1 Garand".
    Falls back to zeros when neither player has any KILL log lines against
    the other (e.g. they never met, or matches predate log capture).
    """
    sql_counts = text("""
        WITH ids AS (
          SELECT
            (SELECT id FROM steam_id_64 WHERE steam_id_64 = :sid1) AS p1,
            (SELECT id FROM steam_id_64 WHERE steam_id_64 = :sid2) AS p2
        )
        SELECT
          COUNT(*) FILTER (
            WHERE ll.player1_steamid = ids.p1 AND ll.player2_steamid = ids.p2
          ) AS p1_killed_p2,
          COUNT(*) FILTER (
            WHERE ll.player1_steamid = ids.p2 AND ll.player2_steamid = ids.p1
          ) AS p2_killed_p1
        FROM log_lines ll, ids
        WHERE ll.type = 'KILL'
          AND (
            (ll.player1_steamid = ids.p1 AND ll.player2_steamid = ids.p2) OR
            (ll.player1_steamid = ids.p2 AND ll.player2_steamid = ids.p1)
          )
    """)
    row = db.execute(sql_counts, {"sid1": sid1, "sid2": sid2}).fetchone()
    p1_killed_p2 = int(row.p1_killed_p2 or 0) if row else 0
    p2_killed_p1 = int(row.p2_killed_p1 or 0) if row else 0

    def _top_weapon(killer: str, victim: str) -> Optional[str]:
        sql = text("""
            WITH ids AS (
              SELECT
                (SELECT id FROM steam_id_64 WHERE steam_id_64 = :killer) AS k,
                (SELECT id FROM steam_id_64 WHERE steam_id_64 = :victim) AS v
            )
            SELECT ll.weapon AS w
            FROM log_lines ll, ids
            WHERE ll.type = 'KILL'
              AND ll.player1_steamid = ids.k
              AND ll.player2_steamid = ids.v
              AND ll.weapon IS NOT NULL
              AND ll.weapon NOT IN ('Unknown', '')
            GROUP BY ll.weapon
            ORDER BY COUNT(*) DESC
            LIMIT 1
        """)
        r = db.execute(sql, {"killer": killer, "victim": victim}).fetchone()
        return r.w if r else None

    return {
        "p1_killed_p2": p1_killed_p2,
        "p2_killed_p1": p2_killed_p1,
        "p1_top_weapon": _top_weapon(sid1, sid2) if p1_killed_p2 else None,
        "p2_top_weapon": _top_weapon(sid2, sid1) if p2_killed_p1 else None,
    }


def find_player_by_name(db: Session, name: str) -> Optional[str]:
    """Lookup steam_id by exact (then ILIKE) match on player name.
    Used to make PVP victim/killer names clickable. Returns None if not found.
    """
    if not name:
        return None
    # Try exact match first (faster, more correct for ambiguous cases)
    sql_exact = text("""
        SELECT s.steam_id_64
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        WHERE ps.name = :name
        GROUP BY s.steam_id_64
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """)
    row = db.execute(sql_exact, {"name": name}).fetchone()
    if row:
        return row[0]
    # Fallback to case-insensitive
    sql_ci = text("""
        SELECT s.steam_id_64
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        WHERE ps.name ILIKE :name
        GROUP BY s.steam_id_64
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """)
    row = db.execute(sql_ci, {"name": name}).fetchone()
    return row[0] if row else None


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


# ============================================================================
# Phase 3: Records page + Player detail
# ============================================================================

# Whitelist for single-game record metrics (avoids SQL injection on metric param)
SINGLE_GAME_METRICS = {
    "kills": "ps.kills",
    "deaths": "ps.deaths",
    "teamkills": "ps.teamkills",
    "combat": "ps.combat",
    "support": "ps.support",
    "offense": "ps.offense",
    "defense": "ps.defense",
    "kills_streak": "ps.kills_streak",
    "kill_death_ratio": "ps.kill_death_ratio",
    "kills_per_minute": "ps.kills_per_minute",
}


def best_single_game(
    db: Session,
    metric: str = "kills",
    limit: int = 20,
    side: Optional[str] = None,
):
    """Top single-game records: highest value of `metric` from any single match.

    Returns list of {steam_id, name, level, value, match_id, map_name, match_date}.
    """
    expr = SINGLE_GAME_METRICS.get(metric, SINGLE_GAME_METRICS["kills"])
    params: dict = {"limit": limit}
    side_join = ""
    side_where = ""
    if side in SIDES:
        side_join = (
            "JOIN player_match_side pms "
            "ON pms.player_id = s.id AND pms.match_id = ps.map_id"
        )
        side_where = "AND pms.side = :side"
        params["side"] = side
    elif side in FACTIONS:
        side_value, faction_maps = maps_for_faction(side, db)
        if side_value and faction_maps:
            side_join = (
                "JOIN player_match_side pms "
                "ON pms.player_id = s.id AND pms.match_id = ps.map_id"
            )
            side_where = "AND pms.side = :side AND m.map_name = ANY(:faction_maps)"
            params["side"] = side_value
            params["faction_maps"] = faction_maps
        else:
            side_where = "AND FALSE"

    # top_weapon: pick the most-used weapon for this player in this specific
    # match. Subquery scans the row's weapons jsonb. Skips matches with no
    # weapons data (returns NULL — UI shows "—").
    sql = text(f"""
        SELECT
            s.steam_id_64 AS steam_id,
            ps.name AS name,
            ps.level AS level,
            ({expr}) AS value,
            m.id AS match_id,
            m.map_name AS map_name,
            m.start AS match_date,
            (
              SELECT key
              FROM jsonb_each_text(ps.weapons) AS kv(key, val)
              WHERE ps.weapons IS NOT NULL AND val::int > 0
              ORDER BY val::int DESC
              LIMIT 1
            ) AS top_weapon
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        JOIN map_history m ON m.id = ps.map_id
        {side_join}
        WHERE ({expr}) IS NOT NULL
        {side_where}
        ORDER BY ({expr}) DESC NULLS LAST
        LIMIT :limit
    """)
    result = db.execute(sql, params)
    rows = []
    for row in result:
        d = dict(row._mapping)
        if d.get("match_date"):
            d["match_date"] = d["match_date"].isoformat()
        rows.append(d)
    return rows


def played_with_against(db: Session, steam_id: str, limit: int = 10) -> dict:
    """Per-player breakdown of frequent teammates vs opponents.

    Uses player_match_side MV to know which side each player was on per
    match — so only matches with log coverage contribute. Two lists each
    capped at `limit`. Output:
      {teammates: [{steam_id, name, matches}], opponents: [...]}
    """
    sql = text("""
        WITH my_sides AS (
          SELECT pms.match_id, pms.side AS my_side
          FROM player_match_side pms
          JOIN steam_id_64 s ON s.id = pms.player_id
          WHERE s.steam_id_64 = :sid
        ),
        teammates AS (
          SELECT s2.steam_id_64 AS steam_id, MAX(ps2.name) AS name, COUNT(*) AS matches
          FROM my_sides ms
          JOIN player_match_side pms2
            ON pms2.match_id = ms.match_id AND pms2.side = ms.my_side
          JOIN steam_id_64 s2 ON s2.id = pms2.player_id
          JOIN player_stats ps2 ON ps2.playersteamid_id = s2.id AND ps2.map_id = ms.match_id
          WHERE s2.steam_id_64 <> :sid
          GROUP BY s2.steam_id_64
          ORDER BY matches DESC
          LIMIT :limit
        ),
        opponents AS (
          SELECT s2.steam_id_64 AS steam_id, MAX(ps2.name) AS name, COUNT(*) AS matches
          FROM my_sides ms
          JOIN player_match_side pms2
            ON pms2.match_id = ms.match_id AND pms2.side <> ms.my_side
          JOIN steam_id_64 s2 ON s2.id = pms2.player_id
          JOIN player_stats ps2 ON ps2.playersteamid_id = s2.id AND ps2.map_id = ms.match_id
          WHERE s2.steam_id_64 <> :sid
          GROUP BY s2.steam_id_64
          ORDER BY matches DESC
          LIMIT :limit
        )
        SELECT 'teammate' AS kind, steam_id, name, matches FROM teammates
        UNION ALL
        SELECT 'opponent' AS kind, steam_id, name, matches FROM opponents
    """)
    teammates: list[dict] = []
    opponents: list[dict] = []
    for r in db.execute(sql, {"sid": steam_id, "limit": limit}):
        entry = {"steam_id": r.steam_id, "name": r.name, "matches": int(r.matches or 0)}
        if r.kind == "teammate":
            teammates.append(entry)
        else:
            opponents.append(entry)
    return {"teammates": teammates, "opponents": opponents}


# Melee weapons — narrow enough that hardcoding is fine. Updated from the
# classify_weapon rules. Used by melee_meta below to filter log_lines.
MELEE_WEAPONS = [
    "FELDSPATEN", "KNIFE", "M3 KNIFE", "BAYONET", "MELEE",
    "M3 FIGHTING KNIFE", "GERBER MARK II",
]


def melee_meta(db: Session, steam_id: str) -> dict:
    """Melee micro-stats: total kills/deaths + last melee death event +
    current streak of melee kills since the last melee death."""
    sql_last_death = text("""
        SELECT ll.weapon, ll.event_time, p1.steam_id_64 AS killer_sid, ll.raw,
               (SELECT m.map_name FROM map_history m
                WHERE ll.event_time BETWEEN m.start AND m.end LIMIT 1) AS map_name,
               (SELECT regexp_replace(ll.raw, '.*KILL: ([^(]+)\\(.*', '\\1')) AS killer_name
        FROM log_lines ll
        JOIN steam_id_64 s ON s.id = ll.player2_steamid
        LEFT JOIN steam_id_64 p1 ON p1.id = ll.player1_steamid
        WHERE ll.type = 'KILL'
          AND s.steam_id_64 = :sid
          AND ll.weapon = ANY(:melee)
        ORDER BY ll.event_time DESC
        LIMIT 1
    """)
    last_row = db.execute(sql_last_death, {"sid": steam_id, "melee": MELEE_WEAPONS}).fetchone()
    last_melee_death = None
    if last_row:
        last_melee_death = {
            "weapon": last_row.weapon,
            "event_time": last_row.event_time.isoformat() if last_row.event_time else None,
            "killer_sid": last_row.killer_sid,
            "killer_name": (last_row.killer_name or "").strip() or None,
            "map_name": last_row.map_name,
        }

    sql_streak = text("""
        WITH last_d AS (
          SELECT MAX(ll.event_time) AS t
          FROM log_lines ll
          JOIN steam_id_64 s ON s.id = ll.player2_steamid
          WHERE ll.type = 'KILL' AND s.steam_id_64 = :sid AND ll.weapon = ANY(:melee)
        )
        SELECT COUNT(*) AS streak
        FROM log_lines ll
        JOIN steam_id_64 s ON s.id = ll.player1_steamid, last_d
        WHERE ll.type = 'KILL'
          AND s.steam_id_64 = :sid
          AND ll.weapon = ANY(:melee)
          AND (last_d.t IS NULL OR ll.event_time > last_d.t)
    """)
    streak_row = db.execute(sql_streak, {"sid": steam_id, "melee": MELEE_WEAPONS}).fetchone()
    current_streak = int(streak_row.streak or 0) if streak_row else 0

    return {
        "last_melee_death": last_melee_death,
        "current_streak": current_streak,
    }


def playstyle_stats(db: Session) -> list[dict]:
    """Server-wide playstyle distribution. TTL-cached at 1h via playstyles.py
    module-level cache."""
    return get_cached_stats_or_compute(lambda: _all_player_profiles(db))


def playstyle_players(db: Session, playstyle_id: str, limit: int = 50, offset: int = 0) -> dict:
    """Players matching one playstyle, paginated. Reads from the same cache
    as playstyle_stats — re-classifies only if cache is cold."""
    # Re-use cached buckets if fresh; otherwise compute and update cache.
    cached = _aggregate_cache.get("buckets")
    import time as _time
    if cached is None or _time.time() - _aggregate_cache.get("computed_at", 0) >= 3600:
        # Force a refresh so subsequent paginated calls hit cache.
        get_cached_stats_or_compute(lambda: _all_player_profiles(db))
    # players_with_playstyle re-iterates _all_player_profiles since the cache
    # only holds samples, not the full bucket. Cost ~1-2s on prod for 28k.
    profiles = _all_player_profiles(db)
    return players_with_playstyle(profiles, playstyle_id, limit=limit, offset=offset)


def autocomplete_players(db: Session, q: str, limit: int = 10) -> list[dict]:
    """Player autocomplete: returns top matches by ILIKE substring against
    ANY historical name (player_stats.name). One row per steam_id with the
    canonical (most-recent / MAX) display name and avatar.
    Ordered by matches_played desc — typed prefix hits the active veterans
    first."""
    sql = text("""
        SELECT
          s.steam_id_64 AS steam_id,
          MAX(ps.name) AS name,
          MAX(si.profile->>'avatarmedium') AS avatar_url,
          COUNT(DISTINCT ps.map_id) AS matches
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        LEFT JOIN steam_info si ON si.playersteamid_id = s.id
        WHERE ps.name ILIKE :pattern
        GROUP BY s.steam_id_64
        ORDER BY matches DESC
        LIMIT :limit
    """)
    return [
        {
            "steam_id": r.steam_id,
            "name": r.name,
            "avatar_url": r.avatar_url,
            "matches": int(r.matches or 0),
        }
        for r in db.execute(sql, {"pattern": f"%{q}%", "limit": limit})
    ]


def country_distribution(db: Session) -> list[dict]:
    """Player count per country (ISO 3166-1 alpha-2) from steam_info.

    Aggregated over the whole population so this can power a server-wide
    world map. Returns sorted descending by player count, with percentage
    against the total known-country population.
    """
    # Steam stores 'private' (literal) for users with hidden profiles. Filter
    # to real 2-letter alpha-2 ISO codes only. Pattern matches A-Z exactly 2.
    sql = text("""
        SELECT
          UPPER(si.country) AS country,
          COUNT(DISTINCT si.playersteamid_id) AS players
        FROM steam_info si
        WHERE si.country IS NOT NULL
          AND LENGTH(si.country) = 2
          AND si.country ~ '^[A-Za-z]{2}$'
        GROUP BY UPPER(si.country)
        ORDER BY players DESC
    """)
    rows = list(db.execute(sql))
    total = sum(int(r.players or 0) for r in rows)
    return [
        {
            "country": r.country,
            "players": int(r.players or 0),
            "pct": round(int(r.players or 0) / total * 100, 2) if total > 0 else 0.0,
        }
        for r in rows
    ]


def hardcounters(db: Session, steam_id: str, min_deaths: int = 5, limit: int = 5) -> list[dict]:
    """Players who have a positive K/D against this player.

    For each player B who killed A at least `min_deaths` times in
    log_lines, computes A's reverse kill count against B. Returns those
    where B_killed_A > A_killed_B, sorted by net advantage descending.

    Useful as a meme-y counter to the leaderboard ("ось 5 гравців, які
    тебе ганяють"). Only works on players with substantial PVP history.
    """
    sql = text("""
        WITH me AS (
          SELECT id FROM steam_id_64 WHERE steam_id_64 = :sid
        ),
        they_killed_me AS (
          SELECT ll.player1_steamid AS killer_id, COUNT(*) AS times
          FROM log_lines ll, me
          WHERE ll.type = 'KILL'
            AND ll.player2_steamid = me.id
            AND ll.player1_steamid IS NOT NULL
            AND ll.player1_steamid <> me.id
          GROUP BY ll.player1_steamid
          HAVING COUNT(*) >= :min_deaths
        ),
        i_killed_them AS (
          SELECT ll.player2_steamid AS killer_id, COUNT(*) AS times
          FROM log_lines ll, me
          WHERE ll.type = 'KILL'
            AND ll.player1_steamid = me.id
            AND ll.player2_steamid IN (SELECT killer_id FROM they_killed_me)
          GROUP BY ll.player2_steamid
        )
        SELECT
          s.steam_id_64 AS steam_id,
          (SELECT MAX(ps.name) FROM player_stats ps WHERE ps.playersteamid_id = s.id) AS name,
          t.times AS killed_me,
          COALESCE(i.times, 0) AS i_killed_them,
          t.times - COALESCE(i.times, 0) AS advantage
        FROM they_killed_me t
        JOIN steam_id_64 s ON s.id = t.killer_id
        LEFT JOIN i_killed_them i ON i.killer_id = t.killer_id
        WHERE t.times > COALESCE(i.times, 0)
        ORDER BY advantage DESC, t.times DESC
        LIMIT :limit
    """)
    return [
        {
            "steam_id": r.steam_id,
            "name": r.name,
            "killed_me": int(r.killed_me or 0),
            "i_killed_them": int(r.i_killed_them or 0),
            "advantage": int(r.advantage or 0),
        }
        for r in db.execute(sql, {"sid": steam_id, "min_deaths": min_deaths, "limit": limit})
    ]


def best_single_game_by_class(
    db: Session,
    weapon_class: str,
    limit: int = 10,
) -> list[dict]:
    """Top single-game records filtered to one weapon class.

    For each (player, match) pair sums kills only from weapons that belong
    to the requested class. Returns the top-N matches by that class-kill
    sum, with the top weapon name within the class identified separately.
    """
    class_weapons = _expand_weapon_class(db, weapon_class)
    if not class_weapons:
        return []
    sql = text("""
        SELECT
            s.steam_id_64 AS steam_id,
            MAX(ps.name) AS name,
            MAX(ps.level) AS level,
            SUM(kv.val::int) AS value,
            m.id AS match_id,
            m.map_name AS map_name,
            m.start AS match_date,
            (
              SELECT key FROM jsonb_each_text(ps.weapons) AS kv2(key, val)
              WHERE kv2.key = ANY(:class_weapons) AND kv2.val::int > 0
              ORDER BY kv2.val::int DESC LIMIT 1
            ) AS top_weapon
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        JOIN map_history m ON m.id = ps.map_id,
             jsonb_each_text(ps.weapons) AS kv(key, val)
        WHERE ps.weapons IS NOT NULL
          AND kv.key = ANY(:class_weapons)
          AND kv.val::int > 0
        GROUP BY ps.id, s.steam_id_64, m.id, m.map_name, m.start
        ORDER BY value DESC NULLS LAST
        LIMIT :limit
    """)
    rows = []
    for row in db.execute(sql, {"class_weapons": class_weapons, "limit": limit}):
        d = dict(row._mapping)
        if d.get("match_date"):
            d["match_date"] = d["match_date"].isoformat()
        rows.append(d)
    return rows


def player_detail(db: Session, steam_id: str):
    """Aggregated all-time stats for a single player.

    Returns: {profile, top_weapons, most_killed, killed_by, recent_matches} or None.
    """
    # 1) Profile aggregation + steam_info join for avatar/country
    sql_profile = text("""
        SELECT
            s.steam_id_64 AS steam_id,
            MAX(ps.name) AS name,
            MAX(ps.level) AS level,
            SUM(ps.kills) AS kills,
            SUM(ps.deaths) AS deaths,
            SUM(ps.teamkills) AS teamkills,
            SUM(ps.deaths_by_tk) AS deaths_by_tk,
            ROUND(CAST(SUM(ps.kills) AS NUMERIC) / NULLIF(SUM(ps.deaths), 0), 2) AS kd_ratio,
            ROUND(CAST(AVG(ps.kills_per_minute) AS NUMERIC), 2) AS kpm,
            COUNT(DISTINCT ps.map_id) AS matches_played,
            SUM(ps.time_seconds) AS total_seconds,
            SUM(ps.combat) AS combat,
            SUM(ps.offense) AS offense,
            SUM(ps.defense) AS defense,
            SUM(ps.support) AS support,
            MAX(ps.kills_streak) AS best_kills_streak,
            MAX(ps.longest_life_secs) AS longest_life_secs,
            MAX(si.profile->>'avatarfull') AS avatar_url,
            MAX(si.profile->>'personaname') AS persona_name,
            MAX(si.profile->>'profileurl') AS profile_url,
            MAX(si.country) AS country
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        LEFT JOIN steam_info si ON si.playersteamid_id = s.id
        WHERE s.steam_id_64 = :sid
        GROUP BY s.steam_id_64
    """)
    profile_row = db.execute(sql_profile, {"sid": steam_id}).fetchone()
    if not profile_row:
        return None
    profile = dict(profile_row._mapping)
    achievements_list = compute_achievements(profile)

    # 2) Top weapons used (sum kills per weapon across all matches)
    # Top-N lists trimmed to 5 — PVP grid columns are narrow, top-10 was
    # forcing horizontal scroll on mobile and burying signal.
    sql_weapons = text("""
        SELECT key AS weapon, SUM(value::int) AS kills
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id,
             jsonb_each_text(ps.weapons)
        WHERE s.steam_id_64 = :sid AND ps.weapons IS NOT NULL
        GROUP BY key
        ORDER BY kills DESC
        LIMIT 5
    """)
    top_weapons = [dict(row._mapping) for row in db.execute(sql_weapons, {"sid": steam_id})]

    # 3) Most killed (victims) — PVP
    sql_killed = text("""
        SELECT key AS victim, SUM(value::int) AS kills
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id,
             jsonb_each_text(ps.most_killed)
        WHERE s.steam_id_64 = :sid AND ps.most_killed IS NOT NULL
        GROUP BY key
        ORDER BY kills DESC
        LIMIT 5
    """)
    most_killed = [dict(row._mapping) for row in db.execute(sql_killed, {"sid": steam_id})]

    # 4) Killed by (nemeses) — PVP reverse
    sql_killers = text("""
        SELECT key AS killer, SUM(value::int) AS deaths
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id,
             jsonb_each_text(ps.death_by)
        WHERE s.steam_id_64 = :sid AND ps.death_by IS NOT NULL
        GROUP BY key
        ORDER BY deaths DESC
        LIMIT 5
    """)
    killed_by = [dict(row._mapping) for row in db.execute(sql_killers, {"sid": steam_id})]

    # 5) Recent matches (last 10) — includes match_id for linking to /games/{id}.
    # Hide barely-played matches (kills=0 AND deaths<=1) — they're usually
    # spectator/disconnect noise, not real games.
    # time_pct = how much of the match this player was actually present:
    # ps.time_seconds / match_duration_seconds. Capped at 100 for cases
    # where the player's time slightly exceeds the recorded match window
    # (boundary noise).
    sql_recent = text("""
        SELECT
            m.id AS match_id,
            m.map_name AS map_name,
            m.start AS match_date,
            ps.kills AS kills,
            ps.deaths AS deaths,
            ps.kill_death_ratio AS kd,
            ps.combat AS combat,
            ps.support AS support,
            ps.time_seconds AS time_seconds,
            CASE
              WHEN m.end IS NOT NULL AND m.start IS NOT NULL
                   AND EXTRACT(EPOCH FROM (m.end - m.start)) > 0
              THEN LEAST(
                ROUND(
                  (CAST(ps.time_seconds AS NUMERIC) /
                   CAST(EXTRACT(EPOCH FROM (m.end - m.start)) AS NUMERIC)) * 100,
                  1
                ),
                100.0
              )
              ELSE NULL
            END AS time_pct
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        JOIN map_history m ON m.id = ps.map_id
        WHERE s.steam_id_64 = :sid
          AND NOT (COALESCE(ps.kills, 0) = 0 AND COALESCE(ps.deaths, 0) <= 1)
        ORDER BY m.start DESC NULLS LAST
        LIMIT 10
    """)
    recent_matches = []
    for row in db.execute(sql_recent, {"sid": steam_id}):
        d = dict(row._mapping)
        if d.get("match_date"):
            d["match_date"] = d["match_date"].isoformat()
        if d.get("time_pct") is not None:
            d["time_pct"] = float(d["time_pct"])
        recent_matches.append(d)

    # 6) Overview meta: first seen + 100+ kill matches + mode distribution.
    sql_overview = text("""
        SELECT
            MIN(m.start) AS first_seen,
            COUNT(*) FILTER (WHERE COALESCE(ps.kills, 0) >= 100) AS matches_100plus,
            COUNT(*) FILTER (WHERE m.map_name ILIKE '%warfare%') AS warfare,
            COUNT(*) FILTER (WHERE m.map_name ILIKE '%offensive%') AS offensive,
            COUNT(*) FILTER (WHERE m.map_name ILIKE '%skirmish%') AS skirmish,
            COUNT(*) AS total_matches
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        JOIN map_history m ON m.id = ps.map_id
        WHERE s.steam_id_64 = :sid
    """)
    ov = db.execute(sql_overview, {"sid": steam_id}).fetchone()
    overview = {
        "first_seen": ov.first_seen.isoformat() if ov and ov.first_seen else None,
        "matches_100plus": int(ov.matches_100plus or 0) if ov else 0,
        "mode_counts": {
            "warfare": int(ov.warfare or 0) if ov else 0,
            "offensive": int(ov.offensive or 0) if ov else 0,
            "skirmish": int(ov.skirmish or 0) if ov else 0,
        },
        "total_matches": int(ov.total_matches or 0) if ov else 0,
    }

    # 7) Top maps by matches played, with kills, K/D and win rate per map.
    # Win rate computed by joining the MV (player's side per match) and
    # map_history.result. Matches without log coverage or with NULL result
    # don't contribute to known_outcomes — win_pct reflects what's
    # attributable, not raw count.
    sql_top_maps = text("""
        SELECT
            m.map_name AS map_name,
            COUNT(*) AS matches,
            SUM(ps.kills) AS kills,
            ROUND(CAST(SUM(ps.kills) AS NUMERIC) / NULLIF(SUM(ps.deaths), 0), 2) AS kd,
            SUM(
              CASE
                WHEN pms.side = 'Allies' AND m.result IS NOT NULL
                     AND m.result ? 'Allied' AND m.result ? 'Axis'
                     AND (m.result->>'Allied')::int > (m.result->>'Axis')::int THEN 1
                WHEN pms.side = 'Axis' AND m.result IS NOT NULL
                     AND m.result ? 'Allied' AND m.result ? 'Axis'
                     AND (m.result->>'Axis')::int > (m.result->>'Allied')::int THEN 1
                ELSE 0
              END
            ) AS wins,
            SUM(
              CASE
                WHEN pms.side IS NOT NULL AND m.result IS NOT NULL
                     AND m.result ? 'Allied' AND m.result ? 'Axis' THEN 1
                ELSE 0
              END
            ) AS known_outcomes
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        JOIN map_history m ON m.id = ps.map_id
        LEFT JOIN player_match_side pms ON pms.player_id = s.id AND pms.match_id = m.id
        WHERE s.steam_id_64 = :sid
        GROUP BY m.map_name
        ORDER BY matches DESC
        LIMIT 10
    """)
    top_maps = []
    for r in db.execute(sql_top_maps, {"sid": steam_id}):
        d = dict(r._mapping)
        wins = int(d.pop("wins", 0) or 0)
        known = int(d.pop("known_outcomes", 0) or 0)
        d["win_pct"] = round(wins / known * 100, 1) if known > 0 else None
        d["known_outcomes"] = known
        top_maps.append(d)

    # 8) Faction preference from player_match_side MV. Matches without log
    # coverage are absent — total_known reflects matches we can attribute.
    sql_faction = text("""
        SELECT pms.side, COUNT(*) AS n
        FROM player_match_side pms
        JOIN steam_id_64 s ON s.id = pms.player_id
        WHERE s.steam_id_64 = :sid
        GROUP BY pms.side
    """)
    side_counts = {"Allies": 0, "Axis": 0}
    for r in db.execute(sql_faction, {"sid": steam_id}):
        if r.side in side_counts:
            side_counts[r.side] = int(r.n or 0)
    total_known = side_counts["Allies"] + side_counts["Axis"]
    faction_pref = {
        "allies": side_counts["Allies"],
        "axis": side_counts["Axis"],
        "total_known": total_known,
        "allies_pct": round(side_counts["Allies"] / total_known * 100, 1) if total_known > 0 else 0.0,
        "axis_pct":   round(side_counts["Axis"]   / total_known * 100, 1) if total_known > 0 else 0.0,
    }

    # 9) Alt names — distinct player_stats.name values for this player.
    sql_alt = text("""
        SELECT DISTINCT ps.name
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        WHERE s.steam_id_64 = :sid AND ps.name IS NOT NULL AND ps.name <> ''
        ORDER BY ps.name
        LIMIT 20
    """)
    alt_names = [r[0] for r in db.execute(sql_alt, {"sid": steam_id})]

    # 10) Kill / death type breakdown — classify each weapon string via the
    # shared weapon_classes Python rules. We pull (weapon, sum) pairs and
    # bucket in Python rather than re-implementing CASE WHEN in SQL.
    sql_kill_weapons = text("""
        SELECT key AS weapon, SUM(value::int) AS n
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id,
             jsonb_each_text(ps.weapons)
        WHERE s.steam_id_64 = :sid AND ps.weapons IS NOT NULL
        GROUP BY weapon
    """)
    sql_death_weapons = text("""
        SELECT key AS weapon, SUM(value::int) AS n
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id,
             jsonb_each_text(ps.death_by_weapons)
        WHERE s.steam_id_64 = :sid AND ps.death_by_weapons IS NOT NULL
        GROUP BY weapon
    """)
    def _aggregate_by_class(rows) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in rows:
            cls = classify_weapon(r.weapon) or "Other"
            out[cls] = out.get(cls, 0) + int(r.n or 0)
        return out

    kills_by_class = _aggregate_by_class(db.execute(sql_kill_weapons, {"sid": steam_id}))
    deaths_by_class = _aggregate_by_class(db.execute(sql_death_weapons, {"sid": steam_id}))

    # 11) Win rate — JOIN player_match_side MV with map_history.result
    # (result jsonb shape: {"Allied": <sectors>, "Axis": <sectors>}). A match
    # is a win when the player's side captured more sectors. Matches with
    # equal sectors → draw. Excludes matches where result is NULL/empty or
    # MV has no side for the player (logs predate capture).
    sql_winrate = text("""
        SELECT
          pms.side,
          CASE
            WHEN (m.result->>'Allied')::int > (m.result->>'Axis')::int THEN 'Allies'
            WHEN (m.result->>'Axis')::int   > (m.result->>'Allied')::int THEN 'Axis'
            ELSE 'Draw'
          END AS winner,
          COUNT(*) AS n
        FROM player_match_side pms
        JOIN steam_id_64 s ON s.id = pms.player_id
        JOIN map_history m ON m.id = pms.match_id
        WHERE s.steam_id_64 = :sid
          AND m.result IS NOT NULL
          AND (m.result ? 'Allied') AND (m.result ? 'Axis')
        GROUP BY pms.side, winner
    """)
    wr_buckets: dict[tuple[str, str], int] = {}
    for r in db.execute(sql_winrate, {"sid": steam_id}):
        wr_buckets[(r.side, r.winner)] = int(r.n or 0)

    def _bucket(side: str, winner: str) -> int:
        return wr_buckets.get((side, winner), 0)

    matches_as_allies = _bucket("Allies", "Allies") + _bucket("Allies", "Axis") + _bucket("Allies", "Draw")
    matches_as_axis   = _bucket("Axis",   "Allies") + _bucket("Axis",   "Axis") + _bucket("Axis",   "Draw")
    wins_as_allies = _bucket("Allies", "Allies")
    wins_as_axis   = _bucket("Axis",   "Axis")
    total = matches_as_allies + matches_as_axis
    wins = wins_as_allies + wins_as_axis
    draws = _bucket("Allies", "Draw") + _bucket("Axis", "Draw")
    losses = total - wins - draws
    win_rate = {
        "total": total,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_pct": round(wins / total * 100, 1) if total > 0 else 0.0,
        "allies_total": matches_as_allies,
        "allies_wins": wins_as_allies,
        "allies_win_pct": round(wins_as_allies / matches_as_allies * 100, 1) if matches_as_allies > 0 else 0.0,
        "axis_total": matches_as_axis,
        "axis_wins": wins_as_axis,
        "axis_win_pct": round(wins_as_axis / matches_as_axis * 100, 1) if matches_as_axis > 0 else 0.0,
    }

    # 12) Hour-of-day distribution — when does this player actually play?
    # Used by the time-of-day heatmap on PlayerDetail.
    sql_hours = text("""
        SELECT EXTRACT(HOUR FROM m.start)::int AS h, COUNT(*) AS n
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        JOIN map_history m ON m.id = ps.map_id
        WHERE s.steam_id_64 = :sid AND m.start IS NOT NULL
        GROUP BY h
        ORDER BY h
    """)
    hour_distribution = [0] * 24
    for r in db.execute(sql_hours, {"sid": steam_id}):
        if r.h is not None and 0 <= r.h < 24:
            hour_distribution[r.h] = int(r.n or 0)

    # 14) Most played with / against — derived from player_match_side MV.
    # Restricted to logged matches; older un-tracked matches don't contribute.
    pwa = played_with_against(db, steam_id, limit=5)

    # 15) Melee micro-stats — last melee death event + current streak.
    melee = melee_meta(db, steam_id)

    # 16) Hardcounters — players with positive K/D against this player.
    hc = hardcounters(db, steam_id, min_deaths=5, limit=5)

    # 17) Achievement progress — top-5 closest-to-earning badges.
    ach_progress = compute_achievement_progress(profile, limit=5)

    # 18) Playstyle — single archetype matched by the shared classifier.
    playstyle = classify_playstyle_one(profile)

    return {
        "profile": profile,
        "achievements": achievements_list,
        "top_weapons": top_weapons,
        "most_killed": most_killed,
        "killed_by": killed_by,
        "recent_matches": recent_matches,
        "overview": overview,
        "top_maps": top_maps,
        "faction_pref": faction_pref,
        "alt_names": alt_names,
        "kills_by_class": kills_by_class,
        "deaths_by_class": deaths_by_class,
        "win_rate": win_rate,
        "hour_distribution": hour_distribution,
        "played_with_against": pwa,
        "melee_meta": melee,
        "hardcounters": hc,
        "achievement_progress": ach_progress,
        "playstyle": playstyle,
    }
