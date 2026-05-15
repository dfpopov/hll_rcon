"""Dynamic-whitelist gate for votemap during seeding hours / low pop.

Editorial policy: votes during seeding should be limited to a curated
set of starter-friendly maps so the server reliably fills:

  • 7 warfare-day maps (the base "always playable" set)
  • 7 offensive variants of those same maps (one offensive per base map,
    canonical attacker side).

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
from rcon.user_config.votemap_seeding import VotemapSeedingUserConfig
from rcon.vote_map import VoteMap

logger = logging.getLogger(__name__)

# All seeding parameters now live in Redis via VotemapSeedingUserConfig
# (rcon/user_config/votemap_seeding.py) and are editable through the
# rcongui Settings UI. See that module for defaults + descriptions.
#
# Backwards-compat constant aliases so external code that imported these
# names continues to work; the *live* values come from _config().
SEEDING_LAYER_IDS: tuple[str, ...] = ()           # populated lazily, see _config
SEEDING_OFFENSIVE_LAYER_IDS: tuple[str, ...] = ()
PLAYER_THRESHOLD: int = 50
SEEDING_HOUR_START: int = 23
SEEDING_HOUR_END: int = 6

_TZ = ZoneInfo("Europe/Kyiv")


def _config() -> VotemapSeedingUserConfig:
    """Load the live config from Redis on each call. The Redis lookup is
    cheap (~ms) and the call frequency is bounded by votemap selection
    events (every map change), so we don't bother caching."""
    return VotemapSeedingUserConfig.load_from_db()


def _kyiv_hour_in_seeding_window(cfg: VotemapSeedingUserConfig) -> bool:
    """True when current Kyiv local hour is in [start, end).

    The window can wrap across midnight when start > end (e.g. 23..6
    means 23:00–05:59). When start == end, the time gate is effectively
    disabled (returns False always — only player-count gating applies)."""
    hour = datetime.now(_TZ).hour
    start, end = cfg.seeding_hour_start, cfg.seeding_hour_end
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def _player_count_in_seeding_window(rcon, cfg: VotemapSeedingUserConfig) -> bool:
    """True when current player count is below cfg.player_threshold.

    Defensive on rcon failures — treat unknown as seeding (safer to
    over-restrict than to ship players a Driel during a 30-player
    moment because rcon hiccuped)."""
    try:
        slots = rcon.get_slots()
        players = int(slots.get("current_players", 0))
    except Exception:
        logger.warning("votemap_seeding: get_slots failed, assuming seeding")
        return True
    return players < cfg.player_threshold


def is_seeding_now(rcon) -> bool:
    """Single source of truth for the seeding-window predicate.

    Returns True when EITHER pop < threshold OR Kyiv hour is in the
    configured window. If `enabled=False` always returns False, so the
    admin's full whitelist is used at all times.
    """
    cfg = _config()
    if not cfg.enabled:
        return False
    return _player_count_in_seeding_window(rcon, cfg) or _kyiv_hour_in_seeding_window(cfg)


def _seeding_whitelist() -> set:
    """Resolve all seeding layer ids (warfares + offensives) from the
    live config to Layer objects. Misconfigured ids (e.g. game patch
    removes a map, or admin typo) are dropped with a warning rather
    than crashing votemap generation."""
    cfg = _config()
    out = set()
    for layer_id in list(cfg.warfare_layer_ids) + list(cfg.offensive_layer_ids):
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


# Minimum number of "golden" warfares (= those in cfg.warfare_layer_ids)
# that must appear among the 4 warfare picks during PRIME time. If the
# upstream random picker selected fewer, we swap in the least-recently-
# played golden maps. Editorial: guarantees 2 of 4 prime warfare slots
# are "safe / popular" maps, the other 2 stay random for variety.
PRIME_MIN_GOLDEN_WARFARES = 2


def _last_played_index() -> dict[str, int]:
    """Return a {layer_id_lower: index} dict where index 0 = most recently
    played. Used to rank candidate maps by staleness so we prefer maps
    that haven't been on the server in a while.

    Layer ids in MapsHistory are mixed-case (e.g. PHL_L_1944_Warfare_Night),
    while admin-configured ids vary (carentan_warfare lower, PHL_* upper),
    so the dict keys are normalised to lowercase.
    """
    try:
        from rcon.utils import MapsHistory
        idx: dict[str, int] = {}
        for i, entry in enumerate(MapsHistory()):
            name = (entry.get("name") if isinstance(entry, dict) else None) or ""
            key = name.lower()
            if key and key not in idx:
                idx[key] = i
        return idx
    except Exception as e:
        logger.warning("votemap_seeding: MapsHistory unreadable: %s", e)
        return {}


def _staleness(layer_id: str, last_played: dict[str, int]) -> int:
    """Lower index = more recent. Maps NOT in history get a large
    'very stale' value so they're preferred when promoting golden maps."""
    return last_played.get(layer_id.lower(), 10**6)


def _dedup_offensive_against_warfare(self, selection: list) -> tuple[list, bool]:
    """Seeding-only: ensure offensive pick's base map differs from all
    warfare picks. Returns (new_selection, swapped)."""
    warfares = [m for m in selection if "warfare" in m.id.lower()]
    offensives = [
        m for m in selection
        if "_off" in m.id.lower() or "offensive" in m.id.lower()
    ]
    if not (warfares and offensives):
        return selection, False

    war_base_maps = {m.map.id for m in warfares}
    cfg = _config()

    fixed: list = []
    swapped = False
    for m in selection:
        is_off = "_off" in m.id.lower() or "offensive" in m.id.lower()
        if is_off and m.map.id in war_base_maps:
            candidates = []
            for oid in cfg.offensive_layer_ids:
                try:
                    cand = parse_layer(oid)
                except Exception:
                    continue
                if cand.map.id in war_base_maps:
                    continue
                if cand.id == m.id:
                    continue
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
                logger.warning(
                    "votemap_seeding: no clean offensive alternative; keeping %s",
                    m.id,
                )
        fixed.append(m)
    return fixed, swapped


def _enforce_prime_golden_min(self, selection: list) -> tuple[list, bool]:
    """Prime-only: ensure ≥ PRIME_MIN_GOLDEN_WARFARES warfare picks come
    from the configured golden (seeding warfare) list. If the upstream
    picker chose fewer, swap in the most-stale (least-recently-played)
    golden warfares, and remove the most-recently-played non-golden
    warfares to make room.

    Returns (new_selection, modified)."""
    cfg = _config()
    if not cfg.enabled or not cfg.warfare_layer_ids:
        return selection, False

    golden_ids = {gid.lower() for gid in cfg.warfare_layer_ids}
    warfares = [m for m in selection if "warfare" in m.id.lower()]
    if len(warfares) < PRIME_MIN_GOLDEN_WARFARES:
        # Not enough warfare slots to enforce the rule
        return selection, False

    golden_in_sel = [m for m in warfares if m.id.lower() in golden_ids]
    needed = PRIME_MIN_GOLDEN_WARFARES - len(golden_in_sel)
    if needed <= 0:
        return selection, False

    sel_ids = {m.id.lower() for m in selection}

    # Candidate golden layers not already in selection
    candidates = []
    for gid in cfg.warfare_layer_ids:
        if gid.lower() in sel_ids:
            continue
        try:
            candidates.append(parse_layer(gid))
        except Exception as e:
            logger.warning("votemap_seeding: golden layer %r unparseable: %s", gid, e)
    if not candidates:
        return selection, False

    last_played = _last_played_index()
    # Prefer golden maps not played for a while (high staleness)
    candidates.sort(key=lambda m: -_staleness(m.id, last_played))
    to_add = candidates[: min(needed, len(candidates))]

    # Pick which non-golden warfares to drop: most recently played first
    non_golden_warfares = [m for m in warfares if m.id.lower() not in golden_ids]
    non_golden_warfares.sort(key=lambda m: _staleness(m.id, last_played))
    to_remove_ids = {m.id for m in non_golden_warfares[: len(to_add)]}

    if not to_remove_ids:
        return selection, False

    new_selection = [m for m in selection if m.id not in to_remove_ids] + to_add
    logger.info(
        "votemap_seeding: prime golden-min enforced — added %s (stale), "
        "removed %s (recent); now %d/%d golden warfares in selection",
        [m.id for m in to_add],
        sorted(to_remove_ids),
        len(golden_in_sel) + len(to_add),
        len(warfares),
    )
    return new_selection, True


def _patched_gen_selection(self):
    """Wrap upstream gen_selection with two post-processing steps:

    1. During SEEDING:   dedup offensive vs warfare base maps so the vote
                         shows 5 distinct maps even if the picker overlaps.
    2. During PRIME:     ensure at least PRIME_MIN_GOLDEN_WARFARES of the
                         warfare picks come from the golden seeding list,
                         preferring least-recently-played golden maps.
                         The remaining slots stay random from the full
                         prime whitelist (variety).
    """
    _original_gen_selection(self)

    selection = self.get_selection()
    if not selection:
        return

    if is_seeding_now(self.rcon):
        new_sel, swapped = _dedup_offensive_against_warfare(self, selection)
        if swapped:
            self.set_selection(selection=new_sel)
        return

    # Prime time: promote golden warfares
    new_sel, modified = _enforce_prime_golden_min(self, selection)
    if modified:
        self.set_selection(selection=new_sel)


VoteMap.gen_selection = _patched_gen_selection  # type: ignore[method-assign]


# Log effective config at startup for ops visibility (numbers come from
# the Redis-backed UserConfig, not module constants).
try:
    _startup_cfg = _config()
    logger.info(
        "votemap_seeding: patched (enabled=%s, threshold=%d, hours=[%d,%d), "
        "%d warfare layers + %d offensive layers, dedup ON)",
        _startup_cfg.enabled,
        _startup_cfg.player_threshold,
        _startup_cfg.seeding_hour_start,
        _startup_cfg.seeding_hour_end,
        len(_startup_cfg.warfare_layer_ids),
        len(_startup_cfg.offensive_layer_ids),
    )
except Exception as _e:
    logger.warning("votemap_seeding: could not log startup config: %s", _e)
