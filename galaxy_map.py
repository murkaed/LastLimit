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

    # Игра управляется клавиатурой через экранные on_key-хендлеры. Авто-фокус
    # Input'а (Textual-дефолт "*") перехватывал Enter/цифры/буквы на экранах
    # с полем ввода и делал их on_key мёртвым. Input остаётся доступен
    # по Tab/клику для текстовых команд.
    AUTO_FOCUS = None

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
    def _interaction_submenu_active(self):
        return self.ctrl._interaction_submenu_active

    @_interaction_submenu_active.setter
    def _interaction_submenu_active(self, v):
        self.ctrl._interaction_submenu_active = v

    @property
    def _saved_interaction_actions(self):
        return self.ctrl._saved_interaction_actions

    @_saved_interaction_actions.setter
    def _saved_interaction_actions(self, v):
        self.ctrl._saved_interaction_actions = v

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
        # Load fog of war settings
        self.ctrl.fog_enabled = _cfg.get("fog_of_war", False)
        self.ctrl.fog_range = _cfg.get("fog_range", 5)
        self.ctrl.explored_tiles = set()
        if self.ctrl.fog_enabled:
            self.ctrl._discover_tiles()
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

    def push_screen(self, screen, callback=None, wait_for_dismiss=False, *, mode=None):
        self.ctrl.world_frozen = True
        super().push_screen(screen, callback=callback, wait_for_dismiss=wait_for_dismiss, mode=mode)

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
        # Any pushed screen (ship menu, battle, expedition, trade, etc.)
        # blocks game key handling — the top screen's own on_key owns the event.
        if len(self.screen_stack) > 1:
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
        elif self.ctrl.state in (GameState.HELP, GameState.NEWS):
            # Выход из HELP/NEWS: Esc, H или N возвращают в предыдущее состояние.
            # Ранний return предотвращает срабатывание глобальных клавиш ниже
            # (например, повторный вход в HELP по "h" или пауза по Esc).
            if event.key in ("escape", "h", "n"):
                self.ctrl.state = self.ctrl._prev_state or GameState.PLAYING
                self.update_map()
                self.update_info()
                return
        elif self._interaction_active:
            self._on_interaction_key(event)

        # Global keys — skip escape if it was already handled by pause handler
        if event.key == "escape" and prev_state != GameState.PAUSED and self.ctrl.state in (
                GameState.PLAYING, GameState.INSPECTING):
            if self._interaction_active:
                self._interaction_active = False
                self._interaction_submenu_active = False
                self._saved_interaction_actions = None
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
        elif event.key == "f6":
            self._do_save()
        elif event.key == "f7":
            self._do_load()
        elif event.key == "f10":
            self._toggle_fog()

    def _toggle_fog(self):
        self.ctrl.fog_enabled = not self.ctrl.fog_enabled
        if self.ctrl.fog_enabled:
            self.ctrl.explored_tiles = set()
            self.ctrl._discover_tiles()
            self.ctrl.logger.system(f"🌫 Fog of War ON (range {self.ctrl.fog_range}).")
        else:
            self.ctrl.logger.system("🌫 Fog of War OFF.")
        self.update_map()

    def _do_save(self):
        if self.ctrl.state != GameState.PLAYING:
            return
        self._saved_state = self.ctrl.save_state()
        self.ctrl.logger.system("💾 Game saved (F7 to load).")

    def _do_load(self):
        if not hasattr(self, "_saved_state") or self._saved_state is None:
            self.ctrl.logger.system("No save data. Press F6 to save first.")
            return
        try:
            GameController.restore_from_state(self.ctrl, self._saved_state)
        except Exception as e:
            self.ctrl.logger.system(f"Load failed: {e}.")
            return
        self.update_map()
        self.update_info()
        self.ctrl.logger.system("📂 Game loaded.")

    def _on_race_select_key(self, event):
        k = event.key.lower()
        # Mode selection (shown first when pressing "New Game")
        if self.ctrl._show_mode_select:
            if k in ("1", "2"):
                self.ctrl.select_mode(k)
                self.update_map()
                self.update_info()
            elif k == "0":
                self.ctrl._show_mode_select = False
                self.ctrl.state = GameState.START_SCREEN
                self.update_map()
                self.update_info()
            return
        # Origin selection (shown after race is picked)
        if self.ctrl._show_origin_select:
            if k in ("1", "2", "3", "4", "5"):
                self.ctrl.select_origin(k)
                self.update_map()
                self.update_info()
            return
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
            self.ctrl._show_mode_select = True
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
        if self._interaction_active:
            # Esc здесь НЕ обрабатывается: его закрывает глобальный блок on_key
            # (закрывает меню и возвращается, не ставя паузу).
            if k == "0":
                self._interaction_active = False
                self._interaction_submenu_active = False
                self._saved_interaction_actions = None
                self.update_map()
                self.update_info()
                event.stop()
                return
            if k.isdigit():
                self._on_interaction_key(event)
                return
            return  # block movement and other keys
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
        elif k in ("f2", "F2"):
            self.push_screen(EngineeringScreen())
        elif k in ("f3", "F3"):
            self.push_screen(TacticalScreen())
        elif k in ("f4", "F4"):
            self.push_screen(CargoScreen())
        elif k in ("f5", "F5"):
            self.push_screen(CrewScreen())
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

        # ── Ship screens submenu mode ──
        if self._interaction_submenu_active:
            if k == "escape" or k == "0":
                self._interaction_submenu_active = False
                self.ctrl.interaction_actions = self._saved_interaction_actions
                self._saved_interaction_actions = None
                self.update_map()
                self.update_info()
                event.stop()
                return
            if k.isdigit():
                idx = int(k) - 1
                if 0 <= idx < len(self.ctrl.interaction_actions):
                    _, label, action_id, _ = self.ctrl.interaction_actions[idx]
                    self._interaction_active = False
                    self._interaction_submenu_active = False
                    self._push_ship_screen(action_id)
                    self.update_map()
                    self.update_info()
                return

        # ── Main interaction menu mode ──
        if k == "escape" or k == "0":
            self._interaction_active = False
            self.ctrl.state = GameState.PLAYING
            self.update_map()
            self.update_info()
            event.stop()
            return
        if k.isdigit():
            idx = int(k) - 1
            if 0 <= idx < len(self.ctrl.interaction_actions):
                _, label, action_id, _ = self.ctrl.interaction_actions[idx]

                # Enter ship screens submenu
                if action_id == "ship_screens":
                    self._saved_interaction_actions = list(self.ctrl.interaction_actions)
                    self._interaction_submenu_active = True
                    self.ctrl.interaction_actions = [
                        ("1", "🚢 Bridge (F1)", "bridge", "Ship"),
                        ("2", "⚙ Engineering (F2)", "engineering", "Ship"),
                        ("3", "🎯 Tactical (F3)", "tactical", "Ship"),
                        ("4", "📦 Cargo (F4)", "cargo", "Ship"),
                        ("5", "👥 Crew (F5)", "crew", "Ship"),
                    ]
                    self.update_map()
                    self.update_info()
                    return

                self._interaction_active = False
                result = self.ctrl.run_interaction(action_id)
                if isinstance(result, tuple):
                    screen_name = result[0]
                    if screen_name == "BattleScreen":
                        enemy = result[1]
                        self._initiate_battle(enemy)
                    elif screen_name == "BridgeScreen":
                        self.push_screen(BridgeScreen())
                    elif screen_name == "EngineeringScreen":
                        self.push_screen(EngineeringScreen())
                    elif screen_name == "TacticalScreen":
                        self.push_screen(TacticalScreen())
                    elif screen_name == "CargoScreen":
                        self.push_screen(CargoScreen())
                    elif screen_name == "CrewScreen":
                        self.push_screen(CrewScreen())
                    elif screen_name in SCREEN_MAP:
                        screen_cls = SCREEN_MAP[screen_name]
                        self.push_screen(screen_cls(result[1]))
                self.update_map()
                self.update_info()
                return

    def _push_ship_screen(self, action_id):
        """Pushes a ship screen by action_id (bridge/engineering/tactical/cargo/crew)."""
        m = {
            "bridge": BridgeScreen,
            "engineering": EngineeringScreen,
            "tactical": TacticalScreen,
            "cargo": CargoScreen,
            "crew": CrewScreen,
        }
        cls = m.get(action_id)
        if cls:
            self.push_screen(cls())

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
        player = create_random_ship(is_player=True)
        enemy = create_random_enemy()
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
