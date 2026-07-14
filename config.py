"""Game constants and data definitions."""

WIDTH, HEIGHT = 80, 40

TILE_EMPTY = "·"
TILE_STAR = "*"
TILE_PLANET = "o"
TILE_STATION = "☐"
TILE_BLACK_HOLE = "◉"
TILE_WORMHOLE = "⭕"
TILE_ASTEROIDS = "░"
TILE_SHIP = "@"
TILE_OTHER_SHIP = "▲"
TILE_CURSOR = "◈"
TILE_TRADER = "T"
TILE_PIRATE = "P"

DIR_LABELS = {
    (-1, -1): "NW", (0, -1): "N",  (1, -1): "NE",
    (-1,  0): "W",                  (1,  0): "E",
    (-1,  1): "SW", (0,  1): "S",  (1,  1): "SE",
}

RESOURCES = {
    "ore":        {"name": "Ore",           "cat": "raw",      "base_price": 5},
    "ice":        {"name": "Ice",           "cat": "raw",      "base_price": 3},
    "silicon":    {"name": "Silicon",       "cat": "raw",      "base_price": 8},
    "metal":      {"name": "Metal",         "cat": "refined",  "base_price": 20},
    "electronics":{"name": "Electronics",   "cat": "refined",  "base_price": 45},
    "fuel_cell":  {"name": "Fuel Cell",     "cat": "refined",  "base_price": 30},
    "shield_mod":   {"name": "Shield Mod",    "cat": "advanced", "base_price": 120},
    "relic":        {"name": "Alien Relic",   "cat": "special",  "base_price": 500},
    "repair_kit":   {"name": "Repair Kit",    "cat": "consumable", "base_price": 50},
    "shield_booster": {"name": "Shield Booster", "cat": "consumable", "base_price": 80},
}

RACES = {
    "human":       {"name": "Human"},
    "mutant":      {"name": "Mutant"},
    "xenos_bio":   {"name": "Xenos Bio"},
    "machine_cult":{"name": "Machine"},
    "voidborn":    {"name": "Voidborn"},
}

RELIGIONS = {
    "orthodox_church": {"name": "Orthodox Church"},
    "cult_of_the_void":{"name": "Cult of Void"},
    "machine_god":     {"name": "Machine God"},
    "old_faith":       {"name": "Old Faith"},
}

FACTIONS = {
    "imperium":           {"name": "Imperium"},
    "chaos_cult":         {"name": "Chaos Cult"},
    "xenos_horde":        {"name": "Xenos Horde"},
    "machine_collective": {"name": "Machine Collective"},
    "free_traders":       {"name": "Free Traders"},
    "void_covenant":      {"name": "Void Covenant"},
}

CONTRABAND = {
    "imperium":          ["relic"],
    "orthodox_church":   ["relic"],
    "chaos_cult":        ["shield_mod"],
    "free_traders":      [],
}

SHIP_MODULES = {
    "fusion_reactor":{"name":"Fusion Reactor","comp":"reactor","energy":0,"power":12,
                      "cost":800,"durability":100,"desc":"Generates 12 power"},
    "ion_drive":{"name":"Ion Drive","comp":"engine","energy":2,"speed":1,"evasion":10,
                 "cost":600,"durability":80,"desc":"Speed +1, evasion +10"},
    "laser_turret":{"name":"Laser Turret","comp":"weapon","energy":3,"damage":15,"accuracy":80,
                    "cost":500,"durability":60,"range":3,"desc":"Damage 15, accuracy 80"},
    "deflector_shield":{"name":"Deflector Shield","comp":"shield","energy":4,"shield_cap":30,
                        "shield_regen":2,"cost":700,"durability":90,"desc":"Shield +30, regen +2"},
    "long_range_scanner":{"name":"Long Range Scanner","comp":"sensor","energy":2,"sensor_range":5,
                          "cost":400,"durability":50,"desc":"Scan range +5"},
    "cargo_expander":{"name":"Cargo Expander","comp":"cargo","energy":0,"cargo_bonus":25,
                      "cost":300,"durability":40,"desc":"Cargo +25"},
    "life_support":{"name":"Life Support","comp":"life_support","energy":1,"crew_efficiency":10,
                    "cost":200,"durability":30,"desc":"Crew efficiency +10%"},
    "plasma_cannon":{"name":"Plasma Cannon","comp":"weapon","energy":5,"damage":30,"accuracy":60,
                     "cost":900,"durability":70,"range":4,"desc":"Damage 30, accuracy 60"},
    "armor_plating":{"name":"Armor Plating","comp":"shield","energy":0,"hull_bonus":20,
                     "cost":500,"durability":100,"desc":"+20 hull"},
    "warp_drive":{"name":"Warp Drive","comp":"engine","energy":3,"speed":2,"evasion":5,
                  "cost":1200,"durability":60,"desc":"Speed +2, evasion +5"},
}

COMPARTMENTS = ["reactor", "engine", "weapon", "shield", "sensor", "life_support", "cargo"]

# ---------------------------------------------------------------------------
# Ship hulls
# ---------------------------------------------------------------------------

SHIP_HULLS = {
    "shuttle": {
        "name": "Shuttle",
        "compartments": 3,
        "hull": 60,
        "cargo": 20,
        "speed": 1,
        "cost": 500,
        "desc": "Tiny scout — few compartments, minimal cargo.",
    },
    "corvette": {
        "name": "Corvette",
        "compartments": 5,
        "hull": 100,
        "cargo": 50,
        "speed": 1,
        "cost": 2000,
        "desc": "Light warship — balanced compartments and cargo.",
    },
    "frigate": {
        "name": "Frigate",
        "compartments": 7,
        "hull": 160,
        "cargo": 80,
        "speed": 1,
        "cost": 6000,
        "desc": "Heavy combat vessel — many modules, sturdy hull.",
    },
    "destroyer": {
        "name": "Destroyer",
        "compartments": 9,
        "hull": 240,
        "cargo": 120,
        "speed": 2,
        "cost": 15000,
        "desc": "Capital ship — maximum firepower and durability.",
    },
}

# ---------------------------------------------------------------------------
# Crafting recipes
# ---------------------------------------------------------------------------

RECIPES = {
    "repair_kit": {
        "name": "Repair Kit",
        "inputs": {"metal": 3, "electronics": 1},
        "craft_time": 3,
        "desc": "Restore 20 hull in combat",
    },
    "fuel_cell": {
        "name": "Fuel Cell",
        "inputs": {"ice": 2, "silicon": 1},
        "craft_time": 2,
        "desc": "Refined fuel (also sold at stations)",
    },
    "laser_turret": {
        "name": "Laser Turret (Mk1)",
        "inputs": {"metal": 5, "electronics": 3, "silicon": 2},
        "craft_time": 8,
        "desc": "Basic weapon module",
    },
    "deflector_shield": {
        "name": "Deflector Shield (Mk1)",
        "inputs": {"metal": 4, "electronics": 4, "shield_mod": 1},
        "craft_time": 10,
        "desc": "Basic shield module",
    },
    "ion_drive": {
        "name": "Ion Drive (Mk1)",
        "inputs": {"metal": 3, "electronics": 3, "silicon": 1},
        "craft_time": 7,
        "desc": "Basic engine module",
    },
}

# ---------------------------------------------------------------------------
# Permanent hull upgrades
# ---------------------------------------------------------------------------

UPGRADES = {
    "hull_reinforcement": {
        "name": "Hull Reinforcement",
        "cost": 2000,
        "inputs": {"metal": 10, "electronics": 2},
        "bonus": {"max_hull": 30},
        "desc": "+30 max hull",
    },
    "cargo_expansion": {
        "name": "Cargo Expansion",
        "cost": 1500,
        "inputs": {"metal": 5, "electronics": 3},
        "bonus": {"cargo_bonus": 20},
        "desc": "+20 cargo capacity",
    },
    "reactor_overclock": {
        "name": "Reactor Overclock",
        "cost": 3000,
        "inputs": {"electronics": 5, "shield_mod": 2},
        "bonus": {"power_bonus": 5},
        "desc": "+5 reactor power output",
    },
    "sensor_boost": {
        "name": "Sensor Boost",
        "cost": 1200,
        "inputs": {"electronics": 3, "silicon": 3},
        "bonus": {"sensor_range": 3},
        "desc": "+3 sensor range",
    },
    "engine_tuning": {
        "name": "Engine Tuning",
        "cost": 1800,
        "inputs": {"metal": 4, "electronics": 2, "silicon": 2},
        "bonus": {"speed": 1},
        "desc": "+1 base speed",
    },
}

# ---------------------------------------------------------------------------
# Crew
# ---------------------------------------------------------------------------

CREW_SPECIALTIES = {
    "Pilot":     {"name": "Pilot",     "posts": ["Pilot"],     "bonus": {"evasion": 5, "speed": 1}},
    "Engineer":  {"name": "Engineer",  "posts": ["Engineer"],  "bonus": {"regen": 2, "power_bonus": 10}},
    "Tactician": {"name": "Tactician", "posts": ["Tactical"],  "bonus": {"accuracy": 10, "damage": 5}},
    "Scientist": {"name": "Scientist", "posts": ["Scientist"], "bonus": {"sensor_range": 2, "scanner": 10}},
    "Medic":     {"name": "Medic",     "posts": ["Engineer"],  "bonus": {"hull_regen": 3}},
}

CREW_NAMES = [
    "Zara", "Kael", "Mira", "Rex", "Lyra", "Torg", "Nyx", "Fynn",
    "Echo", "Vex", "Juno", "Orin", "Sage", "Bolt", "Ivy", "Grim",
]

# ---------------------------------------------------------------------------
# Scan system
# ---------------------------------------------------------------------------

SCAN_ACTIVE_COST = 1       # energy per active scan
SCAN_DEEP_COST = 5         # energy per deep scan
SCAN_PASSIVE_RADIUS = 7    # default passive sensor range
SCAN_ACTIVE_RADIUS = 12    # active scan radius
SCAN_DEEP_RADIUS = 8       # deep scan radius

SCAN_SIGNAL_TYPES = {
    "distress":  {"weight": 30, "title": "Distress Signal",  "missions": ["rescue", "deliver"]},
    "anomaly":   {"weight": 20, "title": "Anomaly Detected", "missions": ["exploration", "salvage"]},
    "wreckage":  {"weight": 25, "title": "Wreckage Field",   "missions": ["salvage", "investigate"]},
    "pirate":    {"weight": 15, "title": "Pirate Outpost",   "missions": ["bounty"]},
    "artifact":  {"weight": 10, "title": "Artifact Reading", "missions": ["exploration", "investigate"]},
}

# ---------------------------------------------------------------------------
# Station types expanded
# ---------------------------------------------------------------------------

STATION_TYPES = {
    "trade_hub":   {"name": "Trade Hub"},
    "industrial":  {"name": "Industrial"},
    "research":    {"name": "Research"},
    "temple":      {"name": "Temple"},
    "shipyard":    {"name": "Shipyard",   "hulls": list(SHIP_HULLS)},
    "workshop":    {"name": "Workshop",   "recipes": list(RECIPES)},
    "tavern":      {"name": "Tavern",     "crew_slots": 4},
}
