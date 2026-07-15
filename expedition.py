"""Ground expedition mode — roguelike dungeon exploration."""

import random
import math
from textual.screen import Screen
from textual.widgets import Static

from config import (
    GROUND_TILES, GROUND_ENEMIES, GROUND_WEAPONS, GROUND_ARMOR,
    EXPEDITION_FOV_RADIUS, RESOURCES,
)

# ---------------------------------------------------------------------------
# ExpeditionMap — dungeon generator
# ---------------------------------------------------------------------------

class ExpeditionMap:
    """Procedurally generated dungeon map with rooms + corridors."""

    def __init__(self, width=30, height=20, site_type="station"):
        self.w = width
        self.h = height
        self.site_type = site_type
        # Tile grid: list[list[str]] of tile ids
        self.grid = [["wall"] * width for _ in range(height)]
        # Object layers
        self.crates = {}       # (x,y) -> item_id or "resource"
        self.terminals = set()
        self.enemies = []      # list of EnemyUnit
        self.exit_pos = None   # (x,y)
        self.player_start = None  # (x,y)
        self.rooms = []        # (x1,y1,x2,y2)
        self._generate()

    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def get_tile(self, x, y):
        if not self.in_bounds(x, y):
            return "void"
        return self.grid[y][x]

    def set_tile(self, x, y, tile_id):
        if self.in_bounds(x, y):
            self.grid[y][x] = tile_id

    def is_passable(self, x, y):
        t = self.get_tile(x, y)
        info = GROUND_TILES.get(t, {})
        return info.get("passable", False)

    # ── Generation helpers ─────────────────────────────────────────────

    def _carve_room(self, x1, y1, x2, y2):
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                if self.in_bounds(x, y):
                    self.grid[y][x] = "floor"
        self.rooms.append((x1, y1, x2, y2))

    def _carve_corridor_h(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if self.in_bounds(x, y):
                self.grid[y][x] = "floor"

    def _carve_corridor_v(self, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if self.in_bounds(x, y):
                self.grid[y][x] = "floor"

    def _generate(self):
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
        """Return a random floor tile in a room (excluding first `offset` rooms)."""
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
    """Ground-combat enemy."""

    def __init__(self, x, y, etype, cfg):
        self.x = x
        self.y = y
        self.etype = etype
        self.name = cfg.get("name", "Enemy")
        self.hp = cfg.get("hp", 20)
        self.max_hp = cfg.get("max_hp", 20)
        self.dmg = cfg.get("dmg", 5)
        self.accuracy = cfg.get("accuracy", 50)
        self.evasion = cfg.get("evasion", 5)
        self.ap = cfg.get("ap", 4)
        self.max_ap = cfg.get("ap", 4)
        self.alive = True
        self.seen = False  # seen by player (for FOV)

    def take_damage(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self.alive = False


# ---------------------------------------------------------------------------
# ExpeditionController — turn logic
# ---------------------------------------------------------------------------

class ExpeditionController:
    """Manages player movement, AP, FOV, combat on the ground map."""

    def __init__(self, crew_member, expedition_map, mission=None):
        self.crew = crew_member
        self.map = expedition_map
        self.mission = mission
        self.px, self.py = expedition_map.player_start
        self.turn = 0
        self.log = ["Expedition begins."]
        self.victory = False
        self.game_over = False
        self.over = False
        self._reset_ap()

    def _reset_ap(self):
        self.crew.ap = self.crew.max_ap

    def _visible_tiles(self):
        """Return set of (x,y) visible from player position."""
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
        """Bresenham-based line of sight."""
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
        w_id = self.crew.weapon
        return GROUND_WEAPONS.get(w_id, GROUND_WEAPONS["pistol"])

    def get_player_defense(self):
        a_id = self.crew.armor
        return GROUND_ARMOR.get(a_id, GROUND_ARMOR["none"]).get("defense", 0)

    def can_act(self):
        return not self.over and self.crew.ap > 0

    # ── Actions ────────────────────────────────────────────────────────

    def move(self, dx, dy):
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
        if self.over:
            return
        self.crew.ap = 0
        self.add_log("Waited.")

    def heal(self, item=None):
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
        """Run enemy AI after player ends turn."""
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
        self.log.append(msg)
        if len(self.log) > 30:
            self.log = self.log[-30:]

    def _enemy_visible(self, enemy):
        return self._has_los(self.px, self.py, enemy.x, enemy.y)


# ═══════════════════════════════════════════════════════════════════════
# ExpeditionScreen
# ═══════════════════════════════════════════════════════════════════════

class ExpeditionScreen(Screen):
    """Roguelike ground expedition screen."""

    def __init__(self, controller: ExpeditionController):
        super().__init__()
        self.ctrl = controller
        self._known = set()  # explored tiles

    def compose(self):
        yield Static(id="expedition-content")

    def on_mount(self):
        self._update()

    def _update(self):
        self.query_one("#expedition-content").update(self._render())

    def _render(self):
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
        else:
            lines.append(f"  Arrow keys / WASD = Move  A = Attack  U = Heal  W = Wait")
            lines.append(f"  O = Open door  G = Pick up  Q = Quit expedition")

        return "\n".join(lines)

    def _enemy_at(self, x, y):
        for e in self.ctrl.map.enemies:
            if e.alive and e.x == x and e.y == y:
                return e
        return None

    def on_key(self, event):
        ctrl = self.ctrl
        if ctrl.over:
            self._apply_outcome()
            self.dismiss()
            return

        k = event.key

        # Movement (arrow keys / vi-keys)
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
            if ctrl.crew.ap > 0:
                ctrl.move(dx, dy)
                if ctrl.over:
                    self._update(); return
                ctrl.end_player_turn()
            else:
                ctrl.add_log("No AP left.")
            self._update()
            return

        if k in ("u", "U"):
            ctrl.heal()
            if not ctrl.over:
                ctrl.end_player_turn()
            self._update()
        elif k in ("o", "O"):
            # Try to open door in facing direction
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
            self._update()
        elif k in ("q", "Q"):
            ctrl.over = True
            ctrl.victory = False
            ctrl.add_log("Aborted expedition.")
            self._update()

    def _apply_outcome(self):
        ctrl = self.ctrl
        app = self.app
        crew = ctrl.crew
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
