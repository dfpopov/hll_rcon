"""Lifetime achievements computation.

Given a player's aggregated stats (from queries.player_detail), produces
a list of achievement badges the player has earned. Pure function over
the profile dict, no DB access here.
"""
from typing import List, Dict, Any


# (id, title, icon, tier, predicate) — tier controls visual rarity color.
# tier: 'common' < 'uncommon' < 'rare' < 'epic' < 'legendary' < 'mythic'
ACHIEVEMENTS = [
    # Matches played
    ("centurion",    "Сотник",            "🏆", "common",    lambda p: p.get("matches_played", 0) >= 100),
    ("veteran",      "Ветеран",            "🎖", "uncommon",  lambda p: p.get("matches_played", 0) >= 500),
    ("lifetime",     "Lifetime гравець",   "👑", "legendary", lambda p: p.get("matches_played", 0) >= 1000),

    # Skill (K/D)
    ("sharpshooter", "Влучний",            "🎯", "uncommon",  lambda p: (p.get("kd_ratio") or 0) >= 2.0),
    ("elite_sniper", "Елітний снайпер",    "🔭", "epic",      lambda p: (p.get("kd_ratio") or 0) >= 3.0),

    # Pure damage
    ("centurion_k",  "100 вбивств",        "💀", "common",    lambda p: p.get("kills", 0) >= 100),
    ("killer_1k",    "1000 вбивств",       "💀", "uncommon",  lambda p: p.get("kills", 0) >= 1000),
    ("killing_mach", "Machine of Kill",    "🔥", "rare",      lambda p: p.get("kills", 0) >= 5000),
    ("reaper",       "Жнець",              "☠️",  "epic",      lambda p: p.get("kills", 0) >= 10000),

    # Streaks
    ("unstoppable",  "Нестримний",         "⚡", "rare",      lambda p: (p.get("best_kills_streak") or 0) >= 30),
    ("legendary_st", "Легендарна серія",   "🌟", "legendary", lambda p: (p.get("best_kills_streak") or 0) >= 60),
    ("god_mode",     "Режим бога",         "💫", "mythic",    lambda p: (p.get("best_kills_streak") or 0) >= 88),

    # Playtime
    ("marathon",     "Марафонець",         "⏱",  "uncommon",  lambda p: p.get("total_seconds", 0) >= 100 * 3600),
    ("time_lord",    "Володар часу",       "⏳", "epic",      lambda p: p.get("total_seconds", 0) >= 500 * 3600),

    # Score components
    ("combat_master","Майстер бою",        "⚔️",  "rare",      lambda p: (p.get("combat") or 0) >= 100000),
    ("support_hero", "Герой підтримки",    "🛡",  "rare",      lambda p: (p.get("support") or 0) >= 300000),
    ("defender",     "Захисник",           "🏰", "rare",      lambda p: (p.get("defense") or 0) >= 200000),
    ("attacker",     "Нападник",           "🗡",  "rare",      lambda p: (p.get("offense") or 0) >= 100000),

    # Level
    ("elite",        "Еліта (lvl 200+)",   "✨", "rare",      lambda p: (p.get("level") or 0) >= 200),
    ("legendary_lvl","Легенда (lvl 250+)", "💎", "legendary", lambda p: (p.get("level") or 0) >= 250),
    ("mythic_lvl",   "Міф (lvl 300+)",     "🔮", "mythic",    lambda p: (p.get("level") or 0) >= 300),

    # Endurance / long life
    ("survivor",     "Виживальник",        "🦾", "uncommon",  lambda p: (p.get("longest_life_secs") or 0) >= 600),

    # Negative / fun
    ("tk_offender",  "TK провокатор",      "⚠️",  "common",    lambda p: p.get("teamkills", 0) >= 100),
    ("clumsy",       "Незграба",           "😅", "uncommon",  lambda p: p.get("deaths_by_tk", 0) >= 100),
]


def compute_achievements(profile: Dict[str, Any]) -> List[Dict[str, str]]:
    """Return list of earned achievements for a player profile."""
    earned = []
    for aid, title, icon, tier, predicate in ACHIEVEMENTS:
        try:
            if predicate(profile):
                earned.append({"id": aid, "title": title, "icon": icon, "tier": tier})
        except (TypeError, ValueError):
            continue  # missing data — skip
    return earned
