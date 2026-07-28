"""
galaxy_map.py — Textual App shell for the galaxy map game.

Thin Textual layer that delegates all game logic and rendering to
GameController (game_controller.py). Handles composition, key bindings,
and screen management only.
"""

import random
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Static, Header, Footer
from textual.reactive import reactive
from textual import events

from game_logger import LogCategory
from config import WIDTH, HEIGHT, TILE_SHIP, TILE_OTHER_SHIP
from models import TraderShip
from game_controller import GameController, GameState
from ui import (
    CommandScreen, CargoScreen, TradeScreen,
    BridgeScreen, EngineeringScreen, TacticalScreen, CrewScreen,
    ModuleShopScreen, MissionScreen,
    ShipyardScreen, CraftingScreen, HireScreen,
    LandingPrepScreen,
    ActionMenu, SettingsScreen,
    PlanetSurfaceScreen, BuildingMenu,
)
from battle import BattleScreen, BattleController
from expedition import (
    ExpeditionScreen, ExpeditionController,
    create_quick_expedition_character, generate_quick_expedition_map,
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

SCREEN_MAP = {
    "TradeScreen": TradeScreen,
    "ModuleShopScreen": ModuleShopScreen,
    "MissionScreen": MissionScreen,
    "ShipyardScreen": ShipyardScreen,
    "CraftingScreen": CraftingScreen,
    "HireScreen": HireScreen,
}


class GalaxyMapApp(App):
    """Textual App shell — delegates game logic to GameController."""

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

    def __init__(self):
        super().__init__()
        self.ctrl = GameController()
        self.ctrl.set_callbacks(
            push_screen=self._ctrl_push_screen,
            update_map=self._ctrl_update_map,
            update_info=self._ctrl_update_info,
            update_log=self._ctrl_update_log,
        )

    # -- Property shortcuts for compatibility with existing code --
    @property
    def state(self):
        return self.ctrl.state

    @state.setter
    def state(self, v):
        self.ctrl.state = v

    @property
    def galaxy(self):
        return self.ctrl.galaxy

    @property
    def ship(self):
        return self.ctrl.ship

    @property
    def logger(self):
        return self.ctrl.logger

    @property
    def player_x(self):
        return self.ctrl.player_x

    @player_x.setter
    def player_x(self, v):
        self.ctrl.player_x = v

    @property
    def player_y(self):
        return self.ctrl.player_y

    @player_y.setter
    def player_y(self, v):
        self.ctrl.player_y = v

    @property
    def death_cause(self):
        return self.ctrl.death_cause

    @death_cause.setter
    def death_cause(self, v):
        self.ctrl.death_cause = v

    @property
    def interaction_actions(self):
        return self.ctrl.interaction_actions

    @interaction_actions.setter
    def interaction_actions(self, v):
        self.ctrl.interaction_actions = v

    @property
    def _interaction_active(self):
        return self.ctrl._interaction_active

    @_interaction_active.setter
    def _interaction_active(self, v):
        self.ctrl._interaction_active = v

    @property
    def cursor_x(self):
        return self.ctrl.cursor_x

    @cursor_x.setter
    def cursor_x(self, v):
        self.ctrl.cursor_x = v

    @property
    def cursor_y(self):
        return self.ctrl.cursor_y

    @cursor_y.setter
    def cursor_y(self, v):
        self.ctrl.cursor_y = v

    @property
    def _pending_battle(self):
        return self.ctrl._pending_battle

    @_pending_battle.setter
    def _pending_battle(self, v):
        self.ctrl._pending_battle = v

    @property
    def world_frozen(self):
        return self.ctrl.world_frozen

    @world_frozen.setter
    def world_frozen(self, v):
        self.ctrl.world_frozen = v

    @property
    def _prev_state(self):
        return self.ctrl._prev_state

    @_prev_state.setter
    def _prev_state(self, v):
        self.ctrl._prev_state = v

    @property
    def _dismiss_handled_escape(self):
        return self.ctrl._dismiss_handled_escape

    @_dismiss_handled_escape.setter
    def _dismiss_handled_escape(self, v):
        self.ctrl._dismiss_handled_escape = v

    @property
    def race_selected(self):
        return self.ctrl.race_selected

    @race_selected.setter
    def race_selected(self, v):
        self.ctrl.race_selected = v

    @property
    def _show_race_select(self):
        return self.ctrl._show_race_select

    @_show_race_select.setter
    def _show_race_select(self, v):
        self.ctrl._show_race_select = v

    # -- Controller callbacks --
    def _ctrl_push_screen(self, screen):
        self.push_screen(screen)

    def _ctrl_update_map(self):
        self.update_map()

    def _ctrl_update_info(self):
        self.update_info()

    def _ctrl_update_log(self):
        self._update_log_only()

    # -------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------

    def restart_game(self):
        self.ctrl.restart_game()
        self.update_map()
        self.update_info()

    def compose(self):
        yield Header()
        yield Container(Static(id="map"))
        yield Static(id="info-panel")
        yield Static(id="log")
        yield Footer()

    def on_mount(self):
        from locales import set_lang
        from config import load_settings
        _cfg = load_settings()
        set_lang(_cfg.get("lang", "ru"))
        self.update_map()
        self.update_info()

    # -------------------------------------------------------------------
    # Map & info rendering (delegated to controller)
    # -------------------------------------------------------------------

    def update_map(self):
        content = self.ctrl.get_map_display()
        self.query_one("#map").update(content)

    def update_info(self):
        info, log_text = self.ctrl.get_info_panel()
        self.query_one("#info-panel").update(info)
        self.query_one("#log").update(log_text)

    def _update_log_only(self):
        info, log_text = self.ctrl.get_info_panel()
        self.query_one("#log").update(log_text)

    # -------------------------------------------------------------------
    # Screen management
    # -------------------------------------------------------------------

    def push_screen(self, screen):
        self.ctrl.world_frozen = True
        super().push_screen(screen)

    def on_screen_resume(self, event=None):
        if len(self.screen_stack) <= 1:
            self.ctrl.world_frozen = False

    def advance_world(self):
        if len(self.screen_stack) <= 1:
            self.ctrl.world_frozen = False
        if self.ctrl.world_frozen:
            return
        self.ctrl.tick_world()
        self.update_map()
        self.update_info()

    # -------------------------------------------------------------------
    # Key handling
    # -------------------------------------------------------------------

    def on_key(self, event):
        if isinstance(self.screen, BattleScreen):
            return
        if isinstance(self.screen, ExpeditionScreen):
            return

        prev_state = self.ctrl.state  # capture before handlers modify it

        if self.ctrl.state == GameState.RACE_SELECT:
            self._on_race_select_key(event)
        elif self.ctrl.state == GameState.START_SCREEN:
            self._on_start_key(event)
        elif self.ctrl.state in (GameState.PLAYING, GameState.INSPECTING):
            self._on_playing_key(event)
        elif self.ctrl.state == GameState.PAUSED:
            self._on_paused_key(event)
        elif self.ctrl.state == GameState.GAME_OVER:
            self._on_game_over_key(event)
        elif self._interaction_active:
            self._on_interaction_key(event)

        # Global keys — skip escape if it was already handled by pause handler
        if event.key == "escape" and prev_state != GameState.PAUSED and self.ctrl.state in (
                GameState.PLAYING, GameState.INSPECTING):
            if self._interaction_active:
                self._interaction_active = False
                self.update_map()
                self.update_info()
                event.stop()
                return
            elif len(self.screen_stack) > 1:
                return
            self.ctrl.state = GameState.PAUSED
            self.update_map()
            self.update_info()
        elif event.key == "/":
            self.ctrl.cycle_log_filter()
            self._update_log_only()
        elif event.key == "`" or event.key == "grave_accent" or event.key == "asciitilde":
            self.push_screen(CommandScreen())
        elif event.key == "h":
            if self.ctrl.state in (GameState.PLAYING, GameState.INSPECTING):
                self.ctrl._prev_state = self.ctrl.state
                self.ctrl.state = GameState.HELP
                self.update_map()
                self.update_info()
        elif event.key == "n":
            if self.ctrl.state in (GameState.PLAYING, GameState.INSPECTING):
                self.ctrl._prev_state = self.ctrl.state
                self.ctrl.state = GameState.NEWS
                self.update_map()
                self.update_info()
        elif event.key == "q":
            if self.ctrl.state in (GameState.PLAYING, GameState.INSPECTING):
                self.exit()

    def _on_race_select_key(self, event):
        k = event.key.lower()
        if k in ("1", "2", "3", "4", "5", "enter", ""):
            choice = k if k != "enter" else ""
            self.ctrl.select_race(choice)
            self.update_map()
            self.update_info()
        elif k == "0":
            self.ctrl._show_race_select = False
            self.ctrl.state = GameState.START_SCREEN
            self.update_map()
            self.update_info()

    def _on_start_key(self, event):
        k = event.key.lower()
        if k == "1":
            self.ctrl._show_race_select = True
            self.ctrl.state = GameState.RACE_SELECT
            self.update_map()
            self.update_info()
        elif k == "2":
            self._start_quick_battle()
        elif k == "3":
            self._start_quick_expedition()
        elif k == "4":
            self.ctrl.state = GameState.HELP
            self.update_map()
            self.update_info()
        elif k == "5":
            self.exit()

    def _on_playing_key(self, event):
        k = event.key.lower()
        # Block movement when interaction menu is active
        if self._interaction_active:
            if k == "0":
                self._interaction_active = False
                self.update_map()
                self.update_info()
                return
            return
        if k in ("up", "w"):
            self._do_move(0, -1)
        elif k in ("down", "s"):
            self._do_move(0, 1)
        elif k in ("left", "a"):
            self._do_move(-1, 0)
        elif k in ("right", "d"):
            self._do_move(1, 0)
        elif k == "0":
            if self.ctrl.state == GameState.PLAYING:
                self._interaction_active = True
                self.ctrl.interaction_actions = self.ctrl.get_available_interactions()
                self.update_map()
                self.update_info()
        elif k in (" ", "space"):
            if self.ctrl.state == GameState.PLAYING:
                self.ctrl.logger.system("Waiting…")
                self.advance_world()
        elif k == "i":
            self.ctrl.state = GameState.INSPECTING
            self.ctrl.cursor_x, self.ctrl.cursor_y = self.ctrl.player_x, self.ctrl.player_y
            self.ctrl.logger.system("Inspect.")
            self.update_map()
            self.update_info()
        elif k == "b":
            st = self.ctrl.galaxy.get_station_at(self.ctrl.player_x, self.ctrl.player_y)
            if st:
                self.push_screen(TradeScreen(st))
        elif k in ("l", "L"):
            result = self.ctrl.try_landing()
            if result:
                screen_type, site_type, site_name = result
                self.push_screen(LandingPrepScreen(site_type=site_type, site_name=site_name))
        elif k in ("c", "C"):
            px, py = self.ctrl.player_x, self.ctrl.player_y
            if self.ctrl.galaxy.objects.get((px, py)) == "planet":
                if (px, py) in self.ctrl.galaxy.colonies:
                    result = self.ctrl.open_colony()
                    if result:
                        _, colony, cx, cy = result
                        self.push_screen(PlanetSurfaceScreen(colony, cx, cy))
                else:
                    self.ctrl.found_colony()
                    self.update_map()
                    self.update_info()
            else:
                self.ctrl.logger.system("Not on a planet tile.")
        elif k == "f":
            rng = self.ctrl.ship.get_effective_stats().get("range", 1)
            closest = None
            closest_dist = 999
            for p in self.ctrl.galaxy.pirates:
                if p.alive:
                    d = max(abs(p.x - self.ctrl.player_x), abs(p.y - self.ctrl.player_y))
                    if d <= rng and d < closest_dist:
                        closest = p
                        closest_dist = d
            if closest:
                self._initiate_battle(closest)
            else:
                self.ctrl.logger.system(f"No pirate in range ({rng}).")
            self.update_map()
            self.update_info()
        elif k in ("f1", "F1"):
            self.push_screen(BridgeScreen())
        # Inspect movement
        if self.ctrl.state == GameState.INSPECTING:
            if k in ("up", "w"):
                self.ctrl.cursor_y = max(0, self.ctrl.cursor_y - 1)
            elif k in ("down", "s"):
                self.ctrl.cursor_y = min(HEIGHT - 1, self.ctrl.cursor_y + 1)
            elif k in ("left", "a"):
                self.ctrl.cursor_x = max(0, self.ctrl.cursor_x - 1)
            elif k in ("right", "d"):
                self.ctrl.cursor_x = min(WIDTH - 1, self.ctrl.cursor_x + 1)
            self.update_map()
            self.update_info()

    def _on_paused_key(self, event):
        k = event.key.lower()
        if k == "1" or k == "c":
            self.ctrl.state = GameState.PLAYING
            self.update_map()
            self.update_info()
        elif k == "escape":
            self.ctrl.state = GameState.PLAYING
            self.update_map()
            self.update_info()
            event.stop()  # prevent global escape handler from re-pausing
        elif k == "2" or k == "r":
            self.restart_game()
        elif k == "3" or k == "q":
            self.exit()

    def _on_game_over_key(self, event):
        k = event.key.lower()
        if k == "1" or k == "r":
            self.restart_game()
        elif k == "2" or k == "q":
            self.exit()

    def _on_interaction_key(self, event):
        k = event.key.lower()
        if k == "escape" or k == "0":
            self._interaction_active = False
            self.ctrl.state = GameState.PLAYING
            self.update_map()
            self.update_info()
            return
        if k.isdigit():
            idx = int(k) - 1
            if 0 <= idx < len(self.ctrl.interaction_actions):
                _, label, action_id, _ = self.ctrl.interaction_actions[idx]
                self._interaction_active = False
                result = self.ctrl.run_interaction(action_id)
                if isinstance(result, tuple):
                    screen_name = result[0]
                    if screen_name == "BattleScreen":
                        enemy = result[1]
                        self._initiate_battle(enemy)
                    elif screen_name in SCREEN_MAP:
                        screen_cls = SCREEN_MAP[screen_name]
                        self.push_screen(screen_cls(result[1]))
                self.update_map()
                self.update_info()
                return

    # -------------------------------------------------------------------
    # Movement
    # -------------------------------------------------------------------

    def _do_move(self, dx, dy):
        if self.ctrl.state == GameState.INSPECTING:
            return
        should_advance, pending = self.ctrl.move_player(dx, dy)
        if should_advance:
            self.advance_world()
        if pending:
            enemy = pending
            self.ctrl._pending_battle = None
            self._initiate_battle(enemy)
        self.update_map()
        self.update_info()

    # -------------------------------------------------------------------
    # Battle
    # -------------------------------------------------------------------

    def _initiate_battle(self, enemy):
        if not enemy or not enemy.alive:
            return
        ctrl = BattleController(self.ctrl.ship, enemy, self)
        self.push_screen(BattleScreen(ctrl))

    # -------------------------------------------------------------------
    # Quick battle / expedition (debug modes)
    # -------------------------------------------------------------------

    def _start_quick_battle(self):
        from models import create_random_ship, create_random_enemy
        self.ctrl.state = GameState.PLAYING
        self.ctrl.race_selected = True
        player = create_random_ship(is_player=True)
        enemy = create_random_enemy()
        self.ctrl.ship = player
        self.ctrl.logger.system("Quick Battle mode.")
        ctrl = BattleController(player, enemy, self)
        self.push_screen(BattleScreen(ctrl, quick_battle=True))

    def _start_quick_expedition(self):
        from expedition import (
            ExpeditionScreen, ExpeditionController,
            create_quick_expedition_character, generate_quick_expedition_map,
        )
        char = create_quick_expedition_character()
        emap = generate_quick_expedition_map()
        ectrl = ExpeditionController(char, emap)
        self.push_screen(ExpeditionScreen(ectrl, quick_expedition=True))

    # -------------------------------------------------------------------
    # Console
    # -------------------------------------------------------------------

    def process_command(self, raw):
        result = self.ctrl.process_command(raw)
        if isinstance(result, tuple):
            action = result[0]
            if action == "battle":
                self._initiate_battle(result[1])
            elif action == "exit":
                self.exit()
        self.update_info()


if __name__ == "__main__":
    app = GalaxyMapApp()
    app.run()
