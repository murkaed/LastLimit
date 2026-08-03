"""UI coverage batch 2 — Engineering, Tactical, ModuleShop, Mission, Crew (2026-08-03)."""

from types import SimpleNamespace

import pytest

from galaxy_map import GalaxyMapApp, GameState
from models import PirateShip, ShipModule


async def _start_game(pilot, app):
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


async def _push(pilot, app, screen):
    app.push_screen(screen)
    await pilot.pause()
    await pilot.pause()
    assert app.screen is screen


def _ev(value):
    return SimpleNamespace(value=value, stop=lambda: None)


# =============================================================================
# EngineeringScreen
# =============================================================================

@pytest.mark.asyncio
async def test_engineering_screen():
    from ui import EngineeringScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        screen = EngineeringScreen()
        await _push(pilot, app, screen)
        await pilot.press("3")  # выбрать weapon
        await pilot.pause()
        assert screen._selected_comp == "weapon"
        await pilot.press("8")  # мощность 8
        await pilot.pause()
        assert app.ctrl.ship.compartments["weapon"]["power"] == 8
        await pilot.press("0")  # мощность 0
        await pilot.pause()
        assert app.ctrl.ship.compartments["weapon"]["power"] == 0
        # текстовые команды
        screen.on_input_submitted(_ev("power reactor 5"))
        await pilot.pause()
        assert app.ctrl.ship.compartments["reactor"]["power"] == 5
        screen.on_input_submitted(_ev("close"))
        await pilot.pause()


# =============================================================================
# TacticalScreen
# =============================================================================

@pytest.mark.asyncio
async def test_tactical_screen_navigation_and_battle():
    from ui import TacticalScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        from models import ShipModule
        # дефолтный корабль без оружия — добавляем
        app.ctrl.ship.compartments["weapon"]["modules"].append(ShipModule("laser_turret"))
        # пират в радиусе сенсоров
        p = PirateShip(app.ctrl.player_x + 3, app.ctrl.player_y)
        app.ctrl.galaxy.pirates.append(p)
        screen = TacticalScreen()
        await _push(pilot, app, screen)
        await pilot.press("down")
        await pilot.pause()
        await pilot.press("up")
        await pilot.pause()
        await pilot.press("tab")  # панель целей
        await pilot.pause()
        assert screen._active_panel == "targets"
        await pilot.press("down")
        await pilot.pause()
        await pilot.press("f")  # огонь по врагу
        await pilot.pause()
        await pilot.pause()
        from battle import BattleScreen
        assert isinstance(app.screen, BattleScreen)
        await pilot.press("escape")
        await pilot.pause()
        await pilot.pause()


@pytest.mark.asyncio
async def test_tactical_ammo_load():
    from ui import TacticalScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        ship = app.ctrl.ship
        kw = ShipModule("kinetic_cannon")
        kw.current_ammo = 0
        ship.compartments["weapon"]["modules"].append(kw)
        ship.cargo.add("slug", 10)
        screen = TacticalScreen()
        await _push(pilot, app, screen)
        await pilot.press("l")  # панель загрузки
        await pilot.pause()
        assert screen._show_ammo_load
        await pilot.press("s")  # slug
        await pilot.pause()
        assert kw.current_ammo == 10
        await pilot.press("0")  # закрыть панель
        await pilot.pause()
        assert not screen._show_ammo_load
        await pilot.press("escape")
        await pilot.pause()


# =============================================================================
# ModuleShopScreen
# =============================================================================

@pytest.mark.asyncio
async def test_module_shop_buy():
    from ui import ModuleShopScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        st = app.ctrl.galaxy.stations[0]
        st.modules_for_sale = ["laser_turret"]
        app.ctrl.player_x, app.ctrl.player_y = st.x, st.y
        app.ctrl.ship.credits = 5000
        screen = ModuleShopScreen(st)
        await _push(pilot, app, screen)
        screen.on_input_submitted(_ev("buy 1"))
        await pilot.pause()
        assert "laser_turret" not in st.modules_for_sale
        # не хватает кредитов
        st.modules_for_sale = ["ion_drive"]
        app.ctrl.ship.credits = 1
        screen2 = ModuleShopScreen(st)
        await _push(pilot, app, screen2)
        screen2.on_input_submitted(_ev("buy 1"))
        await pilot.pause()
        assert "ion_drive" in st.modules_for_sale
        # close
        screen3 = ModuleShopScreen(st)
        await _push(pilot, app, screen3)
        await pilot.press("q")
        await pilot.pause()


# =============================================================================
# MissionScreen
# =============================================================================

@pytest.mark.asyncio
async def test_mission_screen_keys():
    from models import Mission
    from ui import MissionScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        st = app.ctrl.galaxy.stations[0]
        st.missions = [Mission("deliver", "ore", 2, "Y", 50, title="M1")]
        app.ctrl.player_x, app.ctrl.player_y = st.x, st.y
        screen = MissionScreen(st)
        await _push(pilot, app, screen)
        await pilot.press("down")
        await pilot.press("up")
        await pilot.pause()
        await pilot.press("enter")  # принять
        await pilot.pause()
        assert len(st.missions) == 0
        assert len(app.ctrl.ship.missions) == 1
        # accept через ввод
        st.missions = [Mission("deliver", "ore", 2, "Y", 50, title="M2")]
        screen2 = MissionScreen(st)
        await _push(pilot, app, screen2)
        screen2.on_input_submitted(_ev("accept 1"))
        await pilot.pause()
        assert len(st.missions) == 0
        await pilot.press("escape")
        await pilot.pause()


# =============================================================================
# CrewScreen
# =============================================================================

@pytest.mark.asyncio
async def test_crew_screen():
    from ui import CrewScreen, BridgeScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        screen = CrewScreen()
        await _push(pilot, app, screen)
        screen.on_input_submitted(_ev("close"))
        await pilot.pause()
        # F1 → мостик
        screen2 = CrewScreen()
        await _push(pilot, app, screen2)
        await pilot.press("f1")
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, BridgeScreen)
        await pilot.press("escape")
        await pilot.pause()
