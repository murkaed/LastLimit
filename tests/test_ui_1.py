"""UI coverage batch 1 — Cargo, Trade, Bridge, Missions screens (2026-08-03)."""

from types import SimpleNamespace

import pytest

from galaxy_map import GalaxyMapApp, GameState


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
# CargoScreen
# =============================================================================

@pytest.mark.asyncio
async def test_cargo_screen_actions():
    from ui import CargoScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        ship = app.ctrl.ship
        ship.cargo.add("metal", 3)
        ship.cargo.add("laser_turret", 1)
        ship.cargo.add("repair_kit", 2)
        screen = CargoScreen()
        await _push(pilot, app, screen)
        # фильтры
        for key in ("2", "3", "4", "5", "6", "1"):
            await pilot.press(key)
            await pilot.pause()
        assert screen._filter == "all"
        # выбор и использование
        await pilot.press("enter")  # use selected item
        await pilot.pause()
        # джетишон
        await pilot.press("delete")
        await pilot.pause()
        # продать сырьё (не у станции)
        await pilot.press("s")
        await pilot.pause()
        rendered = app.ctrl.logger.render_plain(n=10)
        assert "Not docked" in rendered or "не пристыкован" in rendered
        # ввод close
        screen.on_input_submitted(_ev("close"))
        await pilot.pause()


@pytest.mark.asyncio
async def test_cargo_sell_junk_at_station():
    from ui import CargoScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        st = app.ctrl.galaxy.stations[0]
        app.ctrl.player_x, app.ctrl.player_y = st.x, st.y
        app.ctrl.ship.cargo.add("ore", 5)
        screen = CargoScreen()
        await _push(pilot, app, screen)
        await pilot.press("s")
        await pilot.pause()
        assert app.ctrl.ship.cargo.has("ore") == 0
        await pilot.press("escape")
        await pilot.pause()


@pytest.mark.asyncio
async def test_cargo_use_item_module_and_consumable():
    from ui import CargoScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        ship = app.ctrl.ship
        ship.cargo.add("metal", 1)
        ship.cargo.add("repair_kit", 1)
        ship.hull = 40
        screen = CargoScreen()
        await _push(pilot, app, screen)
        # металл — ресурс, использовать нельзя
        screen._filter = "raw"
        screen._selected = 0
        screen._use_item()
        # ремкомплект — расходник
        screen._filter = "consumable"
        screen._use_item()
        assert ship.cargo.has("repair_kit") == 0
        # пустой список — без краша
        screen._filter = "module"
        screen._use_item()
        screen._jettison()


# =============================================================================
# TradeScreen
# =============================================================================

@pytest.mark.asyncio
async def test_trade_screen_buy_sell_and_close():
    from ui import TradeScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        st = app.ctrl.galaxy.stations[0]
        app.ctrl.player_x, app.ctrl.player_y = st.x, st.y
        app.ctrl.ship.credits = 5000
        screen = TradeScreen(st)
        await _push(pilot, app, screen)
        screen.on_input_submitted(_ev("buy ore 5"))
        await pilot.pause()
        assert app.ctrl.ship.cargo.has("ore") >= 5
        screen.on_input_submitted(_ev("close"))
        await pilot.pause()
        # q тоже закрывает
        screen2 = TradeScreen(st)
        await _push(pilot, app, screen2)
        await pilot.press("q")
        await pilot.pause()


# =============================================================================
# BridgeScreen
# =============================================================================

@pytest.mark.asyncio
async def test_bridge_screen_navigation():
    from ui import BridgeScreen, EngineeringScreen, TacticalScreen, CargoScreen, CrewScreen, MissionsScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        screen = BridgeScreen()
        await _push(pilot, app, screen)
        # 1 → Engineering
        await pilot.press("1")
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, EngineeringScreen)
        await pilot.press("escape")
        await pilot.pause()
        # 2 → Tactical
        await pilot.press("2")
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, TacticalScreen)
        await pilot.press("escape")
        await pilot.pause()
        # 3 → Cargo
        await pilot.press("3")
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, CargoScreen)
        await pilot.press("escape")
        await pilot.pause()
        # 4 → Crew
        await pilot.press("4")
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, CrewScreen)
        await pilot.press("escape")
        await pilot.pause()
        # 5 → Missions
        await pilot.press("5")
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, MissionsScreen)
        await pilot.press("escape")
        await pilot.pause()


@pytest.mark.asyncio
async def test_bridge_station_services():
    from ui import BridgeScreen, StationServicesScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        st = app.ctrl.galaxy.stations[0]
        app.ctrl.player_x, app.ctrl.player_y = st.x, st.y
        screen = BridgeScreen()
        await _push(pilot, app, screen)
        await pilot.press("7")
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, StationServicesScreen)
        await pilot.press("escape")
        await pilot.pause()


# =============================================================================
# MissionsScreen
# =============================================================================

@pytest.mark.asyncio
async def test_missions_screen_active_and_available():
    from models import Mission
    from ui import MissionsScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        ship = app.ctrl.ship
        m = Mission("deliver", "metal", 3, "X", 100, title="Test Mission", description="Desc")
        ship.add_mission(m)
        st = app.ctrl.galaxy.stations[0]
        st.missions = [Mission("deliver", "ore", 2, "Y", 50, title="Station Mission")]
        app.ctrl.player_x, app.ctrl.player_y = st.x, st.y
        screen = MissionsScreen()
        await _push(pilot, app, screen)
        # активная вкладка
        await pilot.press("down")
        await pilot.press("up")
        await pilot.pause()
        await pilot.press("enter")  # track
        await pilot.pause()
        assert ship.tracked_mission == m.id
        await pilot.press("d")  # details
        await pilot.pause()
        await pilot.press("a")  # abandon
        await pilot.pause()
        assert m.id not in (x.id for x in ship.missions)
        # вкладка available
        await pilot.press("2")
        await pilot.pause()
        assert screen._tab == "available"
        await pilot.press("enter")  # accept
        await pilot.pause()
        assert len(st.missions) == 0
        assert len(ship.missions) == 1


@pytest.mark.asyncio
async def test_missions_input_commands():
    from models import Mission
    from ui import MissionsScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        ship = app.ctrl.ship
        st = app.ctrl.galaxy.stations[0]
        st.missions = [Mission("deliver", "ore", 2, "Y", 50, title="Station Mission")]
        app.ctrl.player_x, app.ctrl.player_y = st.x, st.y
        screen = MissionsScreen()
        await _push(pilot, app, screen)
        screen.on_input_submitted(_ev("accept 1"))
        await pilot.pause()
        assert len(ship.missions) == 1
        assert len(st.missions) == 0
        mid = ship.missions[0].id
        screen.on_input_submitted(_ev(f"track {mid}"))
        await pilot.pause()
        screen.on_input_submitted(_ev(f"detail {mid}"))
        await pilot.pause()
        screen.on_input_submitted(_ev(f"abandon {mid}"))
        await pilot.pause()
        assert len(ship.missions) == 0
        screen.on_input_submitted(_ev("close"))
        await pilot.pause()
