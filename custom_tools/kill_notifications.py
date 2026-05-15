"""Per-kill admin-popup notifications.

After every kill, the killer gets a short admin popup showing whom they
killed and with what weapon. Default ON; players opt out with `!lk off`
in chat (and back in with `!lk on`).

Opt-out state lives in Redis (no DB schema needed) under
`kill_notif:disabled:<player_id>` — presence means opted out.

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

# Chat commands (case-insensitive match on the whole sub_content)
_CMD_OFF = "!lk off"
_CMD_ON = "!lk on"
_CMD_STATUS = "!lk"

# Default save_message=False so the popup doesn't clutter the admin log.
_MESSAGE_FOOTER = "\n(вимкнути: !lk off)"


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
    """Handle `!lk`, `!lk on`, `!lk off` chat commands."""
    text = (log.get("sub_content") or "").strip().lower()
    if not text.startswith("!lk"):
        return

    player_id = log.get("player_id_1")
    if not player_id:
        return

    if text == _CMD_OFF:
        _set_disabled(player_id, True)
        reply = (
            "Сповіщення про вбивства ВИМКНУТО.\n"
            "Повернути: !lk on"
        )
    elif text == _CMD_ON:
        _set_disabled(player_id, False)
        reply = (
            "Сповіщення про вбивства УВІМКНЕНО.\n"
            "Вимкнути: !lk off"
        )
    elif text == _CMD_STATUS:
        state = "вимкнено" if _is_disabled(player_id) else "увімкнено"
        reply = (
            f"Сповіщення про вбивства: {state}.\n"
            "!lk on / !lk off — змінити"
        )
    else:
        # `!lk something_else` — ignore silently so users typing unrelated
        # !lk-prefixed words (rare but possible) don't get spammed.
        return

    try:
        rcon.message_player(
            player_id=player_id,
            message=reply,
            by="kill_notifications",
            save_message=False,
        )
    except Exception as e:
        logger.debug("kill_notifications: !lk reply failed for %s: %s", player_id, e)


logger.info("kill_notifications: registered @on_kill + @on_chat handlers (default ON, opt-out via !lk off)")
