"""Dynamic-whitelist gate for votemap during seeding hours / low pop.

Editorial policy: votes during seeding should be limited to a curated
set of 7 starter-friendly warfare-day maps so the server reliably
fills. Outside that window, the admin's full whitelist applies.

Seeding window is active when EITHER:
  • current player count < 50  (gradient-of-fillness threshold), OR
  • Europe/Kyiv local hour is in [23, 6)  (overnight / early morning)

Hour gate spans midnight so 23:00–05:59 Kyiv counts as seeding regardless
of pop — late-night sessions have small player swings and we don't want
fresh joiners landing on an unfamiliar Driel / Foy / El Alamein.

Implementation: monkey-patch `VoteMap.get_map_whitelist` so the votemap
selection generator sees a narrower set during seeding. The admin-stored
whitelist in Redis (`votemap_whitelist` key) is NOT touched — the admin
UI keeps showing the full 26-map list and reverts cleanly when the gate
closes (player count climbs back to ≥50 AND hour falls under 23).

Wiring: imported for side effect from `rcon/hooks.py` so the patch is
installed at supervisor / backend startup, in time for any
`VoteMap().gen_selection()` call to see it.
"""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from rcon.maps import parse_layer
from rcon.vote_map import VoteMap

logger = logging.getLogger(__name__)

# Layer ids of the 7 seeding-friendly warfare-day maps. These are the
# layer IDs from rcon/maps.py LAYERS dict — not base map ids. Each
# resolves to one specific (map, mode=warfare, environment=day) Layer.
SEEDING_LAYER_IDS: tuple[str, ...] = (
    "kharkov_warfare",
    "carentan_warfare",
    "kursk_warfare",
    "omahabeach_warfare",
    "stmereeglise_warfare",
    "stmariedumont_warfare",
    "utahbeach_warfare",
)

# Below this player count the seeding pool kicks in regardless of time
# (49 → seeding, 50 → prime). Hard cutoff per user request — no buffer.
PLAYER_THRESHOLD: int = 50

# Kyiv-local hour range (24-h clock) during which seeding is enforced
# regardless of pop. Spans midnight, so checked with `hour >= 23 or hour < 6`.
SEEDING_HOUR_START: int = 23   # inclusive
SEEDING_HOUR_END: int   = 6    # exclusive

_TZ = ZoneInfo("Europe/Kyiv")


def _kyiv_hour_in_seeding_window() -> bool:
    """True when current Kyiv local hour is in [23, 6)."""
    hour = datetime.now(_TZ).hour
    return hour >= SEEDING_HOUR_START or hour < SEEDING_HOUR_END


def _player_count_in_seeding_window(rcon) -> bool:
    """True when current player count is below PLAYER_THRESHOLD.

    Defensive on rcon failures — treat unknown as seeding (safer to
    over-restrict than to ship players a Driel during a 30-player
    moment because rcon hiccuped)."""
    try:
        slots = rcon.get_slots()
        players = int(slots.get("current_players", 0))
    except Exception:
        logger.warning("votemap_seeding: get_slots failed, assuming seeding")
        return True
    return players < PLAYER_THRESHOLD


def is_seeding_now(rcon) -> bool:
    """Single source of truth for the seeding-window predicate.

    Returns True when EITHER pop < 50 OR Kyiv hour ∈ [23, 6).
    See module docstring for rationale.
    """
    return _player_count_in_seeding_window(rcon) or _kyiv_hour_in_seeding_window()


def _seeding_whitelist() -> set:
    """Resolve the 7 layer ids to Layer objects. Misconfigured ids
    (e.g. game patch removes a map) are dropped with a warning rather
    than crashing votemap generation."""
    out = set()
    for layer_id in SEEDING_LAYER_IDS:
        try:
            out.add(parse_layer(layer_id))
        except Exception as e:
            logger.warning("votemap_seeding: layer %r unparseable: %s", layer_id, e)
    return out


# ─── Monkey-patch ───────────────────────────────────────────────────────────
# We replace VoteMap.get_map_whitelist rather than gen_selection because the
# upstream selection pipeline already uses get_map_whitelist as its sole
# whitelist source. Patching there means every call site (gen_selection,
# admin endpoints, any future caller) sees the narrowed set during seeding
# without further code changes.
#
# The original method is kept on the class as _get_map_whitelist_unpatched
# so the admin-stored whitelist can still be read if/when we need it
# (e.g. for an admin endpoint that should show the *configured* set, not
# the *effective* set).

_original_get_map_whitelist = VoteMap.get_map_whitelist
VoteMap._get_map_whitelist_unpatched = _original_get_map_whitelist  # type: ignore[attr-defined]


def _patched_get_map_whitelist(self) -> set:
    if is_seeding_now(self.rcon):
        whitelist = _seeding_whitelist()
        logger.info(
            "votemap_seeding: gate ACTIVE, returning %d seeding maps",
            len(whitelist),
        )
        return whitelist
    return _original_get_map_whitelist(self)


VoteMap.get_map_whitelist = _patched_get_map_whitelist  # type: ignore[method-assign]

logger.info(
    "votemap_seeding: VoteMap.get_map_whitelist patched (threshold=%d, hours=[%d,%d))",
    PLAYER_THRESHOLD, SEEDING_HOUR_START, SEEDING_HOUR_END,
)
