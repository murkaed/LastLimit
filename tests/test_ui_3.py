"""UI coverage batch 3 — Shipyard, Crafting, Hire screens (2026-08-03)."""

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


def _at_station(app):
    st = app.ctrl.galaxy.stations[0]
    app.ctrl.player_x, app.ctrl.player_y = st.x, st.y
    return st


# =============================================================================
# ShipyardScreen
# =============================================================================

@pytest.mark.asyncio
async def test_shipyard_tabs_and_buy():
    from ui import ShipyardScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        st = _at_station(app)
        st.hulls_for_sale = ["frigate"]
        st.modules_for_sale = ["laser_turret"]
        app.ctrl.ship.credits = 20000
        screen = ShipyardScreen(st)
        await _push(pilot, app, screen)
        # вкладки
        await pilot.press("m")
        await pilot.pause()
        assert screen.tab == "modules"
        await pilot.press("u")
        await pilot.pause()
        assert screen.tab == "upgrades"
        await pilot.press("h")
        await pilot.pause()
        assert screen.tab == "hulls"
        # покупка корпуса
        screen.on_input_submitted(_ev("buy 1"))
        await pilot.pause()
        assert "frigate" not in st.hulls_for_sale
        assert "frigate" in app.ctrl.ship.owned_hulls
        # модуль
        screen.on_input_submitted(_ev("buy mod 1"))
        await pilot.pause()
        assert "laser_turret" not in st.modules_for_sale
        # продать/сменить
        screen.on_input_submitted(_ev("sell shuttle"))
        await pilot.pause()
        screen.on_input_submitted(_ev("switch frigate"))
        await pilot.pause()
        assert app.ctrl.ship.hull_id == "frigate"
        # апгрейд
        screen.on_input_submitted(_ev("upgrade bogus_upgrade"))
        await pilot.pause()
        screen.on_input_submitted(_ev("close"))
        await pilot.pause()


# =============================================================================
# CraftingScreen
# =============================================================================

@pytest.mark.asyncio
async def test_crafting_screen():
    from ui import CraftingScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        st = _at_station(app)
        st.recipes_available = ["repair_kit", "fuel_cell"]
        app.ctrl.ship.cargo.add("metal", 10)
        app.ctrl.ship.cargo.add("electronics", 10)
        app.ctrl.ship.cargo.add("ice", 10)
        app.ctrl.ship.cargo.add("silicon", 10)
        screen = CraftingScreen(st)
        await _push(pilot, app, screen)
        screen.on_input_submitted(_ev("craft 1 repair_kit"))
        await pilot.pause()
        assert app.ctrl.ship.cargo.has("repair_kit") >= 1
        # крафт нескольких
        screen2 = CraftingScreen(st)
        await _push(pilot, app, screen2)
        screen2.on_input_submitted(_ev("craft 2 fuel_cell"))
        await pilot.pause()
        assert app.ctrl.ship.cargo.has("fuel_cell") >= 2
        # нет цели / неизвестный рецепт
        screen3 = CraftingScreen(st)
        await _push(pilot, app, screen3)
        screen3.on_input_submitted(_ev("craft"))
        await pilot.pause()
        screen4 = CraftingScreen(st)
        await _push(pilot, app, screen4)
        screen4.on_input_submitted(_ev("craft 1 bogus_recipe"))
        await pilot.pause()
        rendered = app.ctrl.logger.render_plain(n=10)
        assert "not available" in rendered or "недоступен" in rendered
        # close через клавишу
        screen5 = CraftingScreen(st)
        await _push(pilot, app, screen5)
        await pilot.press("q")
        await pilot.pause()


# =============================================================================
# HireScreen
# =============================================================================

@pytest.mark.asyncio
async def test_hire_screen():
    from models import CrewMember
    from ui import HireScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        st = _at_station(app)
        st.crew_for_hire = [CrewMember("Recruit", "Engineer")]
        app.ctrl.ship.credits = 1000
        screen = HireScreen(st)
        await _push(pilot, app, screen)
        screen.on_input_submitted(_ev("hire 1"))
        await pilot.pause()
        assert len(st.crew_for_hire) == 0
        assert any(cm.name == "Recruit" for cm in app.ctrl.ship.crew_members)
        # невалидный номер
        screen2 = HireScreen(st)
        await _push(pilot, app, screen2)
        screen2.on_input_submitted(_ev("hire abc"))
        await pilot.pause()
        screen2.on_input_submitted(_ev("close"))
        await pilot.pause()
