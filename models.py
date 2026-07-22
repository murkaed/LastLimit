"""
Файл моделей данных игры LastLimit.

Содержит классы для представления игровых сущностей:
  - CargoHold      — грузовой отсек (учёт ресурсов)
  - ShipModule     — модуль корабля (двигатель, щит, оружие и т.д.)
  - CrewMember     — член экипажа со специальностью и боевыми характеристиками
  - PlayerShip     — корабль игрока (корпус, модули, экипаж, миссии, крафт)
  - Station        — станция (торговля, миссии, модули, верфи)
  - Galaxy         — игровая галактика (карта, NPC, события, дипломатия)
  - NPCShip        — базовый NPC-корабль
  - PirateShip     — пиратский корабль (наследник NPCShip)
  - TraderShip     — торговый корабль (наследник NPCShip)
  - NewsEntry      — запись новостной ленты
  - Mission        — миссия (доставка, награда и т.д.)
  - ScanResult     — результат сканирования цели
  - GameEvent      — игровое событие
"""

import random
from config import (
    WIDTH, HEIGHT, RESOURCES, FACTIONS, RACES, SHIP_MODULES,
    COMPARTMENTS, CONTRABAND, TILE_EMPTY, TILE_STAR, TILE_BLACK_HOLE,
    TILE_ASTEROIDS, TILE_PLANET, TILE_STATION, TILE_WORMHOLE,
    SHIP_HULLS, UPGRADES, RECIPES, CREW_SPECIALTIES, CREW_NAMES,
    STATION_TYPES, SCAN_SIGNAL_TYPES,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

MODULE_STAT_KEYS = {"power","speed","evasion","damage","accuracy",
                    "shield_cap","shield_regen","sensor_range",
                    "cargo_bonus","crew_efficiency","hull_bonus","range"}

STARTER_MODULE_MAP = {
    "reactor": "fusion_reactor",
    "engine": "ion_drive",
    "shield": "deflector_shield",
    "sensor": "long_range_scanner",
    "weapon": "laser_turret",
}

# ---------------------------------------------------------------------------
# Scan result
# ---------------------------------------------------------------------------

class ScanResult:
    """Результат сканирования цели (корабля, станции и т.д.).

    Содержит флаг успеха, уровень сканирования и словарь с информацией о цели.
    """

    def __init__(self, success, level="passive", info=None, scanned_obj=None):
        """
        Args:
            success: True, если сканирование прошло успешно.
            level: уровень сканирования — "passive", "active" или "deep".
            info: словарь с данными о цели (тип, прочность, груз и т.д.).
            scanned_obj: ссылка на отсканированный объект (корабль, станцию).
        """
        self.success = success  # успешно ли сканирование
        self.level = level  # уровень сканирования: passive, active, deep
        self.info = info or {}  # словарь с информацией о цели
        self.scanned_obj = scanned_obj  # ссылка на отсканированный объект

    def summary(self):
        """Возвращает однострочное текстовое описание результата сканирования."""
        if not self.success:
            return "Scan failed."
        s = self.info
        parts = [f"Scan: {s.get('type', 'unknown')}"]
        if "hull" in s:
            parts.append(f"H:{s['hull']}/{s.get('max_hull', '?')}")
        if "shield" in s:
            parts.append(f"S:{s['shield']}")
        if "cargo" in s:
            parts.append(f"Cargo:{s['cargo']}")
        if "weapons" in s:
            parts.append(f"Weapons:{s['weapons']}")
        if "signals" in s:
            parts.append(f"Signals:{s['signals']}")
        return " | ".join(parts)

CREW_STAT_MAP = {
    "evasion": "evasion", "speed": "speed", "accuracy": "accuracy",
    "damage": "damage", "sensor_range": "sensor_range",
    "regen": "shield_regen",
}

UPGRADE_STAT_MAP = {
    "cargo_bonus": "cargo_bonus",
    "sensor_range": "sensor_range",
    "speed": "speed",
}

# ---------------------------------------------------------------------------
# Cargo
# ---------------------------------------------------------------------------

class CargoHold:
    """Грузовой отсек корабля.

    Хранит ресурсы в виде словаря {идентификатор: количество}.
    Предоставляет методы для добавления, удаления и проверки наличия ресурсов.
    """

    def __init__(self, capacity=50):
        """
        Args:
            capacity: максимальная вместимость отсека (в единицах ресурсов).
        """
        self.capacity = capacity  # вместимость трюма
        self.items: dict[str, int] = {}  # словарь: идентификатор ресурса -> количество

    def used(self):
        """Возвращает суммарное количество занятого места в трюме."""
        return sum(self.items.values())

    def free(self):
        """Возвращает количество свободного места в трюме."""
        return max(0, self.capacity - self.used())

    def add(self, res_id: str, amount: int) -> bool:
        """Добавляет ресурс в трюм.

        Args:
            res_id: идентификатор ресурса.
            amount: количество.

        Returns:
            True, если ресурс добавлен; False, если не хватает места.
        """
        if self.free() < amount:
            return False
        self.items[res_id] = self.items.get(res_id, 0) + amount
        return True

    def remove(self, res_id: str, amount: int) -> bool:
        """Удаляет ресурс из трюма.

        Args:
            res_id: идентификатор ресурса.
            amount: количество.

        Returns:
            True, если ресурс удалён; False, если его недостаточно.
        """
        if self.items.get(res_id, 0) < amount:
            return False
        self.items[res_id] -= amount
        if self.items[res_id] <= 0:
            del self.items[res_id]
        return True

    def has(self, res_id: str) -> int:
        """Возвращает количество ресурса с указанным идентификатором в трюме.

        Args:
            res_id: идентификатор ресурса.

        Returns:
            Количество единиц ресурса (0, если отсутствует).
        """
        return self.items.get(res_id, 0)

    def total_value(self) -> int:
        """Вычисляет суммарную стоимость всех ресурсов в трюме по базовым ценам.

        Returns:
            Общая стоимость в кредитах.
        """
        return sum(
            RESOURCES.get(r, {}).get("base_price", 0) * a
            for r, a in self.items.items()
        )

# ---------------------------------------------------------------------------
# Ship module
# ---------------------------------------------------------------------------

class ShipModule:
    """Модуль корабля (реактор, двигатель, щит, сенсор, оружие и т.д.).

    Имеет уровень, прочность, потребление энергии и набор характеристик.
    Может быть улучшен до 5-го уровня.
    """

    def __init__(self, mod_id: str, level=1):
        """
        Args:
            mod_id: идентификатор модуля из конфига SHIP_MODULES.
            level: начальный уровень модуля.
        """
        info = SHIP_MODULES.get(mod_id, {})
        self.id = mod_id  # идентификатор модуля
        self.name = info.get("name", mod_id)  # название модуля
        self.comp = info.get("comp", "reactor")  # отсек, куда устанавливается
        self.weapon_class = info.get("weapon_class")  # класс оружия (None для не-оружия)
        self.damage_type = info.get("damage_type", "energy")  # тип урона
        self.energy_consumption = info.get("energy", 0)  # потребление энергии
        self.stats = {k: v for k, v in info.items() if k in MODULE_STAT_KEYS}  # характеристики модуля
        self.level = level  # уровень модуля
        self._apply_level_bonus()
        self.durability = info.get("durability", 50)  # текущая прочность
        self.max_durability = self.durability  # максимальная прочность
        self.cost = info.get("cost", 100)  # базовая стоимость в кредитах
        self.active = True  # активен ли модуль
        self.desc = info.get("desc", "")  # текстовое описание
        # ── Система боеприпасов ──
        self.ammo_capacity = info.get("ammo_capacity", 0)  # макс. количество зарядов
        self.current_ammo = self.ammo_capacity  # текущее количество зарядов
        self.loaded_ammo_type = None  # тип заряженных боеприпасов (str или None)

    def is_broken(self):
        """Проверяет, сломан ли модуль (прочность <= 0).

        Returns:
            True, если модуль сломан.
        """
        return self.durability <= 0

    # ── Система боеприпасов ──

    def needs_ammo(self):
        """Проверяет, требуется ли этому модулю оружия боеприпасы.

        Returns:
            True, если оружие имеет магазин и использует боеприпасы.
        """
        return self.ammo_capacity > 0

    def has_ammo(self):
        """Проверяет, есть ли заряды в магазине.

        Returns:
            True, если current_ammo > 0.
        """
        return self.current_ammo > 0

    def consume_ammo(self, amount=1):
        """Расходует боеприпас при выстреле.

        Args:
            amount: количество расходуемых зарядов.

        Returns:
            True, если заряды были; False, если недостаточно.
        """
        if self.current_ammo < amount:
            return False
        self.current_ammo -= amount
        return True

    def load_ammo(self, ammo_type: str, amount: int, from_cargo) -> int:
        """Загружает боеприпасы в оружие из трюма.

        Args:
            ammo_type: идентификатор типа боеприпасов.
            amount: сколько единиц попытаться загрузить.
            from_cargo: объект CargoHold, откуда брать боеприпасы.

        Returns:
            Количество реально загруженных единиц.
        """
        if not self.needs_ammo():
            return 0
        available = from_cargo.has(ammo_type)
        to_load = min(amount, available, self.ammo_capacity - self.current_ammo)
        if to_load <= 0:
            return 0
        from_cargo.remove(ammo_type, to_load)
        self.current_ammo += to_load
        self.loaded_ammo_type = ammo_type
        return to_load

    def unload_ammo(self, to_cargo) -> int:
        """Выгружает боеприпасы из оружия обратно в трюм.

        Args:
            to_cargo: объект CargoHold, куда вернуть боеприпасы.

        Returns:
            Количество выгруженных единиц.
        """
        if not self.needs_ammo() or self.current_ammo <= 0:
            return 0
        unloaded = self.current_ammo
        if self.loaded_ammo_type:
            to_cargo.add(self.loaded_ammo_type, unloaded)
        self.current_ammo = 0
        self.loaded_ammo_type = None
        return unloaded

    def upgrade_cost(self):
        """Вычисляет стоимость улучшения модуля в кредитах.

        Returns:
            Стоимость улучшения.
        """
        return int(self.cost * 0.6 * self.level)

    def upgrade_resources(self):
        """Возвращает словарь ресурсов, необходимых для улучшения модуля.

        Returns:
            Словарь {идентификатор ресурса: количество}.
        """
        return {"metal": self.level * 2, "electronics": self.level}

    def can_upgrade(self):
        """Проверяет, можно ли улучшить модуль (уровень < 5).

        Returns:
            True, если улучшение возможно.
        """
        return self.level < 5

    def upgrade(self):
        """Повышает уровень модуля на 1 и пересчитывает характеристики.

        Returns:
            True, если улучшение выполнено; False, если достигнут макс. уровень.
        """
        if not self.can_upgrade():
            return False
        self.level += 1
        self._apply_level_bonus()
        return True

    def _apply_level_bonus(self):
        """Пересчитывает характеристики модуля с учётом текущего уровня (+10% за уровень)."""
        if self.level <= 1:
            return
        info = SHIP_MODULES.get(self.id, {})
        factor = 1.0 + (self.level - 1) * 0.10
        self.stats = {k: int(info.get(k, 0) * factor) for k in MODULE_STAT_KEYS if k in info}
        self.energy_consumption = int(info.get("energy", 0) * factor)
        self.durability = int(info.get("durability", 50) * factor)
        self.max_durability = self.durability

# ---------------------------------------------------------------------------
# Crew member
# ---------------------------------------------------------------------------

class CrewMember:
    """Член экипажа со специальностью, уровнем и наземными боевыми характеристиками.

    Может быть назначен на пост на корабле, получает опыт и повышает уровень.
    """

    def __init__(self, name, specialty_id, race=None):
        """
        Args:
            name: имя члена экипажа.
            specialty_id: идентификатор специальности (из CREW_SPECIALTIES).
            race: раса (если None — выбирается случайно).
        """
        self.name = name  # имя члена экипажа
        self.specialty = specialty_id  # идентификатор специальности
        self.race = race or random.choice(list(RACES))  # раса
        self.level = 1  # уровень
        self.experience = 0  # текущий опыт
        spec = CREW_SPECIALTIES.get(specialty_id, {})
        self.post = spec.get("posts", [specialty_id])[0]  # назначенный пост
        self.bonus = dict(spec.get("bonus", {}))  # бонусы к характеристикам корабля
        self.assigned = False  # назначен ли на пост
        self.salary = random.randint(20, 60) * self.level  # зарплата в кредитах
        # Ground combat stats  # характеристики наземного боя
        self.hp = 30  # здоровье в наземном бою
        self.max_hp = 30  # максимальное здоровье
        self.ap = 4       # очки действий за ход
        self.max_ap = 4   # максимальные очки действий
        self.weapon = "pistol"  # текущее оружие
        self.armor = "vest"  # текущая броня
        self.inventory = {}  # инвентарь: идентификатор предмета -> количество
        self.combat_skill = 50  # базовая точность в наземном бою

    def xp_for_next(self):
        """Возвращает количество опыта, необходимое для следующего уровня.

        Returns:
            Опыт, необходимый для уровня (уровень * 50).
        """
        return self.level * 50

    def add_xp(self, amount):
        """Добавляет опыт и повышает уровень, если накоплено достаточно.

        При повышении уровня бонусы специальности увеличиваются на 15% за уровень.

        Args:
            amount: количество добавляемого опыта.
        """
        self.experience += amount
        if self.experience >= self.xp_for_next():
            self.experience -= self.xp_for_next()
            self.level += 1
            # Scale bonuses
            for k in self.bonus:
                self.bonus[k] = int(self.bonus[k] * (1 + (self.level - 1) * 0.15))

    def desc(self):
        """Возвращает краткое текстовое описание члена экипажа.

        Returns:
            Строка вида "Имя (Специальность LvX)".
        """
        spec_name = CREW_SPECIALTIES.get(self.specialty, {}).get("name", self.specialty)
        return f"{self.name} ({spec_name} Lv{self.level})"

# ---------------------------------------------------------------------------
# Player ship
# ---------------------------------------------------------------------------

class PlayerShip:
    """Корабль игрока.

    Содержит корпус, модули в отсеках, экипаж, груз, улучшения,
    миссии, репутацию и навыки. Предоставляет методы для управления
    кораблём: покупка/продажа корпусов, установка модулей, крафт,
    найм экипажа, бой, сканирование.
    """

    def __init__(self, name="Endeavour", hull=100):
        """
        Args:
            name: название корабля.
            hull: начальная прочность корпуса (для обратной совместимости с тестами).
        """
        self.name = name  # название корабля
        self.hull_id = "corvette"  # идентификатор текущего корпуса
        hull_cfg = SHIP_HULLS.get("corvette", {})
        # hull parameter overrides the config hull (backward compat with tests)
        if hull != 100:
            self.hull = hull  # текущая прочность корпуса
            self.max_hull = hull  # максимальная прочность корпуса
        else:
            self.hull = hull_cfg.get("hull", hull)  # текущая прочность корпуса
            self.max_hull = self.hull  # максимальная прочность корпуса
        self.owned_hulls = ["corvette"]  # список купленных корпусов
        self.upgrades = {}  # словарь: идентификатор улучшения -> True
        self.shield_hp = 30  # очки щита
        self.fuel = 80  # запас топлива
        self.credits = 1000  # кредиты
        self.radiation_shield = False  # флаг защиты от радиации звёзд
        self.race = "human"  # раса игрока
        self.race_data = {}  # кэш бонусов/штрафов текущей расы (заполняется apply_race_bonus)
        self.race_hull_bonus = 0  # бонус корпуса от расы
        self.religion = None  # религия (влияет на контрабанду)
        self.reputation = {f: 0 for f in FACTIONS}  # репутация с фракциями
        self.reputation["pirates"] = -10  # начальная репутация с пиратами
        self.skill_trade = 0  # навык торговли (влияет на цены)
        # Crew: assigned posts + roster  # экипаж: назначенные посты + список
        self.crew = {"Pilot": None, "Engineer": None, "Tactical": None, "Scientist": None}  # посты: имя члена экипажа
        self.crew_members: list[CrewMember] = []  # весь нанятый экипаж
        # Calculate cargo from hull + upgrades  # расчёт вместимости с учётом улучшений
        cb = self._upgrade_bonus("cargo_bonus", 0)
        self.cargo = CargoHold(hull_cfg.get("cargo", 50) + cb)  # грузовой отсек
        # Compartments  # отсеки с модулями
        self._init_compartments(hull_cfg)
        self._last_damaged_module = None  # последний повреждённый модуль
        self.missions: list[Mission] = []  # список активных миссий
        self.tracked_mission = None  # идентификатор отслеживаемой миссии

    def _init_compartments(self, hull_cfg):
        """Инициализирует отсеки корабля согласно конфигурации корпуса.

        Создаёт отсеки, устанавливает стартовые модули в активные отсеки.

        Args:
            hull_cfg: словарь конфигурации текущего корпуса.
        """
        num_comps = hull_cfg.get("compartments", 5)  # количество активных отсеков
        priority = ["reactor", "engine", "shield", "sensor", "weapon",
                    "cargo", "life_support"]
        active = set(priority[:num_comps])  # какие отсеки активны
        self.compartments = {}
        for c in COMPARTMENTS:
            self.compartments[c] = {"power": 5, "modules": []}  # мощность отсека + список модулей
        for comp, mod_id in STARTER_MODULE_MAP.items():
            if comp in active:
                self.compartments[comp]["modules"].append(ShipModule(mod_id))

    # ---------- Upgrade helpers ----------

    def _upgrade_bonus(self, key, default=0):
        """Суммирует бонусы от постоянных улучшений по указанному ключу.

        Args:
            key: ключ характеристики (например, "cargo_bonus").
            default: значение по умолчанию.

        Returns:
            Суммарный бонус.
        """
        total = default
        for uid in self.upgrades:
            cfg = UPGRADES.get(uid, {})
            total += cfg.get("bonus", {}).get(key, 0)
        return total

    def _crew_bonus(self, key, default=0):
        """Суммирует бонусы от назначенного экипажа по указанному ключу.

        Args:
            key: ключ характеристики (например, "speed").
            default: значение по умолчанию.

        Returns:
            Суммарный бонус от экипажа.
        """
        total = default
        for post, member_name in self.crew.items():
            if not member_name:
                continue
            cm = self._get_crew(member_name)
            if cm and cm.assigned:
                total += cm.bonus.get(key, 0)
        return total

    def _get_crew(self, name):
        """Находит члена экипажа по имени (регистронезависимо).

        Args:
            name: имя для поиска.

        Returns:
            Объект CrewMember или None, если не найден.
        """
        for cm in self.crew_members:
            if cm.name.lower() == name.lower():
                return cm
        return None

    # ---------- Race bonuses ----------

    def apply_race_bonus(self, race_id=None):
        """Устанавливает текущую расу и пересчитывает её бонусы/штрафы.

        Вызывается при выборе расы в стартовом меню.
        Модифицирует max_hull (если расовый бонус влияет на корпус)
        и кэширует все бонусы в self.race_data.

        Args:
            race_id: идентификатор расы (например, "human", "mutant").
                     Если None — применяет текущую self.race.
        """
        if race_id:
            self.race = race_id
        race_cfg = RACES.get(self.race, RACES["human"])
        bonuses = dict(race_cfg.get("bonus", {}))
        penalties = dict(race_cfg.get("penalty", {}))
        # Собираем все модификаторы в один словарь
        merged = {}
        for k, v in bonuses.items():
            merged[k] = v
        for k, v in penalties.items():
            merged[k] = merged.get(k, 0) + v
        self.race_data = merged
        # Применяем модификаторы корпуса
        hull_mod = merged.pop("max_hull", 0)
        old_max = self.max_hull
        self.race_hull_bonus = hull_mod
        self.max_hull = max(20, self.max_hull + hull_mod)
        self.hull = min(self.hull, self.max_hull)

    def _race_bonus(self, key, default=0):
        """Возвращает расовый бонус/штраф по указанной характеристике.

        Args:
            key: ключ характеристики (например, "accuracy", "damage").
            default: значение по умолчанию.

        Returns:
            Числовое значение бонуса (положительное или отрицательное).
        """
        return self.race_data.get(key, default)

    # ---------- Hull management ----------

    def buy_hull(self, hull_id):
        """Покупает новый корпус на верфи.

        Args:
            hull_id: идентификатор корпуса.

        Returns:
            Кортеж (сообщение, успех).
        """
        if hull_id in self.owned_hulls:
            return f"Already own {hull_id}.", False
        cfg = SHIP_HULLS.get(hull_id)
        if not cfg:
            return f"Unknown hull '{hull_id}'.", False
        if self.credits < cfg["cost"]:
            return f"Need {cfg['cost']}cr, have {self.credits}cr.", False
        self.credits -= cfg["cost"]
        self.owned_hulls.append(hull_id)
        return f"Purchased {cfg['name']} for {cfg['cost']}cr.", True

    def sell_hull(self, hull_id):
        """Продаёт корпус на верфи (50% цены). Нельзя продать текущий корпус.

        Args:
            hull_id: идентификатор корпуса.

        Returns:
            Кортеж (сообщение, успех).
        """
        if hull_id not in self.owned_hulls:
            return f"Don't own {hull_id}.", False
        if hull_id == self.hull_id:
            return "Cannot sell current hull.", False
        cfg = SHIP_HULLS.get(hull_id)
        if not cfg:
            return f"Unknown hull '{hull_id}'.", False
        price = cfg["cost"] // 2
        self.credits += price
        self.owned_hulls.remove(hull_id)
        return f"Sold {cfg['name']} for {price}cr.", True

    def switch_hull(self, hull_id):
        """Переключается на другой корпус из числа купленных, перенося модули.

        Args:
            hull_id: идентификатор корпуса.

        Returns:
            Кортеж (сообщение, успех).
        """
        if hull_id not in self.owned_hulls:
            return f"Don't own {hull_id}.", False
        cfg = SHIP_HULLS.get(hull_id)
        if not cfg:
            return f"Unknown hull '{hull_id}'.", False
        # Collect all current modules
        all_modules = []
        for c in COMPARTMENTS:
            all_modules.extend(self.compartments[c]["modules"])
        # Set new hull
        self.hull_id = hull_id
        self.max_hull = cfg["hull"]  # новая макс. прочность корпуса
        self.hull = min(self.hull, self.max_hull)
        base_cap = cfg.get("cargo", 50)
        cb = self._upgrade_bonus("cargo_bonus", 0)
        self.cargo.capacity = base_cap + cb
        # Re-init compartments and reinstall what fits
        self._init_compartments(cfg)
        # Try to place excess modules
        leftover = []
        for m in all_modules:
            if m.comp in self.compartments and len(self.compartments[m.comp]["modules"]) <= 1:
                # Replace starter module with this one
                existing = [x for x in self.compartments[m.comp]["modules"]]
                if len(existing) == 1 and existing[0].id in ("fusion_reactor", "ion_drive",
                        "deflector_shield", "long_range_scanner", "laser_turret"):
                    self.compartments[m.comp]["modules"] = [m]
                    placed = True
            if not placed:
                leftover.append(m)
        return f"Switched to {cfg['name']}. {len(leftover)} modules moved to cargo (not implemented).", True

    # ---------- Permanent upgrades ----------

    def has_upgrade(self, upgrade_id):
        """Проверяет, установлено ли указанное улучшение.

        Args:
            upgrade_id: идентификатор улучшения.

        Returns:
            True, если улучшение активно.
        """
        return self.upgrades.get(upgrade_id, False)

    def apply_upgrade(self, upgrade_id):
        """Устанавливает постоянное улучшение корпуса.

        Проверяет наличие ресурсов, списывает стоимость, применяет бонусы.

        Args:
            upgrade_id: идентификатор улучшения.

        Returns:
            Кортеж (сообщение, успех).
        """
        if self.has_upgrade(upgrade_id):
            return f"Already have {upgrade_id}.", False
        cfg = UPGRADES.get(upgrade_id)
        if not cfg:
            return f"Unknown upgrade '{upgrade_id}'.", False
        if self.credits < cfg["cost"]:
            return f"Need {cfg['cost']}cr, have {self.credits}cr.", False
        # Check resources
        for rid, amt in cfg["inputs"].items():
            if self.cargo.has(rid) < amt:
                return f"Need {amt} {rid}.", False
        # Consume
        self.credits -= cfg["cost"]
        for rid, amt in cfg["inputs"].items():
            self.cargo.remove(rid, amt)
        self.upgrades[upgrade_id] = True
        # Apply immediate bonuses
        bonus = cfg.get("bonus", {})
        if "max_hull" in bonus:
            self.max_hull += bonus["max_hull"]
            self.hull = min(self.hull + bonus["max_hull"], self.max_hull)
        if "cargo_bonus" in bonus:
            self.cargo.capacity += bonus["cargo_bonus"]
        return f"Installed {cfg['name']}.", True

    # ---------- Crafting ----------

    def craft(self, recipe_id, amount=1):
        """Создаёт предметы по рецепту из имеющихся ресурсов.

        Args:
            recipe_id: идентификатор рецепта.
            amount: количество создаваемых предметов.

        Returns:
            Кортеж (сообщение, успех).
        """
        recipe = RECIPES.get(recipe_id)
        if not recipe:
            return f"Unknown recipe '{recipe_id}'.", False
        # Check resources
        inputs = recipe["inputs"]
        for rid, amt in inputs.items():
            needed = amt * amount
            if self.cargo.has(rid) < needed:
                return f"Need {needed} {rid} (have {self.cargo.has(rid)}).", False
        # Check output space
        output_id = recipe_id
        if self.cargo.free() < amount:
            return f"Need {amount} cargo space (have {self.cargo.free()}).", False
        # Consume inputs
        for rid, amt in inputs.items():
            self.cargo.remove(rid, amt * amount)
        # Create output
        self.cargo.add(output_id, amount)
        return f"Crafted {amount}x {recipe['name']}.", True

    # ---------- Crew management ----------

    def hire_crew(self, crew_member):
        """Нанимает члена экипажа.

        Args:
            crew_member: объект CrewMember.

        Returns:
            Кортеж (сообщение, успех).
        """
        if len(self.crew_members) >= self._max_crew_slots():
            return "Crew quarters full.", False
        if self.credits < crew_member.salary:
            return f"Need {crew_member.salary}cr salary.", False
        self.credits -= crew_member.salary
        self.crew_members.append(crew_member)
        return f"Hired {crew_member.name} ({crew_member.specialty}).", True

    def fire_crew(self, name):
        """Увольняет члена экипажа по имени.

        Args:
            name: имя увольняемого.

        Returns:
            Кортеж (сообщение, успех).
        """
        cm = self._get_crew(name)
        if not cm:
            return f"No crew named '{name}'.", False
        # Unassign if on duty
        for post, member in list(self.crew.items()):
            if member and member.lower() == name.lower():
                self.crew[post] = None
                cm.assigned = False
        self.crew_members.remove(cm)
        return f"Fired {cm.name}.", True

    def assign_crew(self, name, post):
        """Назначает члена экипажа на указанный пост.

        Args:
            name: имя члена экипажа.
            post: название поста (Pilot, Engineer, Tactical, Scientist).

        Returns:
            Кортеж (сообщение, успех).
        """
        cm = self._get_crew(name)
        if not cm:
            return f"No crew named '{name}'.", False
        if post not in self.crew:
            return f"Unknown post '{post}'.", False
        spec_posts = CREW_SPECIALTIES.get(cm.specialty, {}).get("posts", [])
        if post not in spec_posts:
            spec_name = CREW_SPECIALTIES.get(cm.specialty, {}).get("name", cm.specialty)
            return f"{cm.name} ({spec_name}) cannot take '{post}' post.", False
        # Unassign from current post
        for p, member in list(self.crew.items()):
            if member and member.lower() == name.lower():
                self.crew[p] = None
                cm.assigned = False
        # Assign to new post
        old = self.crew[post]
        if old:
            old_cm = self._get_crew(old)
            if old_cm:
                old_cm.assigned = False
        self.crew[post] = cm.name
        cm.assigned = True
        return f"{cm.name} assigned to {post}.", True

    def _max_crew_slots(self):
        """Вычисляет максимальное количество членов экипажа (база + модуль жизнеобеспечения).

        Returns:
            Максимальное количество слотов экипажа.
        """
        base = 2  # базовое количество слотов
        for m in self.compartments.get("life_support", {}).get("modules", []):
            if m.active and not m.is_broken():
                base += m.stats.get("crew_efficiency", 0) // 5
        return base

    def use_item(self, item_id, amount=1):
        """Использует расходный предмет из груза (ремкомплект, топливо, усилитель щита).

        Args:
            item_id: идентификатор предмета.
            amount: количество использований.

        Returns:
            Кортеж (сообщение, успех).
        """
        BONUSES = {
            "repair_kit": {"hull": 20, "msg": "Restored {} hull"},
            "fuel_cell": {"fuel": 10, "msg": "Refined {} fuel"},
            "shield_booster": {"shield": 15, "msg": "Boosted {} shields"},
        }
        bonus = BONUSES.get(item_id)
        if not bonus:
            return f"Item '{item_id}' is not consumable.", False
        have = self.cargo.has(item_id)
        if have < amount:
            return f"Need {amount}, have {have}.", False
        if not self.cargo.remove(item_id, amount):
            return "Cargo error.", False
        applied = 0
        if "hull" in bonus:
            prev = self.hull
            self.hull = min(self.max_hull, self.hull + bonus["hull"] * amount)
            applied += self.hull - prev
        if "fuel" in bonus:
            self.fuel += bonus["fuel"] * amount
            applied += bonus["fuel"] * amount
        if "shield" in bonus:
            cap = self.get_effective_stats().get("shield_cap", 0)  # макс. щит
            prev = self.shield_hp
            self.shield_hp = min(cap, self.shield_hp + bonus["shield"] * amount)
            applied += self.shield_hp - prev
        return (bonus["msg"].format(applied), True)

    def install_module_from_cargo(self, mod_id):
        """Устанавливает модуль из грузового отсека в подходящий отсек.

        Args:
            mod_id: идентификатор модуля.

        Returns:
            Кортеж (сообщение, успех).
        """
        have = self.cargo.has(mod_id)
        if not have:
            return f"No '{mod_id}' in cargo.", False
        info = SHIP_MODULES.get(mod_id)
        if not info:
            return f"Unknown module '{mod_id}'.", False
        comp = info.get("comp", "reactor")  # отсек для этого модуля
        if comp not in self.compartments:
            return f"No '{comp}' compartment.", False
        if not self.cargo.remove(mod_id, 1):
            return "Cargo error.", False
        self.compartments[comp]["modules"].append(ShipModule(mod_id))
        return f"Installed {info.get('name', mod_id)} in {comp}.", True

    def take_damage(self, amount):
        """Наносит урон кораблю: щиты поглощают урон первыми, остаток идёт в корпус.

        Args:
            amount: количество урона.

        Returns:
            True, если корабль ещё жив; False, если корпус разрушен.
        """
        if self.shield_hp > 0:
            absorbed = min(self.shield_hp, amount)  # сколько урона поглотили щиты
            self.shield_hp -= absorbed
            amount -= absorbed
        if amount > 0:
            self.hull = max(0, self.hull - amount)  # остаток урона идёт в корпус
            self._damage_random_module()  # шанс повредить случайный модуль
        return self.hull > 0

    def _damage_random_module(self):
        """С вероятностью 30% повреждает случайный активный модуль при попадании по корпусу."""
        import random
        if random.random() > 0.3:
            return
        candidates = [
            m for c in COMPARTMENTS
            for m in self.compartments[c]["modules"]
            if m.active and not m.is_broken()
        ]
        if candidates:
            m = random.choice(candidates)
            m.durability = max(0, m.durability - random.randint(5, 15))
            self._last_damaged_module = m

    def regen_shields(self):
        """Восстанавливает щиты на величину регенерации за ход.

        Также восстанавливает корпус, если есть соответствующий бонус экипажа.
        """
        cap = self.get_effective_stats().get("shield_cap", 0)  # макс. уровень щита
        rate = self.get_effective_stats().get("shield_regen", 0)  # регенерация за ход
        self.shield_hp = min(cap, self.shield_hp + rate)
        # Crew hull regen
        hr = self._crew_bonus("hull_regen", 0)
        if hr > 0 and self.hull < self.max_hull:
            self.hull = min(self.max_hull, self.hull + hr)

    def repair_module(self, comp_name, cost_metal=2, cost_electronics=1):
        """Ремонтирует наиболее повреждённый модуль в указанном отсеке.

        Args:
            comp_name: название отсека.
            cost_metal: стоимость ремонта в металле.
            cost_electronics: стоимость ремонта в электронике.

        Returns:
            Кортеж (сообщение, стоимость).
        """
        if comp_name not in self.compartments:
            return f"Unknown compartment '{comp_name}'.", 0
        mods = self.compartments[comp_name]["modules"]
        damaged = [m for m in mods if m.durability < m.max_durability]  # повреждённые модули
        if not damaged:
            return f"No damaged modules in {comp_name}.", 0
        m = max(damaged, key=lambda x: x.max_durability - x.durability)  # самый повреждённый
        repair_amount = min(20, m.max_durability - m.durability)  # сколько восстанавливаем
        m.durability += repair_amount
        status = "repaired" if not m.is_broken() else "partially repaired"
        return f"{m.name} {status} (+{repair_amount} dur).", cost_metal + cost_electronics

    def total_power_generated(self):
        """Вычисляет общую генерацию энергии всеми реакторами с учётом улучшений.

        Returns:
            Количество вырабатываемой энергии.
        """
        base = sum(
            m.stats.get("power", 0)
            for m in self.compartments["reactor"]["modules"]
        )
        bonus = self._upgrade_bonus("power_bonus", 0) + self._race_bonus("power_bonus", 0)
        return base + bonus

    def total_power_consumed(self):
        """Вычисляет общее потребление энергии всеми активными модулями.

        Returns:
            Количество потребляемой энергии.
        """
        return sum(
            m.energy_consumption
            for c in COMPARTMENTS
            for m in self.compartments[c]["modules"]
            if m.active and not m.is_broken()
        )

    def get_effective_stats(self):
        """Вычисляет итоговые характеристики корабля с учётом модулей, улучшений и экипажа.

        Учитывает эффективность энергосистемы: если потребление превышает генерацию,
        характеристики пропорционально снижаются (минимум 30%).

        Returns:
            Словарь {название характеристики: значение}.
        """
        stats = {
            "speed": 0, "evasion": 0, "damage": 0, "accuracy": 0,
            "shield_cap": 0, "shield_regen": 0, "sensor_range": 7,
            "cargo_bonus": 0, "crew_efficiency": 0, "hull_bonus": 0,
            "range": 1,
        }
        total = self.total_power_generated()  # всего энергии
        used = self.total_power_consumed()  # потребление энергии
        eff = 1.0 if used <= total else max(0.3, total / max(1, used))  # коэффициент эффективности
        for c in COMPARTMENTS:
            for m in self.compartments[c]["modules"]:
                if m.active and not m.is_broken():
                    for k in stats:
                        stats[k] += m.stats.get(k, 0) * eff
        # Apply upgrade bonuses
        for bonus_key, stat_key in UPGRADE_STAT_MAP.items():
            stats[stat_key] += self._upgrade_bonus(bonus_key, 0)
        # Apply crew bonuses
        for bonus_key, stat_key in CREW_STAT_MAP.items():
            stats[stat_key] += self._crew_bonus(bonus_key, 0)
        # Apply race bonuses (keys that match stat names directly)
        for k in stats:
            stats[k] += self._race_bonus(k, 0)
        return {k: int(v) for k, v in stats.items()}

    def check_missions(self, station):
        """Проверяет, завершены ли какие-либо миссии на текущей станции (доставка).

        Args:
            station: объект Station, на которой находится корабль.

        Returns:
            Список кортежей (миссия, сообщение) для выполненных миссий.
        """
        completed = []
        for m in self.missions:
            if m.mtype == "deliver" and m.target_station == station.name:
                if self.cargo.has(m.resource) >= m.amount:
                    self.cargo.remove(m.resource, m.amount)
                    self.credits += m.reward
                    m.status = "completed"
                    completed.append((m, f"Mission complete! Delivered {m.amount} {m.resource} to {station.name}. +{m.reward}cr"))
        for m, _ in completed:
            self.missions.remove(m)
        return completed

    MAX_MISSIONS = 5  # максимальное количество активных миссий

    def add_mission(self, mission):
        """Принимает миссию (добавляет в список активных).

        Args:
            mission: объект Mission.

        Returns:
            Кортеж (сообщение, успех).
        """
        if len(self.missions) >= self.MAX_MISSIONS:
            return "Mission log full (max 5).", False
        if mission.id in (m.id for m in self.missions):
            return "Already have this mission.", False
        mission.status = "active"
        self.missions.append(mission)
        return f"Accepted: {mission.title}", True

    def abandon_mission(self, mission_id):
        """Отменяет миссию по идентификатору со штрафом репутации.

        Args:
            mission_id: идентификатор миссии.

        Returns:
            Кортеж (сообщение, успех).
        """
        for m in self.missions:
            if m.id == mission_id:
                m.status = "abandoned"
                self.missions.remove(m)
                if m.giver_station:
                    penalty = -10
                    self.reputation[m.giver_station.faction] = \
                        self.reputation.get(m.giver_station.faction, 0) + penalty
                return f"Abandoned: {m.title}. Reputation penalty applied.", True
        return "Mission not found.", False

    def track_mission(self, mission_id):
        """Устанавливает миссию для отслеживания.

        Args:
            mission_id: идентификатор миссии.

        Returns:
            Объект Mission или None, если миссия не найдена.
        """
        for m in self.missions:
            if m.id == mission_id:
                self.tracked_mission = mission_id
                return m
        self.tracked_mission = None
        return None

    def has_mission(self, mission_id):
        """Проверяет, есть ли миссия с указанным идентификатором в списке.

        Args:
            mission_id: идентификатор миссии.

        Returns:
            True, если миссия есть.
        """
        return any(m.id == mission_id for m in self.missions)

    def fail_expired_missions(self, galaxy_news):
        """Тикает дедлайны миссий и помечает просроченные как проваленные.

        Args:
            galaxy_news: список новостей (NewsEntry), куда добавляется запись о провале.

        Returns:
            Список проваленных миссий.
        """
        failed = []
        for m in list(self.missions):
            if m.status != "active":
                continue
            m.ticks -= 1  # уменьшаем оставшееся время
            if m.ticks <= 0:
                m.status = "failed"
                self.missions.remove(m)
                failed.append(m)
                if galaxy_news is not None:
                    galaxy_news.append(NewsEntry("MISSION FAILED", m.title))
        return failed

    def scan_target(self, target, scan_type="active", galaxy=None):
        """Сканирует указанную цель.

        Args:
            target: объект для сканирования (корабль, станция и т.д.).
            scan_type: тип сканирования — "passive", "active" или "deep".
            galaxy: объект Galaxy (для генерации миссий при сканировании).

        Returns:
            Объект ScanResult с информацией о цели.
        """
        from config import SCAN_ACTIVE_COST, SCAN_DEEP_COST
        cost = SCAN_DEEP_COST if scan_type == "deep" else SCAN_ACTIVE_COST  # стоимость сканирования
        if self._crew_bonus("scanner", 0):
            cost = max(1, cost - self._crew_bonus("scanner", 0) // 5)
        if scan_type != "passive":
            spare = self.total_power_generated() - self.total_power_consumed()  # свободная энергия
            if spare < cost:
                return ScanResult(False, info={"error": f"Need {cost} spare power (have {spare})."})
        sensor_range = self.get_effective_stats().get("sensor_range", 5)  # дальность сенсоров
        rng_map = {"active": sensor_range * 2, "deep": sensor_range, "passive": sensor_range}
        rng = rng_map.get(scan_type, sensor_range)  # дальность для данного типа сканирования
        # Build info dict
        info = {"type": type(target).__name__, "scanned": True, "scan_level": scan_type}
        if hasattr(target, "hull"):
            info["hull"] = target.hull  # текущая прочность корпуса
            info["max_hull"] = getattr(target, "max_hull", target.hull)  # макс. прочность
        if hasattr(target, "shield_hp"):
            info["shield"] = target.shield_hp  # очки щита
        if hasattr(target, "cargo") and scan_type in ("active", "deep"):
            info["cargo"] = dict(target.cargo.items) if hasattr(target.cargo, "items") else {}
        if hasattr(target, "compartments") and scan_type == "deep":
            comps = {}
            for c in COMPARTMENTS:
                mods = target.compartments[c]["modules"]
                comps[c] = [{"name": m.name, "dur": m.durability, "max": m.max_durability, "broken": m.is_broken()} for m in mods]
            info["compartments"] = comps  # состояние отсеков
        if hasattr(target, "name"):
            info["name"] = target.name  # имя цели
        if hasattr(target, "faction"):
            info["faction"] = target.faction  # фракция цели
        # Mark target as scanned
        if hasattr(target, "scanned"):
            target.scanned = True
        if hasattr(target, "scan_level"):
            target.scan_level = scan_type
        # Check if scanning generates a mission
        generated_mission = None
        if galaxy and scan_type in ("active", "deep"):
            generated_mission = galaxy.scan_generate_missions(target, scan_type, self)
        return ScanResult(True, scan_type, info, scanned_obj=target)

    def install_module(self, mod_id: str) -> bool:
        """Устанавливает модуль непосредственно (без проверки груза) в соответствующий отсек.

        Args:
            mod_id: идентификатор модуля.

        Returns:
            True, если модуль установлен; False, если модуль неизвестен или отсек не найден.
        """
        info = SHIP_MODULES.get(mod_id)
        if not info:
            return False
        comp = info.get("comp", "reactor")
        if comp not in self.compartments:
            return False
        self.compartments[comp]["modules"].append(ShipModule(mod_id))
        return True

# ---------------------------------------------------------------------------
# NPC ships
# ---------------------------------------------------------------------------

NPCShip_id_counter = 0

class NPCShip:
    """Базовый класс NPC-корабля.

    Содержит позицию на карте, прочность корпуса, фракцию, груз и флаг сканирования.
    """

    def __init__(self, x, y, name, hull, faction, race=None, cc=100):
        """
        Args:
            x, y: координаты на карте.
            name: название корабля.
            hull: прочность корпуса.
            faction: фракция.
            race: раса (если None — случайная).
            cc: вместимость грузового отсека.
        """
        global NPCShip_id_counter
        NPCShip_id_counter += 1
        self.uid = NPCShip_id_counter  # уникальный идентификатор NPC
        self.x, self.y = x, y  # координаты на карте
        self.name = name  # название корабля
        self.hull = hull  # текущая прочность корпуса
        self.max_hull = hull  # максимальная прочность корпуса
        self.shield_hp = 0  # очки щита
        self.faction = faction  # фракция
        self.race = race or random.choice(list(RACES))  # раса
        self.cargo = CargoHold(cc)  # грузовой отсек
        self.credits = 500  # кредиты
        self.alive = True  # жив ли корабль
        self.scanned = False  # был ли отсканирован
        self.scan_level = None  # уровень сканирования

    def take_damage(self, amount):
        """Наносит урон NPC-кораблю (щиты поглощают первой, остаток — корпус).

        Args:
            amount: количество урона.

        Returns:
            True, если корабль ещё жив; False, если уничтожен.
        """
        if self.shield_hp > 0:
            absorbed = min(self.shield_hp, amount)  # сколько урона поглотили щиты
            self.shield_hp -= absorbed
            amount -= absorbed
        if amount > 0:
            self.hull = max(0, self.hull - amount)  # остаток урона в корпус
        if self.hull <= 0:
            self.alive = False
        return self.alive

class TraderShip(NPCShip):
    """Торговый корабль. Следует по маршруту между станциями, торгует ресурсами."""

    NAMES = ["Hornet","Mercury","Venture","Polaris","Comet","Drifter","Nomad"]
    def __init__(self, x, y, route):
        """
        Args:
            x, y: начальные координаты.
            route: список индексов станций в маршруте.
        """
        name = random.choice(self.NAMES) + str(random.randint(1, 99))
        faction = random.choice(["free_traders", "imperium", "machine_collective"])
        super().__init__(x, y, name, 60, faction, None, 100)
        self.shield_hp = 20  # щиты торговца
        self.route = route  # маршрут (список индексов станций)
        self.route_index = 0  # текущая точка маршрута
        self.cargo.add("fuel_cell", 20)
        self.cargo.add("electronics", random.randint(3, 8))
        self.cargo.add("metal", random.randint(5, 15))
        self.credits = random.randint(200, 600)  # кредиты
        self.wait_ticks = 0  # счётчик ожидания на станции

    def current_target(self, stations):
        """Возвращает текущую целевую станцию по маршруту.

        Args:
            stations: список всех станций в галактике.

        Returns:
            Объект Station или None, если маршрут пуст.
        """
        if not self.route or not stations:
            return None
        idx = self.route[self.route_index % len(self.route)]
        if 0 <= idx < len(stations):
            return stations[idx]
        return None

class PirateShip(NPCShip):
    """Пиратский корабль. Атакует игрока и торговцев в радиусе агрессии."""

    NAMES = ["Raider","Reaver","Corsair","Buccaneer","Scourge","Viper","Wraith"]
    def __init__(self, x, y):
        """
        Args:
            x, y: начальные координаты.
        """
        name = random.choice(self.NAMES) + str(random.randint(1, 99))
        faction = random.choice(["chaos_cult", "xenos_horde"])
        super().__init__(x, y, name, 40, faction, None, 30)
        self.shield_hp = 10  # щиты пирата
        self.credits = random.randint(50, 150)  # кредиты
        self.aggro_range = 5  # радиус агрессии
        self.flee_threshold = 8  # порог прочности для бегства

# ---------------------------------------------------------------------------
# Station
# ---------------------------------------------------------------------------

DESIRED_STOCK = 20

class Station:
    """Космическая станция. Поддерживает торговлю, миссии, продажу модулей и корпусов.

    Имеет тип (торговая, промышленная, верфь, храм, таверна и т.д.),
    фракцию, инвентарь с ценами, генерирует миссии и развивает экономику.
    """

    NAMES = ["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Theta",
             "Nova","Prime","Sol","Haven","Forge"]

    def __init__(self, x, y, name=None, stype=None, faction=None):
        """
        Args:
            x, y: координаты на карте.
            name: название станции (если None — случайное).
            stype: тип станции (если None — случайный).
            faction: фракция (если None — случайная).
        """
        self.x, self.y = x, y  # координаты станции
        self.name = name or random.choice(self.NAMES)  # название станции
        stype_choices = list(STATION_TYPES)
        self.stype = stype or random.choice(stype_choices)  # тип станции
        self.faction = faction or random.choice(list(FACTIONS))  # фракция
        self.religion = None  # религия станции
        self.inventory: dict[str, int] = {}  # инвентарь: идентификатор ресурса -> количество
        self.prices: dict[str, tuple[int, int]] = {}  # цены: ресурс -> (цена_покупки, цена_продажи)
        self.crisis_ticks = 0  # счётчик кризиса (экономика заморожена)
        self.price_history: dict[str, list] = {r: [] for r in RESOURCES}  # история цен
        self.missions: list = []  # доступные миссии
        self.modules_for_sale: list[str] = []  # модули в продаже
        self.hulls_for_sale: list[str] = []    # корпуса в продаже (верфь)
        self.recipes_available: list[str] = []  # доступные рецепты (мастерская)
        self.crew_for_hire: list = []           # экипаж для найма (таверна)
        self.scanned = False  # была ли станция отсканирована
        self._init_inventory()
        self._init_modules()
        self._init_type_specific()
        self.update_prices()

    def _init_type_specific(self):
        """Инициализирует специфичные для типа станции предложения (корпуса, рецепты, экипаж)."""
        st_cfg = STATION_TYPES.get(self.stype, {})
        if self.stype == "shipyard":
            hulls = st_cfg.get("hulls", [])
            # Filter a subset of hulls based on faction/random
            self.hulls_for_sale = random.sample(hulls, min(random.randint(2, 4), len(hulls)))
        elif self.stype == "workshop":
            recipes = st_cfg.get("recipes", [])
            self.recipes_available = random.sample(recipes, min(random.randint(2, 4), len(recipes)))
        elif self.stype == "tavern":
            slots = st_cfg.get("crew_slots", 3)
            specs = list(CREW_SPECIALTIES)
            for _ in range(random.randint(1, slots)):
                name = random.choice(CREW_NAMES) + str(random.randint(1, 99))
                spec = random.choice(specs)
                self.crew_for_hire.append(CrewMember(name, spec))

    def _init_inventory(self):
        """Заполняет начальный инвентарь станции случайными количествами ресурсов."""
        for r in RESOURCES:
            self.inventory[r] = random.randint(8, 25)

    def _init_modules(self):
        """Выбирает случайные модули для продажи на станции (исключая стартовые)."""
        import random
        from config import SHIP_MODULES
        available = list(SHIP_MODULES)
        # Exclude starter modules
        starter = {"fusion_reactor", "ion_drive", "deflector_shield", "long_range_scanner"}
        pool = [m for m in available if m not in starter]
        count = random.randint(2, 5)
        self.modules_for_sale = random.sample(pool, min(count, len(pool)))

    def gen_missions(self, all_stations):
        """Генерирует миссии по доставке на другие станции или награды за пиратов.

        Args:
            all_stations: список всех станций в галактике.
        """
        others = [s for s in all_stations if s.name != self.name]
        if not others or len(self.missions) >= 4:
            return
        target = random.choice(others)
        et = random.choice(["deliver", "deliver", "bounty"])
        if et == "deliver":
            rid = random.choice(list(RESOURCES))
            amt = random.randint(3, 8)
            price = RESOURCES[rid]["base_price"]
            reward = price * amt * random.randint(2, 4)
            desc = f"Deliver {amt}x {RESOURCES[rid]['name']} to {target.name}."
            m = Mission("deliver", rid, amt, target.name, reward,
                       random.randint(20, 40), title=desc[:44],
                       description=desc, giver_station=self)
        else:  # bounty
            bounty = random.randint(3, 6) * 50
            desc = f"Hunt pirates near {self.name}. Reward: {bounty}cr."
            m = Mission("bounty", "credits", 1, self.name, bounty,
                       random.randint(15, 30), title=desc[:44],
                       description=desc, giver_station=self)
        self.missions.append(m)

    def update_prices(self):
        """Обновляет цены на ресурсы в зависимости от текущего количества на складе.

        Дефицитные товары дорожают, избыточные дешевеют.
        """
        for rid, info in RESOURCES.items():
            stock = self.inventory.get(rid, 0)  # текущий запас
            base = info["base_price"]  # базовая цена
            if stock < 4:
                factor = 2.5  # дефицит — цена ×2.5
            elif stock < 10:
                factor = 1.8
            elif stock > 40:
                factor = 0.5  # избыток — цена ×0.5
            else:
                factor = max(0.6, min(1.5, 20 / max(1, stock)))
            bp = int(base * factor * 0.85)  # цена покупки у игрока
            sp = int(base * factor * 1.15)  # цена продажи игроку
            self.prices[rid] = (max(1, bp), max(1, sp))
            self.price_history[rid].append((bp, sp))  # сохраняем в историю
            if len(self.price_history[rid]) > 20:
                self.price_history[rid] = self.price_history[rid][-20:]

    def update_economy(self):
        """Обновляет экономику станции: потребляет/производит ресурсы согласно типу.

        Если станция в кризисе (crisis_ticks > 0), экономика заморожена.
        """
        if self.crisis_ticks > 0:
            self.crisis_ticks -= 1
            return
        ti = {
            "trade_hub":  {"consume": {"ice": 1},          "produce": {"electronics": 1}},
            "industrial": {"consume": {"ore": 2, "ice": 1},"produce": {"metal": 2}},
            "research":   {"consume": {"electronics": 1},  "produce": {"shield_mod": 1}},
            "temple":     {"consume": {"relic": 1},        "produce": {"shield_mod": 1}},
        }.get(self.stype, {})
        for r, a in ti.get("consume", {}).items():
            if r in self.inventory:
                self.inventory[r] = max(0, self.inventory[r] - a)  # потребление
        for r, a in ti.get("produce", {}).items():
            self.inventory[r] = self.inventory.get(r, 0) + a  # производство
        self.update_prices()

    def price_for_player(self, rid, buying, ship):
        """Возвращает цену для игрока с учётом репутации и навыка торговли.

        Args:
            rid: идентификатор ресурса.
            buying: True, если игрок покупает; False, если продаёт.
            ship: объект PlayerShip (для проверки репутации и навыка).

        Returns:
            Кортеж (цена, примечания).
        """
        if rid not in self.prices:
            return 0, ""
        bp, sp = self.prices[rid]
        rep = ship.reputation.get(self.faction, 0)
        notes = []
        if buying:
            price = sp
            if rep > 50:
                price = int(price * 0.9); notes.append("friend -10%")
            elif rep < -20:
                price = int(price * 1.5); notes.append("hostile +50%")
        else:
            price = bp
            if rep > 50:
                price = int(price * 1.1); notes.append("friend +10%")
            elif rep < -20:
                price = int(price * 0.7); notes.append("hostile -30%")
        tb = 1 + ship.skill_trade * 0.02  # модификатор навыка торговли
        price = int(price / tb) if buying else int(price * tb)
        return max(1, price), " ".join(notes)

    def buy_from(self, ship, rid, amount):
        """Станция покупает ресурс у игрока (игрок продаёт).

        Args:
            ship: объект PlayerShip.
            rid: идентификатор ресурса.
            amount: количество.

        Returns:
            Строка с результатом операции.
        """
        info = RESOURCES.get(rid)
        if not info:
            return f"Unknown '{rid}'."
        rep = ship.reputation.get(self.faction, 0)
        if rep < -20 and self.faction != "pirates":
            return f"Trade blocked (rep {rep})."
        if ship.cargo.has(rid) < amount:
            return f"Not enough {info['name']}."
        banned = CONTRABAND.get(self.faction, []) + CONTRABAND.get(self.religion, [])
        if rid in banned and rep >= -20:
            return f"Contraband! Use smuggle."
        price, _ = self.price_for_player(rid, False, ship)
        total = price * amount
        if not ship.cargo.remove(rid, amount):
            return "Cargo error."
        ship.credits += total
        self.inventory[rid] = self.inventory.get(rid, 0) + amount
        return f"Sold {amount} {info['name']} for {total}cr."

    def sell_to(self, ship, rid, amount):
        """Станция продаёт ресурс игроку (игрок покупает).

        Args:
            ship: объект PlayerShip.
            rid: идентификатор ресурса.
            amount: количество.

        Returns:
            Строка с результатом операции.
        """
        info = RESOURCES.get(rid)
        if not info:
            return f"Unknown '{rid}'."
        rep = ship.reputation.get(self.faction, 0)
        if rep < -20 and self.faction != "pirates":
            return f"Trade blocked (rep {rep})."
        if self.inventory.get(rid, 0) < amount:
            return f"Only {self.inventory.get(rid, 0)} {info['name']}."
        price, _ = self.price_for_player(rid, True, ship)
        total = price * amount
        if ship.credits < total:
            return f"Need {total}, have {ship.credits}."
        if not ship.cargo.add(rid, amount):
            return "Cargo full."
        ship.credits -= total
        self.inventory[rid] -= amount
        return f"Bought {amount} {info['name']} for {total}cr."

    def price_summary(self):
        """Возвращает краткое однострочное описание цен на станции.

        Returns:
            Строка с названием, типом, фракцией и первыми 5 ценами.
        """
        parts = []
        for rid in sorted(RESOURCES):
            if self.inventory.get(rid, 0) > 0:
                _, sp = self.prices.get(rid, (0, 0))
                parts.append(f"{rid}:{sp}")
        return f"  {self.name}[{self.stype}] {self.faction}: {','.join(parts[:5])}"

    def buy_all_junk(self, ship):
        """Покупает все сырые ресурсы (raw) из трюма игрока.

        Args:
            ship: объект PlayerShip.

        Returns:
            Кортеж (сообщение, успех).
        """
        total_credits = 0
        sold_items = []
        for rid, amt in list(ship.cargo.items.items()):
            info = RESOURCES.get(rid, {})
            if info.get("cat") == "raw":  # только сырьё
                price, _ = self.price_for_player(rid, False, ship)
                t = price * amt
                if ship.cargo.remove(rid, amt):
                    ship.credits += t
                    total_credits += t
                    sold_items.append(f"{amt}x {info.get('name', rid)}")
                    self.inventory[rid] = self.inventory.get(rid, 0) + amt
        if not sold_items:
            return "No raw resources to sell.", False
        return f"Sold {', '.join(sold_items)} for {total_credits}cr.", True

# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class GameEvent:
    """Игровое событие с названием, описанием и длительностью."""

    def __init__(self, name, description, duration=0):
        """
        Args:
            name: название события.
            description: текстовое описание.
            duration: длительность события в тиках (0 — мгновенное).
        """
        self.name = name  # название события
        self.description = description  # описание события
        self.duration = duration  # длительность в тиках

class NewsEntry:
    """Запись в новостной ленте игры с заголовком, текстом и номером хода."""

    def __init__(self, headline, body, turn=0):
        """
        Args:
            headline: заголовок новости.
            body: тело новости.
            turn: номер хода, когда новость была создана.
        """
        self.headline = headline  # заголовок новости
        self.body = body  # тело новости
        self.turn = turn  # номер хода создания

class Mission:
    """Игровая миссия (доставка, награда, исследование, торговля).

    Содержит тип, цель, награду, дедлайн и статус.
    """

    _id_counter = 0

    def __init__(self, mtype, resource, amount, target_station, reward, ticks=30,
                 title="", description="", giver_station=None):
        """
        Args:
            mtype: тип миссии ("deliver", "bounty", "exploration", "trade").
            resource: идентификатор ресурса для доставки.
            amount: количество для доставки.
            target_station: название целевой станции.
            reward: награда в кредитах.
            ticks: оставшееся время в тиках (дедлайн).
            title: краткое название миссии.
            description: полное описание.
            giver_station: объект Station, выдавшей миссию (или None).
        """
        Mission._id_counter += 1
        self.id = Mission._id_counter  # уникальный идентификатор миссии
        self.mtype = mtype  # тип миссии: deliver, bounty, exploration, trade
        self.resource = resource  # ресурс для доставки
        self.amount = amount  # количество для доставки
        self.target_station = target_station  # название целевой станции
        self.reward = reward  # награда в кредитах
        self.ticks = ticks  # оставшееся время (дедлайн)
        self.status = "active"  # статус: active, completed, failed, abandoned
        self.progress = 0  # прогресс выполнения (сколько уже доставлено)
        self.title = title or f"{mtype.title()}: {amount}x {resource}"  # название миссии
        self.description = description or f"Deliver {amount} {resource} to {target_station}."  # описание
        self.giver_station = giver_station  # станция, выдавшая миссию

    def is_expired(self):
        """Проверяет, истёк ли срок миссии.

        Returns:
            True, если время вышло и миссия активна.
        """
        return self.ticks <= 0 and self.status == "active"

    def check_completion(self, ship):
        """Проверяет, выполнены ли условия завершения миссии.

        Args:
            ship: объект PlayerShip (не используется, но может понадобиться для др. типов).

        Returns:
            True, если миссия выполнена.
        """
        if self.status != "active":
            return False
        if self.mtype == "deliver":
            return self.progress >= self.amount  # доставлено достаточно
        return False

# ---------------------------------------------------------------------------
# Galaxy
# ---------------------------------------------------------------------------

class Galaxy:
    """Игровая галактика: карта, объекты, NPC, станции, дипломатия, новости.

    Генерирует звёзды, планеты, станции, чёрные дыры, червоточины, астероиды,
    торговцев и пиратов. Обрабатывает ходы: гравитацию ЧД, радиацию звёзд,
    астероиды, экономику станций, движение NPC.
    """

    def __init__(self, width=WIDTH, height=HEIGHT, seed=None):
        """
        Args:
            width: ширина карты в клетках.
            height: высота карты в клетках.
            seed: сид генерации (если None — случайный).
        """
        self.width = width  # ширина карты
        self.height = height  # высота карты
        self.seed = seed if seed is not None else random.randint(0, 999999)  # сид генерации
        random.seed(self.seed)

        self.tiles = [[TILE_EMPTY for _ in range(width)] for _ in range(height)]  # тайлы карты
        self.objects: dict = {}  # словарь (x,y) -> тип объекта
        self.stations: list[Station] = []  # список станций
        self.traders: list[TraderShip] = []  # список торговцев
        self.pirates: list[PirateShip] = []  # список пиратов
        self.events_queue: list[GameEvent] = []  # очередь событий
        self.global_crisis_ticks = 0  # счётчик глобального кризиса
        self.diplomacy: dict = {}  # дипломатические отношения между фракциями
        self.news: list[NewsEntry] = []  # новостная лента
        self.tick_counter = 0  # счётчик ходов

        self._init_diplomacy()
        self.news.append(NewsEntry("Galaxy News", "A vast galaxy awaits…"))
        self._generate()

        self.black_holes = [p for p, o in self.objects.items() if o == "black_hole"]  # список ЧД
        self.wormholes = [p for p, o in self.objects.items() if o == "wormhole"]  # список червоточин

    def _init_diplomacy(self):
        """Инициализирует начальные дипломатические отношения между фракциями."""
        defaults = {
            "imperium":  {"chaos_cult":"war","xenos_horde":"war","machine_collective":"neutral",
                          "free_traders":"neutral","void_covenant":"war"},
            "chaos_cult": {"imperium":"war","xenos_horde":"war","machine_collective":"war",
                           "free_traders":"neutral","void_covenant":"alliance"},
            "xenos_horde":{"imperium":"war","chaos_cult":"war","machine_collective":"war",
                           "free_traders":"neutral","void_covenant":"war"},
            "machine_collective":{"imperium":"neutral","chaos_cult":"war","xenos_horde":"war",
                                  "free_traders":"neutral","void_covenant":"war"},
            "free_traders":{"imperium":"neutral","chaos_cult":"neutral","xenos_horde":"neutral",
                            "machine_collective":"neutral","void_covenant":"neutral"},
            "void_covenant":{"imperium":"war","chaos_cult":"alliance","xenos_horde":"war",
                             "machine_collective":"war","free_traders":"war"},
        }
        self.diplomacy = {f: dict(d) for f, d in defaults.items()}

    # ---- Generation helpers ----

    def _random_passable(self):
        """Ищет случайную проходимую пустую клетку на карте.

        Returns:
            Кортеж (x, y) с координатами.
        """
        for _ in range(500):
            x, y = random.randint(0, self.width - 1), random.randint(0, self.height - 1)
            if self.tiles[y][x] == TILE_EMPTY and (x, y) not in self.objects:
                return x, y
        return random.randint(0, self.width - 1), random.randint(0, self.height - 1)

    def _random_passable_near(self, obj_type, spread=5):
        """Ищет случайную проходимую клетку рядом с объектами указанного типа.

        Args:
            obj_type: тип объекта (например, "asteroids").
            spread: радиус поиска.

        Returns:
            Кортеж (x, y) с координатами.
        """
        cand = [p for p, o in self.objects.items() if o == obj_type]
        if not cand:
            return self._random_passable()
        cx, cy = random.choice(cand)
        for _ in range(100):
            dx, dy = random.randint(-spread, spread), random.randint(-spread, spread)
            nx, ny = cx + dx, cy + dy
            if (0 <= nx < self.width and 0 <= ny < self.height
                    and self.tiles[ny][nx] == TILE_EMPTY):
                return nx, ny
        return self._random_passable()

    # ---- Generation ----

    def _generate(self):
        """Генерирует карту галактики: звёзды, планеты, станции, ЧД, червоточины, астероиды, NPC."""
        for y in range(self.height):
            for x in range(self.width):
                if random.random() < 0.025:
                    self.tiles[y][x] = TILE_STAR  # звезда
                    self.objects[(x, y)] = "star"
                    if random.random() < 0.2:
                        px, py = self._nearby(x, y)
                        if self.tiles[py][px] == TILE_EMPTY:
                            self.tiles[py][px] = TILE_PLANET  # планета рядом со звездой
                            self.objects[(px, py)] = "planet"
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y][x] == TILE_EMPTY and random.random() < 0.01:
                    self.tiles[y][x] = TILE_STATION  # станция
                    self.objects[(x, y)] = "station"
                    self.stations.append(Station(x, y))
        for _ in range(int(self.width * self.height * 0.0025)):
            x, y = random.randint(0, self.width - 1), random.randint(0, self.height - 1)
            if self.tiles[y][x] == TILE_EMPTY:
                self.tiles[y][x] = TILE_BLACK_HOLE  # чёрная дыра
                self.objects[(x, y)] = "black_hole"
        for _ in range(int(self.width * self.height * 0.0015)):
            x, y = random.randint(0, self.width - 1), random.randint(0, self.height - 1)
            if self.tiles[y][x] == TILE_EMPTY:
                self.tiles[y][x] = TILE_WORMHOLE  # червоточина
                self.objects[(x, y)] = "wormhole"
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y][x] == TILE_EMPTY and random.random() < 0.015:
                    self.tiles[y][x] = TILE_ASTEROIDS  # астероиды
                    self.objects[(x, y)] = "asteroids"
        # Replace generic ships with NPCs
        self.objects = {k: v for k, v in self.objects.items() if v != "ship"}
        # Traders
        if self.stations:
            for _ in range(random.randint(8, 12)):
                x, y = self._random_passable()
                route = random.sample(
                    range(len(self.stations)),
                    min(random.randint(3, 5), len(self.stations)),
                )
                self.traders.append(TraderShip(x, y, route))
        # Pirates
        for _ in range(random.randint(3, 5)):
            x, y = self._random_passable_near("asteroids", 5)
            self.pirates.append(PirateShip(x, y))
        # Generate missions
        for s in self.stations:
            s.gen_missions(self.stations)

    @staticmethod
    def _nearby(x, y, md=2):
        """Возвращает случайную точку рядом с указанными координатами.

        Args:
            x, y: исходные координаты.
            md: максимальное смещение по каждой оси.

        Returns:
            Кортеж (x, y).
        """
        return (
            max(0, min(WIDTH - 1, x + random.randint(-md, md))),
            max(0, min(HEIGHT - 1, y + random.randint(-md, md))),
        )

    # ---- Queries ----

    def get_tile(self, x, y):
        """Возвращает символ тайла по указанным координатам.

        Args:
            x, y: координаты.

        Returns:
            Символ тайла или пробел, если координаты вне карты.
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return " "

    def get_object_info(self, x, y):
        """Возвращает текстовое описание объекта в указанной клетке.

        Args:
            x, y: координаты.

        Returns:
            Строка с описанием (например, "Star", "Station Alpha[imperium]").
        """
        for t in self.traders:
            if t.alive and t.x == x and t.y == y:
                return f"Trader {t.name}[{t.faction}]"
        for p in self.pirates:
            if p.alive and p.x == x and p.y == y:
                return f"Pirate {p.name}[{p.faction}]"
        obj = self.objects.get((x, y))
        if obj:
            n = {"star": "Star", "planet": "Planet", "station": "Station",
                 "black_hole": "Black Hole", "wormhole": "Wormhole",
                 "asteroids": "Asteroids"}.get(obj, obj.title())
            s = self.get_station_at(x, y)
            if s:
                n += f" {s.name}[{s.faction}]"
            return n
        return "Empty"

    def is_passable(self, x, y):
        """Проверяет, проходима ли клетка (не звезда и не чёрная дыра).

        Args:
            x, y: координаты.

        Returns:
            True, если клетка проходима.
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        return self.tiles[y][x] not in (TILE_STAR, TILE_BLACK_HOLE)

    def get_station_at(self, x, y):
        """Находит станцию по координатам.

        Args:
            x, y: координаты.

        Returns:
            Объект Station или None.
        """
        for s in self.stations:
            if s.x == x and s.y == y:
                return s
        return None

    def get_nearest_station(self, x, y, md=1):
        """Находит ближайшую станцию в пределах указанного радиуса.

        Args:
            x, y: координаты.
            md: радиус поиска (Chebyshev).

        Returns:
            Объект Station или None.
        """
        for s in self.stations:
            if max(abs(s.x - x), abs(s.y - y)) <= md:
                return s
        return None

    def get_npc_at(self, x, y):
        """Находит NPC (торговца или пирата) по координатам.

        Args:
            x, y: координаты.

        Returns:
            Объект NPCShip (TraderShip или PirateShip) или None.
        """
        for t in self.traders:
            if t.alive and t.x == x and t.y == y:
                return t
        for p in self.pirates:
            if p.alive and p.x == x and p.y == y:
                return p
        return None

    def get_npc_by_name(self, name):
        """Находит NPC по имени (регистронезависимо).

        Args:
            name: имя NPC.

        Returns:
            Объект NPCShip или None.
        """
        for t in self.traders:
            if t.alive and t.name.lower() == name.lower():
                return t
        for p in self.pirates:
            if p.alive and p.name.lower() == name.lower():
                return p
        return None

    def add_news(self, headline, body):
        """Добавляет запись в новостную ленту.

        Args:
            headline: заголовок.
            body: текст новости.
        """
        self.news.append(NewsEntry(headline, body, self.tick_counter))
        if len(self.news) > 50:
            self.news = self.news[-50:]

    def stations_in_range(self, x, y, r):
        """Возвращает список станций в пределах радиуса от указанной точки.

        Args:
            x, y: координаты центра.
            r: радиус (Chebyshev).

        Returns:
            Список объектов Station.
        """
        return [s for s in self.stations if max(abs(s.x - x), abs(s.y - y)) <= r]

    def get_scannable_objects(self, x, y, radius):
        """Возвращает отсортированные по расстоянию сканируемые объекты вокруг точки.

        Args:
            x, y: координаты центра.
            radius: радиус сканирования.

        Returns:
            Список кортежей (расстояние, описание, объект), отсортированный по расстоянию.
        """
        results = []
        for p in self.pirates:
            if p.alive:
                d = max(abs(p.x - x), abs(p.y - y))
                if d <= radius:
                    results.append((d, f"☠ Pirate {p.name}", p))
        for t in self.traders:
            if t.alive:
                d = max(abs(t.x - x), abs(t.y - y))
                if d <= radius:
                    results.append((d, f"T Trader {t.name}", t))
        for s in self.stations:
            d = max(abs(s.x - x), abs(s.y - y))
            if d <= radius:
                results.append((d, f"◈ Station {s.name}", s))
        results.sort(key=lambda x: x[0])
        return results

    def scan_generate_missions(self, target, scan_type, player_ship):
        """Генерирует скрытую миссию на основе результатов сканирования (с определённой вероятностью).

        Args:
            target: отсканированный объект.
            scan_type: тип сканирования.
            player_ship: объект PlayerShip (не используется, но预留).

        Returns:
            Объект Mission или None.
        """
        if not hasattr(target, "name"):
            return None
        from config import SCAN_SIGNAL_TYPES
        sig_type = random.choice(list(SCAN_SIGNAL_TYPES))
        cfg = SCAN_SIGNAL_TYPES[sig_type]
        if random.random() * 100 > cfg["weight"]:
            return None
        # Generate a title giver string
        giver_label = f"Scan: {cfg['title']} @ {target.name}"
        mission_types = cfg["missions"]
        mt = random.choice(mission_types)
        # Craft a simple mission
        rid = random.choice(list(RESOURCES))
        amt = random.randint(1, 5)
        reward = amt * RESOURCES[rid]["base_price"] * random.randint(3, 6)
        from config import FACTIONS
        target_station_name = target.name if hasattr(target, "name") else "Unknown"
        m = Mission(mt if mt in ("deliver", "bounty") else "deliver",
                     rid, amt, target_station_name, reward, random.randint(20, 40),
                     title=f"{cfg['title']} @ {target.name}",
                     description=f"Discovered via {scan_type} scan of {target.name}.",
                     giver_station=giver_label)
        return m

    def reset_npc_counter(self):
        """Сбрасывает глобальный счётчик идентификаторов NPC (для тестов)."""
        global NPCShip_id_counter
        NPCShip_id_counter = 0

    # ---- World tick ----

    def tick(self, px, py, ps):
        """Выполняет один ход игрового мира: обрабатывает чёрные дыры, радиацию, астероиды, экономику.

        Args:
            px, py: координаты игрока.
            ps: объект PlayerShip.

        Returns:
            Кортеж (новые_координаты_игрока, список_событий, флаг_смерти).
        """
        events = []
        # Black holes
        for bh_x, bh_y in self.black_holes:
            d = max(abs(px - bh_x), abs(py - bh_y))
            if d == 0:
                events.append("Black hole!")
                return px, py, events, True
            if d <= 3:
                dx = 1 if bh_x > px else -1 if bh_x < px else 0
                dy = 1 if bh_y > py else -1 if bh_y < py else 0
                nx, ny = px + dx, py + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    px, py = nx, ny
                    events.append("Gravity pull!")
                    if self.tiles[py][px] == TILE_BLACK_HOLE:
                        events.append("Black hole!")
                        return px, py, events, True
        # Star radiation
        for y in range(max(0, py - 1), min(self.height, py + 2)):
            for x in range(max(0, px - 1), min(self.width, px + 2)):
                if self.tiles[y][x] == TILE_STAR and (x != px or y != py):
                    dmg = 10
                    if hasattr(ps, 'race') and ps.race == "mutant":
                        dmg = int(dmg * 0.5)
                    if not getattr(ps, 'radiation_shield', False):
                        ps.take_damage(dmg)
                        events.append(f"Radiation -{dmg}!")
                        if ps.hull <= 0:
                            return px, py, events, True
        # Asteroids
        if self.tiles[py][px] == TILE_ASTEROIDS and random.random() < 0.3:
            ps.take_damage(5)
            events.append("Asteroid -5!")
            if ps.hull <= 0:
                return px, py, events, True
        # Station economy
        for s in self.stations:
            s.update_economy()
        return px, py, events, False

    # ---- NPC step ----

    def step_npc(self, px, py, ps, out):
        """Выполняет ход всех NPC: движение торговцев, атаки/движение пиратов.

        Args:
            px, py: координаты игрока.
            ps: объект PlayerShip (не используется напрямую).
            out: список строк для записи событий NPC.
        """
        for t in self.traders:
            if not t.alive:
                continue
            tg = t.current_target(self.stations)
            if not tg:
                continue
            if t.x == tg.x and t.y == tg.y:
                t.wait_ticks = random.randint(2, 5) if t.wait_ticks <= 0 else t.wait_ticks - 1
                if t.wait_ticks <= 0:
                    t.route_index += 1
                continue
            self._move_towards(t, tg.x, tg.y)
            if max(abs(t.x - px), abs(t.y - py)) <= 1:
                out.append(f"Trader {t.name} nearby.")
        for p in self.pirates:
            if not p.alive:
                continue
            targets = []
            if max(abs(p.x - px), abs(p.y - py)) <= p.aggro_range:
                targets.append((px, py, "player"))
            for t in self.traders:
                if t.alive and max(abs(p.x - t.x), abs(p.y - t.y)) <= p.aggro_range:
                    targets.append((t.x, t.y, "trader"))
            if targets:
                tx, ty, tt = min(targets, key=lambda c: max(abs(p.x - c[0]), abs(p.y - c[1])))
                if max(abs(p.x - tx), abs(p.y - ty)) == 1:
                    if tt == "player":
                        out.append(f"__BATTLE__:{p.uid}")
                    else:
                        for t2 in self.traders:
                            if t2.alive and t2.x == tx and t2.y == ty:
                                t2.take_damage(15)
                                out.append(f"Pirate attacks {t2.name}!")
                                if not t2.alive:
                                    out.append(f"{t2.name} destroyed.")
                                break
                else:
                    self._move_towards(p, tx, ty)
            elif random.random() < 0.3:
                self._random_move(p)
            if p.hull <= p.flee_threshold:
                dx = px - p.x
                fx = p.x - (1 if dx > 0 else -1 if dx < 0 else 0)
                if self.is_passable(fx, p.y):
                    p.x = fx

    def _move_towards(self, npc, tx, ty):
        """Перемещает NPC на один шаг по направлению к целевой точке.

        Args:
            npc: объект NPC.
            tx, ty: целевые координаты.
        """
        dx = 1 if tx > npc.x else -1 if tx < npc.x else 0
        dy = 1 if ty > npc.y else -1 if ty < npc.y else 0
        if dx != 0 and self.is_passable(npc.x + dx, npc.y) and not self._occupied(npc.x + dx, npc.y):
            npc.x += dx
        elif dy != 0 and self.is_passable(npc.x, npc.y + dy) and not self._occupied(npc.x, npc.y + dy):
            npc.y += dy
        else:
            self._random_move(npc)

    def _random_move(self, npc):
        """Перемещает NPC на один шаг в случайном направлении.

        Args:
            npc: объект NPC.
        """
        for dx, dy in random.sample([(1, 0), (-1, 0), (0, 1), (0, -1)], 4):
            nx, ny = npc.x + dx, npc.y + dy
            if self.is_passable(nx, ny) and not self._occupied(nx, ny):
                npc.x, npc.y = nx, ny
                return

    def _occupied(self, x, y):
        """Проверяет, занята ли клетка другим NPC.

        Args:
            x, y: координаты.

        Returns:
            True, если клетка занята живым NPC.
        """
        for t in self.traders:
            if t.alive and t.x == x and t.y == y:
                return True
        for p in self.pirates:
            if p.alive and p.x == x and p.y == y:
                return True
        return (x, y) in self.objects


# ═══════════════════════════════════════════════════════════════════
# Factory functions for quick battle / debug mode
# ═══════════════════════════════════════════════════════════════════

# Модули, сгруппированные по типу отсека
_MODULES_BY_COMP = {}
for _mid, _minfo in SHIP_MODULES.items():
    _MODULES_BY_COMP.setdefault(_minfo["comp"], []).append(_mid)

# Отсеки, которые могут быть пустыми (не критичны для старта)
_OPTIONAL_COMPS = {"life_support", "cargo"}


def _assign_crew_to_ship(ship, count=2):
    """Создаёт и назначает случайный экипаж на корабль."""
    specs = list(CREW_SPECIALTIES)
    posts = list(ship.crew.keys())
    for _ in range(count):
        name = random.choice(CREW_NAMES) + str(random.randint(1, 99))
        spec = random.choice(specs)
        cm = CrewMember(name, spec)
        cm.level = random.choices([1, 2], weights=[70, 30])[0]
        # Поднять бонусы под уровень
        if cm.level > 1:
            for k in cm.bonus:
                cm.bonus[k] = int(cm.bonus[k] * (1 + (cm.level - 1) * 0.15))
        ship.crew_members.append(cm)
        # Назначить на подходящий пост, если свободен
        spec_posts = CREW_SPECIALTIES.get(spec, {}).get("posts", [])
        for p in spec_posts:
            if p in ship.crew and ship.crew[p] is None:
                ship.crew[p] = cm.name
                cm.assigned = True
                break


def _fill_ship_compartments(ship, hull_cfg):
    """Заполняет отсеки корабля случайными модулями.

    Устанавливает по 1 модулю в каждый доступный отсек.
    Для реактора, двигателя, щита и сенсора — всегда ставит модуль.
    Для оружия — 1 оружие (если отсек активен).
    Для опциональных отсеков (cargo, life_support) — с шансом 50%.
    """
    num_comps = hull_cfg.get("compartments", 5)
    priority = ["reactor", "engine", "shield", "sensor", "weapon",
                "cargo", "life_support"]
    active = set(priority[:num_comps])

    # Очищаем стартовые модули (которые поставил __init__)
    for c in COMPARTMENTS:
        ship.compartments[c]["modules"] = []

    required = {"reactor", "engine", "shield", "sensor", "weapon"}
    for comp in COMPARTMENTS:
        if comp not in active:
            continue
        # Опциональные отсеки — 50% шанс
        if comp in _OPTIONAL_COMPS and random.random() < 0.5:
            continue
        pool = _MODULES_BY_COMP.get(comp, [])
        if not pool:
            continue
        # Случайный модуль, предпочтение 1-2 level, малый шанс mk2
        mod_id = random.choice(pool)
        level = random.choices([1, 2], weights=[60, 40])[0]
        mod = ShipModule(mod_id, level=level)
        ship.compartments[comp]["modules"].append(mod)
        # Если это оружие, можно добавить второе для активного weapon-отсека
        if comp == "weapon" and random.random() < 0.4 and len(pool) > 1:
            mod_id2 = random.choice([m for m in pool if m != mod_id])
            level2 = random.choices([1, 2], weights=[60, 40])[0]
            ship.compartments[comp]["modules"].append(ShipModule(mod_id2, level=level2))


def create_random_ship(is_player=True):
    """Создаёт полностью укомплектованный случайный корабль для быстрого боя.

    Параметры:
        is_player: True — создать PlayerShip; False — создать корабль-противника.

    Возвращает:
        PlayerShip со случайным корпусом, модулями, экипажем и грузом.
    """
    # Выбираем случайный корпус (исключая shuttle)
    hull_ids = [k for k in SHIP_HULLS if k != "shuttle"]
    hull_id = random.choice(hull_ids)
    hull_cfg = SHIP_HULLS[hull_id]

    # Создаём корабль с этим корпусом
    ship = PlayerShip(
        name=f"{(hull_cfg['name'])}-{random.randint(100,999)}",
        hull=hull_cfg["hull"],
    )
    ship.hull_id = hull_id
    ship.max_hull = hull_cfg["hull"]
    ship.name = f"{(hull_cfg['name'])}-{random.randint(100,999)}"

    # Пересоздаём отсеки под этот корпус
    ship._init_compartments(hull_cfg)

    # Заполняем случайными модулями
    _fill_ship_compartments(ship, hull_cfg)

    # Экипаж
    crew_count = random.randint(2, 3)
    _assign_crew_to_ship(ship, crew_count)

    # Груз: расходники
    ship.cargo.add("repair_kit", random.randint(2, 3))
    ship.cargo.add("fuel_cell", random.randint(2, 3))
    ship.cargo.add("shield_booster", random.randint(0, 1))

    # Энергия по умолчанию
    stats = ship.get_effective_stats()
    ship.shield_hp = max(20, stats.get("shield_cap", 20))

    # alive для совместимости с NPCShip (враг проверяет .alive)
    ship.alive = True

    return ship


def create_random_enemy():
    """Создаёт случайного противника для быстрого боя.

    Использует PlayerShip как базу, чтобы у противника были
    полноценные отсеки с модулями. Возвращаемый объект совместим
    с BattleController (имеет hull, shield_hp, .alive, take_damage).

    Возвращает:
        PlayerShip с пониженным на ~15% качеством модулей.
    """
    hull_ids = [k for k in SHIP_HULLS if k != "shuttle"]
    # Противник может быть на корпус проще
    hull_id = random.choice(hull_ids[:min(3, len(hull_ids))])
    hull_cfg = SHIP_HULLS[hull_id]

    ship = PlayerShip(
        name=f"Enemy-{random.choice(['Raider','Reaver','Corsair'])}{random.randint(1,99)}",
        hull=hull_cfg["hull"],
    )
    ship.hull_id = hull_id
    ship.max_hull = hull_cfg["hull"]
    ship._init_compartments(hull_cfg)

    # Заполняем модулями, но чуть слабее
    _fill_ship_compartments(ship, hull_cfg)

    # Противник без экипажа или с одним (меньше бонусов)
    if random.random() < 0.5:
        _assign_crew_to_ship(ship, 1)

    # Минимальный груз
    ship.cargo.add("repair_kit", random.randint(0, 1))

    stats = ship.get_effective_stats()
    ship.shield_hp = max(15, stats.get("shield_cap", 15))
    ship.alive = True

    return ship
