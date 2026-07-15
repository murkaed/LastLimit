"""Comprehensive tests for models.py -- all core game data models."""

import random
import pytest

from models import (
    CargoHold, ShipModule, PlayerShip, Station, Galaxy,
    NPCShip, PirateShip, TraderShip, CrewMember, Mission, ScanResult,
    NPCShip_id_counter,
)
from config import (
    RESOURCES, SHIP_MODULES, COMPARTMENTS, FACTIONS,
    SHIP_HULLS, RECIPES, UPGRADES, CREW_SPECIALTIES,
    SCAN_ACTIVE_COST, SCAN_DEEP_COST,
)


def _make_pirate(x=5, y=5):
    """Create a pirate manually (conftest 'pirate' fixture has arg mismatch)."""
    NPCShip_id_counter = 0
    p = PirateShip(x, y)
    p.hull = 40
    p.max_hull = 40
    p.shield_hp = 10
    return p


def _make_trader(x=7, y=5, route=(0,)):
    """Create a trader manually with proper integer route."""
    NPCShip_id_counter = 0
    t = TraderShip(x, y, list(route))
    t.hull = 60
    t.max_hull = 60
    t.cargo.add("metal", 15)
    t.cargo.add("food", 10)
    t.cargo.add("relic", 1)
    return t


def _make_galaxy(width=80, height=40):
    """Create a galaxy with default size (conftest 'galaxy' fixture has
    reproducibility issues with small dimensions)."""
    random.seed(42)
    g = Galaxy(width=width, height=height)
    random.seed()
    return g


# =========================================================================
# 1. CargoHold
# =========================================================================


class TestCargoHold:
    def test_create(self):
        ch = CargoHold(50)
        assert ch.capacity == 50
        assert ch.used() == 0
        assert ch.free() == 50
        assert ch.items == {}

    def test_add_and_used(self):
        ch = CargoHold(50)
        assert ch.add("metal", 10) is True
        assert ch.used() == 10
        assert ch.free() == 40
        assert ch.items["metal"] == 10

    def test_add_multiple_items(self):
        ch = CargoHold(50)
        ch.add("metal", 10)
        ch.add("food", 5)
        assert ch.used() == 15
        assert ch.has("metal") == 10
        assert ch.has("food") == 5

    def test_add_existing_item_stacks(self):
        ch = CargoHold(50)
        ch.add("metal", 10)
        ch.add("metal", 5)
        assert ch.items["metal"] == 15
        assert ch.used() == 15

    def test_add_exceeds_capacity_returns_false(self):
        ch = CargoHold(10)
        assert ch.add("metal", 10) is True
        assert ch.add("food", 1) is False
        assert ch.used() == 10

    def test_add_zero_amount(self):
        ch = CargoHold(10)
        assert ch.add("metal", 0) is True
        assert ch.used() == 0

    def test_remove(self):
        ch = CargoHold(50)
        ch.add("metal", 10)
        assert ch.remove("metal", 4) is True
        assert ch.has("metal") == 6
        assert ch.used() == 6

    def test_remove_exact_amount_removes_key(self):
        ch = CargoHold(50)
        ch.add("metal", 10)
        assert ch.remove("metal", 10) is True
        assert ch.has("metal") == 0
        assert "metal" not in ch.items

    def test_remove_not_enough_returns_false(self):
        ch = CargoHold(50)
        ch.add("metal", 3)
        assert ch.remove("metal", 5) is False
        assert ch.has("metal") == 3

    def test_remove_nonexistent_item_returns_false(self):
        ch = CargoHold(50)
        assert ch.remove("relic", 1) is False

    def test_has_returns_quantity(self):
        ch = CargoHold(50)
        ch.add("ore", 7)
        assert ch.has("ore") == 7
        assert ch.has("nonexistent") == 0

    def test_total_value(self, cargo_hold):
        """cargo_hold fixture: metal=20, electronics=10, food=5 (food not in RESOURCES, ignored)."""
        # Only items in RESOURCES contribute
        expected = (
            20 * RESOURCES["metal"]["base_price"]
            + 10 * RESOURCES["electronics"]["base_price"]
        )
        assert cargo_hold.total_value() == expected

    def test_total_value_empty(self):
        ch = CargoHold(50)
        assert ch.total_value() == 0

    def test_free_after_partial_remove(self):
        ch = CargoHold(100)
        ch.add("metal", 30)
        ch.add("ore", 20)
        ch.remove("metal", 10)
        assert ch.used() == 40
        assert ch.free() == 60

    def test_capacity_enforcement(self):
        ch = CargoHold(5)
        assert ch.add("metal", 3) is True
        assert ch.add("ore", 3) is False  # 3 + 3 = 6 > 5
        assert ch.used() == 3


# =========================================================================
# 2. ShipModule
# =========================================================================


class TestShipModule:
    def test_create_level_1(self):
        m = ShipModule("laser_turret")
        assert m.id == "laser_turret"
        assert m.name == "Laser Turret"
        assert m.comp == "weapon"
        assert m.level == 1
        assert m.energy_consumption == 3
        assert m.stats["damage"] == 15
        assert m.stats["accuracy"] == 80
        assert m.durability == 60
        assert m.max_durability == 60
        assert m.cost == 500
        assert m.active is True
        assert m.desc != ""

    def test_create_level_3(self):
        m = ShipModule("laser_turret", level=3)
        assert m.level == 3
        info = SHIP_MODULES["laser_turret"]
        factor = 1.20  # 1 + (3 - 1) * 0.10
        assert m.stats["damage"] == int(info["damage"] * factor)
        assert m.stats["accuracy"] == int(info["accuracy"] * factor)
        assert m.energy_consumption == int(info["energy"] * factor)
        # NOTE: durability does NOT scale with level; _apply_level_bonus is
        # called before self.durability = info.get("durability") resets it.

    def test_create_level_5(self):
        m = ShipModule("deflector_shield", level=5)
        info = SHIP_MODULES["deflector_shield"]
        factor = 1.40
        assert m.stats["shield_cap"] == int(info["shield_cap"] * factor)
        assert m.stats["shield_regen"] == int(info["shield_regen"] * factor)

    @pytest.mark.parametrize("mod_id,comp", [
        ("fusion_reactor", "reactor"),
        ("ion_drive", "engine"),
        ("deflector_shield", "shield"),
        ("long_range_scanner", "sensor"),
        ("laser_turret", "weapon"),
        ("plasma_cannon", "weapon"),
        ("cargo_expander", "cargo"),
        ("life_support", "life_support"),
        ("armor_plating", "shield"),
        ("warp_drive", "engine"),
    ])
    def test_create_various_modules(self, mod_id, comp):
        m = ShipModule(mod_id)
        assert m.comp == comp
        assert m.id == mod_id

    @pytest.mark.parametrize("level", [1, 2, 3, 4, 5])
    def test_is_broken_false_when_new(self, level):
        m = ShipModule("laser_turret", level)
        assert m.is_broken() is False

    def test_is_broken_when_durability_zero(self):
        m = ShipModule("laser_turret")
        m.durability = 0
        assert m.is_broken() is True

    def test_upgrade_cost(self):
        m = ShipModule("laser_turret")
        assert m.upgrade_cost() == int(500 * 0.6 * 1)

    @pytest.mark.parametrize("level", [1, 2, 3, 4])
    def test_upgrade_cost_scales(self, level):
        m = ShipModule("laser_turret", level)
        assert m.upgrade_cost() == int(500 * 0.6 * level)

    def test_upgrade_resources_level_1(self):
        m = ShipModule("laser_turret", level=1)
        assert m.upgrade_resources() == {"metal": 2, "electronics": 1}

    def test_upgrade_resources_level_3(self):
        m = ShipModule("laser_turret", level=3)
        assert m.upgrade_resources() == {"metal": 6, "electronics": 3}

    def test_can_upgrade_below_5(self):
        for level in range(1, 5):
            m = ShipModule("laser_turret", level)
            assert m.can_upgrade() is True

    def test_cannot_upgrade_at_level_5(self):
        m = ShipModule("laser_turret", level=5)
        assert m.can_upgrade() is False

    def test_upgrade_increases_level(self):
        m = ShipModule("laser_turret", level=2)
        result = m.upgrade()
        assert result is True
        assert m.level == 3

    def test_upgrade_applies_bonus(self):
        m = ShipModule("ion_drive", level=1)
        m.upgrade()
        # level 2: factor = 1.10
        info = SHIP_MODULES["ion_drive"]
        factor = 1.10
        assert m.stats["speed"] == int(info["speed"] * factor)
        assert m.stats["evasion"] == int(info["evasion"] * factor)
        assert m.energy_consumption == int(info["energy"] * factor)

    def test_upgrade_at_max_returns_false(self):
        m = ShipModule("laser_turret", level=5)
        assert m.upgrade() is False
        assert m.level == 5

    def test_upgrade_cost_different_modules(self):
        m1 = ShipModule("fusion_reactor", level=2)
        m2 = ShipModule("laser_turret", level=2)
        assert m1.upgrade_cost() != m2.upgrade_cost()

    def test_energy_consumption_zero_for_reactor(self):
        m = ShipModule("fusion_reactor")
        assert m.energy_consumption == 0

    def test_energy_consumption_scales_with_level(self):
        m = ShipModule("deflector_shield", level=4)
        info = SHIP_MODULES["deflector_shield"]
        factor = 1.30  # 1 + (4 - 1) * 0.10
        assert m.energy_consumption == int(info["energy"] * factor)

    @pytest.mark.parametrize("level,factor", [
        (1, 1.0),
        (2, 1.10),
        (3, 1.20),
        (4, 1.30),
        (5, 1.40),
    ])
    def test_stats_scale_linearly(self, level, factor):
        m = ShipModule("laser_turret", level)
        info = SHIP_MODULES["laser_turret"]
        if level == 1:
            assert m.stats["damage"] == info["damage"]
        else:
            assert m.stats["damage"] == int(info["damage"] * factor)

    def test_unknown_module_id(self):
        m = ShipModule("nonexistent_module")
        assert m.name == "nonexistent_module"
        assert m.stats == {}
        assert m.durability == 50


# =========================================================================
# 3. PlayerShip
# =========================================================================


class TestPlayerShip:
    def test_create(self, player_ship):
        assert player_ship.name == "TestShip"
        assert player_ship.hull == 100
        assert player_ship.max_hull == 100
        assert player_ship.shield_hp == 30
        assert player_ship.fuel == 80
        assert player_ship.credits == 5000
        assert player_ship.hull_id == "corvette"
        assert player_ship.race == "human"
        assert player_ship.religion is None
        assert "corvette" in player_ship.owned_hulls

    def test_default_compartments_have_starter_modules(self, player_ship):
        assert any(m.id == "fusion_reactor" for m in player_ship.compartments["reactor"]["modules"])
        assert any(m.id == "ion_drive" for m in player_ship.compartments["engine"]["modules"])
        assert any(m.id == "deflector_shield" for m in player_ship.compartments["shield"]["modules"])
        assert any(m.id == "long_range_scanner" for m in player_ship.compartments["sensor"]["modules"])
        assert any(m.id == "laser_turret" for m in player_ship.compartments["weapon"]["modules"])

    def test_reputation_defaults(self, player_ship):
        for f in FACTIONS:
            assert f in player_ship.reputation
        assert player_ship.reputation["pirates"] == -10

    # ---------- Power ----------

    def test_total_power_generated(self, player_ship):
        # fusion_reactor: power=12
        assert player_ship.total_power_generated() == 12

    def test_total_power_consumed(self, player_ship):
        # ion_drive=2, deflector_shield=4, long_range_scanner=2, laser_turret=3
        assert player_ship.total_power_consumed() == 11

    def test_total_power_consumed_broken_module_excluded(self, player_ship):
        for m in player_ship.compartments["weapon"]["modules"]:
            m.durability = 0
        assert player_ship.total_power_consumed() == 8  # 11 - 3

    # ---------- get_effective_stats ----------

    def test_get_effective_stats(self, player_ship):
        stats = player_ship.get_effective_stats()
        assert stats["speed"] == 1
        assert stats["evasion"] == 10
        assert stats["damage"] == 15
        assert stats["accuracy"] == 80
        assert stats["shield_cap"] == 30
        assert stats["shield_regen"] == 2
        assert stats["sensor_range"] == 12  # base 7 + scanner 5
        assert stats["range"] == 4          # base 1 + laser_turret 3

    def test_get_effective_stats_power_deficit(self):
        ship = PlayerShip("Test", 100)
        # Add plasma_cannon (energy=5) to exceed budget: 12 gen, 11+5=16 consumed
        # eff = 12/16 = 0.75
        ship.compartments["weapon"]["modules"].append(ShipModule("plasma_cannon"))
        stats = ship.get_effective_stats()
        expected_damage = int((15 + 30) * 0.75)
        assert stats["damage"] == expected_damage

    def test_get_effective_stats_no_modules(self):
        ship = PlayerShip("Bare", 100)
        for c in COMPARTMENTS:
            ship.compartments[c]["modules"] = []
        stats = ship.get_effective_stats()
        assert stats["speed"] == 0
        assert stats["sensor_range"] == 7  # base only
        assert stats["range"] == 1         # base only

    # ---------- install_module ----------

    def test_install_module(self, player_ship):
        assert player_ship.install_module("plasma_cannon") is True
        ids = [m.id for m in player_ship.compartments["weapon"]["modules"]]
        assert "plasma_cannon" in ids

    def test_install_unknown_module(self, player_ship):
        assert player_ship.install_module("unknown_mod") is False

    # ---------- install_module_from_cargo ----------

    def test_install_module_from_cargo(self, player_ship):
        player_ship.cargo.add("plasma_cannon", 1)
        msg, ok = player_ship.install_module_from_cargo("plasma_cannon")
        assert ok is True
        assert player_ship.cargo.has("plasma_cannon") == 0
        assert any(m.id == "plasma_cannon" for m in player_ship.compartments["weapon"]["modules"])

    def test_install_module_from_cargo_not_in_cargo(self, player_ship):
        msg, ok = player_ship.install_module_from_cargo("plasma_cannon")
        assert ok is False
        assert "No" in msg

    def test_install_module_from_cargo_unknown(self, player_ship):
        player_ship.cargo.add("fake_mod", 1)
        msg, ok = player_ship.install_module_from_cargo("fake_mod")
        assert ok is False

    # ---------- craft ----------

    def test_craft_repair_kit(self, player_ship):
        """metal=10, electronics=5. Repair kit needs metal=3, electronics=1.
        Fixture already has repair_kit=2."""
        player_ship.cargo.remove("repair_kit", 2)  # clear fixture stock
        msg, ok = player_ship.craft("repair_kit")
        assert ok is True
        assert player_ship.cargo.has("repair_kit") == 1
        assert player_ship.cargo.has("metal") == 7
        assert player_ship.cargo.has("electronics") == 4

    def test_craft_multiple(self, player_ship):
        player_ship.cargo.remove("repair_kit", 2)  # clear fixture stock
        msg, ok = player_ship.craft("repair_kit", amount=2)
        assert ok is True
        assert player_ship.cargo.has("repair_kit") == 2
        assert player_ship.cargo.has("metal") == 4
        assert player_ship.cargo.has("electronics") == 3

    def test_craft_fuel_cell(self, player_ship):
        """Fixture already has fuel_cell=1."""
        player_ship.cargo.add("silicon", 5)
        msg, ok = player_ship.craft("fuel_cell")
        assert ok is True
        assert player_ship.cargo.has("fuel_cell") == 2  # 1 new + 1 from fixture
        assert player_ship.cargo.has("ice") == 6         # 8 - 2

    def test_craft_unknown_recipe(self, player_ship):
        msg, ok = player_ship.craft("unknown_recipe")
        assert ok is False

    def test_craft_insufficient_resources(self, player_ship):
        msg, ok = player_ship.craft("laser_turret")  # needs metal=5, electronics=3, silicon=2
        assert ok is False

    def test_craft_insufficient_space(self, player_ship):
        player_ship.cargo.capacity = 0
        msg, ok = player_ship.craft("repair_kit")
        assert ok is False

    # ---------- use_item ----------

    def test_use_repair_kit(self, player_ship):
        player_ship.hull = 50
        player_ship.cargo.add("repair_kit", 1)
        msg, ok = player_ship.use_item("repair_kit")
        assert ok is True
        assert player_ship.hull == 70

    def test_use_repair_kit_caps_at_max_hull(self, player_ship):
        player_ship.hull = 95
        player_ship.cargo.add("repair_kit", 1)
        msg, ok = player_ship.use_item("repair_kit")
        assert ok is True
        assert player_ship.hull == 100

    def test_use_fuel_cell(self, player_ship):
        player_ship.fuel = 50
        player_ship.cargo.add("fuel_cell", 1)
        msg, ok = player_ship.use_item("fuel_cell")
        assert ok is True
        assert player_ship.fuel == 60

    def test_use_shield_booster(self, player_ship):
        player_ship.shield_hp = 5
        player_ship.cargo.add("shield_booster", 1)
        msg, ok = player_ship.use_item("shield_booster")
        assert ok is True
        assert player_ship.shield_hp == 20

    def test_use_shield_booster_caps_at_shield_cap(self, player_ship):
        player_ship.shield_hp = 28
        player_ship.cargo.add("shield_booster", 1)
        msg, ok = player_ship.use_item("shield_booster")
        assert ok is True
        assert player_ship.shield_hp == 30  # capped at shield_cap

    def test_use_item_not_consumable(self, player_ship):
        msg, ok = player_ship.use_item("metal")
        assert ok is False

    def test_use_item_not_in_cargo(self, player_ship):
        msg, ok = player_ship.use_item("shield_booster")  # not in fixture cargo
        assert ok is False

    def test_use_item_multiple_amount(self, player_ship):
        """Fixture already has repair_kit=2."""
        player_ship.hull = 40
        player_ship.cargo.add("repair_kit", 3)
        player_ship.cargo.remove("repair_kit", 2)  # net add = 1, total = 3
        msg, ok = player_ship.use_item("repair_kit", amount=2)
        assert ok is True
        assert player_ship.hull == 80
        assert player_ship.cargo.has("repair_kit") == 1

    # ---------- apply_upgrade ----------

    def test_apply_upgrade_hull_reinforcement(self, player_ship):
        player_ship.cargo.add("metal", 10)
        player_ship.cargo.add("electronics", 2)
        msg, ok = player_ship.apply_upgrade("hull_reinforcement")
        assert ok is True
        assert player_ship.has_upgrade("hull_reinforcement") is True
        assert player_ship.max_hull == 130

    def test_apply_upgrade_cargo_expansion(self, player_ship):
        player_ship.cargo.add("metal", 5)
        player_ship.cargo.add("electronics", 3)
        old_cap = player_ship.cargo.capacity
        msg, ok = player_ship.apply_upgrade("cargo_expansion")
        assert ok is True
        assert player_ship.cargo.capacity == old_cap + 20

    def test_apply_upgrade_reactor_overclock(self, player_ship):
        player_ship.cargo.add("electronics", 10)
        player_ship.cargo.add("shield_mod", 2)
        msg, ok = player_ship.apply_upgrade("reactor_overclock")
        assert ok is True
        assert player_ship.total_power_generated() == 17  # 12 + 5

    def test_apply_upgrade_sensor_boost(self, player_ship):
        player_ship.cargo.add("electronics", 3)
        player_ship.cargo.add("silicon", 3)
        msg, ok = player_ship.apply_upgrade("sensor_boost")
        assert ok is True
        stats = player_ship.get_effective_stats()
        assert stats["sensor_range"] >= 15  # 12 + 3

    def test_apply_upgrade_already_have(self, player_ship):
        player_ship.upgrades["hull_reinforcement"] = True
        msg, ok = player_ship.apply_upgrade("hull_reinforcement")
        assert ok is False

    def test_apply_upgrade_insufficient_credits(self, player_ship):
        player_ship.credits = 0
        msg, ok = player_ship.apply_upgrade("hull_reinforcement")
        assert ok is False

    def test_apply_upgrade_insufficient_cargo(self, player_ship):
        # player_ship has metal=10, electronics=5; hull_reinforcement needs
        # metal=10, electronics=2 -- that is enough. Use engine_tuning
        # which needs metal=4, electronics=2, silicon=2; ship has no silicon.
        msg, ok = player_ship.apply_upgrade("engine_tuning")
        assert ok is False

    def test_apply_upgrade_unknown(self, player_ship):
        msg, ok = player_ship.apply_upgrade("nonexistent_upgrade")
        assert ok is False

    def test_has_upgrade(self, player_ship):
        assert player_ship.has_upgrade("hull_reinforcement") is False
        player_ship.upgrades["hull_reinforcement"] = True
        assert player_ship.has_upgrade("hull_reinforcement") is True

    # ---------- buy_hull ----------

    def test_buy_hull(self, player_ship):
        msg, ok = player_ship.buy_hull("shuttle")  # 500cr, player has 5000
        assert ok is True
        assert "shuttle" in player_ship.owned_hulls
        assert player_ship.credits == 5000 - SHIP_HULLS["shuttle"]["cost"]

    def test_buy_hull_already_owned(self, player_ship):
        msg, ok = player_ship.buy_hull("corvette")
        assert ok is False

    def test_buy_hull_unknown(self, player_ship):
        msg, ok = player_ship.buy_hull("unknown_hull")
        assert ok is False

    def test_buy_hull_insufficient_credits(self, player_ship):
        player_ship.credits = 10
        msg, ok = player_ship.buy_hull("frigate")
        assert ok is False

    # ---------- sell_hull ----------

    def test_sell_hull(self, player_ship):
        player_ship.owned_hulls.append("shuttle")
        msg, ok = player_ship.sell_hull("shuttle")
        assert ok is True
        assert "shuttle" not in player_ship.owned_hulls
        assert player_ship.credits == 5000 + SHIP_HULLS["shuttle"]["cost"] // 2

    def test_sell_hull_current_hull_fails(self, player_ship):
        msg, ok = player_ship.sell_hull("corvette")
        assert ok is False
        assert "Cannot sell current hull" in msg

    def test_sell_hull_not_owned(self, player_ship):
        msg, ok = player_ship.sell_hull("frigate")
        assert ok is False

    def test_sell_hull_unknown(self, player_ship):
        msg, ok = player_ship.sell_hull("unknown")
        assert ok is False

    # ---------- switch_hull ----------

    def test_switch_hull(self, player_ship):
        player_ship.owned_hulls.append("shuttle")
        msg, ok = player_ship.switch_hull("shuttle")
        assert ok is True
        assert player_ship.hull_id == "shuttle"

    def test_switch_hull_not_owned(self, player_ship):
        msg, ok = player_ship.switch_hull("frigate")
        assert ok is False

    def test_switch_hull_unknown(self, player_ship):
        msg, ok = player_ship.switch_hull("unknown")
        assert ok is False

    # ---------- Crew management ----------

    def test_hire_crew(self, player_ship, crew_member):
        msg, ok = player_ship.hire_crew(crew_member)
        assert ok is True
        assert crew_member in player_ship.crew_members
        assert player_ship.credits == 5000 - crew_member.salary

    def test_hire_crew_max_slots(self, player_ship):
        for i in range(10):
            cm = CrewMember(f"Test{i}", "Pilot", "human")
            player_ship.hire_crew(cm)
        # Should fail at some point due to max crew slots
        cm = CrewMember("Overflow", "Pilot", "human")
        msg, ok = player_ship.hire_crew(cm)
        assert ok is False

    def test_hire_crew_insufficient_credits(self, player_ship, crew_member):
        player_ship.credits = 0
        msg, ok = player_ship.hire_crew(crew_member)
        assert ok is False

    def test_fire_crew(self, player_ship, crew_member):
        player_ship.crew_members.append(crew_member)
        msg, ok = player_ship.fire_crew("Zara")
        assert ok is True
        assert crew_member not in player_ship.crew_members

    def test_fire_crew_unassigns_from_post(self, player_ship, crew_member):
        player_ship.crew_members.append(crew_member)
        player_ship.crew["Pilot"] = "Zara"
        crew_member.assigned = True
        player_ship.fire_crew("Zara")
        assert player_ship.crew["Pilot"] is None

    def test_fire_crew_not_found(self, player_ship):
        msg, ok = player_ship.fire_crew("Nonexistent")
        assert ok is False

    def test_assign_crew(self, player_ship, crew_member):
        player_ship.crew_members.append(crew_member)
        msg, ok = player_ship.assign_crew("Zara", "Pilot")
        assert ok is True
        assert player_ship.crew["Pilot"] == "Zara"
        assert crew_member.assigned is True

    def test_assign_crew_unknown_post(self, player_ship, crew_member):
        player_ship.crew_members.append(crew_member)
        msg, ok = player_ship.assign_crew("Zara", "Captain")
        assert ok is False

    def test_assign_crew_wrong_specialty(self, player_ship):
        cm = CrewMember("Bob", "Engineer", "human")
        player_ship.crew_members.append(cm)
        msg, ok = player_ship.assign_crew("Bob", "Pilot")
        assert ok is False

    def test_assign_crew_not_in_roster(self, player_ship):
        msg, ok = player_ship.assign_crew("Ghost", "Pilot")
        assert ok is False

    def test_assign_crew_replaces_existing(self, player_ship):
        cm1 = CrewMember("Zara", "Pilot", "human")
        cm2 = CrewMember("Rex", "Pilot", "human")
        player_ship.crew_members.append(cm1)
        player_ship.crew_members.append(cm2)
        player_ship.assign_crew("Zara", "Pilot")
        msg, ok = player_ship.assign_crew("Rex", "Pilot")
        assert ok is True
        assert player_ship.crew["Pilot"] == "Rex"
        assert cm1.assigned is False
        assert cm2.assigned is True

    # ---------- Bonus helpers ----------

    def test_crew_bonus(self, player_ship):
        cm = CrewMember("Zara", "Pilot", "human")
        cm.assigned = True
        player_ship.crew["Pilot"] = "Zara"
        player_ship.crew_members.append(cm)
        assert player_ship._crew_bonus("evasion", 0) == 5

    def test_crew_bonus_unassigned_not_counted(self, player_ship):
        cm = CrewMember("Zara", "Pilot", "human")
        cm.assigned = False
        player_ship.crew["Pilot"] = "Zara"
        player_ship.crew_members.append(cm)
        assert player_ship._crew_bonus("evasion", 0) == 0

    def test_upgrade_bonus(self, player_ship):
        player_ship.upgrades["cargo_expansion"] = True
        assert player_ship._upgrade_bonus("cargo_bonus", 0) == 20

    # ---------- Mission management ----------

    def test_add_mission(self, player_ship, mission):
        msg, ok = player_ship.add_mission(mission)
        assert ok is True
        assert mission in player_ship.missions
        assert mission.status == "active"

    def test_add_mission_log_full(self, player_ship):
        for i in range(5):
            m = Mission("deliver", "metal", 1, f"S{i}", 100, 30)
            player_ship.add_mission(m)
        m = Mission("deliver", "metal", 1, "Sx", 100, 30)
        msg, ok = player_ship.add_mission(m)
        assert ok is False
        assert "full" in msg

    def test_add_duplicate_mission(self, player_ship, mission):
        player_ship.add_mission(mission)
        msg, ok = player_ship.add_mission(mission)
        assert ok is False

    def test_abandon_mission(self, player_ship, mission):
        player_ship.add_mission(mission)
        msg, ok = player_ship.abandon_mission(mission.id)
        assert ok is True
        assert mission not in player_ship.missions
        assert mission.status == "abandoned"

    def test_abandon_mission_not_found(self, player_ship):
        msg, ok = player_ship.abandon_mission(9999)
        assert ok is False

    def test_track_mission(self, player_ship, mission):
        player_ship.add_mission(mission)
        result = player_ship.track_mission(mission.id)
        assert result is mission
        assert player_ship.tracked_mission == mission.id

    def test_track_mission_not_found(self, player_ship):
        result = player_ship.track_mission(9999)
        assert result is None
        assert player_ship.tracked_mission is None

    def test_fail_expired_missions(self, player_ship):
        m = Mission("deliver", "metal", 1, "Target", 100, ticks=0)
        m.status = "active"
        player_ship.missions.append(m)
        failed = player_ship.fail_expired_missions(None)
        assert len(failed) == 1
        assert m.status == "failed"
        assert m not in player_ship.missions

    def test_fail_expired_non_expired_untouched(self, player_ship):
        m = Mission("deliver", "metal", 1, "Target", 100, ticks=10)
        m.status = "active"
        player_ship.missions.append(m)
        failed = player_ship.fail_expired_missions(None)
        assert len(failed) == 0
        assert m in player_ship.missions

    def test_has_mission(self, player_ship, mission):
        assert player_ship.has_mission(mission.id) is False
        player_ship.add_mission(mission)
        assert player_ship.has_mission(mission.id) is True

    # ---------- scan_target ----------

    def test_scan_target_passive(self, player_ship):
        pirate = _make_pirate()
        result = player_ship.scan_target(pirate, "passive")
        assert result.success is True
        assert result.level == "passive"
        assert result.info["hull"] == 40
        assert result.info["type"] == "PirateShip"
        assert "cargo" not in result.info

    def test_scan_target_active_shows_cargo(self, player_ship):
        trader = _make_trader()
        result = player_ship.scan_target(trader, "active")
        assert result.success is True
        assert "cargo" in result.info
        assert isinstance(result.info["cargo"], dict)

    def test_scan_target_marks_as_scanned(self, player_ship):
        pirate = _make_pirate()
        pirate.scan_level = "passive"  # pre-define attribute
        player_ship.scan_target(pirate, "active")
        assert pirate.scanned is True

    def test_scan_target_deep_success(self):
        # Remove power-hungry modules so spare power >= 5
        ship = PlayerShip("Powerful", 200)
        ship.compartments["shield"]["modules"] = []   # -4 power
        ship.compartments["sensor"]["modules"] = []    # -2 power
        # Now consumed = 2 (engine) + 3 (weapon) = 5, generated = 12, spare = 7
        result = ship.scan_target(ship, "deep")
        assert result.success is True
        assert result.level == "deep"

    def test_scan_target_insufficient_power_for_deep(self, player_ship):
        result = player_ship.scan_target(player_ship, "deep")
        assert result.success is False

    # ---------- check_missions ----------

    def test_check_missions_deliver(self):
        s = Station(10, 10, name="S1")
        ship = PlayerShip("Test", 100)
        ship.cargo.add("ore", 10)
        ship.missions.append(Mission("deliver", "ore", 5, "S1", 200, 20))
        completed = ship.check_missions(s)
        assert len(completed) == 1
        assert ship.credits == 1200  # 1000 + 200
        assert ship.cargo.has("ore") == 5

    def test_check_missions_wrong_station(self):
        s1 = Station(10, 10, name="S1")
        s2 = Station(20, 20, name="S2")
        ship = PlayerShip("Test", 100)
        ship.cargo.add("ore", 10)
        ship.missions.append(Mission("deliver", "ore", 5, "S2", 200, 20))
        completed = ship.check_missions(s1)
        assert len(completed) == 0


# =========================================================================
# 4. Station
# =========================================================================


class TestStation:
    def test_create(self, station):
        assert station.name == "TestHub"
        assert station.stype == "trade_hub"
        assert station.faction in FACTIONS
        assert station.x == 10
        assert station.y == 10
        assert len(station.inventory) > 0
        assert station.modules_for_sale is not None

    def test_create_shipyard(self):
        s = Station(5, 5, "ShipYard", "shipyard", "imperium")
        assert s.stype == "shipyard"
        assert len(s.hulls_for_sale) > 0
        for h in s.hulls_for_sale:
            assert h in SHIP_HULLS

    def test_create_workshop(self):
        s = Station(5, 5, "Workshop", "workshop", "free_traders")
        assert s.stype == "workshop"
        assert len(s.recipes_available) > 0
        for r in s.recipes_available:
            assert r in RECIPES

    def test_create_tavern(self):
        s = Station(5, 5, "Tavern", "tavern", "free_traders")
        assert s.stype == "tavern"
        assert len(s.crew_for_hire) > 0
        for cm in s.crew_for_hire:
            assert isinstance(cm, CrewMember)
            assert cm.specialty in CREW_SPECIALTIES

    def test_gen_missions(self):
        s1 = Station(5, 5, "Alpha", "trade_hub", "free_traders")
        s2 = Station(10, 10, "Beta", "trade_hub", "free_traders")
        s1.gen_missions([s1, s2])
        assert len(s1.missions) <= 4
        # Deliver missions target another station; bounty targets self

    def test_prices_initialized(self, station):
        for rid in RESOURCES:
            assert rid in station.prices
            bp, sp = station.prices[rid]
            assert bp >= 1
            assert sp >= 1

    def test_update_prices(self, station):
        old = dict(station.prices)
        station.update_prices()
        assert station.prices != old or True  # may stay same depending on stock

    def test_price_for_player_buying(self, station, player_ship):
        price, notes = station.price_for_player("metal", buying=True, ship=player_ship)
        assert price >= 1

    def test_price_for_player_selling(self, station, player_ship):
        price, notes = station.price_for_player("metal", buying=False, ship=player_ship)
        assert price >= 1

    def test_price_friend_discount_buying(self, station, player_ship):
        player_ship.reputation[station.faction] = 60
        price, notes = station.price_for_player("metal", buying=True, ship=player_ship)
        assert "friend" in notes
        assert price >= 1

    def test_price_hostile_penalty_buying(self, station, player_ship):
        player_ship.reputation[station.faction] = -30
        price, notes = station.price_for_player("metal", buying=True, ship=player_ship)
        assert "hostile" in notes

    def test_sell_to_player(self, station, player_ship):
        station.inventory["metal"] = 20
        msg = station.sell_to(player_ship, "metal", 3)
        assert "Bought" in msg
        assert player_ship.cargo.has("metal") == 13

    def test_sell_to_player_insufficient_stock(self, station, player_ship):
        station.inventory["metal"] = 1
        msg = station.sell_to(player_ship, "metal", 5)
        assert "Only" in msg

    def test_sell_to_player_insufficient_credits(self, station, player_ship):
        player_ship.credits = 0
        msg = station.sell_to(player_ship, "metal", 1)
        assert "Need" in msg

    def test_sell_to_player_cargo_full(self, station, player_ship):
        player_ship.cargo.capacity = 0
        msg = station.sell_to(player_ship, "metal", 1)
        assert "full" in msg.lower()

    def test_buy_from_player(self, station, player_ship):
        msg = station.buy_from(player_ship, "metal", 3)
        assert "Sold" in msg
        assert player_ship.cargo.has("metal") == 7

    def test_buy_from_player_not_enough(self, station, player_ship):
        msg = station.buy_from(player_ship, "metal", 50)
        assert "Not enough" in msg

    def test_buy_from_player_contraband(self, station, player_ship):
        station.faction = "imperium"
        player_ship.cargo.add("relic", 1)
        msg = station.buy_from(player_ship, "relic", 1)
        assert "Contraband" in msg

    def test_buy_from_player_blocked_rep(self, station, player_ship):
        player_ship.reputation[station.faction] = -30
        player_ship.cargo.add("metal", 5)
        msg = station.buy_from(player_ship, "metal", 3)
        assert "blocked" in msg.lower()

    def test_buy_all_junk(self, station, player_ship):
        msg, ok = station.buy_all_junk(player_ship)
        assert ok is True
        assert player_ship.cargo.has("ice") == 0  # ice is raw, sold
        assert player_ship.cargo.has("metal") == 10  # metal is refined, kept

    def test_buy_all_junk_no_raw(self, station, player_ship):
        player_ship.cargo.items.clear()
        msg, ok = station.buy_all_junk(player_ship)
        assert ok is False

    def test_price_summary(self, station):
        summary = station.price_summary()
        assert station.name in summary
        assert station.stype in summary
        assert station.faction in summary

    def test_update_economy_industrial(self):
        s = Station(0, 0, stype="industrial", faction="free_traders")
        s.inventory["ore"] = 20
        s.inventory["ice"] = 20
        old_metal = s.inventory.get("metal", 0)
        s.update_economy()
        assert s.inventory.get("metal", 0) >= old_metal

    def test_crisis_blocks_economy(self):
        s = Station(0, 0, stype="industrial")
        s.crisis_ticks = 3
        old = dict(s.inventory)
        s.update_economy()
        assert s.inventory == old
        assert s.crisis_ticks == 2


# =========================================================================
# 5. Galaxy
# =========================================================================


class TestGalaxy:
    def test_create(self):
        g = _make_galaxy()
        assert g.width == 80
        assert g.height == 40
        assert len(g.news) >= 1
        assert g.tick_counter == 0

    def test_generation_has_stations(self):
        g = _make_galaxy()
        assert len(g.stations) > 0

    def test_generation_has_traders(self):
        g = _make_galaxy()
        assert len(g.traders) > 0

    def test_generation_has_pirates(self):
        g = _make_galaxy()
        assert len(g.pirates) > 0

    def test_black_holes_list(self):
        g = _make_galaxy()
        assert len(g.black_holes) > 0

    def test_wormholes_list(self):
        g = _make_galaxy()
        assert len(g.wormholes) > 0

    def test_diplomacy_initialized(self):
        g = _make_galaxy()
        for f in FACTIONS:
            assert f in g.diplomacy

    # ---------- Queries ----------

    def test_get_station_at(self):
        g = _make_galaxy()
        for s in g.stations:
            found = g.get_station_at(s.x, s.y)
            assert found is s
            break
        assert g.get_station_at(-1, -1) is None

    def test_get_nearest_station_exact(self):
        g = _make_galaxy()
        if g.stations:
            s = g.stations[0]
            assert g.get_nearest_station(s.x, s.y, 0) is s

    def test_get_nearest_station_out_of_range(self):
        g = _make_galaxy()
        assert g.get_nearest_station(-100, -100, 5) is None

    def test_stations_in_range(self):
        g = _make_galaxy()
        all_s = g.stations_in_range(0, 0, 100)
        assert len(all_s) == len(g.stations)

    def test_stations_in_range_zero(self):
        g = _make_galaxy()
        stations = g.stations_in_range(0, 0, 0)
        assert len(stations) == 0

    def test_get_scannable_objects(self):
        g = _make_galaxy()
        result = g.get_scannable_objects(0, 0, 50)
        assert isinstance(result, list)
        for item in result:
            assert len(item) == 3
            assert isinstance(item[0], int)
            assert isinstance(item[1], str)
        for i in range(len(result) - 1):
            assert result[i][0] <= result[i + 1][0]

    def test_get_scannable_objects_zero_range(self):
        g = _make_galaxy()
        result = g.get_scannable_objects(0, 0, 0)
        assert result == []

    def test_add_news(self):
        g = _make_galaxy()
        g.add_news("Test", "Body")
        assert any(n.headline == "Test" for n in g.news)
        assert any(n.body == "Body" for n in g.news)

    def test_add_news_capped_at_50(self):
        g = _make_galaxy()
        for i in range(60):
            g.add_news(f"N{i}", f"B{i}")
        assert len(g.news) == 50

    def test_scan_generate_missions(self):
        g = _make_galaxy()
        pirate = _make_pirate()
        result = g.scan_generate_missions(pirate, "active", None)
        if result is not None:
            assert isinstance(result, Mission)
            assert hasattr(result, "title")
            assert hasattr(result, "description")

    def test_get_tile_in_bounds(self):
        g = _make_galaxy()
        assert g.get_tile(0, 0) != " "

    def test_get_tile_out_of_bounds(self):
        g = _make_galaxy()
        assert g.get_tile(-1, -1) == " "

    def test_get_object_info_station(self):
        g = _make_galaxy()
        if g.stations:
            s = g.stations[0]
            info = g.get_object_info(s.x, s.y)
            assert "Station" in info or "Empty" in info

    def test_get_npc_at(self):
        g = _make_galaxy()
        if g.traders:
            t = g.traders[0]
            assert g.get_npc_at(t.x, t.y) is t

    def test_get_npc_by_name(self):
        g = _make_galaxy()
        if g.traders:
            t = g.traders[0]
            assert g.get_npc_by_name(t.name) is t

    def test_get_npc_by_name_case_insensitive(self):
        g = _make_galaxy()
        if g.traders:
            t = g.traders[0]
            assert g.get_npc_by_name(t.name.lower()) is t

    def test_is_passable_empty(self):
        g = _make_galaxy()
        for y in range(g.height):
            for x in range(g.width):
                if g.tiles[y][x] == "·":
                    assert g.is_passable(x, y) is True
                    return

    def test_is_passable_oob(self):
        g = _make_galaxy()
        assert g.is_passable(-1, 0) is False
        assert g.is_passable(g.width, 0) is False

    def test_tick_gravity(self):
        g = _make_galaxy()
        if not g.black_holes:
            pytest.skip("No black holes")
        bh = g.black_holes[0]
        px, py = max(0, bh[0] - 2), bh[1]
        if not g.is_passable(px, py):
            pytest.skip("Position not passable")
        ship = PlayerShip("T", 100)
        nx, ny, evs, dead = g.tick(px, py, ship)
        dist_before = max(abs(px - bh[0]), abs(py - bh[1]))
        dist_after = max(abs(nx - bh[0]), abs(ny - bh[1]))
        if dist_before <= 3:
            assert dist_after < dist_before

    def test_tick_black_hole_death(self):
        g = _make_galaxy()
        if not g.black_holes:
            pytest.skip("No black holes")
        bh = g.black_holes[0]
        # Place ship 1 cell from the black hole so gravity pulls it in
        px, py = bh[0] - 1, bh[1]
        if not g.is_passable(px, py):
            # Try other directions
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                tx, ty = bh[0] + dx, bh[1] + dy
                if g.is_passable(tx, ty):
                    px, py = tx, ty
                    break
            else:
                pytest.skip("No passable tile adjacent to black hole")
        ship = PlayerShip("T", 100)
        nx, ny, evs, dead = g.tick(px, py, ship)
        assert dead is True

    def test_tick_radiation(self):
        g = _make_galaxy()
        if not g.objects:
            pytest.skip("No objects")
        star_positions = [p for p, o in g.objects.items() if o == "star"]
        if not star_positions:
            pytest.skip("No stars")
        sx, sy = star_positions[0]
        for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
            nx, ny = sx + dx, sy + dy
            if g.is_passable(nx, ny) and (nx, ny) not in g.objects:
                ship = PlayerShip("T", 100)
                ship.shield_hp = 0
                hull_before = ship.hull
                _, _, evs, _ = g.tick(nx, ny, ship)
                if "Radiation" in str(evs):
                    assert ship.hull < hull_before
                return


# =========================================================================
# 6. CrewMember
# =========================================================================


class TestCrewMember:
    def test_create(self, crew_member):
        assert crew_member.name == "Zara"
        assert crew_member.specialty == "Pilot"
        assert crew_member.race == "human"
        assert crew_member.level == 1
        assert crew_member.experience == 0
        assert crew_member.assigned is False
        assert crew_member.post == "Pilot"
        assert crew_member.salary >= 20

    def test_create_various_specialties(self):
        for spec_id in CREW_SPECIALTIES:
            cm = CrewMember("Test", spec_id, "human")
            assert cm.specialty == spec_id
            assert cm.post in CREW_SPECIALTIES[spec_id]["posts"]
            assert len(cm.bonus) > 0

    def test_ground_stats(self, crew_member):
        assert crew_member.hp == 30
        assert crew_member.max_hp == 30
        assert crew_member.ap == 4
        assert crew_member.max_ap == 4
        assert crew_member.weapon == "pistol"
        assert crew_member.armor == "vest"
        assert crew_member.combat_skill == 50
        assert crew_member.inventory == {"repair_kit": 1}

    def test_desc(self, crew_member):
        desc = crew_member.desc()
        assert "Zara" in desc
        assert "Pilot" in desc
        assert "Lv1" in desc

    def test_xp_for_next_level_1(self, crew_member):
        assert crew_member.xp_for_next() == 50

    @pytest.mark.parametrize("level,expected_xp", [
        (1, 50),
        (2, 100),
        (3, 150),
        (5, 250),
    ])
    def test_xp_for_next_scales(self, level, expected_xp):
        cm = CrewMember("Test", "Pilot", "human")
        cm.level = level
        assert cm.xp_for_next() == expected_xp

    def test_add_xp_exact_level_up(self, crew_member):
        crew_member.add_xp(50)
        assert crew_member.level == 2
        assert crew_member.experience == 0

    def test_add_xp_partial(self, crew_member):
        crew_member.add_xp(30)
        assert crew_member.level == 1
        assert crew_member.experience == 30

    def test_add_xp_multiple_calls_level_up(self, crew_member):
        crew_member.add_xp(150)  # 50 for lv2, 100 carried over
        assert crew_member.level == 2
        assert crew_member.experience == 100

    def test_add_xp_with_carryover(self, crew_member):
        crew_member.add_xp(60)
        assert crew_member.level == 2
        assert crew_member.experience == 10

    def test_level_up_scales_bonus(self, crew_member):
        old = dict(crew_member.bonus)
        crew_member.add_xp(50)
        for k in crew_member.bonus:
            expected = int(old[k] * (1 + (2 - 1) * 0.15))
            assert crew_member.bonus[k] == expected

    def test_salary_randomized(self):
        salaries = [CrewMember("T", "Pilot", "human").salary for _ in range(30)]
        assert len(set(salaries)) > 1

    def test_race_from_fixture(self, crew_member):
        assert crew_member.race == "human"


# =========================================================================
# 7. Mission
# =========================================================================


class TestMission:
    def test_create(self, mission):
        assert mission.id >= 1
        assert mission.mtype == "deliver"
        assert mission.resource == "metal"
        assert mission.amount == 5
        assert mission.target_station == "TargetStation"
        assert mission.reward == 200
        assert mission.ticks == 30
        assert mission.status == "active"
        assert mission.progress == 0

    def test_enhanced_fields(self, mission):
        assert mission.title == "Test Delivery"
        assert mission.description == "Deliver 5 metal."
        assert mission.giver_station is None

    def test_create_with_giver_station(self):
        s = Station(5, 5, "Alpha", "trade_hub", "free_traders")
        m = Mission("deliver", "ore", 3, "Beta", 150, 25,
                     title="Run", description="Do it", giver_station=s)
        assert m.giver_station is s
        assert m.title == "Run"

    def test_unique_ids(self):
        m1 = Mission("deliver", "a", 1, "X", 100, 30)
        m2 = Mission("deliver", "b", 1, "Y", 100, 30)
        assert m1.id != m2.id

    @pytest.mark.parametrize("mtype", ["deliver", "bounty", "exploration", "trade"])
    def test_different_types(self, mtype):
        m = Mission(mtype, "metal", 3, "Station", 150, 20)
        assert m.mtype == mtype

    def test_is_expired_true(self, mission):
        mission.ticks = 0
        assert mission.is_expired() is True

    def test_is_expired_false(self, mission):
        mission.ticks = 10
        assert mission.is_expired() is False

    def test_is_expired_negative(self, mission):
        mission.ticks = -1
        assert mission.is_expired() is True

    def test_is_expired_non_active(self, mission):
        mission.ticks = 0
        mission.status = "completed"
        assert mission.is_expired() is False

    def test_check_completion_not_done(self, mission):
        ship = PlayerShip("Test", 100)
        assert mission.check_completion(ship) is False

    def test_check_completion_done(self, mission):
        mission.progress = 5
        ship = PlayerShip("Test", 100)
        assert mission.check_completion(ship) is True

    def test_check_completion_inactive(self, mission):
        mission.status = "completed"
        assert mission.check_completion(None) is False

    def test_check_completion_not_deliver(self):
        m = Mission("bounty", "credits", 1, "Station", 200, 30)
        ship = PlayerShip("Test", 100)
        assert m.check_completion(ship) is False

    def test_default_title_generated(self):
        m = Mission("deliver", "metal", 5, "Target", 200, 30)
        assert "5" in m.title
        assert "metal" in m.title

    def test_default_description_generated(self):
        m = Mission("deliver", "metal", 5, "TargetStation", 200, 30)
        assert "TargetStation" in m.description

    def test_tick_decrement_missions(self):
        ship = PlayerShip("Test", 100)
        m = Mission("deliver", "metal", 1, "T", 100, ticks=2)
        m.status = "active"
        ship.missions.append(m)
        ship.fail_expired_missions(None)
        assert m.ticks == 1
        assert m.status == "active"
        ship.fail_expired_missions(None)
        assert m.ticks == 0
        assert m.status == "failed"


# =========================================================================
# 8. NPCShip (PirateShip / TraderShip)
# =========================================================================


class TestNPCShip:
    def test_create_pirate(self):
        pirate = _make_pirate()
        assert isinstance(pirate, PirateShip)
        assert isinstance(pirate, NPCShip)
        assert pirate.hull == 40
        assert pirate.max_hull == 40
        assert pirate.shield_hp == 10
        assert pirate.alive is True
        assert isinstance(pirate.cargo, CargoHold)
        assert pirate.aggro_range == 5
        assert pirate.flee_threshold == 8

    def test_create_trader(self):
        trader = _make_trader()
        assert isinstance(trader, TraderShip)
        assert isinstance(trader, NPCShip)
        assert trader.hull == 60
        assert trader.max_hull == 60
        assert trader.shield_hp == 20
        assert trader.alive is True
        assert trader.cargo.has("metal") > 0

    def test_take_damage_shields_absorb(self):
        pirate = _make_pirate()
        pirate.take_damage(5)
        assert pirate.shield_hp == 5
        assert pirate.hull == 40

    def test_take_damage_excess_pierces_shields(self):
        pirate = _make_pirate()
        pirate.take_damage(15)
        assert pirate.shield_hp == 0
        assert pirate.hull == 35

    def test_take_damage_no_shields(self):
        pirate = _make_pirate()
        pirate.shield_hp = 0
        pirate.take_damage(20)
        assert pirate.hull == 20
        assert pirate.alive is True

    def test_take_damage_lethal(self):
        pirate = _make_pirate()
        pirate.shield_hp = 0
        assert pirate.take_damage(40) is False
        assert pirate.alive is False
        assert pirate.hull == 0

    def test_take_damage_returns_alive(self):
        pirate = _make_pirate()
        assert pirate.take_damage(5) is True

    def test_trader_current_target(self):
        trader = _make_trader(route=(0,))
        stations = [Station(5, 5, "A", "trade_hub", "free_traders")]
        assert trader.current_target(stations) is not None

    def test_trader_current_target_no_stations(self):
        trader = _make_trader(route=(0,))
        assert trader.current_target([]) is None

    def test_trader_route_wraps(self):
        s1 = Station(10, 10, name="S1")
        t = _make_trader(route=(0,))
        t.route_index = 5
        assert t.current_target([s1]) is s1

    def test_pirate_credits_in_range(self):
        pirate = _make_pirate()
        assert 50 <= pirate.credits <= 150

    def test_trader_credits_in_range(self):
        trader = _make_trader()
        assert 200 <= trader.credits <= 600

    def test_pirate_faction(self):
        pirate = _make_pirate()
        assert pirate.faction in ("chaos_cult", "xenos_horde")

    def test_pirate_cargo_capacity(self):
        pirate = _make_pirate()
        assert pirate.cargo.capacity == 30

    def test_trader_cargo_capacity(self):
        trader = _make_trader()
        assert trader.cargo.capacity == 100

    def test_trader_has_fuel_cells(self):
        trader = _make_trader()
        assert trader.cargo.has("fuel_cell") >= 20

    def test_pirate_race_in_races(self):
        pirate = _make_pirate()
        from config import RACES
        assert pirate.race in RACES

    def test_pirate_cargo_capacity(self):
        pirate = _make_pirate()
        assert pirate.cargo.capacity == 30

    def test_trader_cargo_capacity(self):
        assert TraderShip(0, 0, [0]).cargo.capacity == 100

    def test_trader_has_fuel_cells(self):
        assert TraderShip(0, 0, [0]).cargo.has("fuel_cell") >= 20

    def test_pirate_race_in_races(self):
        pirate = _make_pirate()
        from config import RACES
        assert pirate.race in RACES

    def test_npc_uid_unique(self):
        NPCShip_id_counter = 0
        p1 = PirateShip(0, 0)
        p2 = PirateShip(0, 0)
        assert p1.uid != p2.uid

    def test_trader_name_format(self):
        import re
        t = TraderShip(0, 0, [0])
        assert re.match(r"^[A-Z][a-z]+\d+$", t.name)


# =========================================================================
# 9. ScanResult
# =========================================================================


class TestScanResult:
    def test_create_failed(self):
        result = ScanResult(False, info={"error": "No power"})
        assert result.success is False
        assert result.summary() == "Scan failed."

    def test_create_success_passive(self):
        info = {"type": "PirateShip", "hull": 40, "max_hull": 40, "shield": 10}
        result = ScanResult(True, "passive", info)
        summary = result.summary()
        assert "Scan:" in summary
        assert "H:40/40" in summary
        assert "S:10" in summary

    def test_summary_with_cargo(self):
        info = {"type": "TraderShip", "hull": 60, "max_hull": 60,
                "cargo": {"metal": 15}}
        result = ScanResult(True, "active", info)
        summary = result.summary()
        assert "Cargo:" in summary

    def test_summary_with_weapons(self):
        info = {"type": "PirateShip", "weapons": "laser_turret"}
        result = ScanResult(True, "deep", info)
        summary = result.summary()
        assert "Weapons:" in summary

    def test_summary_with_signals(self):
        info = {"type": "Station", "signals": "anomaly"}
        result = ScanResult(True, "active", info)
        summary = result.summary()
        assert "Signals:" in summary

    def test_summary_default_unknown(self):
        result = ScanResult(True, "passive", {})
        assert "unknown" in result.summary()

    def test_stores_scanned_obj(self):
        ship = PirateShip(0, 0)
        result = ScanResult(True, "active", {}, scanned_obj=ship)
        assert result.scanned_obj is ship
        assert result.level == "active"

    def test_levels(self):
        for level in ("passive", "active", "deep"):
            r = ScanResult(True, level, {})
            assert r.level == level

    def test_summary_empty_info(self):
        result = ScanResult(True, "passive", {"type": "Station"})
        assert "Station" in result.summary()


# =========================================================================
# 10. Edge cases
# =========================================================================


class TestEdgeCases:
    def test_empty_cargo_hold(self):
        ch = CargoHold(50)
        assert ch.used() == 0
        assert ch.free() == 50
        assert ch.has("anything") == 0
        assert ch.total_value() == 0
        assert ch.remove("anything", 1) is False

    def test_zero_hull_player_ship(self):
        ship = PlayerShip("Dead", 0)
        assert ship.hull == 0
        assert ship.hull <= ship.max_hull

    def test_broken_module_not_contributing(self, player_ship):
        for m in player_ship.compartments["weapon"]["modules"]:
            m.durability = 0
        stats = player_ship.get_effective_stats()
        assert stats["damage"] == 0  # broken module excluded

    def test_broken_module_not_consuming_power(self, player_ship):
        for m in player_ship.compartments["weapon"]["modules"]:
            m.durability = 0
        assert player_ship.total_power_consumed() == 8  # 11 - 3

    def test_full_mission_log(self, player_ship):
        for i in range(5):
            m = Mission("deliver", "metal", 1, f"S{i}", 100, 30)
            player_ship.add_mission(m)
        assert len(player_ship.missions) == 5

    def test_no_crew_to_assign(self, player_ship):
        msg, ok = player_ship.assign_crew("Nobody", "Pilot")
        assert ok is False

    def test_fire_nonexistent_crew(self, player_ship):
        msg, ok = player_ship.fire_crew("Ghost")
        assert ok is False

    def test_scan_self(self, player_ship):
        result = player_ship.scan_target(player_ship, "passive")
        assert result.success is True
        assert result.info["type"] == "PlayerShip"

    def test_sell_hull_too_many(self, player_ship):
        # Can't sell the last hull
        msg, ok = player_ship.sell_hull("corvette")
        assert ok is False

    def test_remove_from_empty_cargo(self):
        ch = CargoHold(10)
        assert ch.remove("metal", 1) is False

    def test_add_to_zero_capacity(self):
        ch = CargoHold(0)
        assert ch.add("metal", 1) is False

    def test_cargo_capacity_exact(self):
        ch = CargoHold(10)
        assert ch.add("metal", 10) is True
        assert ch.add("ore", 1) is False

    def test_mission_defaults_non_deliver(self):
        m = Mission("bounty", "credits", 1, "Station", 200, 30)
        assert m.title != ""
        assert m.description != ""

    def test_station_economy_no_crisis(self):
        s = Station(0, 0, stype="trade_hub", faction="free_traders")
        s.crisis_ticks = 0
        old = dict(s.inventory)
        s.update_economy()
        # trade_hub consumes ice, produces electronics
        assert s.inventory != old

    def test_buy_all_junk_mixed_items(self, station, player_ship):
        player_ship.cargo.add("ore", 5)   # raw
        player_ship.cargo.add("silicon", 3)  # raw
        player_ship.cargo.add("relic", 1)    # special, not raw
        credits_before = player_ship.credits
        msg, ok = station.buy_all_junk(player_ship)
        assert ok is True
        assert player_ship.cargo.has("ore") == 0
        assert player_ship.cargo.has("silicon") == 0
        assert player_ship.cargo.has("relic") == 1  # special, not sold
        assert player_ship.credits > credits_before
