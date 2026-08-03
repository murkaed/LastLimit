"""UI coverage batch 4 — LandingPrep, Scan, ActionMenu, Settings (2026-08-03)."""

from types import SimpleNamespace

import pytest

from galaxy_map import GalaxyMapApp, GameState
from models import CrewMember, TraderShip, PirateShip


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
# LandingPrepScreen
# =============================================================================

@pytest.mark.asyncio
async def test_landing_prep_launch():
    from ui import LandingPrepScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        # свободный член экипажа
        app.ctrl.ship.crew_members.append(CrewMember("Scout1", "Pilot"))
        screen = LandingPrepScreen(site_type="planet", site_name="TestPlanet")
        await _push(pilot, app, screen)
        await pilot.press("down")
        await pilot.pause()
        await pilot.press("up")
        await pilot.pause()
        await pilot.press("enter")  # запуск экспедиции
        await pilot.pause()
        await pilot.pause()
        from expedition import ExpeditionScreen
        assert isinstance(app.screen, ExpeditionScreen)
        await pilot.press("escape")  # выход из экспедиции
        await pilot.pause()
        await pilot.pause()


# =============================================================================
# ScanScreen
# =============================================================================

@pytest.mark.asyncio
async def test_scan_screen():
    from ui import ScanScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        p = PirateShip(app.ctrl.player_x + 3, app.ctrl.player_y)
        app.ctrl.galaxy.pirates.append(p)
        screen = ScanScreen()
        await _push(pilot, app, screen)
        assert screen._mode == "select"
        await pilot.press("down")
        await pilot.pause()
        await pilot.press("up")
        await pilot.pause()
        await pilot.press("enter")  # активное сканирование
        await pilot.pause()
        assert screen._mode == "result"
        assert screen._result is not None
        await pilot.press("escape")  # назад к целям
        await pilot.pause()
        assert screen._mode == "select"
        await pilot.press("escape")  # закрыть
        await pilot.pause()


# =============================================================================
# ActionMenu
# =============================================================================

@pytest.mark.asyncio
async def test_action_menu_navigation():
    from ui import ActionMenu, SettingsScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        screen = ActionMenu()
        await _push(pilot, app, screen)
        assert len(screen._sections) >= 2
        await pilot.press("down")
        await pilot.pause()
        await pilot.press("up")
        await pilot.pause()
        await pilot.press("g")  # настройки
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)
        await pilot.press("escape")
        await pilot.pause()


@pytest.mark.asyncio
async def test_action_menu_trader_talk():
    from ui import ActionMenu
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        t = TraderShip(app.ctrl.player_x + 1, app.ctrl.player_y, [0])
        app.ctrl.galaxy.traders.append(t)
        screen = ActionMenu()
        await _push(pilot, app, screen)
        screen._dispatch("trader_talk")
        await pilot.pause()
        rendered = app.ctrl.logger.render_plain(n=10)
        assert "✉" in rendered  # трейдер ответил
        # миссия от трейдера могла быть добавлена


@pytest.mark.asyncio
async def test_action_menu_attack_npc():
    from ui import ActionMenu
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        p = PirateShip(app.ctrl.player_x + 1, app.ctrl.player_y)
        app.ctrl.galaxy.pirates.append(p)
        screen = ActionMenu()
        await _push(pilot, app, screen)
        screen._dispatch("attack_npc")
        await pilot.pause()
        await pilot.pause()
        from battle import BattleScreen
        assert isinstance(app.screen, BattleScreen)
        await pilot.press("escape")
        await pilot.pause()
        await pilot.pause()


# =============================================================================
# SettingsScreen
# =============================================================================

@pytest.mark.asyncio
async def test_settings_screen():
    from ui import SettingsScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        screen = SettingsScreen()
        await _push(pilot, app, screen)
        lang_before = screen._settings["lang"]
        await pilot.press("enter")  # переключить язык
        await pilot.pause()
        assert screen._settings["lang"] != lang_before
        # настройка клавиш (ожидание)
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.pause()
        screen._waiting = "move_up"  # режим ожидания клавиши
        await pilot.press("w")
        await pilot.pause()
        assert screen._settings["keys"]["move_up"] == "w"
        # change через ввод
        screen.on_input_submitted(_ev("change move_up x"))
        await pilot.pause()
        assert screen._settings["keys"]["move_up"] == "x"
        # reset
        screen._selected = len(screen._opts()) - 1  # последняя опция — reset
        await pilot.press("enter")
        await pilot.pause()
        # сохранение и закрытие
        screen.on_input_submitted(_ev("close"))
        await pilot.pause()
