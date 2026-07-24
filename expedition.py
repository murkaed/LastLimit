"""
expedition.py — Режим высадки на поверхность (ground expedition).

Этот модуль реализует рогалик-подобный (roguelike) режим исследования
процедурно генерируемых подземелий. Игрок управляет членом экипажа,
перемещается по комнатам и коридорам, сражается с врагами, собирает
трофеи и добирается до точки эвакуации.

Ключевые классы:
  - ExpeditionMap: процедурная генерация карты (комнаты + коридоры).
  - EnemyUnit:  враг на карте высадки.
  - ExpeditionController:  логика ходов, FOV, бой.
  - ExpeditionScreen:  экран Textual для отображения карты и управления.
"""

import random
import math
from textual.screen import Screen
from textual.widgets import Static

from config import (
    GROUND_TILES, GROUND_ENEMIES, GROUND_WEAPONS, GROUND_ARMOR,
    EXPEDITION_FOV_RADIUS, RESOURCES, CREW_NAMES, CREW_SPECIALTIES,
)
from models import CrewMember


# ---------------------------------------------------------------------------
# Quick Expedition generators
# ---------------------------------------------------------------------------

def create_quick_expedition_character():
    """Создаёт случайного персонажа для быстрой высадки.

    Returns:
        CrewMember: член экипажа с базовым снаряжением.
    """
    name = random.choice(CREW_NAMES)
    specialty = random.choice(list(CREW_SPECIALTIES.keys()))
    member = CrewMember(name, specialty)
    # Override ground combat stats for quick expedition
    member.hp = 100
    member.max_hp = 100
    member.ap = 10
    member.max_ap = 10
    member.weapon = "rifle"
    member.armor = "vest"
    member.combat_skill = 60
    member.inventory = {"repair_kit": 2}
    return member


def generate_quick_expedition_map(width=30, height=20):
    """Генерирует случайную карту для быстрой высадки.

    Args:
        width: ширина карты.
        height: высота карты.

    Returns:
        ExpeditionMap: готовая карта с комнатами, врагами и лутом.
    """
    site_type = random.choice(["station", "planet", "asteroid"])
    return ExpeditionMap(width=width, height=height, site_type=site_type)

# ---------------------------------------------------------------------------
# ExpeditionMap — dungeon generator
# ---------------------------------------------------------------------------

class ExpeditionMap:
    """Процедурно генерируемая карта подземелья с комнатами и коридорами."""

    def __init__(self, width=30, height=20, site_type="station"):
        """
        Инициализация карты.

        Аргументы:
            width (int): ширина карты в тайлах.
            height (int): высота карты в тайлах.
            site_type (str): тип локации ("station", "research", "asteroid",
                             "wreckage", "planet").
        """
        self.w = width                                 # ширина карты
        self.h = height                                # высота карты
        self.site_type = site_type                     # тип локации
        # Tile grid: list[list[str]] of tile ids
        self.grid = [["wall"] * width for _ in range(height)]  # сетка тайлов
        # Object layers
        self.crates = {}       # ящики: (x,y) -> item_id или "resource"
        self.terminals = set()                         # терминалы
        self.enemies = []      # список врагов (EnemyUnit)
        self.exit_pos = None                           # координаты выхода
        self.player_start = None                       # стартовая позиция игрока
        self.rooms = []        # комнаты: (x1, y1, x2, y2)
        self._generate()

    def in_bounds(self, x, y):
        """Проверяет, находятся ли координаты в пределах карты.

        Аргументы:
            x (int): координата X.
            y (int): координата Y.

        Возвращает:
            bool: True, если (x, y) внутри границ карты.
        """
        return 0 <= x < self.w and 0 <= y < self.h

    def get_tile(self, x, y):
        """Возвращает идентификатор тайла по координатам.

        Аргументы:
            x (int): координата X.
            y (int): координата Y.

        Возвращает:
            str: идентификатор тайла или "void" за пределами карты.
        """
        if not self.in_bounds(x, y):
            return "void"
        return self.grid[y][x]

    def set_tile(self, x, y, tile_id):
        """Устанавливает тайл по координатам.

        Аргументы:
            x (int): координата X.
            y (int): координата Y.
            tile_id (str): идентификатор тайла.
        """
        if self.in_bounds(x, y):
            self.grid[y][x] = tile_id

    def is_passable(self, x, y):
        """Проверяет, можно ли пройти через тайл.

        Аргументы:
            x (int): координата X.
            y (int): координата Y.

        Возвращает:
            bool: True, если тайл проходим.
        """
        t = self.get_tile(x, y)
        info = GROUND_TILES.get(t, {})
        return info.get("passable", False)

    # ── Generation helpers ─────────────────────────────────────────────

    def _carve_room(self, x1, y1, x2, y2):
        """Вырезает прямоугольную комнату, заполняя её полом.

        Аргументы:
            x1 (int): левая граница комнаты.
            y1 (int): верхняя граница комнаты.
            x2 (int): правая граница комнаты.
            y2 (int): нижняя граница комнаты.
        """
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                if self.in_bounds(x, y):
                    self.grid[y][x] = "floor"
        self.rooms.append((x1, y1, x2, y2))

    def _carve_corridor_h(self, x1, x2, y):
        """Вырезает горизонтальный коридор.

        Аргументы:
            x1 (int): начальная координата X.
            x2 (int): конечная координата X.
            y (int): координата Y коридора.
        """
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if self.in_bounds(x, y):
                self.grid[y][x] = "floor"

    def _carve_corridor_v(self, y1, y2, x):
        """Вырезает вертикальный коридор.

        Аргументы:
            y1 (int): начальная координата Y.
            y2 (int): конечная координата Y.
            x (int): координата X коридора.
        """
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if self.in_bounds(x, y):
                self.grid[y][x] = "floor"

    def _generate(self):
        """Генерирует карту: комнаты, коридоры, двери, объекты и врагов."""
        num_rooms = random.randint(4, 7)
        min_room = 3
        max_room = 7
        for _ in range(num_rooms * 3):
            if len(self.rooms) >= num_rooms:
                break
            rw = random.randint(min_room, max_room)
            rh = random.randint(min_room, max_room)
            rx = random.randint(1, self.w - rw - 2)
            ry = random.randint(1, self.h - rh - 2)
            # Check overlap
            overlap = False
            for (ox1, oy1, ox2, oy2) in self.rooms:
                if not (rx + rw + 1 < ox1 or rx > ox2 + 1 or ry + rh + 1 < oy1 or ry > oy2 + 1):
                    overlap = True; break
            if not overlap:
                self._carve_room(rx, ry, rx + rw, ry + rh)

        # Connect rooms with corridors
        for i in range(1, len(self.rooms)):
            x1 = (self.rooms[i - 1][0] + self.rooms[i - 1][2]) // 2
            y1 = (self.rooms[i - 1][1] + self.rooms[i - 1][3]) // 2
            x2 = (self.rooms[i][0] + self.rooms[i][2]) // 2
            y2 = (self.rooms[i][1] + self.rooms[i][3]) // 2
            if random.random() < 0.5:
                self._carve_corridor_h(x1, x2, y1)
                self._carve_corridor_v(y1, y2, x2)
            else:
                self._carve_corridor_v(y1, y2, x1)
                self._carve_corridor_h(x1, x2, y2)

        # Place doors at room entrances (random)
        for (x1, y1, x2, y2) in self.rooms:
            for x in range(x1 - 1, x2 + 2):
                for y in range(y1 - 1, y2 + 2):
                    if self.grid[y][x] == "floor":
                        continue
                    # Check if adjacent to floor and forms a doorway
                    neighbors = [(x, y) for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
                                 if self.in_bounds(x + dx, y + dy) and self.grid[y + dy][x + dx] == "floor"]
                    if 1 <= len(neighbors) <= 2 and random.random() < 0.3:
                        self.grid[y][x] = "door_closed"

        # Player start in first room center
        sx = (self.rooms[0][0] + self.rooms[0][2]) // 2
        sy = (self.rooms[0][1] + self.rooms[0][3]) // 2
        self.player_start = (sx, sy)

        # Exit in last room
        ex = (self.rooms[-1][0] + self.rooms[-1][2]) // 2
        ey = (self.rooms[-1][1] + self.rooms[-1][3]) // 2
        self.exit_pos = (ex, ey)
        self.grid[ey][ex] = "exit"

        # Site-specific features
        if self.site_type in ("station", "research"):
            # More terminals, less obstacles
            for _ in range(len(self.rooms)):
                rx, ry = self._rand_room_floor()
                if rx is not None:
                    self.terminals.add((rx, ry))
                    self.grid[ry][rx] = "terminal"
        elif self.site_type in ("asteroid", "wreckage"):
            # More crates, hazards
            for _ in range(len(self.rooms) * 2):
                rx, ry = self._rand_room_floor()
                if rx is not None and random.random() < 0.5:
                    self.crates[(rx, ry)] = random.choice(["metal", "electronics", "relic", "repair_kit"])
                    self.grid[ry][rx] = "crate"
            # Add some lava/spikes
            for _ in range(random.randint(2, 5)):
                rx = random.randint(1, self.w - 2)
                ry = random.randint(1, self.h - 2)
                if self.grid[ry][rx] == "floor":
                    self.grid[ry][rx] = random.choice(["lava", "spikes"])
        else:  # planet
            for _ in range(len(self.rooms)):
                rx, ry = self._rand_room_floor()
                if rx is not None:
                    self.crates[(rx, ry)] = random.choice(["food", "metal", "relic"])
                    self.grid[ry][rx] = "crate"

        # Place enemies
        num_enemies = random.randint(2, 5)
        enemy_types = ["bandit", "drone", "mutant", "turret"]
        if self.site_type == "station":
            enemy_types = ["drone", "turret"]
        elif self.site_type == "asteroid":
            enemy_types = ["bandit", "mutant"]
        for _ in range(num_enemies):
            rx, ry = self._rand_room_floor(offset=1)  # avoid room 0 (player start)
            if rx is not None:
                etype = random.choice(enemy_types)
                cfg = GROUND_ENEMIES.get(etype, GROUND_ENEMIES["bandit"])
                self.enemies.append(EnemyUnit(rx, ry, etype, cfg))

    def _rand_room_floor(self, offset=0):
        """Возвращает случайную клетку пола в комнате (исключая первые `offset` комнат).

        Аргументы:
            offset (int): сколько первых комнат пропустить.

        Возвращает:
            tuple[int, int] | tuple[None, None]: координаты случайной клетки
            пола или (None, None), если подходящих клеток нет.
        """
        candidates = []
        for i in range(offset, len(self.rooms)):
            x1, y1, x2, y2 = self.rooms[i]
            for y in range(y1, y2 + 1):
                for x in range(x1, x2 + 1):
                    if self.grid[y][x] == "floor" and (x, y) != self.player_start:
                        candidates.append((x, y))
        if candidates:
            return random.choice(candidates)
        return None, None


class EnemyUnit:
    """Противник на карте высадки. Содержит характеристики и состояние."""

    def __init__(self, x, y, etype, cfg):
        """
        Инициализация врага.

        Аргументы:
            x (int): координата X на карте.
            y (int): координата Y на карте.
            etype (str): тип врага (bandit, drone, mutant, turret).
            cfg (dict): конфигурация врага из GROUND_ENEMIES.
        """
        self.x = x                                    # позиция X
        self.y = y                                    # позиция Y
        self.etype = etype                            # тип врага
        self.name = cfg.get("name", "Enemy")          # имя врага
        self.hp = cfg.get("hp", 20)                   # текущее здоровье
        self.max_hp = cfg.get("max_hp", 20)           # максимальное здоровье
        self.dmg = cfg.get("dmg", 5)                  # урон в ближнем бою
        self.accuracy = cfg.get("accuracy", 50)       # точность атаки (%)
        self.evasion = cfg.get("evasion", 5)          # уклонение (%)
        self.ap = cfg.get("ap", 4)                    # текущие очки действий
        self.max_ap = cfg.get("ap", 4)                # максимальные очки действий
        self.alive = True                             # жив ли враг
        self.seen = False  # seen by player (for FOV) # замечен ли игроком

    def take_damage(self, dmg):
        """Наносит урон врагу. Если HP <= 0, помечает как убитого.

        Аргументы:
            dmg (int): количество наносимого урона.
        """
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self.alive = False


# ---------------------------------------------------------------------------
# ExpeditionController — turn logic
# ---------------------------------------------------------------------------

class ExpeditionController:
    """Управляет перемещением игрока, очками действий (AP), обзором (FOV)
    и боем на карте высадки."""

    def __init__(self, crew_member, expedition_map, mission=None):
        """
        Инициализация контроллера высадки.

        Аргументы:
            crew_member: объект члена экипажа (с атрибутами hp, ap, weapon, armor...).
            expedition_map (ExpeditionMap): карта высадки.
            mission (dict | None): данные миссии (необязательно).
        """
        self.crew = crew_member                       # член экипажа
        self.map = expedition_map                     # карта высадки
        self.mission = mission                        # данные миссии
        self.px, self.py = expedition_map.player_start  # позиция игрока на карте
        self.turn = 0                                 # номер текущего хода
        self.log = ["Expedition begins."]             # журнал событий
        self.victory = False                          # флаг победы (достиг выхода)
        self.game_over = False                        # флаг поражения (смерть)
        self.over = False                             # завершена ли экспедиция
        self._reset_ap()

    def _reset_ap(self):
        """Восстанавливает очки действий (AP) экипажа до максимума."""
        self.crew.ap = self.crew.max_ap

    def _visible_tiles(self):
        """Вычисляет множество тайлов, видимых с позиции игрока (FOV).

        Использует радиус обзора EXPEDITION_FOV_RADIUS и проверку
        линии видимости (line of sight).

        Возвращает:
            set[tuple[int, int]]: множество координат видимых тайлов.
        """
        visible = set()
        px, py = self.px, self.py
        r = EXPEDITION_FOV_RADIUS
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                x, y = px + dx, py + dy
                if not self.map.in_bounds(x, y):
                    continue
                d = math.sqrt(dx * dx + dy * dy)
                if d > r:
                    continue
                # Simple raycast — if line of sight passes through wall
                if self._has_los(px, py, x, y):
                    visible.add((x, y))
        return visible

    def _has_los(self, x1, y1, x2, y2):
        """Проверяет линию видимости между двумя точками (алгоритм Брезенхема).

        Аргументы:
            x1, y1 (int): координаты начальной точки (игрок).
            x2, y2 (int): координаты конечной точки.

        Возвращает:
            bool: True, если между точками есть прямая видимость.
        """
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        cx, cy = x1, y1
        while True:
            if (cx, cy) != (x1, y1):
                t = self.map.get_tile(cx, cy)
                info = GROUND_TILES.get(t, {})
                block = info.get("ch", " ") in ("#", " ")
                if block:
                    # Allow line to end at a blocked tile if it's the target
                    if (cx, cy) == (x2, y2):
                        return True
                    return False
            if (cx, cy) == (x2, y2):
                return True
            e2 = err * 2
            if e2 > -dy:
                err -= dy; cx += sx
            if e2 < dx:
                err += dx; cy += sy

    def get_player_weapon_stats(self):
        """Возвращает характеристики текущего оружия игрока.

        Возвращает:
            dict: словарь характеристик оружия из GROUND_WEAPONS.
        """
        w_id = self.crew.weapon
        return GROUND_WEAPONS.get(w_id, GROUND_WEAPONS["pistol"])

    def get_player_defense(self):
        """Возвращает значение защиты игрока от брони.

        Возвращает:
            int: значение защиты.
        """
        a_id = self.crew.armor
        return GROUND_ARMOR.get(a_id, GROUND_ARMOR["none"]).get("defense", 0)

    def can_act(self):
        """Проверяет, может ли игрок совершить действие.

        Возвращает:
            bool: True, если экспедиция не завершена и есть AP.
        """
        return not self.over and self.crew.ap > 0

    # ── Actions ────────────────────────────────────────────────────────

    def move(self, dx, dy):
        """Перемещает игрока на указанный вектор.

        Обрабатывает преграды, двери, опасности (lava/spikes),
        взаимодействие с ящиками и терминалами, проверку выхода.

        Аргументы:
            dx (int): смещение по X (-1, 0, 1).
            dy (int): смещение по Y (-1, 0, 1).
        """
        if self.over:
            return
        nx, ny = self.px + dx, self.py + dy
        if not self.map.in_bounds(nx, ny):
            self.add_log("Blocked by edge.")
            return
        tile = self.map.get_tile(nx, ny)
        info = GROUND_TILES.get(tile, {})

        # Check for enemy in target tile
        for e in self.map.enemies:
            if e.alive and e.x == nx and e.y == ny:
                self.add_log(f"Blocked by {e.name}!")
                return

        if not info.get("passable", False):
            # Try to interact
            if tile == "door_closed":
                self.map.set_tile(nx, ny, "door_open")
                self.crew.ap -= 1
                self.add_log("Opened door.")
                return
            self.add_log("Blocked.")
            return

        # Check hazard
        hazard = info.get("hazard", 0)
        if hazard > 0:
            self.crew.hp -= hazard
            self.add_log(f"Hit by {info.get('name','')}! -{hazard} HP.")

        self.px, self.py = nx, ny
        self.crew.ap -= 1

        # Check exit
        if tile == "exit":
            self.victory = True
            self.over = True
            self.add_log("Reached evac point! Returning to ship.")

        # Check crate
        if (nx, ny) in self.map.crates:
            item = self.map.crates.pop((nx, ny))
            # Try to add to inventory
            self.crew.inventory[item] = self.crew.inventory.get(item, 0) + 1
            self.add_log(f"Picked up {item}.")
            self.map.set_tile(nx, ny, "floor")

        # Check terminal
        if (nx, ny) in self.map.terminals:
            self.add_log("Terminal activated! (placeholder)")

    def attack(self):
        """Атакует ближайшего врага в пределах дальности оружия.

        Тратит AP, производит бросок на попадание, наносит урон.
        При уничтожении врага с шансом 40% выпадает лут.
        """
        if self.over:
            return
        wpn = self.get_player_weapon_stats()
        ap_cost = wpn.get("ap_cost", 2)
        if self.crew.ap < ap_cost:
            self.add_log(f"Need {ap_cost} AP.")
            return

        # Find nearest enemy in range
        rng = wpn.get("range", 3)
        target = None
        tx, ty = -1, -1
        min_d = 999
        for e in self.map.enemies:
            if not e.alive:
                continue
            if not self._enemy_visible(e):
                continue
            d = max(abs(e.x - self.px), abs(e.y - self.py))
            if d <= rng and d < min_d:
                min_d = d; target = e; tx, ty = e.x, e.y

        if not target:
            self.add_log("No enemy in weapon range.")
            return

        self.crew.ap -= ap_cost

        # Hit roll
        hit_chance = min(95, self.crew.combat_skill + wpn.get("accuracy", 50) - target.evasion)
        if random.random() * 100 < hit_chance:
            dmg = wpn.get("dmg", 4) - self.get_player_defense() // 2
            dmg = max(1, dmg)
            target.take_damage(dmg)
            if not target.alive:
                self.add_log(f"★ {target.name} destroyed!")
                # Drop loot
                if random.random() < 0.4:
                    loot = random.choice(["metal", "electronics", "repair_kit"])
                    self.map.crates[(tx, ty)] = loot
                    self.map.set_tile(tx, ty, "crate")
            else:
                self.add_log(f"Hit {target.name}! -{dmg} HP ({target.hp}/{target.max_hp}).")
        else:
            self.add_log(f"Missed {target.name}!")

        # Check if all enemies dead
        if not any(e.alive for e in self.map.enemies):
            self.add_log("★ All enemies eliminated!")

    def wait(self):
        """Пропускает ход игрока (обнуляет AP)."""
        if self.over:
            return
        self.crew.ap = 0
        self.add_log("Waited.")

    def heal(self, item=None):
        """Использует аптечку для восстановления HP.

        Аргументы:
            item (str | None): идентификатор предмета для лечения
                               (по умолчанию "repair_kit").
        """
        if not item:
            item = "repair_kit"
        qty = self.crew.inventory.get(item, 0)
        if qty <= 0:
            self.add_log(f"No {item}.")
            return
        if self.crew.ap < 2:
            self.add_log("Need 2 AP.")
            return
        self.crew.inventory[item] = qty - 1
        self.crew.ap -= 2
        heal_amt = 15
        self.crew.hp = min(self.crew.max_hp, self.crew.hp + heal_amt)
        self.add_log(f"Used {item}. HP +{heal_amt} ({self.crew.hp}/{self.crew.max_hp}).")

    # ── Enemy turn ──────────────────────────────────────────────────────

    def end_player_turn(self):
        """Завершает ход игрока и запускает ИИ врагов.

        Враги перемещаются к игроку, если видят его, и атакуют в упор.
        Проверяет смерть игрока после всех действий врагов.
        Увеличивает счётчик ходов и восстанавливает AP.
        """
        if self.over:
            return
        for e in self.map.enemies:
            if not e.alive:
                continue
            # Basic AI: move toward player if visible
            d = max(abs(e.x - self.px), abs(e.y - self.py))
            e.ap = e.max_ap

            if d <= 1:
                # Melee attack
                hit_chance = min(95, e.accuracy - 5)  # player base evasion 5
                if random.random() * 100 < hit_chance:
                    dmg = max(1, e.dmg - self.get_player_defense())
                    self.crew.hp -= dmg
                    self.add_log(f"☠ {e.name} hits! -{dmg} HP.")
                else:
                    self.add_log(f"{e.name} missed.")
            elif d <= 4 and e.ap >= 2:
                # Move toward player
                dx = 1 if e.x < self.px else -1 if e.x > self.px else 0
                dy = 1 if e.y < self.py else -1 if e.y > self.py else 0
                nx, ny = e.x + dx, e.y + dy
                if self.map.in_bounds(nx, ny) and self.map.is_passable(nx, ny) and not any(
                        e2.alive and e2.x == nx and e2.y == ny for e2 in self.map.enemies if e2 != e):
                    e.x, e.y = nx, ny
                    e.ap -= 2

        # Check player death
        if self.crew.hp <= 0:
            self.crew.hp = 0
            self.game_over = True
            self.over = True
            self.add_log("☠ Crew member lost!")

        if self.over:
            return
        self.turn += 1
        self._reset_ap()

    def add_log(self, msg):
        """Добавляет сообщение в журнал экспедиции.

        Журнал хранит не более 30 последних записей.

        Аргументы:
            msg (str): текст сообщения.
        """
        self.log.append(msg)
        if len(self.log) > 30:
            self.log = self.log[-30:]

    def _enemy_visible(self, enemy):
        """Проверяет, видит ли игрок данного врага (есть ли LOS).

        Аргументы:
            enemy (EnemyUnit): проверяемый враг.

        Возвращает:
            bool: True, если враг в пределах прямой видимости.
        """
        return self._has_los(self.px, self.py, enemy.x, enemy.y)


# ═══════════════════════════════════════════════════════════════════════
# ExpeditionScreen
# ═══════════════════════════════════════════════════════════════════════

class ExpeditionScreen(Screen):
    """Экран Textual для отображения карты высадки, интерфейса и управления."""

    def __init__(self, controller: ExpeditionController, quick_expedition=False):
        """
        Инициализация экрана экспедиции.

        Аргументы:
            controller (ExpeditionController): контроллер высадки.
            quick_expedition (bool): True — режим быстрой высадки (без корабля).
        """
        super().__init__()
        self.ctrl = controller                        # контроллер высадки
        self.quick_expedition = quick_expedition      # режим быстрой высадки
        self._known = set()                           # исследованные (ранее виденные) тайлы
        self._show_action_menu = False                # флаг открытого меню действий

    def compose(self):
        """Создаёт виджеты экрана.

        Возвращает:
            Generator[Static]: единственный Static-виджет для отрисовки.
        """
        yield Static(id="expedition-content")

    def on_mount(self):
        """Вызывается при монтировании экрана. Обновляет отображение."""
        self._update()

    def _update(self):
        """Обновляет содержимое Static-виджета текущей отрисовкой карты."""
        self.query_one("#expedition-content").update(self._build_display())

    def _build_display(self):
        """Отрисовывает карту, статус-панель, журнал и подсказки.

        Возвращает:
            str: готовая текстовая строка для отображения.
        """
        ctrl = self.ctrl
        mp = ctrl.map
        lines = []
        visible = ctrl._visible_tiles()

        # Update known tiles from FOV
        self._known |= visible

        # ── Map ──
        for y in range(mp.h):
            row = ""
            for x in range(mp.w):
                if (x, y) == (ctrl.px, ctrl.py):
                    row += "@"
                elif (x, y) in visible:
                    # Check enemies
                    enemy = self._enemy_at(x, y)
                    if enemy and enemy.alive:
                        enemy.seen = True
                        row += "E"
                    elif mp.get_tile(x, y) == "exit":
                        row += ">"
                    elif mp.get_tile(x, y) == "crate":
                        row += "$"
                    elif mp.get_tile(x, y) == "terminal":
                        row += "!"
                    elif mp.get_tile(x, y) == "lava":
                        row += "~"
                    elif mp.get_tile(x, y) == "spikes":
                        row += "^"
                    elif mp.get_tile(x, y) == "door_closed":
                        row += "+"
                    elif mp.get_tile(x, y) == "door_open":
                        row += "-"
                    elif mp.get_tile(x, y) == "floor":
                        row += "."
                    elif mp.get_tile(x, y) == "wall":
                        row += "#"
                    else:
                        row += " "
                elif (x, y) in self._known:
                    t = mp.get_tile(x, y)
                    if t in ("floor", "door_open"):
                        row += "."
                    elif t in ("wall", "door_closed"):
                        row += "#"
                    else:
                        row += "."
                else:
                    row += " "
            lines.append(row)

        # ── Status panel ──
        crew = ctrl.crew
        wpn = ctrl.get_player_weapon_stats()
        arm = ctrl.get_player_defense()
        wname = wpn.get("name", "?")
        alive = sum(1 for e in mp.enemies if e.alive)
        total = len(mp.enemies)

        lines.append("")
        lines.append(f"── Status ──")
        lines.append(f"  HP: {crew.hp:>2}/{crew.max_hp}  AP: {crew.ap}/{crew.max_ap}")
        lines.append(f"  Weapon: {wname}  Defense: {arm}")
        lines.append(f"  Enemies: {alive}/{total} alive")
        lines.append(f"  Inventory: {dict(crew.inventory)}")
        lines.append(f"  Turn: {ctrl.turn}")
        lines.append(f"")
        lines.append(f"── Log ──")
        for log_line in ctrl.log[-5:]:
            lines.append(f"  {log_line}")
        lines.append(f"")
        lines.append(f"── Controls ──")
        if ctrl.over:
            lines.append(f"  Mission over. Press any key to return.")
        elif self._show_action_menu:
            lines.append(f"  ┌─ Action ────────────┐")
            lines.append(f"  │ 1 - Attack          │")
            lines.append(f"  │ 2 - Heal            │")
            lines.append(f"  │ 3 - Wait            │")
            lines.append(f"  │ 4 - Open door       │")
            lines.append(f"  │ 5 - Quit expedition │")
            lines.append(f"  │ 0 - Cancel          │")
            lines.append(f"  └─────────────────────┘")
        else:
            lines.append(f"  WASD/Arrows = Move  Space = Action menu")

        return "\n".join(lines)

    def _enemy_at(self, x, y):
        """Возвращает врага на указанных координатах, если он есть.

        Аргументы:
            x (int): координата X.
            y (int): координата Y.

        Возвращает:
            EnemyUnit | None: враг на клетке или None.
        """
        for e in self.ctrl.map.enemies:
            if e.alive and e.x == x and e.y == y:
                return e
        return None

    def on_key(self, event):
        """Обрабатывает нажатия клавиш для управления экспедицией.

        WASD/стрелки = движение, Space = меню действий (1-9).

        Аргументы:
            event: событие нажатия клавиши.
        """
        ctrl = self.ctrl
        if ctrl.over:
            self._apply_outcome()
            self.dismiss()
            return

        k = event.key

        # ── Movement (always available) ──
        dx = dy = 0
        if k in ("up", "w", "W"):
            dy = -1
        elif k in ("down", "s", "S"):
            dy = 1
        elif k in ("left", "a", "A"):
            dx = -1
        elif k in ("right", "d", "D"):
            dx = 1

        if dx != 0 or dy != 0:
            if self._show_action_menu:
                self._show_action_menu = False
            if ctrl.crew.ap > 0:
                ctrl.move(dx, dy)
                if ctrl.over:
                    self._update(); return
                ctrl.end_player_turn()
            else:
                ctrl.add_log("No AP left.")
            self._update()
            return

        # ── Action menu toggle ──
        if k in (" ", "space", "enter"):
            if self._show_action_menu:
                self._show_action_menu = False
            else:
                self._show_action_menu = True
            self._update()
            return

        # ── Menu choices (only when action menu is open) ──
        if self._show_action_menu:
            self._show_action_menu = False

            if k == "1":
                # Attack
                ctrl.attack()
                if not ctrl.over:
                    ctrl.end_player_turn()
            elif k == "2":
                # Heal
                ctrl.heal()
                if not ctrl.over:
                    ctrl.end_player_turn()
            elif k == "3":
                # Wait
                ctrl.wait()
                if not ctrl.over:
                    ctrl.end_player_turn()
            elif k == "4":
                # Open door in facing direction
                for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                    nx, ny = ctrl.px + dx, ctrl.py + dy
                    if ctrl.map.in_bounds(nx, ny) and ctrl.map.get_tile(nx, ny) == "door_closed":
                        if ctrl.crew.ap >= 1:
                            ctrl.map.set_tile(nx, ny, "door_open")
                            ctrl.crew.ap -= 1
                            ctrl.add_log("Opened door.")
                            if not ctrl.over:
                                ctrl.end_player_turn()
                            break
                else:
                    ctrl.add_log("No door to open.")
            elif k == "5":
                # Quit expedition
                ctrl.over = True
                ctrl.victory = False
                ctrl.add_log("Aborted expedition.")
            # "0" or any other key — just close menu (do nothing)
            self._update()
            return

    def _apply_outcome(self):
        """Применяет результаты экспедиции к глобальному состоянию.

        В обычном режиме — удаляет члена экипажа из ростера при смерти
        или переносит инвентарь в грузовой отсек корабля при возвращении.

        В режиме быстрой высадки (quick_expedition=True) — только
        выводит итоговую статистику, не трогая глобальные данные.
        """
        ctrl = self.ctrl
        app = self.app
        crew = ctrl.crew

        if self.quick_expedition:
            # Quick expedition mode — just show summary, no global side effects
            killed = sum(1 for e in ctrl.map.enemies if not e.alive)
            items = len(ctrl.map.crates)
            if crew.hp <= 0:
                outcome = f"☠ {crew.name} died after {ctrl.turn} turns."
            elif ctrl.victory:
                outcome = f"✓ Evacuated after {ctrl.turn} turns. Killed {killed} enemies."
            else:
                outcome = f"Aborted after {ctrl.turn} turns."
            # Store result for display (used by dismiss handler)
            self._quick_outcome = outcome
            try:
                self.app.notify(outcome, severity="information", timeout=5)
            except Exception:
                pass
            return

        if crew.hp <= 0:
            # Permanent death: remove from crew roster
            name = crew.name
            app.ship.fire_crew(name)
            if hasattr(app, "logger"):
                app.logger.system(f"☠ {name} died on expedition.")
        else:
            # Return to ship: transfer inventory
            for item_id, qty in crew.inventory.items():
                app.ship.cargo.add(item_id, qty)
            crew.inventory.clear()
            # Restore some HP over time (simplified)
            crew.hp = crew.max_hp
            if hasattr(app, "logger"):
                app.logger.system(f"✓ Expedition complete. Cargo +{sum(crew.inventory.values()) if crew.inventory else 0} items.")
        if hasattr(app, "update_map"):
            app.update_map()
        if hasattr(app, "update_info"):
            app.update_info()
