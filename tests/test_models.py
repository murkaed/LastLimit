"""Tests for models.py — core game data structures."""

import pytest
import random
from models import (
    CargoHold, ShipModule, PlayerShip, NPCShip, TraderShip,
    PirateShip, Station, Galaxy, GameEvent, NewsEntry,
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
    def test_initial_state(self):
        c = CargoHold(100)
        assert c.capacity == 100
        assert c.used() == 0
        assert c.free() == 100
        assert c.items == {}

    def test_add_within_capacity(self):
        c = CargoHold(50)
        assert c.add("ore", 30)
        assert c.used() == 30
        assert c.has("ore") == 30

    def test_add_exact_capacity(self):
        c = CargoHold(10)
        assert c.add("ore", 10)
        assert c.free() == 0

    def test_add_exceeds_capacity(self):
        c = CargoHold(10)
        assert not c.add("ore", 11)
        assert c.used() == 0

    def test_add_multiple_resources(self):
        c = CargoHold(50)
        c.add("ore", 10)
        c.add("ice", 5)
        c.add("ore", 5)
        assert c.used() == 20
        assert c.has("ore") == 15
        assert c.has("ice") == 5

    def test_remove_existing(self):
        c = CargoHold(50)
        c.add("ore", 20)
        assert c.remove("ore", 10)
        assert c.has("ore") == 10

    def test_remove_clears_zero(self):
        c = CargoHold(50)
        c.add("ore", 10)
        assert c.remove("ore", 10)  # removes all
        assert "ore" not in c.items

    def test_remove_insufficient(self):
        c = CargoHold(50)
        c.add("ore", 5)
        assert not c.remove("ore", 10)
        assert c.has("ore") == 5

    def test_remove_nonexistent(self):
        c = CargoHold(50)
        assert not c.remove("ore", 1)

    def test_has_nonexistent(self):
        c = CargoHold(50)
        assert c.has("ghost") == 0

    def test_free_never_negative(self):
        c = CargoHold(10)
        oversize_result = c.add("ore", 15)  # can't fit, should reject
        assert oversize_result is False
        assert c.used() == 0
        assert c.free() == 10  # free() floor is 0, and we're at 10

    def test_total_value(self):
        c = CargoHold(50)
        c.add("ore", 2)  # base_price = 5
        c.add("relic", 1)  # base_price = 500
        assert c.total_value() == 510


# ──────────────────────────────────────────────────────────────────────
# ShipModule
# ──────────────────────────────────────────────────────────────────────

class TestShipModule:
    def test_create_valid(self):
        m = ShipModule("fusion_reactor")
        assert m.id == "fusion_reactor"
        assert m.name == "Fusion Reactor"
        assert m.comp == "reactor"
        assert m.energy_consumption == 0
        assert m.durability == 100
        assert m.max_durability == 100
        assert m.active is True
        assert m.cost == 800

    def test_stats_parsing(self):
        m = ShipModule("laser_turret")
        assert m.stats["damage"] == 15
        assert m.stats["accuracy"] == 80

    def test_is_broken(self):
        m = ShipModule("ion_drive")
        assert not m.is_broken()
        m.durability = 0
        assert m.is_broken()

    def test_unknown_module_has_defaults(self):
        m = ShipModule("nonexistent")
        assert m.name == "nonexistent"
        assert m.comp == "reactor"
        assert m.energy_consumption == 0
        assert m.stats == {}
        assert m.cost == 100


# ──────────────────────────────────────────────────────────────────────
# PlayerShip
# ──────────────────────────────────────────────────────────────────────

class TestPlayerShip:
    def test_initial_state(self):
        s = PlayerShip("TestShip", 120)
        assert s.name == "TestShip"
        assert s.hull == 120
        assert s.fuel == 80
        assert s.credits == 1000
        assert s.race == "human"
        assert s.religion is None
        assert s.cargo.capacity == 50

    def test_take_damage_reduces_hull(self):
        s = PlayerShip("A", 100)
        s.shield_hp = 0  # drain shields to test hull damage directly
        result = s.take_damage(30)
        assert s.hull == 70
        assert result is True

    def test_take_damage_shields_absorb(self):
        s = PlayerShip("A", 100)
        s.shield_hp = 30
        result = s.take_damage(20)
        assert s.shield_hp == 10  # 30 - 20
        assert s.hull == 100  # hull untouched
        assert result is True

    def test_take_damage_shields_partial(self):
        s = PlayerShip("A", 100)
        s.shield_hp = 10
        result = s.take_damage(30)
        assert s.shield_hp == 0  # depleted
        assert s.hull == 80  # 100 - 20 remaining
        assert result is True

    def test_take_damage_lethal(self):
        s = PlayerShip("A", 20)
        s.shield_hp = 0
        result = s.take_damage(30)
        assert s.hull == 0
        assert result is False

    def test_default_reputation(self):
        s = PlayerShip("A", 100)
        assert s.reputation["imperium"] == 0
        assert s.reputation["pirates"] == -10

    def test_compartments_initialized(self):
        s = PlayerShip("A", 100)
        for c in COMPARTMENTS:
            assert c in s.compartments

    def test_default_modules_installed(self):
        s = PlayerShip("A", 100)
        reactor_mods = s.compartments["reactor"]["modules"]
        assert any(m.id == "fusion_reactor" for m in reactor_mods)
        engine_mods = s.compartments["engine"]["modules"]
        assert any(m.id == "ion_drive" for m in engine_mods)

    def test_total_power_generated(self):
        s = PlayerShip("A", 100)
        assert s.total_power_generated() == 12  # fusion_reactor

    def test_total_power_consumed(self):
        s = PlayerShip("A", 100)
        # ion_drive(2) + deflector_shield(4) + long_range_scanner(2) = 8
        assert s.total_power_consumed() == 8

    def test_get_effective_stats(self):
        s = PlayerShip("A", 100)
        stats = s.get_effective_stats()
        assert stats["speed"] >= 1
        assert stats["sensor_range"] >= 12  # 7 base + 5 scanner
        assert stats["shield_cap"] >= 30

    def test_get_effective_stats_power_deficit(self):
        s = PlayerShip("A", 100)
        # reduce reactor power to 0
        s.compartments["reactor"]["modules"] = []
        stats = s.get_effective_stats()
        assert stats["speed"] <= 1  # reduced by power deficit

    def test_install_module(self):
        s = PlayerShip("A", 100)
        assert s.install_module("cargo_expander")
        cargo_mods = s.compartments["cargo"]["modules"]
        assert any(m.id == "cargo_expander" for m in cargo_mods)

    def test_install_module_invalid(self):
        s = PlayerShip("A", 100)
        assert not s.install_module("nonexistent_module")

    def test_regen_shields(self):
        s = PlayerShip("A", 100)
        s.shield_hp = 0
        s.regen_shields()
        assert s.shield_hp > 0  # should regen at least 2

    def test_regen_shields_capped(self):
        s = PlayerShip("A", 100)
        cap = s.get_effective_stats().get("shield_cap", 30)
        s.shield_hp = cap
        s.regen_shields()
        assert s.shield_hp == cap  # shouldn't exceed cap

    def test_module_damage_on_hull_hit(self):
        s = PlayerShip("A", 100)
        s.shield_hp = 0
        s._last_damaged_module = None
        # Force many hits to trigger 30% module damage chance
        damaged = False
        for _ in range(50):
            s.take_damage(5)
            if s._last_damaged_module is not None:
                damaged = True
                break
        assert damaged  # should trigger at least once in 50 hits

    def test_repair_module(self):
        s = PlayerShip("A", 100)
        # Damage a module manually
        m = s.compartments["engine"]["modules"][0]
        m.durability = 10
        msg, cost = s.repair_module("engine")
        assert cost > 0
        assert m.durability > 10  # repaired

    def test_repair_module_unknown_compartment(self):
        s = PlayerShip("A", 100)
        msg, cost = s.repair_module("nonexistent")
        assert cost == 0
        assert "Unknown" in msg

    def test_repair_module_no_damage(self):
        s = PlayerShip("A", 100)
        msg, cost = s.repair_module("sensor")
        assert cost == 0
        assert "No damaged" in msg

    def test_cargo_bonus_from_modules(self):
        s = PlayerShip("A", 100)
        s.install_module("cargo_expander")
        stats = s.get_effective_stats()
        assert stats["cargo_bonus"] == 25

    def test_hull_bonus_from_modules(self):
        s = PlayerShip("A", 100)
        s.install_module("armor_plating")
        stats = s.get_effective_stats()
        assert stats["hull_bonus"] == 20

    def test_crew_initial(self):
        s = PlayerShip("A", 100)
        assert s.crew["Pilot"] is None
        assert s.crew["Engineer"] is None
        assert s.crew["Tactical"] is None
        assert s.crew["Scientist"] is None


# ──────────────────────────────────────────────────────────────────────
# NPCShip / TraderShip / PirateShip
# ──────────────────────────────────────────────────────────────────────

class TestNPCShip:
    def setup_method(self):
        NPCShip_id_counter_reset()

    def test_creation(self):
        n = NPCShip(10, 20, "TestNPC", 50, "imperium")
        assert n.x == 10
        assert n.y == 20
        assert n.name == "TestNPC"
        assert n.hull == 50
        assert n.max_hull == 50
        assert n.faction == "imperium"
        assert n.alive is True

    def test_unique_ids(self):
        a = NPCShip(0, 0, "A", 50, "imperium")
        b = NPCShip(0, 0, "B", 50, "imperium")
        assert a.uid != b.uid

    def test_take_damage(self):
        n = NPCShip(0, 0, "X", 40, "free_traders")
        assert n.take_damage(15)
        assert n.hull == 25
        assert n.alive is True

    def test_take_damage_lethal(self):
        n = NPCShip(0, 0, "X", 30, "free_traders")
        result = n.take_damage(40)
        assert result is False
        assert n.alive is False
        assert n.hull == 0


class TestTraderShip:
    def setup_method(self):
        NPCShip_id_counter_reset()

    def test_creation_defaults(self):
        t = TraderShip(5, 5, [0, 1])
        assert t.hull == 60
        assert t.max_hull == 60
        assert t.faction in ("free_traders", "imperium", "machine_collective")
        assert t.cargo.capacity == 100
        assert t.cargo.has("fuel_cell") >= 20
        assert t.alive is True

    def test_current_target(self):
        stations = [Station(10, 10, name="S1"), Station(20, 20, name="S2")]
        t = TraderShip(0, 0, [0, 1])
        target = t.current_target(stations)
        assert target is not None
        assert target.name == "S1"

    def test_current_target_wraps_route(self):
        stations = [Station(10, 10, name="S1")]
        t = TraderShip(0, 0, [0])
        # Advance route twice to wrap
        t.route_index = 0
        assert t.current_target(stations).name == "S1"
        t.route_index = 1
        assert t.current_target(stations).name == "S1"

    def test_no_route(self):
        t = TraderShip(0, 0, [])
        assert t.current_target([]) is None


class TestPirateShip:
    def setup_method(self):
        NPCShip_id_counter_reset()

    def test_creation_defaults(self):
        p = PirateShip(5, 5)
        assert p.hull == 40
        assert p.faction in ("chaos_cult", "xenos_horde")
        assert p.aggro_range == 5
        assert p.flee_threshold == 8
        assert p.cargo.capacity == 30
        assert p.alive is True


# ──────────────────────────────────────────────────────────────────────
# Station
# ──────────────────────────────────────────────────────────────────────

class TestStation:
    def test_creation(self):
        s = Station(10, 20, name="TestHub", stype="trade_hub", faction="imperium")
        assert s.x == 10
        assert s.y == 20
        assert s.name == "TestHub"
        assert s.stype == "trade_hub"
        assert s.faction == "imperium"
        assert s.crisis_ticks == 0

    def test_inventory_initialized(self):
        s = Station(0, 0)
        for r in RESOURCES:
            assert r in s.inventory
            assert 0 <= s.inventory[r] <= 25

    def test_prices_initialized(self):
        s = Station(0, 0)
        for r in RESOURCES:
            bp, sp = s.prices[r]
            assert bp > 0
            assert sp > 0
            assert bp <= sp  # buy price <= sell price

    def test_price_history_recorded(self):
        s = Station(0, 0)
        for r in RESOURCES:
            assert len(s.price_history[r]) >= 1

    def test_price_for_player_buying(self):
        s = Station(0, 0, faction="free_traders")
        ship = PlayerShip("Test", 100)
        s.inventory["ore"] = 10
        s.update_prices()
        price, _ = s.price_for_player("ore", True, ship)
        assert price > 0

    def test_price_for_player_selling(self):
        s = Station(0, 0, faction="free_traders")
        ship = PlayerShip("Test", 100)
        s.inventory["ore"] = 10
        s.update_prices()
        price, _ = s.price_for_player("ore", False, ship)
        assert price > 0

    def test_price_for_player_friend_bonus(self):
        s = Station(0, 0, faction="imperium")
        ship = PlayerShip("Test", 100)
        ship.reputation["imperium"] = 60
        s.inventory["ore"] = 10
        s.update_prices()
        price, notes = s.price_for_player("ore", True, ship)
        assert "friend" in notes

    def test_price_for_player_hostile_penalty(self):
        s = Station(0, 0, faction="imperium")
        ship = PlayerShip("Test", 100)
        ship.reputation["imperium"] = -30
        s.inventory["ore"] = 10
        s.update_prices()
        price, notes = s.price_for_player("ore", True, ship)
        assert "hostile" in notes

    def test_buy_from_success(self):
        s = Station(0, 0, faction="free_traders")
        ship = PlayerShip("Test", 100)
        ship.cargo.add("ore", 10)
        result = s.buy_from(ship, "ore", 5)
        assert "Sold" in result
        assert ship.cargo.has("ore") == 5
        assert ship.credits > 1000

    def test_buy_from_not_enough_cargo(self):
        s = Station(0, 0)
        ship = PlayerShip("Test", 100)
        result = s.buy_from(ship, "ore", 5)
        assert "Not enough" in result

    def test_buy_from_trade_blocked(self):
        s = Station(0, 0, faction="imperium")
        ship = PlayerShip("Test", 100)
        ship.reputation["imperium"] = -30
        ship.cargo.add("ore", 10)
        result = s.buy_from(ship, "ore", 5)
        assert "blocked" in result.lower()

    def test_sell_to_success(self):
        s = Station(0, 0, faction="free_traders")
        s.inventory["ore"] = 20
        ship = PlayerShip("Test", 100)
        result = s.sell_to(ship, "ore", 5)
        assert "Bought" in result
        assert ship.cargo.has("ore") == 5
        assert ship.credits < 1000

    def test_sell_to_not_enough_stock(self):
        s = Station(0, 0, faction="free_traders")
        s.inventory["ore"] = 2
        ship = PlayerShip("Test", 100)
        result = s.sell_to(ship, "ore", 5)
        assert "Only" in result

    def test_sell_to_not_enough_credits(self):
        s = Station(0, 0, faction="free_traders")
        s.inventory["ore"] = 20
        ship = PlayerShip("Test", 100)
        ship.credits = 0
        result = s.sell_to(ship, "ore", 5)
        assert "Need" in result

    def test_sell_to_cargo_full(self):
        s = Station(0, 0, faction="free_traders")
        s.inventory["ore"] = 20
        ship = PlayerShip("Test", 100)
        ship.cargo.add("metal", ship.cargo.free())  # fill cargo
        result = s.sell_to(ship, "ore", 5)
        assert "full" in result.lower()

    def test_update_economy_produces(self):
        s = Station(0, 0, stype="industrial", faction="free_traders")
        s.inventory["ore"] = 20
        s.inventory["ice"] = 20
        old_metal = s.inventory.get("metal", 0)
        s.update_economy()
        assert s.inventory["metal"] > old_metal

    def test_update_economy_consumes(self):
        s = Station(0, 0, stype="industrial", faction="free_traders")
        s.inventory["ore"] = 20
        old_ore = s.inventory["ore"]
        s.update_economy()
        assert s.inventory["ore"] < old_ore

    def test_crisis_blocks_economy(self):
        s = Station(0, 0, stype="industrial", faction="free_traders")
        s.crisis_ticks = 5
        old_ore = s.inventory["ore"]
        old_metal = s.inventory.get("metal", 0)
        s.update_economy()
        assert s.inventory["ore"] == old_ore
        assert s.inventory.get("metal", 0) == old_metal
        assert s.crisis_ticks == 4

    def test_price_summary(self):
        s = Station(0, 0, name="Hub", faction="free_traders")
        summary = s.price_summary()
        assert "Hub" in summary
        assert "free_traders" in summary


# ──────────────────────────────────────────────────────────────────────
# Galaxy
# ──────────────────────────────────────────────────────────────────────

class TestGalaxy:
    def test_creation_with_seed(self):
        g = Galaxy(seed=42)
        assert g.seed == 42
        assert g.width == WIDTH
        assert g.height == HEIGHT

    def test_creation_with_seed_zero(self):
        """Seed 0 should be valid (not treated as falsy)."""
        g = Galaxy(seed=0)
        assert g.seed == 0

    def test_creation_random_seed(self):
        g1 = Galaxy()
        g2 = Galaxy()
        # Different random seeds
        assert g1.seed != g2.seed

    def test_deterministic_with_same_seed(self):
        g1 = Galaxy(seed=123)
        g2 = Galaxy(seed=123)
        assert g1.tiles == g2.tiles
        assert g1.objects == g2.objects
        assert len(g1.stations) == len(g2.stations)

    def test_get_tile(self):
        g = Galaxy()
        tile = g.get_tile(0, 0)
        assert tile in (
            TILE_EMPTY, TILE_STAR, TILE_PLANET, TILE_STATION,
            TILE_BLACK_HOLE, TILE_WORMHOLE, TILE_ASTEROIDS,
        )

    def test_get_tile_out_of_bounds(self):
        g = Galaxy()
        assert g.get_tile(-1, -1) == " "
        assert g.get_tile(999, 999) == " "

    def test_is_passable(self):
        g = Galaxy(seed=42)
        # Most tiles are passable
        for y in range(g.height):
            for x in range(g.width):
                tile = g.tiles[y][x]
                if tile == TILE_EMPTY:
                    assert g.is_passable(x, y)
                elif tile in (TILE_STAR, TILE_BLACK_HOLE):
                    assert not g.is_passable(x, y)

    def test_is_passable_out_of_bounds(self):
        g = Galaxy()
        assert not g.is_passable(-1, 0)
        assert not g.is_passable(0, -1)
        assert not g.is_passable(g.width, 0)

    def test_has_stations(self):
        g = Galaxy()
        assert len(g.stations) > 0

    def test_has_traders(self):
        g = Galaxy()
        assert len(g.traders) > 0

    def test_has_pirates(self):
        g = Galaxy()
        assert len(g.pirates) > 0

    def test_black_holes(self):
        g = Galaxy()
        assert len(g.black_holes) >= 0
        for bh in g.black_holes:
            assert g.objects.get(bh) == "black_hole"

    def test_wormholes(self):
        g = Galaxy()
        assert len(g.wormholes) >= 0
        for wh in g.wormholes:
            assert g.objects.get(wh) == "wormhole"

    def test_get_object_info_empty(self):
        g = Galaxy(seed=42)
        # Find an empty spot
        for y in range(g.height):
            for x in range(g.width):
                if g.tiles[y][x] == TILE_EMPTY and (x, y) not in g.objects:
                    assert g.get_object_info(x, y) == "Empty"
                    return
        pytest.skip("No empty tiles found")

    def test_get_object_info_star(self):
        g = Galaxy(seed=42)
        stars = [p for p, o in g.objects.items() if o == "star"]
        if stars:
            x, y = stars[0]
            assert "Star" in g.get_object_info(x, y)

    def test_get_station_at(self):
        g = Galaxy(seed=42)
        if g.stations:
            s = g.stations[0]
            found = g.get_station_at(s.x, s.y)
            assert found is s

    def test_get_nearest_station(self):
        g = Galaxy(seed=42)
        if g.stations:
            s = g.stations[0]
            found = g.get_nearest_station(s.x, s.y, 0)
            assert found is s

    def test_get_npc_at(self):
        g = Galaxy(seed=42)
        if g.traders:
            t = g.traders[0]
            found = g.get_npc_at(t.x, t.y)
            assert found is t

    def test_get_npc_by_name(self):
        g = Galaxy(seed=42)
        if g.traders:
            t = g.traders[0]
            found = g.get_npc_by_name(t.name)
            assert found is t

    def test_get_npc_by_name_case_insensitive(self):
        g = Galaxy(seed=42)
        if g.traders:
            t = g.traders[0]
            found = g.get_npc_by_name(t.name.lower())
            assert found is t

    def test_stations_in_range(self):
        g = Galaxy(seed=42)
        if g.stations:
            s = g.stations[0]
            nearby = g.stations_in_range(s.x, s.y, 5)
            assert s in nearby

    def test_add_news(self):
        g = Galaxy()
        initial = len(g.news)
        g.add_news("Test", "Body")
        assert len(g.news) == initial + 1
        assert g.news[-1].headline == "Test"

    def test_news_capped_at_50(self):
        g = Galaxy()
        for i in range(60):
            g.add_news(f"H{i}", f"B{i}")
        assert len(g.news) == 50
        assert g.news[-1].headline == "H59"

    def test_diplomacy_initialized(self):
        g = Galaxy()
        for f in FACTIONS:
            assert f in g.diplomacy
            for f2 in FACTIONS:
                if f != f2:
                    assert f2 in g.diplomacy[f]

    def test_tick_black_hole_gravity(self):
        g = Galaxy(seed=42)
        ship = PlayerShip("Test", 100)
        # Place ship near a black hole
        if g.black_holes:
            bh = g.black_holes[0]
            px, py = bh[0] - 2, bh[1]  # 2 away = within gravity range (<=3)
            if g.is_passable(px, py):
                nx, ny, evs, over = g.tick(px, py, ship)
                # Should be pulled toward black hole
                assert abs(nx - bh[0]) < abs(px - bh[0]) or abs(ny - bh[1]) < abs(py - bh[1])

    def test_tick_radiation_near_star(self):
        g = Galaxy(seed=42)
        ship = PlayerShip("Test", 100)
        stars = [p for p, o in g.objects.items() if o == "star"]
        for sx, sy in stars:
            # Check each adjacent cell
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = sx + dx, sy + dy
                    if (dx == 0 and dy == 0) or not g.is_passable(nx, ny):
                        continue
                    if (nx, ny) in g.objects:
                        continue
                    hull_before = ship.hull
                    ship.shield_hp = 0
                    _, _, evs, over = g.tick(nx, ny, ship)
                    # Radiation should deal damage unless mutant with resistance
                    if ship.race != "mutant" and not ship.radiation_shield:
                        rad_events = [e for e in evs if "Radiation" in e]
                        if rad_events:
                            assert ship.hull < hull_before
                    return
        pytest.skip("No suitable star-adjacent cell")

    def test_tick_asteroid_damage(self):
        g = Galaxy(seed=42)
        ship = PlayerShip("Test", 100)
        # Find an asteroid
        asteroids = [p for p, o in g.objects.items() if o == "asteroids"]
        if asteroids:
            ax, ay = asteroids[0]
            # Run multiple ticks to catch the 30% chance
            hull_before = ship.hull
            for _ in range(20):
                g.tick(ax, ay, ship)
            # Not deterministic, but check no crash
            assert ship.hull <= hull_before

    def test_step_npc_traders_move_towards_station(self):
        g = Galaxy(seed=42)
        if g.traders and g.stations:
            t = g.traders[0]
            t.route = [0]
            t.route_index = 0
            s = g.stations[0]
            # Move trader far from station, test movement
            old_pos = (t.x, t.y)
            out = []
            g.step_npc(0, 0, PlayerShip("T", 100), out)
            # Trader should try to move towards station
            if old_pos != (t.x, t.y):
                new_dist = max(abs(t.x - s.x), abs(t.y - s.y))
                old_dist = max(abs(old_pos[0] - s.x), abs(old_pos[1] - s.y))
                # Should be closer or at station
                assert new_dist <= old_dist

    def test_reset_npc_counter(self):
        g = Galaxy()
        g.reset_npc_counter()
        assert NPCShip_id_counter == 0


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def NPCShip_id_counter_reset():
    """Reset the global NPC counter between tests."""
    import models
    models.NPCShip_id_counter = 0
