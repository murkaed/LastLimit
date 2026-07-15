# Модуль локализации: содержит словари переводов (RU/EN) и функции
# для переключения языка и получения переведённых строк.
"""Localisation module — lazy translation with RU/EN dictionaries."""

import re

# ---------------------------------------------------------------------------
# Language dictionaries
# ---------------------------------------------------------------------------

# Словарь русских переводов: все строки интерфейса, ресурсов, боёв и т.д.
RU = {
    # ── General UI ──
    "ui.bridge.title": "МОСТИК",
    "ui.bridge.commands": "КОМАНДЫ",
    "ui.engineering.title": "ИНЖЕНЕРИЯ",
    "ui.tactical.title": "ТАКТИКА",
    "ui.cargo.title": "ТРЮМ",
    "ui.crew.title": "ЭКИПАЖ",
    "ui.missions.title": "МИССИИ",
    "ui.scanner.title": "СКАНЕР",
    "ui.settings.title": "НАСТРОЙКИ",
    "ui.news.title": "НОВОСТИ",
    "ui.pause.title": "ПАУЗА",
    "ui.game_over": "ИГРА ОКОНЧЕНА",
    "ui.exit": "ВЫХОД",
    "ui.credits": "Кредиты",
    "ui.close": "Закрыть",
    "ui.back": "Назад",
    "ui.save": "Сохранить",
    "ui.load": "Загрузить",
    "ui.reset_defaults": "Сбросить настройки",
    "ui.lang": "Язык",
    "ui.lang_en": "English",
    "ui.lang_ru": "Русский",
    "ui.autosave": "Автосохранение",
    "ui.autosave_on": "Вкл",
    "ui.autosave_off": "Выкл",
    "ui.keys": "Клавиши",
    "ui.change_key": "Изменить",

    # ── Ship ──
    "ship.hull": "Корпус",
    "ship.shields": "Щиты",
    "ship.energy": "Энергия",
    "ship.fuel": "Топливо",
    "ship.speed": "Скорость",
    "ship.evasion": "Уклоенение",
    "ship.damage": "Урон",
    "ship.accuracy": "Точность",
    "ship.sensors": "Сенсоры",
    "ship.cargo": "Груз",
    "ship.modules": "Модули",
    "ship.weapons": "Оружие",
    "ship.targets": "Цели",
    "ship.power_gen": "Генерация",
    "ship.power_used": "Потребление",
    "ship.engine": "Двигатель",
    "ship.reactor": "Реактор",

    # ── Resources ──
    "res.metal": "Металл",
    "res.ice": "Лёд",
    "res.silicon": "Кремний",
    "res.electronics": "Электроника",
    "res.food": "Еда",
    "res.fuel": "Топливо",
    "res.ore": "Руда",
    "res.relic": "Артефакт",
    "res.shield_mod": "Мод.щита",
    "res.medicine": "Медикаменты",
    "res.repair_kit": "Ремкомплект",
    "res.fuel_cell": "Топлив.элемент",
    "res.shield_booster": "Усилитель щита",

    # ── Station types ──
    "station.trade_hub": "Торговая станция",
    "station.industrial": "Индустриальная",
    "station.research": "Исследовательская",
    "station.temple": "Храм",
    "station.shipyard": "Верфь",
    "station.workshop": "Мастерская",
    "station.tavern": "Таверна",

    # ── Factions ──
    "faction.free_traders": "Вольные торговцы",
    "faction.imperium": "Империум",
    "faction.chaos_cult": "Культ Хаоса",
    "faction.pirates": "Пираты",

    # ── Controls ──
    "ctrl.move_up": "Вверх",
    "ctrl.move_down": "Вниз",
    "ctrl.move_left": "Влево",
    "ctrl.move_right": "Вправо",
    "ctrl.interact": "Взаимодействие",
    "ctrl.inspect": "Осмотр",
    "ctrl.bridge": "Мостик",
    "ctrl.news": "Новости",
    "ctrl.help": "Помощь",
    "ctrl.console": "Консоль",
    "ctrl.land": "Высадка",
    "ctrl.wait": "Ожидание",
    "ctrl.action_menu": "Меню действий",

    # ── Battle ──
    "battle.title": "БОЙ",
    "battle.attack": "Атака",
    "battle.defend": "Защита",
    "battle.items": "Предметы",
    "battle.skills": "Навыки",
    "battle.escape": "Бегство",
    "battle.victory": "★ ПОБЕДА! ★",
    "battle.defeat": "☠ ПОРАЖЕНИЕ ☠",
    "battle.target": "Цель",
    "battle.weapon": "Оружие",
    "battle.fire_will": "Автоогонь",

    # ── Ground expedition ──
    "expedition.title": "ЭКСПЕДИЦИЯ",
    "expedition.land_prep": "ПОДГОТОВКА К ВЫСАДКЕ",
    "expedition.crew_select": "Выбор экипажа",
    "expedition.deploy": "Высадить",
    "expedition.evac": "Эвакуация",
    "expedition.status": "Статус",
    "expedition.log": "Лог",
    "expedition.controls": "Управление",

    # ── Scan ──
    "scan.result": "Результат сканирования",
    "scan.targets": "Цели в радиусе",
    "scan.active": "Активное",
    "scan.deep": "Глубокое",
    "scan.passive": "Пассивное",
    "scan.scanned": "Отсканировано",
    "scan.unknown": "Неизвестно",
    "scan.no_targets": "Нет целей в радиусе",
    "scan.cargo": "Груз",
    "scan.signals": "Сигналы",
    "scan.failed": "Сканирование не удалось",

    # ── Missions ──
    "mission.active": "Активные",
    "mission.available": "Доступные",
    "mission.accept": "Принять",
    "mission.abandon": "Отказаться",
    "mission.track": "Отслеживать",
    "mission.detail": "Детали",
    "mission.no_active": "Нет активных миссий",
    "mission.no_available": "Нет доступных миссий",
    "mission.log_full": "Журнал миссий полон (макс 5)",
    "mission.failed": "Миссия провалена",
    "mission.completed": "Миссия выполнена",
    "mission.reward": "Награда",
    "mission.deadline": "Срок",
    "mission.status": "Статус",

    # ── Log ──
    "log.radiation": "Радиация!",
    "log.refueled": "Заправлено топливо",
    "log.repaired": "Корпус отремонтирован",
    "log.no_credits": "Недостаточно кредитов",
    "log.docked": "Стыковка с {station}",
    "log.undocked": "Отстыковка",

    # ── Action Menu ──
    "action.ship": "Корабль",
    "action.interact": "Взаимодействие",
    "action.combat": "Бой",
    "action.system": "Система",
    "action.settings": "Настройки",
    "action.save": "Сохранить игру",
    "action.load": "Загрузить игру",
    "action.main_menu": "Главное меню",
    "action.quit": "Выйти",
    "action.bridge": "Мостик",
    "action.engineering": "Инженерия",
    "action.tactical": "Тактика",
    "action.cargo": "Трюм",
    "action.crew": "Экипаж",
    "action.missions": "Миссии",
    "action.scan": "Сканирование",
    "action.trade": "Торговля",
    "action.shipyard": "Верфь",
    "action.craft": "Крафт",
    "action.refuel": "Заправиться",
    "action.repair": "Починить",
    "action.land": "Высадиться",
    "action.talk": "Поговорить",
    "action.attack": "Атаковать",
    "action.flee": "Сбежать",
    "action.close": "Закрыть",

    # ── Misc ──
    "misc.yes": "Да",
    "misc.no": "Нет",
    "misc.on": "Вкл",
    "misc.off": "Выкл",
    "misc.all": "Все",
    "misc.raw": "Сырьё",
    "misc.refined": "Обраб.",
    "misc.advanced": "Прод.",
    "misc.special": "Особ.",
    "misc.modules": "Модули",
    "misc.press_any_key": "Нажмите любую клавишу",
    "misc.search": "Поиск",
    "misc.none": "Нет",
    "misc.empty": "Пусто",
    "misc.level": "Уровень",
    "misc.durability": "Прочность",
}

# Словарь английских переводов: строки интерфейса на английском языке.
EN = {
    # ── General UI ──
    "ui.bridge.title": "BRIDGE",
    "ui.bridge.commands": "COMMANDS",
    "ui.engineering.title": "ENGINEERING",
    "ui.tactical.title": "TACTICAL",
    "ui.cargo.title": "CARGO",
    "ui.crew.title": "CREW",
    "ui.missions.title": "MISSIONS",
    "ui.scanner.title": "SCANNER",
    "ui.settings.title": "SETTINGS",
    "ui.news.title": "NEWS",
    "ui.pause.title": "PAUSED",
    "ui.game_over": "GAME OVER",
    "ui.exit": "EXIT",
    "ui.credits": "Credits",
    "ui.close": "Close",
    "ui.back": "Back",
    "ui.save": "Save",
    "ui.load": "Load",
    "ui.reset_defaults": "Reset to Defaults",
    "ui.lang": "Language",
    "ui.lang_en": "English",
    "ui.lang_ru": "Русский",
    "ui.autosave": "Autosave",
    "ui.autosave_on": "On",
    "ui.autosave_off": "Off",
    "ui.keys": "Keys",
    "ui.change_key": "Change",

    # ── Ship ──
    "ship.hull": "Hull",
    "ship.shields": "Shields",
    "ship.energy": "Energy",
    "ship.fuel": "Fuel",
    "ship.speed": "Speed",
    "ship.evasion": "Evasion",
    "ship.damage": "Damage",
    "ship.accuracy": "Accuracy",
    "ship.sensors": "Sensors",
    "ship.cargo": "Cargo",
    "ship.modules": "Modules",
    "ship.weapons": "Weapons",
    "ship.targets": "Targets",
    "ship.power_gen": "Power Gen",
    "ship.power_used": "Power Used",
    "ship.engine": "Engine",
    "ship.reactor": "Reactor",

    # ── Resources ──
    "res.metal": "Metal",
    "res.ice": "Ice",
    "res.silicon": "Silicon",
    "res.electronics": "Electronics",
    "res.food": "Food",
    "res.fuel": "Fuel",
    "res.ore": "Ore",
    "res.relic": "Relic",
    "res.shield_mod": "Shield Mod",
    "res.medicine": "Medicine",
    "res.repair_kit": "Repair Kit",
    "res.fuel_cell": "Fuel Cell",
    "res.shield_booster": "Shield Booster",

    # ── Station types ──
    "station.trade_hub": "Trade Hub",
    "station.industrial": "Industrial",
    "station.research": "Research",
    "station.temple": "Temple",
    "station.shipyard": "Shipyard",
    "station.workshop": "Workshop",
    "station.tavern": "Tavern",

    # ── Factions ──
    "faction.free_traders": "Free Traders",
    "faction.imperium": "Imperium",
    "faction.chaos_cult": "Chaos Cult",
    "faction.pirates": "Pirates",

    # ── Controls ──
    "ctrl.move_up": "Move Up",
    "ctrl.move_down": "Move Down",
    "ctrl.move_left": "Move Left",
    "ctrl.move_right": "Move Right",
    "ctrl.interact": "Interact",
    "ctrl.inspect": "Inspect",
    "ctrl.bridge": "Bridge",
    "ctrl.news": "News",
    "ctrl.help": "Help",
    "ctrl.console": "Console",
    "ctrl.land": "Land",
    "ctrl.wait": "Wait",
    "ctrl.action_menu": "Action Menu",

    # ── Battle ──
    "battle.title": "BATTLE",
    "battle.attack": "Attack",
    "battle.defend": "Defend",
    "battle.items": "Items",
    "battle.skills": "Skills",
    "battle.escape": "Escape",
    "battle.victory": "★ VICTORY! ★",
    "battle.defeat": "☠ DEFEATED ☠",
    "battle.target": "Target",
    "battle.weapon": "Weapon",
    "battle.fire_will": "Fire at Will",

    # ── Ground expedition ──
    "expedition.title": "EXPEDITION",
    "expedition.land_prep": "LANDING PREP",
    "expedition.crew_select": "Crew Selection",
    "expedition.deploy": "Deploy",
    "expedition.evac": "Evacuation",
    "expedition.status": "Status",
    "expedition.log": "Log",
    "expedition.controls": "Controls",

    # ── Scan ──
    "scan.result": "Scan Result",
    "scan.targets": "Targets in Range",
    "scan.active": "Active",
    "scan.deep": "Deep",
    "scan.passive": "Passive",
    "scan.scanned": "Scanned",
    "scan.unknown": "Unknown",
    "scan.no_targets": "No targets in range",
    "scan.cargo": "Cargo",
    "scan.signals": "Signals",
    "scan.failed": "Scan failed",

    # ── Missions ──
    "mission.active": "Active",
    "mission.available": "Available",
    "mission.accept": "Accept",
    "mission.abandon": "Abandon",
    "mission.track": "Track",
    "mission.detail": "Details",
    "mission.no_active": "No active missions",
    "mission.no_available": "No missions available",
    "mission.log_full": "Mission log full (max 5)",
    "mission.failed": "Mission Failed",
    "mission.completed": "Mission Complete",
    "mission.reward": "Reward",
    "mission.deadline": "Deadline",
    "mission.status": "Status",

    # ── Log ──
    "log.radiation": "Radiation!",
    "log.refueled": "Refueled",
    "log.repaired": "Hull repaired",
    "log.no_credits": "Not enough credits",
    "log.docked": "Docked at {station}",
    "log.undocked": "Undocked",

    # ── Action Menu ──
    "action.ship": "Ship",
    "action.interact": "Interact",
    "action.combat": "Combat",
    "action.system": "System",
    "action.settings": "Settings",
    "action.save": "Save Game",
    "action.load": "Load Game",
    "action.main_menu": "Main Menu",
    "action.quit": "Quit",
    "action.bridge": "Bridge",
    "action.engineering": "Engineering",
    "action.tactical": "Tactical",
    "action.cargo": "Cargo",
    "action.crew": "Crew",
    "action.missions": "Missions",
    "action.scan": "Scan",
    "action.trade": "Trade",
    "action.shipyard": "Shipyard",
    "action.craft": "Craft",
    "action.refuel": "Refuel",
    "action.repair": "Repair",
    "action.land": "Land",
    "action.talk": "Talk",
    "action.attack": "Attack",
    "action.flee": "Flee",
    "action.close": "Close",

    # ── Misc ──
    "misc.yes": "Yes",
    "misc.no": "No",
    "misc.on": "On",
    "misc.off": "Off",
    "misc.all": "All",
    "misc.raw": "Raw",
    "misc.refined": "Refined",
    "misc.advanced": "Advanced",
    "misc.special": "Special",
    "misc.modules": "Modules",
    "misc.press_any_key": "Press any key",
    "misc.search": "Search",
    "misc.none": "None",
    "misc.empty": "Empty",
    "misc.level": "Level",
    "misc.durability": "Durability",
}

# ---------------------------------------------------------------------------
# Translation function
# ---------------------------------------------------------------------------

_current_lang = "ru"  # Текущий активный язык (по умолчанию русский)
_dicts = {"ru": RU, "en": EN}  # Сопоставление кода языка и словаря переводов


def set_lang(lang):
    """Установить текущий язык локализации.

    Параметры:
        lang (str): код языка — "ru" или "en".
    """
    global _current_lang
    if lang in _dicts:
        _current_lang = lang


def get_lang():
    """Вернуть код текущего активного языка.

    Возвращает:
        str: "ru" или "en".
    """
    return _current_lang


def t(key, **kwargs):
    """Перевести строку по ключу, с опциональной подстановкой значений.

    Параметры:
        key (str): ключ перевода (например, "ui.bridge.title").
        **kwargs: именованные аргументы для подстановки в строку
                  (например, station="Alpha").

    Возвращает:
        str: переведённая строка. Если ключ не найден — возвращается
             "❌{key}" как запасной вариант.
    """
    d = _dicts.get(_current_lang, RU)
    val = d.get(key)
    if val is None:
        # Fallback to EN keys
        val = EN.get(key, f"❌{key}")
    if kwargs:
        return val.format(**kwargs)
    return val


def t_lang(key, lang):
    """Перевести строку на указанный язык (для отображения в настройках).

    Параметры:
        key (str): ключ перевода.
        lang (str): код целевого языка ("ru" или "en").

    Возвращает:
        str: переведённая строка.
    """
    d = _dicts.get(lang, RU)
    val = d.get(key)
    if val is None:
        val = EN.get(key, f"❌{key}")
    return val
