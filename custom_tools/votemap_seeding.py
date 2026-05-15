"""Dynamic-whitelist gate for votemap during seeding hours / low pop.

Editorial policy: votes during seeding should be limited to a curated
set of starter-friendly maps so the server reliably fills:

  • 7 warfare-day maps (the base "always playable" set)
  • 6 offensive variants of those same maps (one offensive per base map
    where HLL has an offensive variant; Stmariedumont has none).

Combined with the admin's vote settings (num_warfare_options=4,
num_offensive_options=1), the player sees: 4 warfare from the 7 +
1 offensive from the 6, total 5 vote options during seeding.

Outside that window, the admin's full whitelist (26 maps incl. Foy,
Hurtgen, Driel, etc.) applies and votemap picks freely from it.

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
import random
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

# Offensive variants of the same base maps. One per map, picking the
# canonical attacker side (US for D-Day, RUS for Kharkov 1943 counter-
# attack, GER for Operation Citadel at Kursk). Stmariedumont has no
# offensive variant in HLL, so the list has 6 entries for 7 base maps —
# fine, votemap picks num_offensive_options=1 from whatever is available.
#
# These attacker-side picks were validated against admin_analytics:
#   carentan_offensive_us  → 277 player·matches, 37.9% return rate (#1)
#   kharkov_offensive_rus  → 892 player·matches, 29.5% return rate
#   omahabeach_offensive_us → 603 PM (largest D-Day off sample)
#   utahbeach_offensive_us → 470 PM, 33% return, 41% long-play
#   kursk_offensive_ger    → 136 PM (only kursk off variant with data)
#   stmereeglise_offensive_us → no historical data on US side but
#                               canonical for D-Day paratroopers
SEEDING_OFFENSIVE_LAYER_IDS: tuple[str, ...] = (
    "carentan_offensive_us",
    "kharkov_offensive_rus",
    "kursk_offensive_ger",
    "omahabeach_offensive_us",
    "stmereeglise_offensive_us",
    "utahbeach_offensive_us",
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
    """Resolve all seeding layer ids (warfares + offensives) to Layer
    objects. Misconfigured ids (e.g. game patch removes a map) are
    dropped with a warning rather than crashing votemap generation.

    Returns the combined set so votemap's natural picking can satisfy
    both num_warfare_options and num_offensive_options from a single
    whitelist."""
    out = set()
    for layer_id in SEEDING_LAYER_IDS + SEEDING_OFFENSIVE_LAYER_IDS:
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


# ─── Dedup wrapper around gen_selection ─────────────────────────────────────
# During seeding our whitelist is narrow (7 warfares + 6 offensives sharing
# base maps). With num_warfare=4 and num_offensive=1, the natural picker
# overlaps the offensive with one of the 4 warfares ~56% of the time
# (same base map appears twice in the vote). User wants the vote to always
# show 5 distinct base maps — so we post-process the selection: if the
# offensive's base map is among the warfares, swap in a different offensive
# from our seeding-offensive pool that doesn't overlap.
#
# Only applied during seeding. Outside seeding, the admin's full whitelist
# is in use and any overlap is what the admin configured.

_original_gen_selection = VoteMap.gen_selection
VoteMap._gen_selection_unpatched = _original_gen_selection  # type: ignore[attr-defined]


def _patched_gen_selection(self):
    """Generate selection, then (only during seeding) ensure the offensive's
    base map is not duplicated in the warfare picks."""
    _original_gen_selection(self)

    if not is_seeding_now(self.rcon):
        return  # outside seeding, admin's intent stands

    selection = self.get_selection()
    if not selection:
        return

    warfares   = [m for m in selection if "warfare"   in m.id.lower()]
    offensives = [m for m in selection if "offensive" in m.id.lower()]
    if not (warfares and offensives):
        return

    war_base_maps = {m.map.id for m in warfares}

    fixed = []
    swapped = False
    for m in selection:
        if "offensive" in m.id.lower() and m.map.id in war_base_maps:
            # Find an alternative offensive whose base map isn't already in warfares
            candidates = []
            for oid in SEEDING_OFFENSIVE_LAYER_IDS:
                try:
                    cand = parse_layer(oid)
                except Exception:
                    continue
                if cand.map.id in war_base_maps:
                    continue
                if cand.id == m.id:
                    continue
                # Also make sure not already in current fixed list
                if any(cand.id == f.id for f in fixed):
                    continue
                candidates.append(cand)
            if candidates:
                replacement = random.choice(candidates)
                logger.info(
                    "votemap_seeding: deduped offensive %s → %s (warfares: %s)",
                    m.id, replacement.id, sorted(war_base_maps),
                )
                fixed.append(replacement)
                swapped = True
                continue
            else:
                # No clean alternative — fall back to original (very rare)
                logger.warning(
                    "votemap_seeding: no clean offensive alternative; keeping %s",
                    m.id,
                )
        fixed.append(m)

    if swapped:
        self.set_selection(selection=fixed)


VoteMap.gen_selection = _patched_gen_selection  # type: ignore[method-assign]


logger.info(
    "votemap_seeding: patched (threshold=%d, hours=[%d,%d), %d seeding warfares + %d offensives, dedup ON)",
    PLAYER_THRESHOLD, SEEDING_HOUR_START, SEEDING_HOUR_END,
    len(SEEDING_LAYER_IDS), len(SEEDING_OFFENSIVE_LAYER_IDS),
)
