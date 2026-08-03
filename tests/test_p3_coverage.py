"""P3 coverage tests — remaining audit gaps (2026-08-03).

Covers: political & random events, enemy AI branches (repair/flee/attack/ram),
repair_module + console repair command, map rendering, radiation shield,
turn order.
"""

import random
import pytest

from battle import BattleController
from game_controller import GameController, GameState
from models import Galaxy, PlayerShip, PirateShip, create_random_ship
from config import TILE_EMPTY, TILE_SHIP, TILE_STAR


# =============================================================================
# Political events (_check_political_events)
# =============================================================================

def test_political_events_gated_by_timer():
    ctrl = GameController()
    ctrl._politics_timer = 0
    n_news = len(ctrl.galaxy.news)
    for _ in range(20):
        ctrl._check_political_events([])
    assert len(ctrl.galaxy.news) == n_news  # таймер не дозрел — событий нет


def test_political_event_crusade_changes_diplomacy():
    ctrl = GameController()
    ctrl._politics_timer = 100
    random.seed(2)  # crusade
    ctrl._check_political_events([])
    headlines = " ".join(e.headline for e in ctrl.galaxy.news).lower()
    assert "crusade" in headlines
    # Империум объявляет войну Хаосу
    if "chaos_cult" in ctrl.galaxy.diplomacy.get("imperium", {}):
        assert ctrl.galaxy.diplomacy["imperium"]["chaos_cult"] == "war"


def test_political_event_invasion_spawns_pirates():
    ctrl = GameController()
    ctrl._politics_timer = 100
    n_pirates = len(ctrl.galaxy.pirates)
    POL = ["crusade", "invasion", "schism", "plague", "scandal", "treaty"]
    # Пробуем те же вызовы RNG, что и в функции (randint таймера, затем choice)
    for seed in range(1, 300):
        random.seed(seed)
        random.randint(30, 60)
        if random.choice(POL) == "invasion":
            random.seed(seed)
            ctrl._check_political_events([])
            break
    assert len(ctrl.galaxy.pirates) > n_pirates


# =============================================================================
# Random events (_check_random_events)
# =============================================================================

def test_random_event_supernova_damages_nearby_player():
    ctrl = GameController()
    ctrl.galaxy.black_holes = [(10, 10)]  # единственная ЧД — choice детерминирован
    ctrl.ship.shield_hp = 0
    ctrl.player_x, ctrl.player_y = 10, 10
    random.seed(139)  # 3% шанс + supernova
    ctrl._check_random_events([])
    assert ctrl.ship.hull == 90  # -10 от взрыва


def test_random_event_crisis_sets_global_ticks():
    ctrl = GameController()
    EVS = ["caravan", "raid", "supernova", "crisis"]
    # seed, где событие = crisis (3% шанс + choice)
    for seed in range(1, 300):
        random.seed(seed)
        if random.random() <= 0.03 and random.choice(EVS) == "crisis":
            random.seed(seed)
            ctrl._check_random_events([])
            break
    assert ctrl.galaxy.global_crisis_ticks == 10


# =============================================================================
# Enemy AI branches (_do_enemy_turn)
# =============================================================================

def test_enemy_repairs_at_low_hull():
    p = create_random_ship(is_player=True)
    e = PirateShip(1, 1)
    bc = BattleController(p, e, app=None)
    bc.enemy_items = ["repair_kit"]
    bc.enemy.shield_hp = 0
    bc.enemy.hull = 10  # < 30% от 40
    bc._do_enemy_turn()
    assert bc.enemy.hull >= 30  # +20 от ремкомплекта
    assert bc.enemy_items == []


def test_enemy_flees_at_critical_hull():
    p = create_random_ship(is_player=True)
    e = PirateShip(1, 1)
    bc = BattleController(p, e, app=None)
    bc.enemy_items = []
    bc.enemy.hull = 5  # < 20%
    random.seed(4)  # первый random < 0.4 и второй < 0.5 — побег удался
    bc._do_enemy_turn()
    assert bc.over is True
    assert bc.victory is True


def test_enemy_attacks_with_weapon_and_deals_damage():
    dealt = False
    for seed in range(10, 25):
        p = create_random_ship(is_player=True)
        e = PirateShip(1, 1)
        bc = BattleController(p, e, app=None)
        p.hull = 100
        p.shield_hp = 0
        random.seed(seed)
        bc._do_enemy_turn()
        # Урон идёт либо по корпусу, либо по модулю отсека
        if p.hull < 100 or any(
            m.durability < m.max_durability
            for c in p.compartments.values() for m in c["modules"]
        ):
            dealt = True
            break
    assert dealt  # с оружием враг рано или поздно попадает


def test_enemy_rams_without_weapons():
    p = create_random_ship(is_player=True)
    e = PirateShip(1, 1)
    bc = BattleController(p, e, app=None)
    bc.enemy_comps["weapon"]["modules"] = []
    p.hull = 100
    p.shield_hp = 0
    bc._do_enemy_turn()
    assert p.hull <= 90  # таран 10 (или 5 в защите)


# =============================================================================
# repair_module + console repair command
# =============================================================================

def test_repair_module_direct():
    s = PlayerShip("T", 100)
    m = s.compartments["engine"]["modules"][0]
    m.durability = 5
    msg, cost = s.repair_module("engine")
    assert m.durability > 5
    assert cost == 3  # 2 металла + 1 электроника
    # Чиним до максимума, затем чинить нечего
    while m.durability < m.max_durability:
        msg2, cost2 = s.repair_module("engine")
        assert cost2 == 3
    msg3, cost3 = s.repair_module("engine")
    assert cost3 == 0


def test_console_repair_command_fixes_module():
    ctrl = GameController()
    ctrl.process_command("give metal 10")
    ctrl.process_command("give electronics 10")
    m = ctrl.ship.compartments["engine"]["modules"][0]
    m.durability = 5
    before = m.durability
    ctrl.process_command("repair engine")
    assert m.durability > before
    assert ctrl.ship.cargo.has("metal") == 8
    assert ctrl.ship.cargo.has("electronics") == 9


def test_console_repair_requires_resources():
    ctrl = GameController()
    ctrl.ship.cargo.items.clear()  # в трюме нет металла/электроники
    m = ctrl.ship.compartments["engine"]["modules"][0]
    m.durability = 5
    before = m.durability
    ctrl.process_command("repair engine")
    assert m.durability == before


# =============================================================================
# Map rendering, radiation shield, turn order
# =============================================================================

def test_get_map_display_renders_map():
    ctrl = GameController()
    ctrl.state = GameState.PLAYING
    txt = ctrl.get_map_display()
    lines = txt.split("\n")
    assert len(lines) == ctrl.galaxy.height
    assert len(lines[0]) == ctrl.galaxy.width
    assert TILE_SHIP in txt  # маркер корабля на карте


def test_radiation_shield_blocks_star_damage():
    g = Galaxy(seed=1)
    g.black_holes = []  # чтобы гравитация не мешала
    px, py = 10, 10
    g.tiles[py][px] = TILE_EMPTY
    g.tiles[py - 1][px] = TILE_STAR  # звезда рядом
    ship = PlayerShip("T", 100)
    ship.shield_hp = 0
    ship.radiation_shield = True
    g.tick(px, py, ship)
    assert ship.hull == 100


def test_compute_turn_order_sets_order_and_logs():
    p = create_random_ship(is_player=True)
    e = PirateShip(1, 1)
    bc = BattleController(p, e, app=None)
    random.seed(7)
    bc._compute_turn_order()
    assert bc.turn_order in ("player", "enemy")
    assert len(bc.log) >= 1
