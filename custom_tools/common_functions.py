"""
common_functions.py

Common functions and variables
for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool)
custom plugins

Source : https://github.com/ElGuillermo

Feel free to use/modify/distribute, as long as you keep this note in your code
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager
from typing import Generator, Tuple
import requests
import discord
from discord.errors import HTTPException, NotFound
from requests.exceptions import ConnectionError, RequestException
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from rcon.rcon import Rcon
from rcon.game_logs import get_recent_logs
from rcon.steam_utils import get_steam_api_key
from rcon.user_config.rcon_server_settings import RconServerSettingsUserConfig
from rcon.utils import get_server_number


# Configuration (you don't have to change these)
# ----------------------------------------------

# Discord : embed author icon
DISCORD_EMBED_AUTHOR_ICON_URL = (
    "https://cdn.discordapp.com/icons/316459644476456962/73a28de670af9e6569f231c9385398f3.webp?size=64"
)

# Discord : default avatars
DEFAULT_AVATAR_STEAM = (
    "https://steamcdn-a.akamaihd.net/steamcommunity/public/images/avatars/b5/b5bd56c1aa4644a474a2e4972be27ef9e82e517e_medium.jpg"
)
DEFAULT_AVATAR_GAMEPASS = (
    "https://raw.githubusercontent.com/ElGuillermo/HLL_CRCON_custom_common_functions.py/refs/heads/main/avatar_default_nonsteam.png"
)

# Discord : external profile infos urls
STEAM_PROFILE_INFO_URL = "https://steamcommunity.com/profiles/"  # + id
GAMEPASS_PROFILE_INFO_URL = "https://xboxgamertag.com/search/"  # + name (spaces are replaced by -)

# Clan related (as set in /settings/rcon-server)
try:
    config = RconServerSettingsUserConfig.load_from_db()
    CLAN_URL = str(config.discord_invite_url)
    DISCORD_EMBED_AUTHOR_URL = str(config.server_url)
except Exception:
    CLAN_URL = ""
    DISCORD_EMBED_AUTHOR_URL = ""

# Static lists
# Used in :
#   watch_killrate.py
WEAPONS_ARTILLERY = [
    # US
    "155MM HOWITZER [M114]",
    # GER
    "150MM HOWITZER [sFH 18]",
    # USSR
    "122MM HOWITZER [M1938 (M-30)]",
    # GB
    "QF 25-POUNDER [QF 25-Pounder]"
]

# Used in :
#   watch_killrate.py
WEAPONS_MG = [
    # US
    "BROWNING M1919",
    # GER
    "MG34",
    "MG42",
    # USSR
    "DP-27",
    # GB
    "Lewis Gun"
]

# Used in :
#   watch_roles
OFFICERS = {'armycommander', 'officer', 'tankcommander', 'spotter', 'artilleryobserver'}

# Used in :
#   watch_roles
SUPPORT_CANDIDATES = {'antitank', 'automaticrifleman', 'assault', 'heavymachinegunner', 'rifleman', 'engineer', 'medic'}


# (End of configuration)
# -----------------------------------------------------------------------------

class Base(DeclarativeBase):
    """
    Adapted from scorebot... Not sure about how it's working :/
    """


class WatchBalanceMessage(Base):
    """
    Adapted from scorebot... Not sure about how it's working :/
    """
    __tablename__ = "stats_messages"
    server_number: Mapped[int] = mapped_column(primary_key=True)
    message_type: Mapped[str] = mapped_column(default="live", primary_key=True)
    message_id: Mapped[int] = mapped_column(primary_key=True)
    webhook: Mapped[str] = mapped_column(primary_key=True)


# Used in :
#   watch_balance
def bold_the_highest(
    first_value: int,
    second_value: int
) -> Tuple[str, str]:
    """
    Returns two strings, the highest value formatted in bold
    """
    if first_value > second_value:
        return f"**{first_value}**", str(second_value)
    if first_value < second_value:
        return str(first_value), f"**{second_value}**"
    return str(first_value), str(second_value)


def discord_embed_selfrefresh_cleanup_orphaned_messages(
    session: Session, server_number: int, webhook_url: str
) -> None:
    """
    Adapted from scorebot... Not sure about how it's working :/
    """
    stmt = (
        select(WatchBalanceMessage)
        .where(WatchBalanceMessage.server_number == server_number)
        .where(WatchBalanceMessage.webhook == webhook_url)
    )
    res = session.scalars(stmt).one_or_none()
    if res:
        session.delete(res)


@contextmanager
def discord_embed_selfrefresh_enter_session(engine) -> Generator[Session, None, None]:
    """
    Adapted from scorebot... Not sure about how it's working :/
    """
    with Session(engine) as session:
        session.begin()
        try:
            yield session
        except:
            session.rollback()
            raise
        else:
            session.commit()


def discord_embed_selfrefresh_fetch_existing(
    session: Session, server_number: str, webhook_url: str
) -> WatchBalanceMessage | None:
    """
    Adapted from scorebot... Not sure about how it's working :/
    """
    stmt = (
        select(WatchBalanceMessage)
        .where(WatchBalanceMessage.server_number == server_number)
        .where(WatchBalanceMessage.webhook == webhook_url)
    )
    return session.scalars(stmt).one_or_none()


def get_avatar_url(
    player_id: str
) -> str:
    """
    Returns the avatar url from a player ID
    Steam players can have an avatar
    GamePass players will get a default avatar
    """
    if len(player_id) == 17 and player_id.isdigit():
        try:
            return get_steam_avatar(player_id)
        except Exception:
            return DEFAULT_AVATAR_STEAM
    return DEFAULT_AVATAR_GAMEPASS


def get_external_profile_url(
    player_id: str,
    player_name: str,
) -> str:
    """
    Constructs the external profile url for Steam or GamePass
    """
    ext_profile_url = ""
    if len(player_id) == 17 and player_id.isdigit():
        ext_profile_url = f"{STEAM_PROFILE_INFO_URL}{player_id}"
    elif len(player_id) > 17:
        gamepass_pseudo_url = player_name.replace(" ", "-")
        ext_profile_url = f"{GAMEPASS_PROFILE_INFO_URL}{gamepass_pseudo_url}"
    return ext_profile_url


def get_match_elapsed_secs() -> float:
    """
    Returns the number of seconds since MATCH START
    """
    secs_since_match_start = 1
    logs_match_start = get_recent_logs(
        action_filter=["MATCH START"],
        exact_action=True
    )
    match_start_timestamp = logs_match_start["logs"][0]["timestamp_ms"] / 1000
    secs_since_match_start = (
        datetime.now() - datetime.fromtimestamp(match_start_timestamp)
    ).total_seconds()
    return secs_since_match_start


def get_steam_avatar(
    player_id: str,
    avatar_size: str = "avatarmedium"
) -> str:
    """
    Returns the Steam avatar image url, according to desired size
    Available avatar_size :
        "avatar" : 32x32 ; "avatarmedium" : 64x64 ; "avatarfull" : 184x184
    """
    try:
        steam_api_key = get_steam_api_key()
        if not steam_api_key or steam_api_key == "":
            return DEFAULT_AVATAR_STEAM
    except Exception:
        return DEFAULT_AVATAR_STEAM

    steam_api_url = (
        "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
        f"?key={steam_api_key}"
        f"&steamids={player_id}"
    )
    try:
        steam_api_json = requests.get(steam_api_url, timeout=10)
        steam_api_json_parsed = json.loads(steam_api_json.text)
        return steam_api_json_parsed["response"]["players"][0][avatar_size]
    except Exception:
        return DEFAULT_AVATAR_STEAM


def green_to_red(
        value: float,
        min_value: float,
        max_value: float = 0.0
    ) -> str:
    """
    Returns an string value
    corresponding to a color
    from plain green 00ff00 (value <= min_value)
    to plain red ff0000 (value >= max_value)
    You will have to convert it in the caller code :
    ie for a decimal Discord embed color : int(hex_color, base=16)
    """
    if max_value == 0.0:
        max_value = min_value * 2
    if value < min_value:
        value = min_value
    elif value > max_value:
        value = max_value
    if max_value <= min_value:
        return "c0c0c0"
    range_value = max_value - min_value
    ratio = (value - min_value) / range_value
    red = int(255 * ratio)
    green = int(255 * (1 - ratio))
    hex_color = f"{red:02x}{green:02x}00"
    return hex_color


def seconds_until_start(schedule) -> int:
    """
    Outside scheduled activity :
        Returns the number of seconds until the next scheduled activity time
    During scheduled activity :
        Returns 0

    schedule example :
    # Activity schedule (UTC time)
    # FR setting : (heure d'hiver = UTC+1 ; heure d'été = UTC+2)
    # specified hours : "0: (4, 30, 21, 15)" means "active on mondays, from 4:30am to 9:15pm"
    # all day long : "3: (0, 0, 23, 59)" means "active on thursdays, from 0:00am to 11:59pm"

    SCHEDULE = {
        0: (3, 1, 21, 0),  # Monday
        1: (3, 1, 21, 0),  # Tuesday
        2: (3, 1, 21, 0),  # Wednesday
        3: (3, 1, 21, 0),  # Thursday
        4: (3, 1, 21, 0),  # Friday
        5: (3, 1, 21, 0),  # Saturday
        6: (3, 1, 21, 0)  # Sunday
    }
    """
    # Get the user config
    now = datetime.now(timezone.utc)
    (
        today_start_hour,
        today_start_minute,
        today_end_hour,
        today_end_minute
    ) = schedule[now.weekday()]

    # Build a timestamp for today's start time
    today_dt = datetime.today()
    today_start_str = (
        f"{today_dt.day}"
        f" {today_dt.month}"
        f" {today_dt.year}"
        f" {today_start_hour}"
        f" {today_start_minute}+0000"
    )
    today_start_dt = datetime.strptime(today_start_str, "%d %m %Y %H %M%z")

    # Build a timestamp for tomorrow's start time
    tomorrow_dt = datetime.today() + timedelta(days=1)
    if now.weekday() == 6:  # Today is sunday
        tomorrow_start_hour, tomorrow_start_minute, _, _ = schedule[0]
    else:
        tomorrow_start_hour, tomorrow_start_minute, _, _ = schedule[now.weekday()+1]
    tomorrow_start_str = (
        f"{tomorrow_dt.day}"
        f" {tomorrow_dt.month}"
        f" {tomorrow_dt.year}"
        f" {tomorrow_start_hour}"
        f" {tomorrow_start_minute}+0000"
    )
    tomorrow_start_dt = datetime.strptime(tomorrow_start_str, "%d %m %Y %H %M%z")

    # Evaluate the seconds to wait until the next activity time
    if (
        today_start_hour - now.hour > 0
        or (
            today_start_hour - now.hour == 0
            and today_start_minute - now.minute > 0
        )
    ):
        return_value = int((today_start_dt - now).total_seconds())
    elif (
        today_start_hour - now.hour < 0
        and (
            (
                today_end_hour - now.hour == 0
                and today_end_minute - now.minute <= 0
            )
            or today_end_hour - now.hour < 0
        )
    ):
        return_value = int((tomorrow_start_dt - now).total_seconds())
    else:
        return_value = 0
    return return_value


def discord_embed_selfrefresh_sendoredit(
    session: Session,
    webhook: discord.SyncWebhook,
    embeds: list[discord.Embed],
    server_number: int,
    message_id: int | None = None,
    edit: bool = True,
):
    """
    Adapted from scorebot... Not sure about how it's working :/
    """
    logger = logging.getLogger('rcon')
    # Force creation of a new message if message ID isn't set
    try:
        if not edit or message_id is None:
            logger.info("Creating a new message")
            message = webhook.send(embeds=embeds, wait=True)
            return message.id
        webhook.edit_message(message_id, embeds=embeds)
        return message_id

    # The message can't be found - delete its session
    except NotFound:
        logger.error("Message with ID: %s in our records does not exist", message_id)
        discord_embed_selfrefresh_cleanup_orphaned_messages(
            session=session,
            server_number=server_number,
            webhook_url=webhook.url,
        )
        return None

    # The message can't be reached at this time
    except (HTTPException, RequestException, ConnectionError):
        logger.exception("Temporary failure when trying to edit message ID: %s", message_id)

    # The message can't be edited - delete its session
    except Exception as error:
        logger.exception("Unable to edit message. Deleting record. Error : %s", error)
        discord_embed_selfrefresh_cleanup_orphaned_messages(
            session=session,
            server_number=server_number,
            webhook_url=webhook.url,
        )
        return None


def discord_embed_send(
        embed: discord.Embed,
        webhook: discord.Webhook,
        engine = None
    ) -> None:
    """
    Sends an embed message to Discord
    - one-time embed if no "engine" set
    - self-refreshing embed if "engine" set
    """
    logger = logging.getLogger('rcon')
    # seen_messages: set[int] = set()
    embeds = []
    embeds.append(embed)

    # Normal embed
    if engine is None:
        # embeds = []
        # embeds.append(embed)
        webhook.send(embeds=embeds, wait=True)
        return

    # Self-refreshing embed
    server_number = get_server_number()
    seen_messages: set[int] = set()
    with discord_embed_selfrefresh_enter_session(engine) as session:
        db_message = discord_embed_selfrefresh_fetch_existing(
            session=session,
            server_number=server_number,
            webhook_url=webhook.url,
        )

        # A previous message using this webhook exists in database
        if db_message:
            message_id = db_message.message_id
            if message_id not in seen_messages:
                logger.debug("Resuming with message_id %s", message_id)
                seen_messages.add(message_id)
            message_id = discord_embed_selfrefresh_sendoredit(
                session=session,
                webhook=webhook,
                embeds=embeds,
                server_number=int(server_number),
                message_id=message_id,
                edit=True,
            )

        # There is no previous message using this webhook in database
        else:
            message_id = discord_embed_selfrefresh_sendoredit(
                session=session,
                webhook=webhook,
                embeds=embeds,
                server_number=int(server_number),
                message_id=None,
                edit=False,
            )
            if message_id:
                db_message = WatchBalanceMessage(
                    server_number=server_number,
                    message_id=message_id,
                    webhook=webhook.url,
                )
                session.add(db_message)


def is_vip_for_less_than_xh(
        rcon: Rcon,
        player_id: str,
        vip_delay_hours: int
    ):
    """
    returns 'true' if player has no VIP or a VIP that expires in less than vip_delay_hours,
    'false' if he has a VIP that expires in more than vip_delay_hours or no VIP at all.
    """
    actual_vips = rcon.get_vip_ids()
    for item in actual_vips:
        if item['player_id'] == player_id and item['vip_expiration'] is not None:
            vip_expiration_output = str(item['vip_expiration'])
            vip_expiration = datetime.fromisoformat(vip_expiration_output)
            if vip_expiration < datetime.now(timezone.utc) + timedelta(hours=vip_delay_hours):
                return True
            return False
    return True  # player wasn't in the VIP list


# Used in:
#   watch_balance
def team_view_stats(rcon: Rcon):
    """
    Get the get_team_view data
    and gather the infos according to the squad types and soldier roles
    """
    all_teams = []
    all_players = []
    all_commanders = []
    all_infantry_players = []
    all_armor_players = []
    all_artillery_players = []
    all_recon_players = []
    all_infantry_squads = []
    all_armor_squads = []
    all_artillery_squads = []
    all_recon_squads = []

    try:
        get_team_view: dict = rcon.get_team_view()
    except Exception as error:
        logger = logging.getLogger(__name__)
        logger.error("Command failed : get_team_view()\n%s", error)
        return (
            all_teams,
            all_players,
            all_commanders,
            all_infantry_players,
            all_armor_players,
            all_artillery_players,
            all_recon_players,
            all_infantry_squads,
            all_armor_squads,
            all_artillery_squads,
            all_recon_squads
        )

    for team in ["allies", "axis"]:

        if team in get_team_view:

            # Commanders
            if get_team_view[team]["commander"] is not None:
                all_players.append(get_team_view[team]["commander"])
                all_commanders.append(get_team_view[team]["commander"])

            for squad in get_team_view[team]["squads"]:

                squad_data = get_team_view[team]["squads"][squad]
                squad_data["team"] = team  # Injection du nom de team dans la branche de la squad

                # Infantry
                if squad_data["type"] == "infantry":
                    all_players.extend(squad_data["players"])
                    all_infantry_players.extend(squad_data["players"])
                    squad_data.pop("players", None)
                    all_infantry_squads.append({squad: squad_data})

                # Armor
                elif squad_data["type"] == "armor":
                    all_players.extend(squad_data["players"])
                    all_armor_players.extend(squad_data["players"])
                    squad_data.pop("players", None)
                    all_armor_squads.append({squad: squad_data})

                # Artillery
                elif squad_data["type"] == "artillery":
                    all_players.extend(squad_data["players"])
                    all_artillery_players.extend(squad_data["players"])
                    squad_data.pop("players", None)
                    all_artillery_squads.append({squad: squad_data})

                # Recon
                elif squad_data["type"] == "recon":
                    all_players.extend(squad_data["players"])
                    all_recon_players.extend(squad_data["players"])
                    squad_data.pop("players", None)
                    all_recon_squads.append({squad: squad_data})

            # Teams global stats
            team_data = get_team_view[team]
            team_data.pop("squads", None)
            team_data.pop("commander", None)
            all_teams.append({team: team_data})

    return (
        all_teams,
        all_players,
        all_commanders,
        all_infantry_players,
        all_armor_players,
        all_artillery_players,
        all_recon_players,
        all_infantry_squads,
        all_armor_squads,
        all_artillery_squads,
        all_recon_squads
    )
