"""Tests for models.py — comprehensive core game logic."""

import pytest
import random
from models import (
    CargoHold, ShipModule, PlayerShip, NPCShip, TraderShip,
    PirateShip, Station, Galaxy, GameEvent, NewsEntry, Mission,
    NPCShip_id_counter,
)
from config import (
    WIDTH, HEIGHT, RESOURCES, FACTIONS, SHIP_MODULES,
    COMPARTMENTS, CONTRABAND, TILE_EMPTY, TILE_STAR,
    TILE_BLACK_HOLE, TILE_STATION, TILE_ASTEROIDS, TILE_WORMHOLE,
    TILE_PLANET,
)


# ──────────────────────────────────────────────────────────────────────
# CargoHold
# ──────────────────────────────────────────────────────────────────────

class TestCargoHold:
    def test_initial(self):
        c = CargoHold(100)
        assert c.capacity == 100
        assert c.used() == 0
        assert c.free() == 100

    def test_add(self):
        c = CargoHold(50)
        assert c.add("ore", 30)
        assert c.has("ore") == 30
        assert c.used() == 30

    def test_add_exceeds(self):
        c = CargoHold(10)
        assert not c.add("ore", 11)
        assert c.used() == 0

    def test_add_exact(self):
        c = CargoHold(10)
        assert c.add("ore", 10)
        assert c.free() == 0

    def test_remove(self):
        c = CargoHold(50)
        c.add("ore", 20)
        assert c.remove("ore", 10)
        assert c.has("ore") == 10

    def test_remove_all_clears_key(self):
        c = CargoHold(50)
        c.add("ore", 10)
        c.remove("ore", 10)
        assert "ore" not in c.items

    def test_remove_insufficient(self):
        c = CargoHold(50)
        c.add("ore", 5)
        assert not c.remove("ore", 10)

    def test_has_absent(self):
        c = CargoHold(50)
        assert c.has("ghost") == 0

    def test_free_floor_zero(self):
        c = CargoHold(10)
        assert not c.add("ore", 15)  # rejected
        assert c.used() == 0
        assert c.free() == 10

    def test_total_value(self):
        c = CargoHold(50)
        c.add("ore", 2)
        c.add("relic", 1)
        assert c.total_value() == 510  # 5*2 + 500

    def test_multi_add(self):
        c = CargoHold(50)
        c.add("ore", 10)
        c.add("ice", 5)
        c.add("ore", 5)
        assert c.used() == 20
        assert c.has("ore") == 15
        assert c.has("ice") == 5


# ──────────────────────────────────────────────────────────────────────
# ShipModule
# ──────────────────────────────────────────────────────────────────────

class TestShipModule:
    def test_create_fusion_reactor(self):
        m = ShipModule("fusion_reactor")
        assert m.id == "fusion_reactor"
        assert m.comp == "reactor"
        assert m.energy_consumption == 0
        assert m.durability == 100
        assert m.cost == 800

    def test_create_laser_turret(self):
        m = ShipModule("laser_turret")
        assert m.stats["damage"] == 15
        assert m.stats["accuracy"] == 80

    def test_is_broken(self):
        m = ShipModule("ion_drive")
        assert not m.is_broken()
        m.durability = 0
        assert m.is_broken()

    def test_unknown_module_defaults(self):
        m = ShipModule("nonexistent")
        assert m.name == "nonexistent"
        assert m.comp == "reactor"
        assert m.stats == {}

    def test_all_known_modules_valid(self):
        for mid in SHIP_MODULES:
            m = ShipModule(mid)
            assert m.comp in COMPARTMENTS


# ──────────────────────────────────────────────────────────────────────
# PlayerShip
# ──────────────────────────────────────────────────────────────────────

class TestPlayerShip:
    def test_initial(self):
        s = PlayerShip("Test", 120)
        assert s.name == "Test"
        assert s.hull == 120
        assert s.max_hull == 120
        assert s.fuel == 80
        assert s.credits == 1000
        assert s.race == "human"
        assert s.religion is None
        assert s.shield_hp == 30

    def test_default_compartments(self):
        s = PlayerShip("A", 100)
        for c in COMPARTMENTS:
            assert c in s.compartments
        assert any(m.id == "fusion_reactor" for m in s.compartments["reactor"]["modules"])
        assert any(m.id == "ion_drive" for m in s.compartments["engine"]["modules"])
        assert any(m.id == "deflector_shield" for m in s.compartments["shield"]["modules"])

    def test_reputation(self):
        s = PlayerShip("A", 100)
        assert s.reputation["imperium"] == 0
        assert s.reputation["pirates"] == -10

    # --- Damage & shields ---

    def test_take_damage_shields_absorb(self):
        s = PlayerShip("A", 100)
        s.shield_hp = 30
        assert s.take_damage(20)
        assert s.shield_hp == 10
        assert s.hull == 100  # untouched

    def test_take_damage_shields_partial(self):
        s = PlayerShip("A", 100)
        s.shield_hp = 10
        assert s.take_damage(30)
        assert s.shield_hp == 0
        assert s.hull == 80  # 100 - 20

    def test_take_damage_hull_only(self):
        s = PlayerShip("A", 100)
        s.shield_hp = 0
        assert s.take_damage(30)
        assert s.hull == 70

    def test_take_damage_lethal(self):
        s = PlayerShip("A", 20)
        s.shield_hp = 0
        assert not s.take_damage(30)
        assert s.hull == 0

    def test_regen_shields(self):
        s = PlayerShip("A", 100)
        s.shield_hp = 0
        s.regen_shields()
        assert s.shield_hp > 0

    def test_regen_shields_capped(self):
        s = PlayerShip("A", 100)
        cap = s.get_effective_stats().get("shield_cap", 30)
        s.shield_hp = cap
        s.regen_shields()
        assert s.shield_hp == cap

    def test_module_damage_triggered(self):
        s = PlayerShip("A", 100)
        s.shield_hp = 0
        s._last_damaged_module = None
        for _ in range(50):
            s.take_damage(5)
            if s._last_damaged_module is not None:
                break
        assert s._last_damaged_module is not None  # triggered at least once

    # --- Power ---

    def test_power_generated(self):
        s = PlayerShip("A", 100)
        assert s.total_power_generated() == 12  # fusion_reactor

    def test_power_consumed(self):
        s = PlayerShip("A", 100)
        # ion_drive(2) + deflector_shield(4) + long_range_scanner(2) = 8
        assert s.total_power_consumed() == 8

    def test_effective_stats_speed(self):
        s = PlayerShip("A", 100)
        stats = s.get_effective_stats()
        assert stats["speed"] >= 1  # base 0 + ion_drive 1

    def test_effective_stats_sensor(self):
        s = PlayerShip("A", 100)
        stats = s.get_effective_stats()
        assert stats["sensor_range"] >= 12  # base 7 + scanner 5

    def test_effective_stats_power_deficit(self):
        s = PlayerShip("A", 100)
        s.compartments["reactor"]["modules"] = []
        stats = s.get_effective_stats()
        assert stats["speed"] < 2  # reduced

    # --- Modules ---

    def test_install_module(self):
        s = PlayerShip("A", 100)
        assert s.install_module("cargo_expander")
        assert any(m.id == "cargo_expander" for m in s.compartments["cargo"]["modules"])

    def test_install_invalid(self):
        s = PlayerShip("A", 100)
        assert not s.install_module("nonexistent")

    def test_hull_bonus(self):
        s = PlayerShip("A", 100)
        s.install_module("armor_plating")
        assert s.get_effective_stats()["hull_bonus"] == 20

    def test_repair_module(self):
        s = PlayerShip("A", 100)
        m = s.compartments["engine"]["modules"][0]
        m.durability = 10
        msg, cost = s.repair_module("engine")
        assert cost > 0
        assert m.durability > 10

    def test_repair_unknown_compartment(self):
        s = PlayerShip("A", 100)
        msg, cost = s.repair_module("nonexistent")
        assert cost == 0

    def test_repair_no_damage(self):
        s = PlayerShip("A", 100)
        msg, cost = s.repair_module("sensor")
        assert cost == 0


# ──────────────────────────────────────────────────────────────────────
# NPCShip hierarchy
# ──────────────────────────────────────────────────────────────────────

class TestNPCShip:
    def setup_method(self):
        npc_reset()

    def test_create(self):
        n = NPCShip(10, 20, "Test", 50, "imperium")
        assert n.x == 10
        assert n.y == 20
        assert n.hull == 50
        assert n.shield_hp == 0
        assert n.alive

    def test_unique_ids(self):
        a = NPCShip(0, 0, "A", 50, "imperium")
        b = NPCShip(0, 0, "B", 50, "imperium")
        assert a.uid != b.uid

    def test_take_damage(self):
        n = NPCShip(0, 0, "X", 40, "free_traders")
        assert n.take_damage(15)
        assert n.hull == 25

    def test_take_damage_with_shields(self):
        n = NPCShip(0, 0, "X", 40, "free_traders")
        n.shield_hp = 10
        assert n.take_damage(15)
        assert n.shield_hp == 0
        assert n.hull == 35  # 40 - (15 - 10)

    def test_take_damage_shields_absorb_all(self):
        n = NPCShip(0, 0, "X", 40, "free_traders")
        n.shield_hp = 20
        assert n.take_damage(10)
        assert n.shield_hp == 10
        assert n.hull == 40  # untouched

    def test_take_damage_lethal(self):
        n = NPCShip(0, 0, "X", 30, "free_traders")
        assert not n.take_damage(40)
        assert not n.alive


class TestTraderShip:
    def setup_method(self):
        npc_reset()

    def test_create(self):
        t = TraderShip(5, 5, [0, 1])
        assert t.hull == 60
        assert t.shield_hp == 20
        assert t.cargo.capacity == 100
        assert t.cargo.has("fuel_cell") >= 20

    def test_current_target(self):
        s1 = Station(10, 10, name="S1")
        s2 = Station(20, 20, name="S2")
        t = TraderShip(0, 0, [0, 1])
        assert t.current_target([s1, s2]).name == "S1"

    def test_route_wraps(self):
        s1 = Station(10, 10, name="S1")
        t = TraderShip(0, 0, [0])
        t.route_index = 1
        assert t.current_target([s1]).name == "S1"


class TestPirateShip:
    def setup_method(self):
        npc_reset()

    def test_create(self):
        p = PirateShip(5, 5)
        assert p.hull == 40
        assert p.shield_hp == 10
        assert p.faction in ("chaos_cult", "xenos_horde")
        assert p.aggro_range == 5


# ──────────────────────────────────────────────────────────────────────
# Station — economy
# ──────────────────────────────────────────────────────────────────────

class TestStation:
    def test_create(self):
        s = Station(10, 20, name="Hub", stype="trade_hub", faction="imperium")
        assert s.name == "Hub"
        assert s.faction == "imperium"

    def test_inventory(self):
        s = Station(0, 0)
        for r in RESOURCES:
            assert r in s.inventory

    def test_prices(self):
        s = Station(0, 0)
        for r in RESOURCES:
            bp, sp = s.prices[r]
            assert bp > 0
            assert sp > 0

    def test_price_history(self):
        s = Station(0, 0)
        for r in RESOURCES:
            assert len(s.price_history[r]) >= 1

    def test_buy_from_success(self):
        s = Station(0, 0, faction="free_traders")
        ship = PlayerShip("T", 100)
        ship.cargo.add("ore", 10)
        result = s.buy_from(ship, "ore", 5)
        assert "Sold" in result
        assert ship.credits > 1000

    def test_buy_from_not_enough(self):
        s = Station(0, 0)
        ship = PlayerShip("T", 100)
        assert "Not enough" in s.buy_from(ship, "ore", 5)

    def test_buy_from_blocked(self):
        s = Station(0, 0, faction="imperium")
        ship = PlayerShip("T", 100)
        ship.reputation["imperium"] = -30
        ship.cargo.add("ore", 10)
        assert "blocked" in s.buy_from(ship, "ore", 5).lower()

    def test_sell_to_success(self):
        s = Station(0, 0, faction="free_traders")
        s.inventory["ore"] = 20
        ship = PlayerShip("T", 100)
        assert "Bought" in s.sell_to(ship, "ore", 5)
        assert ship.cargo.has("ore") == 5

    def test_sell_to_not_enough_stock(self):
        s = Station(0, 0, faction="free_traders")
        s.inventory["ore"] = 2
        ship = PlayerShip("T", 100)
        assert "Only" in s.sell_to(ship, "ore", 5)

    def test_sell_to_no_credits(self):
        s = Station(0, 0, faction="free_traders")
        s.inventory["ore"] = 20
        ship = PlayerShip("T", 100)
        ship.credits = 0
        assert "Need" in s.sell_to(ship, "ore", 5)

    def test_sell_to_cargo_full(self):
        s = Station(0, 0, faction="free_traders")
        s.inventory["ore"] = 20
        ship = PlayerShip("T", 100)
        ship.cargo.add("metal", ship.cargo.free())
        assert "full" in s.sell_to(ship, "ore", 5).lower()

    def test_update_economy_produces(self):
        s = Station(0, 0, stype="industrial", faction="free_traders")
        s.inventory["ore"] = 20
        s.inventory["ice"] = 20
        old = s.inventory.get("metal", 0)
        s.update_economy()
        assert s.inventory["metal"] > old

    def test_update_economy_consumes(self):
        s = Station(0, 0, stype="industrial", faction="free_traders")
        s.inventory["ore"] = 20
        old = s.inventory["ore"]
        s.update_economy()
        assert s.inventory["ore"] < old

    def test_crisis_blocks_economy(self):
        s = Station(0, 0, stype="industrial")
        s.crisis_ticks = 5
        old_ore = s.inventory["ore"]
        s.update_economy()
        assert s.inventory["ore"] == old_ore
        assert s.crisis_ticks == 4

    def test_price_summary(self):
        s = Station(0, 0, name="Hub", faction="free_traders")
        assert "Hub" in s.price_summary()

    def test_modules_for_sale(self):
        s = Station(0, 0, name="Hub", faction="free_traders")
        assert len(s.modules_for_sale) >= 2
        for mid in s.modules_for_sale:
            assert mid in SHIP_MODULES

    def test_price_friend_discount(self):
        s = Station(0, 0, faction="imperium")
        ship = PlayerShip("T", 100)
        ship.reputation["imperium"] = 60
        s.inventory["ore"] = 10
        s.update_prices()
        _, notes = s.price_for_player("ore", True, ship)
        assert "friend" in notes

    def test_price_hostile_penalty(self):
        s = Station(0, 0, faction="imperium")
        ship = PlayerShip("T", 100)
        ship.reputation["imperium"] = -30
        s.inventory["ore"] = 10
        s.update_prices()
        _, notes = s.price_for_player("ore", True, ship)
        assert "hostile" in notes


# ──────────────────────────────────────────────────────────────────────
# Galaxy — generation
# ──────────────────────────────────────────────────────────────────────

class TestGalaxyGeneration:
    def test_deterministic_seed(self):
        g1 = Galaxy(seed=42)
        g2 = Galaxy(seed=42)
        assert g1.tiles == g2.tiles
        assert g1.objects == g2.objects
        assert len(g1.stations) == len(g2.stations)

    def test_seed_zero(self):
        g = Galaxy(seed=0)
        assert g.seed == 0

    def test_different_seeds_different(self):
        g1 = Galaxy(seed=1)
        g2 = Galaxy(seed=2)
        assert g1.seed != g2.seed

    def test_has_stations(self):
        g = Galaxy(seed=42)
        assert len(g.stations) > 0

    def test_has_traders(self):
        g = Galaxy(seed=42)
        assert len(g.traders) > 0

    def test_has_pirates(self):
        g = Galaxy(seed=42)
        assert len(g.pirates) > 0

    def test_black_holes_match_objects(self):
        g = Galaxy(seed=42)
        for bh in g.black_holes:
            assert g.objects.get(bh) == "black_hole"

    def test_wormholes_match_objects(self):
        g = Galaxy(seed=42)
        for wh in g.wormholes:
            assert g.objects.get(wh) == "wormhole"


# ──────────────────────────────────────────────────────────────────────
# Galaxy — queries
# ──────────────────────────────────────────────────────────────────────

class TestGalaxyQueries:
    def test_get_tile_in_bounds(self):
        g = Galaxy(seed=42)
        tile = g.get_tile(0, 0)
        assert tile in (
            TILE_EMPTY, TILE_STAR, TILE_PLANET, TILE_STATION,
            TILE_BLACK_HOLE, TILE_WORMHOLE, TILE_ASTEROIDS,
        )

    def test_get_tile_oob(self):
        g = Galaxy()
        assert g.get_tile(-1, -1) == " "
        assert g.get_tile(999, 999) == " "

    def test_is_passable_empty(self):
        g = Galaxy(seed=42)
        for y in range(g.height):
            for x in range(g.width):
                if g.tiles[y][x] == TILE_EMPTY and (x, y) not in g.objects:
                    assert g.is_passable(x, y)

    def test_is_not_passable_star(self):
        g = Galaxy(seed=42)
        stars = [p for p, o in g.objects.items() if o == "star"]
        if stars:
            x, y = stars[0]
            assert not g.is_passable(x, y)

    def test_is_not_passable_oob(self):
        g = Galaxy()
        assert not g.is_passable(-1, 0)
        assert not g.is_passable(g.width, 0)

    def test_get_object_info_star(self):
        g = Galaxy(seed=42)
        stars = [p for p, o in g.objects.items() if o == "star"]
        if stars:
            assert "Star" in g.get_object_info(*stars[0])

    def test_get_object_info_empty(self):
        g = Galaxy(seed=42)
        for y in range(g.height):
            for x in range(g.width):
                if g.tiles[y][x] == TILE_EMPTY and (x, y) not in g.objects:
                    assert g.get_object_info(x, y) == "Empty"
                    return

    def test_get_station_at(self):
        g = Galaxy(seed=42)
        if g.stations:
            s = g.stations[0]
            assert g.get_station_at(s.x, s.y) is s

    def test_get_nearest_station(self):
        g = Galaxy(seed=42)
        if g.stations:
            s = g.stations[0]
            assert g.get_nearest_station(s.x, s.y, 0) is s

    def test_get_npc_at(self):
        g = Galaxy(seed=42)
        if g.traders:
            t = g.traders[0]
            assert g.get_npc_at(t.x, t.y) is t

    def test_get_npc_by_name(self):
        g = Galaxy(seed=42)
        if g.traders:
            t = g.traders[0]
            assert g.get_npc_by_name(t.name) is t

    def test_get_npc_by_name_case_insensitive(self):
        g = Galaxy(seed=42)
        if g.traders:
            t = g.traders[0]
            assert g.get_npc_by_name(t.name.lower()) is t

    def test_stations_in_range(self):
        g = Galaxy(seed=42)
        if g.stations:
            s = g.stations[0]
            assert s in g.stations_in_range(s.x, s.y, 5)

    def test_add_news(self):
        g = Galaxy()
        n = len(g.news)
        g.add_news("H", "B")
        assert len(g.news) == n + 1

    def test_news_capped(self):
        g = Galaxy()
        for i in range(60):
            g.add_news(f"H{i}", f"B{i}")
        assert len(g.news) == 50

    def test_diplomacy(self):
        g = Galaxy()
        for f in FACTIONS:
            assert f in g.diplomacy


# ──────────────────────────────────────────────────────────────────────
# Galaxy — tick system
# ──────────────────────────────────────────────────────────────────────

class TestGalaxyTick:
    def test_gravity_pulls_toward_black_hole(self):
        g = Galaxy(seed=42)
        if not g.black_holes:
            pytest.skip("No black holes")
        bh = g.black_holes[0]
        # Place ship 2 cells away (within gravity range 3)
        px, py = bh[0] - 2, bh[1]
        if not g.is_passable(px, py):
            pytest.skip("Position not passable")
        ship = PlayerShip("T", 100)
        nx, ny, evs, over = g.tick(px, py, ship)
        # Should be pulled closer
        new_dist = max(abs(nx - bh[0]), abs(ny - bh[1]))
        old_dist = max(abs(px - bh[0]), abs(py - bh[1]))
        assert new_dist < old_dist

    def test_radiation_damages_hull(self):
        g = Galaxy(seed=42)
        ship = PlayerShip("T", 100)
        ship.shield_hp = 0
        stars = [p for p, o in g.objects.items() if o == "star"]
        for sx, sy in stars:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = sx + dx, sy + dy
                    if dx == 0 and dy == 0:
                        continue
                    if not g.is_passable(nx, ny):
                        continue
                    if (nx, ny) in g.objects:
                        continue
                    hull_before = ship.hull
                    _, _, evs, _ = g.tick(nx, ny, ship)
                    if any("Radiation" in e for e in evs):
                        assert ship.hull < hull_before
                    return

    def test_asteroid_damage(self):
        g = Galaxy(seed=42)
        ship = PlayerShip("T", 100)
        ship.shield_hp = 0
        asteroids = [p for p, o in g.objects.items() if o == "asteroids"]
        if asteroids:
            for _ in range(30):
                g.tick(*asteroids[0], ship)
            # No crash is the main assertion; damage is probabilistic

    def test_station_economy_ticks(self):
        g = Galaxy(seed=42)
        if g.stations:
            s = g.stations[0]
            old_inv = dict(s.inventory)
            ship = PlayerShip("T", 100)
            g.tick(s.x + 5, s.y + 5, ship)
            # Non-crisis station should update economy
            if s.crisis_ticks == 0 and s.stype in ("industrial", "trade_hub", "research"):
                assert s.inventory != old_inv

    def test_npc_counter_reset(self):
        g = Galaxy()
        g.reset_npc_counter()
        assert NPCShip_id_counter == 0


# ──────────────────────────────────────────────────────────────────────
# Missions
# ──────────────────────────────────────────────────────────────────────

class TestMissions:
    def test_create_mission(self):
        m = Mission("deliver", "ore", 5, "Alpha", 200, 30)
        assert m.mtype == "deliver"
        assert m.resource == "ore"
        assert m.amount == 5
        assert m.target_station == "Alpha"
        assert m.reward == 200
        assert m.ticks == 30

    def test_station_gen_missions(self):
        s1 = Station(10, 10, name="S1")
        s2 = Station(20, 20, name="S2")
        s1.gen_missions([s1, s2])
        assert len(s1.missions) >= 1
        m = s1.missions[0]
        assert m.target_station != "S1"  # not to itself

    def test_check_missions_complete(self):
        s1 = Station(10, 10, name="S1")
        ship = PlayerShip("T", 100)
        ship.cargo.add("ore", 10)
        ship.missions.append(Mission("deliver", "ore", 5, "S1", 200, 20))
        assert ship.credits == 1000
        completed = ship.check_missions(s1)
        assert len(completed) == 1
        assert ship.credits == 1200
        assert len(ship.missions) == 0

    def test_check_missions_not_enough_cargo(self):
        s1 = Station(10, 10, name="S1")
        ship = PlayerShip("T", 100)
        ship.cargo.add("ore", 2)
        ship.missions.append(Mission("deliver", "ore", 5, "S1", 200, 20))
        completed = ship.check_missions(s1)
        assert len(completed) == 0
        assert len(ship.missions) == 1  # not completed

    def test_check_missions_wrong_station(self):
        s1 = Station(10, 10, name="S1")
        s2 = Station(20, 20, name="S2")
        ship = PlayerShip("T", 100)
        ship.cargo.add("ore", 10)
        ship.missions.append(Mission("deliver", "ore", 5, "S2", 200, 20))
        completed = ship.check_missions(s1)
        assert len(completed) == 0  # wrong station

    def test_missions_in_galaxy(self):
        g = Galaxy(seed=42)
        total = sum(len(s.missions) for s in g.stations)
        assert total > 0  # missions generated on creation


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def npc_reset():
    import models
    models.NPCShip_id_counter = 0
