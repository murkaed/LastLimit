"""Coverage tests — galaxy_map round 3: playing-key navigation (2026-08-03)."""

import pytest

from galaxy_map import GalaxyMapApp, GameState
from config import TILE_PLANET, TILE_EMPTY
from models import PirateShip


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


def _goto(app, pos):
    g = app.ctrl.galaxy
    g.tiles[pos[1]][pos[0]] = TILE_EMPTY
    app.ctrl.player_x, app.ctrl.player_y = pos


def _colonizable_planet(app):
    from colony import PLANET_TYPES
    for p, t in app.ctrl.galaxy.planet_types.items():
        if not PLANET_TYPES.get(t, {}).get("orbit_only"):
            return p
    return None


# =============================================================================
# Movement and inspect mode
# =============================================================================

@pytest.mark.asyncio
async def test_wasd_movement():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        px, py = app.ctrl.player_x, app.ctrl.player_y
        _goto(app, (px, py))
        for key in ("w", "a", "s", "d"):
            await pilot.press(key)
            await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING


@pytest.mark.asyncio
async def test_inspect_mode_cursor():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        px, py = app.ctrl.player_x, app.ctrl.player_y
        _goto(app, (px, py))
        await pilot.press("i")
        await pilot.pause()
        assert app.ctrl.state == GameState.INSPECTING
        cx0, cy0 = app.ctrl.cursor_x, app.ctrl.cursor_y
        await pilot.press("w")
        await pilot.pause()
        assert app.ctrl.cursor_y == max(0, cy0 - 1)
        await pilot.press("right")
        await pilot.pause()
        assert app.ctrl.cursor_x == min(79, cx0 + 1)
        # «i» входит в inspect без прямого выхода: escape → pause → playing
        await pilot.press("escape")
        await pilot.pause()
        assert app.ctrl.state == GameState.PAUSED
        await pilot.press("escape")
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING


# =============================================================================
# Playing keys: b (trade), l (land), c (colony), f (fight), F1-F4
# =============================================================================

@pytest.mark.asyncio
async def test_b_trade_at_station():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        st = app.ctrl.galaxy.stations[0]
        _goto(app, (st.x, st.y))
        await pilot.press("b")
        await pilot.pause()
        await pilot.pause()
        from ui import TradeScreen
        assert isinstance(app.screen, TradeScreen)
        await pilot.press("escape")
        await pilot.pause()


@pytest.mark.asyncio
async def test_l_landing_prep():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        pos = _colonizable_planet(app)
        if pos is None:
            return
        _goto(app, pos)
        app.ctrl.galaxy.tiles[pos[1]][pos[0]] = TILE_PLANET
        app.ctrl.galaxy.objects[pos] = "planet"
        await pilot.press("l")
        await pilot.pause()
        await pilot.pause()
        from ui import LandingPrepScreen
        assert isinstance(app.screen, LandingPrepScreen)
        # закрываем напрямую (dismiss через клавишу конфликтует с teardown)
        screen = app.screen
        screen.dismiss()
        await pilot.pause()
        await pilot.pause()


@pytest.mark.asyncio
async def test_c_colony_found_and_open():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        pos = _colonizable_planet(app)
        if pos is None:
            return
        _goto(app, pos)
        app.ctrl.galaxy.tiles[pos[1]][pos[0]] = TILE_PLANET
        app.ctrl.galaxy.objects[pos] = "planet"
        app.ctrl.ship.cargo.add("colony_starter", 1)
        await pilot.press("c")  # основать колонию
        await pilot.pause()
        assert pos in app.ctrl.galaxy.colonies
        await pilot.press("c")  # открыть колонию
        await pilot.pause()
        await pilot.pause()
        from ui import PlanetSurfaceScreen
        assert isinstance(app.screen, PlanetSurfaceScreen)
        await pilot.press("escape")
        await pilot.pause()


@pytest.mark.asyncio
async def test_f_battle_pirate_and_no_pirate():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        # без пирата — сообщение
        await pilot.press("f")
        await pilot.pause()
        rendered = app.ctrl.logger.render_plain(n=5)
        assert "No pirate" in rendered or "нет пиратов" in rendered
        # с пиратом рядом — бой
        p = PirateShip(app.ctrl.player_x + 1, app.ctrl.player_y)
        app.ctrl.galaxy.pirates.append(p)
        await pilot.press("f")
        await pilot.pause()
        await pilot.pause()
        from battle import BattleScreen
        assert isinstance(app.screen, BattleScreen)
        await pilot.press("escape")
        await pilot.pause()


@pytest.mark.asyncio
async def test_f1_f4_ship_screens():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        from ui import EngineeringScreen, TacticalScreen, CargoScreen
        await pilot.press("f2")
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, EngineeringScreen)
        await pilot.press("escape")
        await pilot.pause()
        await pilot.press("f3")
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, TacticalScreen)
        await pilot.press("escape")
        await pilot.pause()
        await pilot.press("f4")
        await pilot.pause()
        await pilot.pause()
        assert isinstance(app.screen, CargoScreen)
        await pilot.press("escape")
        await pilot.pause()


# =============================================================================
# Interaction menu — SCREEN_MAP dispatch (trade at station)
# =============================================================================

@pytest.mark.asyncio
async def test_menu_trade_opens_trade_screen():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        st = app.ctrl.galaxy.stations[0]
        _goto(app, (st.x, st.y))
        await pilot.press("0")
        await pilot.pause()
        acts = app.ctrl.interaction_actions
        idx = next(i for i, a in enumerate(acts) if a[2] == "trade")
        await pilot.press(str(idx + 1))
        await pilot.pause()
        await pilot.pause()
        from ui import TradeScreen
        assert isinstance(app.screen, TradeScreen)
        await pilot.press("escape")
        await pilot.pause()


# =============================================================================
# _do_move with pending battle
# =============================================================================

@pytest.mark.asyncio
async def test_move_triggers_pending_battle():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        p = PirateShip(1, 1)
        app.ctrl.galaxy.pirates.append(p)
        app.ctrl._pending_battle = p
        px, py = app.ctrl.player_x, app.ctrl.player_y
        _goto(app, (px, py))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if app.ctrl.galaxy.is_passable(px + dx, py + dy):
                await pilot.press("d" if dx == 1 else "a" if dx == -1 else "s" if dy == 1 else "w")
                await pilot.pause()
                await pilot.pause()
                from battle import BattleScreen
                assert isinstance(app.screen, BattleScreen)
                await pilot.press("escape")
                await pilot.pause()
                return
        pytest.skip("no passable neighbor")


# =============================================================================
# F7 load error paths
# =============================================================================

@pytest.mark.asyncio
async def test_f7_no_save_file(tmp_path, monkeypatch):
    import galaxy_map as gm
    monkeypatch.setattr(gm, "SAVE_FILE", str(tmp_path / "missing.dat"))
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("f7")
        await pilot.pause()
        rendered = app.ctrl.logger.render_plain(n=5)
        assert "No save file" in rendered or "нет сохранения" in rendered


@pytest.mark.asyncio
async def test_f7_corrupt_save(tmp_path, monkeypatch):
    import galaxy_map as gm
    f = tmp_path / "bad.dat"
    f.write_bytes(b"not a pickle")
    monkeypatch.setattr(gm, "SAVE_FILE", str(f))
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("f7")
        await pilot.pause()
        rendered = app.ctrl.logger.render_plain(n=5)
        assert "Load failed" in rendered or "Ошибка загрузки" in rendered


# =============================================================================
# Start screen: quick battle / race select
# =============================================================================

@pytest.mark.asyncio
async def test_start_screen_quick_battle():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("2")  # quick battle
        await pilot.pause()
        await pilot.pause()
        from battle import BattleScreen
        assert isinstance(app.screen, BattleScreen)
        await pilot.press("escape")
        await pilot.pause()
        await pilot.pause()


@pytest.mark.asyncio
async def test_race_select_keys_and_back():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")  # new game → mode
        await pilot.pause()
        await pilot.press("1")  # free play → race select
        await pilot.pause()
        assert app.ctrl.state == GameState.RACE_SELECT
        await pilot.press("2")  # mutant
        await pilot.pause()
        assert app.ctrl.ship.race == "mutant"
        await pilot.press("0")  # назад
        await pilot.pause()


@pytest.mark.asyncio
async def test_q_quits_playing():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        await pilot.press("q")
        await pilot.pause()
