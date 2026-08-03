"""Tests for P0 fixes from the audit (2026-08-03).

Covers:
- push_screen callback passthrough (colony build menu TypeError)
- push-then-dismiss ordering (battle never started)
- F5 double-push of CrewScreen
- HELP/NEWS soft-lock and Esc pausing after closing the interaction menu
- consumables wasted at full hull / zero shield cap
- console ValueError on non-numeric input
- mission destroyed when the mission log is full
"""

import pytest
from textual.screen import Screen

from galaxy_map import GalaxyMapApp, GameState
from game_controller import GameController
from models import PirateShip, Mission
from battle import BattleController


async def _start_game(pilot, app):
    """Full start flow (menu → mode → race → origin → PLAYING)."""
    await pilot.pause()
    await pilot.press("1")
    await pilot.pause()
    await pilot.press("1")
    await pilot.pause()
    await pilot.press("1")
    await pilot.pause()
    await pilot.press("1")
    await pilot.pause()
    assert app.ctrl.state == GameState.PLAYING


# =============================================================================
# P0-1: push_screen must accept Textual's callback parameter
# =============================================================================

@pytest.mark.asyncio
async def test_push_screen_accepts_callback():
    """PlanetSurfaceScreen passes a callback to push_screen — no TypeError,
    and the callback fires with the dismiss result."""
    app = GalaxyMapApp()
    results = []

    class Probe(Screen):
        def on_key(self, event):
            if event.key == "escape":
                event.stop()
                self.dismiss("done")

    async with app.run_test(size=(80, 44)) as pilot:
        app.push_screen(Probe(), callback=results.append)
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert results == ["done"]
        assert len(app.screen_stack) == 1


# =============================================================================
# P0-2: dismiss-then-push — battle screen must survive
# =============================================================================

@pytest.mark.asyncio
async def test_tactical_start_battle_keeps_battle_screen():
    """TacticalScreen._start_battle must dismiss first, then push: otherwise
    dismiss() pops the just-pushed BattleScreen off the stack."""
    from ui import TacticalScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        # Place a pirate within weapon range of the player
        p = PirateShip(app.ctrl.player_x + 1, app.ctrl.player_y)
        app.ctrl.galaxy.pirates.append(p)
        tac = TacticalScreen()
        app.push_screen(tac)
        await pilot.pause()
        tac._start_battle(p)
        await pilot.pause()
        from battle import BattleScreen
        assert isinstance(app.screen, BattleScreen)


@pytest.mark.asyncio
async def test_command_console_dismiss_before_process_command():
    """CommandScreen: submitting 'attack <npc>' must leave BattleScreen on top
    (dismiss first, then process_command which may push a screen)."""
    from types import SimpleNamespace
    from ui import CommandScreen
    from battle import BattleScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        p = PirateShip(app.ctrl.player_x + 1, app.ctrl.player_y)
        p.name = "TargetPirate"
        app.ctrl.galaxy.pirates.append(p)
        screen = CommandScreen()
        app.push_screen(screen)
        await pilot.pause()
        screen.on_input_submitted(SimpleNamespace(value="attack TargetPirate"))
        await pilot.pause()
        assert isinstance(app.screen, BattleScreen)


# =============================================================================
# P0-3: F5 must open CrewScreen exactly once
# =============================================================================

@pytest.mark.asyncio
async def test_f5_opens_crew_screen_once():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("f5")
        await pilot.pause()
        assert len(app.screen_stack) == 2
        # One Esc returns to the map (not two)
        await pilot.press("escape")
        await pilot.pause()
        assert len(app.screen_stack) == 1
        assert app.ctrl.state == GameState.PLAYING


# =============================================================================
# P0-4: HELP/NEWS exit + Esc in interaction menu must not pause
# =============================================================================

@pytest.mark.asyncio
async def test_help_exits_back_to_playing():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("h")
        await pilot.pause()
        assert app.ctrl.state == GameState.HELP
        await pilot.press("h")
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING


@pytest.mark.asyncio
async def test_help_escape_returns_without_pause():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("h")
        await pilot.pause()
        assert app.ctrl.state == GameState.HELP
        await pilot.press("escape")
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING


@pytest.mark.asyncio
async def test_news_exits_back_to_playing():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("n")
        await pilot.pause()
        assert app.ctrl.state == GameState.NEWS
        await pilot.press("n")
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING


@pytest.mark.asyncio
async def test_escape_closes_interaction_menu_without_pausing():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("0")
        await pilot.pause()
        assert app.ctrl._interaction_active
        await pilot.press("escape")
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING
        assert not app.ctrl._interaction_active


# =============================================================================
# P0-5: consumables must not be wasted
# =============================================================================

def test_use_repair_kit_not_wasted_at_full_hull(player_ship):
    player_ship.hull = player_ship.max_hull
    before = player_ship.cargo.has("repair_kit")
    msg, ok = player_ship.use_item("repair_kit")
    assert ok is False
    assert player_ship.cargo.has("repair_kit") == before
    assert player_ship.hull == player_ship.max_hull


def test_use_shield_booster_not_wasted_without_shield_cap(player_ship):
    for m in player_ship.compartments["shield"]["modules"]:
        m.active = False
        m.durability = 0
    assert player_ship.get_effective_stats().get("shield_cap", 0) == 0
    player_ship.cargo.add("shield_booster", 1)
    msg, ok = player_ship.use_item("shield_booster")
    assert ok is False
    assert player_ship.cargo.has("shield_booster") == 1


def test_battle_use_item_not_wasted_at_full_hull(player_ship):
    enemy = PirateShip(1, 1)
    player_ship.hull = player_ship.max_hull
    before = player_ship.cargo.has("repair_kit")
    bc = BattleController(player_ship, enemy)
    bc.do_use_item("repair_kit")
    assert player_ship.cargo.has("repair_kit") == before
    assert any("already max" in m for m in bc.log)


def test_battle_use_item_still_consumed_when_effect_applies(player_ship):
    enemy = PirateShip(1, 1)
    player_ship.hull = 40
    before = player_ship.cargo.has("repair_kit")
    bc = BattleController(player_ship, enemy)
    # Ход врага не запускаем: _next_turn выходит по over, иначе случайный
    # урон/потеря груза делают тест зависимым от глобального random
    bc.over = True
    bc.do_use_item("repair_kit")
    assert player_ship.cargo.has("repair_kit") == before - 1
    assert player_ship.hull == 60


# =============================================================================
# P0-6: console must not crash on non-numeric input
# =============================================================================

def test_console_invalid_numbers_do_not_crash():
    ctrl = GameController()
    ctrl.process_command("give metal abc")
    ctrl.process_command("take metal abc")
    ctrl.process_command("set hull abc")
    ctrl.process_command("power reactor abc")
    ctrl.process_command("cargo jettison metal abc")
    ctrl.process_command("smuggle metal abc")
    ctrl.process_command("trade buy metal abc")
    ctrl.process_command("market scan abc")
    # Ничего не изменилось и никаких исключений
    assert ctrl.ship.cargo.has("metal") == 0
    assert ctrl.ship.hull == ctrl.ship.max_hull


def test_console_invalid_number_logs_message():
    ctrl = GameController()
    ctrl.process_command("give metal abc")
    rendered = ctrl.logger.render_plain(n=20)
    assert "Invalid number" in rendered


def test_console_valid_number_still_works():
    ctrl = GameController()
    ctrl.process_command("give metal 5")
    assert ctrl.ship.cargo.has("metal") == 5


# =============================================================================
# P0-7: mission must not be destroyed when the mission log is full
# =============================================================================

@pytest.mark.asyncio
async def test_mission_not_lost_when_log_full():
    from types import SimpleNamespace
    from ui import MissionScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        ctrl = app.ctrl
        st = next((s for s in ctrl.galaxy.stations if s.missions), None)
        if st is None:
            return  # no station with missions in this seed — vacuous
        ctrl.player_x, ctrl.player_y = st.x, st.y
        while len(ctrl.ship.missions) < 5:
            m = Mission("deliver", "ore", 1, "X", 1)
            ctrl.ship.add_mission(m)
        n_before = len(st.missions)
        screen = MissionScreen(st)
        app.push_screen(screen)
        await pilot.pause()
        screen.on_input_submitted(SimpleNamespace(value="accept 1"))
        await pilot.pause()
        assert len(st.missions) == n_before  # mission NOT removed
        assert len(ctrl.ship.missions) == 5
