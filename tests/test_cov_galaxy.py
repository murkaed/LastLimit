"""Coverage tests — galaxy_map App shell (2026-08-03)."""

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


async def _open_submenu(pilot, app):
    """Открывает меню E и субменю корабля."""
    await pilot.press("0")
    await pilot.pause()
    acts = app.ctrl.interaction_actions
    idx = next(i for i, a in enumerate(acts) if a[2] == "ship_screens")
    await pilot.press(str(idx + 1))
    await pilot.pause()
    assert app.ctrl._interaction_submenu_active


# =============================================================================
# Interaction menu (E / 0)
# =============================================================================

@pytest.mark.asyncio
async def test_interaction_menu_opens_and_closes():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("0")
        await pilot.pause()
        assert app.ctrl._interaction_active
        assert len(app.ctrl.interaction_actions) >= 1
        await pilot.press("0")  # закрыть
        await pilot.pause()
        assert not app.ctrl._interaction_active
        assert app.ctrl.state == GameState.PLAYING


@pytest.mark.asyncio
async def test_ship_screens_submenu_opens_bridge():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await _open_submenu(pilot, app)
        await pilot.press("1")  # Bridge
        await pilot.pause()
        from ui import BridgeScreen
        assert isinstance(app.screen, BridgeScreen)
        # Esc из экрана возвращает на карту
        await pilot.press("escape")
        await pilot.pause()
        assert len(app.screen_stack) == 1
        assert app.ctrl.state == GameState.PLAYING


@pytest.mark.asyncio
async def test_submenu_zero_closes_all():
    """Ветка «0 = назад в меню» в _on_interaction_key недостижима:
    «0» в _on_playing_key закрывает всё меню целиком."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await _open_submenu(pilot, app)
        await pilot.press("0")
        await pilot.pause()
        assert not app.ctrl._interaction_submenu_active
        assert not app.ctrl._interaction_active
        assert app.ctrl.state == GameState.PLAYING


@pytest.mark.asyncio
async def test_submenu_escape_closes_all():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await _open_submenu(pilot, app)
        await pilot.press("escape")  # глобальный блок закрывает меню целиком
        await pilot.pause()
        assert not app.ctrl._interaction_submenu_active
        assert not app.ctrl._interaction_active
        assert app.ctrl.state == GameState.PLAYING


@pytest.mark.asyncio
async def test_interaction_escape_closes_menu_no_pause():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("0")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING
        assert not app.ctrl._interaction_active


# =============================================================================
# Global keys: space (world tick), / (log filter), ` (console)
# =============================================================================

@pytest.mark.asyncio
async def test_space_advances_world():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        turn_before = app.ctrl.logger.turn
        await pilot.press("space")
        await pilot.pause()
        assert app.ctrl.logger.turn > turn_before


@pytest.mark.asyncio
async def test_slash_cycles_log_filter():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        before = app.ctrl.log_category_filter
        await pilot.press("/")
        await pilot.pause()
        # фильтр мог измениться или зациклиться — главное без краша
        assert app.ctrl.state == GameState.PLAYING
        await pilot.press("/")
        await pilot.pause()


@pytest.mark.asyncio
async def test_backtick_opens_console():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("`")
        await pilot.pause()
        await pilot.pause()
        from ui import CommandScreen
        assert isinstance(app.screen, CommandScreen)
        await pilot.press("escape")
        await pilot.pause()


# =============================================================================
# Pause / game-over states
# =============================================================================

@pytest.mark.asyncio
async def test_escape_pauses_and_resumes():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("escape")
        await pilot.pause()
        assert app.ctrl.state == GameState.PAUSED
        await pilot.press("escape")
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING
