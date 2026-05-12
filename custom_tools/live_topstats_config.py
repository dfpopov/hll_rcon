"""
live_topstat_config.py

A plugin for HLL CRCON (see : https://github.com/MarechJ/hll_rcon_tool)
that displays and rewards top players

Source : https://github.com/ElGuillermo

Feel free to use/modify/distribute, as long as you keep this note in your code
"""

# Configuration (you should review/change these !)
# -----------------------------------------------------------------------------

# Translation
# Available : 0 english, 1 french, 2 german,
#             3 spanish, 4 polish, 5 brazilian portuguese,
#             6 russian, 7 chinese
LANG = 6  # 6 = Ukrainian (slot 6 holds UA in our common_translations.py); all players see UA on broadcasts

# Can be enabled/disabled on your different game servers
# ie : [1]           = enabled only on server 1
#      [1, 2]      = enabled on servers 1 and 2
#      [2, 4, 5] = enabled on servers 2, 4 and 5
ENABLE_ON_SERVERS = [1]

# Should we display the stats to every player on matchend ?
# True / False
DISPLAY_ON_MATCHEND = True

# The command(s) the players have to enter in chat to display their stats
# You can have multiple commands
# ex : ["!top", "!topstats"]
# Note : the command(s) must start with a "!"
# Note : the command(s) aren't case sensitive (ie : '!top' or '!TOP' will work the same)
CHAT_COMMAND = ["!top"]

# Stats to display
# ----------------------------------------
# Define the stats to observe for each players and squads types
#   (see all available stats in example config below)
# Parameters :
#   (players & squads) "display"              : number of top players/squads to be listed
#   (players only)     "details" (True/False) : choose to display the (team/squad first letter) before the name of the player. ex : "(Axis/C) Playername"
#   (players only)     "vip_winners"          : give a VIP to this number of top players (up to 'display' number above)
STATS_TO_DISPLAY = {
    "players": {
        "armycommander": [
            {"score": "player_teamplay", "display": 2, "details": True, "vip_winners": 1},             # combat + support * SUPPORT_BONUS
        ],
        "infantry": [
            # {"score": "combat", "display": 3, "details": True, "vip_winners": 0},
            # {"score": "offense", "display": 3, "details": True, "vip_winners": 0},
            # {"score": "defense", "display": 3, "details": True, "vip_winners": 0},
            # {"score": "defense_bonus", "display": 3, "details": True, "vip_winners": 0},             # defense * DEFENSE_BONUS
            # {"score": "support", "display": 3, "details": True, "vip_winners": 0},
            # {"score": "support_bonus", "display": 3, "details": True, "vip_winners": 0},             # support * SUPPORT_BONUS
            # {"score": "kills", "display": 3, "details": True, "vip_winners": 0},
            # {"score": "deaths", "display": 3, "details": True, "vip_winners": 0},
            # {"score": "player_team_kills", "display": 3, "details": True, "vip_winners": 0},
            # {"score": "player_vehicle_kills", "display": 3, "details": True, "vip_winners": 0},
            # {"score": "player_vehicles_destroyed", "display": 3, "details": True, "vip_winners": 0},
            # Simplified per user request: one infantry category only — top-5 by raw kills,
            # VIP awarded to top-3. K/D and KPM categories removed (were dominated by
            # 1-kill 0-death farmers and not informative for casual players).
            {"score": "kills", "display": 5, "details": True, "vip_winners": 3},                       # top-5 by raw kills, VIP for top-3
        ],
        "armor": [
            # add any stat using the templates above
        ],
        "artillery": [
            # add any stat using the templates above
        ],
        "recon": [
            # add any stat using the templates above
        ],
    },
    "squads": {
        "armycommander": [
            # Prefer using the "armycommander" part in "players"
        ],
        "infantry": [
            # {"score": "combat", "display": 2},
            # {"score": "offense", "display": 2},
            # {"score": "defense", "display": 2},
            # {"score": "defense_bonus", "display": 2},
            # {"score": "support", "display": 2},
            # {"score": "support_bonus", "display": 2},
            # {"score": "kills", "display": 2},
            # {"score": "deaths", "display": 2},
            # {"score": "squad_team_kills", "display": 2},
            # {"score": "squad_vehicle_kills", "display": 2},
            # {"score": "squad_vehicles_destroyed", "display": 2},
            {"score": "squad_teamplay", "display": 2},
            {"score": "squad_offdef", "display": 2},
            # {"score": "squad_kd", "display": 2},
            # {"score": "squad_kpm", "display": 2},
        ],
        "armor": [
            {"score": "squad_teamplay", "display": 2},
            {"score": "squad_vehicles_destroyed", "display": 2},
        ],
        "artillery": [
            {"score": "squad_teamplay", "display": 2}
        ],
        "recon": [
            {"score": "squad_teamplay", "display": 2}
        ]
    }
}

# offdef defense bonus (offense + defense * bonus)
# ie : 1.5  = defense counts 1.5x more than offense (defense bonus)
#      1    = bonus disabled
#      0.67 = offense counts 1.5x more than defense (defense malus)
#      0.5  = offense counts 2x more than defense (defense malus)
#      0    = bonus disabled
# Any negative value will be ignored and defaulted to 1 (no bonus)
DEFENSE_BONUS = 1.5

# teamplay support bonus (combat + support * bonus)
SUPPORT_BONUS = 1.5


# VIP (only given to players at the end of a game)
# ----------------------------------------

# Don't give a VIP to an "entered at last second" commander
VIP_COMMANDER_MIN_PLAYTIME_MINS = 20
VIP_COMMANDER_MIN_SUPPORT_SCORE = 1000

# Give VIP if there is at least this number of players ingame
# 0 = disabled (VIP will always be given)
# Recommended : the same number as your seed limit
SEED_LIMIT = 40

# How many VIP hours should be given ?
# (If the player already has a VIP that ends AFTER this delay, VIP won't be given)
GRANTED_VIP_HOURS = 24

# VIP message : local time in expiration date/hour
# Find you local timezone : https://utctime.info/timezone/
# ie : "Europe/Berlin"
#      "Asia/Shanghai"
# default : "Etc/UTC"
LOCAL_TIMEZONE = "Europe/Kiev"


# Discord
# -------------------------------------

# Dedicated Discord's channel webhook : send matchend topstats (the DISPLAY_ON_MATCHEND parameter above must be set on True)
# (the script can run without any Discord output)
# Syntax : ["webhook url", enabled (True/False)]
DISCORD_CONFIG = [
    ("https://discord.com/api/webhooks/1503466934224556238/53H6vM6HFi-aiJ10vdvzpJPD5LVUuihEgT9J8DywlI6EcD7iiHHwebXH4dUZWL6vYdYw", True),  # Server 1 — enabled for matchend embed
]


# Miscellaneous (you don't need to change these)
# -------------------------------------

# Discord : embed author icon
DISCORD_EMBED_AUTHOR_ICON_URL = "https://cdn.discordapp.com/icons/316459644476456962/73a28de670af9e6569f231c9385398f3.webp?size=64"

# Bot name that will be displayed in CRCON "audit logs" and Discord embeds
BOT_NAME = "custom_tools_live_topstats"
