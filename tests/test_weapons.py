"""Tests for weapon/ammo system — damage types, resistances, ammo, reload."""

import pytest
import random
from models import create_random_ship, create_random_enemy, ShipModule
from config import (
    SHIP_MODULES, WEAPON_CLASSES, AMMO_TYPES, DAMAGE_TYPES,
    SHIELD_RESIST, ARMOR_RESIST, COMP_DAMAGE_MOD, RECIPES,
)
from battle import (
    _apply_shield_resist, _apply_armor_resist, _apply_comp_damage_mod,
    _get_weapon_damage_type, BattleController,
)


# ═══════════════════════════════════════════════════════════════════════
# Config integrity
# ═══════════════════════════════════════════════════════════════════════

class TestWeaponConfig:
    """Check weapon/ammo config data is well-formed."""

    def test_weapon_classes_have_names(self):
        for wcid, wc in WEAPON_CLASSES.items():
            assert "name" in wc
            assert "ammo_slots" in wc
            assert "can_change_ammo" in wc

    def test_ammo_types_have_damage_types(self):
        for aid, ainfo in AMMO_TYPES.items():
            assert "damage_type" in ainfo
            assert ainfo["damage_type"] in DAMAGE_TYPES

    def test_ammo_types_have_names(self):
        for aid, ainfo in AMMO_TYPES.items():
            assert "name" in ainfo

    def test_damage_types_have_names(self):
        for dtid, dt in DAMAGE_TYPES.items():
            assert "name" in dt

    def test_shield_resist_covers_all_damage_types(self):
        for dt in DAMAGE_TYPES:
            assert dt in SHIELD_RESIST, f"Missing shield resist for {dt}"

    def test_armor_resist_covers_all_damage_types(self):
        for dt in DAMAGE_TYPES:
            assert dt in ARMOR_RESIST, f"Missing armor resist for {dt}"

    def test_comp_damage_mod_covers_all_damage_types(self):
        for dt in DAMAGE_TYPES:
            assert dt in COMP_DAMAGE_MOD, f"Missing comp damage mod for {dt}"

    def test_weapon_modules_have_weapon_class(self):
        """All weapon-compartment modules should define weapon_class."""
        for mid, minfo in SHIP_MODULES.items():
            if minfo.get("comp") == "weapon":
                assert "weapon_class" in minfo, f"{mid} missing weapon_class"
                assert minfo["weapon_class"] in WEAPON_CLASSES

    def test_weapon_modules_have_damage_type(self):
        for mid, minfo in SHIP_MODULES.items():
            if minfo.get("comp") == "weapon":
                assert "damage_type" in minfo, f"{mid} missing damage_type"
                assert minfo["damage_type"] in DAMAGE_TYPES

    def test_new_weapons_have_ammo_capacity(self):
        """Kinetic, missile and ion weapons need ammo_capacity."""
        for mid, minfo in SHIP_MODULES.items():
            wc = minfo.get("weapon_class")
            if wc in ("kinetic", "missile", "ion"):
                assert "ammo_capacity" in minfo, f"{mid} missing ammo_capacity"
                assert minfo["ammo_capacity"] > 0

    def test_ammo_recipes_have_yield(self):
        """Ammo recipes should define how many units they produce."""
        for rid, recipe in RECIPES.items():
            if rid in AMMO_TYPES:
                assert "yield" in recipe, f"{rid} recipe missing yield"


# ═══════════════════════════════════════════════════════════════════════
# ShipModule ammo methods
# ═══════════════════════════════════════════════════════════════════════

class TestShipModuleAmmo:
    """ShipModule ammo system methods."""

    def test_weapon_without_ammo_capacity(self):
        """Laser/plasma/disruptor don't need ammo."""
        m = ShipModule("laser_turret")
        assert not m.needs_ammo()
        assert m.ammo_capacity == 0

    def test_weapon_with_ammo_capacity(self):
        m = ShipModule("kinetic_cannon")
        assert m.needs_ammo()
        assert m.ammo_capacity == 20
        assert m.current_ammo == 20  # starts full
        assert m.has_ammo()

    def test_consume_ammo(self):
        m = ShipModule("kinetic_cannon")
        assert m.consume_ammo(1) is True
        assert m.current_ammo == 19
        assert m.has_ammo()

    def test_consume_ammo_empty(self):
        m = ShipModule("kinetic_cannon")
        m.current_ammo = 0
        assert m.consume_ammo(1) is False

    def test_has_ammo_when_empty(self):
        m = ShipModule("kinetic_cannon")
        m.current_ammo = 0
        assert not m.has_ammo()

    def test_load_ammo_fills_to_capacity(self):
        m = ShipModule("kinetic_cannon")
        m.current_ammo = 0
        # Create ship with expanded cargo to fit ammo
        ship = create_random_ship(is_player=True)
        ship.cargo.capacity = 200  # ensure enough space
        ship.cargo.add("slug", 50)
        loaded = m.load_ammo("slug", 30, ship.cargo)
        assert loaded == 20  # limited by ammo_capacity
        assert m.current_ammo == 20
        assert m.loaded_ammo_type == "slug"
        assert ship.cargo.has("slug") == 30  # 50-20 = 30

    def test_load_ammo_partial(self):
        m = ShipModule("kinetic_cannon")
        m.current_ammo = 10  # already 10 loaded
        ship = create_random_ship(is_player=True)
        ship.cargo.capacity = 200
        ship.cargo.add("slug", 50)
        loaded = m.load_ammo("slug", 20, ship.cargo)
        assert loaded == 10  # fills to 20
        assert m.current_ammo == 20
        assert m.loaded_ammo_type == "slug"

    def test_load_ammo_no_ammo_in_cargo(self):
        m = ShipModule("kinetic_cannon")
        m.current_ammo = 0
        ship = create_random_ship(is_player=True)
        loaded = m.load_ammo("slug", 20, ship.cargo)
        assert loaded == 0  # no ammo in cargo

    def test_load_ammo_non_ammo_weapon(self):
        m = ShipModule("laser_turret")
        ship = create_random_ship(is_player=True)
        loaded = m.load_ammo("slug", 20, ship.cargo)
        assert loaded == 0  # laser doesn't need ammo

    def test_unload_ammo(self):
        m = ShipModule("kinetic_cannon")
        m.current_ammo = 15
        m.loaded_ammo_type = "slug"
        ship = create_random_ship(is_player=True)
        unloaded = m.unload_ammo(ship.cargo)
        assert unloaded == 15
        assert m.current_ammo == 0
        assert m.loaded_ammo_type is None
        assert ship.cargo.has("slug") == 15

    def test_unload_ammo_empty(self):
        m = ShipModule("kinetic_cannon")
        m.current_ammo = 0
        m.loaded_ammo_type = None
        ship = create_random_ship(is_player=True)
        assert m.unload_ammo(ship.cargo) == 0

    def test_level_up_preserves_ammo(self):
        """Level-up should not reset ammo fields."""
        m = ShipModule("kinetic_cannon", level=1)
        m.current_ammo = 10
        m.loaded_ammo_type = "slug"
        m.upgrade()  # level 2
        assert m.current_ammo == 10  # preserved
        assert m.loaded_ammo_type == "slug"


# ═══════════════════════════════════════════════════════════════════════
# Damage type calculations
# ═══════════════════════════════════════════════════════════════════════

class TestShieldResist:
    """Shield resistance calculations."""

    def test_no_shields(self):
        to_shield, to_hull = _apply_shield_resist(100, "kinetic", 0)
        assert to_shield == 0
        assert to_hull == 100

    def test_kinetic_vs_shields(self):
        """Kinetic is bad vs shields — 20% resist means 80% gets through."""
        to_shield, to_hull = _apply_shield_resist(100, "kinetic", 50)
        # 20% resist → 80% of damage hits shields → min(50, 80) = 50
        assert to_shield == 50  # all shields consumed
        assert to_hull == 50  # remaining passes through

    def test_energy_vs_shields(self):
        """Energy is good vs shields — 50% resist means 50% hits shields."""
        to_shield, to_hull = _apply_shield_resist(100, "energy", 50)
        # 50% resist → 50% hits shields → min(50, 50) = 50
        assert to_shield == 50
        assert to_hull == 50

    def test_disruption_vs_shields(self):
        """Disruption mostly bypasses shields — 10% resist."""
        to_shield, to_hull = _apply_shield_resist(100, "disruption", 50)
        assert to_shield > 0  # some absorbed
        assert to_hull > 0  # most passes through

    def test_limited_shields(self):
        """Small shields absorb less."""
        to_shield, to_hull = _apply_shield_resist(100, "energy", 10)
        # 50% resist → 50% hits shields → min(10, 50) = 10
        assert to_shield == 10
        assert to_hull == 90


class TestArmorResist:
    """Armor resistance calculations."""

    def test_no_armor(self):
        result = _apply_armor_resist(100, "kinetic", 0)
        assert 50 <= result <= 100  # base resist ~40% without armor

    def test_armor_reduces_damage(self):
        unarmored = _apply_armor_resist(100, "kinetic", 0)
        armored = _apply_armor_resist(100, "kinetic", 20)
        assert armored <= unarmored

    def test_explosive_vs_armor(self):
        """Explosive is good vs armor (20% resist)."""
        result = _apply_armor_resist(100, "explosive", 10)
        assert result > 0

    def test_ion_vs_armor(self):
        """Ion is bad vs armor (50% resist)."""
        ion = _apply_armor_resist(100, "ion", 5)
        kinetic = _apply_armor_resist(100, "kinetic", 5)
        assert ion <= kinetic  # ion has higher resist

    def test_armor_pen_reduces_effect(self):
        """AP rounds with armor_pen should deal more damage."""
        no_pen = _apply_armor_resist(100, "kinetic", 20, 0)
        with_pen = _apply_armor_resist(100, "kinetic", 20, 10)
        assert with_pen >= no_pen

    def test_minimum_one_damage(self):
        result = _apply_armor_resist(5, "ion", 50)
        assert result >= 1


class TestCompDamageMod:
    """Compartment damage type modifiers."""

    def test_energy_vs_shield_increases(self):
        """Energy deals 1.3× to shield compartments."""
        result = _apply_comp_damage_mod(100, "energy", "shield")
        assert result == 130

    def test_kinetic_vs_shield_decreases(self):
        """Kinetic deals 0.6× to shield compartments."""
        result = _apply_comp_damage_mod(100, "kinetic", "shield")
        assert result == 60

    def test_disruption_vs_sensor(self):
        """Disruption deals 1.8× to sensor."""
        result = _apply_comp_damage_mod(100, "disruption", "sensor")
        assert result == 180

    def test_explosive_vs_reactor(self):
        """Explosive deals 1.5× to reactor."""
        result = _apply_comp_damage_mod(100, "explosive", "reactor")
        assert result == 150

    def test_unknown_comp_defaults_to_1x(self):
        result = _apply_comp_damage_mod(100, "energy", "nonexistent")
        assert result == 100


class TestGetWeaponDamageType:
    """Weapon damage type resolution."""

    def test_laser_default_type(self):
        w = create_random_ship(is_player=True)
        laser = w.compartments["weapon"]["modules"][0]
        # Most ships start with laser_turret or similar
        dt = _get_weapon_damage_type(laser, None)
        assert dt == laser.damage_type

    def test_ammo_overrides_type(self):
        """Loaded ammo can change the damage type."""
        w = create_random_ship(is_player=True)
        weapon = w.compartments["weapon"]["modules"][0]
        # Simulate loading HE warhead (explosive)
        dt = _get_weapon_damage_type(weapon, "high_explosive")
        assert dt == "explosive"

    def test_ammo_slug_keeps_kinetic(self):
        dt = _get_weapon_damage_type({"damage_type": "kinetic"}, "slug")
        assert dt == "kinetic"

    def test_no_ammo_uses_weapon_type(self):
        dt = _get_weapon_damage_type({"damage_type": "energy"}, None)
        assert dt == "energy"

    def test_dict_weapon_works(self):
        """Support both ShipModule and dict."""
        dt = _get_weapon_damage_type({"damage_type": "disruption"}, None)
        assert dt == "disruption"


# ═══════════════════════════════════════════════════════════════════════
# BattleController integration — ammo/reload
# ═══════════════════════════════════════════════════════════════════════

class TestBattleAmmo:
    """BattleController ammo & reload integration."""

    def test_kinetic_cannon_needs_ammo(self):
        p = create_random_ship(is_player=True)
        e = create_random_enemy()
        bc = BattleController(p, e, app=None)
        # Find a kinetic weapon
        kws = [w for w in bc._get_player_weapons() if w.needs_ammo()]
        if not kws:
            # Convert first weapon to kinetic
            w = bc._get_player_weapons()[0]
            w.weapon_class = "kinetic"
            w.ammo_capacity = 20
            w.current_ammo = 0
            kws = [w]
        kw = kws[0]
        kw.current_ammo = 0  # ensure empty for test
        assert kw.needs_ammo() is True
        assert kw.has_ammo() is False  # empty

    def test_reload_fills_ammo(self):
        p = create_random_ship(is_player=True)
        e = create_random_enemy()
        p.cargo.capacity = 200
        bc = BattleController(p, e, app=None)
        # Setup kinetic weapon with no ammo
        weapons = bc._get_player_weapons()
        kw = weapons[0]
        kw.weapon_class = "kinetic"
        kw.ammo_capacity = 20
        kw.current_ammo = 0
        kw.loaded_ammo_type = "slug"
        # Add ammo to cargo
        p.cargo.add("slug", 50)
        # Reload
        bc.do_reload()
        assert kw.current_ammo == 20
        assert kw.loaded_ammo_type == "slug"

    def test_reload_no_ammo_in_cargo(self):
        p = create_random_ship(is_player=True)
        e = create_random_enemy()
        bc = BattleController(p, e, app=None)
        weapons = bc._get_player_weapons()
        kw = weapons[0]
        kw.weapon_class = "kinetic"
        kw.ammo_capacity = 20
        kw.current_ammo = 0
        bc.do_reload()
        assert kw.current_ammo == 0  # no ammo in cargo

    def test_attack_with_empty_ammo_fails(self):
        p = create_random_ship(is_player=True)
        e = create_random_enemy()
        bc = BattleController(p, e, app=None)
        weapons = bc._get_player_weapons()
        kw = weapons[0]
        kw.weapon_class = "kinetic"
        kw.ammo_capacity = 20
        kw.current_ammo = 0
        old_log = len(bc.log)
        bc.do_attack(0, "shield")
        new_msgs = bc.log[old_log:]
        assert any("out of ammo" in msg for msg in new_msgs), f"No 'out of ammo' in {new_msgs}"

    def test_attack_with_ammo_succeeds(self):
        p = create_random_ship(is_player=True)
        e = create_random_enemy()
        p.cargo.capacity = 200
        bc = BattleController(p, e, app=None)
        weapons = bc._get_player_weapons()
        kw = weapons[0]
        kw.weapon_class = "kinetic"
        kw.ammo_capacity = 20
        kw.current_ammo = 5
        kw.loaded_ammo_type = "slug"
        bc.do_attack(0, "shield")
        assert kw.current_ammo < 5  # consumed ammo

    def test_energy_weapon_ignores_ammo(self):
        """Laser/plasma should not be affected by ammo system."""
        p = create_random_ship(is_player=True)
        e = create_random_enemy()
        bc = BattleController(p, e, app=None)
        weapons = bc._get_player_weapons()
        w = weapons[0]
        w.weapon_class = "laser"
        w.ammo_capacity = 0
        w.current_ammo = 0
        # Laser should fire even with current_ammo=0 (no ammo slot)
        bc.do_attack(0, "shield")
        assert not any("out of ammo" in msg for msg in bc.log[-3:])


# ═══════════════════════════════════════════════════════════════════════
# BattleController — damage type integration
# ═══════════════════════════════════════════════════════════════════════

class TestBattleDamageTypes:
    """Verify damage types are applied in actual combat."""

    def test_damage_type_logged(self):
        p = create_random_ship(is_player=True)
        e = create_random_enemy()
        bc = BattleController(p, e, app=None)
        weapons = bc._get_player_weapons()
        old_log = len(bc.log)
        bc.do_attack(0, "shield")
        # Check that a damage type name appears in the log
        new_msgs = bc.log[old_log:]
        combined = " ".join(new_msgs)
        # Any of the damage type names should appear
        dts = [dt["name"] for dt in DAMAGE_TYPES.values()]
        assert any(dt in combined for dt in dts), f"No damage type in log: {new_msgs}"

    def test_attack_logs_damage_type(self):
        """The attack log line should show [Energy], [Kinetic], etc."""
        p = create_random_ship(is_player=True)
        e = create_random_enemy()
        bc = BattleController(p, e, app=None)
        bc.do_attack(0, "shield")
        # Find the final "→ Weapon @ comp [Type]" line
        for msg in reversed(bc.log):
            if msg.startswith("→"):
                assert "[" in msg and "]" in msg, f"Missing damage type in: {msg}"
                break

    def test_enemy_damage_type_logged(self):
        """Enemy attacks should also show damage type."""
        p = create_random_ship(is_player=True)
        e = create_random_enemy()
        bc = BattleController(p, e, app=None)
        old_log = len(bc.log)
        bc._do_enemy_turn()
        new_msgs = bc.log[old_log:]
        # If enemy attacked, should see damage type
        attack_msgs = [m for m in new_msgs if "attacks" in m]
        if attack_msgs:
            assert any("[" in m and "]" in m for m in attack_msgs)


# ═══════════════════════════════════════════════════════════════════════
# Quick battle integration
# ═══════════════════════════════════════════════════════════════════════

class TestQuickBattleWeapons:
    """Quick battle ships should work with new weapon system."""

    def test_quick_battle_ship_has_weapon_class(self):
        for _ in range(10):
            p = create_random_ship(is_player=True)
            for w in p.compartments["weapon"]["modules"]:
                assert w.weapon_class in WEAPON_CLASSES or w.weapon_class is None
                assert w.damage_type in DAMAGE_TYPES

    def test_quick_battle_enemy_has_weapon_class(self):
        for _ in range(10):
            e = create_random_enemy()
            for w in e.compartments["weapon"]["modules"]:
                assert w.weapon_class in WEAPON_CLASSES or w.weapon_class is None

    def test_ammo_weapon_in_quick_battle_starts_loaded(self):
        """Quick battle ships should start with ammo-loaded weapons."""
        for _ in range(20):
            p = create_random_ship(is_player=True)
            for w in p.compartments["weapon"]["modules"]:
                if w.needs_ammo():
                    assert w.current_ammo > 0, f"{w.name} has no ammo"
                    assert w.has_ammo()
