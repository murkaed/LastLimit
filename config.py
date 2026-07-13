"""Game constants and data definitions."""

WIDTH, HEIGHT = 80, 40

TILE_EMPTY = "·"
TILE_STAR = "*"
TILE_PLANET = "o"
TILE_STATION = "☐"
TILE_TEMPLE = "⛪"
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
    "shield_mod": {"name": "Shield Mod",    "cat": "advanced", "base_price": 120},
    "relic":      {"name": "Alien Relic",   "cat": "special",  "base_price": 500},
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
                    "cost":500,"durability":60,"desc":"Damage 15, accuracy 80"},
    "deflector_shield":{"name":"Deflector Shield","comp":"shield","energy":4,"shield_cap":30,
                        "shield_regen":2,"cost":700,"durability":90,"desc":"Shield +30, regen +2"},
    "long_range_scanner":{"name":"Long Range Scanner","comp":"sensor","energy":2,"sensor_range":5,
                          "cost":400,"durability":50,"desc":"Scan range +5"},
    "cargo_expander":{"name":"Cargo Expander","comp":"cargo","energy":0,"cargo_bonus":25,
                      "cost":300,"durability":40,"desc":"Cargo +25"},
    "life_support":{"name":"Life Support","comp":"life_support","energy":1,"crew_efficiency":10,
                    "cost":200,"durability":30,"desc":"Crew efficiency +10%"},
    "plasma_cannon":{"name":"Plasma Cannon","comp":"weapon","energy":5,"damage":30,"accuracy":60,
                     "cost":900,"durability":70,"desc":"Damage 30, accuracy 60"},
    "armor_plating":{"name":"Armor Plating","comp":"shield","energy":0,"hull_bonus":20,
                     "cost":500,"durability":100,"desc":"+20 hull"},
    "warp_drive":{"name":"Warp Drive","comp":"engine","energy":3,"speed":2,"evasion":5,
                  "cost":1200,"durability":60,"desc":"Speed +2, evasion +5"},
}

COMPARTMENTS = ["reactor", "engine", "weapon", "shield", "sensor", "life_support", "cargo"]
