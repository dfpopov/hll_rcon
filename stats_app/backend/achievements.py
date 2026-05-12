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
    ("sharpshooter", "Влучний",            "🎯", "uncommon",  "Мати K/D 2.0+",                       lambda p: (p.get("kd_ratio") or 0) >= 2.0),
    ("elite_sniper", "Елітний снайпер",    "🔭", "epic",      "Мати K/D 3.0+",                       lambda p: (p.get("kd_ratio") or 0) >= 3.0),

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
    ("marathon",     "Марафонець",         "⏱",  "uncommon",  "Зіграти 100+ годин у грі",            lambda p: p.get("total_seconds", 0) >= 100 * 3600),
    ("time_lord",    "Володар часу",       "⏳", "epic",      "Зіграти 500+ годин у грі",            lambda p: p.get("total_seconds", 0) >= 500 * 3600),

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
]


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
