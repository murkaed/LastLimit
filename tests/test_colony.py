"""Tests for colony.py — building system, resource nodes, colony manager."""

import random
import pytest

from colony import (
    ColonyManager, Building, ResourceNode,
    BUILDING_DEFS, get_building_def, SURFACE_SIZE,
    PLANET_TYPES, random_planet_type,
)


def make_colony(planet_type="temperate") -> ColonyManager:
    """Helper to create a colony for testing."""
    c = ColonyManager("TestColony", planet_type)
    # Give some resources
    c.storage["metal"] = 50
    c.storage["electronics"] = 30
    c.storage["silicon"] = 20
    c.storage["ore"] = 20
    return c


# =========================================================================
# 1. Building
# =========================================================================


class TestBuilding:
    def test_create(self):
        b = Building("command_center", 5, 5)
        assert b.building_id == "command_center"
        assert b.name == "Command Center"
        assert b.x == 5
        assert b.y == 5
        assert b.level == 1
        assert b.active is True
        assert b.build_progress == 1.0

    def test_power_consumption(self):
        b = Building("mine", 0, 0)
        assert b.power_consumption > 0

        # Power plant produces (negative consumption)
        b2 = Building("power_plant_solar", 0, 0)
        assert b2.power_consumption < 0

    def test_workers_required(self):
        b = Building("mine", 0, 0)
        assert b.workers_required == 3
        b.level = 5
        assert b.workers_required == 4  # 3 * (1.0 + 0.4) = 4.2 -> int 4

    def test_size(self):
        b = Building("command_center", 0, 0)
        assert b.size == 2

    def test_can_upgrade(self):
        b = Building("mine", 0, 0)
        assert b.can_upgrade() is True

        for _ in range(4):
            b.level += 1
        assert b.can_upgrade() is False  # max level 5

        turret = Building("turret", 0, 0)
        assert turret.can_upgrade() is False  # turret not upgradeable

    def test_upgrade_cost(self):
        b = Building("mine", 0, 0)
        cost = b.upgrade_cost()
        assert "metal" in cost
        assert cost["metal"] >= 3  # base cost metal:3

        b.level = 3
        cost3 = b.upgrade_cost()
        assert cost3["metal"] > cost["metal"]  # higher level = higher cost

    def test_get_output_slots(self):
        b = Building("mine", 0, 0)
        slots = b.get_output_slots()
        assert len(slots) > 0
        assert slots[0][0] == "ore"
        assert slots[0][1] == 5  # base rate

        b.level = 3
        slots_lv3 = b.get_output_slots()
        assert slots_lv3[0][1] > 5  # scales with level

    def test_get_input_slots(self):
        smelter = Building("smelter", 0, 0)
        slots = smelter.get_input_slots()
        assert len(slots) == 1
        assert slots[0][0] == "ore"

        mine = Building("mine", 0, 0)
        assert len(mine.get_input_slots()) == 0  # no input for mines

    def test_building_def_exists(self):
        """All defined buildings have valid configs."""
        for bid in BUILDING_DEFS:
            bdef = get_building_def(bid)
            assert bdef, f"Building {bid} has no def"
            assert "name" in bdef
            assert "cost" in bdef
            assert "size" in bdef
            assert bdef["size"] in (1, 2, 3)


# =========================================================================
# 2. ResourceNode
# =========================================================================


class TestResourceNode:
    def test_create(self):
        rn = ResourceNode("ore", 100, 5, 10)
        assert rn.resource_id == "ore"
        assert rn.remaining == 100
        assert rn.total == 100
        assert rn.x == 5
        assert rn.y == 10
        assert rn.depleted is False

    def test_extract(self):
        rn = ResourceNode("ore", 50, 0, 0)
        taken = rn.extract(10)
        assert taken == 10
        assert rn.remaining == 40

    def test_extract_depleted(self):
        rn = ResourceNode("ore", 3, 0, 0)
        taken = rn.extract(10)
        assert taken == 3
        assert rn.remaining == 0
        assert rn.depleted is True

    def test_extract_empty(self):
        rn = ResourceNode("ore", 0, 0, 0)
        assert rn.extract(5) == 0
        assert rn.depleted is True


# =========================================================================
# 3. ColonyManager
# =========================================================================


class TestColonyManager:
    def test_create_colony(self):
        colony = make_colony("temperate")
        assert colony.name == "TestColony"
        assert colony.planet_type == "temperate"
        assert colony.surface is not None
        assert len(colony.surface) == SURFACE_SIZE
        assert len(colony.surface[0]) == SURFACE_SIZE

    def test_resource_nodes_generated(self):
        colony = make_colony("temperate")
        assert len(colony.resource_nodes) > 0  # temperate has ore, silicon, ice

    def test_place_building(self):
        colony = make_colony()
        # Find a clear spot to build
        placed = False
        for y in range(5, SURFACE_SIZE - 2):
            for x in range(5, SURFACE_SIZE - 2):
                if colony.surface[y][x] in ("plain", "hills"):
                    success = colony.place_building("mine", x, y)
                    if success:
                        assert len(colony.buildings) == 1
                        assert colony.surface[y][x] == "building"
                        placed = True
                        break
            if placed:
                break
        assert placed, "Could not find a clear spot to place a building"

    def test_place_building_out_of_bounds(self):
        colony = make_colony()
        ok, reason = colony.can_place_building("mine", -1, 5)
        assert ok is False
        assert "Out of bounds" in reason

    def test_place_building_overlap(self):
        colony = make_colony()
        # Find a clear 2x2 spot for command center
        placed_cc = False
        for y in range(5, SURFACE_SIZE - 3):
            for x in range(5, SURFACE_SIZE - 3):
                if (colony.surface[y][x] in ("plain", "hills") and
                        colony.surface[y][x+1] in ("plain", "hills") and
                        colony.surface[y+1][x] in ("plain", "hills") and
                        colony.surface[y+1][x+1] in ("plain", "hills")):
                    placed_cc = colony.place_building("command_center", x, y)
                    if placed_cc:
                        # Try to place on overlapping cell
                        ok, reason = colony.can_place_building("mine", x, y)
                        assert ok is False
                        assert "can't build" in reason.lower()
                        break
            if placed_cc:
                break
        assert placed_cc, "Could not find a clear 2x2 spot"

    def test_building_limit(self):
        colony = make_colony()
        # Command center allows 5 buildings + 3 base = 5 total (with 1 command center)
        # Actually: command_center has max_buildings_bonus=5, so max=5
        colony.place_building("command_center", 5, 5)
        # Try placing more than limit
        for i in range(8):
            ok, reason = colony.can_place_building("mine", 10 + i * 2, 5)
            if not ok:
                assert "limit" in reason or "Overlaps" in reason or "can't build" in reason
                break
            colony.place_building("mine", 10 + i * 2, 5)

    def test_get_building_at(self):
        colony = make_colony()
        # Find clear spot
        b = None
        for y in range(5, SURFACE_SIZE - 3):
            for x in range(5, SURFACE_SIZE - 3):
                if colony.surface[y][x] in ("plain", "hills"):
                    colony.place_building("command_center", x, y)
                    b = colony.get_building_at(x, y)
                    if b:
                        break
            if b:
                break
        assert b is not None
        assert b.building_id == "command_center"

        # Check within size 2
        assert colony.get_building_at(b.x + 1, b.y) is not None

        assert colony.get_building_at(10, 10) is None

    def test_remove_building(self):
        colony = make_colony()
        # Find clear spot
        for y in range(5, SURFACE_SIZE - 2):
            for x in range(5, SURFACE_SIZE - 2):
                if colony.surface[y][x] in ("plain", "hills"):
                    colony.place_building("mine", x, y)
                    break
            if colony.buildings:
                break
        assert len(colony.buildings) == 1

        bx, by = colony.buildings[0].x, colony.buildings[0].y
        removed = colony.remove_building(bx, by)
        assert removed is True
        assert len(colony.buildings) == 0
        # Surface restored
        assert colony.surface[by][bx] != "building"

    def test_command_center_bonuses(self):
        colony = make_colony()
        colony.place_building("command_center", 5, 5)
        assert colony.max_storage >= 50  # command center gives storage bonus

    def test_warehouse_bonus(self):
        colony = make_colony()
        base_storage = colony.max_storage  # 50
        # Find a clear 2x2 for command center, then a spot for warehouse
        found = False
        for y in range(5, SURFACE_SIZE - 3):
            for x in range(5, SURFACE_SIZE - 3):
                if colony.surface[y][x] in ("plain", "hills"):
                    colony.place_building("warehouse", x, y)
                    found = True
                    break
            if found:
                break
        assert colony.max_storage == base_storage + 100, (
            f"Expected {base_storage + 100}, got {colony.max_storage}")

    def test_habitat_bonus(self):
        colony = make_colony()
        assert colony.max_colonists == 0  # no buildings yet
        # Find a clear 1x1 spot for habitat
        found = False
        for y in range(5, SURFACE_SIZE - 2):
            for x in range(5, SURFACE_SIZE - 2):
                if colony.surface[y][x] in ("plain", "hills"):
                    colony.place_building("habitat", x, y)
                    found = True
                    break
            if found:
                break
        assert found, "Could not place habitat"
        assert colony.max_colonists == 10  # habitat gives +10 population

    def test_tick_basic(self):
        colony = make_colony()
        colony.place_building("command_center", 5, 5)  # no workers needed
        events = colony.tick()
        # Should run without errors
        assert isinstance(events, list)

    def test_surface_generation_different_types(self):
        """Different planet types generate different surface features."""
        for ptype in ("desert", "ice", "volcanic", "temperate", "gas_giant"):
            colony = make_colony(ptype)
            assert colony.planet_type == ptype
            assert len(colony.surface) == SURFACE_SIZE

    def test_summary_structure(self):
        colony = make_colony()
        summary = colony.summary()
        assert "name" in summary
        assert "buildings" in summary
        assert "storage_used" in summary
        assert "colonists" in summary
        assert "power" in summary

    def test_storage_summary(self):
        colony = make_colony()
        colony.storage["metal"] = 10
        s = colony.storage_summary()
        assert "metal" in s
        assert "10" in s
        assert str(sum(colony.storage.values())) in s

    def test_transfer_to_ship(self):
        colony = make_colony()
        colony.storage["metal"] = 20
        from models import CargoHold
        cargo = CargoHold(100)

        moved = colony.transfer_to_ship("metal", 10, cargo)
        assert moved == 10
        assert colony.storage.get("metal", 0) == 10
        assert cargo.has("metal") == 10

    def test_transfer_to_ship_insufficient(self):
        colony = make_colony()
        colony.storage["metal"] = 5
        from models import CargoHold
        cargo = CargoHold(100)

        moved = colony.transfer_to_ship("metal", 10, cargo)
        assert moved == 5  # only what's available
        assert colony.storage.get("metal", 0) == 0

    def test_transfer_from_ship(self):
        colony = make_colony()
        colony.storage.clear()  # start empty
        from models import CargoHold
        cargo = CargoHold(100)
        cargo.add("metal", 20)

        moved = colony.transfer_from_ship("metal", 10, cargo)
        assert moved == 10
        assert colony.storage.get("metal", 0) == 10
        assert cargo.has("metal") == 10

    def test_planet_types_config(self):
        """All planet types have required fields."""
        for ptype, info in PLANET_TYPES.items():
            assert "name" in info
            assert "habitability" in info
            assert "danger" in info
            assert "resources" in info
            assert isinstance(info["resources"], dict)

    def test_random_planet_type(self):
        """random_planet_type returns a valid type."""
        for _ in range(20):
            t = random_planet_type()
            assert t in PLANET_TYPES

    def test_place_building_water(self):
        """Cannot build on water tiles."""
        colony = make_colony("temperate")
        # Find a water tile or make one
        water_found = False
        for y in range(SURFACE_SIZE):
            for x in range(SURFACE_SIZE):
                if colony.surface[y][x] == "water":
                    ok, reason = colony.can_place_building("mine", x, y)
                    assert ok is False
                    assert "can't build" in reason.lower() or "water" in reason.lower()
                    water_found = True
                    break
            if water_found:
                break
        if not water_found:
            # Manually set a water tile
            colony.surface[10][10] = "water"
            ok, reason = colony.can_place_building("mine", 10, 10)
            assert ok is False

    def test_colony_tick_production(self):
        """Colony tick processes production from buildings."""
        colony = make_colony()
        center = SURFACE_SIZE // 2
        colony.place_building("command_center", center - 1, center - 1)
        # Place a power plant so there's energy
        colony.place_building("power_plant_solar", center + 3, center - 1)
        # Place a smelter (needs ore input)
        colony.place_building("smelter", center + 6, center - 1)
        colony.storage["ore"] = 30

        events = colony.tick()
        # Should have production events
        assert isinstance(events, list)
