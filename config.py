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
    "human": {
        "name": "Human",
        "desc": "Balanced crew, all-rounder",
        "bonus": {"accuracy": 5, "evasion": 3, "shield_regen": 1},
        "penalty": {},
    },
    "mutant": {
        "name": "Mutant",
        "desc": "Brute force — tough hull, strong weapons, clumsy",
        "bonus": {"max_hull": 25, "hull_bonus": 10, "damage": 8, "power_bonus": 3},
        "penalty": {"accuracy": -10, "evasion": -5},
    },
    "xenos_bio": {
        "name": "Xenos Bio",
        "desc": "Agile — fast, evasive, sharp sensors, fragile",
        "bonus": {"evasion": 8, "speed": 1, "sensor_range": 3},
        "penalty": {"max_hull": -15, "damage": -3},
    },
    "machine_cult": {
        "name": "Machine",
        "desc": "Precise — surgical accuracy, efficient reactors, sluggish",
        "bonus": {"accuracy": 10, "power_bonus": 5, "shield_cap": 10},
        "penalty": {"evasion": -5, "speed": -1},
    },
    "voidborn": {
        "name": "Voidborn",
        "desc": "Void-native — tough shields, natural regen, slow aiming",
        "bonus": {"shield_cap": 15, "shield_regen": 3, "evasion": 5},
        "penalty": {"speed": -1, "accuracy": -5},
    },
}  # доступные расы персонажей с бонусами к характеристикам

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
    # ── Реакторы ──
    "fusion_reactor":{"name":"Fusion Reactor","comp":"reactor","energy":0,"power":12,
                      "cost":800,"durability":100,"desc":"Generates 12 power"},
    # ── Двигатели ──
    "ion_drive":{"name":"Ion Drive","comp":"engine","energy":2,"speed":1,"evasion":10,
                 "cost":600,"durability":80,"desc":"Speed +1, evasion +10"},
    "warp_drive":{"name":"Warp Drive","comp":"engine","energy":3,"speed":2,"evasion":5,
                  "cost":1200,"durability":60,"desc":"Speed +2, evasion +5"},
    # ── Лазеры ──
    "laser_turret":{"name":"Laser Turret","comp":"weapon","weapon_class":"laser","damage_type":"energy",
                    "energy":3,"damage":15,"accuracy":80,
                    "cost":500,"durability":60,"range":3,"desc":"Laser — high accuracy, good vs shields"},
    # ── Плазма ──
    "plasma_cannon":{"name":"Plasma Cannon","comp":"weapon","weapon_class":"plasma","damage_type":"energy",
                     "energy":5,"damage":30,"accuracy":60,
                     "cost":900,"durability":70,"range":4,"desc":"Plasma — heavy damage, partial armor ignore"},
    # ── Кинетика ──
    "kinetic_cannon":{"name":"Kinetic Cannon","comp":"weapon","weapon_class":"kinetic","damage_type":"kinetic",
                      "energy":1,"damage":22,"accuracy":65,
                      "cost":700,"durability":80,"range":3,
                      "ammo_capacity":20,
                      "desc":"Kinetic — needs ammo, high hull damage"},
    # ── Ракеты ──
    "missile_launcher":{"name":"Missile Launcher","comp":"weapon","weapon_class":"missile","damage_type":"explosive",
                        "energy":2,"damage":40,"accuracy":90,
                        "cost":1200,"durability":50,"range":5,
                        "ammo_capacity":6,
                        "desc":"Missile — homing, very high damage, expensive ammo"},
    # ── Разрушитель ──
    "disruptor":{"name":"Disruptor","comp":"weapon","weapon_class":"disruptor","damage_type":"disruption",
                 "energy":4,"damage":10,"accuracy":75,
                 "cost":1100,"durability":60,"range":3,"desc":"Disruptor — bypasses shields, damages modules"},
    # ── Ионное ──
    "ion_cannon":{"name":"Ion Cannon","comp":"weapon","weapon_class":"ion","damage_type":"ion",
                  "energy":4,"damage":5,"accuracy":70,
                  "cost":1000,"durability":55,"range":3,
                  "ammo_capacity":12,
                  "desc":"Ion — drains enemy energy, disables modules"},
    # ── Щиты ──
    "deflector_shield":{"name":"Deflector Shield","comp":"shield","energy":4,"shield_cap":30,
                        "shield_regen":2,"cost":700,"durability":90,"desc":"Shield +30, regen +2"},
    "armor_plating":{"name":"Armor Plating","comp":"shield","energy":0,"hull_bonus":20,
                     "cost":500,"durability":100,"desc":"+20 hull"},
    # ── Сенсоры ──
    "long_range_scanner":{"name":"Long Range Scanner","comp":"sensor","energy":2,"sensor_range":5,
                          "cost":400,"durability":50,"desc":"Scan range +5"},
    # ── Груз ──
    "cargo_expander":{"name":"Cargo Expander","comp":"cargo","energy":0,"cargo_bonus":25,
                      "cost":300,"durability":40,"desc":"Cargo +25"},
    # ── Жизнеобеспечение ──
    "life_support":{"name":"Life Support","comp":"life_support","energy":1,"crew_efficiency":10,
                    "cost":200,"durability":30,"desc":"Crew efficiency +10%"},
}  # все модули корабля: отсек, потребление энергии, характеристики, стоимость

COMPARTMENTS = ["reactor", "engine", "weapon", "shield", "sensor", "life_support", "cargo"]
# список типов отсеков корабля

# ---------------------------------------------------------------------------
# Damage types
# ---------------------------------------------------------------------------

DAMAGE_TYPES = {
    "energy":     {"name": "Energy"},
    "kinetic":    {"name": "Kinetic"},
    "explosive":  {"name": "Explosive"},
    "disruption": {"name": "Disruption"},
    "ion":        {"name": "Ion"},
}  # типы урона для оружия и боеприпасов

# ---------------------------------------------------------------------------
# Weapon classes
# ---------------------------------------------------------------------------

WEAPON_CLASSES = {
    "laser":     {"name": "Laser",     "ammo_slots": 0, "can_change_ammo": False,
                  "desc": "High accuracy, energy-efficient, good vs shields"},
    "plasma":    {"name": "Plasma",    "ammo_slots": 0, "can_change_ammo": False,
                  "desc": "High damage, ignores partial armor, costly energy"},
    "kinetic":   {"name": "Kinetic",   "ammo_slots": 1, "can_change_ammo": True,
                  "desc": "Needs ammo, high hull damage, poor vs shields"},
    "missile":   {"name": "Missile",   "ammo_slots": 1, "can_change_ammo": True,
                  "desc": "Homing, extreme damage, expensive ammo, long cooldown"},
    "disruptor": {"name": "Disruptor", "ammo_slots": 0, "can_change_ammo": False,
                  "desc": "Bypasses shields, damages modules directly"},
    "ion":       {"name": "Ion",       "ammo_slots": 1, "can_change_ammo": True,
                  "desc": "Drains energy, disables modules, minimal hull damage"},
}  # классы оружия: тип, возможность смены боеприпасов

# ---------------------------------------------------------------------------
# Ammo types
# ---------------------------------------------------------------------------

AMMO_TYPES = {
    "slug": {
        "name": "Slug",
        "damage_type": "kinetic",
        "damage_mod": 0,
        "accuracy_mod": 0,
        "desc": "Cheap kinetic round",
    },
    "armor_piercing": {
        "name": "AP Round",
        "damage_type": "kinetic",
        "damage_mod": -3,
        "accuracy_mod": -5,
        "armor_pen": 10,
        "desc": "Ignores 10 armor",
    },
    "high_explosive": {
        "name": "HE Warhead",
        "damage_type": "explosive",
        "damage_mod": 10,
        "accuracy_mod": 0,
        "desc": "For missiles — massive boom",
    },
    "emp_charge": {
        "name": "EMP Charge",
        "damage_type": "ion",
        "damage_mod": -2,
        "accuracy_mod": 0,
        "energy_drain": 15,
        "desc": "Drains 15 enemy energy",
    },
    "plasma_cartridge": {
        "name": "Plasma Cell",
        "damage_type": "energy",
        "damage_mod": 5,
        "accuracy_mod": -5,
        "desc": "Enhanced plasma charge",
    },
}  # типы боеприпасов: модификаторы урона/точности, тип урона, особые свойства

# ---------------------------------------------------------------------------
# Default resistances
# ---------------------------------------------------------------------------

# Сопротивление щита (% поглощения) по типам урона
SHIELD_RESIST = {
    "energy":     50,   # щиты держат энергетический урон
    "kinetic":    20,   # кинетика прошивает щиты
    "explosive":  30,
    "disruption": 10,   # разрушитель почти игнорирует щиты
    "ion":        40,
}  # % урона, поглощаемый щитами (остаток идёт на щиты, не на корпус)

# Сопротивление брони/корпуса (% снижения) по типам урона
ARMOR_RESIST = {
    "energy":     30,   # броня хорошо держит энергетику
    "kinetic":    40,   # броня лучше всего держит кинетику
    "explosive":  20,   # взрывчатка эффективна против брони
    "disruption": 10,   # разрушитель игнорирует броню
    "ion":        50,   # ионка почти бесполезна против брони
}  # % урона, поглощаемый бронёй при попадании в корпус

# Модификатор урона по отсекам (type → множитель)
COMP_DAMAGE_MOD = {
    "energy":     {"shield": 1.3, "weapon": 1.0, "reactor": 1.0, "engine": 1.0, "sensor": 1.0},
    "kinetic":    {"shield": 0.6, "weapon": 1.2, "reactor": 1.0, "engine": 0.8, "sensor": 0.8},
    "explosive":  {"shield": 0.8, "weapon": 1.3, "reactor": 1.5, "engine": 1.2, "sensor": 1.2},
    "disruption": {"shield": 0.0, "weapon": 1.5, "reactor": 1.3, "engine": 1.3, "sensor": 1.8},
    "ion":        {"shield": 0.5, "weapon": 1.0, "reactor": 1.8, "engine": 1.5, "sensor": 0.5},
}  # множители урона по отсекам для каждого типа урона (× урон после резистов)

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
    "kinetic_cannon": {
        "name": "Kinetic Cannon (Mk1)",
        "inputs": {"metal": 6, "electronics": 2, "silicon": 2},
        "craft_time": 9,
        "desc": "Kinetic weapon — needs ammo",
    },
    "missile_launcher": {
        "name": "Missile Launcher (Mk1)",
        "inputs": {"metal": 8, "electronics": 5, "silicon": 3, "shield_mod": 1},
        "craft_time": 12,
        "desc": "Missile weapon — extreme damage",
    },
    "disruptor": {
        "name": "Disruptor (Mk1)",
        "inputs": {"metal": 5, "electronics": 6, "shield_mod": 2},
        "craft_time": 11,
        "desc": "Disruptor — bypasses shields",
    },
    "ion_cannon": {
        "name": "Ion Cannon (Mk1)",
        "inputs": {"metal": 4, "electronics": 4, "silicon": 4},
        "craft_time": 10,
        "desc": "Ion cannon — drains energy",
    },
    # ── Боеприпасы ──
    "slug": {
        "name": "Slug ×10",
        "inputs": {"metal": 1},
        "craft_time": 1,
        "yield": 10,
        "desc": "Ammo: cheap kinetic rounds",
    },
    "armor_piercing": {
        "name": "AP Round ×5",
        "inputs": {"metal": 2, "electronics": 1},
        "craft_time": 2,
        "yield": 5,
        "desc": "Ammo: armor-piercing kinetic rounds",
    },
    "high_explosive": {
        "name": "HE Warhead ×3",
        "inputs": {"metal": 3, "electronics": 2, "silicon": 1},
        "craft_time": 3,
        "yield": 3,
        "desc": "Ammo: high-explosive missile warhead",
    },
    "emp_charge": {
        "name": "EMP Charge ×3",
        "inputs": {"electronics": 3, "shield_mod": 1},
        "craft_time": 4,
        "yield": 3,
        "desc": "Ammo: electromagnetic pulse charge",
    },
    "plasma_cartridge": {
        "name": "Plasma Cell ×5",
        "inputs": {"metal": 1, "silicon": 2, "fuel_cell": 1},
        "craft_time": 2,
        "yield": 5,
        "desc": "Ammo: enhanced plasma cell",
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
