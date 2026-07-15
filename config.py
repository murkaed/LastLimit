# ============================================================================
# config.py — Конфигурация и игровые константы
#
# Этот файл содержит все настройки, таблицы и константы игры LastLimit:
# размеры экрана, типы тайлов карты, ресурсы, расы, религии, фракции,
# модули кораблей, корпуса кораблей, рецепты крафта, улучшения, экипаж,
# параметры сканирования, наземные объекты, оружие и броня для экспедиций,
# настройки управления и типы станций. Файл не содержит игровой логики —
# только данные.
# ============================================================================

"""Game constants and data definitions."""

WIDTH, HEIGHT = 80, 40  # ширина и высота игрового поля в символах

TILE_EMPTY = "·"        # пустое пространство
TILE_STAR = "*"          # звезда
TILE_PLANET = "o"        # планета
TILE_STATION = "☐"       # космическая станция
TILE_BLACK_HOLE = "◉"    # чёрная дыра
TILE_WORMHOLE = "⭕"      # варп-врата / червоточина
TILE_ASTEROIDS = "░"     # астероидное поле
TILE_SHIP = "@"          # корабль игрока
TILE_OTHER_SHIP = "▲"    # корабль другого персонажа
TILE_CURSOR = "◈"        # курсор выбора
TILE_TRADER = "T"        # торговец
TILE_PIRATE = "P"        # пират

DIR_LABELS = {
    (-1, -1): "NW", (0, -1): "N",  (1, -1): "NE",
    (-1,  0): "W",                  (1,  0): "E",
    (-1,  1): "SW", (0,  1): "S",  (1,  1): "SE",
}  # соответствие между смещением (dx, dy) и текстовым названием направления

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
}  # все типы ресурсов: категория (сырьё / переработанное / продвинутое / особое / расходник) и базовая цена

RACES = {
    "human":       {"name": "Human"},
    "mutant":      {"name": "Mutant"},
    "xenos_bio":   {"name": "Xenos Bio"},
    "machine_cult":{"name": "Machine"},
    "voidborn":    {"name": "Voidborn"},
}  # доступные расы персонажей

RELIGIONS = {
    "orthodox_church": {"name": "Orthodox Church"},
    "cult_of_the_void":{"name": "Cult of Void"},
    "machine_god":     {"name": "Machine God"},
    "old_faith":       {"name": "Old Faith"},
}  # доступные религии

FACTIONS = {
    "imperium":           {"name": "Imperium"},
    "chaos_cult":         {"name": "Chaos Cult"},
    "xenos_horde":        {"name": "Xenos Horde"},
    "machine_collective": {"name": "Machine Collective"},
    "free_traders":       {"name": "Free Traders"},
    "void_covenant":      {"name": "Void Covenant"},
}  # игровые фракции

CONTRABAND = {
    "imperium":          ["relic"],
    "orthodox_church":   ["relic"],
    "chaos_cult":        ["shield_mod"],
    "free_traders":      [],
}  # список контрабандных ресурсов для каждой фракции

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
}  # все модули корабля: отсек, потребление энергии, характеристики, стоимость

COMPARTMENTS = ["reactor", "engine", "weapon", "shield", "sensor", "life_support", "cargo"]
# список типов отсеков корабля

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
}  # доступные корпуса кораблей с базовыми характеристиками

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
}  # рецепты крафта: входные ресурсы и время изготовления

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
}  # постоянные улучшения корпуса: цена, материалы, бонус

# ---------------------------------------------------------------------------
# Crew
# ---------------------------------------------------------------------------

CREW_SPECIALTIES = {
    "Pilot":     {"name": "Pilot",     "posts": ["Pilot"],     "bonus": {"evasion": 5, "speed": 1}},
    "Engineer":  {"name": "Engineer",  "posts": ["Engineer"],  "bonus": {"regen": 2, "power_bonus": 10}},
    "Tactician": {"name": "Tactician", "posts": ["Tactical"],  "bonus": {"accuracy": 10, "damage": 5}},
    "Scientist": {"name": "Scientist", "posts": ["Scientist"], "bonus": {"sensor_range": 2, "scanner": 10}},
    "Medic":     {"name": "Medic",     "posts": ["Engineer"],  "bonus": {"hull_regen": 3}},
}  # специальности членов экипажа и их бонусы

CREW_NAMES = [
    "Zara", "Kael", "Mira", "Rex", "Lyra", "Torg", "Nyx", "Fynn",
    "Echo", "Vex", "Juno", "Orin", "Sage", "Bolt", "Ivy", "Grim",
]  # пул имён для генерации членов экипажа

# ---------------------------------------------------------------------------
# Scan system
# ---------------------------------------------------------------------------

SCAN_ACTIVE_COST = 1       # энергия за активное сканирование
SCAN_DEEP_COST = 5         # энергия за глубокое сканирование
SCAN_PASSIVE_RADIUS = 7    # радиус пассивного обзора (по умолчанию)
SCAN_ACTIVE_RADIUS = 12    # радиус активного сканирования
SCAN_DEEP_RADIUS = 8       # радиус глубокого сканирования

SCAN_SIGNAL_TYPES = {
    "distress":  {"weight": 30, "title": "Distress Signal",  "missions": ["rescue", "deliver"]},
    "anomaly":   {"weight": 20, "title": "Anomaly Detected", "missions": ["exploration", "salvage"]},
    "wreckage":  {"weight": 25, "title": "Wreckage Field",   "missions": ["salvage", "investigate"]},
    "pirate":    {"weight": 15, "title": "Pirate Outpost",   "missions": ["bounty"]},
    "artifact":  {"weight": 10, "title": "Artifact Reading", "missions": ["exploration", "investigate"]},
}  # типы сигналов при сканировании: вес появления, название и подходящие миссии

# ---------------------------------------------------------------------------
# Expedition / ground tiles
# ---------------------------------------------------------------------------

GROUND_TILES = {
    "wall":       {"ch": "#", "passable": False, "name": "Wall", "destructible": True, "hp": 20},
    "floor":      {"ch": ".", "passable": True,  "name": "Floor"},
    "door_closed": {"ch": "+", "passable": False, "name": "Door", "interact": "open", "hp": 10},
    "door_open":  {"ch": "-", "passable": True,  "name": "Open Door"},
    "lava":       {"ch": "~", "passable": True,  "name": "Lava", "hazard": 5},
    "spikes":     {"ch": "^", "passable": True,  "name": "Spikes", "hazard": 3},
    "crate":      {"ch": "$", "passable": False, "name": "Crate", "interact": "loot"},
    "terminal":   {"ch": "!", "passable": False, "name": "Terminal", "interact": "use"},
    "exit":       {"ch": ">", "passable": True,  "name": "Evac Point"},
    "enemy":      {"ch": "E", "passable": False, "name": "Enemy"},
    "player":     {"ch": "@", "passable": False, "name": "Player"},
    "void":       {"ch": " ", "passable": False, "name": "Void"},
}  # типы тайлов наземных экспедиций: символ, проходимость, свойства

GROUND_ENEMIES = {
    "bandit":  {"name": "Bandit",  "hp": 20, "max_hp": 20, "dmg": 5,  "accuracy": 50, "evasion": 5,  "ap": 4, "ch": "E"},
    "drone":   {"name": "Drone",   "hp": 12, "max_hp": 12, "dmg": 3,  "accuracy": 60, "evasion": 10, "ap": 5, "ch": "E"},
    "mutant":  {"name": "Mutant",  "hp": 35, "max_hp": 35, "dmg": 8,  "accuracy": 40, "evasion": 3,  "ap": 4, "ch": "E"},
    "turret":  {"name": "Turret",  "hp": 25, "max_hp": 25, "dmg": 6,  "accuracy": 70, "evasion": 0,  "ap": 3, "ch": "E"},
}  # типы врагов в наземных экспедициях

GROUND_WEAPONS = {
    "pistol":   {"name": "Pistol",  "dmg": 4,  "accuracy": 75, "ap_cost": 2, "range": 4},
    "rifle":    {"name": "Rifle",   "dmg": 7,  "accuracy": 65, "ap_cost": 3, "range": 6},
    "shotgun":  {"name": "Shotgun", "dmg": 10, "accuracy": 50, "ap_cost": 3, "range": 3},
    "knife":    {"name": "Knife",   "dmg": 3,  "accuracy": 85, "ap_cost": 1, "range": 1},
}  # наземное оружие для экспедиций

GROUND_ARMOR = {
    "none":     {"name": "None",   "defense": 0},
    "vest":     {"name": "Vest",   "defense": 3},
    "combat":   {"name": "Combat", "defense": 5},
}  # наземная броня для экспедиций

EXPEDITION_FOV_RADIUS = 6  # радиус обзора (FOV) в наземных экспедициях

# ---------------------------------------------------------------------------
# Settings — defaults
# ---------------------------------------------------------------------------

SETTINGS_FILE = "settings.json"  # путь к файлу с сохранёнными настройками

DEFAULT_SETTINGS = {
    "lang": "ru",
    "autosave": True,
    "keys": {
        "move_up": "up",
        "move_down": "down",
        "move_left": "left",
        "move_right": "right",
        "interact": "e",
        "inspect": "i",
        "bridge": "f1",
        "news": "n",
        "help": "h",
        "console": "`",
        "land": "l",
        "wait": "space",
        "action_menu": "e",
    },
}  # настройки по умолчанию: язык, автосохранение, раскладка клавиш

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
}  # типы станций и их особенности


# ---------------------------------------------------------------------------
# Settings load/save
# ---------------------------------------------------------------------------

def load_settings():
    """
    Загружает настройки из JSON-файла.

    Если файл не существует или повреждён, возвращает настройки по умолчанию.
    Отсутствующие ключи заполняются значениями по умолчанию (слияние словарей).

    Returns:
        dict: Словарь с настройками игры.
    """
    import json, os
    if not os.path.exists(SETTINGS_FILE):
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge with defaults (fill missing keys)
        result = dict(DEFAULT_SETTINGS)
        result.update(data)
        return result
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    """
    Сохраняет настройки в JSON-файл.

    Args:
        settings (dict): Словарь с настройками для сохранения.
    """
    import json
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except OSError:
        pass
