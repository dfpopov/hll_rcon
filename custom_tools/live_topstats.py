"""
live_topstats.py

A plugin for HLL CRCON (see : https://github.com/MarechJ/hll_rcon_tool)
that displays and rewards top players

Source : https://github.com/ElGuillermo

Feel free to use/modify/distribute, as long as you keep this note in your code
"""

from urllib.parse import urlparse                                # validate_url()
import re                                                        # validate_url()
from datetime import datetime, timedelta, timezone               # is_vip_for_less_than_xh(), # give_xh_vip()
from typing import get_origin, get_args, Any, Dict, List, Tuple  # validate_config_var()
from zoneinfo import ZoneInfo                                    # give_xh_vip()
import logging                                                   # logger setup
import os                                                        # logger setup
import discord

from rcon.rcon import Rcon, StructuredLogLineWithMetaData
from rcon.user_config.rcon_server_settings import RconServerSettingsUserConfig
from rcon.utils import get_server_number
from rcon.models import enter_session, SteamInfo  # get_player_language
import threading                                  # _lang_lock

from custom_tools.common_translations import TRANSL
import custom_tools.live_topstats_config as live_topstats_config


# Setup logger
os.makedirs('/logs', exist_ok=True)
logger = logging.getLogger('live_topstats_standalone')
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s')
    file_handler = logging.FileHandler('/logs/custom_tools_live_topstats.log', mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def validate_config_var(
        checked_value: Any, output_type: Any, default_value: Any,
        min_val=None, max_val=None, min_len=None, max_len=None,
        custom_check=None) -> Any:
    """
    Complete recursive validation engine with constraints.
    Handles nested types and checks for numeric ranges and lengths.
    """
    value = checked_value
    origin = get_origin(output_type) or output_type
    args = get_args(output_type)

    try:
        # Basic types conversion
        if origin in [int, float]:
            # Converts , to .
            if isinstance(value, str):
                value = value.replace(',', '.', 1).strip()
            value = origin(value)
            # Numeric range check
            if min_val is not None and value < min_val:
                return default_value
            if max_val is not None and value > max_val:
                return default_value

        elif origin is str:
            value = str(value)
            # String length check
            if min_len is not None and len(value) < min_len:
                return default_value
            if max_len is not None and len(value) > max_len:
                return default_value

        elif origin is bool:
            if isinstance(value, str):
                lower_val = value.lower()
                if lower_val in ['true', '1', 'y', 'yes', 'on', 'enable', 'enabled']:
                    value = True
                elif lower_val in ['false', '0', 'n', 'no', 'off', 'disable', 'disabled']:
                    value = False
                else: value = bool(value)
            else:
                value = bool(value)

        # Dict
        elif origin is dict or origin is Dict:
            if not isinstance(value, dict):
                return default_value
            if not args:
                final_val = value
            else:
                key_type, val_type = args[0], args[1]
                final_val = {
                    validate_config_var(k, key_type, k): validate_config_var(v, val_type, v)
                    for k, v in value.items()
                }
            value = final_val

        # List
        elif origin is list or origin is List:
            if not isinstance(value, list):
                return default_value
            if args:
                value = [validate_config_var(item, args[0], None) for item in value]

            # List length check
            if min_len is not None and len(value) < min_len:
                return default_value
            if max_len is not None and len(value) > max_len:
                return default_value

        # Tuple
        elif origin is tuple or origin is Tuple:
            if not isinstance(value, (list, tuple)):
                return default_value
            if args:
                value = tuple(
                    validate_config_var(value[i], args[i], None)
                    for i in range(min(len(value), len(args)))
                )
            else:
                value = tuple(value)

    except (ValueError, TypeError, IndexError, AttributeError):
        return default_value

    # Custom
    if custom_check is not None:
        try:
            if not custom_check(value):
                return default_value
        except Exception:
            return default_value

    return value


def validate_url(url: str, url_type: str = "any") -> bool:
    """
    Validates an url based on its type.
    """
    try:
        # Is this an url at least ?
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False

        # Any url (url_type = "any")
        if url_type == "any":
            return True

        # Specific urls types
        if url_type == "discord_webhook":
            # Pattern : https://discord.com/api/webhooks/{ID}/{TOKEN}
            # \d+ : several digits
            # [a-zA-Z0-9_-]+ : several letters, digits, underscores and hyphens
            webhook_pattern = r"^https://discord\.com/api/webhooks/\d+/[a-zA-Z0-9_-]+$"
            return bool(re.match(webhook_pattern, url))

        # unrecognized url_type
        return False

    except Exception:
        return False


# Validate config values
class ValidConfig:
    """
    Config file variables types
    (construction class)
    """
    lang: int
    enable_on_servers: list[int]
    display_on_matchend: bool
    chat_command: list[str]
    stats_to_display: dict
    defense_bonus: float
    support_bonus: float
    vip_commander_min_playtime_mins: int
    vip_commander_min_support_score: int
    seed_limit: int
    granted_vip_hours: int
    local_timezone: str
    discord_config: list[tuple[str, bool]]
    discord_embed_author_icon_url: str
    bot_name: str
    discord_embed_author_url: str


valid_config = ValidConfig()  # Create a new class


num_langs = len(next(iter(TRANSL.values())))
# Per-player language detection (used by stats_on_chat_command).
# Serialized with stats_on_match_end via _lang_lock to avoid race conditions
# when both events fire near-simultaneously (chat command mutates the shared
# valid_config.lang, matchend reads it — without a lock matchend could see
# a per-player language instead of the configured one).
_lang_lock = threading.RLock()


def get_player_language(player_id: str) -> int:
    """
    Determine the player's language from their Steam country code.
    Returns 6 (Ukrainian) for UA/RU/BY/MD/KZ/KG/TJ/TM/UZ/AZ/AM/GE,
    0 (English) for any other resolved country,
    or valid_config.lang as fallback on error/unknown.
    """
    try:
        with enter_session() as sess:
            steam_info = sess.query(SteamInfo).join(
                SteamInfo.player
            ).filter(
                SteamInfo.player.has(player_id=player_id)
            ).first()
            if steam_info and steam_info.country:
                country_code = steam_info.country.upper()
                if country_code in {'UA', 'RU', 'BY', 'MD', 'KZ', 'KG',
                                    'TJ', 'TM', 'UZ', 'AZ', 'AM', 'GE'}:
                    return 6  # Ukrainian (slot 6 in our common_translations.py)
                return 0  # English
    except Exception as e:
        logger.debug("Could not determine player language for %s: %s", player_id, e)
    return valid_config.lang


valid_config.lang = \
    validate_config_var(
        live_topstats_config.LANG,
        int, 0,
        min_val=0, max_val=num_langs - 1
    )
valid_config.enable_on_servers = \
    validate_config_var(
        live_topstats_config.ENABLE_ON_SERVERS,
        list[int], [],
        custom_check=lambda x: all(s > 0 for s in x)
    )
valid_config.display_on_matchend = \
    validate_config_var(
        live_topstats_config.DISPLAY_ON_MATCHEND,
        bool, False
    )
valid_config.chat_command = \
    validate_config_var(
        live_topstats_config.CHAT_COMMAND,
        list[str], ["!top"],
        min_len=1,
        custom_check=lambda x: all(s.startswith("!") for s in x)
    )
valid_config.stats_to_display = \
    validate_config_var(
        live_topstats_config.STATS_TO_DISPLAY,
        dict[str, dict[str, list[dict]]], {},
        custom_check=lambda d: (
            all(k in ["players", "squads"] for k in d.keys())
            and all(category in ["armycommander", "infantry", "armor", "artillery", "recon"] for sub_dict in d.values() for category in sub_dict.keys())
        )
    )
valid_config.defense_bonus = \
    validate_config_var(
        live_topstats_config.DEFENSE_BONUS,
        float, 1.0,
        min_val=0.0
    )
valid_config.support_bonus = \
    validate_config_var(
        live_topstats_config.SUPPORT_BONUS,
        float, 1.0,
        min_val=0.0
    )
valid_config.vip_commander_min_playtime_mins = \
    validate_config_var(
        live_topstats_config.VIP_COMMANDER_MIN_PLAYTIME_MINS,
        int, 20,
        min_val=0
    )
valid_config.vip_commander_min_support_score = \
    validate_config_var(
        live_topstats_config.VIP_COMMANDER_MIN_SUPPORT_SCORE,
        int, 1000,
        min_val=0
    )
valid_config.seed_limit = \
    validate_config_var(
        live_topstats_config.SEED_LIMIT,
        int, 40,
        min_val=0, max_val=100
    )
valid_config.granted_vip_hours = \
    validate_config_var(
        live_topstats_config.GRANTED_VIP_HOURS,
        int, 0,
        min_val=0
    )
valid_config.local_timezone = \
    validate_config_var(
        live_topstats_config.LOCAL_TIMEZONE,
        str, "Etc/UTC",
        custom_check=lambda x: ZoneInfo(x) or True
    )
valid_config.discord_config = \
    validate_config_var(
        live_topstats_config.DISCORD_CONFIG,
        list[tuple[str, bool]], []
    )
valid_config.discord_embed_author_icon_url = (
    live_topstats_config.DISCORD_EMBED_AUTHOR_ICON_URL \
        if validate_url(live_topstats_config.DISCORD_EMBED_AUTHOR_ICON_URL, "any")
        else "https://cdn.discordapp.com/icons/316459644476456962/73a28de670af9e6569f231c9385398f3.webp?size=64"
)
valid_config.bot_name = \
    validate_config_var(
        live_topstats_config.BOT_NAME,
        str, "custom_tools_live_topstats"
    )

# Clan related (as set in CRCON user interface, in http://<ip>:8010/settings/others/crcon)
try:
    rcon_server_settings_userconfig = RconServerSettingsUserConfig.load_from_db()
    url_to_test = str(rcon_server_settings_userconfig.server_url)
    valid_config.discord_embed_author_url = url_to_test if validate_url(url_to_test, "any") else "https://github.com/ElGuillermo/HLL_CRCON_Live_topstats"
except Exception as error:
    logger.error("Could not retrieve DISCORD_EMBED_AUTHOR_URL from database : %s", error)
    valid_config.discord_embed_author_url = "https://github.com/ElGuillermo/HLL_CRCON_Live_topstats"


def is_vip_for_less_than_xh(rcon: Rcon, player_id: str, vip_delay_hours: int) -> bool:
    """
    returns
    'true' if player has no VIP or a VIP that expires in less than vip_delay_hours,
    'false' if he has a VIP that expires in more than vip_delay_hours or no VIP at all.
    """
    # Get the VIP list
    try:
        actual_vips = rcon.get_vip_ids()
    except Exception as error:
        logger.error("Can't get the VIP list : %s", error)
        return False  # Consider the player as a VIP by default (giving a VIP could erase an actual -larger- VIP)

    # Check each VIP lease
    for item in actual_vips:
        if item['player_id'] == player_id and item['vip_expiration'] is not None:
            vip_expiration_output = str(item['vip_expiration'])
            vip_expiration = datetime.fromisoformat(vip_expiration_output)

            # VIP will expire in less than vip_delay_hours
            if vip_expiration < datetime.now(timezone.utc) + timedelta(hours=vip_delay_hours):
                return True

            # VIP won't expire in less than vip_delay_hours
            return False

    return True  # Player isn't in the VIP list


def give_xh_vip(rcon: Rcon, player_id: str, player_name: str, hours_awarded: int):
    """
    Gives a X hour(s) VIP
    returns a fully formatted and localized message :

        You are in the topstats!

        You won a VIP until
        01/01/2001, at 12h00 !
    """
    combined_name = f"{player_name} (top player)"

    # Gives X hours VIP
    expiration_dt = datetime.now(timezone.utc) + timedelta(hours=hours_awarded)
    rcon.add_vip(player_id, combined_name, expiration_dt.strftime('%Y-%m-%dT%H:%M:%SZ'))

    # Local timezone
    local_tz = ZoneInfo(valid_config.local_timezone)
    local_dt = expiration_dt.astimezone(local_tz)

    # Message building
    header = TRANSL['vip_header'][valid_config.lang]
    won_text = TRANSL['vip_won'][valid_config.lang]
    date_str = local_dt.strftime('%d/%m/%Y')
    at_text = TRANSL['vip_at'][valid_config.lang]
    time_str = local_dt.strftime('%Hh%M')

    return f"{header}\n\n{won_text}\n{date_str}, {at_text} {time_str} !"


# Declared in SCORE_FUNCTIONS
def get_player_teamplay(player: dict) -> int:
    """
    Calculates the teamplay score using combat and support stats.
    Formula: combat + (support * SUPPORT_BONUS)
    """
    combat = int(player.get("combat", 0))
    support = int(player.get("support", 0))
    support_bonus = valid_config.support_bonus

    return int(round(combat + (support * support_bonus)))


# Declared in SCORE_FUNCTIONS
def get_player_offdef(player: dict) -> int:
    """
    Calculates the combined offense and defense score.
    Formula: offense + (defense * DEFENSE_BONUS)
    """
    offense = int(player.get("offense", 0))
    defense = int(player.get("defense", 0))
    defense_bonus = valid_config.defense_bonus

    return int(round(offense + (defense * defense_bonus)))


# Declared in SCORE_FUNCTIONS
def get_player_kd(player: dict) -> float:
    """
    Calculates the kills/deaths ratio.
    If deaths are 0, the ratio equals the number of kills.
    """
    kills = int(player.get("kills", 0))
    deaths = int(player.get("deaths", 0))

    if deaths == 0:
        return float(kills)

    return round(kills / deaths, 2)


# Declared in SCORE_FUNCTIONS
def get_player_kpm(player: dict) -> float:
    """
    Calculates the kills per minute (KPM).
    Requires at least 1 minute of play to avoid aberrant ratios.
    """
    playtime_seconds = int(player.get("map_playtime_seconds", 0))

    # Player must have played > 5 mins
    if playtime_seconds < 300:
        return 0.0

    kills = int(player.get("kills", 0))
    if kills == 0:
        return 0.0

    playtime_min = playtime_seconds / 60

    return round(kills / playtime_min, 2)


# Declared in SCORE_FUNCTIONS
def get_squad_team_kills(squad: dict) -> int:
    """
    Calculates combined team_kills for a whole squad.
    """
    players = squad.get("players", [])
    if not players:
        return 0

    total_tks = sum(int(p.get("team_kills", 0)) for p in players)
    if total_tks == 0:
        return 0

    return total_tks


# Declared in SCORE_FUNCTIONS
def get_squad_vehicle_kills(squad: dict) -> int:
    """
    Calculates combined vehicle_kills for a whole squad.
    """
    players = squad.get("players", [])
    if not players:
        return 0

    total_vehicle_kills = sum(int(p.get("vehicle_kills", 0)) for p in players)
    if total_vehicle_kills == 0:
        return 0

    return total_vehicle_kills


# Declared in SCORE_FUNCTIONS
def get_squad_vehicles_destroyed(squad: dict) -> int:
    """
    Calculates combined vehicles_destroyed for a whole squad.
    """
    players = squad.get("players", [])
    if not players:
        return 0

    total_vehicles_destroyed = sum(int(p.get("vehicles_destroyed", 0)) for p in players)
    if total_vehicles_destroyed == 0:
        return 0

    return total_vehicles_destroyed


# Declared in SCORE_FUNCTIONS
def get_squad_teamplay(squad: dict) -> int:
    """
    Calculates combined teamplay score for a whole squad.
    Formula: combat + (support * SUPPORT_BONUS)
    """
    combat = int(squad.get("combat", 0))
    support = int(squad.get("support", 0))
    support_bonus = valid_config.support_bonus

    return int(round(combat + (support * support_bonus)))


# Declared in SCORE_FUNCTIONS
def get_squad_offdef(squad: dict) -> int:
    """
    Calculates combined off/def score for a whole squad.
    Formula: offense + (defense * DEFENSE_BONUS)
    """
    offense = int(squad.get("offense", 0))
    defense = int(squad.get("defense", 0))
    defense_bonus = valid_config.defense_bonus

    return int(round(offense + (defense * defense_bonus)))


# Declared in SCORE_FUNCTIONS
def get_squad_kd(squad: dict) -> float:
    """
    Calculates the cumulative K/D ratio of all players in the squad.
    """
    players = squad.get("players", [])
    if not players:
        return 0.0

    total_kills = sum(int(p.get("kills", 0)) for p in players)
    total_deaths = sum(int(p.get("deaths", 0)) for p in players)

    if total_deaths == 0:
        return float(total_kills)

    return round(total_kills / total_deaths, 2)


# Declared in SCORE_FUNCTIONS
def get_squad_kpm(squad: dict) -> float:
    """
    Calculates the squad kills/min based on cumulative kills.
    Requires at least 10 minutes of cumulated playtime to avoid aberrant ratios.
    """
    players = squad.get("players", [])
    if not players:
        return 0.0

    total_playtime_sec = sum(int(p.get("map_playtime_seconds", 0)) for p in players)
    # Players must have 10 min cumulated playtime
    if total_playtime_sec < 600:
        return 0.0

    total_kills = sum(int(p.get("kills", 0)) for p in players)
    if total_kills == 0:
        return 0.0

    kpm = total_kills / (total_playtime_sec / 60)

    return round(kpm, 2)


# Functions mapping (must be declared AFTER the functions definitions)
SCORE_FUNCTIONS = {
    # (players and squads)
    # No need to create a dedicated function, as the stat is directly available from the 'get_team_view' endpoint
    "combat": lambda p: int(p.get("combat", 0)),
    "offense": lambda p: int(p.get("offense", 0)),
    "defense": lambda p: int(p.get("defense", 0)),
    "support": lambda p: int(p.get("support", 0)),
    "kills": lambda p: int(p.get("kills", 0)),
    "deaths": lambda p: int(p.get("deaths", 0)),
    # Directly calculated (no dedicated function)
    "defense_bonus": lambda p: int(int(p.get("defense", 0)) * valid_config.defense_bonus),
    "support_bonus": lambda p: int(int(p.get("support", 0)) * valid_config.support_bonus),

    # (players)
    "player_team_kills": lambda p: int(p.get("team_kills", 0)),
    "player_vehicle_kills": lambda p: int(p.get("vehicle_kills", 0)),
    "player_vehicles_destroyed": lambda p: int(p.get("vehicles_destroyed", 0)),
    # These are calculated stats, provided by dedicated functions
    "player_teamplay": get_player_teamplay,                    # combat + support * support_bonus
    "player_offdef": get_player_offdef,                        # offense + defense * defense bonus
    "player_kd": get_player_kd,                                # kills / deaths
    "player_kpm": get_player_kpm,                              # kills / minute

    # (squads)
    "squad_team_kills": get_squad_team_kills,                  # cumulated team_kills
    "squad_vehicle_kills": get_squad_vehicle_kills,            # cumulated vehicle_kills
    "squad_vehicles_destroyed": get_squad_vehicles_destroyed,  # cumulated vehicles_destroyed
    "squad_teamplay": get_squad_teamplay,                      # combat + support * support_bonus
    "squad_offdef": get_squad_offdef,                          # offense + defense * defense bonus
    "squad_kd": get_squad_kd,                                  # kills / deaths
    "squad_kpm": get_squad_kpm,                                # kills / minute
}


def get_player_ranking(
    rcon: Rcon,
    server_status,
    get_team_view_output: dict,
    observed_unit_type: str,
    score_func,
    display: int = 3,
    details: bool = False,
    vip_winners: int = 0,
    score_key: str = "",
) -> list:
    """
    Extracts, ranks, and optionally triggers VIP rewards.

    `score_key` is the raw config string (e.g. "kills", "combat",
    "player_kd") and is only consulted to suppress the trailing
    " : score" when the score itself is already implied by the inline
    "N/M KD:X" triple — i.e. when ranking by kills. Other stats still
    print the score after the name so users see the value they're
    being ranked by.
    """
    # Get data (initial "result" branch can be missing)
    result = get_team_view_output.get("result", get_team_view_output)

    players_stats = []

    for side in ["allies", "axis"]:
        team_data = result.get(side, {})

        # armycommander in "commander" branch
        if observed_unit_type == "armycommander":
            cmd = team_data.get("commander")
            if cmd:

                # Calculate score
                score = score_func(cmd)

                # Retain only players having score > 0
                if score and score > 0:

                    # [:28] avoids line returns
                    name = cmd["name"][:28]

                    # Add team/squad details + K/D info inline
                    if details:
                        c_k = cmd.get("kills", 0)
                        c_d = cmd.get("deaths", 0)
                        c_kd = _fmt_kd(c_k, c_d)
                        name = f"({TRANSL[side+'_short'][valid_config.lang].capitalize()}) {name[:16]} {_fmt_kdk(c_k, c_d)}"

                    # Add the formatted entry to the global list
                    players_stats.append({
                        "name": name,
                        "score": score,
                        "player_id": cmd.get("player_id"),
                        "raw_data": cmd  # Allows checkings in VIP part
                    })

        # players in "squads" branch
        else:
            squads = team_data.get("squads", {})
            for s_name, s_info in squads.items():

                # Ignore "unassigned" squad, only observe observed_unit_type squads
                if s_name != "unassigned" and str(s_info.get("type")).lower() == observed_unit_type.lower():

                    # List players in squad
                    for p in s_info.get("players", []):

                        # Calculate score
                        score = score_func(p)

                        # Min kills threshold for infantry (uses module-level constant)
                        kills_count = p.get("kills", 0)
                        if observed_unit_type.lower() == "infantry" and kills_count <= MIN_KILLS_INFANTRY:
                            continue

                        # Retain only players having score > 0
                        if score and score > 0:

                            # [:30] avoids line returns
                            name = p["name"][:28]
                            if details:
                                # Include K/D info inline like the commander branch — user wants
                                # "name 18/3 KD:6.0" everywhere instead of the bare score the
                                # rank line used to show after `:`.
                                p_k = p.get("kills", 0)
                                p_d = p.get("deaths", 0)
                                name = (
                                    f"({TRANSL[side+'_short'][valid_config.lang].capitalize()}/"
                                    f"{s_name.capitalize()}) {name[:16]} {_fmt_kdk(p_k, p_d)}"
                                )

                            # Add the formatted entry to the global list
                            players_stats.append({
                                "name": name,
                                "score": score,
                                "player_id": p.get("player_id"),
                                "raw_data": p
                            })

    # Sort global list on "score" (descending)
    players_stats.sort(key=lambda x: x["score"], reverse=True)

    # Determine who won a VIP -> store the 'player_id' values in a 'winners_ids' list
    winners_ids = []
    vip_winners_count = validate_config_var(vip_winners, int, 0)

    if (vip_winners_count > 0
        and server_status["current_players"] >= valid_config.seed_limit
        and valid_config.granted_vip_hours > 0):

        # Enumerate the first <vip_winners> top players from the (now sorted) global list
        for player in players_stats[:vip_winners_count]:
            raw = player['raw_data']

            # No VIP for "entered at last second" commander
            if raw.get('role') == "armycommander":
                commander_playtime = (int(raw.get('offense', 0)) + int(raw.get('defense', 0))) / 20
                if (commander_playtime < valid_config.vip_commander_min_playtime_mins
                    or int(raw.get('support', 0)) < valid_config.vip_commander_min_support_score):
                    continue

            # Add the player_id to the winners_ids list
            winners_ids.append(player['player_id'])

            # Only give VIP if the player has either :
            # - no VIP at all
            # - a VIP that ends in less than GRANTED_VIP_HOURS
            if is_vip_for_less_than_xh(rcon, player['player_id'], valid_config.granted_vip_hours):
                vip_message = give_xh_vip(rcon, player['player_id'], raw.get('name', player['name']), valid_config.granted_vip_hours)
            else:
                vip_message = f"{TRANSL['vip_header'][valid_config.lang]}\n\n{TRANSL['already_vip'][valid_config.lang]}"

            # Send a message to the winners
            try:
                rcon.message_player(player_id=player['player_id'], message=vip_message, by=valid_config.bot_name, save_message=False)
            except Exception as error:
                logger.error("VIP message error: %s", error)

    # Final output list
    formatted_list = []
    # Ranking by kills? The inline "N/M KD:X" triple in `name` already
    # carries the kills value, so the trailing ": score" would just repeat
    # it. Skip the suffix for kills-style rankings only.
    suppress_trailing = score_key.lower() in {"kills", "deaths"}
    for p in players_stats[:display]:
        score_val = f"{p['score']:.1f}" if isinstance(p['score'], float) else str(p['score'])

        # Add the ★ at the end of the line if this player_id is in the 'winners_ids' list
        star = " ★" if p['player_id'] in winners_ids else ""
        if suppress_trailing:
            formatted_list.append(f"{p['name']}{star}")
        else:
            formatted_list.append(f"{p['name']} : {score_val}{star}")

    return formatted_list


def get_squad_ranking(get_team_view_output: dict, observed_unit_type: str, score_func, display: int = 3) -> list:
    """
    Ranks squads or the Commander unit.
    """
    # Get data (initial "result" branch can be missing)
    result = get_team_view_output.get("result", get_team_view_output)

    squads_stats = []

    for side in ["allies", "axis"]:
        team_data = result.get(side, {})

        # armycommander in "commander" branch
        if observed_unit_type == "armycommander":
            cmd = team_data.get("commander")
            if cmd:

                # Harmonizing data structure : create an "armycommander" squad subtree
                fake_squad = {
                    "type": "armycommander",
                    "players": [cmd],
                    "offense": cmd.get("offense", 0),
                    "defense": cmd.get("defense", 0),
                    "combat": cmd.get("combat", 0),
                    "support": cmd.get("support", 0)
                }

                # Calculate score
                score = score_func(fake_squad)

                # Retain only players having score > 0
                if score and score > 0:

                    # Add the formatted entry to the global list
                    squads_stats.append({"name": f"{TRANSL[side][valid_config.lang].capitalize()}/{TRANSL['armycommander_short'][valid_config.lang].capitalize()}", "score": score})

        # squads in "squads" branch
        else:
            squads = team_data.get("squads", {})
            for s_name, s_info in squads.items():

                # Ignore "unassigned" squad, only observe observed_unit_type squads
                if s_name != "unassigned" and str(s_info.get("type")).lower() == observed_unit_type.lower():

                    # Calculate score
                    score = score_func(s_info)

                    # Retain only squads having score > 0
                    if score and score > 0:

                        name = f"{TRANSL[side][valid_config.lang].capitalize()}/{s_name.capitalize()}"

                        # Add a formatted line to the global list
                        squads_stats.append({
                            "name": name,
                            "score": score
                        })

    # Sort global list on "score" (descending)
    squads_stats.sort(key=lambda x: x["score"], reverse=True)

    # Final output list
    formatted_list = []
    for s in squads_stats[:display]:
        # Limit the float values to 1 decimal (0.x)
        score_val = f"{s['score']:.1f}" if isinstance(s['score'], float) else str(s['score'])
        # Add the listed lines to the output list
        formatted_list.append(f"{s['name']} : {score_val}")

    return formatted_list


# Squad/player names treated as phantom buckets (HLL state when squad lead leaves,
# leftover players land in these — they shouldn't pollute the "top squads" list).
_SKIPPED_SQUAD_NAMES = {"unassigned", "command", "commander", "none", ""}

# Min kills required to appear in any infantry top-N or squad-member row.
# Applies in both get_player_ranking (TOP GRAVCI) and generate_squads_breakdown
# (TOP ZAGONI player rows). Squad header totals/averages still count ALL members.
MIN_KILLS_INFANTRY = 5

# When ranking individual players (not squads), replace the squad-type
# header ("armor" → "Бронетехніка") with a singular role-flavored one
# ("Танкіст" / "Снайпер") via a different TRANSL key. Squad rankings still
# use the default plural type header. Keys must exist in TRANSL.
PLAYER_CATEGORY_LABEL_OVERRIDE = {
    "armor": "tanker",   # → "Танкіст" (UA) / "Tanker" (EN) / ... — short
                         # colloquial form, not the formal "командир танка"
    "recon": "sniper",   # → "Снайпер"  / "Sniper"
}


def _fmt_kd(k: int, d: int) -> str:
    """K/D formatting with sensible fallbacks:
      K>0 D>0  → "X.Y"
      K>0 D=0  → "∞"   (perfect run — earned the badge)
      K=0 D=0  → "—"   (AFK / just connected — not informative)
      K=0 D>0  → "0.0"
    """
    if d > 0:
        return f"{k / d:.1f}"
    if k > 0:
        return "∞"
    return "—"


def _fmt_kdk(k: int, d: int) -> str:
    """Compact "K/D KD:X" — replaces the verbose "K:N D:M K/D:X" so a line
    like `(Союз/Charlie) jartug  18/3 KD:6.0` reads in one glance instead
    of three separate label/value pairs. User-requested shortening."""
    return f"{k}/{d} KD:{_fmt_kd(k, d)}"


def generate_squads_breakdown(get_team_view_output: dict, lang: int) -> str:
    """
    Per-side, per-role squad breakdown showing EVERY squad member with K/D/KD.

    Layout:
        ТОП ЗАГОНИ — СОЮЗ
        ├ Піхота
        │ ├ Загін Able (4 гр., K:47 D:18 K/D:2.6)
        │ │  · PlayerName  K:15 D:5 K/D:3.0
        ...

    Skips: artillery (per user preference). Commander is shown in players section.
    """
    result = get_team_view_output.get("result", get_team_view_output)

    sides = [
        ("allies", TRANSL.get("allies_short", ["all"] * 8)[lang]),
        ("axis", TRANSL.get("axis_short", ["axi"] * 8)[lang]),
    ]
    # Reuse the PLAYER_CATEGORY_LABEL_OVERRIDE mapping so the squad-section
    # role labels read the same as the (now-removed) single-player sections did:
    #   armor → "Танкіст" (was "Бронетехніка")
    #   recon → "Снайпер" (was "Розвідка")
    # User feedback: the squad-type plural sounded technical/cold; the role
    # noun matches how players actually refer to these specialists in chat.
    role_order = [
        ("infantry", TRANSL["infantry"][lang].capitalize()),
        ("armor", TRANSL[PLAYER_CATEGORY_LABEL_OVERRIDE["armor"]][lang].capitalize()),
        ("recon", TRANSL[PLAYER_CATEGORY_LABEL_OVERRIDE["recon"]][lang].capitalize()),
    ]

    blocks = []
    for side_key, side_short in sides:
        side_data = result.get(side_key, {})
        squads = side_data.get("squads", {}) or {}
        if not squads:
            continue

        side_display = side_short.upper()
        side_lines = [f"{TRANSL['top_squads'][lang].upper()} — {side_display}"]

        roles_present = []
        for role_key, role_display in role_order:
            role_squads = [
                (name, info) for name, info in squads.items()
                if (info.get("type") or "").lower() == role_key
                and (name or "").lower() not in _SKIPPED_SQUAD_NAMES
            ]
            if role_squads:
                role_squads.sort(
                    key=lambda item: sum(p.get("kills", 0) for p in (item[1].get("players") or [])),
                    reverse=True
                )
                # Show only top-1 squad per role (was top-3) — user wants compact view
                role_squads = role_squads[:1]
                # role_key is kept so the per-member loop can decide whether
                # to apply the MIN_KILLS_INFANTRY filter (infantry only).
                roles_present.append((role_key, role_display, role_squads))

        for role_idx, (role_key, role_display, role_squads) in enumerate(roles_present):
            is_last_role = role_idx == len(roles_present) - 1
            role_branch = "└" if is_last_role else "├"
            role_cont = " " if is_last_role else "│"
            side_lines.append(f"{role_branch} {role_display}")

            for sq_idx, (sq_name, sq_info) in enumerate(role_squads):
                is_last_squad = sq_idx == len(role_squads) - 1
                squad_branch = "└" if is_last_squad else "├"
                squad_cont = " " if is_last_squad else "│"

                players = sq_info.get("players") or []
                sq_k = sum(p.get("kills", 0) for p in players)
                sq_d = sum(p.get("deaths", 0) for p in players)
                sq_kd = _fmt_kd(sq_k, sq_d)

                # Recon special case: a recon squad has 2 members (sniper +
                # spotter) but the spotter rarely kills anything. User wants
                # ONE sniper per side, so we skip the "Загін …" / "Всього …"
                # scaffolding entirely and render the top-killer as a single
                # bullet under the "Снайпер" role header. Same idea as the
                # commander block (one player, no squad-level numbers).
                if role_key == "recon":
                    sniper = max(players, key=lambda p: p.get("kills", 0)) if players else None
                    if sniper is not None:
                        p_name = (sniper.get("name") or "?")[:16]
                        p_k = sniper.get("kills", 0)
                        p_d = sniper.get("deaths", 0)
                        side_lines.append(
                            f"{role_cont} {squad_branch} {p_name}  {_fmt_kdk(p_k, p_d)}"
                        )
                    continue

                n = len(players)
                avg_k = sq_k / n if n > 0 else 0
                avg_d = sq_d / n if n > 0 else 0
                # Two-line squad header (per user feedback: easier to read
                # than the long single line we had before):
                #   Загін Baker [6] (avg K:26.7 D:27.8)
                #     Всього K:160 D:167 KD:1.0
                side_lines.append(
                    f"{role_cont} {squad_branch} Загін {sq_name.capitalize()}"
                    f" [{n}] (avg K:{avg_k:.1f} D:{avg_d:.1f})"
                )
                side_lines.append(
                    f"{role_cont} {squad_cont}    Всього K:{sq_k} D:{sq_d} KD:{sq_kd}"
                )

                # Show only members above kills threshold — squad header still
                # reflects ALL members (sq_k, sq_d, n).
                # For armor crews (tiny squads where every role matters —
                # driver in a tank) we show every member, even if they have
                # 0 kills. The MIN_KILLS_INFANTRY filter is only useful for
                # full infantry squads where rear support roles often farm
                # 1-2 kills and clutter the output.
                players_sorted = sorted(players, key=lambda p: p.get("kills", 0), reverse=True)
                apply_min_kills = role_key == "infantry"
                for player in players_sorted:
                    p_k = player.get("kills", 0)
                    if apply_min_kills and p_k <= MIN_KILLS_INFANTRY:
                        continue
                    p_name = (player.get("name") or "?")[:16]
                    p_d = player.get("deaths", 0)
                    p_kd = _fmt_kd(p_k, p_d)
                    side_lines.append(
                        f"{role_cont} {squad_cont}  · {p_name}  {_fmt_kdk(p_k, p_d)}"
                    )

        blocks.append("\n".join(side_lines))

    return "\n\n".join(blocks)


def generate_full_report(rcon, get_team_view_output, stats_to_display, is_match_end: bool = False):
    """
    Calls children functions to get/sort/format rankings for players and squads,
    then assemble them to generate the ingame message.

    Arguments :
        - rcon
        - get_team_view_output : raw get_team_view() output from API
        - stats_to_display : the STATS_TO_DISPLAY dict set in config file
        - is_match_end : enable VIP granting if True
    """
    server_status = rcon.get_status()
    report_sections = []

    def process_config_category(category_key, fetch_func, main_header_key):
        """
        Get/sort/format rankings for players and squads

        arguments:
            - category_key : either "players" or "squads"
            - fetch_func : name of the function called to provide data
                - "get_player_ranking" if category_key is "players"
                - "get_squad_ranking" if category_key is "squads"
            - main_header_key : a TRANSL dict key
                - "top_players" if category_key is "players"
                - "top_squads" if category_key is "squads"
        """
        cfg = stats_to_display.get(category_key, {})
        category_lines = []

        active_categories = []
        for observed_unit_type, rankings in cfg.items():
            valid_results = []
            for r in rankings:

                # set the <vip_winners> number to 0 if match_end == False (called from chat) or if this is a squad-type score
                vip_winners = r.get("vip_winners", 0) if is_match_end and category_key == "players" else 0

                if category_key == "players":
                    data = fetch_func(rcon, server_status, get_team_view_output, observed_unit_type, SCORE_FUNCTIONS[r["score"]], r.get("display", 3), r.get("details", True), vip_winners, score_key=r["score"])
                else:
                    data = fetch_func(get_team_view_output, observed_unit_type, SCORE_FUNCTIONS[r["score"]], r.get("details", True))

                if data:
                    valid_results.append((r, data))

            if valid_results:
                active_categories.append((observed_unit_type, valid_results))

        if not active_categories:
            return []

        # Headers ("TOP PLAYERS", "TOP SQUADS")
        title = TRANSL[main_header_key][valid_config.lang].upper()
        category_lines.append(f"{title}")

        for idx_cat, (observed_unit_type, valid_results) in enumerate(active_categories):
            is_last_cat = (idx_cat == len(active_categories) - 1)

            # Units ("Infantry", "Armor", etc.)
            unit_branch = "└" if is_last_cat else "├"
            # For PLAYER rankings we prefer a singular role-flavored header
            # ("Танкіст" / "Снайпер") over the squad-type plural ("Бронетехніка"
            # / "Розвідка"). Squad rankings keep the default plural which fits
            # the unit context better.
            label_key = observed_unit_type.lower()
            if category_key == "players":
                label_key = PLAYER_CATEGORY_LABEL_OVERRIDE.get(label_key, label_key)
            unit_name = TRANSL.get(label_key, [observed_unit_type])[valid_config.lang].capitalize()
            category_lines.append(f"{unit_branch} {unit_name}")

            # Stats ("Combat + Support", etc.)
            unit_prefix = "\u00A0\u00A0" if is_last_cat else "│\u00A0"

            for idx_stat, (r, results) in enumerate(valid_results):
                is_last_stat = (idx_stat == len(valid_results) - 1)

                stat_branch = "└" if is_last_stat else "├"

                raw_score_key = r['score'].lower()
                clean_key = raw_score_key.removeprefix("player_").removeprefix("squad_")
                translations = TRANSL.get(clean_key)
                stat_label = translations[valid_config.lang].capitalize() if translations else clean_key.capitalize()
                # For the kills stat the player lines now carry the full
                # "N/M KD:X" triple, so the header is annotated to explain
                # what those three numbers mean instead of just "Kills".
                if clean_key == "kills":
                    deaths_translations = TRANSL.get("deaths")
                    deaths_label = (
                        deaths_translations[valid_config.lang].capitalize()
                        if deaths_translations else "Deaths"
                    )
                    stat_label = f"{stat_label}/{deaths_label} KD:"

                category_lines.append(f"{unit_prefix}{stat_branch} {stat_label}")

                # Tops
                stat_prefix = "\u00A0\u00A0\u00A0" if is_last_stat else "│\u00A0"  # \u2003 (large) ? \u2002 (medium) ?

                for idx_res, line in enumerate(results):
                    # is_last_res = (idx_res == len(results) - 1)
                    # res_branch = "└" if is_last_res else "├"
                    res_branch = "·"

                    category_lines.append(f"{unit_prefix}{stat_prefix}{res_branch} {line}")

        return category_lines

    # Final report construction
    # -------------------- -------------------- --------------------
    player_lines = process_config_category("players", get_player_ranking, "top_players")
    squads_breakdown = generate_squads_breakdown(get_team_view_output, valid_config.lang)
    squad_lines = []  # legacy variable kept for bonus-note logic compatibility

    # VIP legend
    # --------------------
    # Check if VIP granting is available
    if (
        is_match_end
        and server_status["current_players"] >= valid_config.seed_limit
        and valid_config.granted_vip_hours > 0
        and player_lines
    ):
        # Check if VIP granting is enabled for observed stats
        player_cfg = stats_to_display.get("players", {})
        has_vip_enabled = any(
            any(r.get("vip_winners", 0) > 0 for r in rankings)
            for rankings in player_cfg.values()
        )

        if has_vip_enabled:
            vip_note = f"{TRANSL['vip_note'][valid_config.lang]} ({valid_config.granted_vip_hours} {TRANSL['hours'][valid_config.lang]})"
            report_sections.append(f"★ = {vip_note}")

    # Bonus
    # --------------------
    # Collect only scores that actually produced results in the report
    all_active_scores = set()
    for cat_lines in [player_lines, squad_lines]:
        if cat_lines:
            # We look into stats_to_display but only for categories that are not empty
            category_key = "players" if cat_lines is player_lines else "squads"
            cfg = stats_to_display.get(category_key, {})
            for rankings in cfg.values():
                for r in rankings:
                    all_active_scores.add(r.get("score", "").lower())

    bonus_notes = []

    # Defense
    defense_keys = {"defense_bonus", "player_offdef", "squad_offdef"}
    if (all_active_scores & defense_keys) and valid_config.defense_bonus != 1.0:
        label = TRANSL['defense_bonus'][valid_config.lang]
        bonus_notes.append(f"{label}: x{valid_config.defense_bonus}")

    # Support
    support_keys = {"support_bonus", "player_teamplay", "squad_teamplay"}
    if (all_active_scores & support_keys) and valid_config.support_bonus != 1.0:
        label = TRANSL['support_bonus'][valid_config.lang]
        bonus_notes.append(f"{label}: x{valid_config.support_bonus}")

    if bonus_notes:
        report_sections.append("\n".join(bonus_notes))

    # Top players
    # --------------------
    if player_lines:
        report_sections.append("\n".join(player_lines))

    # Top squads (new per-side breakdown with all members)
    # --------------------
    if squads_breakdown:
        report_sections.append(squads_breakdown)

    return "\n\n".join(report_sections)


def stats_on_chat_command(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    """
    Message actual top stats to the player who types the defined command in chat
    """
    # Check if script is enabled in config for this server
    server_number = get_server_number()
    if int(server_number) not in valid_config.enable_on_servers:
        return

    # Check log for mandatory variable
    chat_message: str|None = struct_log["sub_content"]
    if chat_message is None:
        logger.error("No sub_content in CHAT log")
        return

    # This message is one of the expected command word(s) (case insensitive)
    if chat_message.lower() in (cmd.lower() for cmd in valid_config.chat_command):

        logger.info("'%s' ('%s') asked for topstats using '%s' command in chat on server '%s'", struct_log.get("player_name_1"), struct_log.get("player_id_1"), chat_message.lower(), server_number)

        # Check log for mandatory variable
        player_id: str|None = struct_log["player_id_1"]
        if player_id is None:
            return

        # Per-player language: mutate valid_config.lang inside _lang_lock,
        # so internal helpers (generate_full_report + its callees) see the
        # right language. Restored in `finally` to prevent leakage to matchend.
        with _lang_lock:
            original_lang = valid_config.lang
            try:
                valid_config.lang = get_player_language(player_id)

                # Get data from RCON
                get_team_view_output: dict = rcon.get_team_view()

                # Process data
                report = generate_full_report(rcon, get_team_view_output, valid_config.stats_to_display, is_match_end=False)  # is_match_end=False disables VIP granting

                # Ingame message
                if not report:
                    message = f"{TRANSL['nostatsyet'][valid_config.lang]}"
                else:
                    message = f"{report}"
            finally:
                valid_config.lang = original_lang

        try:
            rcon.message_player(
                player_id=player_id,
                message=message,
                by=valid_config.bot_name,
                save_message=False
            )
        except Exception as error:
            logger.error("Ingame message_player couldn't be sent : %s", error)


def stats_on_match_end(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    """
    - Sends ingame message to all the players
    - Gives VIP to the top players as configured
    - Logs the message
    - Sends the message to a Discord embed
    """
    server_number = int(get_server_number())

    # Check if script is enabled in config for this server
    if int(server_number) not in valid_config.enable_on_servers:
        return

    # Check if script is enabled in config to be displayed on matchend
    if not valid_config.display_on_matchend:
        return

    # Acquire _lang_lock so concurrent !top commands (which temporarily mutate
    # valid_config.lang for per-player language) don't bleed into the matchend
    # broadcast — matchend uses the configured global LANG for all players.
    with _lang_lock:
        # Get data from RCON
        get_team_view_output: dict = rcon.get_team_view()

        # Process data
        report = generate_full_report(rcon, get_team_view_output, valid_config.stats_to_display, is_match_end=True)  # is_match_end=True enables VIP granting

        # Prepare ingame message and logs
        if not report:
            message = f"{TRANSL['nostatsyet'][valid_config.lang]}"
        else:
            message = f"{report}"

        # logs
        logger.info("\n%s", message)

        # Ingame message
        # only if there is stats to display
        if report:
            try:
                rcon.message_all_players(message=message)
            except Exception as error:
                logger.error("Ingame message_all_players couldn't be sent : %s", error)

        # Discord
        # DEBUG: trace why matchend Discord may not be reaching the channel
        logger.info("matchend Discord: server_number=%s, discord_config_len=%d, discord_config=%r",
                    server_number, len(valid_config.discord_config), valid_config.discord_config)
        # Sending to Discord is disabled for this server
        try:
            disc_entry = valid_config.discord_config[server_number - 1]
        except (IndexError, TypeError) as e:
            logger.error("matchend Discord: discord_config index %d failed: %s — skipping", server_number - 1, e)
            return
        # entry can be tuple/list of (url, enabled)
        try:
            disc_url = disc_entry[0]
            disc_enabled = disc_entry[1]
        except Exception as e:
            logger.error("matchend Discord: cannot unpack entry %r: %s — skipping", disc_entry, e)
            return
        if not disc_enabled:
            logger.info("matchend Discord: send DISABLED for server %s, skipping", server_number)
            return
        logger.info("matchend Discord: SENDING embed to webhook %s...", str(disc_url)[:60])

        # Get the webhook url from config
        discord_webhook = valid_config.discord_config[server_number - 1][0]

        # This webhook url is not valid
        if not validate_url(url=discord_webhook, url_type="discord_webhook"):
            logger.warning("invalid webhook url for server '%s'. Please check your valid_config.", str(server_number))
            return

        webhook = discord.SyncWebhook.from_url(discord_webhook)

        embed = discord.Embed(
            title=TRANSL['gamejustended'][valid_config.lang],
            url="",
            description=message,
            color=0xffffff
        )

        embed.set_author(
            name=valid_config.bot_name,
            url=valid_config.discord_embed_author_url,
            icon_url=valid_config.discord_embed_author_icon_url
        )

        embeds = []
        embeds.append(embed)

        try:
            webhook.send(embeds=embeds, wait=True)
        except Exception as error:
            logger.error("Discord embed couldn't be sent : %s", error)
