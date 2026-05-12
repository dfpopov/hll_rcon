"""SQL aggregation queries for stats_app.

Hand-written SQL (raw text()) for clarity and ability to use JSONB
operators that SQLAlchemy ORM doesn't express cleanly. Read-only.
"""
from typing import Optional, List
from sqlalchemy import text
from sqlalchemy.orm import Session

from weapon_classes import classify_weapon, all_class_names
from achievements import compute_achievements, ACHIEVEMENTS


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

# Recognised values for the `side` filter (data lives in player_match_side MV).
SIDES = {"Allies", "Axis"}


def _build_filters(
    period: Optional[str],
    weapon: Optional[str],
    map_name: Optional[str],
    search: Optional[str] = None,
    game_mode: Optional[str] = None,
    weapon_class: Optional[str] = None,
    weapon_names_for_class: Optional[List[str]] = None,
    side: Optional[str] = None,
) -> tuple[list[str], list[str], dict]:
    """Build (extra_joins, where_parts, params) from optional filters.

    Returned extra_joins are appended to the FROM clause; where_parts go into
    WHERE. Side filter joins player_match_side (matches without log coverage
    are silently excluded — we can't infer their side).
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
        parts.append("ps.name ILIKE :search")
        params["search"] = f"%{search}%"

    if side in SIDES:
        joins.append(
            "JOIN player_match_side pms "
            "ON pms.player_id = s.id AND pms.match_id = ps.map_id"
        )
        parts.append("pms.side = :side")
        params["side"] = side

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
        period, weapon, map_name, search, game_mode, weapon_class, class_weapons, side,
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
        period, weapon, map_name, search, game_mode, weapon_class, class_weapons, side,
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
    sql = text("""
        SELECT DISTINCT w
        FROM player_stats, jsonb_object_keys(weapons) AS w
        WHERE weapons IS NOT NULL
        ORDER BY w
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

    sql = text(f"""
        SELECT
            s.steam_id_64 AS steam_id,
            ps.name AS name,
            ps.level AS level,
            ({expr}) AS value,
            m.id AS match_id,
            m.map_name AS map_name,
            m.start AS match_date
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
    sql_weapons = text("""
        SELECT key AS weapon, SUM(value::int) AS kills
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id,
             jsonb_each_text(ps.weapons)
        WHERE s.steam_id_64 = :sid AND ps.weapons IS NOT NULL
        GROUP BY key
        ORDER BY kills DESC
        LIMIT 10
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
        LIMIT 10
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
        LIMIT 10
    """)
    killed_by = [dict(row._mapping) for row in db.execute(sql_killers, {"sid": steam_id})]

    # 5) Recent matches (last 10) — includes match_id for linking to /games/{id}.
    # Hide barely-played matches (kills=0 AND deaths<=1) — they're usually
    # spectator/disconnect noise, not real games.
    sql_recent = text("""
        SELECT
            m.id AS match_id,
            m.map_name AS map_name,
            m.start AS match_date,
            ps.kills AS kills,
            ps.deaths AS deaths,
            ps.kill_death_ratio AS kd,
            ps.combat AS combat,
            ps.support AS support
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

    # 7) Top maps by matches played, with kills & K/D per map.
    sql_top_maps = text("""
        SELECT
            m.map_name AS map_name,
            COUNT(*) AS matches,
            SUM(ps.kills) AS kills,
            ROUND(CAST(SUM(ps.kills) AS NUMERIC) / NULLIF(SUM(ps.deaths), 0), 2) AS kd
        FROM player_stats ps
        JOIN steam_id_64 s ON s.id = ps.playersteamid_id
        JOIN map_history m ON m.id = ps.map_id
        WHERE s.steam_id_64 = :sid
        GROUP BY m.map_name
        ORDER BY matches DESC
        LIMIT 10
    """)
    top_maps = [dict(r._mapping) for r in db.execute(sql_top_maps, {"sid": steam_id})]

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
    }
