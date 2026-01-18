import json
import logging
import random
import re
import shlex
import time as time_module
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Final

from discord_webhook import DiscordEmbed

import rcon.steam_utils as steam_utils
import custom_tools.live_topstats as live_topstats
import custom_tools.all_time_stats as all_time_stats
from discord.utils import escape_markdown
from rcon.arguments import max_arg_index, replace_params
from rcon.blacklist import (
    apply_blacklist_punishment,
    blacklist_or_ban,
    is_player_blacklisted,
)
from rcon.cache_utils import invalidates, get_redis_client
from rcon.commands import HLLCommandFailedError
from rcon.discord import get_prepared_discord_hooks, send_to_discord_audit
from rcon.logs.loop import (
    on_camera,
    on_chat,
    on_connected,
    on_disconnected,
    on_match_end,
    on_match_start,
)
from rcon.maps import UNKNOWN_MAP_NAME, parse_layer
from rcon.message_variables import format_message_string, populate_message_variables
from rcon.models import PlayerID, enter_session, GameLayout
from rcon.player_history import (
    _get_set_player,
    get_player,
    save_end_player_session,
    save_player,
    save_start_player_session,
)
from rcon.rcon import Rcon, StructuredLogLineWithMetaData, do_run_commands
from rcon.recent_actions import get_recent_actions
from rcon.types import (
    MessageVariableContext,
    MostRecentEvents,
    PlayerFlagType,
    SteamBansType,
    WindowsStoreIdActionType,
)
from rcon.user_config.camera_notification import CameraNotificationUserConfig
from rcon.user_config.chat_commands import (
    MESSAGE_VAR_RE,
    BaseChatCommand,
    ChatCommand,
    ChatCommandsUserConfig,
    chat_contains_command_word,
    is_command_word,
    is_description_word,
    is_help_word,
)
from rcon.user_config.rcon_chat_commands import (
    RConChatCommand,
    RConChatCommandsUserConfig,
)
from rcon.user_config.rcon_server_settings import RconServerSettingsUserConfig
from rcon.user_config.real_vip import RealVipUserConfig
from rcon.user_config.vac_game_bans import VacGameBansUserConfig
from rcon.user_config.webhooks import CameraWebhooksUserConfig
from rcon.utils import DefaultStringFormat, MapsHistory
from rcon.vote_map import VoteMap
from rcon.workers import record_stats_worker, temporary_broadcast, temporary_welcome

logger = logging.getLogger(__name__)
ARG_RE = re.compile(r"\$(\d+)")


@on_chat
def count_vote(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    enabled = VoteMap().handle_vote_command(rcon=rcon, struct_log=struct_log)
    if enabled and (match := re.match(r"\d\s*$", struct_log["sub_content"].strip())):
        rcon.message_player(
            player_id=struct_log["player_id_1"],
            message=f"INVALID VOTE\n\nUse: !votemap {match.group()}",
        )


def initialise_vote_map(struct_log):
    logger.info("New match started initializing vote map. %s", struct_log)
    try:
        vote_map = VoteMap()
        vote_map.clear_votes()
        vote_map.gen_selection()
        vote_map.reset_last_reminder_time()
        vote_map.apply_results()
    except Exception as ex:
        logger.exception("Something went wrong in vote map init", ex)


@on_chat
def chat_commands(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    chat_config = ChatCommandsUserConfig.load_from_db()
    rcon_config = RConChatCommandsUserConfig.load_from_db()

    words: list[BaseChatCommand] = []
    if chat_config.enabled:
        words.extend(chat_config.command_words)
    if rcon_config.enabled:
        words.extend(rcon_config.command_words)
    if len(words) == 0:
        logger.debug("[CHAT COMMANDS] No commands configured or both configs disabled")
        return

    chat_message = struct_log["sub_content"]
    if chat_message is None:
        return

    event_cache = get_recent_actions()
    player_id: str = struct_log["player_id_1"]
    if player_id is None:
        return

    player_cache = event_cache.get(player_id, MostRecentEvents())
    chat_words = set(chat_message.split())
    
    # Debug logging for !me command
    if "!me" in chat_words:
        logger.debug(
            f"[CHAT COMMANDS] !me command detected. "
            f"Chat message: '{chat_message}', "
            f"Chat words: {chat_words}, "
            f"Total commands available: {len(words)}, "
            f"Chat config enabled: {chat_config.enabled}, "
            f"RCon config enabled: {rcon_config.enabled}"
        )
    ctx = {
        MessageVariableContext.player_name.value: struct_log["player_name_1"],
        MessageVariableContext.player_id.value: player_id,
        MessageVariableContext.last_victim_player_id.value: player_cache.last_victim_player_id,
        MessageVariableContext.last_victim_name.value: player_cache.last_victim_name,
        MessageVariableContext.last_victim_weapon.value: player_cache.last_victim_weapon,
        MessageVariableContext.last_nemesis_player_id.value: player_cache.last_nemesis_player_id,
        MessageVariableContext.last_nemesis_name.value: player_cache.last_nemesis_name,
        MessageVariableContext.last_nemesis_weapon.value: player_cache.last_nemesis_weapon,
        MessageVariableContext.last_tk_nemesis_player_id.value: player_cache.last_tk_nemesis_player_id,
        MessageVariableContext.last_tk_nemesis_name.value: player_cache.last_tk_nemesis_name,
        MessageVariableContext.last_tk_nemesis_weapon.value: player_cache.last_tk_nemesis_weapon,
        MessageVariableContext.last_tk_victim_player_id.value: player_cache.last_tk_victim_player_id,
        MessageVariableContext.last_tk_victim_name.value: player_cache.last_tk_victim_name,
        MessageVariableContext.last_tk_victim_weapon.value: player_cache.last_tk_victim_weapon,
    }

    # Simple command: !victim or !lastkill - returns last victim name
    if "!vc" in chat_words or "!lk" in chat_words:
        last_victim = player_cache.last_victim_name
        if last_victim:
            rcon.message_player(
                player_id=player_id,
                message=f"Last victim: {last_victim}",
                save_message=False,
            )
        else:
            rcon.message_player(
                player_id=player_id,
                message="You haven't killed anyone yet in this match.",
                save_message=False,
            )
        return

    for command in words:
        if not (
            triggered_word := chat_contains_command_word(
                chat_words, command.words, command.help_words
            )
        ):
            continue

        # Debug logging for !me command
        if "!me" in chat_words:
            logger.debug(
                f"[CHAT COMMANDS] !me matched command. "
                f"Command words: {command.words}, "
                f"Triggered word: {triggered_word}, "
                f"Is command word: {is_command_word(triggered_word)}, "
                f"Command type: {type(command).__name__}, "
                f"Is RCon command enabled: {getattr(command, 'enabled', 'N/A')}"
            )

        if is_command_word(triggered_word) and isinstance(command, ChatCommand):
            chat_message_command(rcon, command, ctx)
        if (
            is_command_word(triggered_word)
            and isinstance(command, RConChatCommand)
            and command.enabled
        ):
            chat_rcon_command(rcon, command, ctx, triggered_word, chat_message)
        if is_help_word(triggered_word):
            # Help words describe a specific command
            chat_help_command(rcon, command, ctx)

    # Description words trigger the entire help menu, test outside the loop
    # since these are global help words
    if is_description_word(chat_words, chat_config.describe_words):
        description = chat_config.describe_chat_commands()
        if description:
            rcon.message_player(
                player_id=player_id,
                message="\n".join(description),
                save_message=False,
            )
        else:
            logger.warning(
                "No descriptions set for command words, %s",
                ", ".join(chat_config.describe_words),
            )


def chat_message_command(rcon: Rcon, command: ChatCommand, ctx: dict[str, str]):
    player_id = ctx[MessageVariableContext.player_id.value]
    message_vars: list[str] = MESSAGE_VAR_RE.findall(command.message)
    populated_variables = populate_message_variables(
        vars=message_vars, player_id=player_id
    )
    formatted_message = format_message_string(
        command.message,
        populated_variables=populated_variables,
        context=ctx,
    )
    rcon.message_player(
        player_id=player_id,
        message=formatted_message,
        save_message=False,
    )


def chat_rcon_command(
    rcon: Rcon,
    command: RConChatCommand,
    ctx: dict[str, str],
    triggering_word: str,
    msg: str,
):
    player_id = ctx[MessageVariableContext.player_id.value]
    player: PlayerID
    with enter_session() as session:
        player = (
            session.query(PlayerID)
            .filter(PlayerID.player_id == player_id)
            .one_or_none()
        )
        if player is None:
            logger.debug(
                "player executed a command but does not exist in database: %s",
                player_id,
            )
        if not command.conditions_fulfilled(rcon, player, ctx):
            return

        arguments = msg[msg.find(triggering_word) + len(triggering_word) + 1 :]
        args = shlex.split(arguments)
        expected_argument_count = 0
        for _, params in command.commands.items():
            for _, v in params.items():
                a = max_arg_index(v)
                if a > expected_argument_count:
                    expected_argument_count = a
        if len(args) != expected_argument_count:
            logger.info(
                "provided message does not have expected number of arguments. Expected %d, got %d. Message: %s, Command: %s",
                expected_argument_count,
                len(args),
                msg,
                triggering_word,
            )
            return

        commands: dict[str, dict[str, str | list[str]]] = {}
        for name, params in command.commands.items():
            logger.info("Original: %s -> %s, args: %s", name, params, args)
            commands[name] = {}
            for k, v in params.items():
                commands[name][k] = replace_params(ctx, args, v)

        do_run_commands(rcon, commands)


def chat_help_command(rcon: Rcon, command: BaseChatCommand, ctx: dict[str, str]):
    player_id = ctx[MessageVariableContext.player_id.value]
    description = command.description
    if description:
        rcon.message_player(
            player_id=player_id,
            message=description,
            save_message=False,
        )
    else:
        rcon.message_player(
            player_id=player_id,
            message="Command description not set, let the admins know!",
            save_message=False,
        )
        logger.warning(
            "No descriptions set for chat command word(s), %s",
            ", ".join(command.words),
        )


@on_match_end
def remind_vote_map(rcon: Rcon, struct_log):
    logger.info("Match ended reminding to vote map. %s", struct_log)
    vote_map = VoteMap()
    vote_map.apply_with_retry()
    vote_map.vote_map_reminder(rcon, force=True)


@on_match_start
def reset_watch_killrate_cooldown(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    """Reset the last reported time cache for new matches"""
    from rcon.watch_killrate import reset_cache

    reset_cache()


@on_match_start
def handle_new_match_start(rcon: Rcon, struct_log):
    try:
        logger.info("New match started recording map %s", struct_log)
        with invalidates(Rcon.get_map, Rcon.get_next_map):
            try:
                # Don't use the current_map property and clear the cache to pull the new map name
                current_map = rcon.get_map()
            except HLLCommandFailedError:
                current_map = parse_layer(UNKNOWN_MAP_NAME)
                logger.error(
                    "Unable to get current map, falling back to recording map as %s",
                    UNKNOWN_MAP_NAME,
                )

        guessed = True
        log_map_name = struct_log["sub_content"].rsplit(" ", 1)[0]
        log_time = datetime.fromtimestamp(struct_log["timestamp_ms"] / 1000)
        # Check that the log is less than 5min old
        if (datetime.utcnow() - log_time).total_seconds() < 5 * 60:
            # then we use the current map to be more accurate
            if current_map.map.name.lower() == log_map_name.lower().removesuffix(
                " night"
            ):
                map_name_to_save = current_map
                guessed = False
            else:
                map_name_to_save = parse_layer(UNKNOWN_MAP_NAME)
                logger.warning(
                    "Got recent match start but map doesn't match %s != %s",
                    log_map_name,
                    current_map.map.name,
                )
        else:
            map_name_to_save = str(current_map)

        # TODO added guess - check if it's already in there - set prev end if None
        maps_history = MapsHistory()
        if len(maps_history) > 0:
            if maps_history[0]["end"] is None and maps_history[0]["name"]:
                maps_history.save_map_end(
                    old_map=maps_history[0]["name"],
                    end_timestamp=int(struct_log["timestamp_ms"] / 1000),
                )

        game_layout = GameLayout
        try:
            red = get_redis_client()
            raw = red.getdel('GAME_LAYOUT')
            game_layout = json.loads(raw) if raw is not None else {}
        except Exception as e:
            logger.error("Could not fetch Game Layout", e)
            pass
        map_start_ts = int(struct_log["timestamp_ms"] / 1000)
        maps_history.save_new_map(
            new_map=str(map_name_to_save),
            guessed=guessed,
            start_timestamp=map_start_ts,
            game_layout=game_layout,
        )
        
    except:
        raise
    finally:
        initialise_vote_map(struct_log)
        try:
            record_stats_worker(MapsHistory()[1])
        except Exception:
            logger.exception("Unexpected error while running stats worker")


# Порог игроков для переключения логики rotation
PLAYER_COUNT_THRESHOLD = 40  # Если < 40: St. Mary карты, если >= 40: обычная rotation

def _get_st_mary_day_maps():
    """Возвращает список карт St. Mere Eglise (день) и St. Marie Du Mont (день)"""
    return [
        parse_layer("stmereeglise_warfare"),
        parse_layer("stmariedumont_warfare"),
    ]


def _get_last_st_mary_map_id(red):
    """Получает ID последней использованной St. Mary карты из Redis"""
    key = "last_st_mary_map_id"
    value = red.get(key)
    if value:
        if isinstance(value, bytes):
            value = value.decode()
        return value
    return None


def _set_last_st_mary_map_id(red, map_id):
    """Сохраняет ID последней использованной St. Mary карты в Redis"""
    key = "last_st_mary_map_id"
    red.setex(key, 24 * 60 * 60, map_id)  # Храним 24 часа


def _get_map_max_players(map_info: dict) -> int | None:
    """
    Получает количество игроков для карты из player_stats.
    Использует len(player_stats) из MapsHistory.
    """
    if map_info and map_info.get("player_stats"):
        player_stats = map_info.get("player_stats", {})
        if isinstance(player_stats, dict):
            player_count = len(player_stats)
            if player_count > 0:
                return player_count
    return None


def _get_last_5_maps_with_40_plus_players(maps_history: MapsHistory) -> set:
    """
    Возвращает множество базовых ID карт из последних 5 игр, где было >=PLAYER_COUNT_THRESHOLD игроков.
    
    Логика:
    - Проходит по всей истории карт
    - Фильтрует только игры с >=PLAYER_COUNT_THRESHOLD игроками
    - Берет последние 5 из отфильтрованных
    - Возвращает их base_map_ids для исключения из rotation
    
    Пример:
    - Позавчера: 3 игры с 50 игроками (A, B, C)
    - Вчера: 4 игры с 20 игроками (D, E, F, G) - пропускаются
    - Сегодня: 1 игра с 10 игроками (H) - пропускается
    - Сегодня: 4 игры с 60 игроками (I, J, K, L)
    Результат: исключаем L, K, J, I, C (последние 5 игр с >=40)
    """
    exclude_last_n = 5  # Берем последние 5 игр с >=40 игроками
    last_5_base_map_ids = set()
    
    if len(maps_history) == 0:
        return last_5_base_map_ids
    
    # Сначала фильтруем все игры с >=PLAYER_COUNT_THRESHOLD игроками
    maps_with_40_plus = []
    
    for map_info in maps_history:
        if map_info.get("name") and map_info.get("start"):
            try:
                parsed = parse_layer(map_info["name"])
                
                # Проверяем количество игроков для этой карты из player_stats
                max_players = _get_map_max_players(map_info)
                
                # Учитываем только карты с >=PLAYER_COUNT_THRESHOLD игроками
                if max_players is not None and max_players >= PLAYER_COUNT_THRESHOLD:
                    maps_with_40_plus.append({
                        "map_info": map_info,
                        "parsed": parsed,
                        "max_players": max_players
                    })
            except Exception as e:
                logger.warning(f"[ROTATION FILTER] Failed to parse map {map_info.get('name')}: {e}")
    
    # Берем последние N игр из отфильтрованных
    last_n_maps = maps_with_40_plus[:exclude_last_n]
    
    for map_data in last_n_maps:
        parsed = map_data["parsed"]
        last_5_base_map_ids.add(parsed.map.id)
    return last_5_base_map_ids


def _check_and_update_rotation(rcon: Rcon, player_count: int, context: str = "unknown"):
    """
    Проверяет и обновляет ротацию карт в зависимости от количества игроков.
    Вызывается при начале матча и при изменении количества игроков.
    
    Args:
        rcon: Rcon instance
        player_count: Количество игроков для проверки (может быть None)
        context: Контекст вызова для логирования (например, "match_start", "match_end", "player_connected")
    """
    try:
        # Получаем текущую карту
        try:
            current_map = rcon.get_map()
        except HLLCommandFailedError:
            logger.warning("[ROTATION FILTER] Could not get current map, skipping rotation check")
            return

        # Получаем следующую карту из ротации
        rotation = rcon.get_map_rotation()["maps"]
        next_map_in_rotation = None
        if rotation and len(rotation) > 1:
            next_map_in_rotation = rotation[1]
        elif rotation:
            try:
                next_map_in_rotation = rcon.get_next_map()
            except Exception as e:
                logger.warning(f"[ROTATION FILTER] Could not get next map: {e}")
        
        if not next_map_in_rotation:
            logger.warning("[ROTATION FILTER] No next map found in rotation")

        slots = rcon.get_slots()
        current_player_count = slots["current_players"]
        
        # Используем переданное количество или текущее
        if player_count is None:
            player_count = current_player_count

        red = get_redis_client()
        st_mary_day_maps = _get_st_mary_day_maps()
        current_map_parsed = parse_layer(str(current_map))
        
        # Если < PLAYER_COUNT_THRESHOLD игроков - только St. Mary карты (день) по очереди
        if player_count < PLAYER_COUNT_THRESHOLD:
            # Если следующая карта не St. Mary (день), меняем её
            if next_map_in_rotation:
                next_map_parsed = parse_layer(str(next_map_in_rotation))
                is_next_st_mary_day = any(
                    next_map_parsed.map.id == m.map.id 
                    for m in st_mary_day_maps
                )
                
                if not is_next_st_mary_day:
                    # Получаем последнюю использованную St. Mary карту
                    last_st_mary_id = _get_last_st_mary_map_id(red)
                    
                    # Выбираем другую St. Mary карту (по очереди)
                    if last_st_mary_id:
                        # Находим индекс последней карты
                        last_index = next(
                            (i for i, m in enumerate(st_mary_day_maps) if m.map.id == last_st_mary_id),
                            -1
                        )
                        # Берем следующую по очереди
                        next_index = (last_index + 1) % len(st_mary_day_maps)
                        new_map = st_mary_day_maps[next_index]
                    else:
                        # Первый раз - выбираем случайную
                        new_map = random.choice(st_mary_day_maps)
                    
                    logger.info(
                        f"[ROTATION FILTER] Players {player_count} < {PLAYER_COUNT_THRESHOLD}: changing next map from {next_map_in_rotation.pretty_name} to {new_map.pretty_name}"
                    )
                    rcon.set_map_rotation([current_map.id, new_map.id])
                    _set_last_st_mary_map_id(red, new_map.map.id)
                    return
        
        # Если >= PLAYER_COUNT_THRESHOLD игроков - обычный rotation с логикой исключения последних 5 игр с >=40 игроками
        else:
            maps_history = MapsHistory()
            # Получаем базовые имена карт из последних 5 игр с >=40 игроками
            last_5_base_map_ids = _get_last_5_maps_with_40_plus_players(maps_history)
            
            if next_map_in_rotation:
                next_map_parsed = parse_layer(str(next_map_in_rotation))
                next_base_map_id = next_map_parsed.map.id
                
                # Проверяем, является ли текущая карта St. Mary (день)
                is_current_st_mary_day = any(
                    current_map_parsed.map.id == m.map.id 
                    for m in st_mary_day_maps
                )
                
                # Проверяем, является ли следующая карта St. Mary (день)
                is_next_st_mary_day = any(
                    next_map_parsed.map.id == m.map.id 
                    for m in st_mary_day_maps
                )
                
                # Проверяем, не повторяется ли базовая карта из последних 5 игр с >=40 игроками
                # (проверка по base_id, чтобы исключить Kharkov Offensive если был Kharkov Warfare)
                is_in_excluded = next_base_map_id in last_5_base_map_ids
                
                # Если текущая карта St. Mary (день), то следующая НЕ должна быть St. Mary (день)
                # (чтобы не было двух подряд матчей на St. Mary картах)
                should_avoid_st_mary = is_current_st_mary_day and is_next_st_mary_day
                
                # Если базовая карта повторяется из последних 5 игр с >=40 игроками ИЛИ
                # текущая карта St. Mary и следующая тоже St. Mary - меняем
                if is_in_excluded or should_avoid_st_mary:
                    # Получаем все доступные карты
                    all_maps = [parse_layer(m) for m in rcon.get_maps()]
                    
                    # Исключаем:
                    # 1. Карты из последних 5 игр с >=40 игроками (по base_id)
                    # 2. Текущую карту
                    # 3. St. Mary карты (день), если текущая карта тоже St. Mary (чтобы не было двух подряд)
                    current_base_map_id = current_map_parsed.map.id
                    available_maps = [
                        m for m in all_maps 
                        if m.map.id not in last_5_base_map_ids  # Исключаем по base_id (Kharkov Offensive = Kharkov Warfare)
                        and m.map.id != current_base_map_id
                        and not (is_current_st_mary_day and any(m.map.id == sm.map.id for sm in st_mary_day_maps))  # Если текущая St. Mary, исключаем все St. Mary
                    ]
                    
                    if not available_maps:
                        available_maps = [
                            m for m in all_maps 
                            if m.map.id != current_base_map_id
                            and not (is_current_st_mary_day and any(m.map.id == sm.map.id for sm in st_mary_day_maps))
                        ]
                    
                    if available_maps:
                        # Выбираем случайную карту из доступных
                        new_map = random.choice(available_maps)
                        reason_parts = []
                        if is_in_excluded:
                            reason_parts.append("in last 5 games with >=40 players")
                        if should_avoid_st_mary:
                            reason_parts.append("avoiding consecutive St. Mary")
                        reason = " / ".join(reason_parts) if reason_parts else "unknown"
                        logger.info(
                            f"[ROTATION FILTER] Players {player_count} >= {PLAYER_COUNT_THRESHOLD}: changing next map from {next_map_in_rotation.pretty_name} ({reason}) to {new_map.pretty_name}"
                        )
                        rcon.set_map_rotation([current_map.id, new_map.id])
                        return
                    else:
                        logger.warning(f"[ROTATION FILTER] No available maps found after filtering, cannot change rotation")
        
    except Exception as e:
        logger.exception(f"Error in _check_and_update_rotation: {e}")


@on_match_start
def filter_map_rotation(rcon: Rcon, struct_log):
    """
    Фильтрует ротацию карт при начале матча:
    - Если < PLAYER_COUNT_THRESHOLD игроков: только St. Mere Eglise (день) или St. Marie Du Mont (день) по очереди
    - Если >= PLAYER_COUNT_THRESHOLD игроков: обычный rotation с логикой shuffle (не повторять карты из последних 5 игр)
    """
    try:
        logger.info("[ROTATION FILTER] Match started, checking rotation")
        slots = rcon.get_slots()
        player_count = slots["current_players"]
        _check_and_update_rotation(rcon, player_count, context="match_start")
    except Exception as e:
        logger.exception(f"[ROTATION FILTER] Error in filter_map_rotation: {e}")


@on_connected()
def check_player_count_for_rotation(rcon: Rcon, _, name: str, player_id: str):
    """
    Проверяет количество игроков при подключении и обновляет ротацию если нужно.
    Если количество изменилось с <PLAYER_COUNT_THRESHOLD на >=PLAYER_COUNT_THRESHOLD, меняет следующую карту.
    """
    try:
        # Небольшая задержка, чтобы количество игроков успело обновиться
        time_module.sleep(1)
        
        slots = rcon.get_slots()
        player_count = slots["current_players"]
        
        logger.info(f"[ROTATION FILTER] Player {name} connected, current players: {player_count}")
        
        # Проверяем и обновляем ротацию
        _check_and_update_rotation(rcon, player_count, context="player_connected")
    except Exception as e:
        logger.debug(f"[ROTATION FILTER] Error in check_player_count_for_rotation: {e}")




@on_match_end
def record_map_end(rcon: Rcon, struct_log):
    logger.info("Match ended recording map %s", struct_log)
    maps_history = MapsHistory()
    try:
        current_map = rcon.current_map
    except HLLCommandFailedError:
        current_map = parse_layer(UNKNOWN_MAP_NAME)
        logger.error(
            "Unable to get current map, falling back to recording map as %s",
            current_map,
        )

    # Log map names are inconsistently formatted but should match the map name that each Layer has
    log_map_name = struct_log["sub_content"]
    log_time = datetime.fromtimestamp(struct_log["timestamp_ms"] / 1000)

    # The log event loop can receive and process old log lines sometimes
    # Check to make sure that if we're processing an old logl ine
    if (datetime.utcnow() - log_time).total_seconds() < 60:
        # then we use the current map to be more accurate
        if current_map.map.name.lower() in log_map_name.lower():
            
            maps_history.save_map_end(
                str(current_map), end_timestamp=int(struct_log["timestamp_ms"] / 1000)
            )
            
            # Проверяем и обновляем ротацию для следующей карты
            try:
                slots = rcon.get_slots()
                player_count = slots["current_players"]
                _check_and_update_rotation(rcon, player_count, context="match_end")
            except Exception as e:
                logger.exception(f"[ROTATION FILTER] Error checking rotation at match end: {e}")
        return

    # If we're processing an old match
    current_map = parse_layer(UNKNOWN_MAP_NAME)
    logger.info(f"Recording map end: {current_map}")
    maps_history.save_map_end(
        str(current_map), end_timestamp=int(struct_log["timestamp_ms"] / 1000)
    )


def ban_if_blacklisted(rcon: Rcon, player_id: str, name: str):
    with enter_session() as sess:
        blacklist = is_player_blacklisted(sess, player_id)
        if not blacklist:
            return False

        return apply_blacklist_punishment(
            rcon, blacklist, player_id=player_id, player_name=name
        )


def should_ban(
    bans: SteamBansType | None,
    max_game_bans: float,
    max_days_since_ban: int,
    player_flags: list[PlayerFlagType] = [],
    whitelist_flags: list[str] = [],
) -> bool | None:
    if not bans:
        return

    if any(player_flag in whitelist_flags for player_flag in player_flags):
        return False

    try:
        days_since_last_ban = int(bans["DaysSinceLastBan"])
        number_of_game_bans = int(bans.get("NumberOfGameBans", 0))
    except ValueError:  # In case DaysSinceLastBan can be null
        return

    has_a_ban = bans.get("VACBanned") == True or number_of_game_bans >= max_game_bans

    if days_since_last_ban <= 0:
        return False

    if days_since_last_ban <= max_days_since_ban and has_a_ban:
        return True

    return False


def ban_if_has_vac_bans(rcon: Rcon, player_id: str, name: str):
    config = VacGameBansUserConfig.load_from_db()

    max_days_since_ban = config.vac_history_days
    max_game_bans = (
        float("inf") if config.game_ban_threshhold <= 0 else config.game_ban_threshhold
    )
    whitelist_flags = config.whitelist_flags

    if max_days_since_ban <= 0:
        return  # Feature is disabled

    with enter_session() as sess:
        player = get_player(sess, player_id)

        if not player:
            logger.error("Can't check VAC history, player not found %s", player_id)
            return

        bans = player.steaminfo.bans if player.steaminfo else None
        if not bans or not isinstance(bans, dict):
            logger.warning(
                "Can't fetch Bans for player %s, received %s", player_id, bans
            )
            return

        if should_ban(
            bans,
            max_game_bans,
            max_days_since_ban,
            player_flags=player.flags,
            whitelist_flags=whitelist_flags,
        ):
            days_since_last_ban = bans["DaysSinceLastBan"]
            reason = config.ban_on_vac_history_reason.format(
                DAYS_SINCE_LAST_BAN=days_since_last_ban,
                MAX_DAYS_SINCE_BAN=str(max_days_since_ban),
            )
            if config.auto_expire:
                days_until_expire = max_days_since_ban - days_since_last_ban
                expires_at = datetime.now(tz=timezone.utc) + timedelta(
                    days=days_until_expire
                )
            else:
                expires_at = None
            blacklist_or_ban(
                rcon=rcon,
                blacklist_id=config.blacklist_id,
                player_id=player_id,
                reason=reason,
                expires_at=expires_at,
                admin_name="VAC BOT",
            )
            logger.info(
                "Player %s was banned due VAC history, last ban: %s days ago",
                str(player),
                bans.get("DaysSinceLastBan"),
            )


def inject_player_ids(func):
    @wraps(func)
    def wrapper(rcon, struct_log: StructuredLogLineWithMetaData):
        name = struct_log["player_name_1"]
        player_id = struct_log["player_id_1"]
        return func(rcon, struct_log, name, player_id)

    return wrapper


@on_connected()
@inject_player_ids
def handle_on_connect(
    rcon: Rcon, struct_log: StructuredLogLineWithMetaData, name: str, player_id: str
):
    try:
        rcon.get_players.cache_clear()
        rcon.get_player_info.clear_for(player_id=struct_log["player_id_1"])
        rcon.get_detailed_player_info.clear_for(player_id=struct_log["player_id_1"])
    except Exception:
        logger.exception("Unable to clear cache for %s", player_id)

    timestamp = int(struct_log["timestamp_ms"]) / 1000
    if not player_id:
        logger.error(
            "Unable to get player ID for %s, can't process connection",
            struct_log,
        )
        return
    save_player(
        struct_log["player_name_1"],
        player_id,
        timestamp=int(struct_log["timestamp_ms"]) / 1000,
    )

    blacklisted = ban_if_blacklisted(rcon, player_id, struct_log["player_name_1"])
    if blacklisted:
        # We don't need the player potentially blacklisted a second
        # time because of VAC bans. So we return here.
        return

    save_start_player_session(player_id, timestamp=timestamp)
    ban_if_has_vac_bans(rcon, player_id, struct_log["player_name_1"])


@on_disconnected
@inject_player_ids
def handle_on_disconnect(rcon, struct_log, _, player_id: str):
    save_end_player_session(player_id, struct_log["timestamp_ms"] / 1000)


# Make the steam API call before the handle_on_connect hook so it's available for ban_if_blacklisted
@on_connected(0)
@inject_player_ids
def update_player_steaminfo_on_connect(
    rcon, struct_log: StructuredLogLineWithMetaData, _, player_id: str
):
    if not player_id:
        logger.error(
            "Can't update steam info, no steam id available for %s",
            struct_log.get("player_name_1"),
        )
        return

    logger.info(
        "Updating steam profile for player %s %s",
        struct_log["player_name_1"],
        struct_log["player_id_1"],
    )
    with enter_session() as sess:
        player = _get_set_player(
            sess, player_name=struct_log["player_name_1"], player_id=player_id
        )

        steam_utils.update_missing_old_steam_info_single_player(
            sess=sess, player=player
        )


@on_connected()
@inject_player_ids
def windows_store_player_check(rcon: Rcon, _, name: str, player_id: str):
    config = RconServerSettingsUserConfig.load_from_db().windows_store_players

    if not config.enabled or steam_utils.is_steam_id_64(player_id):
        return

    action = config.action
    action_value = action.value if action else None

    logger.info(
        "Windows store player '%s' (%s) connected, action=%s",
        name,
        player_id,
        action_value,
    )

    try:
        send_to_discord_audit(
            message=config.audit_message.format_map(
                DefaultStringFormat(name=name, player_id=player_id, action=action_value)
            ),
            command_name=str(action_value),
        )
    except Exception:
        logger.exception(
            "Unable to send %s %s (%s) to audit", action_value, name, player_id
        )

    try:
        if action == WindowsStoreIdActionType.kick:
            rcon.kick(
                name,
                reason=config.player_message,
                by=config.audit_message_author,
                player_id=player_id,
            )
        elif action == WindowsStoreIdActionType.temp_ban:
            rcon.temp_ban(
                player_id=player_id,
                duration_hours=config.temp_ban_length_hours,
                reason=config.player_message,
                by=config.audit_message_author,
            )
        elif action == WindowsStoreIdActionType.perma_ban:
            rcon.perma_ban(
                player_id=player_id,
                reason=config.player_message,
                by=config.audit_message_author,
            )
    except Exception as e:
        logger.error(
            "Could not %s whitespace name player %s/%s: %s",
            action_value,
            name,
            player_id,
            e,
        )


def _set_real_vips(rcon: Rcon, struct_log):
    config = RealVipUserConfig.load_from_db()
    if not config.enabled:
        logger.debug("Real VIP is disabled")
        return

    desired_nb_vips = config.desired_total_number_vips
    min_vip_slot = config.minimum_number_vip_slots
    vip_count = rcon.get_vips_count()

    remaining_vip_slots = max(desired_nb_vips - vip_count, max(min_vip_slot, 0))
    rcon.set_vip_slots_num(remaining_vip_slots)
    logger.info("Real VIP set slots to %s", remaining_vip_slots)


@on_connected()
def do_real_vips(rcon: Rcon, struct_log):
    _set_real_vips(rcon, struct_log)


@on_disconnected
def undo_real_vips(rcon: Rcon, struct_log):
    _set_real_vips(rcon, struct_log)


@on_camera
def notify_camera(rcon: Rcon, struct_log):
    send_to_discord_audit(
        command_name="camera", message=struct_log["message"], by="CRCON"
    )
    short_name: Final = RconServerSettingsUserConfig.load_from_db().short_name

    try:
        if hooks := get_prepared_discord_hooks(CameraWebhooksUserConfig):
            embeded = DiscordEmbed(
                title=f'{escape_markdown(struct_log["player_name_1"])}  - {escape_markdown(struct_log["player_id_1"])}',
                description=f'{short_name} - {struct_log["sub_content"]}',
                color=242424,
            )
            for h in hooks:
                h.add_embed(embeded)
                h.execute()
    except Exception:
        logger.exception("Unable to forward to hooks")

    config = CameraNotificationUserConfig.load_from_db()
    if config.broadcast:
        temporary_broadcast(rcon, struct_log["message"], 60)

    if config.welcome:
        temporary_welcome(rcon, struct_log["message"], 60)


# Custom plugins hooks
# -----------------------------------------------------------------------------

@on_chat
def livetopstats_onchat(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    live_topstats.stats_on_chat_command(rcon, struct_log)


@on_match_end
def livetopstats_onmatchend(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    live_topstats.stats_on_match_end(rcon, struct_log)


@on_connected()
def alltimestats_on_connected(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    all_time_stats.all_time_stats_on_connected(rcon, struct_log)


@on_chat
def alltimestats_on_chat_command(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    all_time_stats.all_time_stats_on_chat_command(rcon, struct_log)
