"""Coverage tests — galaxy_map round 2: interaction actions (2026-08-03)."""

import pytest

from galaxy_map import GalaxyMapApp, GameState
from config import TILE_PLANET, TILE_ASTEROIDS, TILE_WORMHOLE, TILE_EMPTY
from models import TraderShip, PirateShip


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


async def _press_action(pilot, app, action_id):
    """Открывает меню E и нажимает действие с заданным id."""
    await pilot.press("0")
    await pilot.pause()
    acts = app.ctrl.interaction_actions
    idx = next(i for i, a in enumerate(acts) if a[2] == action_id)
    await pilot.press(str(idx + 1))
    await pilot.pause()
    await pilot.pause()


def _set_tile(app, pos, tile, obj):
    g = app.ctrl.galaxy
    g.tiles[pos[1]][pos[0]] = tile
    g.objects[pos] = obj


# =============================================================================
# Interaction actions on objects
# =============================================================================

@pytest.mark.asyncio
async def test_interaction_scan_planet():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        pos = next(iter(app.ctrl.galaxy.planet_types))
        _set_tile(app, pos, TILE_PLANET, "planet")
        app.ctrl.player_x, app.ctrl.player_y = pos
        await _press_action(pilot, app, "scan_planet")
        # сканирование логирует результат и остаётся на карте
        assert app.ctrl.state == GameState.PLAYING
        assert len(app.screen_stack) == 1


@pytest.mark.asyncio
async def test_interaction_land_on_planet():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        pos = next(iter(app.ctrl.galaxy.planet_types))
        _set_tile(app, pos, TILE_PLANET, "planet")
        app.ctrl.player_x, app.ctrl.player_y = pos
        await _press_action(pilot, app, "land")
        # «land» в меню E — случайные события высадки (_act_land), без экрана
        assert app.ctrl.state == GameState.PLAYING
        assert len(app.screen_stack) == 1


@pytest.mark.asyncio
async def test_interaction_mine_asteroids():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        g = app.ctrl.galaxy
        pos = (3, 3)
        _set_tile(app, pos, TILE_ASTEROIDS, "asteroids")
        app.ctrl.player_x, app.ctrl.player_y = pos
        await _press_action(pilot, app, "mine")
        # шахта вероятностная — главное без краша
        assert app.ctrl.state == GameState.PLAYING


@pytest.mark.asyncio
async def test_interaction_wormhole():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        g = app.ctrl.galaxy
        pos = (3, 3)
        g.wormholes = [pos, (10, 10)]
        _set_tile(app, pos, TILE_WORMHOLE, "wormhole")
        app.ctrl.player_x, app.ctrl.player_y = pos
        await _press_action(pilot, app, "wormhole")
        assert (app.ctrl.player_x, app.ctrl.player_y) != pos


@pytest.mark.asyncio
async def test_interaction_hail_trader():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        t = TraderShip(app.ctrl.player_x + 1, app.ctrl.player_y, [0])
        app.ctrl.galaxy.traders.append(t)
        await _press_action(pilot, app, "hail_npc")
        assert app.ctrl.state == GameState.PLAYING


@pytest.mark.asyncio
async def test_interaction_battle_pirate():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        p = PirateShip(app.ctrl.player_x + 1, app.ctrl.player_y)
        app.ctrl.galaxy.pirates.append(p)
        await _press_action(pilot, app, "battle_pirate")
        from battle import BattleScreen
        assert isinstance(app.screen, BattleScreen)
        await pilot.press("escape")
        await pilot.pause()


# =============================================================================
# Quick expedition from start screen
# =============================================================================

@pytest.mark.asyncio
async def test_start_screen_quick_expedition():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("3")  # quick expedition
        await pilot.pause()
        await pilot.pause()
        from expedition import ExpeditionScreen
        assert isinstance(app.screen, ExpeditionScreen)
        await pilot.press("escape")  # выход из экспедиции
        await pilot.pause()
        await pilot.pause()


# =============================================================================
# Pause / game-over rendering
# =============================================================================

@pytest.mark.asyncio
async def test_game_over_screen_renders():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        app.ctrl.state = GameState.GAME_OVER
        app.ctrl.death_cause = "Test death"
        app.update_map()
        txt = app.ctrl.render_game_over_screen(app.ctrl.build_map_lines())
        assert "┏" in txt  # рамка оверлея поверх карты
        # Q на экране game over закрывает приложение
        await pilot.press("q")
        await pilot.pause()
