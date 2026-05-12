"""Weapon classification for stats_app.

Groups the ~212 distinct HLL weapons into ~10 categories so users can
filter by "Sniper" rather than picking one of 12 sniper-rifle variants.
Pattern-based: each rule is checked in order, first match wins.

This is a stats_app-local copy; if it ever drifts from the canonical
ElGuillermo `common_functions.py:WEAPONS_*` collections, that's the
source of truth.
"""
from typing import Optional


# Classification rules in priority order. Each tuple: (class_name, list_of_substrings_to_match_case_insensitively).
WEAPON_CLASS_PATTERNS: list[tuple[str, list[str]]] = [
    # Specific must come before more general (e.g. "ARTILLERY" patterns before tank-gun "GUN")
    ("Artillery",  ["HOWITZER", "WERFER", "150MM", "152MM", "122MM", "105MM"]),
    ("Anti-Tank",  ["PANZERSCHRECK", "BAZOOKA", "FAUST", "PIAT", "PTRS", "PTRD", "AT MINE", "ATR"]),
    ("Tank Gun",   ["GUN [", "CANNON [", "MAIN GUN", "COAXIAL", "HULL MG", "HALF-TRACK"]),
    ("Machine Gun", ["MG34", "MG42", "BROWNING M1919", "M1919", "M2 BROWNING", "BREN", "DP-27", "DP27",
                      "VICKERS", "MG-34", "MG-42", "ZB-26", "HEAVY MG"]),
    ("Submachine Gun", ["MP40", "MP-40", "MP41", "THOMPSON", "STEN", "PPSH", "PPS-43", "GREASE GUN",
                          "MAS-38", "M3 SMG", "M3 GREASE", "STG44", "STG 44", "SUOMI"]),
    # Sniper rifles: explicit "SNIPER", "SCOPE", or HLL's "x8" suffix (8x scope variant)
    ("Sniper Rifle", ["SNIPER", "SCOPE", "K x8", " x8", "X8"]),
    ("Rifle",      ["KARABINER 98K", "K98", "M1 GARAND", "M1903", "MOSIN", "LEE-ENFIELD",
                      "LEE ENFIELD", "SVT-40", "SVT40", "GEWEHR"]),
    ("Pistol",     ["LUGER", "WALTHER", "TT-33", "TT33", "WEBLEY", "COLT", "M1911", "M1A1"]),
    ("Flame",      ["FLAMETHROWER", "FLAME"]),
    ("Explosive",  ["GRENADE", "SATCHEL", "DYNAMITE", "C4", "EXPLOSIVE", "MOLOTOV"]),
    ("Mine",       ["TELLER", "S-MINE", "POMZ", "M-MINE", "BOUNCING", "SHU-MINE", "RIEGEL"]),
    ("Melee",      ["KNIFE", "FELDSPATEN", "SHOVEL", "BAYONET", "MELEE"]),
    ("Vehicle Run-over", ["RUN OVER", "BUMPER"]),
]


def classify_weapon(name: str) -> str:
    """Return the weapon class name, or 'Other' if no rule matches."""
    if not name:
        return "Other"
    upper = name.upper()
    for class_name, patterns in WEAPON_CLASS_PATTERNS:
        for p in patterns:
            if p in upper:
                return class_name
    return "Other"


def all_class_names() -> list[str]:
    """Order in which to display classes (matches WEAPON_CLASS_PATTERNS order + Other)."""
    return [c for c, _ in WEAPON_CLASS_PATTERNS] + ["Other"]
