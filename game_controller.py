"""
game_controller.py — Game logic and rendering, separated from Textual UI.

GameController holds all game state (galaxy, ship, player position, logger)
and provides:
  - Rendering methods (return strings for the App to display)
  - Game logic (movement, interactions, economy, commands, world ticks)
  - State management (race select, restart, pause, game over)

It has no Textual dependency. GalaxyMapApp (galaxy_map.py) is the thin
Textual shell that delegates to this controller.
"""

import random
import re
from enum import Enum, auto

from game_logger import GameLogger, LogLevel, LogCategory, LogMessage, DetailLevel, CATEGORY_LABEL, CATEGORY_COLOR
from config import (
    WIDTH, HEIGHT, RESOURCES, RACES, FACTIONS, COMPARTMENTS, CONTRABAND,
    SHIP_HULLS, SHIP_MODULES, UPGRADES, RECIPES, CREW_SPECIALTIES,
    TILE_EMPTY, TILE_STAR, TILE_PLANET, TILE_STATION, TILE_BLACK_HOLE,
    TILE_WORMHOLE, TILE_ASTEROIDS, TILE_SHIP, TILE_OTHER_SHIP,
    TILE_CURSOR, TILE_TRADER, TILE_PIRATE, DIR_LABELS,
)
from models import PlayerShip, Galaxy, TraderShip, PirateShip, CargoHold, NPCShip, create_random_ship, create_random_enemy
import models
from battle import BattleController
from colony import ColonyManager, PLANET_TYPES, SURFACE_SIZE

# ---------------------------------------------------------------------------
# Game state enum
# ---------------------------------------------------------------------------

class GameState(Enum):
    RACE_SELECT = auto()
    START_SCREEN = auto()
    PLAYING = auto()
    PAUSED = auto()
    INSPECTING = auto()
    HELP = auto()
    NEWS = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# GameController
# ---------------------------------------------------------------------------

class GameController:
    """All game state, logic, and rendering. No Textual dependency."""

    OBJ_LABELS = {
        "planet": ("Planet", TILE_PLANET),
        "station": ("Station", TILE_STATION),
        "asteroids": ("Asteroids", TILE_ASTEROIDS),
        "wormhole": ("Wormhole", TILE_WORMHOLE),
    }

    def __init__(self):
        self.state = GameState.RACE_SELECT
        self.galaxy = Galaxy()
        self.ship = PlayerShip("Endeavour", 100)
        self.logger = GameLogger()
        self.death_cause = None
        self.interaction_actions = []
        self.cursor_x = WIDTH // 2
        self.cursor_y = HEIGHT // 2
        self._politics_timer = 0
        self.race_selected = False
        self._show_race_select = False
        self.log_category_filter = None
        self.log_filter_index = 0
        self._prev_state = GameState.START_SCREEN
        self._interaction_active = False
        self._pending_battle = None
        self._dismiss_handled_escape = False
        self.world_frozen = False
        self.player_x = WIDTH // 2
        self.player_y = HEIGHT // 2

        # Callback for screen push requests (set by GalaxyMapApp)
        self._push_screen = None
        self._update_map = None
        self._update_info = None
        self._update_log = None

        self._init_player_position()

    def set_callbacks(self, push_screen, update_map, update_info, update_log):
        """Set Textual callbacks from GalaxyMapApp."""
        self._push_screen = push_screen
        self._update_map = update_map
        self._update_info = update_info
        self._update_log = update_log

    def _init_player_position(self):
        self.player_x = WIDTH // 2
        self.player_y = HEIGHT // 2
        while not self.galaxy.is_passable(self.player_x, self.player_y):
            self.player_x = random.randint(0, WIDTH - 1)
            self.player_y = random.randint(0, HEIGHT - 1)

    # -------------------------------------------------------------------
    # Race selection
    # -------------------------------------------------------------------

    def select_race(self, choice):
        c = choice.lower().strip()
        race_map = {
            "1": "human", "human": "human",
            "2": "mutant", "mutant": "mutant",
            "3": "xenos_bio", "xenos": "xenos_bio",
            "4": "machine_cult", "machine": "machine_cult",
            "5": "voidborn", "void": "voidborn",
            "": "human",
        }
        race_id = race_map.get(c)
        if not race_id:
            return
        self.ship.race = race_id
        self.ship.apply_race_bonus()
        race_name = RACES.get(race_id, {}).get("name", race_id)
        self.logger.system(f"Race: {race_name}.")
        self.race_selected = True
        self._show_race_select = False
        self.state = GameState.PLAYING

    # -------------------------------------------------------------------
    # Restart
    # -------------------------------------------------------------------

    def restart_game(self):
        models.npc_ids.reset()
        self.state = GameState.RACE_SELECT
        self.galaxy = Galaxy()
        self.ship = PlayerShip("Endeavour", 100)
        self.ship.shield_hp = self.ship.get_effective_stats().get("shield_cap", 30)
        self.logger.clear()
        self.death_cause = None
        self.interaction_actions = []
        self.race_selected = False
        self._show_race_select = False
        self._pending_battle = None
        self._dismiss_handled_escape = False
        self.world_frozen = False
        self._interaction_active = False
        self._init_player_position()

    # ===================================================================
    # Rendering methods — all return strings
    # ===================================================================

    def render_start_screen(self):
        if self._show_race_select:
            lines = ["", ""]
            lines.append("  ┏━ CHOOSE YOUR RACE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
            cfg = RACES
            race_keys = ["human", "mutant", "xenos_bio", "machine_cult", "voidborn"]
            for i, rid in enumerate(race_keys, 1):
                rc = cfg.get(rid, {})
                name = rc.get("name", rid)
                desc = rc.get("desc", "")
                bonuses = rc.get("bonus", {})
                penalties = rc.get("penalty", {})
                parts = []
                for k, v in bonuses.items():
                    if k == "max_hull":
                        parts.append(f"+{v} hull")
                    else:
                        parts.append(f"+{v} {k}")
                for k, v in penalties.items():
                    if k == "max_hull":
                        parts.append(f"{v} hull")
                    else:
                        parts.append(f"{v} {k}")
                bonus_str = ", ".join(parts) if parts else "—"
                lines.append(f"  ┃                                                         ┃")
                lines.append(f"  ┃  [{i}] {name:<12}                                   ┃")
                lines.append(f"  ┃      {desc:<55}┃")
                lines.append(f"  ┃      [{bonus_str:<53}┃")
            lines.append(f"  ┃                                                         ┃")
            lines.append(f"  ┃  [0] Back                          [Enter] Human        ┃")
            lines.append(f"  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
        else:
            lines = ["", "",
                "        ██╗     █████╗ ███████╗████████╗    ██╗     ██╗███╗   ███╗██╗████████╗",
                "        ██║    ██╔══██╗██╔════╝╚══██╔══╝    ██║     ██║████╗ ████║██║╚══██╔══╝",
                "        ██║    ███████║███████╗   ██║       ██║     ██║██╔████╔██║██║   ██║   ",
                "        ██║    ██╔══██║╚════██║   ██║       ██║     ██║██║╚██╔╝██║██║   ██║   ",
                "        ███████╗██║  ██║███████║   ██║       ███████╗██║██║ ╚═╝ ██║██║   ██║   ",
                "        ╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝       ╚══════╝╚═╝╚═╝     ╚═╝╚═╝   ╚═╝   ",
                "",
                "              In the grim darkness of the far future, there is only war.",
                "",
                "  ╔══════════════════════════════════════════════════════════════════╗",
                "  ║                                                                  ║",
                "  ║              [N] New Game                                        ║",
                "  ║              [B] Quick Battle  (Training / Debug)                ║",
                "  ║              [E] Quick Expedition  (Training / Debug)             ║",
                "  ║              [H] Help                                            ║",
                "  ║              [Q] Quit                                            ║",
                "  ║                                                                  ║",
                "  ╚══════════════════════════════════════════════════════════════════╝",
            ]
        return "\n".join(lines)

    def render_help_screen(self):
        return (
            "  ┏━ HELP ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "  ┃                                                 ┃\n"
            "  ┃  MOVEMENT:                                      ┃\n"
            "  ┃    W/↑ N  A/← W  S/↓ S  D/→ E                  ┃\n"
            "  ┃    Space = wait (advance time 1 turn)            ┃\n"
            "  ┃                                                 ┃\n"
            "  ┃  ACTIONS:                                       ┃\n"
            "  ┃    E = interact with nearby objects              ┃\n"
            "  ┃    F = engage turn-based battle with pirate         ┃\n"
            "  ┃    I = inspect / free look around                ┃\n"
            "  ┃    B = open trade screen (at station)            ┃\n"
            "  ┃                                                 ┃\n"
            "  ┃  SHIP MANAGEMENT:                               ┃\n"
            "  ┃    F1 = Bridge (ship status + all subsystems)  ┃\n"
            "  ┃                                                 ┃\n"
            "  ┃  INTERFACE:                                     ┃\n"
            "  ┃    H = help        N = news      ~ = console    ┃\n"
            "  ┃    Esc = pause     Q = quit                     ┃\n"
            "  ┃                                                 ┃\n"
            "  ┃  CONSOLE COMMANDS (~):                          ┃\n"
            "  ┃    scan / inv / give/take / refuel / set hull   ┃\n"
            "  ┃    trade buy/sell / prices / market scan/history┃\n"
            "  ┃    power <comp> <val> / modules list            ┃\n"
            "  ┃    cargo / cargo jettison / cargo sellall       ┃\n"
            "  ┃    reputation / diplomacy / declare war         ┃\n"
            "  ┃    attack / hail / smuggle / news / exit        ┃\n"
            "  ┃                                                 ┃\n"
            "  ┃  FACTIONS: imperium chaos_cult xenos_horde      ┃\n"
            "  ┃  machine_collective  free_traders void_covenant ┃\n"
            "  ┃  RACES: human mutant xenos_bio machine_cult     ┃\n"
            "  ┃         voidborn                                ┃\n"
            "  ┃                                                 ┃\n"
            "  ┃  Rep < -20 = trade blocked (use blackmarket)    ┃\n"
            "  ┃  Contraband flagged per faction/religion        ┃\n"
            "  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
        )

    def render_news_screen(self):
        g = self.galaxy
        s = self.ship
        nt = ["┌" + "─" * 58 + "┐"]
        nt.append("│" + "GALAXY NEWS".center(58) + "│")
        nt.append("├" + "─" * 58 + "┤")
        if g.news:
            nt.append("│" + "── Latest Reports ──".center(58) + "│")
            for e in g.news[-6:]:
                tag = f"[T{e.turn}]"
                nt.append(f"│ {tag:<6} {e.headline:<20}{e.body:<30}│")
        else:
            nt.append("│  (no news)                                          │")
        nt.append("├" + "─" * 58 + "┤")
        wars = []
        truces = []
        for f1 in sorted(g.diplomacy):
            for f2, rel in g.diplomacy[f1].items():
                if f1 < f2:
                    name1 = FACTIONS.get(f1, {}).get("name", f1)
                    name2 = FACTIONS.get(f2, {}).get("name", f2)
                    entry = f"{name1} vs {name2}"
                    if rel == "war":
                        wars.append(entry)
                    elif rel in ("truce", "alliance"):
                        truces.append(entry)
        nt.append("│" + "── Diplomacy ──".center(58) + "│")
        if wars:
            for w in wars[:4]:
                nt.append(f"│  ⚔ {w:<53}│")
        if truces:
            for tr in truces[:4]:
                nt.append(f"│  ☮ {tr:<53}│")
        if not wars and not truces:
            nt.append("│  (no active conflicts)                              │")
        nt.append("├" + "─" * 58 + "┤")
        nt.append("│" + "── Active Missions ──".center(58) + "│")
        if s.missions:
            for m in s.missions:
                name = RESOURCES.get(m.resource, {}).get("name", m.resource)
                nt.append(f"│  → {m.amount}x {name:<12} → {m.target_station:<15} +{m.reward}cr  │")
        else:
            nt.append("│  (no active missions — visit stations for contracts)│")
        nt.append("├" + "─" * 58 + "┤")
        nt.append("│" + "── Market Snapshot (nearby) ──".center(58) + "│")
        stations_near = g.stations_in_range(
            self.player_x, self.player_y, 15)
        if stations_near:
            for st in stations_near[:5]:
                summary = st.price_summary()
                nt.append(f"│  {summary[:56]}")
        else:
            nt.append("│  (no stations within scan range)                    │")
        nt.append("└" + "─" * 58 + "┘")
        nt.append("  Press N or Esc to close")
        return "\n".join(nt)

    def render_pause_overlay(self, map_lines):
        ov = [
            "", "  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
            "  ┃          PAUSED              ┃",
            "  ┃                            ┃",
            "  ┃    C  —  Continue             ┃",
            "  ┃    R  —  Restart             ┃",
            "  ┃    Q  —  Quit                 ┃",
            "  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
        ]
        lines = map_lines[:]
        cy = len(lines) // 2 - len(ov) // 2
        for i, o in enumerate(ov):
            idx = cy + i
            if 0 <= idx < len(lines):
                pad = max(0, len(lines[0]) - len(o)) // 2
                lines[idx] = lines[idx][:pad] + o + lines[idx][pad + len(o):]
        return "\n".join(lines)

    def render_game_over_screen(self, map_lines):
        cause = self.death_cause or f"{self.ship.name} lost."
        if len(cause) > 36:
            cause = cause[:33] + "..."
        lines = map_lines[:]
        ov = [
            "  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
            "  ┃         GAME OVER            ┃",
            "  ┃                            ┃",
            f"  ┃  {cause:^30}  ┃",
            "  ┃                            ┃",
            "  ┃    R  —  Restart              ┃",
            "  ┃    Q  —  Quit                 ┃",
            "  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
        ]
        cy = len(lines) // 2 - len(ov) // 2
        for i, o in enumerate(ov):
            idx = cy + i
            if 0 <= idx < len(lines):
                pad = max(0, len(lines[0]) - len(o)) // 2
                lines[idx] = lines[idx][:pad] + o + lines[idx][pad + len(o):]
        return "\n".join(lines)

    def render_interaction_menu(self, map_lines):
        lines = map_lines[:]
        acts = self.interaction_actions or [("", "Nothing.", "", "")]
        bw = 50
        ov = [
            "┌" + "─" * (bw - 2) + "┐",
            "│" + "ACTIONS".center(bw - 2) + "│",
            "├" + "─" * (bw - 2) + "┤",
        ]
        for k, l, _, _ in acts:
            clean = l[:bw - 8]
            ov.append(f"│  {clean:<{bw - 6}}  │")
        ov.append("├" + "─" * (bw - 2) + "┤")
        ov.append("│" + "Esc=Close".center(bw - 2) + "│")
        ov.append("└" + "─" * (bw - 2) + "┘")
        cy = max(2, len(lines) // 2 - len(ov) // 2)
        for i, o in enumerate(ov):
            idx = cy + i
            if 0 <= idx < len(lines):
                ln = lines[idx]
                pad = max(0, len(ln) - len(o)) // 2
                lines[idx] = ln[:pad] + o + ln[pad + len(o):]
        return "\n".join(lines)

    # -------------------------------------------------------------------
    # Map rendering
    # -------------------------------------------------------------------

    def build_map_lines(self):
        lines = []
        show = (self.state in (GameState.PLAYING, GameState.INSPECTING)
                or self._interaction_active)
        nc = {}
        for t in self.galaxy.traders:
            if t.alive:
                nc[(t.x, t.y)] = TILE_TRADER
        for p in self.galaxy.pirates:
            if p.alive:
                nc[(p.x, p.y)] = TILE_PIRATE
        for y in range(self.galaxy.height):
            line = ""
            for x in range(self.galaxy.width):
                if x == self.player_x and y == self.player_y and show:
                    line += TILE_SHIP
                elif (self.state == GameState.INSPECTING
                      and x == self.cursor_x and y == self.cursor_y):
                    line += TILE_CURSOR
                elif (x, y) in nc:
                    line += nc[(x, y)]
                else:
                    line += self.galaxy.get_tile(x, y)
            lines.append(line)
        return lines

    def get_map_display(self):
        """Returns the appropriate map content string for the current state."""
        if self.state == GameState.RACE_SELECT:
            return self.render_start_screen()
        elif self.state == GameState.HELP:
            return self.render_help_screen()
        elif self.state == GameState.NEWS:
            return self.render_news_screen()
        elif self.state == GameState.START_SCREEN:
            return self.render_start_screen()
        elif self._interaction_active:
            return self.render_interaction_menu(self.build_map_lines())
        elif self.state == GameState.PAUSED:
            return self.render_pause_overlay(self.build_map_lines())
        elif self.state == GameState.GAME_OVER:
            return self.render_game_over_screen(self.build_map_lines())
        else:
            return "\n".join(self.build_map_lines())

    # -------------------------------------------------------------------
    # Info panel helpers
    # -------------------------------------------------------------------

    def _scan_nearby(self):
        radius = int(self.ship.get_effective_stats().get("sensor_range", 7))
        found = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = self.player_x + dx, self.player_y + dy
                dist = max(abs(dx), abs(dy))
                dk = (1 if dx > 0 else -1 if dx < 0 else 0,
                      1 if dy > 0 else -1 if dy < 0 else 0)
                d = DIR_LABELS[dk]
                npc = self.galaxy.get_npc_at(nx, ny)
                if npc:
                    tag = TILE_TRADER if isinstance(npc, TraderShip) else TILE_PIRATE
                    found.append(f"{d}:{tag}({dist})[{npc.name}]")
                    continue
                obj = self.galaxy.objects.get((nx, ny))
                if obj is None:
                    continue
                icon = {"star": TILE_STAR, "planet": TILE_PLANET,
                        "station": TILE_STATION, "black_hole": TILE_BLACK_HOLE,
                        "wormhole": TILE_WORMHOLE,
                        "asteroids": TILE_ASTEROIDS}.get(obj, "?")
                e = f"{d}:{icon}({dist})"
                if obj == "station" and dist <= 1:
                    st = self.galaxy.get_station_at(nx, ny)
                    if st:
                        e += f"[{st.name}|{st.faction}]"
                found.append(e)
        if not found:
            return "  Nothing within scan range"

        def _sort_key(s):
            try:
                return int(s.split("(")[1].split(")")[0])
            except Exception:
                return 99
        found.sort(key=_sort_key)
        return "  " + "  ".join(found[:8])

    def _get_ship_status(self):
        eff = []
        px, py = self.player_x, self.player_y
        for bh_x, bh_y in self.galaxy.black_holes:
            dist = max(abs(px - bh_x), abs(py - bh_y))
            dk = (1 if bh_x > px else -1 if bh_x < px else 0,
                  1 if bh_y > py else -1 if bh_y < py else 0)
            dl = DIR_LABELS.get(dk, "?")
            if self.ship.race == "voidborn":
                continue
            if 0 < dist <= 3:
                eff.append(f"⚠Gravity {dl}-{dist}")
            elif 3 < dist <= 5:
                eff.append(f"○Gravity {dl}-{dist}")
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                if self.galaxy.objects.get((px + dx, py + dy)) == "star":
                    eff.append("⚠Radiation")
                    break
        if self.galaxy.objects.get((px, py)) == "asteroids":
            eff.append("⚠Asteroids")
        for wx, wy in self.galaxy.wormholes:
            if max(abs(px - wx), abs(py - wy)) <= 2:
                eff.append("○Wormhole")
                break
        return eff

    def _cargo_summary(self):
        if not self.ship.cargo.items:
            return "Cargo: empty"
        parts = [
            f"{RESOURCES.get(r, {}).get('name', r)}:{a}"
            for r, a in sorted(self.ship.cargo.items.items())
        ]
        cb = self.ship.get_effective_stats().get("cargo_bonus", 0)
        return (f"Cargo: {'  '.join(parts)}  "
                f"({self.ship.cargo.used()}/{self.ship.cargo.capacity + cb})")

    def _reputation_summary(self):
        return "  ".join(
            f"{k}:{v}" for k, v in self.ship.reputation.items() if k in FACTIONS
        )

    def get_info_panel(self):
        """Returns (info_text, log_text) tuple for the current state."""
        if self.state in (GameState.RACE_SELECT, GameState.START_SCREEN):
            if self._show_race_select:
                return ("Pick a race. 1-5 or Enter. 0=Back", "")
            else:
                return ("N=New Game  B=Quick Battle  E=Quick Expedition  H=Help  Q=Quit", "")
        if self.state == GameState.HELP:
            return ("H to return.", "")
        if self.state == GameState.NEWS:
            return ("N to close.", "")
        if self._interaction_active:
            return ("Select or Esc.", self.logger.render(10))
        if self.state == GameState.PAUSED:
            return ("PAUSED", "")
        if self.state == GameState.GAME_OVER:
            return (
                f"☠ {self.death_cause or 'Destroyed.'}  R=Restart Q=Quit",
                self.logger.render(10),
            )
        if self.state == GameState.INSPECTING:
            cx, cy = self.cursor_x, self.cursor_y
            desc = self.galaxy.get_object_info(cx, cy)
            dist = max(abs(cx - self.player_x), abs(cy - self.player_y))
            extra = ""
            st = self.galaxy.get_station_at(cx, cy)
            if st:
                extra = f"\n{st.price_summary()}"
            npc = self.galaxy.get_npc_at(cx, cy)
            if npc:
                extra = f"\nFaction:{npc.faction} Hull:{npc.hull}/{npc.max_hull}"
            return (
                f"Inspect: ({cx},{cy}) {desc}\nDist:{dist}{extra}",
                self.logger.render(10),
            )

        # PLAYING
        desc = self.galaxy.get_object_info(self.player_x, self.player_y)
        stats = self.ship.get_effective_stats()
        rn = RACES.get(self.ship.race, {}).get("name", "Human")
        rl = self.ship.religion or "none"
        max_h = self.ship.max_hull + stats.get("hull_bonus", 0)
        shield_cap = stats.get("shield_cap", 0)
        cargo = self._cargo_summary()
        cval = self.ship.cargo.total_value()
        rep = self._reputation_summary()
        sl = self._get_ship_status()
        sline = " | ".join(sl) if sl else "Nominal"
        stn = self.galaxy.get_nearest_station(self.player_x, self.player_y, 1)
        econ = "│ " + stn.price_summary() + "\n" if stn else ""

        info = (
            f"┌─ {self.ship.name} [{rn}]  ({self.player_x},{self.player_y}) {desc} ───┐\n"
            f"│ H:{self.ship.hull}/{max_h}  "
            f"🛡{self.ship.shield_hp}/{shield_cap}  "
            f"⛽{self.ship.fuel}  💰{self.ship.credits}cr  "
            f"Rel:{rl}                 │\n"
            f"│ {cargo}                │\n"
            f"│ Val:{cval}cr                                        │\n"
            f"│ Rep: {rep}             │\n"
            f"│ {sline[:52]}               │\n"
            f"{econ}"
            f"└{'─' * 52}┘"
        )
        return (info, self._get_log_display())

    # -------------------------------------------------------------------
    # Log helpers
    # -------------------------------------------------------------------

    def _log_filter_options(self):
        return [None] + list(LogCategory)

    def cycle_log_filter(self):
        opts = self._log_filter_options()
        self.log_filter_index = (self.log_filter_index + 1) % len(opts)
        self.log_category_filter = opts[self.log_filter_index]

    def _log_filter_label(self):
        cf = self.log_category_filter
        if cf is None:
            return "All"
        return CATEGORY_LABEL.get(cf, "?")

    def _get_log_display(self):
        rendered = self.logger.render(n=8, category=self.log_category_filter)
        label = self._log_filter_label()
        filter_bar = f"[bold]Log:[/] /{label}/  [dim]Press [/][bold]/[/][dim] to filter[/dim]"
        return f"{filter_bar}\n{rendered}" if rendered else filter_bar

    def handle_log_command(self, p: list[str]):
        if len(p) >= 2:
            sub = p[1].lower()
            if sub == "filter" and len(p) >= 3:
                f = p[2].lower()
                found = None
                for cat in LogCategory:
                    if CATEGORY_LABEL.get(cat, "").lower() == f or cat.name.lower() == f:
                        found = cat; break
                if f == "all":
                    self.log_category_filter = None
                    self.logger.system("Log filter: All")
                elif found is not None:
                    self.log_category_filter = found
                    label = CATEGORY_LABEL.get(found, found.name)
                    self.logger.system(f"Log filter: {label}")
                else:
                    self.logger.system(f"Unknown filter '{f}'. Try: all, combat, economy, ship, ...")
            elif sub == "detail" and len(p) >= 3:
                d = p[2].lower()
                mapping = {"low": DetailLevel.LOW, "medium": DetailLevel.MEDIUM,
                           "high": DetailLevel.HIGH, "debug": DetailLevel.DEBUG}
                if d in mapping:
                    self.logger.detail_level = mapping[d]
                    self.logger.system(f"Log detail: {d}")
                else:
                    self.logger.system("detail: low|medium|high|debug")
            elif sub == "search" and len(p) >= 3:
                query = " ".join(p[2:])
                result = self.logger.render_plain(search=query, n=10)
                if result:
                    self.logger.system(f"── Search: '{query}' ──")
                    for line in result.split("\n"):
                        self.logger.system(line)
                else:
                    self.logger.system(f"No matches for '{query}'.")
            elif sub == "clear":
                self.logger.clear()
                self.logger.system("Log cleared.")
            elif sub == "show":
                rendered = self.logger.render_plain(n=12)
                if rendered:
                    for line in rendered.split("\n"):
                        self.logger.system(line)
                else:
                    self.logger.system("Log empty.")
            else:
                rendered = self.logger.render_plain(n=12)
                if rendered:
                    for line in rendered.split("\n"):
                        self.logger.system(line)
                else:
                    self.logger.system("Log empty.")
        else:
            rendered = self.logger.render_plain(n=12)
            if rendered:
                for line in rendered.split("\n"):
                    self.logger.system(line)
            else:
                self.logger.system("Log empty.")

    # -------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------

    def _log_event(self, m):
        ml = m.lower()
        if "radiation" in ml or "collision" in ml:
            self.logger.combat(m)
        elif any(x in ml for x in ("gravity", "pulled", "destroyed", "attack", "stole")):
            self.logger.danger(m)
        elif "[event]" in m:
            self.logger.system(m)
        else:
            self.logger.exploration(m)

    # -------------------------------------------------------------------
    # Events
    # -------------------------------------------------------------------

    def _check_political_events(self, out):
        self._politics_timer += 1
        if self._politics_timer < random.randint(30, 60):
            return
        self._politics_timer = 0
        g = self.galaxy
        et = random.choice(["crusade", "invasion", "schism", "plague", "scandal", "treaty"])
        if et == "crusade":
            g.add_news("⚔ CRUSADE!", "Imperium launches crusade against Chaos!"); out.append("[EVENT] Crusade!")
            if "chaos_cult" in g.diplomacy.get("imperium", {}):
                g.diplomacy["imperium"]["chaos_cult"] = "war"
        elif et == "invasion":
            count = random.randint(3, 5)
            for _ in range(count):
                x, y = g._random_passable()
                g.pirates.append(PirateShip(x, y))
            g.add_news(f"☠ RAID!", f"{count} pirate ships spawned in the sector."); out.append("[EVENT] Invasion!")
        elif et == "schism":
            count = 0
            for s in g.stations:
                if s.faction == "imperium" and random.random() < 0.3:
                    s.crisis_ticks = 10
                    count += 1
            g.add_news("⛪ SCHISM!", f"Imperium church divided! {count} stations in crisis."); out.append("[EVENT] Schism!")
        elif et == "plague":
            t = random.choice(list(FACTIONS))
            count = 0
            for s in g.stations:
                if s.faction == t:
                    s.crisis_ticks = 10
                    count += 1
            name = FACTIONS.get(t, {}).get("name", t)
            g.add_news(f"☣ PLAGUE at {name}!", f"{count} {name} stations quarantined."); out.append(f"[EVENT] Plague at {t}!")
        elif et == "scandal":
            f1, f2 = random.sample(list(FACTIONS), 2)
            if f2 in g.diplomacy.get(f1, {}):
                g.diplomacy[f1][f2] = "war"
                if f1 in g.diplomacy.get(f2, {}):
                    g.diplomacy[f2][f1] = "war"
            name1 = FACTIONS.get(f1, {}).get("name", f1)
            name2 = FACTIONS.get(f2, {}).get("name", f2)
            g.add_news(f"🔥 SCANDAL!", f"{name1} declares war on {name2}!"); out.append("[EVENT] Scandal!")
        elif et == "treaty":
            f1, f2 = random.sample(list(FACTIONS), 2)
            if f2 in g.diplomacy.get(f1, {}):
                g.diplomacy[f1][f2] = "truce"
                if f1 in g.diplomacy.get(f2, {}):
                    g.diplomacy[f2][f1] = "truce"
            name1 = FACTIONS.get(f1, {}).get("name", f1)
            name2 = FACTIONS.get(f2, {}).get("name", f2)
            g.add_news(f"☮ TREATY!", f"{name1} and {name2} sign truce."); out.append("[EVENT] Treaty!")

    def _check_random_events(self, out):
        if random.random() > 0.03:
            return
        g = self.galaxy
        et = random.choice(["caravan", "raid", "supernova", "crisis"])
        if et == "caravan":
            for _ in range(3):
                x, y = g._random_passable()
                rt = random.sample(range(len(g.stations)),
                                   min(3, len(g.stations))) if g.stations else []
                t = TraderShip(x, y, rt)
                t.cargo = CargoHold(100)
                t.cargo.add("relic", random.randint(1, 3))
                t.cargo.add("electronics", random.randint(5, 15))
                g.traders.append(t)
            g.add_news("Caravan!", "Rare goods."); out.append("[EVENT] Caravan!")
        elif et == "raid":
            for _ in range(random.randint(2, 4)):
                x, y = g._random_passable()
                g.pirates.append(PirateShip(x, y))
            g.add_news("Raid!", "Pirates."); out.append("[EVENT] Raid!")
        elif et == "supernova" and g.black_holes:
            bh = random.choice(g.black_holes)
            if max(abs(self.player_x - bh[0]), abs(self.player_y - bh[1])) <= 10:
                self.ship.take_damage(10)
                out.append("Supernova! Hull -10.")
                if self.ship.hull <= 0:
                    self.death_cause = "Supernova."
            g.add_news("Supernova!", "Star exploded!"); out.append("[EVENT] Supernova!")
        elif et == "crisis":
            g.global_crisis_ticks = 10
            g.add_news("Crisis!", "Prices -30%."); out.append("[EVENT] Crisis!")

    # -------------------------------------------------------------------
    # Interactions
    # -------------------------------------------------------------------

    def get_available_interactions(self):
        acts = []
        px, py = self.player_x, self.player_y

        def add(ot, x, y, dx, dy):
            dn = self._direction_name(dx, dy) if (dx or dy) else "here"
            nm, ic = self.OBJ_LABELS.get(ot, (ot.capitalize(), "?"))
            if ot == "station" and dx == 0 and dy == 0:
                st = self.galaxy.get_station_at(x, y)
                tag = f"[{st.faction}]" if st else ""
                acts.append(("r", f"(R)efuel-50cr {tag}", "refuel", f"Station {dn}"))
                acts.append(("h", f"Repair(H)ull-30cr {tag}", "repair", f"Station {dn}"))
                acts.append(("b", f"(B)uy/Sell {tag}", "trade", f"Station {dn}"))
                if st and st.stype == "temple" and self.ship.religion is None:
                    acts.append(("j", f"(J)oin {st.name}", "religion", f"Temple {dn}"))
                if st and st.modules_for_sale:
                    acts.append(("p", f"Shop (P)arts [{len(st.modules_for_sale)} modules]", "modules_shop", f"Station {dn}"))
                if st and st.stype == "shipyard":
                    acts.append(("y", f"(Y)ard — hulls/modules/upgrades", "shipyard", f"Shipyard {dn}"))
                if st and st.stype == "workshop":
                    acts.append(("k", f"Wor(K)shop — craft {len(st.recipes_available)} items", "workshop", f"Workshop {dn}"))
                if st and st.stype == "tavern":
                    acts.append(("t", f"(T)avern — hire crew [{len(st.crew_for_hire)} available]", "tavern", f"Tavern {dn}"))
                if st and st.missions:
                    acts.append(("v", f"Miss(V)ons [{len(st.missions)} available]", "missions", f"Station {dn}"))
            elif ot == "planet":
                acts.append(("s", f"(S)can {ic} {nm}", "scan_planet", f"{nm} {dn}"))
                acts.append(("l", f"(L)and {ic}", "land", f"{nm} {dn}"))
            elif ot == "asteroids" and dx == 0 and dy == 0:
                acts.append(("m", f"(M)ine {ic}", "mine", f"{nm} {dn}"))
            elif ot == "wormhole" and dx == 0 and dy == 0:
                acts.append(("u", f"(U)se Wormhole {ic}", "wormhole", f"{nm} {dn}"))

        for t in self.galaxy.traders:
            if t.alive and max(abs(t.x - px), abs(t.y - py)) <= 1:
                nn = self._direction_name(t.x - px, t.y - py) if (t.x != px or t.y != py) else ""
                acts.append(("c", f"(C)hat {t.name}[{t.faction}]", "hail_npc", f"Trader {nn}"))
        rng = self.ship.get_effective_stats().get("range", 1)
        for p in self.galaxy.pirates:
            if p.alive and max(abs(p.x - px), abs(p.y - py)) <= rng:
                nn = self._direction_name(p.x - px, p.y - py) if (p.x != px or p.y != py) else ""
                acts.append(("f", f"(F)ight {p.name} [{nn}]", "battle_pirate", f"Pirate {nn}"))

        ob = self.galaxy.objects.get((px, py))
        if ob:
            add(ob, px, py, 0, 0)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nob = self.galaxy.objects.get((px + dx, py + dy))
                if nob:
                    add(nob, px + dx, py + dy, dx, dy)
        return acts

    def run_interaction(self, action_id):
        """Execute an interaction by action_id. Returns screen to push or None."""
        method_name = f"_act_{action_id}"
        handler = getattr(self, method_name, None)
        if handler:
            result = handler()
            if self.state != GameState.GAME_OVER:
                self.state = GameState.PLAYING
            return result
        return None

    # --- Interaction handlers ---

    def _act_refuel(self):
        if self.ship.credits >= 50:
            self.ship.credits -= 50
            self.ship.fuel = min(100, self.ship.fuel + 20)
            self.logger.trade(f"Refuel +20. Fuel:{self.ship.fuel}")
        else:
            self.logger.system("Need 50cr.")

    def _act_repair(self):
        if self.ship.credits >= 30:
            self.ship.credits -= 30
            max_hull = 100 + self.ship.get_effective_stats().get("hull_bonus", 0)
            o = self.ship.hull
            self.ship.hull = min(max_hull, self.ship.hull + 15)
            self.logger.trade(f"Hull +{self.ship.hull - o}.")
        else:
            self.logger.system("Need 30cr.")

    def _act_trade(self):
        st = self.galaxy.get_station_at(self.player_x, self.player_y)
        if st:
            return ("TradeScreen", st)
        self.logger.system("No station.")

    def _act_religion(self):
        st = self.galaxy.get_station_at(self.player_x, self.player_y)
        if not st or st.stype != "temple":
            return
        if self.ship.religion:
            self.logger.system("Already have religion.")
            return
        if st.religion:
            self.ship.religion = st.religion
            self.logger.system(f"Joined {st.religion}!")
        else:
            self.logger.system("No doctrine.")

    def _act_modules_shop(self):
        st = self.galaxy.get_station_at(self.player_x, self.player_y)
        if st and st.modules_for_sale:
            return ("ModuleShopScreen", st)
        self.logger.system("No modules for sale.")

    def _act_missions(self):
        st = self.galaxy.get_station_at(self.player_x, self.player_y)
        if st and st.missions:
            return ("MissionScreen", st)
        self.logger.system("No missions.")

    def _act_shipyard(self):
        st = self.galaxy.get_station_at(self.player_x, self.player_y)
        if st and st.stype == "shipyard":
            return ("ShipyardScreen", st)
        self.logger.system("No shipyard.")

    def _act_workshop(self):
        st = self.galaxy.get_station_at(self.player_x, self.player_y)
        if st and st.stype == "workshop":
            return ("CraftingScreen", st)
        self.logger.system("No workshop.")

    def _act_tavern(self):
        st = self.galaxy.get_station_at(self.player_x, self.player_y)
        if st and st.stype == "tavern":
            return ("HireScreen", st)
        self.logger.system("No tavern.")

    def _act_scan_planet(self):
        self.logger.exploration(
            f"Scan: {random.choice(['rocky','gas giant','ice','desert','oceanic'])}, "
            f"{random.choice(['iron','silicon','water ice','minerals'])}."
        )

    def _act_land(self):
        outcomes = [
            ("Ruins +50cr", 50, ""), ("Wildlife! Hull-5", -5, ""),
            ("Resources +30cr", 30, ""), ("Storm! Hull-8", -8, ""),
            ("Traded +20cr", 20, ""), ("Minerals +2ore", 0, "ore"),
        ]
        msg, delta, cid = random.choice(outcomes)
        if delta > 0:
            self.ship.credits += delta
        elif delta < 0:
            self.ship.take_damage(-delta)
        if cid and not self.ship.cargo.add(cid, 2):
            msg += " (full)"
        self.logger.exploration(f"Landed. {msg}")
        if self.ship.hull <= 0:
            self.state = GameState.GAME_OVER
            self.death_cause = "Killed on planet."

    def _act_mine(self):
        if random.random() < 0.6:
            amt = random.randint(2, 6)
            if self.ship.cargo.add("ore", amt):
                self.logger.exploration(
                    f"Mined {amt} ore ({self.ship.cargo.used()}/{self.ship.cargo.capacity})")
            else:
                self.logger.exploration("Cargo full!")
        else:
            self.logger.exploration("Depleted.")

    def _act_wormhole(self):
        if len(self.galaxy.wormholes) > 1:
            o = (self.player_x, self.player_y)
            while o == (self.player_x, self.player_y):
                o = random.choice(self.galaxy.wormholes)
            self.player_x, self.player_y = o
            self.logger.exploration("Teleported!")
            self.logger.new_turn()
        else:
            self.logger.exploration("Collapse!")
            px, py = self.player_x, self.player_y
            self.galaxy.tiles[py][px] = TILE_EMPTY
            self.galaxy.objects.pop((px, py), None)
            self.galaxy.wormholes = [w for w in self.galaxy.wormholes if w != (px, py)]

    def _act_hail_npc(self):
        for t in self.galaxy.traders:
            if t.alive and max(abs(t.x - self.player_x), abs(t.y - self.player_y)) <= 1:
                self.logger.exploration(
                    f"Trader {t.name}[{t.faction}]: Hull {t.hull}/{t.max_hull}")
                return
        for p in self.galaxy.pirates:
            if p.alive and max(abs(p.x - self.player_x), abs(p.y - self.player_y)) <= 1:
                self.logger.danger(f"Pirate {p.name}: 'Back off!'")
                return
        self.logger.system("No NPC.")

    def _act_battle_pirate(self):
        rng = self.ship.get_effective_stats().get("range", 1)
        for p in self.galaxy.pirates:
            if p.alive and max(abs(p.x - self.player_x), abs(p.y - self.player_y)) <= rng:
                return ("BattleScreen", p)
        self.logger.system("No pirate.")

    # --- Colony ---

    def try_landing(self):
        tile = self.galaxy.tiles[self.player_y][self.player_x]
        TILE_TO_SITE = {"o": "planet", "÷": "asteroid", "◈": "station"}
        st = self.galaxy.get_station_at(self.player_x, self.player_y)
        if st:
            site_type = st.stype
            site_name = st.name
        else:
            site_type = TILE_TO_SITE.get(tile)
            site_name = f"{tile} at ({self.player_x},{self.player_y})"
        if not site_type:
            self.logger.system("Nothing to land on here.")
            return None
        return ("LandingPrepScreen", site_type, site_name)

    def open_colony(self):
        px, py = self.player_x, self.player_y
        colony = self.galaxy.colonies.get((px, py))
        if colony:
            return ("PlanetSurfaceScreen", colony, px, py)

    def found_colony(self):
        px, py = self.player_x, self.player_y
        if not self.galaxy.objects.get((px, py)) == "planet":
            self.logger.system("Not on a planet tile.")
            return
        if (px, py) in self.galaxy.colonies:
            self.logger.system("Colony already exists here! Press C to open it.")
            return
        if not self.ship.cargo.has("colony_starter"):
            self.logger.system("Need a Colony Starter Kit to found a colony! "
                             "Craft one at a Workshop (metal:10, electronics:8, silicon:5, shield_mod:2).")
            return
        planet_type = self.galaxy.planet_types.get((px, py), "temperate")
        planet_info = PLANET_TYPES.get(planet_type, {})
        if planet_info.get("orbit_only"):
            self.logger.system(f"Cannot colonize {planet_info['name']} — orbit only.")
            return
        self.ship.cargo.remove("colony_starter", 1)
        colony_name = f"Colony-{planet_info.get('name', planet_type)}"
        colony = ColonyManager(colony_name, planet_type)
        self.galaxy.colonies[(px, py)] = colony
        center = SURFACE_SIZE // 2
        colony.storage["metal"] = 10
        colony.storage["electronics"] = 5
        colony.storage["silicon"] = 3
        colony.colonists = 5
        colony.max_colonists = 5
        colony.place_building("command_center", center - 1, center - 1)
        self.logger.system(f"🏗 Colony founded on {planet_info['name']} planet!")
        self.logger.system("Press C to open colony surface.")
        self.logger.system(f"Name: {colony_name}")
        self.logger.system("Initial colonists: 5")

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    @staticmethod
    def _roll_hit(accuracy, evasion):
        chance = max(5, min(95, accuracy - evasion))
        return random.random() * 100 < chance

    @staticmethod
    def _direction_name(dx, dy):
        return DIR_LABELS.get((dx, dy), "?")

    # -------------------------------------------------------------------
    # Movement & world tick
    # -------------------------------------------------------------------

    def move_player(self, dx, dy):
        """Move player. Returns (should_advance_world, pending_battle_enemy_or_none)."""
        if self.state != GameState.PLAYING:
            return (False, None)
        dn = self._direction_name(dx, dy)
        speed = max(1, self.ship.get_effective_stats().get("speed", 1))
        moved = 0
        for _ in range(speed):
            nx, ny = self.player_x + dx, self.player_y + dy
            if not (0 <= nx < self.galaxy.width and 0 <= ny < self.galaxy.height):
                break
            tt = self.galaxy.get_tile(nx, ny)
            if not self.galaxy.is_passable(nx, ny):
                if moved == 0:
                    self.logger.blocked(dn, self.galaxy.get_object_info(nx, ny))
                break
            if tt == TILE_WORMHOLE:
                if len(self.galaxy.wormholes) > 1:
                    o = (nx, ny)
                    while o == (nx, ny):
                        o = random.choice(self.galaxy.wormholes)
                    nx, ny = o
                    self.logger.exploration("Teleported!")
                else:
                    self.logger.exploration("Collapse.")
                    self.galaxy.tiles[ny][nx] = TILE_EMPTY
                    self.galaxy.objects.pop((nx, ny), None)
                    self.galaxy.wormholes = [w for w in self.galaxy.wormholes if w != (nx, ny)]
            self.player_x, self.player_y = nx, ny
            moved += 1
        if moved > 0:
            self.ship.fuel = max(0, self.ship.fuel - 1)
            self.logger.movement(dn, self.player_x, self.player_y)
            return (True, self._pending_battle)
        return (False, None)

    def tick_world(self):
        self.logger.new_turn()
        self.ship.regen_shields()
        failed = self.ship.fail_expired_missions(self.galaxy.news)
        for m in failed:
            self.logger.system(f"⚠ Mission expired: {m.title}")
        nx, ny, evs, over = self.galaxy.tick(self.player_x, self.player_y, self.ship)
        self.player_x, self.player_y = nx, ny
        for ev in evs:
            self._log_event(ev)
        npc_ev = []
        self.galaxy.step_npc(self.player_x, self.player_y, self.ship, npc_ev)
        for ev in npc_ev:
            self._log_event(ev)
        for ev in npc_ev:
            if ev.startswith("__BATTLE__:"):
                uid = int(ev.split(":")[1])
                for p in self.galaxy.pirates:
                    if p.uid == uid and p.alive:
                        self._pending_battle = p
                        break
        dm = self.ship._last_damaged_module
        if dm:
            if dm.is_broken():
                self.logger.danger(f"{dm.name} BROKEN! dur:0/{dm.max_durability}")
            else:
                self.logger.danger(f"{dm.name} damaged! dur:{dm.durability}/{dm.max_durability}")
            self.ship._last_damaged_module = None
        pol_ev = []
        self._check_political_events(pol_ev)
        for ev in pol_ev:
            self._log_event(ev)
        rand_ev = []
        self._check_random_events(rand_ev)
        for ev in rand_ev:
            self._log_event(ev)
        if over:
            self.state = GameState.GAME_OVER
            self.death_cause = evs[-1] if evs else "Unknown"
            self.logger.danger("Destroyed.")
        st = self.galaxy.get_station_at(self.player_x, self.player_y)
        if st:
            completed = self.ship.check_missions(st)
            for _, msg in completed:
                self.logger.trade(msg)

    # -------------------------------------------------------------------
    # Console commands
    # -------------------------------------------------------------------

    def process_command(self, raw):
        """Parse and execute a console command. Returns list of system messages."""
        self.logger.system(f"> {raw}")
        p = re.split(r"\s+", raw.strip())
        if not p or not p[0]:
            return
        c = p[0].lower()
        if c == "help":
            self.logger.system("scan | inv[entory] | give <res> [amt] | take <res> [amt]")
            self.logger.system("refuel | set hull <n> | trade buy/sell <res> [amt]")
            self.logger.system("prices | market scan [r] | market history <st> <res>")
            self.logger.system("power <comp> <val> | modules list | cargo jettison <res> [amt]")
            self.logger.system("cargo sellall | reputation | diplomacy | declare war <fac>")
            self.logger.system("attack <name> | hail | smuggle <res> <amt> | news")
            self.logger.system("log [filter <cat>|detail <lvl>|search <text>|clear|show]")
            self.logger.system("save | exit")
        elif c in ("scan", "l"):  # quick radar
            info = self._scan_nearby()
            for line in info.split("\n"):
                self.logger.system(line)
        elif c in ("inv", "inventory"):
            cb = self.ship.get_effective_stats().get("cargo_bonus", 0)
            total_cap = self.ship.cargo.capacity + cb
            self.logger.system(f"Cargo: {self.ship.cargo.used()}/{total_cap}")
            for r, a in sorted(self.ship.cargo.items.items()):
                name = RESOURCES.get(r, {}).get("name", r)
                self.logger.system(f"  {name}: {a}")
        elif c == "give":
            if len(p) >= 2:
                rid = p[1].lower()
                amt = int(p[2]) if len(p) >= 3 else 1
                if rid in RESOURCES:
                    self.ship.cargo.add(rid, amt)
                    name = RESOURCES[rid]["name"]
                    self.logger.system(f"+{amt} {name}.")
                else:
                    self.logger.system(f"Unknown '{rid}'.")
        elif c == "take":
            if len(p) >= 2:
                rid = p[1].lower()
                amt = int(p[2]) if len(p) >= 3 else 1
                if rid in RESOURCES:
                    self.ship.cargo.remove(rid, amt)
                    name = RESOURCES[rid]["name"]
                    self.logger.system(f"-{amt} {name}.")
                else:
                    self.logger.system(f"Unknown '{rid}'.")
        elif c == "set" and len(p) >= 3:
            if p[1] == "hull":
                self.ship.hull = max(1, int(p[2]))
                self.logger.system(f"Hull={self.ship.hull}.")
        elif c == "refuel":
            self.ship.fuel = 100
            self.logger.system("Fuel=100")
        elif c in ("trade", "tr"):
            self._handle_trade_command(p)
        elif c == "prices":
            st = self.galaxy.get_station_at(self.player_x, self.player_y)
            if st:
                for rid, (bp, sp) in sorted(st.prices.items()):
                    name = RESOURCES.get(rid, {}).get("name", rid)
                    self.logger.system(f"  {name}: buy={bp} sell={sp}")
            else:
                self.logger.system("Not at station.")
        elif c == "market" and len(p) >= 2:
            self._handle_market_command(p)
        elif c == "power" and len(p) >= 3:
            comp = p[1].lower()
            val = int(p[2])
            if comp in self.ship.compartments:
                self.ship.compartments[comp]["power"] = max(0, min(10, val))
                self.logger.system(f"{comp} power={self.ship.compartments[comp]['power']}.")
            else:
                self.logger.system(f"Unknown compartment '{comp}'.")
        elif c in ("modules", "mods"):
            if len(p) >= 2 and p[1] == "list":
                for comp in COMPARTMENTS:
                    mods = self.ship.compartments[comp]["modules"]
                    if mods:
                        for m in mods:
                            dur = f" dur:{m.durability}/{m.max_durability}" if m.durability != m.max_durability else ""
                            lvl = f" Lv{m.level}" if m.level > 1 else ""
                            self.logger.system(f"  {comp}: {m.name}{lvl}{dur}")
        elif c == "cargo":
            if len(p) >= 2:
                sub = p[1].lower()
                if sub == "jettison" and len(p) >= 3:
                    rid = p[2].lower()
                    amt = int(p[3]) if len(p) >= 4 else 999
                    have = self.ship.cargo.has(rid)
                    amt = min(amt, have)
                    if amt > 0:
                        self.ship.cargo.remove(rid, amt)
                        self.logger.system(f"Jettisoned {amt} {rid}.")
                elif sub == "sellall":
                    st = self.galaxy.get_station_at(self.player_x, self.player_y)
                    if st:
                        msg, ok = st.buy_all_junk(self.ship)
                        self.logger.system(msg)
                    else:
                        self.logger.system("Not at station.")
        elif c == "reputation":
            for f, v in self.ship.reputation.items():
                self.logger.system(f"  {f}: {v}")
        elif c == "diplomacy":
            for f1 in sorted(self.galaxy.diplomacy):
                for f2, rel in self.galaxy.diplomacy[f1].items():
                    if f1 < f2:
                        self.logger.system(f"  {f1} vs {f2}: {rel}")
        elif c == "declare" and len(p) >= 3 and p[1] == "war":
            f = p[2].lower()
            if f in FACTIONS:
                self.ship.reputation[f] = -100
                self.logger.system(f"Declared war on {f}!")
            else:
                self.logger.system(f"Unknown faction '{f}'.")
        elif c == "attack" and len(p) >= 2:
            name = " ".join(p[1:])
            npc = self.galaxy.get_npc_by_name(name)
            if npc:
                return ("battle", npc)
            self.logger.system(f"No '{name}'.")
        elif c == "hail":
            self._act_hail_npc()
        elif c == "smuggle" and len(p) >= 3:
            rid = p[1].lower()
            amt = int(p[2])
            st = self.galaxy.get_station_at(self.player_x, self.player_y)
            if not st:
                self.logger.system("Not at station.")
            elif self.ship.cargo.has(rid) < amt:
                self.logger.system(f"Not enough {rid}.")
            else:
                info = RESOURCES.get(rid, {})
                price = info.get("base_price", 0) * 2
                total = price * amt
                self.ship.cargo.remove(rid, amt)
                self.ship.credits += total
                self.logger.system(f"Smuggled {amt} {info.get('name', rid)} for {total}cr!")
                if self.ship.reputation.get(st.faction, 0) > -50:
                    self.ship.reputation[st.faction] = self.ship.reputation.get(st.faction, 0) - 5
        elif c == "news":
            for e in self.galaxy.news[-5:]:
                self.logger.system(f"  [T{e.turn}] {e.headline}: {e.body}")
        elif c == "log":
            self.handle_log_command(p)
        elif c == "save":
            self.logger.system("Save not implemented.")
        elif c == "exit":
            return ("exit", None)

    def _handle_trade_command(self, p):
        st = self.galaxy.get_station_at(self.player_x, self.player_y)
        if not st:
            self.logger.system("Not at station."); return
        if len(p) < 3:
            self.logger.system("trade buy/sell <res> [amt]"); return
        sub = p[1].lower()
        rid = p[2].lower()
        amt = int(p[3]) if len(p) >= 4 else 1
        if sub == "buy":
            self.logger.system(st.sell_to(self.ship, rid, amt))
        elif sub == "sell":
            self.logger.system(st.buy_from(self.ship, rid, amt))

    def _handle_market_command(self, p):
        sub = p[1].lower()
        if sub == "scan":
            r = int(p[2]) if len(p) >= 3 else 12
            stations = self.galaxy.stations_in_range(self.player_x, self.player_y, r)
            if stations:
                for s in stations[:6]:
                    self.logger.system(s.price_summary())
            else:
                self.logger.system("No stations in range.")
        elif sub == "history" and len(p) >= 3:
            name = p[2].lower()
            rid = p[3].lower() if len(p) >= 4 else "metal"
            for s in self.galaxy.stations:
                if s.name.lower() == name:
                    hist = s.price_history.get(rid, [])
                    for i, (bp, sp) in enumerate(hist[-10:]):
                        self.logger.system(f"  T{i}: buy={bp} sell={sp}")
                    return
            self.logger.system(f"Station '{name}' not found.")
