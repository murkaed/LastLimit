"""P2 coverage tests — mechanics previously untested (audit 2026-08-03).

Covers: console commands, NPC world AI (step_npc), wormholes, colonies,
race mechanics (voidborn/machine_cult), save/load round-trip, t() safety.
"""

import pytest
from types import SimpleNamespace

from game_controller import GameController
from models import Galaxy, PlayerShip, PirateShip, TraderShip
from config import TILE_BLACK_HOLE, TILE_EMPTY


# =============================================================================
# Console commands (valid flows)
# =============================================================================

def test_console_give_take():
    ctrl = GameController()
    ctrl.process_command("give metal 5")
    assert ctrl.ship.cargo.has("metal") == 5
    ctrl.process_command("take metal 3")
    assert ctrl.ship.cargo.has("metal") == 2


def test_console_set_hull_and_power():
    ctrl = GameController()
    ctrl.process_command("set hull 50")
    assert ctrl.ship.hull == 50
    ctrl.process_command("power reactor 8")
    assert ctrl.ship.compartments["reactor"]["power"] == 8
    ctrl.process_command("power reactor 99")  # клампится в 10
    assert ctrl.ship.compartments["reactor"]["power"] == 10


def test_console_cargo_jettison():
    ctrl = GameController()
    ctrl.process_command("give metal 5")
    ctrl.process_command("cargo jettison metal 2")
    assert ctrl.ship.cargo.has("metal") == 3


def test_console_refuel():
    ctrl = GameController()
    ctrl.ship.fuel = 30
    ctrl.process_command("refuel")
    assert ctrl.ship.fuel == 100


# =============================================================================
# NPC world AI (step_npc)
# =============================================================================

def test_pirate_adjacent_to_player_starts_battle():
    g = Galaxy(seed=1)
    g.pirates = [PirateShip(5, 5)]
    g.traders = []
    out = []
    g.step_npc(6, 5, None, out)  # игрок рядом с пиратом
    assert any(m.startswith("__BATTLE__") for m in out)


def test_pirate_attacks_and_steals_from_trader():
    g = Galaxy(seed=1)
    g.pirates = [PirateShip(5, 5)]
    g.traders = [TraderShip(6, 5, [0])]
    t = g.traders[0]
    t.cargo.add("metal", 5)
    before = t.cargo.has("metal")
    out = []
    for _ in range(50):  # пират догоняет торговца
        g.step_npc(10, 10, None, out)
        if any("steals" in m for m in out):
            break
    assert any("steals" in m for m in out), f"no theft in: {out}"
    assert t.cargo.has("metal") < before


def test_trader_moves_toward_route():
    g = Galaxy(seed=1)
    t = g.traders[0]
    g.pirates = []
    start = (t.x, t.y)
    g.step_npc(0, 0, None, [])
    assert (t.x, t.y) != start or t.route_index > 0


# =============================================================================
# Wormholes
# =============================================================================

def test_wormhole_teleports_between_two():
    ctrl = GameController()
    ctrl.galaxy.wormholes = [(10, 10), (20, 20)]
    ctrl.player_x, ctrl.player_y = 5, 5
    ctrl._act_wormhole()
    assert (ctrl.player_x, ctrl.player_y) in [(10, 10), (20, 20)]
    assert len(ctrl.galaxy.wormholes) == 2  # ни один не исчез


def test_wormhole_collapses_when_alone():
    ctrl = GameController()
    px, py = 10, 10
    ctrl.galaxy.wormholes = [(px, py)]
    ctrl.galaxy.tiles[py][px] = TILE_BLACK_HOLE  # любой тайл; важно наличие объекта
    ctrl.galaxy.objects[(px, py)] = "wormhole"
    ctrl.player_x, ctrl.player_y = px, py
    ctrl._act_wormhole()
    assert (px, py) not in ctrl.galaxy.wormholes


# =============================================================================
# Colonies
# =============================================================================

def test_found_colony_requires_starter():
    ctrl = GameController()
    px, py = next(iter(ctrl.galaxy.planet_types))
    ctrl.player_x, ctrl.player_y = px, py
    ctrl.found_colony()
    assert (px, py) not in ctrl.galaxy.colonies


def test_found_colony_creates_and_open_returns_screen():
    ctrl = GameController()
    px, py = next(iter(ctrl.galaxy.planet_types))
    ctrl.player_x, ctrl.player_y = px, py
    ctrl.ship.cargo.add("colony_starter", 1)
    ctrl.found_colony()
    assert (px, py) in ctrl.galaxy.colonies
    assert ctrl.ship.cargo.has("colony_starter") == 0  # комплект израсходован
    result = ctrl.open_colony()
    assert result is not None
    assert result[0] == "PlanetSurfaceScreen"


# =============================================================================
# Race mechanics (README promises)
# =============================================================================

def test_voidborn_hated_by_all_factions():
    s = PlayerShip("T", 100)
    s.apply_race_bonus("voidborn")
    assert all(v <= -10 for v in s.reputation.values())


def test_voidborn_immune_to_black_hole_gravity():
    g = Galaxy(seed=1)
    g.black_holes = [(10, 10)]
    g.tiles[10][10] = TILE_BLACK_HOLE
    px, py, evs, dead = g.tick(11, 10, SimpleNamespace(race="voidborn"))
    assert (px, py) == (11, 10)  # не притянут
    assert dead is False


def test_black_hole_pulls_and_kills_normal_race():
    g = Galaxy(seed=1)
    g.black_holes = [(10, 10)]
    g.tiles[10][10] = TILE_BLACK_HOLE
    px, py, evs, dead = g.tick(11, 10, SimpleNamespace(race="human"))
    assert (px, py) == (10, 10)
    assert dead is True


def test_machine_cult_auto_repairs():
    ctrl = GameController()
    ctrl.ship.race = "machine_cult"
    ctrl.ship.hull = ctrl.ship.max_hull - 10
    px, py = ctrl.player_x, ctrl.player_y
    w, h = ctrl.galaxy.width, ctrl.galaxy.height
    # Очищаем окрестность от звёзд, чтобы радиация не портила замер
    for y in range(py - 2, py + 3):
        for x in range(px - 2, px + 3):
            if 0 <= x < w and 0 <= y < h:
                ctrl.galaxy.tiles[y][x] = TILE_EMPTY
    before = ctrl.ship.hull
    ctrl.tick_world()
    assert ctrl.ship.hull == before + 2


def test_mutant_takes_half_radiation():
    g = Galaxy(seed=1)
    px, py = 10, 10
    g.tiles[py][px] = TILE_EMPTY
    g.tiles[py - 1][px] = TILE_BLACK_HOLE  # не звезда; ниже перезапишем
    from config import TILE_STAR
    g.tiles[py - 1][px] = TILE_STAR  # звезда рядом
    ship = PlayerShip("T", 100)
    ship.race = "mutant"
    ship.hull = 100
    ship.shield_hp = 0  # чтобы радиация била по корпусу, а не щитам
    px2, py2, evs, dead = g.tick(px, py, ship)
    # мутант получает 5 вместо 10
    assert ship.hull == 95, evs


# =============================================================================
# Save/load round-trip
# =============================================================================

def test_save_restore_preserves_ship_and_world():
    ctrl = GameController()
    ctrl.ship.cargo.add("metal", 7)
    ctrl.ship.hull = 77
    ctrl.ship.credits = 4321
    data = ctrl.save_state()
    ctrl2 = GameController()
    GameController.restore_from_state(ctrl2, data)
    assert ctrl2.ship.cargo.has("metal") == 7
    assert ctrl2.ship.hull == 77
    assert ctrl2.ship.credits == 4321
    assert ctrl2.player_x == ctrl.player_x
    assert ctrl2.player_y == ctrl.player_y
    assert ctrl2.galaxy.seed == ctrl.galaxy.seed


# =============================================================================
# t() format safety
# =============================================================================

def test_t_format_error_returns_marker_not_exception():
    from locales import t
    # Ключ ждёт {station}, а передан другой kwargs — не должно быть исключения
    result = t("log.docked", wrong="x")
    assert result.startswith("❌")
