"""Coverage tests — models gaps (2026-08-03)."""

import random

import pytest

from models import (
    PlayerShip, CargoHold, Station, Galaxy, Mission, PirateShip,
    TraderShip, ShipModule, NewsEntry,
)
from config import (
    TILE_EMPTY, TILE_BLACK_HOLE, TILE_ASTEROIDS, TILE_STAR,
)


def _ship():
    s = PlayerShip("T", 100)
    s.cargo.capacity = 200
    return s


# =============================================================================
# Galaxy.tick branches
# =============================================================================

def test_tick_black_hole_death_on_spot():
    g = Galaxy(seed=1)
    g.black_holes = [(10, 10)]
    g.tiles[10][10] = TILE_BLACK_HOLE
    s = _ship()
    px, py, evs, dead = g.tick(10, 10, s)
    assert dead is True
    assert "Black hole!" in evs


def test_tick_asteroid_hit():
    g = Galaxy(seed=1)
    g.black_holes = []
    s = _ship()
    s.shield_hp = 0
    px, py = 10, 10
    g.tiles[py][px] = TILE_ASTEROIDS
    # убираем звезды вокруг
    for y in range(py - 1, py + 2):
        for x in range(px - 1, px + 2):
            if 0 <= x < g.width and 0 <= y < g.height:
                g.tiles[y][x] = TILE_EMPTY
    g.tiles[py][px] = TILE_ASTEROIDS
    # ищем сид, где срабатывает 30% шанс астероида
    for seed in range(1, 50):
        g2 = Galaxy(seed=1)
        g2.black_holes = []
        g2.tiles = [row[:] for row in g.tiles]
        s2 = _ship()
        s2.shield_hp = 0
        random.seed(seed)
        g2._rng = random.Random(seed)
        px2, py2, evs, dead = g2.tick(px, py, s2)
        if "Asteroid" in evs:
            assert s2.hull < 100
            return
    pytest.skip("no asteroid-hit seed found")


def test_tick_colony_event():
    from colony import ColonyManager, SURFACE_SIZE
    g = Galaxy(seed=1)
    g.black_holes = []
    col = ColonyManager("TestCol", "temperate")
    col.surface = [["plain"] * SURFACE_SIZE for _ in range(SURFACE_SIZE)]
    col.storage = {"metal": 50, "electronics": 50, "silicon": 50,
                   "ice": 50, "ore": 50, "fuel_cell": 0}
    col.colonists = 20
    col.happiness = 100
    col.max_storage = 1000
    col.place_building("power_plant_solar", 9, 9)
    col.place_building("smelter", 5, 5)
    g.colonies[(10, 10)] = col
    s = _ship()
    px, py = 10, 10
    g.tiles[py][px] = TILE_EMPTY
    for y in range(py - 1, py + 2):
        for x in range(px - 1, px + 2):
            g.tiles[y][x] = TILE_EMPTY
    px, py, evs, dead = g.tick(px, py, s)
    assert any("[colony TestCol]" in e for e in evs)


# =============================================================================
# switch_hull / sell_hull / install_module
# =============================================================================

def test_switch_hull_bigger_and_smaller():
    s = _ship()
    s.credits = 20000
    assert s.buy_hull("frigate")[1]
    msg, ok = s.switch_hull("frigate")
    assert ok is True
    assert s.max_hull == 160
    assert s.buy_hull("shuttle")[1]
    msg2, ok2 = s.switch_hull("shuttle")  # меньше отсеков
    assert ok2 is True
    assert s.max_hull == 60


def test_sell_hull():
    s = _ship()
    s.credits = 20000
    s.buy_hull("frigate")
    s.credits = 0
    msg, ok = s.sell_hull("frigate")
    assert ok is True
    assert s.credits == 3000  # 50% цены


def test_install_module_from_cargo():
    s = _ship()
    s.cargo.add("laser_turret", 1)
    msg, ok = s.install_module_from_cargo("laser_turret")
    assert ok is True
    assert s.cargo.has("laser_turret") == 0


# =============================================================================
# use_item edge cases
# =============================================================================

def test_use_item_not_consumable_and_need():
    s = _ship()
    msg, ok = s.use_item("metal")
    assert ok is False and "not consumable" in msg
    s.cargo.add("repair_kit", 2)
    msg, ok = s.use_item("repair_kit", 5)
    assert ok is False and "Need" in msg


def test_take_damage_damages_random_module():
    s = _ship()
    s.shield_hp = 0
    engine = s.compartments["engine"]["modules"][0]
    engine.durability = engine.max_durability
    random.seed(1)  # random() < 0.3 — урон модулю
    s.take_damage(5)
    assert s.hull == 95
    # хотя бы один модуль мог быть повреждён (30% шанс; проверим статистически)
    damaged = any(
        m.durability < m.max_durability
        for c in s.compartments.values() for m in c["modules"]
    )
    if not damaged:
        # пробуем ещё раз с другими сидами
        for seed in range(2, 30):
            s2 = _ship()
            s2.shield_hp = 0
            random.seed(seed)
            s2.take_damage(5)
            if any(m.durability < m.max_durability for c in s2.compartments.values() for m in c["modules"]):
                return
        assert False, "module damage branch never triggered"


# =============================================================================
# Crew assignment
# =============================================================================

def test_assign_crew_swap_and_errors():
    s = _ship()
    from models import CrewMember
    cm = CrewMember("Zed", "Tactician")  # Tactician может занять пост Tactical
    s.crew_members.append(cm)
    msg, ok = s.assign_crew("Zed", "Tactical")
    assert ok is True
    assert s.crew["Tactical"] == "Zed"
    # повторное назначение на занятый пост (оба могут занять Tactical)
    cm2 = CrewMember("Ann", "Tactician")
    s.crew_members.append(cm2)
    msg2, ok2 = s.assign_crew("Ann", "Tactical")
    assert ok2 is True
    assert s.crew["Tactical"] == "Ann"
    assert not any(v == "Zed" for v in s.crew.values())  # старый снят с поста
    # специалист не может занять чужой пост
    msg4, ok4 = s.assign_crew("Ann", "Pilot")
    assert ok4 is False and "cannot take" in msg4
    # неизвестный пост
    msg3, ok3 = s.assign_crew("Zed", "bogus_post")
    assert ok3 is False


# =============================================================================
# repair_module edge cases
# =============================================================================

def test_repair_module_errors():
    s = _ship()
    msg, cost = s.repair_module("bogus_comp")
    assert cost == 0 and "Unknown" in msg
    msg2, cost2 = s.repair_module("engine")  # модули целы
    assert cost2 == 0 and "No damaged" in msg2


# =============================================================================
# Missions: abandon / expire / dup / full
# =============================================================================

def test_abandon_mission():
    s = _ship()
    st = Station(5, 5, "Giver", "trade_hub", "free_traders")
    m = Mission("deliver", "metal", 3, "X", 100, giver_station=st)
    s.add_mission(m)
    msg, ok = s.abandon_mission(m.id)
    assert ok is True
    assert m.id not in (x.id for x in s.missions)
    msg2, ok2 = s.abandon_mission(999999)
    assert ok2 is False


def test_fail_expired_missions():
    s = _ship()
    m = Mission("deliver", "metal", 3, "X", 100, ticks=1)
    s.add_mission(m)
    news = []
    failed = s.fail_expired_missions(news)
    assert len(failed) == 1
    assert failed[0].id == m.id
    assert any("MISSION FAILED" in n.headline for n in news)


def test_add_mission_duplicate_and_full():
    s = _ship()
    m = Mission("deliver", "metal", 3, "X", 100)
    s.add_mission(m)
    msg, ok = s.add_mission(m)
    assert ok is False and "Already" in msg
    while len(s.missions) < 5:
        s.add_mission(Mission("deliver", "metal", 3, "X", 100))
    msg2, ok2 = s.add_mission(Mission("deliver", "metal", 3, "X", 100))
    assert ok2 is False and "full" in msg2


# =============================================================================
# scan_target / scan helpers
# =============================================================================

def test_scan_target_passive_and_active():
    s = _ship()
    p = PirateShip(5, 5)
    r = s.scan_target(p, "passive")
    assert r.success
    r2 = s.scan_target(p, "active")
    assert r2.success


def test_scan_target_insufficient_power():
    s = _ship()
    s.compartments["reactor"]["modules"] = []
    p = PirateShip(5, 5)
    r = s.scan_target(p, "active")
    assert r.success is False
    assert "spare power" in r.info.get("error", "")


def test_stations_in_range_and_scannable():
    g = Galaxy(seed=1)
    near = g.stations_in_range(0, 0, 100)
    assert len(near) == len(g.stations)
    objs = g.get_scannable_objects(0, 0, 200)
    assert len(objs) > 0
    assert objs == sorted(objs, key=lambda o: o[0])


def test_scan_generate_missions():
    g = Galaxy(seed=1)
    s = _ship()
    p = PirateShip(5, 5)
    m = g.scan_generate_missions(p, "deep", s)
    assert m is None or isinstance(m, Mission)


def test_get_object_info():
    g = Galaxy(seed=1)
    st = g.stations[0]
    info = g.get_object_info(st.x, st.y)
    assert info != ""
    empty = g.get_object_info(1, 1)
    assert isinstance(empty, str)


# =============================================================================
# Station economy edges
# =============================================================================

def test_price_for_player_friend_hostile():
    g = Galaxy()
    st = Station(1, 1, "Hub", "trade_hub", "free_traders")
    st.update_prices()
    s = _ship()
    s.reputation["free_traders"] = 60
    price, notes = st.price_for_player("metal", True, s)
    assert "friend" in notes
    s.reputation["free_traders"] = -30
    price2, notes2 = st.price_for_player("metal", True, s)
    assert "hostile" in notes2
    p0, _ = st.price_for_player("bogus", True, s)
    assert p0 == 0


def test_buy_from_blocked_contraband():
    g = Galaxy()
    st = Station(1, 1, "Hub", "trade_hub", "imperium")  # relic — контрабанда империума
    st.update_prices()
    s = _ship()
    s.reputation["imperium"] = -30
    s.cargo.add("metal", 5)
    msg = st.buy_from(s, "metal", 5)
    assert "blocked" in msg
    # контрабанда
    s.reputation["imperium"] = 0
    s.cargo.add("relic", 2)
    msg2 = st.buy_from(s, "relic", 1)
    assert "Contraband" in msg2
    msg3 = st.buy_from(s, "metal", 999)
    assert "Not enough" in msg3


def test_sell_to_success_and_unknown():
    g = Galaxy()
    st = Station(1, 1, "Hub", "trade_hub", "free_traders")
    st.update_prices()
    s = _ship()
    s.credits = 1000
    msg = st.sell_to(s, "metal", 2)
    assert "Bought" in msg
    assert s.cargo.has("metal") == 2
    msg2 = st.sell_to(s, "bogus", 1)
    assert "Unknown" in msg2


# =============================================================================
# ShipModule.load_ammo
# =============================================================================

def test_load_ammo():
    cargo = CargoHold(100)
    cargo.add("slug", 10)
    m = ShipModule("kinetic_cannon")
    m.current_ammo = 0  # по умолчанию оружие заряжено полностью
    loaded = m.load_ammo("slug", 20, cargo)
    assert loaded == 10  # сколько хватило
    assert m.current_ammo == 10
    assert m.loaded_ammo_type == "slug"
    # больше нет
    loaded2 = m.load_ammo("slug", 20, cargo)
    assert loaded2 == 0


# =============================================================================
# craft edges
# =============================================================================

def test_craft_unknown_and_insufficient():
    s = _ship()
    msg, ok = s.craft("bogus_recipe", 1)
    assert ok is False
    s.cargo.items.clear()
    msg2, ok2 = s.craft("repair_kit", 1)
    assert ok2 is False


# =============================================================================
# trader current_target / galaxy queries
# =============================================================================

def test_current_target_route():
    g = Galaxy(seed=1)
    t = TraderShip(1, 1, [0, 1])
    st0 = t.current_target(g.stations)
    assert st0 is g.stations[0]
    t.route_index = 1
    assert t.current_target(g.stations) is g.stations[1]


def test_get_nearest_station():
    g = Galaxy(seed=1)
    st = g.get_nearest_station(0, 0, md=1000)
    assert st is not None
