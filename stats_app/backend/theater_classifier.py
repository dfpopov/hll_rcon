"""Map → theater → faction classifier for the side filter (Phase 2).

HLL maps cover three theaters of WW2; each theater pairs one specific Allies
faction with one Axis faction. The MV `player_match_side` only tracks the
binary side (Allies / Axis), so faction must be derived at filter time by
joining map_history and bucketing the map_name.

Reference:
  Western Front:  US      vs Wehrmacht
  Eastern Front:  USSR    vs Wehrmacht  (same Wehrmacht, different theater)
  North Africa:   GB / CW vs DAK

HLL map names come in two styles in the prod DB (75 distinct values as of
2026-05-12):
  - lowercase substring  (carentan_warfare, kursk_offensive_ger, ...)
  - 3-5 letter code prefix + underscore (CAR_S_1944_..., STA_L_1942_..., ...)

The classifier handles both styles. New maps added in future game updates
will return None and silently drop out of faction filters until this file
is updated (no-op for old maps).
"""
from typing import Optional


def classify_theater(map_name: str) -> Optional[str]:
    """Return 'western' | 'eastern' | 'africa' | None for an HLL map name."""
    if not map_name:
        return None
    n = map_name.lower()

    # Eastern Front: USSR vs Wehrmacht
    if (n.startswith('sta_') or
        any(s in n for s in ('kharkov', 'kursk', 'smolensk', 'stalingrad'))):
        return 'eastern'

    # North Africa: GB vs DAK
    if any(s in n for s in ('elalamein', 'tobruk')):
        return 'africa'

    # Western Front: US vs Wehrmacht (code prefixes + lowercase substrings).
    # Note: 'foy' substring is short — kept here as a last-resort match because
    # it's unique among current HLL map names. Add a stricter check if a new
    # map called something with 'foy' in the middle appears.
    western_prefixes = ('car_', 'hil_', 'phl_', 'rem_', 'smdm_')
    western_substr = (
        'carentan', 'driel', 'elsenbornridge', 'foy', 'hill400',
        'hurtgenforest', 'mortain', 'omahabeach', 'stmariedumont',
        'stmereeglise', 'utahbeach', 'remagen',
    )
    if n.startswith(western_prefixes) or any(s in n for s in western_substr):
        return 'western'

    return None


# Faction filter config. Each faction maps to (side, set_of_theaters).
# Wehrmacht spans Western + Eastern; the others are theater-pinned.
FACTION_FILTERS: dict[str, dict] = {
    'US':        {'side': 'Allies', 'theaters': ['western']},
    'GB':        {'side': 'Allies', 'theaters': ['africa']},
    'USSR':      {'side': 'Allies', 'theaters': ['eastern']},
    'Wehrmacht': {'side': 'Axis',   'theaters': ['western', 'eastern']},
    'DAK':       {'side': 'Axis',   'theaters': ['africa']},
}

FACTIONS = set(FACTION_FILTERS.keys())


# Cache: theater → [map_name, ...]. Populated lazily on first DB call.
_THEATER_MAPS_CACHE: dict[str, list[str]] = {}


def maps_by_theater(db) -> dict[str, list[str]]:
    """Return {theater_name: [map_names]} computed from map_history.
    Result is cached at module level — restart the container to pick up
    newly-classified maps. Safe because new maps just won't match faction
    filters until the cache is fresh.
    """
    from sqlalchemy import text  # local import: this module imports nothing else
    if _THEATER_MAPS_CACHE:
        return _THEATER_MAPS_CACHE
    out = {'western': [], 'eastern': [], 'africa': []}
    rows = db.execute(text("SELECT DISTINCT map_name FROM map_history"))
    for row in rows:
        t = classify_theater(row[0])
        if t:
            out[t].append(row[0])
    _THEATER_MAPS_CACHE.update(out)
    return _THEATER_MAPS_CACHE


def maps_for_faction(faction: str, db) -> tuple[str, list[str]]:
    """Return (side, [map_names]) for a faction filter, or ('', []) if unknown."""
    config = FACTION_FILTERS.get(faction)
    if not config:
        return '', []
    cache = maps_by_theater(db)
    maps: list[str] = []
    for t in config['theaters']:
        maps.extend(cache.get(t, []))
    return config['side'], maps
