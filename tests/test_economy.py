"""Tests for economy, trading, crafting, upgrades, and hull system."""

import pytest
from models import PlayerShip, Station
from config import RESOURCES, SHIP_HULLS, UPGRADES, RECIPES, SHIP_MODULES


# ──────────────────────────────────────────────────────────────────────
# Prices
# ──────────────────────────────────────────────────────────────────────

class TestPrices:
    """Verify base prices and station pricing mechanics."""

    def test_all_resource_base_prices_positive(self):
        for rid, info in RESOURCES.items():
            assert info["base_price"] > 0, f"{rid} base_price must be positive"

    def test_station_price_for_player_returns_tuple(self, station, player_ship):
        price = station.price_for_player("metal", True, player_ship)
        assert isinstance(price, tuple)
        assert len(price) == 2

    def test_sell_price_less_than_buy_price(self, station, player_ship):
        """Player sells at bp (buy-price), player buys at sp (sell-price). bp < sp."""
        for rid in RESOURCES:
            bp, _ = station.price_for_player(rid, False, player_ship)
            sp, _ = station.price_for_player(rid, True, player_ship)
            assert bp < sp, (
                f"{rid}: station buy price {bp} >= station sell price {sp}"
            )

    def test_unknown_resource_returns_zero(self, station, player_ship):
        price, notes = station.price_for_player("nonexistent", True, player_ship)
        assert price == 0
        assert notes == ""


# ──────────────────────────────────────────────────────────────────────
# Trading
# ──────────────────────────────────────────────────────────────────────

class TestTrading:
    """Player buying from and selling to stations."""

    def test_sell_to_player_reduces_credits_adds_cargo(self, station, player_ship):
        """station.sell_to(ship) = player buys from station."""
        credits_before = player_ship.credits
        cargo_before = player_ship.cargo.has("metal")
        msg = station.sell_to(player_ship, "metal", 5)
        assert "Bought" in msg
        assert player_ship.credits < credits_before
        assert player_ship.cargo.has("metal") == cargo_before + 5

    def test_buy_from_player_adds_credits_removes_cargo(self, station, player_ship):
        """station.buy_from(ship) = player sells to station."""
        player_ship.cargo.add("metal", 10)
        credits_before = player_ship.credits
        cargo_before = player_ship.cargo.has("metal")
        msg = station.buy_from(player_ship, "metal", 5)
        assert "Sold" in msg
        assert player_ship.credits > credits_before
        assert player_ship.cargo.has("metal") == cargo_before - 5

    def test_trade_unknown_resource_fails(self, station, player_ship):
        msg = station.sell_to(player_ship, "nonexistent", 1)
        assert "Unknown" in msg
        msg = station.buy_from(player_ship, "nonexistent", 1)
        assert "Unknown" in msg

    def test_buy_from_player_insufficient_cargo(self, station, player_ship):
        """Player can't sell what they don't have."""
        player_ship.cargo.items = {}
        msg = station.buy_from(player_ship, "metal", 1)
        assert "Not enough" in msg

    def test_sell_to_player_insufficient_credits(self, station, player_ship):
        """Player can't buy what they can't afford."""
        player_ship.credits = 0
        msg = station.sell_to(player_ship, "metal", 1)
        assert "Need" in msg

    def test_sell_to_player_insufficient_stock(self, station, player_ship):
        """Station can't sell what it doesn't have."""
        station.inventory["metal"] = 0
        msg = station.sell_to(player_ship, "metal", 1)
        assert "Only" in msg

    def test_trade_updates_station_inventory(self, station, player_ship):
        """Station inventory decreases on sell, increases on buy."""
        inv_before = station.inventory.get("metal", 0)
        station.sell_to(player_ship, "metal", 3)
        assert station.inventory["metal"] == inv_before - 3

        player_ship.cargo.add("electronics", 5)
        inv_after_sell = station.inventory.get("electronics", 0)
        station.buy_from(player_ship, "electronics", 5)
        assert station.inventory["electronics"] == inv_after_sell + 5

    def test_contraband_blocked(self, station, player_ship):
        """Station refuses to buy contraband relics from player."""
        station.faction = "imperium"
        player_ship.reputation["imperium"] = 0
        player_ship.cargo.add("relic", 1)
        msg = station.buy_from(player_ship, "relic", 1)
        assert "Contraband" in msg


# ──────────────────────────────────────────────────────────────────────
# Reputation effects
# ──────────────────────────────────────────────────────────────────────

class TestReputationEffects:
    """High reputation improves trade prices; low reputation worsens them."""

    def test_high_reputation_reduces_buy_price(self, station, player_ship):
        """Player with high rep pays less when buying from station."""
        price_neutral, _ = station.price_for_player("metal", True, player_ship)
        player_ship.reputation["free_traders"] = 60
        price_friendly, _ = station.price_for_player("metal", True, player_ship)
        assert price_friendly < price_neutral

    def test_high_reputation_increases_sell_price(self, station, player_ship):
        """Player with high rep earns more when selling to station."""
        price_neutral, _ = station.price_for_player("metal", False, player_ship)
        player_ship.reputation["free_traders"] = 60
        price_friendly, _ = station.price_for_player("metal", False, player_ship)
        assert price_friendly > price_neutral

    def test_low_reputation_increases_buy_price(self, station, player_ship):
        """Player with low rep pays more when buying from station."""
        price_neutral, _ = station.price_for_player("metal", True, player_ship)
        player_ship.reputation["free_traders"] = -30
        price_hostile, _ = station.price_for_player("metal", True, player_ship)
        assert price_hostile > price_neutral

    def test_low_reputation_decreases_sell_price(self, station, player_ship):
        """Player with low rep earns less when selling to station."""
        price_neutral, _ = station.price_for_player("metal", False, player_ship)
        player_ship.reputation["free_traders"] = -30
        price_hostile, _ = station.price_for_player("metal", False, player_ship)
        assert price_hostile < price_neutral

    def test_very_low_reputation_blocks_trade(self, station, player_ship):
        """Station refuses to trade with hostile reputation (< -20)."""
        player_ship.reputation["free_traders"] = -30
        msg = station.sell_to(player_ship, "metal", 1)
        assert "blocked" in msg
        msg = station.buy_from(player_ship, "metal", 1)
        assert "blocked" in msg

    def test_low_rep_only_blocks_matching_faction(self, station, player_ship):
        """Low reputation only blocks trade with that faction, not others."""
        player_ship.reputation["free_traders"] = -30
        player_ship.reputation["imperium"] = 0
        station_imperium = Station(5, 5, "ImperiumHub", "trade_hub", "imperium")
        station_imperium.inventory = {"metal": 20}
        station_imperium.update_prices()
        msg = station_imperium.sell_to(player_ship, "metal", 1)
        assert "blocked" not in msg or "Bought" in msg


# ──────────────────────────────────────────────────────────────────────
# Crafting
# ──────────────────────────────────────────────────────────────────────

class TestCrafting:
    """PlayerShip.craft() consumes inputs and creates output."""

    @pytest.mark.parametrize("recipe_id", list(RECIPES))
    def test_every_recipe_is_craftable(self, player_ship, recipe_id):
        """Try crafting each known recipe with sufficient resources."""
        recipe = RECIPES[recipe_id]
        for rid, amt in recipe["inputs"].items():
            player_ship.cargo.add(rid, amt * 2)
        msg, ok = player_ship.craft(recipe_id, 1)
        assert ok, f"Failed to craft {recipe_id}: {msg}"

    def test_craft_consumes_inputs(self, player_ship):
        """Crafting repair_kit consumes 3 metal + 1 electronics."""
        player_ship.cargo.add("metal", 3)
        player_ship.cargo.add("electronics", 1)
        metal_before = player_ship.cargo.has("metal")
        elec_before = player_ship.cargo.has("electronics")
        msg, ok = player_ship.craft("repair_kit", 1)
        assert ok, f"craft failed: {msg}"
        assert player_ship.cargo.has("metal") == metal_before - 3
        assert player_ship.cargo.has("electronics") == elec_before - 1

    def test_craft_creates_output(self, player_ship):
        """Crafting produces the output item in cargo."""
        player_ship.cargo.add("metal", 3)
        player_ship.cargo.add("electronics", 1)
        before = player_ship.cargo.has("repair_kit")
        msg, ok = player_ship.craft("repair_kit", 1)
        assert ok, f"craft failed: {msg}"
        assert player_ship.cargo.has("repair_kit") == before + 1

    def test_craft_fails_without_resources(self, empty_ship):
        """Crafting without required inputs returns failure."""
        msg, ok = empty_ship.craft("repair_kit", 1)
        assert not ok
        assert "Need" in msg

    def test_craft_fails_with_partial_resources(self, empty_ship):
        """Crafting with only some inputs returns failure."""
        empty_ship.cargo.add("metal", 3)
        msg, ok = empty_ship.craft("repair_kit", 1)
        assert not ok
        assert "Need" in msg

    def test_craft_fails_if_cargo_full(self, player_ship):
        """Crafting without cargo space returns failure."""
        player_ship.cargo.add("metal", 3)
        player_ship.cargo.add("electronics", 1)
        player_ship.cargo.capacity = 0
        msg, ok = player_ship.craft("repair_kit", 1)
        assert not ok
        assert "cargo space" in msg

    def test_craft_unknown_recipe(self, player_ship):
        msg, ok = player_ship.craft("nonexistent", 1)
        assert not ok
        assert "Unknown" in msg

    def test_craft_multiple_items(self, empty_ship):
        """Crafting 2x repair_kit consumes double resources."""
        empty_ship.cargo.add("metal", 6)
        empty_ship.cargo.add("electronics", 2)
        msg, ok = empty_ship.craft("repair_kit", 2)
        assert ok, f"craft failed: {msg}"
        assert empty_ship.cargo.has("repair_kit") == 2
        assert empty_ship.cargo.has("metal") == 0
        assert empty_ship.cargo.has("electronics") == 0

    def test_craft_uses_output_name_from_recipe(self, player_ship):
        """The crafted item id matches the recipe key."""
        player_ship.cargo.add("ice", 2)
        player_ship.cargo.add("silicon", 1)
        msg, ok = player_ship.craft("fuel_cell", 1)
        assert ok, f"craft failed: {msg}"
        assert player_ship.cargo.has("fuel_cell") >= 1


# ──────────────────────────────────────────────────────────────────────
# Upgrades
# ──────────────────────────────────────────────────────────────────────

class TestUpgrades:
    """Permanent hull upgrades via PlayerShip.apply_upgrade()."""

    def test_every_upgrade_has_valid_config(self):
        for uid, cfg in UPGRADES.items():
            assert "cost" in cfg, f"{uid} missing cost"
            assert cfg["cost"] > 0, f"{uid} cost must be positive"
            assert "inputs" in cfg, f"{uid} missing inputs"
            assert isinstance(cfg["inputs"], dict), f"{uid} inputs must be dict"
            assert "bonus" in cfg, f"{uid} missing bonus"
            assert isinstance(cfg["bonus"], dict), f"{uid} bonus must be dict"

    def test_apply_cargo_expansion_increases_cargo(self, player_ship):
        """Cargo Expansion adds +20 cargo capacity."""
        cap_before = player_ship.cargo.capacity
        player_ship.credits = 9999
        player_ship.cargo.add("metal", 5)
        player_ship.cargo.add("electronics", 3)
        msg, ok = player_ship.apply_upgrade("cargo_expansion")
        assert ok, f"apply_upgrade failed: {msg}"
        assert player_ship.cargo.capacity == cap_before + 20

    def test_apply_hull_reinforcement_increases_max_hull(self, player_ship):
        """Hull Reinforcement adds +30 max hull."""
        max_hull_before = player_ship.max_hull
        player_ship.credits = 9999
        player_ship.cargo.add("metal", 10)
        player_ship.cargo.add("electronics", 2)
        msg, ok = player_ship.apply_upgrade("hull_reinforcement")
        assert ok, f"apply_upgrade failed: {msg}"
        assert player_ship.max_hull == max_hull_before + 30

    def test_apply_upgrade_consumes_resources(self, empty_ship):
        """Upgrade deducts credits and consumes cargo inputs."""
        empty_ship.credits = 9999
        empty_ship.cargo.add("metal", 10)
        empty_ship.cargo.add("electronics", 2)
        msg, ok = empty_ship.apply_upgrade("hull_reinforcement")
        assert ok, f"apply_upgrade failed: {msg}"
        assert empty_ship.cargo.has("metal") == 0
        assert empty_ship.cargo.has("electronics") == 0
        assert empty_ship.credits == 9999 - 2000

    def test_apply_upgrade_fails_if_already_applied(self, player_ship):
        """Cannot apply the same upgrade twice."""
        player_ship.credits = 9999
        player_ship.cargo.add("metal", 20)
        player_ship.cargo.add("electronics", 5)
        player_ship.apply_upgrade("cargo_expansion")
        msg, ok = player_ship.apply_upgrade("cargo_expansion")
        assert not ok
        assert "Already" in msg

    def test_apply_upgrade_fails_without_credits(self, player_ship):
        """Cannot apply upgrade when credits are insufficient."""
        player_ship.credits = 0
        player_ship.cargo.add("metal", 5)
        player_ship.cargo.add("electronics", 3)
        msg, ok = player_ship.apply_upgrade("cargo_expansion")
        assert not ok
        assert "Need" in msg or "cr" in msg

    def test_apply_upgrade_fails_without_resources(self, empty_ship):
        """Cannot apply upgrade without the required cargo inputs."""
        empty_ship.credits = 9999
        msg, ok = empty_ship.apply_upgrade("cargo_expansion")
        assert not ok
        assert "Need" in msg

    def test_unknown_upgrade(self, player_ship):
        msg, ok = player_ship.apply_upgrade("nonexistent")
        assert not ok
        assert "Unknown" in msg

    def test_has_upgrade_tracks_applied_upgrades(self, player_ship):
        """has_upgrade returns True only after applying."""
        assert not player_ship.has_upgrade("cargo_expansion")
        player_ship.credits = 9999
        player_ship.cargo.add("metal", 5)
        player_ship.cargo.add("electronics", 3)
        player_ship.apply_upgrade("cargo_expansion")
        assert player_ship.has_upgrade("cargo_expansion")


# ──────────────────────────────────────────────────────────────────────
# Hull purchasing
# ──────────────────────────────────────────────────────────────────────

class TestHullPurchasing:
    """Buying and selling hulls via PlayerShip."""

    @pytest.mark.parametrize("hull_id", ["shuttle", "frigate", "destroyer"])
    def test_buy_hull_costs_credits(self, player_ship, hull_id):
        """Buying a new hull deducts credits and adds to owned_hulls."""
        player_ship.credits = 99999
        cost = SHIP_HULLS[hull_id]["cost"]
        msg, ok = player_ship.buy_hull(hull_id)
        assert ok, f"buy_hull failed: {msg}"
        assert player_ship.credits == 99999 - cost
        assert hull_id in player_ship.owned_hulls

    def test_buy_already_owned_hull_fails(self, player_ship):
        """Cannot buy a hull the player already owns."""
        msg, ok = player_ship.buy_hull("corvette")
        assert not ok
        assert "Already own" in msg

    def test_buy_hull_insufficient_credits(self, player_ship):
        """Cannot buy a hull without enough credits."""
        player_ship.credits = 0
        msg, ok = player_ship.buy_hull("frigate")
        assert not ok
        assert "Need" in msg

    def test_buy_unknown_hull(self, player_ship):
        msg, ok = player_ship.buy_hull("nonexistent")
        assert not ok
        assert "Unknown" in msg

    def test_sell_hull_returns_50_percent(self, player_ship):
        """Selling an owned hull returns 50% of its cost."""
        player_ship.credits = 99999
        player_ship.buy_hull("shuttle")
        credits_before = player_ship.credits
        msg, ok = player_ship.sell_hull("shuttle")
        assert ok, f"sell_hull failed: {msg}"
        expected = SHIP_HULLS["shuttle"]["cost"] // 2
        assert player_ship.credits == credits_before + expected
        assert "shuttle" not in player_ship.owned_hulls

    def test_cannot_sell_current_hull(self, player_ship):
        """Player cannot sell the hull they are currently flying."""
        msg, ok = player_ship.sell_hull("corvette")
        assert not ok
        assert "Cannot sell current hull" in msg

    def test_cannot_sell_unowned_hull(self, player_ship):
        msg, ok = player_ship.sell_hull("frigate")
        assert not ok
        assert "Don't own" in msg

    def test_sell_unknown_hull(self, player_ship):
        msg, ok = player_ship.sell_hull("nonexistent")
        assert not ok
        assert "Don't own" in msg


# ──────────────────────────────────────────────────────────────────────
# Module installation
# ──────────────────────────────────────────────────────────────────────

class TestModuleInstallation:
    """Installing modules on the player ship."""

    def test_install_known_module(self, player_ship):
        """Installing a valid module adds it to the correct compartment."""
        comp = SHIP_MODULES["cargo_expander"]["comp"]
        before = len(player_ship.compartments[comp]["modules"])
        ok = player_ship.install_module("cargo_expander")
        assert ok
        assert len(player_ship.compartments[comp]["modules"]) == before + 1
        added = [m for m in player_ship.compartments[comp]["modules"]
                 if m.id == "cargo_expander"]
        assert len(added) >= 1

    def test_install_invalid_module(self, player_ship):
        ok = player_ship.install_module("nonexistent")
        assert not ok

    @pytest.mark.parametrize("mod_id", list(SHIP_MODULES))
    def test_all_modules_can_be_installed(self, player_ship, mod_id):
        """Every module in config can be installed somewhere on the ship."""
        ok = player_ship.install_module(mod_id)
        assert ok, f"Failed to install {mod_id}"

    def test_install_from_cargo_consumes_item(self, player_ship):
        """install_module_from_cargo removes the module item from cargo."""
        player_ship.cargo.add("cargo_expander", 1)
        before = player_ship.cargo.has("cargo_expander")
        msg, ok = player_ship.install_module_from_cargo("cargo_expander")
        assert ok, f"install_module_from_cargo failed: {msg}"
        assert player_ship.cargo.has("cargo_expander") == before - 1

    def test_install_from_cargo_fails_without_item(self, player_ship):
        msg, ok = player_ship.install_module_from_cargo("plasma_cannon")
        assert not ok
        assert "No" in msg

    def test_installed_module_appears_in_stats(self, player_ship):
        """Installing a module with cargo_bonus updates effective stats."""
        stats_before = player_ship.get_effective_stats()
        player_ship.install_module("cargo_expander")
        stats_after = player_ship.get_effective_stats()
        assert stats_after["cargo_bonus"] > stats_before["cargo_bonus"]


# ──────────────────────────────────────────────────────────────────────
# Market dynamics
# ──────────────────────────────────────────────────────────────────────

class TestMarketDynamics:
    """Station prices fluctuate based on supply and demand."""

    def test_buy_all_junk_increases_station_stock(self, station, player_ship):
        """buy_all_junk adds raw resources to station inventory."""
        player_ship.cargo.add("ore", 10)
        player_ship.cargo.add("ice", 5)
        inv_before_ore = station.inventory.get("ore", 0)
        inv_before_ice = station.inventory.get("ice", 0)
        station.buy_all_junk(player_ship)
        assert station.inventory.get("ore", 0) > inv_before_ore
        assert station.inventory.get("ice", 0) > inv_before_ice

    def test_buy_all_junk_pays_player(self, station, player_ship):
        """Player receives credits for raw resources sold via buy_all_junk."""
        player_ship.cargo.add("ore", 10)
        credits_before = player_ship.credits
        station.buy_all_junk(player_ship)
        assert player_ship.credits > credits_before

    def test_low_stock_increases_price(self, station, player_ship):
        """Very low stock (< 4) produces a higher price multiplier."""
        station.inventory["metal"] = 2
        station.update_prices()
        sp_low, _ = station.price_for_player("metal", True, player_ship)

        station.inventory["metal"] = 30
        station.update_prices()
        sp_normal, _ = station.price_for_player("metal", True, player_ship)

        assert sp_low > sp_normal

    def test_high_stock_lowers_price(self, station, player_ship):
        """Very high stock (> 40) produces a lower price multiplier."""
        station.inventory["metal"] = 50
        station.update_prices()
        sp_high, _ = station.price_for_player("metal", True, player_ship)

        station.inventory["metal"] = 30
        station.update_prices()
        sp_normal, _ = station.price_for_player("metal", True, player_ship)

        assert sp_high < sp_normal

    def test_dumping_resources_changes_prices(self, station, player_ship):
        """Selling raw resources increases supply and can reduce price."""
        player_ship.cargo.add("ore", 30)
        station.update_prices()
        sp_before, _ = station.price_for_player("ore", True, player_ship)

        station.buy_all_junk(player_ship)
        station.update_prices()
        sp_after, _ = station.price_for_player("ore", True, player_ship)

        assert sp_after <= sp_before

    def test_buy_all_junk_no_raw_returns_message(self, station, player_ship):
        """buy_all_junk with no raw resources returns appropriate failure."""
        player_ship.cargo.items = {"repair_kit": 1}
        msg, ok = station.buy_all_junk(player_ship)
        assert not ok
        assert "No raw" in msg

    def test_update_economy_changes_inventory(self, station):
        """Station.update_economy() consumes/produces per type."""
        inv_before = station.inventory.get("ice", 0)
        station.update_economy()
        # trade_hub consumes ice
        assert station.inventory.get("ice", 0) <= inv_before

    def test_prices_are_recalculated_after_update_economy(self, station):
        """update_economy calls update_prices, so prices stay in sync."""
        station.update_economy()
        for rid in RESOURCES:
            assert rid in station.prices, f"{rid} missing after update"


# ──────────────────────────────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge cases: insufficient credits, cargo space, invalid ids."""

    def test_not_enough_credits_for_any_resource(self, station, empty_ship):
        """Ship with zero credits cannot buy any resource."""
        empty_ship.credits = 0
        for rid in station.inventory:
            if rid in RESOURCES and station.inventory[rid] > 0:
                msg = station.sell_to(empty_ship, rid, 1)
                assert "Need" in msg, f"Expected 'Need' for {rid}, got: {msg}"

    def test_not_enough_cargo_space(self, station, empty_ship):
        """Ship with a full cargo hold cannot buy more."""
        empty_ship.cargo.add("metal", empty_ship.cargo.capacity)
        msg = station.sell_to(empty_ship, "metal", 1)
        assert "Cargo full" in msg

    def test_trade_invalid_resource_id(self, station, player_ship):
        msg = station.sell_to(player_ship, "unicornium", 1)
        assert "Unknown" in msg
        msg = station.buy_from(player_ship, "unicornium", 1)
        assert "Unknown" in msg

    def test_zero_amount_trade_does_not_crash(self, station, player_ship):
        """Trading zero items should not raise an exception."""
        msg = station.sell_to(player_ship, "metal", 0)
        assert isinstance(msg, str)
        msg = station.buy_from(player_ship, "metal", 0)
        assert isinstance(msg, str)

    def test_sell_all_cargo_and_buy_back(self, station, empty_ship):
        """Full round-trip: sell resources, then buy them back."""
        empty_ship.credits = 5000
        empty_ship.cargo.add("metal", 5)
        credits_before = empty_ship.credits
        station.buy_from(empty_ship, "metal", 5)
        assert empty_ship.credits > credits_before
        assert empty_ship.cargo.has("metal") == 0

        credits_mid = empty_ship.credits
        station.sell_to(empty_ship, "metal", 5)
        assert empty_ship.credits < credits_mid
        assert empty_ship.cargo.has("metal") == 5

    def test_exact_credits_for_purchase(self, station, empty_ship):
        """Player can buy with exactly enough credits."""
        empty_ship.credits = 5000
        empty_ship.cargo.add("ice", 5)
        station.buy_from(empty_ship, "ice", 5)
        price, _ = station.price_for_player("metal", True, empty_ship)
        empty_ship.credits = price
        msg = station.sell_to(empty_ship, "metal", 1)
        assert "Bought" in msg

    def test_station_out_of_stock_all_resources(self, station, player_ship):
        """Station with zero inventory cannot sell anything."""
        for rid in RESOURCES:
            station.inventory[rid] = 0
        station.update_prices()
        for rid in RESOURCES:
            msg = station.sell_to(player_ship, rid, 1)
            assert "Only" in msg or "Cargo full" in msg or "blocked" in msg, (
                f"Unexpected message for {rid}: {msg}"
            )
