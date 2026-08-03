"""Coverage tests — galaxy_map round 4: property shims, pause keys, console (2026-08-03)."""

import pytest

from galaxy_map import GalaxyMapApp, GameState
from config import TILE_EMPTY


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


# =============================================================================
# Property shims
# =============================================================================

@pytest.mark.asyncio
async def test_property_shims():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        app.state = GameState.INSPECTING
        assert app.state == GameState.INSPECTING
        app.player_x = 5
        app.player_y = 6
        assert app.ctrl.player_x == 5 and app.ctrl.player_y == 6
        app.cursor_x = 3
        app.cursor_y = 4
        assert app.cursor_x == 3 and app.cursor_y == 4
        app._pending_battle = None
        app.world_frozen = True
        assert app.world_frozen is True
        app._prev_state = GameState.PLAYING
        app._dismiss_handled_escape = True
        app.race_selected = True
        app._show_race_select = True
        assert app.race_selected is True
        assert app._show_race_select is True
        acts = app.ctrl.get_available_interactions()
        app.interaction_actions = acts
        assert app._saved_interaction_actions is None
        assert len(app.interaction_actions) >= 1


# =============================================================================
# Race select: back (0)
# =============================================================================

@pytest.mark.asyncio
async def test_race_select_back_to_start():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")  # new game → mode
        await pilot.pause()
        await pilot.press("1")  # free play → race select
        await pilot.pause()
        assert app.ctrl.state == GameState.RACE_SELECT
        await pilot.press("0")  # назад к стартовому экрану
        await pilot.pause()
        assert app.ctrl.state == GameState.START_SCREEN


# =============================================================================
# Pause keys: restart (r) / quit (q)
# =============================================================================

@pytest.mark.asyncio
async def test_pause_restart_and_quit():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("escape")
        await pilot.pause()
        assert app.ctrl.state == GameState.PAUSED
        await pilot.press("r")  # рестарт
        await pilot.pause()
        assert app.ctrl.state in (GameState.START_SCREEN, GameState.RACE_SELECT)


@pytest.mark.asyncio
async def test_pause_quit():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("escape")
        await pilot.pause()
        await pilot.press("q")
        await pilot.pause()


# =============================================================================
# 'c' on non-planet tile
# =============================================================================

@pytest.mark.asyncio
async def test_c_not_on_planet():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        g = app.ctrl.galaxy
        px, py = app.ctrl.player_x, app.ctrl.player_y
        g.tiles[py][px] = TILE_EMPTY
        g.objects.pop((px, py), None)
        await pilot.press("c")
        await pilot.pause()
        rendered = app.ctrl.logger.render_plain(n=5)
        assert "Not on a planet" in rendered or "не на планете" in rendered


# =============================================================================
# Console: save / exit through app.process_command
# =============================================================================

@pytest.mark.asyncio
async def test_console_save_and_exit(tmp_path, monkeypatch):
    import galaxy_map as gm
    monkeypatch.setattr(gm, "SAVE_FILE", str(tmp_path / "savegame.dat"))
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("`")  # консоль
        await pilot.pause()
        await pilot.pause()
        from ui import CommandScreen
        assert isinstance(app.screen, CommandScreen)
        # команда save → app.process_command → _do_save → файл
        app.screen.on_input_submitted(type("E", (), {"value": "save"})())
        await pilot.pause()
        assert (tmp_path / "savegame.dat").exists()


# =============================================================================
# Save failure path
# =============================================================================

@pytest.mark.asyncio
async def test_save_failure_logs_error(tmp_path, monkeypatch):
    import galaxy_map as gm
    monkeypatch.setattr(gm, "SAVE_FILE", str(tmp_path / "ro" / "save.dat"))
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("f6")
        await pilot.pause()
        rendered = app.ctrl.logger.render_plain(n=5)
        assert "Save failed" in rendered or "Ошибка" in rendered


# =============================================================================
# Inspect cursor: down / left
# =============================================================================

@pytest.mark.asyncio
async def test_inspect_cursor_down_left():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("i")
        await pilot.pause()
        assert app.ctrl.state == GameState.INSPECTING
        await pilot.press("s")
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        assert app.ctrl.state == GameState.INSPECTING
