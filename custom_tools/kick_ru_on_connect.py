"""
Kick on connect for players whose Steam profile lists Russia as their country.

Editorial decision for a Ukrainian community server hosting players who have
lost friends and family to the russian invasion. Steam's loccountrycode is
self-reported (a player can change it to anything), so this is a symbolic
filter, not an airtight one — anyone determined to play can simply set their
Steam country to another flag. The intent here is to make clear what kind of
community this is.

Knobs (edit and `docker compose restart stats_app` — hooks pick up on next
container restart since this module is imported at process start):

  KICK_RU_ENABLED       Master switch. Set False to disable without code
                        changes elsewhere.
  KICK_RU_COUNTRIES     ISO-3166-1 alpha-2 codes to act on. Default: {"RU"}.
  KICK_RU_MESSAGE       Reason text shown to the player on the kick screen.
                        Default: "ПТН ПНХ".
  KICK_RU_VIP_EXEMPT    If True, VIPs (allowlisted friends/contributors) are
                        skipped. Use this to whitelist specific russian users
                        you want to keep — grant them VIP.

Notes:
  * Hook runs at default priority, which is AFTER `update_player_steaminfo_on_connect`
    (priority 0), so Steam info is already populated for fresh joiners.
  * If Steam API was unavailable and we have no country on file, the player
    is left alone (we don't kick on missing data).
  * Every kick is mirrored to the Discord audit channel.
"""
import logging

from rcon.discord import send_to_discord_audit
from rcon.rcon import Rcon
from rcon.steam_utils import get_steam_profile
from rcon.types import StructuredLogLineWithMetaData

logger = logging.getLogger(__name__)

# ---- Config ----------------------------------------------------------------
KICK_RU_ENABLED: bool = True
KICK_RU_COUNTRIES: set[str] = {"RU"}
KICK_RU_MESSAGE: str = "ПТН ПНХ"
KICK_RU_VIP_EXEMPT: bool = True
KICK_RU_AUDIT_AUTHOR: str = "kick_ru"
# ----------------------------------------------------------------------------


def _player_country(player_id: str) -> str | None:
    """Return uppercase ISO-3166-1 alpha-2 country for the player, or None."""
    try:
        profile = get_steam_profile(steam_id_64=player_id)
    except Exception:
        logger.exception("kick_ru: get_steam_profile failed for %s", player_id)
        return None
    if not profile:
        return None
    country = profile.get("country")
    return country.upper() if country else None


def _is_vip(rcon: Rcon, player_id: str) -> bool:
    try:
        return any(v.get("player_id") == player_id for v in rcon.get_vip_ids())
    except Exception:
        logger.exception("kick_ru: VIP lookup failed for %s", player_id)
        # Fail closed on VIP check — if we can't tell, do not kick.
        # Better to leave one russian online than to accidentally kick a friend.
        return True


def kick_ru_on_connected(
    rcon: Rcon, struct_log: StructuredLogLineWithMetaData
) -> None:
    if not KICK_RU_ENABLED:
        return

    player_id = struct_log.get("player_id_1")
    player_name = struct_log.get("player_name_1")
    if not player_id:
        return

    country = _player_country(player_id)
    if country not in KICK_RU_COUNTRIES:
        return

    if KICK_RU_VIP_EXEMPT and _is_vip(rcon, player_id):
        logger.info(
            "kick_ru: %s (%s) country=%s is VIP — skipping",
            player_name, player_id, country,
        )
        return

    logger.info(
        "kick_ru: kicking %s (%s) country=%s message=%r",
        player_name, player_id, country, KICK_RU_MESSAGE,
    )
    try:
        rcon.kick(
            player_id=player_id,
            reason=KICK_RU_MESSAGE,
            by=KICK_RU_AUDIT_AUTHOR,
            player_name=player_name,
        )
    except Exception:
        logger.exception(
            "kick_ru: kick failed for %s (%s)", player_name, player_id
        )
        return

    try:
        send_to_discord_audit(
            message=(
                f"Kicked **{player_name}** (`{player_id}`) — "
                f"Steam country `{country}` — reason: {KICK_RU_MESSAGE}"
            ),
            command_name="kick_ru",
            by=KICK_RU_AUDIT_AUTHOR,
        )
    except Exception:
        logger.exception(
            "kick_ru: discord audit failed for %s (%s)", player_name, player_id
        )
