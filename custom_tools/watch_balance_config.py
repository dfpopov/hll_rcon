"""
watch_balance_config.py

A plugin for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool)
that filters (kick) players based upon their language.

Source : https://github.com/ElGuillermo

Feel free to use/modify/distribute, as long as you keep this note in your code
"""

# Per role stats
# "key": {"role1", "role2", ...}
# Each key and role MUST be a key in the TRANSL list in common_translations.py
# for each key/value, two lines will be generated :
# ex :
# for 'armycommander": {"commander"}'
#       Army commander - level (avg) : 97.50
#       88 45% [--------------------|<<----------------------] 107 55%
# You can specify multiple roles as values to group soldiers (see below)
CATEGORIES = {
    # commanders
    "armycommander": {"armycommander"},

    # infantry
    "officer": {"officer"},
    "infantry": {"antitank", "automaticrifleman", "assault", "heavymachinegunner", "support", "rifleman", "engineer", "medic"},

    # armor
    "tankcommander": {"tankcommander"},
    "armor": {"crewman"},

    # artillery
    "artilleryobserver": {"artilleryobserver"},
    "artillery": {"gunner", "operator"},

    # recon
    "spotter": {"spotter"},
    "recon": {"sniper"}
}

# Discord embeds strings translations
# Available : 0 for english, 1 for french, 2 for german,
#             3 for spanish, 4 for polish, 5 for brazilian portuguese,
#             6 for russian, 7 for chinese
LANG = 6  # 6 = Ukrainian (slot 6 holds UA in our common_translations.py)

# Dedicated Discord's channel webhook
# ServerNumber, Webhook, Enabled
SERVER_CONFIG = [
    ["https://discord.com/api/webhooks/1503407951355056308/rY1bezSI79krp4PYdbGkPf9yPz_wlA3cTuYzMOuYcddUEL0sXvCqxfAu7BS0rmzFX-pW", True],  # Server 1 — enabled
]


# Miscellaneous (you don't have to change these)
# ----------------------------------------------

# The interval between watch turns (in seconds)
# Recommended : as the stats must be gathered for all the players,
#               requiring some amount of data from the game server,
#               you may encounter slowdowns if done too frequently.
# Default : 60
WATCH_INTERVAL_SECS = 180  # 3 minutes — embed self-refreshes on each tick

# Bot name that will be displayed in CRCON "audit logs" and Discord embeds
BOT_NAME = "custom_tools_watch_balance"
