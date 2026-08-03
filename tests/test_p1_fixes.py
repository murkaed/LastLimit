"""Tests for P1 fixes from the audit (2026-08-03).

Covers:
- traders stuck at stations (route never advances)
- expedition crates/terminals unreachable
- colony buildings permanently deactivated
- Input auto-focus breaking screen keyboard handling
- ActionMenu dispatch AttributeError (app._act_*) and duplicate hotkeys
- station repair capped at 100 instead of ship max hull
- mine/water purifier double production "from thin air"
"""

import pytest

from galaxy_map import GalaxyMapApp, GameState
from game_controller import GameController
from colony import ColonyManager, ResourceNode


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
# P1-8: traders must advance their routes (not get stuck at stations)
# =============================================================================

def test_traders_advance_routes():
    from models import Galaxy
    advanced = False
    for seed in (1, 42, 123):
        g = Galaxy(seed=seed)
        for _ in range(500):
            g.step_npc(0, 0, None, [])
        if any(t.route_index > 0 for t in g.traders):
            advanced = True
            break
    # Раньше route_index никогда не менялся: торговцы застревали у станции
    assert advanced


# =============================================================================
# P1-9: crates must be lootable by walking onto them
# =============================================================================

def test_crate_tile_is_lootable():
    from expedition import ExpeditionMap, ExpeditionController
    from models import CrewMember
    m = ExpeditionMap(20, 15, site_type="station")
    ctrl = ExpeditionController(CrewMember("T", "Pilot"), m)
    # Ensure a clean path and no nearby enemies
    m.grid[5][5] = "floor"
    m.grid[5][6] = "crate"  # get_tile(x, y) → grid[y][x]
    m.crates[(6, 5)] = "repair_kit"
    m.enemies = [e for e in m.enemies if max(abs(e.x - 5), abs(e.y - 5)) > 2]
    ctrl.px, ctrl.py = 5, 5
    ctrl.crew.ap = ctrl.crew.max_ap
    ctrl.move(1, 0)  # идём вправо на (6,5) — на ящик
    assert ctrl.crew.inventory.get("repair_kit", 0) == 1
    assert m.grid[5][6] == "floor"
    assert (6, 5) not in m.crates


# =============================================================================
# P1-10: colony buildings must reactivate when conditions recover
# =============================================================================

def test_building_reactivates_after_worker_shortage():
    from colony import SURFACE_SIZE
    col = ColonyManager("C", "temperate")
    col.surface = [["plain"] * SURFACE_SIZE for _ in range(SURFACE_SIZE)]
    col.storage = {"metal": 50, "electronics": 50, "silicon": 50, "ice": 50, "ore": 50, "fuel_cell": 0}
    col.colonists = 0
    assert col.place_building("smelter", 5, 5)
    sm = next(b for b in col.buildings if b.building_id == "smelter")
    col.tick()
    assert sm.active is False
    # Условия восстановились — здание должно снова заработать
    col.colonists = 10
    col.storage["ore"] = 20
    col.tick()
    assert sm.active is True


# =============================================================================
# P1-11: no Input auto-focus — screen hotkeys must work
# =============================================================================

@pytest.mark.asyncio
async def test_cargo_screen_hotkey_works_without_input_focus():
    from ui import CargoScreen
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        screen = CargoScreen()
        app.push_screen(screen)
        await pilot.pause()
        await pilot.pause()
        assert app.screen is screen
        # Раньше "2" уходил в авто-сфокусированный Input, экранный on_key не срабатывал.
        # fkeys: 1=all, 2=raw, 3=refined, 4=advanced, 5=special, 6=module
        await pilot.press("2")
        await pilot.pause()
        assert screen._filter == "raw"


# =============================================================================
# P1-12: ActionMenu dispatch must route through GameController
# =============================================================================

@pytest.mark.asyncio
async def test_action_menu_dispatch_refuel_repair_land():
    """Раньше — AttributeError: у GalaxyMapApp нет _act_refuel/_act_repair/_try_landing."""
    from config import TILE_EMPTY
    from ui import ActionMenu
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        # Каждое действие на свежем экземпляре меню: _dispatch сам закрывает меню
        for action in ("refuel", "repair", "land"):
            menu = ActionMenu()
            app.push_screen(menu)
            await pilot.pause()
            await pilot.pause()
            if action == "land":
                # детерминированно: игрок на пустом тайле — try_landing вернёт None
                px, py = app.ctrl.player_x, app.ctrl.player_y
                app.ctrl.galaxy.tiles[py][px] = TILE_EMPTY
            menu._dispatch(action)  # не должно быть AttributeError
            await pilot.pause()
        # После трёх dismiss'ов на стеке снова только главный экран
        assert len(app.screen_stack) == 1


# =============================================================================
# P1-13: station repair must cap at the ship's real max hull
# =============================================================================

def test_station_repair_caps_at_ship_max_hull():
    ctrl = GameController()
    ctrl.ship.max_hull = 160  # фрегат-уровень
    ctrl.ship.hull = 100
    ctrl.ship.credits = 1000
    ctrl._act_repair()
    # Раньше кап был хардкод 100 — ремонт не работал выше сотни
    assert ctrl.ship.hull == 115
    assert ctrl.ship.credits == 970


# =============================================================================
# P1-14: ActionMenu sections must not share hotkeys
# =============================================================================

@pytest.mark.asyncio
async def test_action_menu_sections_have_unique_keys():
    from ui import ActionMenu
    from models import TraderShip
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await _start_game(pilot, app)
        ctrl = app.ctrl
        st = next((s for s in ctrl.galaxy.stations if s.missions), None)
        assert st is not None
        ctrl.player_x, ctrl.player_y = st.x, st.y
        # Трейдер рядом — добавляет trader_talk в раздел «Взаимодействие»
        ctrl.galaxy.traders.append(TraderShip(st.x + 1, st.y, [0]))
        menu = ActionMenu()
        app.push_screen(menu)
        await pilot.pause()
        keys = [k for _, acts in menu._sections for k, _, _ in acts]
        assert len(keys) == len(set(keys)), f"duplicate hotkeys: {keys}"


# =============================================================================
# P1-15: mine / water purifier must not produce "from thin air"
# =============================================================================

def _colony_with_power(ptype="temperate"):
    from colony import SURFACE_SIZE
    col = ColonyManager("C", ptype)
    col.surface = [["plain"] * SURFACE_SIZE for _ in range(SURFACE_SIZE)]
    col.storage = {"metal": 50, "electronics": 50, "silicon": 50, "ice": 0, "ore": 0, "fuel_cell": 0}
    col.colonists = 20
    col.happiness = 100
    col.max_storage = 1000  # чтобы тестовые запасы не превышали лимит
    col.place_building("power_plant_solar", 9, 9)
    return col


def test_water_purifier_on_dry_planet_produces_nothing():
    col = _colony_with_power("desert")
    col.place_building("water_purifier", 5, 5)
    col.tick()
    # Раньше общий output-путь давал 3 льда даже без воды
    assert col.storage.get("ice", 0) == 0


def test_mine_without_vein_produces_nothing():
    col = _colony_with_power("temperate")
    col.resource_nodes = []
    col.place_building("mine", 5, 5)
    events = col.tick()
    # Раньше общий output-путь давал 5 руды «из воздуха»
    assert col.storage.get("ore", 0) == 0
    assert any("no ore vein" in e for e in events)


def test_mine_with_vein_produces_only_vein_amount():
    col = _colony_with_power("temperate")
    col.resource_nodes = [ResourceNode("ore", 100, 6, 6)]
    col.place_building("mine", 5, 5)
    col.tick()
    # Уровень-1 шахта: 3 + 2*1 = 5 руды из жилы.
    # Раньше: 5 (общий путь) + 5 (жила) = 10.
    assert col.storage.get("ore", 0) == 5
