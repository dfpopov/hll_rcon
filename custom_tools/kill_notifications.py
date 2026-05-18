"""Per-kill admin-popup notifications.

After every kill, the killer gets a short admin popup showing whom they
killed and with what weapon. Default ON; players opt out with `!kn off`
in chat (and back in with `!kn on`).

Command word: `!kn` (kill notify). NOT `!lk` — that one is already
taken by CRCON's built-in "last killed by you" command, so a toggle on
`!lk` would clash with the upstream reply.

Opt-out state lives in Redis (no DB schema needed) under
`kill_notif:disabled:<player_id>` — presence means opted out.

Burst aggregation: when the first kill of a burst arrives we arm a
timer for AGGREGATION_WINDOW_SECONDS. Any kills the same player makes
within that window are counted but DON'T trigger their own popup;
when the timer fires we send ONE popup with the total count and the
first victim's name. So a 3-kill spree → 1 popup with
"+3: <first_name> (ще +2)". Keeps the UI calm and limits RCON load
on busy 100-player matches.

Wiring: imported for side effect in `rcon/hooks.py` so the @on_kill /
@on_chat handlers register at backend / supervisor startup.

Editorial notes:
  - Ukrainian wording matches the rest of HILF UA messaging.
  - No notification on teamkills (separate `@on_tk` handler could be
    added later; for now teamkill popups would compete with the
    upstream punish flow and add noise).
  - No notification on suicide (killer_id == victim_id).
  - Empty weapon string is replaced with «-» so the line stays one row.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

import redis

from rcon.cache_utils import get_redis_pool
from rcon.logs.loop import on_chat, on_kill
from rcon.models import SteamInfo, enter_session
from rcon.rcon import Rcon
from rcon.types import StructuredLogLineWithMetaData

logger = logging.getLogger(__name__)

# Per-player language buckets. CRCON's Steam country code resolution is
# the same source live_topstats uses (see get_player_language there).
# We only need a binary UA/EN split for kill notifications.
_UA_COUNTRIES = frozenset({
    "UA", "RU", "BY", "MD", "KZ", "KG", "TJ", "TM", "UZ", "AZ", "AM", "GE",
})


def _player_lang(player_id: str) -> str:
    """Return 'ua' for ex-USSR Steam countries, 'en' otherwise (default).
    Defensive: any DB hiccup → 'en' (broader audience, safer fallback)."""
    try:
        with enter_session() as sess:
            si = (
                sess.query(SteamInfo)
                .join(SteamInfo.player)
                .filter(SteamInfo.player.has(player_id=player_id))
                .first()
            )
            if si and si.country and si.country.upper() in _UA_COUNTRIES:
                return "ua"
    except Exception as e:
        logger.debug("kill_notifications: lang lookup failed for %s: %s", player_id, e)
    return "en"


# Per-language message strings. Keep all under ~40 chars per line so the
# in-game popup stays in one screen-line on HLL's narrow admin overlay.
_MESSAGES = {
    "en": {
        "footer":          "\n!kn off",
        "burst_suffix":    " (+{n} more)",
        "off_reply":       "Popups OFF.\n!kn on / !lk",
        "on_reply":        "Popups ON.\n!kn off",
        "status_on":       "Popups: ON.\n!kn off",
        "status_off":      "Popups: OFF.\n!kn on / !lk",
        "lk_hint":         "Auto popups: !kn on",
    },
    "ua": {
        "footer":          "\n!kn off",
        "burst_suffix":    " (+{n} ще)",
        "off_reply":       "Сповіщення ВИМК.\n!kn on / !lk",
        "on_reply":        "Сповіщення УВІМК.\n!kn off",
        "status_on":       "Сповіщення: УВІМК.\n!kn off",
        "status_off":      "Сповіщення: ВИМК.\n!kn on / !lk",
        "lk_hint":         "Авто-сповіщення: !kn on",
    },
}


def _msg(player_id: str, key: str, **fmt) -> str:
    """Pick the message string for the player's language and substitute
    {n}/etc. tokens. Falls back to English if key missing in 'ua' bucket."""
    lang = _player_lang(player_id)
    s = _MESSAGES.get(lang, _MESSAGES["en"]).get(key) or _MESSAGES["en"][key]
    return s.format(**fmt) if fmt else s

_REDIS_KEY_PREFIX = "kill_notif:disabled:"

# Aggregation window: when the first kill arrives we start a timer for
# this many seconds. Any kills the same player makes within that window
# are counted but DON'T trigger their own popup; when the timer fires we
# send one popup mentioning the count. So a 3-kill spree → 1 popup with
# "+3: <first_name> ще +2 — лише перше імʼя :D".
AGGREGATION_WINDOW_SECONDS = 1.0

# Chat commands. Match the whole sub_content (case-insensitive).
# We use `!kn` because `!lk` is already a CRCON built-in (shows last
# player you killed) and we don't want both handlers replying to it.
_CMD_PREFIX = "!kn"
_CMD_OFF = "!kn off"
_CMD_ON = "!kn on"
_CMD_STATUS = "!kn"

# (Per-language footer lives in _MESSAGES above; _msg(player_id, "footer")
# returns the right one. Kept tight — just the command, no extra prose.)


def _redis() -> redis.StrictRedis:
    return redis.StrictRedis(connection_pool=get_redis_pool())


def _is_disabled(player_id: str) -> bool:
    """True = player opted out, don't send notifications."""
    try:
        return _redis().get(_REDIS_KEY_PREFIX + player_id) == b"1"
    except Exception:
        # On Redis hiccup, default to sending — opt-out is an explicit
        # action; transient errors shouldn't silently suppress messages.
        return False


def _set_disabled(player_id: str, disabled: bool) -> None:
    key = _REDIS_KEY_PREFIX + player_id
    if disabled:
        _redis().set(key, "1")
    else:
        _redis().delete(key)


# ── Burst aggregation state ────────────────────────────────────────────
# Process-local: keyed by killer player_id, holds the first victim name
# captured for this burst and a running kill count. A threading.Timer is
# armed when the burst starts and fires _flush_burst when AGGREGATION_
# WINDOW_SECONDS elapses, sending one combined popup. State is in-memory
# (not Redis) because the timer thread must run in the same process that
# observed the kills.
_pending_lock = threading.Lock()
_pending: dict[str, dict] = {}


def _flush_burst(rcon: Rcon, killer_id: str) -> None:
    """Timer callback — assemble and send the aggregated popup."""
    with _pending_lock:
        data = _pending.pop(killer_id, None)
    if not data:
        return

    n: int = data["count"]
    first: str = (data["first_victim"] or "?")[:24]

    footer = _msg(killer_id, "footer")
    if n == 1:
        message = f"+1: {first}{footer}"
    else:
        suffix = _msg(killer_id, "burst_suffix", n=n - 1)
        message = f"+{n}: {first}{suffix}{footer}"

    try:
        rcon.message_player(
            player_id=killer_id,
            message=message,
            by="kill_notifications",
            save_message=False,
        )
    except Exception as e:
        logger.debug("kill_notifications: flush send failed for %s: %s", killer_id, e)


@on_kill
def _notify_killer(rcon: Rcon, log: StructuredLogLineWithMetaData) -> None:
    """Aggregate kills within AGGREGATION_WINDOW into a single popup.

    First kill starts a burst: record victim name, set count=1, arm a
    timer. Subsequent kills by the same killer within the window just
    bump the count; no popup yet. When the timer fires, _flush_burst
    sends one popup mentioning how many kills happened — but only the
    first victim's name is shown (others omitted to keep popup small)."""
    killer_id = log.get("player_id_1")
    victim_name = log.get("player_name_2")
    victim_id = log.get("player_id_2")

    if not killer_id or not victim_name:
        return
    if victim_id and killer_id == victim_id:
        return  # suicide — no popup
    if _is_disabled(killer_id):
        return

    with _pending_lock:
        if killer_id in _pending:
            # Burst already collecting — just bump the count
            _pending[killer_id]["count"] += 1
            return

        # New burst — arm timer (will call _flush_burst after window)
        timer = threading.Timer(
            AGGREGATION_WINDOW_SECONDS,
            _flush_burst,
            args=(rcon, killer_id),
        )
        timer.daemon = True
        _pending[killer_id] = {
            "first_victim": victim_name,
            "count": 1,
            "timer": timer,
        }
        timer.start()


@on_chat
def _toggle_via_chat(rcon: Rcon, log: StructuredLogLineWithMetaData) -> None:
    """Handle `!kn`, `!kn on`, `!kn off` chat commands."""
    text = (log.get("sub_content") or "").strip().lower()
    if not text.startswith(_CMD_PREFIX):
        return

    player_id = log.get("player_id_1")
    if not player_id:
        return

    if text == _CMD_OFF:
        _set_disabled(player_id, True)
        reply = _msg(player_id, "off_reply")
    elif text == _CMD_ON:
        _set_disabled(player_id, False)
        reply = _msg(player_id, "on_reply")
    elif text == _CMD_STATUS:
        key = "status_off" if _is_disabled(player_id) else "status_on"
        reply = _msg(player_id, key)
    else:
        # `!kn something_else` — ignore silently so users typing unrelated
        # !kn-prefixed words (rare but possible) don't get spammed.
        return

    try:
        rcon.message_player(
            player_id=player_id,
            message=reply,
            by="kill_notifications",
            save_message=False,
        )
    except Exception as e:
        logger.debug("kill_notifications: !kn reply failed for %s: %s", player_id, e)


@on_chat
def _augment_lk_with_hint(rcon: Rcon, log: StructuredLogLineWithMetaData) -> None:
    """When a player types CRCON's built-in `!lk` (or alias `!vc`) and
    they're currently OPTED OUT of auto-notifications, append a small
    hint pointing them at `!kn on` so they discover the auto mode.

    Runs as a separate @on_chat handler so we DON'T disturb CRCON's
    own `!lk` reply ("you killed X with Y") — both popups will show:
    one from CRCON with the kill info, one from us with the hint.

    Skipped when the player is already opted-IN (default state): they're
    already getting auto-notifications, the hint would be redundant.
    """
    text = (log.get("sub_content") or "").strip().lower()
    if text not in ("!lk", "!vc"):
        return
    player_id = log.get("player_id_1")
    if not player_id:
        return
    if not _is_disabled(player_id):
        return  # already opted-in, no need to advertise

    hint = _msg(player_id, "lk_hint")
    try:
        rcon.message_player(
            player_id=player_id,
            message=hint,
            by="kill_notifications",
            save_message=False,
        )
    except Exception as e:
        logger.debug("kill_notifications: !lk hint failed for %s: %s", player_id, e)


logger.info(
    "kill_notifications: registered @on_kill + @on_chat handlers "
    "(default ON, opt-out via !kn off, aggregation window %.1fs)",
    AGGREGATION_WINDOW_SECONDS,
)
