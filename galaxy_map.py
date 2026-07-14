"""Galaxy Map — main app entry point."""

import random
import re
from enum import Enum, auto

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Static, Header, Footer
from textual.reactive import reactive
from textual import events

from game_logger import GameLogger
from config import (
    WIDTH, HEIGHT, RESOURCES, RACES, FACTIONS, COMPARTMENTS, CONTRABAND,
    TILE_EMPTY, TILE_STAR, TILE_PLANET, TILE_STATION, TILE_BLACK_HOLE,
    TILE_WORMHOLE, TILE_ASTEROIDS, TILE_SHIP, TILE_OTHER_SHIP,
    TILE_CURSOR, TILE_TRADER, TILE_PIRATE, DIR_LABELS,
)
from models import PlayerShip, Galaxy, TraderShip, PirateShip, CargoHold, NPCShip
import models
from ui import (
    CommandScreen, CargoScreen, TradeScreen,
    BridgeScreen, EngineeringScreen, TacticalScreen, CrewScreen,
)

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
# App
# ---------------------------------------------------------------------------

class GalaxyMapApp(App):
    CSS = """
    #map { height: 1fr; content-align: center middle; }
    #info-panel {
        height: 12; border: solid green; margin: 1 2; padding: 0 1;
        background: $surface;
    }
    #log { height: 10; border: solid yellow; margin: 1 2; padding: 0 1; color: yellow; }
    CommandScreen Input { dock: bottom; margin: 1 2; }
    CargoScreen DataTable { height: 1fr; margin: 1; }
    TradeScreen Static, BridgeScreen Static, EngineeringScreen Static,
    TacticalScreen Static, CrewScreen Static, ModuleShopScreen Static,
    MissionScreen Static {
        border: solid $primary; margin: 1; padding: 0 1;
        background: $surface;
    }
    TradeScreen Input, EngineeringScreen Input, TacticalScreen Input,
    CrewScreen Input, ModuleShopScreen Input, MissionScreen Input {
        dock: bottom; margin: 1 2;
    }
    """

    player_x = reactive(WIDTH // 2)
    player_y = reactive(HEIGHT // 2)

    def __init__(self):
        super().__init__()
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
        self._prev_state = GameState.START_SCREEN
        self._interaction_active = False
        self._init_player_position()

    def _init_player_position(self):
        self.player_x = WIDTH // 2
        self.player_y = HEIGHT // 2
        while not self.galaxy.is_passable(self.player_x, self.player_y):
            self.player_x = random.randint(0, WIDTH - 1)
            self.player_y = random.randint(0, HEIGHT - 1)

    # -----------------------------------------------------------------------
    # Race selection
    # -----------------------------------------------------------------------

    def select_race(self, choice):
        c = choice.lower().strip()
        if c in ("1", "human", ""):
            self.ship.race = "human"
        elif c in ("2", "mutant"):
            self.ship.race = "mutant"
        elif c in ("3", "xenos_bio", "xenos"):
            self.ship.race = "xenos_bio"
        elif c in ("4", "machine_cult", "machine"):
            self.ship.race = "machine_cult"
        elif c in ("5", "voidborn", "void"):
            self.ship.race = "voidborn"
        self.logger.system(f"Race: {RACES.get(self.ship.race, {}).get('name', 'Human')}.")
        self.race_selected = True
        self.state = GameState.PLAYING
        self.update_map()
        self.update_info()

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def restart_game(self):
        models.NPCShip_id_counter = 0
        self.state = GameState.RACE_SELECT
        self.galaxy = Galaxy()
        self.ship = PlayerShip("Endeavour", 100)
        self.ship.shield_hp = self.ship.get_effective_stats().get("shield_cap", 30)
        self.logger.clear()
        self.death_cause = None
        self.interaction_actions = []
        self.race_selected = False
        self._interaction_active = False
        self._init_player_position()
        self.update_map()
        self.update_info()

    def compose(self):
        yield Header()
        yield Container(Static(id="map"))
        yield Static(id="info-panel")
        yield Static(id="log")
        yield Footer()

    def on_mount(self):
        self.update_map()
        self.update_info()

    # -----------------------------------------------------------------------
    # Rendering — screens
    # -----------------------------------------------------------------------

    def render_start_screen(self):
        if self.state == GameState.RACE_SELECT:
            self.query_one("#map").update("\n".join([
                "", "",
                "  ┏━ CHOOSE RACE ━━━━━━━━━━━━━━━┓",
                "  ┃ 1 Human    2 Mutant         ┃",
                "  ┃ 3 Xenos Bio  4 Machine      ┃",
                "  ┃ 5 Voidborn                  ┃",
                "  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛", "",
                "  Press 1-5 or Enter for Human",
            ]))
            return
        self.query_one("#map").update("\n".join([
            "", "",
            "  ┏━ GALAXY MAP ━━━━━━━━━━━━━━━━━━━━━━━━┓",
            "  ┃ In the grim darkness of the far     ┃",
            "  ┃ future, there is only war.          ┃",
            "  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
            f"  Race: {RACES.get(self.ship.race, {}).get('name', 'Human')}", "",
            "  WASD Move  E Interact  I Inspect  H Help",
            "  N News  F1 Bridge  F2 Engineering  ~ Console", "",
            "  Press any key to start...",
        ]))

    def render_help_screen(self):
        lines = [
            "  ┏━ HELP ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
            "  ┃                                                 ┃",
            "  ┃  MOVEMENT:                                      ┃",
            "  ┃    W/↑ N  A/← W  S/↓ S  D/→ E                  ┃",
            "  ┃    Space = wait (advance time 1 turn)            ┃",
            "  ┃                                                 ┃",
            "  ┃  ACTIONS:                                       ┃",
            "  ┃    E = interact with nearby objects              ┃",
            "  ┃    F = fire at adjacent pirate                   ┃",
            "  ┃    I = inspect / free look around                ┃",
            "  ┃    B = open trade screen (at station)            ┃",
            "  ┃                                                 ┃",
            "  ┃  SHIP MANAGEMENT:                               ┃",
            "  ┃    F1 = Bridge (ship status, modules)           ┃",
            "  ┃    F2 = Engineering (power distribution)        ┃",
            "  ┃    F3 = Tactical (weapons, targets, fire)       ┃",
            "  ┃    F4 = Cargo inventory                          ┃",
            "  ┃    F5 = Crew (assign crew to stations)          ┃",
            "  ┃                                                 ┃",
            "  ┃  INTERFACE:                                     ┃",
            "  ┃    H = help        N = news      ~ = console    ┃",
            "  ┃    Esc = pause     Q = quit                     ┃",
            "  ┃                                                 ┃",
            "  ┃  CONSOLE COMMANDS (~):                          ┃",
            "  ┃    scan / inv / give/take / refuel / set hull   ┃",
            "  ┃    trade buy/sell / prices / market scan/history┃",
            "  ┃    power <comp> <val> / modules list            ┃",
            "  ┃    cargo / cargo jettison / cargo sellall       ┃",
            "  ┃    reputation / diplomacy / declare war         ┃",
            "  ┃    attack / hail / smuggle / news / exit        ┃",
            "  ┃                                                 ┃",
            "  ┃  FACTIONS: imperium chaos_cult xenos_horde      ┃",
            "  ┃  machine_collective  free_traders void_covenant ┃",
            "  ┃  RACES: human mutant xenos_bio machine_cult     ┃",
            "  ┃         voidborn                                ┃",
            "  ┃                                                 ┃",
            "  ┃  Rep < -20 = trade blocked (use blackmarket)    ┃",
            "  ┃  Contraband flagged per faction/religion        ┃",
            "  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
        ]
        out = ["" for _ in range(HEIGHT)]
        cy = max(0, (HEIGHT - len(lines)) // 2)
        for i, ht in enumerate(lines):
            if 0 <= cy + i < HEIGHT:
                out[cy + i] = " " * (max(0, WIDTH - len(ht)) // 2) + ht
        return "\n".join(out)

    def render_news_screen(self):
        nt = ["  ┏━ GALAXY NEWS ━━━━━━━━━━━━━━━━━━━━━━┓"]
        for e in self.galaxy.news[-8:]:
            nt.append(f"  ┃ [{e.turn}] {e.headline:<35}┃")
            nt.append(f"  ┃ {e.body:<45}┃")
        nt.append("  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
        nt.append("  Press N or any key to return")
        out = ["" for _ in range(HEIGHT)]
        cy = max(0, (HEIGHT - len(nt)) // 2)
        for i, ht in enumerate(nt):
            if 0 <= cy + i < HEIGHT:
                out[cy + i] = " " * (max(0, WIDTH - len(ht)) // 2) + ht
        return "\n".join(out)

    def render_pause_overlay(self):
        lines = self._build_map_lines()
        ov = [
            "", "  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
            "  ┃          PAUSED              ┃",
            "  ┃                            ┃",
            "  ┃    C  —  Continue             ┃",
            "  ┃    R  —  Restart             ┃",
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

    def render_game_over_screen(self):
        lines = self._build_map_lines()
        cause = self.death_cause or f"{self.ship.name} lost."
        if len(cause) > 36:
            cause = cause[:33] + "..."
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

    def render_interaction_menu(self):
        lines = self._build_map_lines()
        acts = self.interaction_actions or [("", "Nothing.", "", "")]
        bw = 44
        ov = [
            f"  ┏{'━' * (bw - 2)}┓",
            f"  ┃{'INTERACTION MENU':^{bw - 2}}┃",
            f"  ┃{'':^{bw - 2}}┃",
        ]
        for _, l, _, _ in acts:
            clean = l[:bw - 6]
            ov.append(f"  ┃  {clean:<{bw - 6}}  ┃")
        ov.extend([
            f"  ┃{'':^{bw - 2}}┃",
            f"  ┃{'Esc-Close':^{bw - 2}}┃",
            f"  ┗{'━' * (bw - 2)}┛",
        ])
        cy = len(lines) // 2 - len(ov) // 2
        for i, o in enumerate(ov):
            idx = cy + i
            if 0 <= idx < len(lines):
                pad = max(0, len(lines[0]) - len(o)) // 2
                lines[idx] = lines[idx][:pad] + o + lines[idx][pad + len(o):]
        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Map rendering helpers
    # -----------------------------------------------------------------------

    def _build_map_lines(self):
        lines = []
        show = self.state in (GameState.PLAYING, GameState.INSPECTING) or self._interaction_active
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
                elif self.state == GameState.INSPECTING and x == self.cursor_x and y == self.cursor_y:
                    line += TILE_CURSOR
                elif (x, y) in nc:
                    line += nc[(x, y)]
                else:
                    line += self.galaxy.get_tile(x, y)
            lines.append(line)
        return lines

    def update_map(self):
        if self.state == GameState.RACE_SELECT:
            self.render_start_screen()
        elif self.state == GameState.HELP:
            self.query_one("#map").update(self.render_help_screen())
        elif self.state == GameState.NEWS:
            self.query_one("#map").update(self.render_news_screen())
        elif self.state == GameState.START_SCREEN:
            self.render_start_screen()
        elif self._interaction_active:
            self.query_one("#map").update(self.render_interaction_menu())
        elif self.state == GameState.INSPECTING:
            self.query_one("#map").update("\n".join(self._build_map_lines()))
        elif self.state == GameState.PAUSED:
            self.query_one("#map").update(self.render_pause_overlay())
        elif self.state == GameState.GAME_OVER:
            self.query_one("#map").update(self.render_game_over_screen())
        else:
            self.query_one("#map").update("\n".join(self._build_map_lines()))

    # -----------------------------------------------------------------------
    # Info panel & helpers
    # -----------------------------------------------------------------------

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

    def update_info(self):
        if self.state in (GameState.RACE_SELECT, GameState.START_SCREEN):
            self.query_one("#info-panel").update("H=Help  N=News  F1=Bridge")
            self.query_one("#log").update("")
            return
        if self.state == GameState.HELP:
            self.query_one("#info-panel").update("H to return.")
            self.query_one("#log").update(""); return
        if self.state == GameState.NEWS:
            self.query_one("#info-panel").update("N to close.")
            self.query_one("#log").update(""); return
        if self._interaction_active:
            self.query_one("#info-panel").update("Select or Esc.")
            self.query_one("#log").update(self.logger.render(10)); return
        if self.state == GameState.PAUSED:
            self.query_one("#info-panel").update("PAUSED")
            self.query_one("#log").update(""); return
        if self.state == GameState.GAME_OVER:
            self.query_one("#info-panel").update(
                f"☠ {self.death_cause or 'Destroyed.'}  R=Restart Q=Quit"
            )
            self.query_one("#log").update(self.logger.render(10)); return
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
            self.query_one("#info-panel").update(
                f"Inspect: ({cx},{cy}) {desc}\nDist:{dist}{extra}")
            self.query_one("#log").update(self.logger.render(10)); return

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
        self.query_one("#info-panel").update(info)
        self.query_one("#log").update(self.logger.render(8))

    # -----------------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------------

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

    # -----------------------------------------------------------------------
    # Events
    # -----------------------------------------------------------------------

    def _check_political_events(self, out):
        self._politics_timer += 1
        if self._politics_timer < random.randint(30, 60):
            return
        self._politics_timer = 0
        g = self.galaxy
        et = random.choice(["crusade", "invasion", "schism", "plague", "scandal", "treaty"])
        if et == "crusade":
            g.add_news("Crusade!", "Imperium vs Chaos!"); out.append("[EVENT] Crusade!")
        elif et == "invasion":
            for _ in range(random.randint(3, 5)):
                x, y = g._random_passable()
                g.pirates.append(PirateShip(x, y))
            g.add_news("Invasion!", "Hostiles spawned."); out.append("[EVENT] Invasion!")
        elif et == "schism":
            for s in g.stations:
                if s.faction == "imperium" and random.random() < 0.3:
                    s.crisis_ticks = 10
            g.add_news("Schism!", "Church divided."); out.append("[EVENT] Schism!")
        elif et == "plague":
            t = random.choice(list(FACTIONS))
            for s in g.stations:
                if s.faction == t:
                    s.crisis_ticks = 10
            g.add_news(f"Plague at {t}!", f"Afflicted {t} stations."); out.append(f"[EVENT] Plague at {t}!")
        elif et == "scandal":
            f1, f2 = random.sample(list(FACTIONS), 2)
            if f2 in g.diplomacy.get(f1, {}):
                g.diplomacy[f1][f2] = "war"
            g.add_news("Scandal!", f"{f1} vs {f2} at war!"); out.append("[EVENT] Scandal!")
        elif et == "treaty":
            f1, f2 = random.sample(list(FACTIONS), 2)
            if f2 in g.diplomacy.get(f1, {}):
                g.diplomacy[f1][f2] = "truce"
            g.add_news("Treaty!", f"{f1} and {f2} sign truce."); out.append("[EVENT] Treaty!")

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

    # -----------------------------------------------------------------------
    # Interaction system
    # -----------------------------------------------------------------------

    OBJ_LABELS = {
        "planet": ("Planet", TILE_PLANET),
        "station": ("Station", TILE_STATION),
        "asteroids": ("Asteroids", TILE_ASTEROIDS),
        "wormhole": ("Wormhole", TILE_WORMHOLE),
    }

    def _get_available_interactions(self):
        acts = []
        px, py = self.player_x, self.player_y

        def add(ot, x, y, dx, dy):
            dn = self._direction_name(dx, dy) if (dx or dy) else "here"
            nm, ic = self.OBJ_LABELS.get(ot, (ot.capitalize(), "?"))
            if ot == "station" and dx == 0 and dy == 0:
                st = self.galaxy.get_station_at(x, y)
                tag = f"[{st.faction}]" if st else ""
                acts.append(("r", f"(R)efuel-50cr {tag}", "_act_refuel", f"Station {dn}"))
                acts.append(("h", f"Repair(H)ull-30cr {tag}", "_act_repair", f"Station {dn}"))
                acts.append(("b", f"(B)uy/Sell {tag}", "_act_open_trade", f"Station {dn}"))
                if st and st.stype == "temple" and self.ship.religion is None:
                    acts.append(("j", f"(J)oin {st.name}", "_act_join_religion", f"Temple {dn}"))
                if st and st.modules_for_sale:
                    acts.append(("p", f"Shop (P)arts [{len(st.modules_for_sale)} modules]", "_act_modules_shop", f"Station {dn}"))
                if st and st.missions:
                    acts.append(("v", f"Miss(V)ons [{len(st.missions)} available]", "_act_missions", f"Station {dn}"))
            elif ot == "planet":
                acts.append(("s", f"(S)can {ic} {nm}", "_act_scan_planet", f"{nm} {dn}"))
                acts.append(("l", f"(L)and {ic}", "_act_land", f"{nm} {dn}"))
            elif ot == "asteroids" and dx == 0 and dy == 0:
                acts.append(("m", f"(M)ine {ic}", "_act_mine", f"{nm} {dn}"))
            elif ot == "wormhole" and dx == 0 and dy == 0:
                acts.append(("u", f"(U)se Wormhole {ic}", "_act_use_wormhole", f"{nm} {dn}"))

        # NPCs nearby
        for t in self.galaxy.traders:
            if t.alive and max(abs(t.x - px), abs(t.y - py)) <= 1:
                nn = self._direction_name(t.x - px, t.y - py) if (t.x != px or t.y != py) else ""
                acts.append(("c", f"(C)hat {t.name}[{t.faction}]", "_act_hail_npc", f"Trader {nn}"))
        rng = self.ship.get_effective_stats().get("range", 1)
        for p in self.galaxy.pirates:
            if p.alive and max(abs(p.x - px), abs(p.y - py)) <= rng:
                nn = self._direction_name(p.x - px, p.y - py) if (p.x != px or p.y != py) else ""
                acts.append(("f", f"(F)ire {p.name} [{nn}]", "_act_fire_pirate", f"Pirate {nn}"))

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

    def _run_interaction(self, mn):
        h = getattr(self, mn, None)
        if h:
            h()
            if self.state != GameState.GAME_OVER:
                self.state = GameState.PLAYING
            self.update_map()
            self.update_info()

    # ---------- interaction handlers ----------

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

    def _act_open_trade(self):
        st = self.galaxy.get_station_at(self.player_x, self.player_y)
        if st:
            self.push_screen(TradeScreen(st))
        else:
            self.logger.system("No station.")

    def _act_join_religion(self):
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
            from ui import ModuleShopScreen
            self.push_screen(ModuleShopScreen(st))
        else:
            self.logger.system("No modules for sale.")

    def _act_missions(self):
        st = self.galaxy.get_station_at(self.player_x, self.player_y)
        if st and st.missions:
            from ui import MissionScreen
            self.push_screen(MissionScreen(st))
        else:
            self.logger.system("No missions.")

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

    def _act_use_wormhole(self):
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

    def _act_fire_pirate(self):
        rng = self.ship.get_effective_stats().get("range", 1)
        for p in self.galaxy.pirates:
            if p.alive and max(abs(p.x - self.player_x), abs(p.y - self.player_y)) <= rng:
                stats = self.ship.get_effective_stats()
                dmg = stats.get("damage", 20)
                acc = stats.get("accuracy", 80)
                if not self._roll_hit(acc, 5):
                    self.logger.combat(f"Missed {p.name}!")
                    return
                shield_before = p.shield_hp if hasattr(p, 'shield_hp') else 0
                p.take_damage(dmg)
                if hasattr(p, 'shield_hp') and shield_before > 0 and p.shield_hp < shield_before:
                    self.logger.combat(f"Hit {p.name}! Shield absorbed. {p.hull}/{p.max_hull}")
                else:
                    self.logger.combat(f"Hit {p.name}! {p.hull}/{p.max_hull}")
                if not p.alive:
                    r = random.randint(50, 150)
                    self.ship.credits += r
                    self.ship.cargo.add("relic", 1)
                    self.ship.reputation["free_traders"] = min(
                        100, self.ship.reputation.get("free_traders", 0) + 2)
                    self.logger.combat(f"{p.name} destroyed! +{r}cr")
                else:
                    # Pirate retaliates if within their range
                    pirate_range = 1
                    if max(abs(p.x - self.player_x), abs(p.y - self.player_y)) <= pirate_range:
                        ret_dmg = 8
                        evasion = self.ship.get_effective_stats().get("evasion", 0)
                        if random.random() * 100 >= evasion:
                            self.ship.take_damage(ret_dmg)
                            self.logger.combat(f"{p.name} retaliates! -{ret_dmg}")
                        else:
                            self.logger.combat(f"{p.name} misses!")
                return
        self.logger.system("No pirate.")

    @staticmethod
    def _roll_hit(accuracy, evasion):
        """Roll for hit: accuracy minus evasion = hit chance (0-100)."""
        chance = max(5, min(95, accuracy - evasion))
        return random.random() * 100 < chance

    @staticmethod
    def _direction_name(dx, dy):
        return {
            (0, -1): "N", (0, 1): "S", (-1, 0): "W", (1, 0): "E",
            (-1, -1): "NW", (1, -1): "NE", (-1, 1): "SW", (1, 1): "SE",
        }.get((dx, dy), "?")

    # -----------------------------------------------------------------------
    # World tick
    # -----------------------------------------------------------------------

    def tick_world(self):
        self.logger.new_turn()
        self.ship.regen_shields()
        nx, ny, evs, over = self.galaxy.tick(self.player_x, self.player_y, self.ship)
        self.player_x, self.player_y = nx, ny
        for ev in evs:
            self._log_event(ev)
        npc_ev = []
        self.galaxy.step_npc(self.player_x, self.player_y, self.ship, npc_ev)
        for ev in npc_ev:
            self._log_event(ev)
        # Module damage notification
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
        # Check mission completion at station
        st = self.galaxy.get_station_at(self.player_x, self.player_y)
        if st:
            completed = self.ship.check_missions(st)
            for _, msg in completed:
                self.logger.trade(msg)
        self.update_map()
        self.update_info()

    def move_player(self, dx, dy):
        if self.state != GameState.PLAYING:
            return
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
            self.tick_world()
        self.update_map()
        self.update_info()

    # -----------------------------------------------------------------------
    # Console
    # -----------------------------------------------------------------------

    def process_command(self, raw):
        raw = raw.strip()
        if not raw:
            self.logger.system("Type 'help'.")
            return
        p = raw.split()
        c = p[0].lower()

        if c == "help":
            self.logger.system("── COMMANDS ──")
            self.logger.system(
                "scan inv give/take refuel set hull "
                "trade buy/sell prices market scan/history "
                "power modules list cargo cargo jettison/sellall "
                "blackmarket list smuggle "
                "reputation diplomacy declare war attack hail missions news exit"
            )
            self.logger.system("── KEYS ──")
            self.logger.system("WASD E I F N H F1 F2 F5 ~ Esc")

        elif c == "scan":
            self.logger.system(
                f"Sector ({self.player_x},{self.player_y}): "
                f"{self.galaxy.get_object_info(self.player_x, self.player_y)}")
            self.logger.system(self._scan_nearby())
            self.logger.system(self._cargo_summary())

        elif c in ("inv", "inventory"):
            if not self.ship.cargo.items:
                self.logger.system("Cargo empty.")
            else:
                p2 = [f"{RESOURCES.get(r, {}).get('name', r)}:{a}"
                      for r, a in sorted(self.ship.cargo.items.items())]
                self.logger.system(
                    f"Cargo: {'  '.join(p2)} ({self.ship.cargo.used()}/"
                    f"{self.ship.cargo.capacity}) Val:{self.ship.cargo.total_value()}cr")

        elif c == "give" and len(p) >= 3:
            rid = p[1]
            try:
                amt = int(p[2])
            except ValueError:
                self.logger.system("give <res> <amt>"); return
            if rid not in RESOURCES:
                self.logger.system(f"Unknown '{rid}'."); return
            if self.ship.cargo.add(rid, amt):
                self.logger.system(f"Added {amt} {RESOURCES[rid]['name']}.")
            else:
                self.logger.system("Cargo full!")

        elif c == "take" and len(p) >= 3:
            rid = p[1]
            try:
                amt = int(p[2])
            except ValueError:
                self.logger.system("take <res> <amt>"); return
            if self.ship.cargo.remove(rid, amt):
                self.logger.system(f"Removed {amt}.")
            else:
                self.logger.system(f"Not enough {rid}.")

        elif c == "refuel":
            self.ship.fuel = 100
            self.logger.system("Refuelled to 100.")

        elif c == "set" and len(p) >= 3 and p[1] == "hull":
            try:
                self.ship.hull = max(0, min(100, int(p[2])))
                self.logger.system(f"Hull={self.ship.hull}.")
            except ValueError:
                self.logger.system("set hull <n>")

        elif c == "trade" and len(p) >= 4:
            st = self.galaxy.get_nearest_station(self.player_x, self.player_y, 1)
            if not st:
                self.logger.system("No station."); return
            act, rid, amt_s = p[1], p[2], p[3]
            try:
                amt = int(amt_s)
            except ValueError:
                self.logger.system("trade buy/sell <res> <amt>"); return
            if rid not in RESOURCES:
                self.logger.system(f"Unknown '{rid}'."); return
            if act == "buy":
                self.logger.system(st.sell_to(self.ship, rid, amt))
            elif act == "sell":
                self.logger.system(st.buy_from(self.ship, rid, amt))
            else:
                self.logger.system("trade buy/sell <res> <amt>")

        elif c == "prices":
            st = self.galaxy.get_nearest_station(self.player_x, self.player_y, 1)
            if not st:
                self.logger.system("No station."); return
            self.logger.system(f"Prices at {st.name}[{st.faction}]:")
            for rid in sorted(RESOURCES):
                pb, _ = st.price_for_player(rid, True, self.ship)
                ps, _ = st.price_for_player(rid, False, self.ship)
                sk = st.inventory.get(rid, 0)
                self.logger.system(f"  {rid:<12} buy:{pb:>4} sell:{ps:>4} stock:{sk}")

        elif c == "market":
            if len(p) >= 2 and p[1] == "scan":
                rng = 7
                if len(p) >= 3:
                    try:
                        rng = int(p[2])
                    except ValueError:
                        pass
                stations = self.galaxy.stations_in_range(
                    self.player_x, self.player_y, rng)
                self.logger.system(f"Market scan (range {rng}):")
                for st in stations:
                    dist = max(abs(st.x - self.player_x), abs(st.y - self.player_y))
                    self.logger.system(f"  {st.name}[{st.faction}] dist:{dist}")
                    for rid in sorted(RESOURCES):
                        if st.inventory.get(rid, 0) > 0:
                            sp, _ = st.price_for_player(rid, True, self.ship)
                            bp, _ = st.price_for_player(rid, False, self.ship)
                            self.logger.system(
                                f"    {rid:<12} buy:{sp:>4} "
                                f"sell:{bp:>4} stock:{st.inventory.get(rid, 0)}")
            elif len(p) >= 4 and p[1] == "history":
                sname, rid = p[2], p[3]
                st = None
                for s in self.galaxy.stations:
                    if s.name.lower() == sname.lower():
                        st = s; break
                if not st:
                    self.logger.system(f"Station '{sname}' not found."); return
                if rid not in RESOURCES:
                    self.logger.system(f"Unknown '{rid}'."); return
                hist = st.price_history.get(rid, [])
                if not hist:
                    self.logger.system("No history.")
                else:
                    self.logger.system(f"History for {rid} at {st.name}:")
                    for i, (b, s) in enumerate(hist[-10:]):
                        self.logger.system(f"  t-{len(hist)-i}: buy:{b} sell:{s}")
            else:
                self.logger.system("market scan [range] | market history <station> <res>")

        elif c == "power" and len(p) >= 3:
            comp = p[1]
            try:
                val = int(p[2])
            except ValueError:
                self.logger.system("power <comp> <0-10>"); return
            if comp not in COMPARTMENTS:
                self.logger.system(f"Unknown: {comp}"); return
            self.ship.compartments[comp]["power"] = max(0, min(10, val))
            self.logger.system(f"Power to {comp} set to {val}.")

        elif c == "modules" and len(p) >= 2 and p[1] == "list":
            self.logger.system("── Installed Modules ──")
            for c2 in COMPARTMENTS:
                for m in self.ship.compartments[c2]["modules"]:
                    sts = ("ON" if m.active and not m.is_broken()
                           else "OFF" if m.is_broken() else "ON")
                    self.logger.system(
                        f"  [{sts}] {m.name} ({c2}) "
                        f"dur:{m.durability}/{m.max_durability} pow:{m.energy_consumption}")

        elif c == "modules" and len(p) >= 3 and p[1] == "repair":
            comp = p[2]
            st = self.galaxy.get_nearest_station(self.player_x, self.player_y, 1)
            if not st:
                self.logger.system("Must be at a station to repair."); return
            msg, cost = self.ship.repair_module(comp)
            if cost == 0:
                self.logger.system(msg); return
            if self.ship.credits < cost * 10:
                self.logger.system(f"Need {cost * 10}cr for repair."); return
            if self.ship.cargo.has("metal") < 2 or self.ship.cargo.has("electronics") < 1:
                self.logger.system("Need metal (2) + electronics (1) for repair."); return
            self.ship.credits -= cost * 10
            self.ship.cargo.remove("metal", 2)
            self.ship.cargo.remove("electronics", 1)
            msg, _ = self.ship.repair_module(comp)
            self.logger.system(msg)

        elif c == "modules":
            self.logger.system("modules list | modules repair <comp>")

        elif c == "cargo":
            if len(p) >= 2 and p[1] == "jettison":
                rid = p[2] if len(p) >= 3 else ""
                amt = int(p[3]) if len(p) >= 4 else 1
                if rid not in RESOURCES:
                    self.logger.system(f"Unknown '{rid}'."); return
                if self.ship.cargo.remove(rid, amt):
                    self.logger.system(f"Jettisoned {amt} {rid}.")
                else:
                    self.logger.system(f"Not enough {rid}.")
            elif len(p) >= 2 and p[1] == "sellall":
                st = self.galaxy.get_nearest_station(self.player_x, self.player_y, 1)
                if not st:
                    self.logger.system("No station."); return
                total = 0
                for rid in list(self.ship.cargo.items.keys()):
                    if RESOURCES.get(rid, {}).get("cat") == "raw":
                        amt = self.ship.cargo.has(rid)
                        if amt > 0 and "Sold" in st.buy_from(self.ship, rid, amt):
                            total += 1
                self.logger.system(f"Sold {total} raw items.")
            else:
                self.push_screen(CargoScreen())

        elif c == "blackmarket" and len(p) >= 2 and p[1] == "list":
            st = self.galaxy.get_nearest_station(self.player_x, self.player_y, 1)
            if not st:
                self.logger.system("No station."); return
            if self.ship.reputation.get(st.faction, 0) >= -20:
                self.logger.system("No black market."); return
            self.logger.system(f"Black market at {st.name}:")
            for rid in sorted(RESOURCES):
                sk = st.inventory.get(rid, 0)
                if sk > 0:
                    bp, sp = st.prices.get(rid, (0, 0))
                    self.logger.system(
                        f"  {rid:<12} buy:{int(bp * random.uniform(2, 5)):>4} "
                        f"sell:{int(sp * random.uniform(2, 5)):>4}")

        elif c == "smuggle" and len(p) >= 3:
            rid = p[1]
            try:
                amt = int(p[2])
            except ValueError:
                self.logger.system("smuggle <res> <amt>"); return
            st = self.galaxy.get_nearest_station(self.player_x, self.player_y, 1)
            if not st:
                self.logger.system("No station."); return
            banned = CONTRABAND.get(st.faction, []) + CONTRABAND.get(st.religion, [])
            if rid not in banned:
                self.logger.system(f"{rid} not contraband here."); return
            if self.ship.cargo.has(rid) < amt:
                self.logger.system(f"Not enough {rid}."); return
            if random.random() < 0.2:
                self.ship.cargo.remove(rid, amt)
                self.ship.reputation[st.faction] = max(
                    -100, self.ship.reputation.get(st.faction, 0) - 5)
                self.logger.danger(f"Scanned! Lost {amt} {rid}.")
            else:
                bp, _ = st.prices.get(rid, (0, 0))
                t = int(bp * random.uniform(2, 4)) * amt
                self.ship.cargo.remove(rid, amt)
                self.ship.credits += t
                self.logger.exploration(f"Smuggled {amt} {rid} for {t}cr!")

        elif c == "reputation":
            self.logger.system("Reputation:")
            for f in sorted(FACTIONS):
                self.logger.system(
                    f"  {FACTIONS[f]['name']:<18} {self.ship.reputation.get(f, 0):>4}")

        elif c == "diplomacy":
            self.logger.system("Diplomacy:")
            for f1 in sorted(FACTIONS):
                for f2, st in self.galaxy.diplomacy.get(f1, {}).items():
                    if f1 < f2:
                        self.logger.system(
                            f"  {FACTIONS[f1]['name']:<14} vs "
                            f"{FACTIONS[f2]['name']:<14} = {st}")

        elif c == "declare" and len(p) >= 3 and p[1] == "war":
            t = p[2]
            if t not in FACTIONS:
                self.logger.system(f"Unknown. Options: {', '.join(FACTIONS)}")
                return
            for f in FACTIONS:
                if f != t and t in self.galaxy.diplomacy.get(f, {}):
                    self.galaxy.diplomacy[f][t] = "war"
            self.ship.reputation[t] = max(-100, self.ship.reputation.get(t, 0) - 20)
            self.galaxy.add_news(f"War on {t}!", f"Player declared war on {t}.")
            self.logger.system(f"War on {t}!")

        elif c == "attack" and len(p) >= 2:
            name = " ".join(p[1:])
            npc = self.galaxy.get_npc_by_name(name)
            rng = self.ship.get_effective_stats().get("range", 1)
            if not npc or not npc.alive or max(abs(npc.x - self.player_x),
                                                abs(npc.y - self.player_y)) > rng:
                self.logger.system(f"No '{name}' in range ({rng})."); return
            stats = self.ship.get_effective_stats()
            dmg = stats.get("damage", 25)
            acc = stats.get("accuracy", 70)
            if not self._roll_hit(acc, 5):
                self.logger.combat(f"Missed {npc.name}!"); return
            npc.take_damage(dmg)
            self.logger.combat(f"Hit {npc.name}! {npc.hull}/{npc.max_hull}")
            if npc.faction in self.ship.reputation:
                self.ship.reputation[npc.faction] = max(
                    -100, self.ship.reputation[npc.faction] - 5)
            if not npc.alive:
                self.ship.credits += random.randint(50, 150)
                self.logger.combat(f"{npc.name} destroyed!")

        elif c == "hail":
            self._act_hail_npc()

        elif c == "targets":
            g = self.galaxy
            targets = []
            for p in g.pirates:
                if p.alive:
                    d = max(abs(p.x - self.player_x), abs(p.y - self.player_y))
                    targets.append((d, f"Pirate {p.name}", p, "P"))
            for t in g.traders:
                if t.alive:
                    d = max(abs(t.x - self.player_x), abs(t.y - self.player_y))
                    targets.append((d, f"Trader {t.name}", t, "T"))
            targets.sort(key=lambda x: x[0])
            if not targets:
                self.logger.system("No targets in range.")
            else:
                self.logger.system("── Targets ──")
                for i, (d, label, npc, tag) in enumerate(targets, 1):
                    sh = f" sh:{npc.shield_hp}" if hasattr(npc, 'shield_hp') and npc.shield_hp > 0 else ""
                    self.logger.system(
                        f"  [{i}] {label} hull:{npc.hull}/{npc.max_hull}{sh} dist:{d} [{tag}]")

        elif c == "missions":
            if self.ship.missions:
                self.logger.system("── Active Missions ──")
                for m in self.ship.missions:
                    info = RESOURCES.get(m.resource, {})
                    self.logger.system(
                        f"  Deliver {m.amount} {info.get('name', m.resource)} "
                        f"→ {m.target_station}  +{m.reward}cr  ({m.ticks} ticks left)")
            else:
                self.logger.system("No active missions. Visit stations for contracts.")

        elif c == "news":
            self._prev_state = self.state
            self.state = GameState.NEWS
            self.update_map()
            self.update_info()

        elif c == "exit":
            self.exit()

        else:
            self.logger.system(f"Unknown '{c}'. Type 'help'.")

    # -----------------------------------------------------------------------
    # Key handling
    # -----------------------------------------------------------------------

    def on_key(self, event):
        if self.state == GameState.RACE_SELECT:
            if event.key in ("1", "2", "3", "4", "5"):
                self.select_race(event.key)
            elif event.key in ("enter", " "):
                self.select_race("")
            return

        if self.state == GameState.START_SCREEN:
            if event.key == "h":
                self._prev_state = GameState.START_SCREEN
                self.state = GameState.HELP
                self.update_map(); self.update_info(); return
            if event.key == "n":
                self._prev_state = GameState.START_SCREEN
                self.state = GameState.NEWS
                self.update_map(); self.update_info(); return
            self.state = GameState.PLAYING
            self.logger.system("Journey begins…")
            self.update_map(); self.update_info(); return

        if self.state == GameState.HELP:
            self.state = self._prev_state
            self.update_map(); self.update_info(); return

        if self.state == GameState.NEWS:
            self.state = self._prev_state
            self.update_map(); self.update_info(); return

        if self.state == GameState.GAME_OVER:
            if event.key == "r":
                self.restart_game()
            elif event.key == "q":
                self.exit()
            return

        if self.state == GameState.INSPECTING:
            if event.key in ("escape", "i"):
                self.state = GameState.PLAYING
                self.update_map(); self.update_info(); return
            if event.key in ("up", "w"):
                self.cursor_y = max(0, self.cursor_y - 1)
            elif event.key in ("down", "s"):
                self.cursor_y = min(self.galaxy.height - 1, self.cursor_y + 1)
            elif event.key in ("left", "a"):
                self.cursor_x = max(0, self.cursor_x - 1)
            elif event.key in ("right", "d"):
                self.cursor_x = min(self.galaxy.width - 1, self.cursor_x + 1)
            self.update_map(); self.update_info(); return

        if self.state == GameState.PAUSED:
            if event.key == "c":
                self.state = GameState.PLAYING
                self.update_map(); self.update_info()
            elif event.key == "r":
                self.restart_game()
            elif event.key == "q":
                self.exit()
            return

        # --- PLAYING ---
        if event.key == "escape":
            if len(self.screen_stack) > 1:
                return  # let the pushed screen handle it
            self.state = GameState.PAUSED
            self.update_map(); self.update_info()
        elif self._interaction_active:
            if event.key == "escape":
                self._interaction_active = False
                self.update_map(); self.update_info()
            elif len(event.key) == 1 and event.key.isalnum():
                for k, _, hn, _ in self.interaction_actions:
                    if event.key == k:
                        self._interaction_active = False
                        self._run_interaction(hn)
                        break
                else:
                    self._interaction_active = False
                    self.update_map(); self.update_info()
        elif event.key in ("up", "w"):
            self.move_player(0, -1)
        elif event.key in ("down", "s"):
            self.move_player(0, 1)
        elif event.key in ("left", "a"):
            self.move_player(-1, 0)
        elif event.key in ("right", "d"):
            self.move_player(1, 0)
        elif event.key == "q":
            self.exit()
        elif event.key == "e":
            self.interaction_actions = self._get_available_interactions()
            if self.interaction_actions:
                self._interaction_active = True
                self.update_map(); self.update_info()
            else:
                self.logger.system("Nothing.")
        elif event.key == "h":
            self._prev_state = self.state
            self.state = GameState.HELP
            self.update_map(); self.update_info()
        elif event.key == "i":
            self.state = GameState.INSPECTING
            self.cursor_x, self.cursor_y = self.player_x, self.player_y
            self.logger.system("Inspect.")
            self.update_map(); self.update_info()
        elif event.key == "n":
            self._prev_state = self.state
            self.state = GameState.NEWS
            self.update_map(); self.update_info()
        elif event.key == "b":
            st = self.galaxy.get_station_at(self.player_x, self.player_y)
            if st:
                self.push_screen(TradeScreen(st))
                self.update_map(); self.update_info()
            else:
                self.logger.system("No station.")
        elif event.key == "f":
            rng = self.ship.get_effective_stats().get("range", 1)
            closest = None
            closest_dist = 999
            for p in self.galaxy.pirates:
                if p.alive:
                    d = max(abs(p.x - self.player_x), abs(p.y - self.player_y))
                    if d <= rng and d < closest_dist:
                        closest = p
                        closest_dist = d
            if closest:
                self._act_fire_pirate()
            else:
                self.logger.system(f"No pirate in range ({rng}).")
            self.update_map(); self.update_info()
        elif event.key in ("f1", "F1"):
            self.push_screen(BridgeScreen())
        elif event.key in ("f2", "F2"):
            self.push_screen(EngineeringScreen())
        elif event.key in ("f3", "F3"):
            self.push_screen(TacticalScreen())
        elif event.key in ("f4", "F4"):
            self.push_screen(CargoScreen())
        elif event.key in ("f5", "F5"):
            self.push_screen(CrewScreen())
        elif event.key == " ":
            self.logger.system("Waiting…")
            self.tick_world()
        elif event.key in ("`", "grave_accent", "asciitilde"):
            self.push_screen(CommandScreen())


if __name__ == "__main__":
    app = GalaxyMapApp()
    app.run()
