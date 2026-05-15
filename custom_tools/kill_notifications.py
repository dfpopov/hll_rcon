"""Per-kill admin-popup notifications.

After every kill, the killer gets a short admin popup showing whom they
killed and with what weapon. Default ON; players opt out with `!kn off`
in chat (and back in with `!kn on`).

Command word: `!kn` (kill notify). NOT `!lk` — that one is already
taken by CRCON's built-in "last killed by you" command, so a toggle on
`!lk` would clash with the upstream reply.

Opt-out state lives in Redis (no DB schema needed) under
`kill_notif:disabled:<player_id>` — presence means opted out.

Rate limit: at most one popup per killer per RATE_LIMIT_SECONDS.
Prevents both UI spam (top fragger getting 5 popups in 1 second) and
RCON-channel pressure on a busy 100-player server.

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

import redis

from rcon.cache_utils import get_redis_pool
from rcon.logs.loop import on_chat, on_kill
from rcon.rcon import Rcon
from rcon.types import StructuredLogLineWithMetaData

logger = logging.getLogger(__name__)

_REDIS_KEY_PREFIX = "kill_notif:disabled:"
_REDIS_COOLDOWN_PREFIX = "kill_notif:cooldown:"

# At most one popup per killer in this many seconds. Multi-kill bursts
# collapse into a single notification (showing only the FIRST victim in
# the window — keeps the in-game UI calm and limits RCON load).
RATE_LIMIT_SECONDS = 3

# Chat commands. Match the whole sub_content (case-insensitive).
# We use `!kn` because `!lk` is already a CRCON built-in (shows last
# player you killed) and we don't want both handlers replying to it.
_CMD_PREFIX = "!kn"
_CMD_OFF = "!kn off"
_CMD_ON = "!kn on"
_CMD_STATUS = "!kn"

# Default save_message=False so the popup doesn't clutter the admin log.
_MESSAGE_FOOTER = "\n(вимкнути: !kn off)"


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


def _is_on_cooldown(player_id: str) -> bool:
    """True if the killer already got a popup within RATE_LIMIT_SECONDS.

    We use SET NX with EX semantics — atomic test-and-set: if the cooldown
    key wasn't there, set it (return False = can send); if it was there,
    don't set (return True = skip)."""
    try:
        key = _REDIS_COOLDOWN_PREFIX + player_id
        # SET key 1 NX EX <seconds> — returns True if key was set, None if it existed
        was_set = _redis().set(key, "1", nx=True, ex=RATE_LIMIT_SECONDS)
        return not bool(was_set)
    except Exception:
        return False  # on Redis hiccup, allow the send


@on_kill
def _notify_killer(rcon: Rcon, log: StructuredLogLineWithMetaData) -> None:
    """Send the killer a popup with the victim name + weapon."""
    killer_id = log.get("player_id_1")
    victim_name = log.get("player_name_2")
    victim_id = log.get("player_id_2")
    weapon = log.get("weapon") or "-"

    if not killer_id or not victim_name:
        return
    if victim_id and killer_id == victim_id:
        return  # suicide — no popup
    if _is_disabled(killer_id):
        return
    if _is_on_cooldown(killer_id):
        return  # multi-kill burst collapsed — wait for cooldown to expire

    # Trim name to keep the popup compact (in-game admin overlay is narrow)
    short_name = victim_name[:24]
    message = f"+1: {short_name}\n{weapon}{_MESSAGE_FOOTER}"

    try:
        rcon.message_player(
            player_id=killer_id,
            message=message,
            by="kill_notifications",
            save_message=False,
        )
    except Exception as e:
        # Don't spam logs — server can hiccup on individual sends; the
        # next kill will retry. Only debug-level on routine failures.
        logger.debug("kill_notifications: send failed for %s: %s", killer_id, e)


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
        reply = (
            "Сповіщення про вбивства ВИМКНУТО.\n"
            "Повернути: !kn on"
        )
    elif text == _CMD_ON:
        _set_disabled(player_id, False)
        reply = (
            "Сповіщення про вбивства УВІМКНЕНО.\n"
            "Вимкнути: !kn off"
        )
    elif text == _CMD_STATUS:
        state = "вимкнено" if _is_disabled(player_id) else "увімкнено"
        reply = (
            f"Сповіщення про вбивства: {state}.\n"
            "!kn on / !kn off — змінити"
        )
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


logger.info(
    "kill_notifications: registered @on_kill + @on_chat handlers "
    "(default ON, opt-out via !kn off, rate-limit %ds)",
    RATE_LIMIT_SECONDS,
)
