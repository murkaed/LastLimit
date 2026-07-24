"""Energy- and crew-aware turn-based combat system."""
"""
Файл: battle.py
Назначение: пошаговая боевая система для космической игры LastLimit.

Как работает боевая система:
- Бой происходит между кораблём игрока и кораблём NPC (пират или торговец).
- Очерёдность хода определяется скоростью кораблей (бросок кубика d6 + модификаторы).
- В свой ход игрок может: атаковать выбранным оружием в отсек противника,
  защищаться (восстановление щитов), использовать предметы/навыки или попытаться сбежать.
- Урон рассчитывается с учётом генерации/потребления энергии корабля, точности,
  уклонения противника, брони отсеков и бонусов экипажа.
- При уничтожении отсека срабатывают штрафы COMP_EFFECTS (падение характеристик).
- Система поддерживает критические попадания, восстановление энергии каждый ход,
  использование расходников и специальных навыков.
- NPC управляется ИИ: выбирает цели по приоритетам, использует ремонтные наборы
  при низком уровне прочности и может убежать при критическом состоянии.
"""

import random
from textual.screen import Screen
from textual.widgets import Static

from config import RESOURCES, COMPARTMENTS, SHIELD_RESIST, ARMOR_RESIST, COMP_DAMAGE_MOD, AMMO_TYPES, WEAPON_CLASSES, DAMAGE_TYPES

# ---------------------------------------------------------------------------
# Расходники, доступные в бою (ремонт корпуса, топливо для энергии, усиление щита)
# ---------------------------------------------------------------------------

BATTLE_CONSUMABLES = {
    "repair_kit": {"name": "Repair Kit", "desc": "Restore 20 hull", "effect": {"hull": 20}},
    "fuel_cell": {"name": "Fuel Cell", "desc": "Restore 10 energy", "effect": {"energy": 10}},
    "shield_booster": {"name": "Shield Booster", "desc": "Restore 15 shields", "effect": {"shield": 15}},
}

# ---------------------------------------------------------------------------
# Особые навыки, требующие энергии (перегрузка щитов, точный выстрел, экстренный ремонт)
# ---------------------------------------------------------------------------

BATTLE_SKILLS = {
    "overload_shields": {"name": "Overload Shields", "desc": "Restore 30% shields (15e)", "energy_cost": 15},
    "precise_shot": {"name": "Precise Shot", "desc": "High-crit attack (10e)", "energy_cost": 10},
    "emergency_repair": {"name": "Emergency Repair", "desc": "Restore 30 hull (10e)", "energy_cost": 10},
}

# ── Штрафы к характеристикам при разрушении отсека ─────────────────────
# Каждый отсек при уничтожении снижает определённые параметры корабля.
COMP_EFFECTS = {
    "reactor":     {"power_bonus": -3},
    "engine":      {"evasion": -4, "speed": -1},
    "weapon":      {"damage": -4, "accuracy": -10},
    "shield":      {"shield_cap": -8, "shield_regen": -2},
    "sensor":      {"accuracy": -8},
    "life_support": {"evasion": -2},
    "cargo":       {},
}

# ── Приоритеты целей для разных типов NPC ──────────────────────────────
# Определяют, в каком порядке ИИ атакует отсеки игрока.
ENEMY_TARGET_PRIORITIES = {
    "pirate": ["shield", "weapon", "engine", "reactor", "sensor", "life_support", "cargo"],
    "trader": ["weapon", "engine", "shield", "reactor", "sensor", "life_support", "cargo"],
}


def _bar_s(current, maximum, width=10):
    """Создаёт текстовую полосу прогресса из символов █ и ░.

    Параметры:
        current: текущее значение
        maximum: максимальное значение
        width: ширина полосы в символах (по умолчанию 10)

    Возвращает:
        строку вида "█████░░░░░"
    """
    if maximum <= 0: return "░" * width
    filled = int(current / maximum * width)
    return "█" * filled + "░" * (width - filled)


def _build_enemy_compartments(is_pirate):
    """Создаёт структуру отсеков для вражеского корабля.

    Заполняет каждый отсек модулями в зависимости от типа NPC.
    Пираты получают более агрессивное оснащение, торговцы — гражданское.

    Параметры:
        is_pirate: True — пиратский корабль, False — торговец

    Возвращает:
        словарь отсеков с вложенными модулями и их характеристиками
    """
    comps = {c: {"modules": [], "power": 3} for c in COMPARTMENTS}
    if is_pirate:
        comps["reactor"]["modules"].append({"name":"Scavenged Reactor","dur":40,"max_dur":40,"active":True,"armor":5})
        comps["engine"]["modules"].append({"name":"Booster Drive","dur":30,"max_dur":30,"active":True,"armor":3,"evasion":5})
        comps["weapon"]["modules"].append({"name":"Pirate Laser","dur":25,"max_dur":25,"active":True,"armor":5,"damage":8,"accuracy":60,
                                            "weapon_class":"laser","damage_type":"energy"})
        comps["shield"]["modules"].append({"name":"Scrap Shield","dur":30,"max_dur":30,"active":True,"armor":8,"shield_cap":10,"shield_regen":1})
    else:
        comps["reactor"]["modules"].append({"name":"Civilian Reactor","dur":50,"max_dur":50,"active":True,"armor":5})
        comps["engine"]["modules"].append({"name":"Civilian Drive","dur":40,"max_dur":40,"active":True,"armor":5,"evasion":2})
        comps["weapon"]["modules"].append({"name":"Light Turret","dur":20,"max_dur":20,"active":True,"armor":5,"damage":5,"accuracy":50,
                                            "weapon_class":"laser","damage_type":"energy"})
        comps["shield"]["modules"].append({"name":"Basic Shield","dur":35,"max_dur":35,"active":True,"armor":5,"shield_cap":15,"shield_regen":2})
    # Общие для всех NPC отсеки
    comps["sensor"]["modules"].append({"name":"Scanner","dur":20,"max_dur":20,"active":True,"armor":3})
    comps["life_support"]["modules"].append({"name":"Life Support","dur":20,"max_dur":20,"active":True,"armor":3})
    comps["cargo"]["modules"].append({"name":"Cargo Bay","dur":20,"max_dur":20,"active":True,"armor":3})
    return comps


def _total_enemy_stat(comps, key):
    """Суммирует указанную характеристику по всем активным модулям врага.

    Параметры:
        comps: словарь отсеков врага
        key: имя характеристики (например, "damage", "evasion")

    Возвращает:
        суммарное значение характеристики по всем живым модулям
    """
    total = 0
    for c in COMPARTMENTS:
        for m in comps[c]["modules"]:
            if m.get("active") and m.get("dur", 0) > 0:
                total += m.get(key, 0)
    return total


def _compartment_status_str(comp, comp_data, width=10):
    """Формирует строку состояния отсека с полосой прочности.

    Если все модули отсека уничтожены — помечает отсек как [☠DESTROYED].

    Параметры:
        comp: название отсека
        comp_data: данные отсека (словарь с ключом "modules")
        width: ширина полосы прочности

    Возвращает:
        отформатированную строку состояния
    """
    alive = [m for m in comp_data["modules"] if m.get("active") and m.get("dur", 0) > 0]
    total_dur = sum(m.get("dur", 0) for m in alive)
    max_dur = sum(m.get("max_dur", 1) for m in comp_data["modules"] if m.get("active", True))
    if not alive or total_dur <= 0:
        return f"{comp:<9}[☠DESTROYED]"
    pct = int(total_dur / max(1, max_dur) * 100)
    bar = _bar_s(pct, 100, width)
    return f"{comp:<9}{bar}"


def _player_comp_status_str(comp_name, comp_data, width=10):
    """Формирует строку состояния отсека ИГРОКА.

    ShipModule хранит состояние в атрибутах .active, .durability, .max_durability.
    Если все модули отсека уничтожены — помечает отсек как [☠DESTROYED].

    Параметры:
        comp_name: название отсека
        comp_data: словарь отсека {"modules": [ShipModule, ...], ...}
        width: ширина полосы прочности

    Возвращает:
        отформатированную строку состояния
    """
    modules = comp_data.get("modules", [])
    alive = [m for m in modules if m.active and not m.is_broken()]
    total_dur = sum(m.durability for m in alive)
    max_dur = sum(m.max_durability for m in modules if not m.is_broken() or m.durability > 0)
    if not alive or total_dur <= 0:
        return f"{comp_name:<9}[☠DESTROYED]"
    pct = int(total_dur / max(1, max_dur) * 100)
    bar = _bar_s(pct, 100, width)
    return f"{comp_name:<9}{bar}"


# ═══════════════════════════════════════════════════════════════════════
# Damage calculation helpers
# ═══════════════════════════════════════════════════════════════════════

def _apply_shield_resist(damage, damage_type, shield_hp):
    """Применяет сопротивление щита к урону определённого типа.

    Щиты поглощают часть урона в зависимости от SHIELD_RESIST[damage_type].
    Остаток урона проходит к корпусу/модулям.

    Параметры:
        damage: исходный урон
        damage_type: тип урона (str)
        shield_hp: текущая прочность щита

    Возвращает:
        (damage_to_shield, damage_to_hull) — сколько урона ушло на щиты и на корпус
    """
    if shield_hp <= 0:
        return (0, damage)
    resist_pct = SHIELD_RESIST.get(damage_type, 30) / 100.0
    # Часть урона поглощается щитами
    to_shield = min(shield_hp, int(damage * (1 - resist_pct)))
    # Остаток проходит к корпусу
    remaining = max(0, damage - to_shield)
    return (to_shield, remaining)


def _apply_armor_resist(damage, damage_type, armor=0, armor_pen=0):
    """Применяет сопротивление брони к урону определённого типа.

    Args:
        damage: урон после щитов
        damage_type: тип урона
        armor: значение брони цели
        armor_pen: пробитие брони (снижает эффективную броню)

    Returns:
        урон после резиста брони
    """
    resist_pct = ARMOR_RESIST.get(damage_type, 20) / 100.0
    effective_armor = max(0, armor - armor_pen)
    # Броня снижает урон: resist_pct + armour_factor
    armor_factor = effective_armor / 100.0  # 5 armor = 5% reduction
    total_resist = min(0.8, resist_pct + armor_factor)
    return max(1, int(damage * (1 - total_resist)))


def _apply_comp_damage_mod(damage, damage_type, target_comp):
    """Применяет модификатор урона по отсеку для данного типа урона.

    Args:
        damage: урон после резистов
        damage_type: тип урона
        target_comp: название целевого отсека

    Returns:
        модифицированный урон
    """
    comp_mods = COMP_DAMAGE_MOD.get(damage_type, {})
    mod = comp_mods.get(target_comp, 1.0)
    return max(1, int(damage * mod))


def _get_weapon_damage_type(weapon, loaded_ammo_type=None):
    """Определяет фактический тип урона оружия с учётом загруженных боеприпасов.

    Args:
        weapon: объект оружия (ShipModule или dict)
        loaded_ammo_type: идентификатор загруженных боеприпасов (или None)

    Returns:
        тип урона (str)
    """
    if loaded_ammo_type and loaded_ammo_type in AMMO_TYPES:
        return AMMO_TYPES[loaded_ammo_type].get("damage_type",
                                                 weapon.get("damage_type", "energy")
                                                 if isinstance(weapon, dict)
                                                 else weapon.damage_type)
    if isinstance(weapon, dict):
        return weapon.get("damage_type", "energy")
    return weapon.damage_type


# ═══════════════════════════════════════════════════════════════════════

class BattleController:
    """Управляет логикой пошагового боя.

    Содержит состояние боя: характеристики игрока и врага, энергию, очерёдность хода,
    логирование событий. Реализует действия: атака, защита, использование предметов,
    применение навыков, побег. Обрабатывает ход врага (ИИ), проверки смерти,
    начисление награды при победе.
    """

    def __init__(self, player_ship, enemy_npc, app=None, selected_weapon_idx=0):
        """Инициализирует контроллер боя.

        Параметры:
            player_ship: объект корабля игрока
            enemy_npc: объект корабля противника
            app: ссылка на главное приложение (для обратного вызова, опционально)
            selected_weapon_idx: индекс выбранного оружия (по умолчанию 0)
        """
        self.player = player_ship  # корабль игрока
        self.enemy = enemy_npc  # корабль противника
        self.app = app  # главное приложение (может быть None для быстрого боя)
        self.is_pirate = type(enemy_npc).__name__ == "PirateShip"  # тип врага: пират или торговец
        self.enemy_comps = _build_enemy_compartments(self.is_pirate)  # отсеки вражеского корабля
        self.enemy_max_hull = enemy_npc.max_hull  # максимальная прочность корпуса врага
        self.enemy_shield_cap = getattr(enemy_npc, "shield_hp", 0) or _total_enemy_stat(self.enemy_comps, "shield_cap")  # ёмкость щита врага
        self.enemy_items = ["repair_kit"] if random.random() < 0.3 else []  # предметы врага (30% шанс получить ремкомплект)
        self.player_energy = 50  # текущая энергия игрока
        self.player_max_energy = 50  # максимальная энергия игрока
        self.selected_weapon_idx = selected_weapon_idx  # индекс выбранного оружия
        self.log = []  # лог событий боя
        self.over = False  # флаг окончания боя
        self.victory = False  # флаг победы игрока
        self.player_defending = False  # флаг: игрок в защите в текущий ход
        self._compute_turn_order()  # определить, кто ходит первым

    def _get_player_weapons(self):
        """Возвращает список активных (не сломанных) модулей оружия игрока."""
        return [m for m in self.player.compartments["weapon"]["modules"] if m.active and not m.is_broken()]

    # ── Состояние отсеков игрока ──────────────────────────────────────

    def _player_comp_destroyed(self, comp_name):
        """Проверяет, уничтожены ли ВСЕ модули в указанном отсеке игрока.

        Отсек считается уничтоженным, если ни один модуль в нём
        не активен и не повреждён (is_broken).

        Параметры:
            comp_name: название отсека (например, "reactor", "engine")

        Возвращает:
            True — все модули в отсеке мертвы, False — есть хотя бы один живой модуль
        """
        modules = self.player.compartments.get(comp_name, {}).get("modules", [])
        if not modules:
            return True  # пустой отсек = уничтожен
        return not any(m.active and not m.is_broken() for m in modules)

    def _player_comp_statuses(self):
        """Возвращает словарь {comp: destroyed} для всех отсеков игрока.

        Используется в отрисовке UI для визуальной индикации.
        """
        return {c: self._player_comp_destroyed(c) for c in COMPARTMENTS}

    def _player_evasion(self):
        """Возвращает показатель уклонения корабля игрока.

        Учитывает:
        - базовое уклонение от модулей, экипажа и расы
        - штраф COMP_EFFECTS за каждый уничтоженный отсек
        - engine уничтожен → уклонение = 0
        """
        ev = self.player.get_effective_stats().get("evasion", 0)
        for c in COMPARTMENTS:
            if self._player_comp_destroyed(c):
                ev += COMP_EFFECTS.get(c, {}).get("evasion", 0)
        if self._player_comp_destroyed("engine"):
            ev = 0
        return max(0, ev)

    def _player_accuracy_bonus(self):
        """Возвращает суммарный бонус/штраф к точности от уничтоженных отсеков."""
        bonus = 0
        for c in COMPARTMENTS:
            if self._player_comp_destroyed(c):
                bonus += COMP_EFFECTS.get(c, {}).get("accuracy", 0)
        return bonus

    def _player_has_working_engine(self):
        """Проверяет, работает ли хотя бы один модуль двигателя."""
        return not self._player_comp_destroyed("engine")

    def _player_can_skill(self, skill_id):
        """Проверяет, доступен ли навык с учётом состояния отсеков.

        precise_shot требует рабочий сенсор.
        """
        if skill_id == "precise_shot" and self._player_comp_destroyed("sensor"):
            return False
        return True

    def _crew_bonus(self, key):
        """Возвращает бонус экипажа по указанной характеристике.

        Параметры:
            key: имя характеристики (например, "speed", "accuracy", "damage")

        Возвращает:
            числовое значение бонуса (0, если метод _crew_bonus отсутствует)
        """
        return self.player._crew_bonus(key, 0) if hasattr(self.player, "_crew_bonus") else 0

    def _compute_turn_order(self):
        """Определяет очерёдность хода на основе скорости и броска кубика d6.

        Каждая сторона кидает d6 и добавляет модификатор скорости.
        У кого сумма больше — тот ходит первым.
        """
        p_spd = self.player.get_effective_stats().get("speed", 1) + self._crew_bonus("speed")
        e_spd = _total_enemy_stat(self.enemy_comps, "evasion") // 5 + 2
        p_roll = p_spd + random.randint(1, 6)
        e_roll = e_spd + random.randint(1, 6)
        if e_roll > p_roll:
            self.turn_order = "enemy"
            self.add_log(f"☠ {self.enemy.name} moves first!")
        else:
            self.turn_order = "player"
            self.add_log(f"▶ {self.player.name} moves first!")

    def add_log(self, msg):
        """Добавляет запись в лог боя. Лог обрезается до последних 30 записей.

        Параметры:
            msg: текст сообщения
        """
        self.log.append(msg)
        if len(self.log) > 30:
            self.log = self.log[-30:]

    def _enemy_stat_with_effects(self, key, default=0):
        """Вычисляет характеристику врага с учётом штрафов от разрушенных отсеков.

        Параметры:
            key: имя характеристики
            default: значение по умолчанию, если характеристика не найдена (по умолчанию 0)

        Возвращает:
            итоговое значение характеристики (не меньше 0)
        """
        base = _total_enemy_stat(self.enemy_comps, key) or default
        penalty = 0
        for c in COMPARTMENTS:
            alive = [m for m in self.enemy_comps[c]["modules"] if m.get("active") and m.get("dur", 0) > 0]
            if not alive:
                penalty += COMP_EFFECTS.get(c, {}).get(key, 0)
        return max(0, base + penalty)

    def _regen_player_energy(self):
        """Восстанавливает энергию игрока в конце каждого хода.

        Величина восстановления зависит от мощности реактора и бонуса экипажа.
        Минимум 5 единиц за ход.
        """
        reactor_power = self.player.total_power_generated()
        eng_bonus = self._crew_bonus("power_bonus") // 10
        regen = max(5, reactor_power // 2) + eng_bonus
        # Реактор уничтожен — реген энергии падает вдвое
        if self._player_comp_destroyed("reactor"):
            regen = max(1, regen // 2)
        old = self.player_energy
        self.player_energy = min(self.player_max_energy, self.player_energy + regen)
        if self.player_energy > old:
            self.add_log(f"⚡ Energy +{self.player_energy - old} (regen {regen}).")

    # ── Действия игрока ───────────────────────────────────────────────

    def do_attack(self, weapon_idx, target_comp=None):
        """Выполняет атаку выбранным оружием по указанному отсеку.

        Учитывает: энергопотребление оружия, эффективность энергосистемы,
        бонусы экипажа к точности и урону, уклонение врага, броню отсека,
        поглощение урона щитами, шанс критического попадания.

        Параметры:
            weapon_idx: индекс оружия в списке активного оружия
            target_comp: название целевого отсека (если None — выбирается случайно)
        """
        self.player_defending = False
        weapons = self._get_player_weapons()
        if not weapons:
            self.add_log("No weapons!")
            self._next_turn(); return
        weapon = weapons[weapon_idx] if 0 <= weapon_idx < len(weapons) else weapons[0]
        base_dmg = weapon.stats.get("damage", 10)
        accuracy = weapon.stats.get("accuracy", 70)
        weapon_name = weapon.name
        en_cost = weapon.energy_consumption
        # Определяем класс оружия и тип урона
        weapon_class = weapon.weapon_class or "laser"
        damage_type = _get_weapon_damage_type(weapon, weapon.loaded_ammo_type if hasattr(weapon, 'loaded_ammo_type') else None)
        # Проверка боеприпасов
        if weapon.needs_ammo() and not weapon.has_ammo():
            self.add_log(f"✗ {weapon_name} out of ammo! Reload required.")
            self._next_turn(); return
        # Проверка: хватает ли энергии на выстрел
        if self.player_energy < en_cost:
            self.add_log(f"⚡ Need {en_cost}e for {weapon_name} (have {self.player_energy}).")
            self._next_turn(); return
        self.player_energy -= en_cost
        # Расход боеприпаса
        ammo_used = False
        if weapon.needs_ammo():
            weapon.consume_ammo(1)
            ammo_used = True
            # Боеприпас может менять damage_type
            if weapon.loaded_ammo_type and weapon.loaded_ammo_type in AMMO_TYPES:
                ammo_info = AMMO_TYPES[weapon.loaded_ammo_type]
                base_dmg += ammo_info.get("damage_mod", 0)
                accuracy += ammo_info.get("accuracy_mod", 0)
                armor_pen = ammo_info.get("armor_pen", 0)
            else:
                armor_pen = 0
        else:
            armor_pen = 0
        # Модификатор урона от эффективности энергосистемы
        p_gen = self.player.total_power_generated()
        p_con = self.player.total_power_consumed()
        eff = min(1.5, p_gen / max(1, p_con))
        damage = max(1, int(base_dmg * eff))
        # Бонусы экипажа
        crew_acc = self._crew_bonus("accuracy")
        crew_dmg = self._crew_bonus("damage")
        accuracy += crew_acc
        damage += crew_dmg
        # Штрафы от разрушенных отсеков (COMP_EFFECTS, сенсор)
        accuracy += self._player_accuracy_bonus()
        # Проверка попадания
        e_evasion = self._enemy_stat_with_effects("evasion")
        hit_chance = max(5, min(95, accuracy - e_evasion))
        is_crit = random.random() < 0.10 + self._crew_bonus("accuracy") * 0.002
        if random.random() * 100 >= hit_chance:
            self.add_log(f"✗ {weapon_name} missed!")
            self._next_turn(); return
        # Критический удар — удвоение урона
        if is_crit:
            damage = int(damage * 2)
            self.add_log(f"★ CRITICAL!")
        # Выбор цели
        if target_comp is None or target_comp not in self.enemy_comps:
            target_comp = random.choice(COMPARTMENTS)
        comp = self.enemy_comps[target_comp]

        # ── Расчёт урона с учётом типов и резистов ──

        # Шаг 1: сопротивление щита
        shield_dmg, hull_dmg = _apply_shield_resist(damage, damage_type, self.enemy.shield_hp)
        if shield_dmg > 0:
            self.enemy.shield_hp = max(0, self.enemy.shield_hp - shield_dmg)
            self.add_log(f"🛡 Shield: -{shield_dmg} ({damage_type})")

        # Шаг 2: для disruption — урон идёт напрямую модулям, минуя броню
        if damage_type == "disruption":
            alive = [m for m in comp["modules"] if m.get("active") and m.get("dur", 0) > 0]
            if alive:
                hit = random.choice(alive)
                hit["dur"] = max(0, hit["dur"] - hull_dmg)
                if hit["dur"] <= 0:
                    hit["active"] = False
                    self.add_log(f"💥 Disruptor: {hit['name']} DESTROYED! (shield bypass)")
                else:
                    self.add_log(f"⚡ Disruptor: {hit['name']} -{hull_dmg} dur ({hit['dur']}/{hit['max_dur']})")
            elif hull_dmg > 0:
                self.enemy.hull = max(0, self.enemy.hull - hull_dmg)
                self.add_log(f"💢 Disruptor hits hull! -{hull_dmg}")
        else:
            # Шаг 2: сопротивление брони
            armor = sum(m.get("armor", 0) for m in comp["modules"])
            hull_dmg = _apply_armor_resist(hull_dmg, damage_type, armor, armor_pen)
            # Шаг 3: модификатор отсека
            hull_dmg = _apply_comp_damage_mod(hull_dmg, damage_type, target_comp)

            # Шаг 4: нанесение урона модулю
            if hull_dmg > 0:
                alive = [m for m in comp["modules"] if m.get("active") and m.get("dur", 0) > 0]
                if alive:
                    hit = random.choice(alive)
                    hit["dur"] = max(0, hit["dur"] - hull_dmg)
                    if hit["dur"] <= 0:
                        hit["active"] = False
                        self.add_log(f"💥 {hit['name']} DESTROYED!")
                    else:
                        self.add_log(f"🔧 {hit['name']} -{hull_dmg} dur ({hit['dur']}/{hit['max_dur']})")
                else:
                    self.enemy.hull = max(0, self.enemy.hull - hull_dmg)
                    self.add_log(f"💢 Hull hit! -{hull_dmg} ({damage_type})")

        # Спецэффект ионного урона
        if damage_type == "ion" and ammo_used and weapon.loaded_ammo_type == "emp_charge":
            drain = AMMO_TYPES["emp_charge"].get("energy_drain", 0)
            if drain > 0:
                self.add_log(f"⚡ Ion drain: -{drain} enemy energy!")

        # Лог выстрела
        dt_name = DAMAGE_TYPES.get(damage_type, {}).get("name", damage_type)
        self.add_log(f"→ {weapon_name} @ {target_comp} [{dt_name}] {'★' if is_crit else ''}")
        # Проверка: уничтожен ли враг
        if self.enemy.hull <= 0:
            self._on_enemy_defeated(); return
        self._next_turn()

    def do_defend(self):
        """Переводит корабль в режим защиты.

        Щиты восстанавливаются с удвоенной скоростью.
        Входящий урон в этом ходу будет уменьшен вдвое.
        """
        self.player_defending = True
        stats = self.player.get_effective_stats()
        regen = stats.get("shield_regen", 0) * 2 + self._crew_bonus("regen")
        cap = stats.get("shield_cap", 30)
        old = self.player.shield_hp
        self.player.shield_hp = min(cap, self.player.shield_hp + regen)
        self.add_log(f"🛡 Defensive! Shields {self.player.shield_hp}/{cap} (+{self.player.shield_hp-old}).")
        self._next_turn()

    def do_use_item(self, item_rid):
        """Использует расходный предмет из трюма игрока.

        Параметры:
            item_rid: идентификатор предмета (например, "repair_kit", "fuel_cell")
        """
        self.player_defending = False
        info = BATTLE_CONSUMABLES.get(item_rid)
        if not info: self.add_log(f"Unknown '{item_rid}'."); return
        if not self.player.cargo.has(item_rid): self.add_log(f"No {info['name']}!"); return
        self.player.cargo.remove(item_rid, 1)
        eff = info["effect"]
        if "hull" in eff:
            self.player.hull = min(self.player.max_hull, self.player.hull + eff["hull"])
            self.add_log(f"{info['name']}! Hull +{eff['hull']}.")
        elif "shield" in eff:
            cap = self.player.get_effective_stats().get("shield_cap", 30)
            old, s = self.player.shield_hp, self.player.shield_hp
            self.player.shield_hp = min(cap, self.player.shield_hp + eff["shield"])
            self.add_log(f"{info['name']}! Shield +{self.player.shield_hp - old}.")
        elif "energy" in eff:
            old = self.player_energy
            self.player_energy = min(self.player_max_energy, self.player_energy + eff["energy"])
            self.add_log(f"{info['name']}! Energy +{self.player_energy - old}.")
        self._next_turn()

    def do_skill(self, skill_id):
        """Применяет особый навык, расходующий энергию.

        Доступные навыки:
        - overload_shields: восстанавливает 30% щита
        - precise_shot: атака с высоким шансом крита
        - emergency_repair: восстанавливает 30 единиц корпуса

        Параметры:
            skill_id: идентификатор навыка
        """
        self.player_defending = False
        skill = BATTLE_SKILLS.get(skill_id)
        if not skill: return
        if self.player_energy < skill["energy_cost"]:
            self.add_log(f"Need {skill['energy_cost']}e, have {self.player_energy}."); return
        if not self._player_can_skill(skill_id):
            self.add_log(f"✗ {skill['name']} unavailable (sensor destroyed)."); return
        self.player_energy -= skill["energy_cost"]
        if skill_id == "overload_shields":
            cap = self.player.get_effective_stats().get("shield_cap", 30)
            restore = int(cap * 0.3)
            self.player.shield_hp = min(cap, self.player.shield_hp + restore)
            self.add_log(f"⚡ Overload Shields! +{restore} shield.")
        elif skill_id == "precise_shot":
            dmg = 15 + self.player.get_effective_stats().get("damage", 0) + self._crew_bonus("damage")
            is_crit = random.random() < 0.5
            if is_crit: dmg *= 2; self.add_log("★ PRECISE SHOT CRIT!")
            self.enemy.take_damage(dmg)
            self.add_log(f"🎯 Precise Shot! {self.enemy.hull} hull remains.")
            if not self.enemy.alive: self._on_enemy_defeated(); return
        elif skill_id == "emergency_repair":
            self.player.hull = min(self.player.max_hull, self.player.hull + 30)
            self.add_log("🔧 Emergency Repair! +30 hull.")
        self._next_turn()

    def do_escape(self):
        """Пытается сбежать из боя.

        Шанс побега зависит от разницы скоростей кораблей.
        База 40% с модификатором +5% за каждую единицу разницы скорости.
        Шанс ограничен диапазоном [10%, 90%].

        Если двигатель уничтожен — побег невозможен.
        """
        if not self._player_has_working_engine():
            self.add_log("✗ Engine destroyed! Can't escape.")
            self._next_turn(); return
        p_spd = self.player.get_effective_stats().get("speed", 1) + self._crew_bonus("speed")
        e_spd = _total_enemy_stat(self.enemy_comps, "evasion") // 5 + 2
        base = 40 + (p_spd - e_spd) * 5
        chance = max(10, min(90, base))
        if random.random() * 100 < chance:
            self.add_log("✓ Escaped!"); self.over = True; self.victory = False
        else:
            self.add_log("✗ Escape failed!"); self._next_turn()

    def do_reload(self):
        """Перезаряжает первое оружие, в котором закончились боеприпасы.

        Проверяет трюм на наличие боеприпасов, совместимых с классом оружия.
        Если оружие имеет loaded_ammo_type — грузит его; иначе — slug по умолчанию.
        Тратит ход.
        """
        self.player_defending = False
        weapons = self._get_player_weapons()
        # Ищем первое оружие без патронов
        reloaded = False
        for w in weapons:
            if w.needs_ammo() and not w.has_ammo():
                # Определяем, какой тип боеприпасов загружать
                target_ammo = w.loaded_ammo_type or "slug"
                loaded = w.load_ammo(target_ammo, w.ammo_capacity, self.player.cargo)
                if loaded > 0:
                    self.add_log(f"🔃 {w.name} reloaded: {w.current_ammo}/{w.ammo_capacity} ({target_ammo})")
                    reloaded = True
                else:
                    self.add_log(f"✗ No {target_ammo} in cargo for {w.name}!")
                    self._next_turn(); return
                break
        if not reloaded:
            # Проверяем, есть ли оружие с неполным магазином
            for w in weapons:
                if w.needs_ammo() and w.current_ammo < w.ammo_capacity:
                    target_ammo = w.loaded_ammo_type or "slug"
                    loaded = w.load_ammo(target_ammo, w.ammo_capacity - w.current_ammo, self.player.cargo)
                    if loaded > 0:
                        self.add_log(f"🔃 {w.name} topped up: {w.current_ammo}/{w.ammo_capacity} ({target_ammo})")
                        reloaded = True
                    break
        if not reloaded:
            self.add_log("✗ All weapons already loaded.")
        self._next_turn()

    def _tick_player_status_effects(self):
        """Применяет эффекты от разрушенных отсеков в начале каждого хода игрока.

        - Life support уничтожен: экипаж теряет кислород → -5 hull в ход
        - Cargo уничтожен: грузовой отсек разгерметизирован → теряется случайный предмет
        """
        if self.over: return
        if self._player_comp_destroyed("life_support"):
            dmg = 5
            self.player.hull = max(0, self.player.hull - dmg)
            self.add_log(f"☠ Life support failed! -{dmg} hull (crew suffocating).")
            if self.player.hull <= 0:
                self._on_player_defeated(); return
        if self._player_comp_destroyed("cargo"):
            items = [k for k, v in self.player.cargo.items.items() if v > 0]
            if items:
                lost = random.choice(items)
                qty = self.player.cargo.remove(lost, 1)
                self.add_log(f"💨 Cargo breached! Lost 1×{lost}.")

    def _next_turn(self):
        """Завершает ход игрока: тикают эффекты, реген энергии, ход врага."""
        if self.over: return
        self._tick_player_status_effects()
        if self.over: return
        self._regen_player_energy()
        self._do_enemy_turn()

    def _do_enemy_turn(self):
        """Реализует ход врага под управлением ИИ.

        Логика ИИ:
        - Восстанавливает щиты
        - При низком уровне корпуса (<30%) использует ремкомплект
        - При критическом уровне корпуса (<20%) с вероятностью 40% пытается сбежать
        - Атакует приоритетные отсеки игрока выбранным оружием
        - Если оружия нет — таранит корабль игрока
        """
        if self.over: return
        regen = _total_enemy_stat(self.enemy_comps, "shield_regen")
        self.enemy.shield_hp = min(self.enemy_shield_cap, self.enemy.shield_hp + regen)
        hull_pct = self.enemy.hull / max(1, self.enemy_max_hull)
        shield_pct = self.enemy.shield_hp / max(1, self.enemy_shield_cap)
        weapons = [m for m in self.enemy_comps["weapon"]["modules"] if m.get("active") and m.get("dur", 0) > 0]
        priorities = ENEMY_TARGET_PRIORITIES.get("pirate" if self.is_pirate else "trader", COMPARTMENTS)
        # Использование ремкомплекта при низком уровне корпуса
        if hull_pct < 0.3 and "repair_kit" in self.enemy_items:
            self.enemy_items.remove("repair_kit")
            self.enemy.hull = min(self.enemy_max_hull, self.enemy.hull + 20)
            self.add_log(f"☠ {self.enemy.name} uses Repair Kit!")
            self._check_player_death(); return
        # Попытка побега при критическом уровне корпуса
        elif hull_pct < 0.2 and random.random() < 0.4:
            if random.random() < 0.5:
                self.add_log(f"☠ {self.enemy.name} fled!"); self.over = True; self.victory = True; return
        # Атака оружием или таран
        if weapons:
            weapon = random.choice(weapons)
            base_dmg = weapon.get("damage", 8)
            acc = weapon.get("accuracy", 60)
            damage_type = weapon.get("damage_type", "energy")
            hit_chance = max(5, min(95, acc - self._player_evasion()))
            if random.random() * 100 < hit_chance:
                damage = base_dmg
                if self.player_defending: damage = max(1, damage // 2)  # защита уменьшает урон вдвое
                viable = [c for c in priorities if self.enemy_comps[c]["modules"]]
                tcomp = viable[0] if viable else random.choice(COMPARTMENTS)
                target = self.player.compartments[tcomp]

                # ── Расчёт урона с типом (аналогично атаке игрока) ──
                shield_dmg, hull_dmg = _apply_shield_resist(damage, damage_type, self.player.shield_hp)
                if shield_dmg > 0:
                    self.player.shield_hp = max(0, self.player.shield_hp - shield_dmg)

                if hull_dmg > 0:
                    if damage_type == "disruption":
                        alive_mods = [m for m in target["modules"] if m.active and not m.is_broken()]
                        if alive_mods:
                            hit = random.choice(alive_mods)
                            hit.durability = max(0, hit.durability - hull_dmg)
                            self.add_log(f"☠ {self.enemy.name} disrupts {hit.name}! (-{hull_dmg})")
                            if hit.is_broken(): hit.active = False; self.add_log(f"💥 {hit.name} BROKEN!")
                        else:
                            self.player.hull = max(0, self.player.hull - hull_dmg)
                            self.add_log(f"☠ {self.enemy.name} hull hit! -{hull_dmg}")
                    else:
                        alive_mods = [m for m in target["modules"] if m.active and not m.is_broken()]
                        if alive_mods:
                            hit = random.choice(alive_mods)
                            hit.durability = max(0, hit.durability - hull_dmg)
                            self.add_log(f"☠ {self.enemy.name} hits {hit.name}! (-{hull_dmg})")
                            if hit.is_broken(): hit.active = False; self.add_log(f"💥 {hit.name} BROKEN!")
                        else:
                            self.player.hull = max(0, self.player.hull - hull_dmg)
                            self.add_log(f"☠ {self.enemy.name} hits hull! (-{hull_dmg})")
                dt_name = DAMAGE_TYPES.get(damage_type, {}).get("name", damage_type)
                self.add_log(f"☠ {self.enemy.name} attacks {tcomp} [{dt_name}].")
            else:
                self.add_log(f"☠ {self.enemy.name} missed!")
        else:
            # Таран — если у врага нет оружия
            dmg = 10
            if self.player_defending: dmg = max(1, dmg // 2)
            self.player.take_damage(dmg)
            self.add_log(f"☠ {self.enemy.name} rams! -{dmg} hull.")
        self._check_player_death()

    def _check_player_death(self):
        """Проверяет, не уничтожен ли корабль игрока. Если да — вызывает поражение."""
        if self.player.hull <= 0: self._on_player_defeated()

    def _on_enemy_defeated(self):
        """Обрабатывает победу игрока: начисляет кредиты, трофеи, репутацию.

        Лут: случайное количество кредитов (50-150), случайный предмет (1-3 единицы).
        За победу над пиратом повышается репутация у свободных торговцев.
        """
        self.over = True; self.victory = True
        loot_cr = random.randint(50, 150)
        self.player.credits += loot_cr
        loot_item = random.choice(["metal", "electronics", "shield_mod", "relic"])
        amt = random.randint(1, 3)
        self.player.cargo.add(loot_item, amt)
        if self.is_pirate:
            self.player.reputation["free_traders"] = min(100, self.player.reputation.get("free_traders", 0) + 2)
        self.add_log(f"★ {self.enemy.name} destroyed! +{loot_cr}cr, {amt}×{loot_item}.")
        if self.app is not None and hasattr(self.app, "logger"):
            self.app.logger.combat(f"★ Victory! +{loot_cr}cr, {amt}×{loot_item}.")

    def _on_player_defeated(self):
        """Обрабатывает поражение игрока: завершает бой и записывает причину смерти."""
        self.over = True; self.victory = False
        self.add_log(f"☠ {self.player.name} destroyed...")
        if self.app is not None and hasattr(self.app, "death_cause"):
            self.app.death_cause = f"Destroyed by {self.enemy.name}."

    def debug_enemy_status(self):
        """Возвращает отладочную строку с состоянием всех отсеков врага.

        Для каждого отсека выводит список живых модулей с их прочностью
        или пометку DESTROYED, если отсек уничтожен.

        Возвращает:
            строку с информацией для отладки
        """
        lines = []
        for c in COMPARTMENTS:
            alive = [m for m in self.enemy_comps[c]["modules"] if m.get("active") and m.get("dur", 0) > 0]
            if alive:
                for m in alive:
                    lines.append(f"  {c}/{m['name']} dur={m['dur']}/{m['max_dur']}")
            else:
                lines.append(f"  {c}: DESTROYED")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# BattleScreen — экран боя (Textual)
# ═══════════════════════════════════════════════════════════════════════

class BattleScreen(Screen):
    """Текстовый экран боя на базе Textual.

    Отображает состояние боя: здоровье/щиты/энергию обеих сторон,
    схему отсеков врага, лог событий и меню действий.
    Управляется с клавиатуры через on_key.
    """

    def __init__(self, controller: BattleController, quick_battle=False):
        """Инициализирует экран боя.

        Параметры:
            controller: экземпляр BattleController, управляющий логикой боя
            quick_battle: True — режим быстрого боя (не переключает GAME_OVER при смерти)
        """
        super().__init__()
        self.ctrl = controller  # контроллер боя
        self.quick_battle = quick_battle  # режим быстрого боя (без GAME_OVER)
        self.menu_state = "main"  # текущее состояние меню (main / attack_weapon / attack_target / items / skills)
        self.menu_index = 0  # индекс в текущем меню
        self.selected_weapon_idx = controller.selected_weapon_idx  # индекс выбранного оружия

    def compose(self):
        """Создаёт виджеты экрана. Содержит один Static-виджет с id 'battle-content'."""
        yield Static(id="battle-content")

    def on_mount(self):
        """Вызывается при монтировании экрана. Обновляет отображение."""
        self._update_display()

    def _update_display(self):
        """Перерисовывает весь экран боя: статусы, отсеки врага, лог, меню.

        Формирует панель с информацией о кораблях (H/S/E), состоянием отсеков
        противника, последними записями лога и текущим меню действий.
        """
        c = self.ctrl
        lines = []
        W = 74

        lines.append(f"  ┌{'─' * (W-4)}┐")
        lines.append(f"  │{'':^{W-4}}│")

        ps = c.player; pe = c.enemy
        lines.append(f"  │  {ps.name[:18]:<18}  {'':>7}  {pe.name[:18]:<18}  │")

        p_hull_pct = int(ps.hull / max(1, ps.max_hull) * 100)
        e_hull_pct = int(pe.hull / max(1, c.enemy_max_hull) * 100)
        p_sh_pct = int(ps.shield_hp / max(1, ps.get_effective_stats().get("shield_cap",1)) * 100)
        e_sh_pct = int(pe.shield_hp / max(1, c.enemy_shield_cap) * 100)
        lines.append(f"  │  H:{_bar_s(p_hull_pct,100,12)} {ps.hull:>3}/{ps.max_hull:<3}  vs  H:{_bar_s(e_hull_pct,100,12)} {pe.hull:>3}/{c.enemy_max_hull:<3}  │")
        lines.append(f"  │  S:{_bar_s(p_sh_pct,100,12)} {ps.shield_hp:>3}/{ps.get_effective_stats().get('shield_cap',1):<3}  vs  S:{_bar_s(e_sh_pct,100,12)} {pe.shield_hp:>3}/{c.enemy_shield_cap:<3}  │")
        e_bar = _bar_s(c.player_energy, c.player_max_energy, 12)
        lines.append(f"  │  E:{e_bar} {c.player_energy:>2}/{c.player_max_energy:<2}{'':>32}  │")

        # ── Схема отсеков врага ──
        lines.append(f"  │  {'─' * (W-6)}  │")
        lines.append(f"  │  {'ENEMY COMPARTMENTS':^{W-6}}  │")
        lines.append(f"  │  {'─' * (W-6)}  │")
        for i, comp_name in enumerate(COMPARTMENTS):
            cd = c.enemy_comps[comp_name]
            status = _compartment_status_str(comp_name, cd, 10)
            marker = f"[{i+1}]" if not c.over else "   "
            lines.append(f"  │  {marker} {status:<30}{'':>35}  │")

        # ── Схема отсеков игрока ──
        lines.append(f"  │  {'─' * (W-6)}  │")
        lines.append(f"  │  {'YOUR COMPARTMENTS':^{W-6}}  │")
        lines.append(f"  │  {'─' * (W-6)}  │")
        for comp_name in COMPARTMENTS:
            pd = c.player.compartments[comp_name]
            status = _player_comp_status_str(comp_name, pd, 10)
            destroyed = c._player_comp_destroyed(comp_name)
            icon = " ☠" if destroyed else "  "
            lines.append(f"  │  {icon}{status:<30}{'':>35}  │")

        # ── Лог боя (последние 5 записей) ──
        lines.append(f"  │  {'─' * (W-6)}  │")
        for entry in c.log[-5:]:
            lines.append(f"  │  {entry:<{W-6}}  │")

        # ── Меню действий ──
        lines.append(f"  │  {'─' * (W-6)}  │")
        if c.over:
            msg = "★ VICTORY! ★" if c.victory else "☠ DEFEATED ☠"
            lines.append(f"  │  {msg:^{W-6}}  │")
            lines.append(f"  │  {'':^{W-4}}  │")
            lines.append(f"  │  {'Press any key...':^{W-6}}  │")
        else:
            menu = self._render_menu()
            for ml in menu:
                lines.append(f"  │  {ml:<{W-6}}  │")

        lines.append(f"  │{'':^{W-4}}│")
        lines.append(f"  └{'─' * (W-4)}┘")
        self.query_one("#battle-content").update("\n".join(lines))

    def _render_menu(self):
        """Формирует список строк текущего меню в зависимости от состояния.

        Возвращает:
            список строк для отображения в нижней части экрана боя
        """
        ms = self.menu_state; c = self.ctrl
        if ms == "main":
            return [
                "\\[1] Attack  \\[2] Defend  \\[3] Items  \\[4] Skills  \\[5] Escape  \\[6] Reload",
                f"    Energy: {c.player_energy}/{c.player_max_energy}",
            ]
        elif ms == "attack_weapon":
            r = []
            for i, w in enumerate(c._get_player_weapons()):
                r.append(f"  \\[{i+1}] {w.name}  ⚔{w.stats.get('damage',0)} 🎯{w.stats.get('accuracy',0)}% ⚡{w.energy_consumption}")
            r.append("  \\[0] Back"); return r
        elif ms == "attack_target":
            r = []
            for i, cn in enumerate(COMPARTMENTS):
                alive = [m for m in c.enemy_comps[cn]["modules"] if m.get("active") and m.get("dur", 0) > 0]
                r.append(f"    \\[{i+1}] {cn:<14} ({len(alive)} mod)" if alive else f"    \\[{i+1}] {cn:<14} (inert)")
            r.append("    \\[0] Random")
            return r
        elif ms == "items":
            found = False; r = []
            item_list = list(BATTLE_CONSUMABLES.items())
            for i, (rid, info) in enumerate(item_list):
                qty = c.player.cargo.has(rid)
                if qty > 0:
                    found = True
                    r.append(f"  [{i+1}] {info['name']:<16} x{qty}")
            if not found: r.append("  (no items)")
            r.append("  [0] Back"); return r
        elif ms == "skills":
            r = []
            skill_list = list(BATTLE_SKILLS.items())
            for i, (sid, sk) in enumerate(skill_list):
                ok = "✓" if c.player_energy >= sk["energy_cost"] else "✗"
                can = c._player_can_skill(sid)
                disabled = "" if can else " 🔒(no sensor)"
                r.append(f"  [{i+1}] {sk['name']:<20} {sk['energy_cost']}e {ok}{disabled}")
            r.append("  [0] Back"); return r
        return []

    def on_key(self, event):
        """Обрабатывает нажатия клавиш в зависимости от текущего состояния меню.

        Если бой окончен — закрывает экран и применяет результат.
        Иначе маршрутизирует нажатие в соответствующую ветку меню.

        Параметры:
            event: событие нажатия клавиши
        """
        c = self.ctrl
        if c.over:
            self._apply_outcome()
            event.stop()
            self.dismiss()
            return
        event.stop()
        k = event.key.lower()
        if self.menu_state == "main":
            if k == "1":
                if c._get_player_weapons(): self.menu_state = "attack_weapon"
                else: c.add_log("No weapons!")
            elif k == "2": c.do_defend()
            elif k == "3": self.menu_state = "items"
            elif k == "4": self.menu_state = "skills"
            elif k == "5": c.do_escape()
            elif k == "6": c.do_reload()
            self._update_display()
        elif self.menu_state == "attack_weapon":
            wk = c._get_player_weapons()
            if k == "0": self.menu_state = "main"
            elif k in "123456789":
                idx = int(k) - 1
                if idx < len(wk): self.selected_weapon_idx = idx; self.menu_state = "attack_target"
            self._update_display()
        elif self.menu_state == "attack_target":
            if k == "0": c.do_attack(self.selected_weapon_idx, None); self.menu_state = "main"
            elif k.isdigit() and k != "0":
                idx = int(k) - 1
                if idx < len(COMPARTMENTS): c.do_attack(self.selected_weapon_idx, COMPARTMENTS[idx]); self.menu_state = "main"
            self._update_display()
        elif self.menu_state == "items":
            item_list = list(BATTLE_CONSUMABLES.keys())
            if k == "0": self.menu_state = "main"
            elif k in "123456789":
                idx = int(k) - 1
                if idx < len(item_list):
                    rid = item_list[idx]
                    if c.player.cargo.has(rid):
                        c.do_use_item(rid)
                        self.menu_state = "main"
            self._update_display()
        elif self.menu_state == "skills":
            skill_list = list(BATTLE_SKILLS.keys())
            if k == "0": self.menu_state = "main"
            elif k in "123456789":
                idx = int(k) - 1
                if idx < len(skill_list):
                    c.do_skill(skill_list[idx])
                    self.menu_state = "main"
            self._update_display()

    def _apply_outcome(self):
        """Применяет результат боя к состоянию игры.

        В режиме быстрого боя (quick_battle=True) не переключает GameState.GAME_OVER
        и не модифицирует состояние приложения — экран просто закрывается.
        В обычном режиме при поражении устанавливает GameState.GAME_OVER
        и записывает причину смерти. Обновляет карту и информационную панель.
        """
        if self.quick_battle:
            return  # в быстром бою не трогаем состояние приложения
        c = self.ctrl; app = self.app
        if not c.victory and c.player.hull <= 0:
            if hasattr(app, "GameState"):
                from galaxy_map import GameState
                app.state = GameState.GAME_OVER
            app.death_cause = f"Destroyed by {c.enemy.name}."
        if hasattr(app, "update_map"): app.update_map()
        if hasattr(app, "update_info"): app.update_info()
