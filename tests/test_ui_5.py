"""UI coverage batch 5 — BuildingMenu, PlanetSurfaceScreen (2026-08-03)."""

from types import SimpleNamespace

import pytest

from galaxy_map import GalaxyMapApp, GameState
from colony import ColonyManager, SURFACE_SIZE


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


def _colony():
    c = ColonyManager("TestCol", "temperate")
    c.surface = [["plain"] * SURFACE_SIZE for _ in range(SURFACE_SIZE)]
    c.storage = {"metal": 50, "electronics": 50, "silicon": 50,
                 "ice": 50, "ore": 50, "fuel_cell": 0}
    c.colonists = 5
    c.max_colonists = 10
    c.happiness = 80
    c.max_storage = 1000
    c.place_building("command_center", SURFACE_SIZE // 2 - 1, SURFACE_SIZE // 2 - 1)
    return c


# =============================================================================
# BuildingMenu
# =============================================================================

@pytest.mark.asyncio
async def test_building_menu():
    from ui import BuildingMenu
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        colony = _colony()
        screen = BuildingMenu(colony)
        await _push(pilot, app, screen)
        await pilot.press("down")
        await pilot.pause()
        await pilot.press("up")
        await pilot.pause()
        # фильтры категорий 1-6
        for key in ("1", "2", "3", "4", "5", "6", "1"):
            await pilot.press(key)
            await pilot.pause()
        # Enter выбирает здание и закрывает с результатом
        screen._selected = 0
        await pilot.press("enter")
        await pilot.pause()
        assert screen._result is not None or len(app.screen_stack) == 1


# =============================================================================
# PlanetSurfaceScreen
# =============================================================================

@pytest.mark.asyncio
async def test_planet_surface_build_and_remove():
    from ui import PlanetSurfaceScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        colony = _colony()
        screen = PlanetSurfaceScreen(colony, SURFACE_SIZE // 2, SURFACE_SIZE // 2)
        await _push(pilot, app, screen)
        # движение
        await pilot.press("w")
        await pilot.press("a")
        await pilot.pause()
        # информация по тайлу
        await pilot.press("i")
        await pilot.pause()
        # меню строительства
        await pilot.press("b")
        await pilot.pause()
        await pilot.pause()
        from ui import BuildingMenu
        assert isinstance(app.screen, BuildingMenu)
        await pilot.press("escape")
        await pilot.pause()
        # управление колонистами
        await pilot.press("c")
        await pilot.pause()
        # передача груза без космопорта (заглавная S)
        await pilot.press("S")
        await pilot.pause()
        content = str(screen.query_one("#planet-surface").render())
        assert "Spaceport" in content or "космопорт" in content
        assert len(app.screen.query("#transfer-input")) == 0
        # удаление здания (курсор на command_center)
        screen._cursor_x = SURFACE_SIZE // 2 - 1
        screen._cursor_y = SURFACE_SIZE // 2 - 1
        await pilot.press("r")
        await pilot.pause()
        assert colony.get_building_at(SURFACE_SIZE // 2 - 1, SURFACE_SIZE // 2 - 1) is None
        await pilot.press("escape")
        await pilot.pause()


@pytest.mark.asyncio
async def test_planet_surface_place_building():
    from ui import PlanetSurfaceScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        colony = _colony()
        screen = PlanetSurfaceScreen(colony, SURFACE_SIZE // 2, SURFACE_SIZE // 2)
        await _push(pilot, app, screen)
        # режим строительства: выбор здания через callback
        screen._on_build_result("smelter")
        assert screen._mode == "build"
        # перемещаем курсор и ставим здание
        screen._cursor_x = SURFACE_SIZE // 2 + 2
        screen._cursor_y = SURFACE_SIZE // 2 + 2
        await pilot.press("enter")
        await pilot.pause()
        assert colony.get_building_at(SURFACE_SIZE // 2 + 2, SURFACE_SIZE // 2 + 2) is not None
        assert screen._mode == "view"
        # не хватает ресурсов — отмена
        colony.storage = {"metal": 0}
        screen._on_build_result("smelter")
        screen._cursor_x = SURFACE_SIZE // 2 + 4
        screen._cursor_y = SURFACE_SIZE // 2 + 4
        await pilot.press("enter")
        await pilot.pause()
        assert screen._mode == "view"
        await pilot.press("escape")
        await pilot.pause()


@pytest.mark.asyncio
async def test_planet_surface_transfer_with_spaceport():
    from ui import PlanetSurfaceScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        colony = _colony()
        colony.place_building("spaceport", SURFACE_SIZE // 2 + 3, SURFACE_SIZE // 2 + 3)
        colony.storage["ore"] = 10
        screen = PlanetSurfaceScreen(colony, SURFACE_SIZE // 2, SURFACE_SIZE // 2)
        await _push(pilot, app, screen)
        await pilot.press("S")
        await pilot.pause()
        await pilot.pause()
        # появился input для передачи (монтируется в subtree экрана)
        inp = app.screen.query("#transfer-input")
        assert len(inp) > 0, f"transfer input not found: {[w.id for w in app.screen.query('*')]}"
        # ввод команды (обработчик назначен инстансно — вызываем напрямую)
        inp[0].on_input_submitted(SimpleNamespace(value="to_ship ore 5"))
        await pilot.pause()
        assert colony.storage.get("ore", 0) == 5
        assert app.ctrl.ship.cargo.has("ore") >= 5
        await pilot.press("escape")
        await pilot.pause()
