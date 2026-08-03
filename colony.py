"""
colony.py — Система колонизации и строительства баз на планетах.

Содержит классы:
  - PlanetType — перечисление типов планет
  - BuildingDef — определение здания (конфигурация)
  - ResourceNode — ресурсная жила на поверхности планеты
  - Building — построенное здание
  - ColonyManager — ядро колонии (здания, ресурсы, население, энергия)

Каждая планета в галактике может иметь ссылку ColonyManager.
Колония создаётся через Colony Starter Kit (ресурс "colony_starter").
В будущем: конвейеры, дроны, скриптинг логистики (задел через
input/output буферы у Building).
"""

from __future__ import annotations
import random
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════
# Planet types
# ═══════════════════════════════════════════════════════════════════════════

PLANET_TYPES = {
    "desert": {
        "name": "Desert",
        "habitability": 30,
        "danger": 40,
        "resources": {"ore": (50, 200), "silicon": (30, 150)},
        "water": False,
        "energy_bonus": {"solar": 50},
        "building_bonus": {},
    },
    "ice": {
        "name": "Ice",
        "habitability": 20,
        "danger": 50,
        "resources": {"ice": (80, 300), "silicon": (20, 100)},
        "water": True,
        "energy_bonus": {"geothermal": 20},
        "building_bonus": {},
    },
    "volcanic": {
        "name": "Volcanic",
        "habitability": 10,
        "danger": 70,
        "resources": {"ore": (80, 250), "metal": (20, 80)},
        "water": False,
        "energy_bonus": {"geothermal": 60},
        "building_bonus": {},
    },
    "temperate": {
        "name": "Temperate",
        "habitability": 80,
        "danger": 20,
        "resources": {"ore": (30, 120), "silicon": (20, 100), "ice": (30, 100)},
        "water": True,
        "energy_bonus": {"solar": 20, "geothermal": 10},
        "building_bonus": {"farm": 30},
    },
    "gas_giant": {
        "name": "Gas Giant",
        "habitability": 0,
        "danger": 90,
        "resources": {"fuel_cell": (40, 150)},
        "water": False,
        "energy_bonus": {"fusion": 40},
        "building_bonus": {},
        "orbit_only": True,
    },
}


def random_planet_type() -> str:
    """Возвращает случайный тип планеты с весами."""
    weights = {"desert": 25, "ice": 20, "volcanic": 15, "temperate": 30, "gas_giant": 10}
    types = list(weights.keys())
    w = [weights[t] for t in types]
    return random.choices(types, weights=w, k=1)[0]


# ═══════════════════════════════════════════════════════════════════════════
# Resource node — жила на поверхности планеты
# ═══════════════════════════════════════════════════════════════════════════

class ResourceNode:
    """Ресурсная жила на поверхности планеты.

    Attributes:
        resource_id: идентификатор ресурса (напр. "ore", "ice").
        remaining: оставшийся запас.
        total: начальный запас.
        x, y: координаты на карте поверхности.
    """

    def __init__(self, resource_id: str, amount: int, x: int = 0, y: int = 0):
        self.resource_id = resource_id
        self.remaining = amount
        self.total = amount
        self.x = x
        self.y = y

    @property
    def depleted(self) -> bool:
        return self.remaining <= 0

    def extract(self, amount: int) -> int:
        """Добывает ресурс из жилы, возвращает реально добытое кол-во."""
        taken = min(amount, self.remaining)
        self.remaining -= taken
        return taken


# ═══════════════════════════════════════════════════════════════════════════
# Building definition
# ═══════════════════════════════════════════════════════════════════════════

BUILDING_DEFS: dict[str, dict] = {
    "command_center": {
        "name": "Command Center",
        "category": "infrastructure",
        "cost": {"metal": 5, "electronics": 3},
        "build_time": 1,
        "size": 2,
        "power_consumption": 0,
        "workers": 0,
        "storage": 50,
        "max_buildings_bonus": 5,
        "max_population_bonus": 0,
        "production": {},
        "input_slots": [],
        "output_slots": [],
        "desc": "Сердце базы. Определяет лимит зданий.",
        "upgradeable": True,
        "upgrade_cost_mult": 1.5,
    },
    "habitat": {
        "name": "Habitat Module",
        "category": "infrastructure",
        "cost": {"metal": 3, "electronics": 1, "silicon": 1},
        "build_time": 2,
        "size": 1,
        "power_consumption": 1,
        "workers": 0,
        "storage": 0,
        "max_buildings_bonus": 0,
        "max_population_bonus": 10,
        "production": {},
        "input_slots": [],
        "output_slots": [],
        "desc": "Жилой модуль — увеличивает лимит колонистов.",
        "upgradeable": True,
        "upgrade_cost_mult": 1.4,
    },
    "power_plant_solar": {
        "name": "Solar Plant",
        "category": "power",
        "cost": {"metal": 4, "silicon": 3, "electronics": 1},
        "build_time": 2,
        "size": 2,
        "power_consumption": -15,
        "workers": 1,
        "storage": 0,
        "max_buildings_bonus": 0,
        "max_population_bonus": 0,
        "production": {},
        "input_slots": [],
        "output_slots": [],
        "desc": "Солнечная электростанция. Эффективность зависит от типа планеты.",
        "upgradeable": True,
        "upgrade_cost_mult": 1.5,
    },
    "power_plant_geothermal": {
        "name": "Geothermal Plant",
        "category": "power",
        "cost": {"metal": 5, "electronics": 2},
        "build_time": 3,
        "size": 2,
        "power_consumption": -20,
        "workers": 2,
        "storage": 0,
        "max_buildings_bonus": 0,
        "max_population_bonus": 0,
        "production": {},
        "input_slots": [],
        "output_slots": [],
        "desc": "Геотермальная станция. Работает на вулканических и ледяных планетах.",
        "upgradeable": True,
        "upgrade_cost_mult": 1.5,
    },
    "mine": {
        "name": "Mine",
        "category": "production",
        "cost": {"metal": 3, "electronics": 1},
        "build_time": 2,
        "size": 1,
        "power_consumption": 2,
        "workers": 3,
        "storage": 0,
        "max_buildings_bonus": 0,
        "max_population_bonus": 0,
        "production": {},
        "input_slots": [],
        "output_slots": [("ore", 5)],
        "desc": "Шахта — добывает руду из жилы. Должна стоять рядом с жилой.",
        "upgradeable": True,
        "upgrade_cost_mult": 1.4,
    },
    "water_purifier": {
        "name": "Water Purifier",
        "category": "production",
        "cost": {"metal": 2, "electronics": 2, "silicon": 1},
        "build_time": 2,
        "size": 1,
        "power_consumption": 2,
        "workers": 2,
        "storage": 0,
        "max_buildings_bonus": 0,
        "max_population_bonus": 0,
        "production": {},
        "input_slots": [],
        "output_slots": [("ice", 3)],
        "desc": "Очиститель — добывает воду/лёд из водного источника.",
        "upgradeable": True,
        "upgrade_cost_mult": 1.4,
    },
    "smelter": {
        "name": "Smelter",
        "category": "production",
        "cost": {"metal": 4, "electronics": 2, "silicon": 1},
        "build_time": 3,
        "size": 2,
        "power_consumption": 4,
        "workers": 2,
        "storage": 0,
        "max_buildings_bonus": 0,
        "max_population_bonus": 0,
        "production": {},
        "input_slots": [("ore", 3)],
        "output_slots": [("metal", 2)],
        "desc": "Плавильня — перерабатывает руду в металл.",
        "upgradeable": True,
        "upgrade_cost_mult": 1.5,
    },
    "factory": {
        "name": "Factory",
        "category": "production",
        "cost": {"metal": 6, "electronics": 4, "silicon": 2},
        "build_time": 4,
        "size": 3,
        "power_consumption": 6,
        "workers": 3,
        "storage": 0,
        "max_buildings_bonus": 0,
        "max_population_bonus": 0,
        "production": {},
        "input_slots": [("metal", 2)],
        "output_slots": [("electronics", 1)],
        "desc": "Фабрика — производит электронику и компоненты.",
        "upgradeable": True,
        "upgrade_cost_mult": 1.6,
    },
    "warehouse": {
        "name": "Warehouse",
        "category": "storage",
        "cost": {"metal": 3},
        "build_time": 1,
        "size": 1,
        "power_consumption": 0,
        "workers": 0,
        "storage": 100,
        "max_buildings_bonus": 0,
        "max_population_bonus": 0,
        "production": {},
        "input_slots": [],
        "output_slots": [],
        "desc": "Склад — увеличивает ёмкость хранилища базы.",
        "upgradeable": True,
        "upgrade_cost_mult": 1.3,
    },
    "lab": {
        "name": "Laboratory",
        "category": "research",
        "cost": {"metal": 3, "electronics": 5, "silicon": 2},
        "build_time": 4,
        "size": 2,
        "power_consumption": 4,
        "workers": 2,
        "storage": 0,
        "max_buildings_bonus": 0,
        "max_population_bonus": 0,
        "production": {},
        "input_slots": [],
        "output_slots": [],
        "desc": "Лаборатория — исследует технологии колонии.",
        "upgradeable": True,
        "upgrade_cost_mult": 1.6,
    },
    "turret": {
        "name": "Defense Turret",
        "category": "defense",
        "cost": {"metal": 3, "electronics": 2},
        "build_time": 2,
        "size": 1,
        "power_consumption": 2,
        "workers": 0,
        "storage": 0,
        "max_buildings_bonus": 0,
        "max_population_bonus": 0,
        "production": {},
        "input_slots": [],
        "output_slots": [],
        "desc": "Оборонная турель — защищает базу от рейдов.",
        "upgradeable": False,
        "upgrade_cost_mult": 1.0,
    },
    "spaceport": {
        "name": "Spaceport",
        "category": "infrastructure",
        "cost": {"metal": 8, "electronics": 5, "silicon": 3},
        "build_time": 5,
        "size": 3,
        "power_consumption": 3,
        "workers": 2,
        "storage": 0,
        "max_buildings_bonus": 0,
        "max_population_bonus": 0,
        "production": {},
        "input_slots": [],
        "output_slots": [],
        "desc": "Космопорт — торговля с орбиты, стыковка корабля.",
        "upgradeable": True,
        "upgrade_cost_mult": 1.5,
    },
}


def get_building_def(building_id: str) -> dict:
    """Возвращает конфигурацию здания или пустой словарь."""
    return BUILDING_DEFS.get(building_id, {})


# ═══════════════════════════════════════════════════════════════════════════
# Surface tile types for colony map
# ═══════════════════════════════════════════════════════════════════════════

SURFACE_TILES = {
    "plain": {"ch": ".", "passable": True, "name": "Plain", "buildable": True},
    "hills": {"ch": "^", "passable": True, "name": "Hills", "buildable": True},
    "water": {"ch": "~", "passable": False, "name": "Water", "buildable": False},
    "lava": {"ch": "≈", "passable": False, "name": "Lava", "buildable": False},
    "resource_vein": {"ch": "*", "passable": True, "name": "Resource Vein", "buildable": False},
    "building": {"ch": "█", "passable": False, "name": "Building", "buildable": False},
    "void": {"ch": " ", "passable": False, "name": "Void", "buildable": False},
}

SURFACE_SIZE = 30  # размер карты поверхности 30x30


# ═══════════════════════════════════════════════════════════════════════════
# Building — экземпляр здания в колонии
# ═══════════════════════════════════════════════════════════════════════════

class Building:
    """Построенное здание в колонии.

    Attributes:
        building_id: идентификатор типа здания.
        x, y: позиция на карте поверхности (верхний левый угол).
        level: уровень здания.
        active: работает ли здание.
        input_buffer: dict[resource_id, amount] — для будущих конвейеров.
        output_buffer: dict[resource_id, amount] — для будущих конвейеров.
        build_progress: прогресс строительства (0..1).
    """

    def __init__(self, building_id: str, x: int = 0, y: int = 0):
        self.building_id = building_id
        self.x = x
        self.y = y
        self.level = 1
        self.active = True
        self.build_progress = 1.0  # 1.0 = построено
        # Буферы для будущей автоматизации (конвейеры/дроны)
        self.input_buffer: dict[str, int] = {}
        self.output_buffer: dict[str, int] = {}

    @property
    def defn(self) -> dict:
        return get_building_def(self.building_id)

    @property
    def name(self) -> str:
        return self.defn.get("name", self.building_id)

    @property
    def power_consumption(self) -> int:
        base = self.defn.get("power_consumption", 0)
        multiplier = 1.0 + (self.level - 1) * 0.15
        return int(base * multiplier)

    @property
    def workers_required(self) -> int:
        base = self.defn.get("workers", 0)
        multiplier = 1.0 + (self.level - 1) * 0.10
        return int(base * multiplier)

    @property
    def size(self) -> int:
        return self.defn.get("size", 1)

    @property
    def upgradeable(self) -> bool:
        return self.defn.get("upgradeable", False)

    def can_upgrade(self) -> bool:
        return self.upgradeable and self.level < 5

    def upgrade_cost(self) -> dict[str, int]:
        """Возвращает стоимость улучшения здания."""
        base = self.defn.get("cost", {})
        mult = self.defn.get("upgrade_cost_mult", 1.5) ** (self.level - 1)
        return {k: max(1, int(v * mult)) for k, v in base.items()}

    def get_input_slots(self) -> list[tuple[str, int]]:
        """Возвращает слоты входа (resource_id, amount_per_tick) — для автоматизации."""
        return self.defn.get("input_slots", [])

    def get_output_slots(self) -> list[tuple[str, int]]:
        """Возвращает слоты выхода (resource_id, amount_per_tick) — для автоматизации."""
        slots = self.defn.get("output_slots", [])
        # Масштабируем с уровнем
        return [(rid, int(amt * (1.0 + (self.level - 1) * 0.20))) for rid, amt in slots]

    def __repr__(self) -> str:
        return f"<Building {self.name} Lv{self.level} ({self.x},{self.y})>"


# ═══════════════════════════════════════════════════════════════════════════
# ColonyManager — ядро колонии
# ═══════════════════════════════════════════════════════════════════════════

class ColonyManager:
    """Управляет колонией на планете.

    Хранит здания, ресурсы, население, энергосеть.
    Вызывается в каждом тике галактики для обновления производства.

    Attributes:
        name: название колонии.
        planet_type: тип планеты (ключ из PLANET_TYPES).
        buildings: список зданий.
        storage: dict[resource_id, amount] — локальное хранилище.
        max_storage: максимальная ёмкость хранилища.
        colonists: количество колонистов.
        max_colonists: лимит колонистов.
        power_produced: сколько энергии генерируется.
        power_consumed: сколько энергии потребляется.
        resource_nodes: список ResourceNode на поверхности.
        surface: 2D список тайлов поверхности (str).
        happiness: уровень счастья 0..100.
    """

    def __init__(self, name: str, planet_type: str):
        self.name = name
        self.planet_type = planet_type
        self.planet_info = PLANET_TYPES.get(planet_type, PLANET_TYPES["temperate"])

        self.buildings: list[Building] = []
        self.storage: dict[str, int] = {}
        self.max_storage = 50  # начальная ёмкость (командный центр даёт +)

        self.colonists = 0
        self.max_colonists = 0
        self.happiness = 70  # начальное счастье

        self.power_produced = 0
        self.power_consumed = 0

        self.resource_nodes: list[ResourceNode] = []
        self.surface: list[list[str]] = []

        self._init_surface()
        self._init_resource_nodes()

    def _init_surface(self):
        """Генерирует карту поверхности планеты."""
        self.surface = []
        for y in range(SURFACE_SIZE):
            row = []
            for x in range(SURFACE_SIZE):
                r = random.random()
                if r < 0.7:
                    tile = "plain"
                elif r < 0.85:
                    tile = "hills"
                elif r < 0.93:
                    tile = "water" if self.planet_info.get("water") else "hills"
                else:
                    tile = "plain"
                row.append(tile)
            self.surface.append(row)

    def _init_resource_nodes(self):
        """Размещает ресурсные жилы на карте согласно типу планеты."""
        resources = self.planet_info.get("resources", {})
        for rid, (min_amt, max_amt) in resources.items():
            count = random.randint(2, 5)
            for _ in range(count):
                x = random.randint(1, SURFACE_SIZE - 2)
                y = random.randint(1, SURFACE_SIZE - 2)
                if self.surface[y][x] in ("plain", "hills"):
                    amt = random.randint(min_amt, max_amt)
                    self.resource_nodes.append(ResourceNode(rid, amt, x, y))
                    self.surface[y][x] = "resource_vein"

    # ── Building management ──

    def max_buildings_allowed(self) -> int:
        """Сколько зданий можно построить (от командного центра)."""
        total = 0
        for b in self.buildings:
            if b.building_id == "command_center":
                total += b.defn.get("max_buildings_bonus", 5)
            total += b.defn.get("max_buildings_bonus", 0)
        return max(3, total)

    def can_place_building(self, building_id: str, x: int, y: int) -> tuple[bool, str]:
        """Проверяет, можно ли разместить здание в (x, y).

        Returns:
            (True, "") или (False, причина).
        """
        bdef = get_building_def(building_id)
        if not bdef:
            return False, f"Unknown building '{building_id}'."

        size = bdef.get("size", 1)
        # Проверка границ
        if x < 0 or y < 0 or x + size > SURFACE_SIZE or y + size > SURFACE_SIZE:
            return False, "Out of bounds."

        # Проверка свободной территории
        for dy in range(size):
            for dx in range(size):
                tile = self.surface[y + dy][x + dx]
                tile_info = SURFACE_TILES.get(tile, {})
                if not tile_info.get("buildable", False):
                    return False, f"Tile ({x+dx},{y+dy}) is '{tile_info.get('name', tile)}' — can't build."
        # Проверка пересечения с другими зданиями
        for b in self.buildings:
            if (b.x < x + size and b.x + b.size > x and
                    b.y < y + size and b.y + b.size > y):
                return False, "Overlaps with existing building."

        # Проверка лимита зданий
        if len(self.buildings) >= self.max_buildings_allowed():
            return False, f"Building limit reached ({self.max_buildings_allowed()}). Build more Command Centers."

        return True, ""

    def place_building(self, building_id: str, x: int, y: int) -> bool:
        """Размещает здание на карте. Возвращает True при успехе."""
        ok, reason = self.can_place_building(building_id, x, y)
        if not ok:
            return False

        b = Building(building_id, x, y)
        self.buildings.append(b)

        # Отмечаем тайлы
        size = b.size
        for dy in range(size):
            for dx in range(size):
                self.surface[y + dy][x + dx] = "building"

        # Применяем бонусы командного центра
        if building_id == "command_center":
            self.max_storage += b.defn.get("storage", 50)
            self.max_colonists += b.defn.get("max_population_bonus", 0)
        elif building_id == "warehouse":
            self.max_storage += b.defn.get("storage", 100)
        elif building_id == "habitat":
            self.max_colonists += b.defn.get("max_population_bonus", 10)

        return True

    def remove_building(self, x: int, y: int) -> bool:
        """Удаляет здание по координатам."""
        for i, b in enumerate(self.buildings):
            if b.x == x and b.y == y:
                # Очищаем тайлы
                size = b.size
                for dy in range(size):
                    for dx in range(size):
                        self.surface[b.y + dy][b.x + dx] = "plain"
                self.buildings.pop(i)
                return True
        return False

    def get_building_at(self, x: int, y: int) -> Optional[Building]:
        """Находит здание по координатам."""
        for b in self.buildings:
            if b.x <= x < b.x + b.size and b.y <= y < b.y + b.size:
                return b
        return None

    def get_resource_node_at(self, x: int, y: int) -> Optional[ResourceNode]:
        """Находит ресурсную жилу по координатам."""
        for rn in self.resource_nodes:
            if rn.x == x and rn.y == y:
                return rn
        return None

    # ── Tick — производство, потребление, энергия ──

    def tick(self) -> list[str]:
        """Обрабатывает один тик колонии.

        Returns:
            Список сообщений о событиях за тик.
        """
        events: list[str] = []

        # 1. Энергия
        self._update_power()

        # 2. Производство
        if self.power_produced >= self.power_consumed:
            efficiency = 1.0
        elif self.power_produced > 0:
            efficiency = self.power_produced / max(1, self.power_consumed)
        else:
            efficiency = 0.0

        if efficiency < 1.0:
            events.append(f"Power shortage! Efficiency: {int(efficiency * 100)}%")

        # 3. Работа зданий
        assigned = sum(1 for b in self.buildings if b.active and b.workers_required > 0)
        available_workers = self.colonists
        for b in self.buildings:
            # Активность пересчитывается КАЖДЫЙ тик: здание, отключённое за
            # нехватку рабочих/ресурсов, снова включается, когда условия
            # восстановились (раньше b.active=False оставалось навсегда).
            if b.workers_required > 0 and available_workers < b.workers_required:
                if b.active:
                    b.active = False
                    events.append(f"{b.name} stopped — not enough workers.")
                continue
            if b.workers_required > 0:
                available_workers -= b.workers_required
            b.active = True

            # Производство с учётом эффективности
            prod_efficiency = efficiency
            if b.workers_required > 0:
                # Влияние счастья (0.5..1.0)
                happiness_mod = 0.5 + self.happiness / 200.0
                prod_efficiency *= happiness_mod

            self._process_building_production(b, prod_efficiency, events)

        # 4. Регенерация счастья
        if self.colonists > 0:
            # Базовая потребность в жилье
            housing_ratio = self.max_colonists / max(1, self.colonists * 2)
            if housing_ratio > 1.0:
                self.happiness = min(100, self.happiness + 1)
            else:
                self.happiness = max(10, self.happiness - 1)

        return events

    def _update_power(self):
        """Пересчитывает производство и потребление энергии."""
        produced = 0
        consumed = 0

        for b in self.buildings:
            if not b.active:
                continue
            pwr = b.power_consumption
            if pwr < 0:
                # Генерация энергии с планетарным бонусом
                base = abs(pwr)
                ptype = b.building_id
                energy_bonus = self.planet_info.get("energy_bonus", {})
                if ptype in ("power_plant_solar", "power_plant_geothermal"):
                    key = "solar" if "solar" in ptype else "geothermal"
                    bonus_pct = energy_bonus.get(key, 0)
                    base = int(base * (1.0 + bonus_pct / 100.0))
                produced += base
            else:
                consumed += pwr

        self.power_produced = produced
        self.power_consumed = consumed

    def _process_building_production(self, b: Building, efficiency: float, events: list[str]):
        """Обрабатывает производство одного здания за тик."""
        # Проверяем ресурсы на входе
        for rid, amt in b.get_input_slots():
            needed = int(amt * efficiency)
            if needed <= 0:
                continue
            available = self.storage.get(rid, 0)
            if available < needed:
                b.active = False
                events.append(f"{b.name} — not enough {rid} (need {needed}, have {available}).")
                return
            self.storage[rid] = available - needed

        # Производим ресурсы на выходе. Шахта и очиститель воды имеют
        # собственную логику ниже (жила/вода) и НЕ должны давать ресурсы
        # «из воздуха» через общий путь — иначе производство задваивается.
        if b.building_id not in ("mine", "water_purifier"):
            for rid, amt in b.get_output_slots():
                produced = int(amt * efficiency)
                if produced <= 0:
                    continue
                self._add_to_storage(rid, produced)
                if produced > 0 and efficiency >= 1.0:
                    events.append(f"{b.name} produced {produced} {rid}.")

        # Специальная обработка: шахта добывает из жилы
        if b.building_id == "mine":
            node = self._find_nearest_node("ore", b.x, b.y)
            if node and not node.depleted:
                base_rate = 3 + b.level * 2
                extracted = node.extract(int(base_rate * efficiency))
                if extracted > 0:
                    self._add_to_storage("ore", extracted)
                    events.append(f"{b.name} mined {extracted} ore.")
                if node.depleted:
                    events.append(f"Resource vein depleted at ({node.x},{node.y})!")
            else:
                events.append(f"{b.name} — no ore vein nearby.")

        if b.building_id == "water_purifier":
            has_water = self.planet_info.get("water", False)
            if has_water:
                base_rate = 2 + b.level
                produced = int(base_rate * efficiency)
                if produced > 0:
                    self._add_to_storage("ice", produced)
                    events.append(f"{b.name} produced {produced} ice.")

    def _find_nearest_node(self, resource_id: str, bx: int, by: int, radius: int = 5) -> Optional[ResourceNode]:
        """Ищет ближайшую жилу заданного ресурса рядом с позицией."""
        best = None
        best_dist = 999
        for rn in self.resource_nodes:
            if rn.resource_id != resource_id:
                continue
            dist = max(abs(rn.x - bx), abs(rn.y - by))
            if dist <= radius and dist < best_dist:
                best = rn
                best_dist = dist
        return best

    def _add_to_storage(self, resource_id: str, amount: int):
        """Добавляет ресурс в хранилище с учётом лимита."""
        current = self.storage.get(resource_id, 0)
        free_space = self.max_storage - sum(self.storage.values())
        if free_space <= 0:
            return
        actual = min(amount, free_space)
        if actual > 0:
            self.storage[resource_id] = current + actual

    # ── Resource transfer with ship ──

    def transfer_to_ship(self, resource_id: str, amount: int, ship_cargo) -> int:
        """Перемещает ресурс из хранилища колонии на корабль.

        Returns:
            Реально перемещённое количество.
        """
        available = self.storage.get(resource_id, 0)
        to_move = min(amount, available)
        if to_move <= 0:
            return 0
        self.storage[resource_id] = available - to_move
        if self.storage[resource_id] <= 0:
            del self.storage[resource_id]
        ship_cargo.add(resource_id, to_move)
        return to_move

    def transfer_from_ship(self, resource_id: str, amount: int, ship_cargo) -> int:
        """Перемещает ресурс с корабля в хранилище колонии.

        Returns:
            Реально перемещённое количество.
        """
        available = ship_cargo.has(resource_id)
        to_move = min(amount, available)
        if to_move <= 0:
            return 0
        ship_cargo.remove(resource_id, to_move)
        self._add_to_storage(resource_id, to_move)
        return to_move

    # ── Summary ──

    def summary(self) -> dict:
        """Возвращает сводку состояния колонии."""
        return {
            "name": self.name,
            "planet_type": self.planet_info.get("name", self.planet_type),
            "buildings": len(self.buildings),
            "max_buildings": self.max_buildings_allowed(),
            "storage_used": sum(self.storage.values()),
            "max_storage": self.max_storage,
            "colonists": self.colonists,
            "max_colonists": self.max_colonists,
            "happiness": self.happiness,
            "power": f"{self.power_produced}/{self.power_consumed}",
        }

    def storage_summary(self) -> str:
        """Форматирует содержимое хранилища для отображения."""
        if not self.storage:
            return "  Storage: empty"
        parts = [f"  {rid}:{amt}" for rid, amt in sorted(self.storage.items())]
        total = sum(self.storage.values())
        return f"  Storage: {'  '.join(parts)}  ({total}/{self.max_storage})"
