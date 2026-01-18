import logging
import pickle
import time

from rcon.audit import ingame_mods, online_mods
from rcon.cache_utils import get_redis_client
from rcon.commands import HLLCommandFailedError
from rcon.rcon import HLLCommandFailedError, Rcon, get_rcon
from rcon.user_config.auto_kick import AutoVoteKickUserConfig
from rcon.vote_map import VoteMap

logger = logging.getLogger(__name__)


def toggle_votekick(rcon: Rcon):
    config = AutoVoteKickUserConfig.load_from_db()

    if not config.enabled:
        return

    condition_type = config.condition.upper()
    min_online = config.minimum_online_mods
    min_ingame = config.minimum_ingame_mods
    condition = all if condition_type == "AND" else any
    online_mods_ = online_mods()
    ingame_mods_ = ingame_mods(rcon)

    ok_online = len(online_mods_) >= min_online
    ok_ingame = len(ingame_mods_) >= min_ingame

    if condition([ok_ingame, ok_online]):
        logger.debug(
            f"Turning votekick off {condition_type=} {min_online=} {min_ingame=} {ok_online=} {ok_ingame=} {online_mods_=} {ingame_mods_=}"
        )
        rcon.set_votekick_enabled(False)
    else:
        logger.debug(
            f"Turning votekick on {condition_type=} {min_online=} {min_ingame=} {ok_online=} {ok_ingame=} {online_mods_=} {ingame_mods_=}"
        )
        rcon.set_votekick_enabled(True)


def auto_disband_empty_squads(rcon: Rcon):
    """
    Automatically disband empty squads and track who created them.
    Empty squads are squads with 0 players.
    """
    try:
        logger.info("[EMPTY SQUAD] Starting auto_disband_empty_squads check")
        red = get_redis_client()
        team_view = rcon.get_team_view()
        detailed_players = rcon.get_detailed_players()["players"]
        logger.debug(f"[EMPTY SQUAD] Got team_view and detailed_players. Teams: {list(team_view.keys())}, Players: {len(detailed_players)}")
        
        # Get previous state from Redis to track squad creation
        previous_squads_key = "previous_squads_state"
        previous_squads_raw = red.get(previous_squads_key)
        previous_squads = pickle.loads(previous_squads_raw) if previous_squads_raw else {}
        logger.debug(f"[EMPTY SQUAD] Previous squads count: {len(previous_squads)}")
        
        current_squads = {}
        empty_squads_to_disband = []
        new_squads = []
        
        # Build a map of all squads from detailed_players to catch empty squads
        # that might not appear in get_team_view()
        all_squads_from_players = {}
        for player in detailed_players.values():
            team_raw = player.get("team")
            # Handle None or empty team
            if team_raw is None:
                continue
            team = str(team_raw).lower() if team_raw else ""
            squad_name = player.get("unit_name", "")
            if team and squad_name and squad_name not in ["unassigned", "Commander"]:
                squad_key = f"{team}:{squad_name}"
                if squad_key not in all_squads_from_players:
                    all_squads_from_players[squad_key] = {
                        "team": team,
                        "squad": squad_name,
                        "players": []
                    }
                all_squads_from_players[squad_key]["players"].append(player)
        
        # Check all teams from team_view
        for team_name in ["allies", "axis"]:
            if team_name not in team_view:
                continue
                
            team_data = team_view[team_name]
            squads = team_data.get("squads", {})
            
            for squad_name, squad_data in squads.items():
                # Skip unassigned and commander
                if squad_name == "unassigned" or squad_name == "Commander":
                    continue
                
                players = squad_data.get("players", [])
                player_count = len(players)
                
                # Track current squads
                squad_key = f"{team_name}:{squad_name}"
                current_squads[squad_key] = {
                    "team": team_name,
                    "squad": squad_name,
                    "player_count": player_count,
                    "players": [p.get("name", "Unknown") for p in players],
                }
                
                # Debug: Log all squads for troubleshooting
                logger.debug(
                    f"[EMPTY SQUAD DEBUG] Squad {squad_name} in {team_name}: {player_count} players"
                )
                
                # Check if squad is empty (0 players)
                # Note: Empty squads might appear in get_team_view() temporarily
                # before the game removes them automatically, or they might persist
                # if created before our tracking started
                if player_count == 0:
                    # Log who created this empty squad (if we tracked it)
                    creator_key = f"squad_creator:{team_name}:{squad_name}"
                    creator_info = red.get(creator_key)
                    creator_name = "Unknown"
                    creator_id = "Unknown"
                    created_at = "Unknown"
                    
                    if creator_info:
                        creator_info = pickle.loads(creator_info)
                        creator_name = creator_info.get('player_name', 'Unknown')
                        creator_id = creator_info.get('player_id', 'Unknown')
                        created_at = creator_info.get('created_at', 'Unknown')
                    
                    # Always log empty squads, even if we don't know the creator
                    if creator_name != "Unknown":
                        logger.info(
                            f"[EMPTY SQUAD] Found empty squad {squad_name} in {team_name} team. "
                            f"Created by: {creator_name} ({creator_id}) at {created_at}"
                        )
                    else:
                        logger.info(
                            f"[EMPTY SQUAD] Found empty squad {squad_name} in {team_name} team. "
                            f"Created before tracking started (creator unknown)"
                        )
                    
                    # Add to list for processing
                    empty_squads_to_disband.append({
                        "team": team_name,
                        "squad": squad_name,
                        "creator_name": creator_name,
                        "creator_id": creator_id,
                    })
                
                # Track new squads (squads that appeared since last check)
                if squad_key not in previous_squads:
                    logger.debug(f"[NEW SQUAD] Detected new squad: {squad_key} with {player_count} players")
                    # This is a new squad, try to find who created it
                    if player_count > 0:
                        # Squad has players, the first player (usually the leader) likely created it
                        creator = players[0] if players else None
                        if creator:
                            creator_key = f"squad_creator:{team_name}:{squad_name}"
                            creator_info = {
                                "player_name": creator.get("name", "Unknown"),
                                "player_id": creator.get("player_id", "Unknown"),
                                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                            }
                            red.setex(creator_key, 3600, pickle.dumps(creator_info))  # Store for 1 hour
                            
                            # Get all players in the squad for logging
                            squad_players_names = [p.get("name", "Unknown") for p in players]
                            
                            logger.info(
                                f"[NEW SQUAD] Squad '{squad_name}' created in {team_name} team. "
                                f"Creator: {creator_info['player_name']} ({creator_info['player_id']}). "
                                f"Players ({player_count}): {', '.join(squad_players_names)}"
                            )
                            new_squads.append({
                                "team": team_name,
                                "squad": squad_name,
                                "creator": creator_info,
                            })
                    else:
                        # New squad but empty (shouldn't happen often, but log it)
                        logger.info(
                            f"[NEW SQUAD] Empty squad '{squad_name}' appeared in {team_name} team "
                            f"(created before tracking started or appeared empty)"
                        )
        
        # Check for squads that existed before but are now empty
        # (they won't appear in current team_view if they have 0 players)
        for squad_key, previous_squad_info in previous_squads.items():
            if squad_key not in current_squads:
                # Squad disappeared from team_view - check if it's because it's empty
                team_name = previous_squad_info["team"]
                squad_name = previous_squad_info["squad"]
                
                # Check if this squad still exists but is empty
                # by checking if any players are in this squad
                squad_players_in_detailed = []
                for p in detailed_players.values():
                    team_raw = p.get("team")
                    if team_raw is None:
                        continue
                    team = str(team_raw).lower() if team_raw else ""
                    if team == team_name and p.get("unit_name", "") == squad_name:
                        squad_players_in_detailed.append(p)
                
                if len(squad_players_in_detailed) == 0:
                    # Squad exists in previous state but has no players now
                    # This is an empty squad that disappeared from team_view
                    creator_key = f"squad_creator:{team_name}:{squad_name}"
                    creator_info = red.get(creator_key)
                    creator_name = "Unknown"
                    creator_id = "Unknown"
                    created_at = "Unknown"
                    
                    if creator_info:
                        creator_info = pickle.loads(creator_info)
                        creator_name = creator_info.get('player_name', 'Unknown')
                        creator_id = creator_info.get('player_id', 'Unknown')
                        created_at = creator_info.get('created_at', 'Unknown')
                    
                    logger.info(
                        f"[EMPTY SQUAD] Found empty squad {squad_name} in {team_name} team "
                        f"(disappeared from team_view, likely empty). "
                        f"Created by: {creator_name} ({creator_id}) at {created_at}"
                    )
                    
                    empty_squads_to_disband.append({
                        "team": team_name,
                        "squad": squad_name,
                        "creator_name": creator_name,
                        "creator_id": creator_id,
                    })
        
        # Debug: Log all squads we found
        logger.debug(
            f"[EMPTY SQUAD DEBUG] Found {len(current_squads)} squads in team_view, "
            f"{len(all_squads_from_players)} squads from detailed_players, "
            f"{len(empty_squads_to_disband)} empty squads detected, "
            f"{len(new_squads)} new squads detected"
        )
        
        # Log summary
        if new_squads:
            logger.info(f"[NEW SQUAD] Summary: {len(new_squads)} new squad(s) detected in this check")
        
        # Disband empty squads
        # Note: disband_squad_by_name requires players in the squad to remove them.
        # If squad is already empty, we can't use disband_squad_by_name, but we log it.
        # The game should remove empty squads automatically, but we track them for monitoring.
        for empty_squad in empty_squads_to_disband:
            try:
                # Double-check by getting detailed players to see if squad still exists
                detailed_players_check = rcon.get_detailed_players()["players"]
                squad_players = []
                for p in detailed_players_check.values():
                    team_raw = p.get("team")
                    if team_raw is None:
                        continue
                    team = str(team_raw).lower() if team_raw else ""
                    if team == empty_squad["team"] and p.get("unit_name", "") == empty_squad["squad"]:
                        squad_players.append(p)
                
                if squad_players:
                    # Squad has players now (shouldn't happen if we detected it as empty)
                    logger.warning(
                        f"[EMPTY SQUAD] Squad {empty_squad['squad']} in {empty_squad['team']} "
                        f"now has {len(squad_players)} players, skipping disband"
                    )
                else:
                    # Squad is confirmed empty - log it
                    # Note: We can't disband it via disband_squad_by_name because it requires players
                    # The game should remove empty squads automatically, but we track them
                    creator_info_str = ""
                    if empty_squad["creator_name"] != "Unknown":
                        # Get created_at from Redis if available
                        creator_key = f"squad_creator:{empty_squad['team']}:{empty_squad['squad']}"
                        creator_info_redis = red.get(creator_key)
                        created_at_str = "unknown time"
                        if creator_info_redis:
                            try:
                                creator_info_parsed = pickle.loads(creator_info_redis)
                                created_at_str = creator_info_parsed.get('created_at', 'unknown time')
                            except:
                                pass
                        creator_info_str = f" (created by {empty_squad['creator_name']} at {created_at_str})"
                    else:
                        creator_info_str = " (existed before tracking started - creator unknown)"
                    
                    logger.info(
                        f"[EMPTY SQUAD] Empty squad {empty_squad['squad']} in {empty_squad['team']} team detected."
                        f"{creator_info_str} "
                        f"Game should remove it automatically. If it persists, it may be a display artifact."
                    )
            except Exception as e:
                logger.debug(f"[EMPTY SQUAD] Error checking squad {empty_squad['squad']}: {e}")
        
        # Save current state for next check
        red.setex(previous_squads_key, 300, pickle.dumps(current_squads))  # Store for 5 minutes
        
        # Clean up creator info for squads that no longer exist
        for squad_key in previous_squads:
            if squad_key not in current_squads:
                team_name, squad_name = squad_key.split(":", 1)
                creator_key = f"squad_creator:{team_name}:{squad_name}"
                red.delete(creator_key)
                
    except Exception as e:
        logger.exception(f"[EMPTY SQUAD] Error in auto_disband_empty_squads: {e}")
        # Log the error type to help debug
        logger.error(f"[EMPTY SQUAD] Exception type: {type(e).__name__}, message: {str(e)}")


def run():
    max_fails = 5
    rcon = get_rcon()

    while True:
        try:
            toggle_votekick(rcon)
            VoteMap().vote_map_reminder(rcon)
            auto_disband_empty_squads(rcon)
        except HLLCommandFailedError:
            max_fails -= 1
            if max_fails <= 0:
                logger.exception("Routines 5 failures in a row. Stopping")
                raise
        time.sleep(30)
