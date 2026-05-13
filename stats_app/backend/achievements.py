"""Lifetime achievements computation.

Given a player's aggregated stats (from queries.player_detail), produces
a list of achievement badges the player has earned. Pure function over
the profile dict, no DB access here.
"""
from typing import List, Dict, Any


# (id, title, icon, tier, description, predicate) — tier controls visual rarity color.
# tier: 'common' < 'uncommon' < 'rare' < 'epic' < 'legendary' < 'mythic'
# Description is the user-facing earn condition; surfaced on /achievements,
# /achievements/{id}, and as the badge tooltip. Keep it short, second-person.
ACHIEVEMENTS = [
    # Matches played
    ("centurion",    "Сотник",            "🏆", "common",    "Зіграти 100+ матчів",                 lambda p: p.get("matches_played", 0) >= 100),
    ("veteran",      "Ветеран",            "🎖", "uncommon",  "Зіграти 500+ матчів",                 lambda p: p.get("matches_played", 0) >= 500),
    ("lifetime",     "Lifetime гравець",   "👑", "legendary", "Зіграти 1000+ матчів",                lambda p: p.get("matches_played", 0) >= 1000),

    # Skill (K/D)
    ("sharpshooter", "Влучний",            "🎯", "uncommon",  "Мати K/D 2.0+ з 30+ матчів",          lambda p: (p.get("kd_ratio") or 0) >= 2.0 and (p.get("matches_played") or 0) >= 30),
    ("elite_sniper", "Елітний снайпер",    "🔭", "epic",      "Мати K/D 3.0+ з 30+ матчів",          lambda p: (p.get("kd_ratio") or 0) >= 3.0 and (p.get("matches_played") or 0) >= 30),

    # Pure damage
    ("centurion_k",  "100 вбивств",        "💀", "common",    "Зробити 100+ вбивств за весь час",    lambda p: p.get("kills", 0) >= 100),
    ("killer_1k",    "1000 вбивств",       "💀", "uncommon",  "Зробити 1000+ вбивств за весь час",   lambda p: p.get("kills", 0) >= 1000),
    ("killing_mach", "Machine of Kill",    "🔥", "rare",      "Зробити 5000+ вбивств за весь час",   lambda p: p.get("kills", 0) >= 5000),
    ("reaper",       "Жнець",              "☠️",  "epic",      "Зробити 10000+ вбивств за весь час",  lambda p: p.get("kills", 0) >= 10000),

    # Streaks
    ("unstoppable",  "Нестримний",         "⚡", "rare",      "Серія 30+ вбивств в одному матчі",    lambda p: (p.get("best_kills_streak") or 0) >= 30),
    ("legendary_st", "Легендарна серія",   "🌟", "legendary", "Серія 60+ вбивств в одному матчі",    lambda p: (p.get("best_kills_streak") or 0) >= 60),
    ("god_mode",     "Режим бога",         "💫", "mythic",    "Серія 88+ вбивств в одному матчі",    lambda p: (p.get("best_kills_streak") or 0) >= 88),

    # Playtime
    ("marathon",     "Марафонець",         "⏱",  "uncommon",  "Провести 100+ годин на сервері",      lambda p: p.get("total_seconds", 0) >= 100 * 3600),
    ("time_lord",    "Володар часу",       "⏳", "epic",      "Провести 500+ годин на сервері",      lambda p: p.get("total_seconds", 0) >= 500 * 3600),

    # Score components
    ("combat_master","Майстер бою",        "⚔️",  "rare",      "Накопичити 100K+ combat score",       lambda p: (p.get("combat") or 0) >= 100000),
    ("support_hero", "Герой підтримки",    "🛡",  "rare",      "Накопичити 300K+ support score",      lambda p: (p.get("support") or 0) >= 300000),
    ("defender",     "Захисник",           "🏰", "rare",      "Накопичити 200K+ defense score",      lambda p: (p.get("defense") or 0) >= 200000),
    ("attacker",     "Нападник",           "🗡",  "rare",      "Накопичити 100K+ offense score",      lambda p: (p.get("offense") or 0) >= 100000),

    # Level
    ("elite",        "Еліта (lvl 200+)",   "✨", "rare",      "Досягти рівня 200",                   lambda p: (p.get("level") or 0) >= 200),
    ("legendary_lvl","Легенда (lvl 250+)", "💎", "legendary", "Досягти рівня 250",                   lambda p: (p.get("level") or 0) >= 250),
    ("mythic_lvl",   "Міф (lvl 300+)",     "🔮", "mythic",    "Досягти рівня 300",                   lambda p: (p.get("level") or 0) >= 300),

    # Endurance / long life
    ("survivor",     "Виживальник",        "🦾", "uncommon",  "Прожити 10+ хвилин без смерті",       lambda p: (p.get("longest_life_secs") or 0) >= 600),

    # Negative / fun
    ("tk_offender",  "TK провокатор",      "⚠️",  "common",    "Зробити 100+ team kills (своїх)",     lambda p: p.get("teamkills", 0) >= 100),
    ("clumsy",       "Незграба",           "😅", "uncommon",  "Загинути 100+ разів від ТК своїх",    lambda p: p.get("deaths_by_tk", 0) >= 100),

    # Long-tenure / dedication (D-batch additions)
    ("disciplined",  "Дисциплінований",    "🎖", "uncommon",  "Зіграти 100+ матчів з TK rate < 10%",
        lambda p: (p.get("matches_played") or 0) >= 100 and (p.get("teamkills") or 0) * 10 < (p.get("kills") or 0)),
    ("spotless",     "Чисте сумління",     "🕊", "rare",       "Зіграти 100+ матчів і жодного разу не вмерти від ТК своїх",
        lambda p: (p.get("matches_played") or 0) >= 100 and (p.get("deaths_by_tk") or 0) == 0),
    ("fortress",     "Фортеця",            "🏯", "epic",       "Накопичити 500K+ defense score",
        lambda p: (p.get("defense") or 0) >= 500000),
    ("tireless",     "Невтомний",          "⏰", "legendary",  "Провести 1000+ годин на сервері",
        lambda p: (p.get("total_seconds") or 0) >= 1000 * 3600),
    ("lone_survivor","Самотній виживальник","🌵", "epic",       "Прожити 30+ хвилин без смерті",
        lambda p: (p.get("longest_life_secs") or 0) >= 1800),
    ("old_guard",    "Стара гвардія",      "🪖", "legendary",  "Зіграти 2000+ матчів",
        lambda p: (p.get("matches_played") or 0) >= 2000),

    # Weapon-class achievements — require kills_by_class in profile (which
    # _all_player_profiles_enriched provides). player_detail injects
    # kills_by_class before calling compute_achievements.
    ("samurai",      "Самурай",             "🔪", "rare",      "Зробити 50+ вбивств у ближньому бою",
        lambda p: (p.get("kills_by_class") or {}).get("Melee", 0) >= 50),
    ("tank_god",     "Танковий бог",         "🚜", "epic",      "200+ kills через Tank Gun / Anti-Tank",
        lambda p: ((p.get("kills_by_class") or {}).get("Tank Gun", 0)
                   + (p.get("kills_by_class") or {}).get("Anti-Tank", 0)) >= 200),
    ("all_rounder",  "Універсальний солдат","🎻", "epic",      "Робити вбивства з 8+ різних класів зброї",
        lambda p: (p.get("classes_with_kills") or 0) >= 8),

    # Per-weapon-class achievements (E-batch). Driven by kills_by_class which
    # _all_player_profiles_enriched fills in. The "200+ kills" thresholds are
    # tuned so a focused specialist earns them while a generalist with the
    # same total kill count doesn't — see also `tank_god` / `samurai` which
    # already cover Tank/AT and Melee buckets.
    ("sniper_ghost",   "Снайпер-привид",       "👻", "epic",      "Зробити 500+ вбивств зі Sniper Rifle",
        lambda p: (p.get("kills_by_class") or {}).get("Sniper Rifle", 0) >= 500),
    ("mg_master",      "Майстер MG",           "🔫", "rare",      "Зробити 500+ вбивств з Machine Gun",
        lambda p: (p.get("kills_by_class") or {}).get("Machine Gun", 0) >= 500),
    ("artillerist",    "Артилерист",           "💥", "epic",      "Зробити 300+ вбивств з артилерії",
        lambda p: (p.get("kills_by_class") or {}).get("Artillery", 0) >= 300),
    ("grenadier",      "Гранатомет",           "💣", "rare",      "Зробити 300+ вбивств вибухівкою (granade/satchel/rocket)",
        lambda p: (p.get("kills_by_class") or {}).get("Explosive", 0) >= 300),
    ("miner",          "Сапер",                "⚙️", "rare",       "Зробити 100+ вбивств мінами",
        lambda p: (p.get("kills_by_class") or {}).get("Mine", 0) >= 100),
    ("fire_fist",      "Вогняний кулак",       "🔥", "legendary", "Зробити 100+ вбивств вогнеметом",
        lambda p: (p.get("kills_by_class") or {}).get("Flame", 0) >= 100),
    ("anti_tank_ace",  "Бронебійник",          "🚀", "rare",      "Зробити 200+ вбивств з Anti-Tank зброї",
        lambda p: (p.get("kills_by_class") or {}).get("Anti-Tank", 0) >= 200),

    # Behavioural / pace (F-batch). Profile-only signals — no per-match data
    # needed thanks to the enriched fields kpm, unique_weapons_count, peak_hour_pct.
    ("fast_killer",    "Швидкий стрілець",     "⚡", "rare",      "KPM 1.5+ з 30+ матчів",
        lambda p: (p.get("kpm") or 0) >= 1.5 and (p.get("matches_played") or 0) >= 30),
    ("loyal_soldier",  "Вірний солдат",        "🕊", "legendary", "500+ матчів і жодного власного TK",
        lambda p: (p.get("matches_played") or 0) >= 500 and (p.get("teamkills") or 0) == 0),
    ("weapon_master",  "Майстер арсеналу",     "🎻", "uncommon",  "Використати 50+ різних видів зброї",
        lambda p: (p.get("unique_weapons_count") or 0) >= 50),
    ("night_owl",      "Сова",                 "🦉", "rare",      "60%+ усіх матчів грав у одну й ту саму годину доби",
        lambda p: (p.get("peak_hour_pct") or 0) >= 60),
    ("storm",          "Шторм",                "🌪", "epic",      "Сумарний score (combat+offense+defense+support) 1M+",
        lambda p: ((p.get("combat") or 0) + (p.get("offense") or 0)
                   + (p.get("defense") or 0) + (p.get("support") or 0)) >= 1_000_000),

    # Hidden achievements / easter eggs. Pure aggregate from profile — no
    # per-match data needed. These reward unusual statistical signatures
    # rather than raw volume.
    ("balanced",     "Дзен-балансист",     "☯",   "rare",      "Combat / offense / defense / support — усі в межах 15% одне від одного",
        lambda p: _scores_balanced(p, tol=15.0) and (p.get("matches_played") or 0) >= 50),
    ("exact_one",    "Рівновага",          "⚖",   "rare",      "K/D рівно 1.00 (тонкий баланс перемог і смертей)",
        lambda p: (p.get("kd_ratio") or 0) > 0 and round(p.get("kd_ratio") or 0, 2) == 1.00 and (p.get("matches_played") or 0) >= 50),
    ("iron_apron",   "Залізний фартух",    "🛡",  "epic",      "Defense складає 50%+ від суми всіх score-категорій",
        lambda p: _defense_dominant(p)),
    ("supply_main",  "Логіст-маньяк",      "📦", "epic",      "Support складає 60%+ від суми всіх score-категорій",
        lambda p: _support_dominant(p)),
]


def _scores_balanced(p: Dict[str, Any], tol: float = 15.0) -> bool:
    """True when combat/offense/defense/support are within ±tol% of each other.
    Tolerance is relative to the average score (handles wildly different total magnitudes)."""
    vals = [p.get("combat") or 0, p.get("offense") or 0, p.get("defense") or 0, p.get("support") or 0]
    total = sum(vals)
    if total == 0:
        return False
    avg = total / 4
    if avg == 0:
        return False
    return all(abs(v - avg) / avg * 100 <= tol for v in vals)


def _defense_dominant(p: Dict[str, Any]) -> bool:
    total = (p.get("combat") or 0) + (p.get("offense") or 0) + (p.get("defense") or 0) + (p.get("support") or 0)
    if total == 0:
        return False
    return (p.get("defense") or 0) / total >= 0.50


def _support_dominant(p: Dict[str, Any]) -> bool:
    total = (p.get("combat") or 0) + (p.get("offense") or 0) + (p.get("defense") or 0) + (p.get("support") or 0)
    if total == 0:
        return False
    return (p.get("support") or 0) / total >= 0.60


# For each simple "metric >= threshold" achievement, the metric field name
# in the profile + the threshold value. Used by compute_achievement_progress
# to show "X more to next badge" progress bars. Composite/relative achievements
# (balanced, iron_apron, supply_main, exact_one) deliberately excluded —
# their predicates don't fit a single-axis progress display.
SIMPLE_THRESHOLDS: Dict[str, tuple] = {
    "centurion":     ("matches_played",     100),
    "veteran":       ("matches_played",     500),
    "lifetime":      ("matches_played",     1000),
    "sharpshooter":  ("kd_ratio",           2.0),
    "elite_sniper":  ("kd_ratio",           3.0),
    "centurion_k":   ("kills",              100),
    "killer_1k":     ("kills",              1000),
    "killing_mach":  ("kills",              5000),
    "reaper":        ("kills",              10000),
    "unstoppable":   ("best_kills_streak",  30),
    "legendary_st":  ("best_kills_streak",  60),
    "god_mode":      ("best_kills_streak",  88),
    "marathon":      ("total_seconds",      100 * 3600),
    "time_lord":     ("total_seconds",      500 * 3600),
    "combat_master": ("combat",             100000),
    "support_hero":  ("support",            300000),
    "defender":      ("defense",            200000),
    "attacker":      ("offense",            100000),
    "elite":         ("level",              200),
    "legendary_lvl": ("level",              250),
    "mythic_lvl":    ("level",              300),
    "survivor":      ("longest_life_secs",  600),
    "tk_offender":   ("teamkills",          100),
    "clumsy":        ("deaths_by_tk",       100),
    # D-batch — only the single-axis ones; disciplined / spotless are
    # compound predicates and are skipped from progress UI.
    "fortress":      ("defense",            500000),
    "tireless":      ("total_seconds",      1000 * 3600),
    "lone_survivor": ("longest_life_secs",  1800),
    "old_guard":     ("matches_played",     2000),
    # F-batch progress entries — single-axis only. Weapon-class predicates
    # use kills_by_class.<class> which doesn't fit the flat profile.get(key)
    # lookup used here, so they're shown as binary earned/not-earned only.
    "fast_killer":   ("kpm",                1.5),
    "weapon_master": ("unique_weapons_count", 50),
    "night_owl":     ("peak_hour_pct",      60),
    "storm":         ("combat",             1_000_000),  # rough proxy — total score = combat+others
}


def compute_achievement_progress(profile: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    """Top-N closest-to-earning achievements for this profile.

    Returns each as {id, title, icon, tier, description, current, threshold, pct}.
    Sorted by completion % descending. Excludes already-earned and
    excludes composite predicates that don't fit the simple progress model.
    """
    earned_ids = {a["id"] for a in compute_achievements(profile)}
    rows: List[Dict[str, Any]] = []
    for aid, (key, threshold) in SIMPLE_THRESHOLDS.items():
        if aid in earned_ids:
            continue
        try:
            current = profile.get(key) or 0
            current_f = float(current)
        except (TypeError, ValueError):
            continue
        if threshold <= 0:
            continue
        pct = min(99.0, (current_f / threshold) * 100)
        meta = next((a for a in ACHIEVEMENTS if a[0] == aid), None)
        if not meta:
            continue
        rows.append({
            "id": aid,
            "title": meta[1],
            "icon": meta[2],
            "tier": meta[3],
            "description": meta[4],
            "current": current_f,
            "threshold": threshold,
            "pct": round(pct, 1),
        })
    rows.sort(key=lambda r: r["pct"], reverse=True)
    return rows[:limit]


def compute_achievements(profile: Dict[str, Any]) -> List[Dict[str, str]]:
    """Return list of earned achievements for a player profile."""
    earned = []
    for aid, title, icon, tier, description, predicate in ACHIEVEMENTS:
        try:
            if predicate(profile):
                earned.append({
                    "id": aid, "title": title, "icon": icon,
                    "tier": tier, "description": description,
                })
        except (TypeError, ValueError):
            continue  # missing data — skip
    return earned
