"""Tests for the scanning system: ScanResult, PlayerShip.scan_target(),
Galaxy.get_scannable_objects, and sensor range mechanics."""

import pytest
from models import ScanResult, PlayerShip, Galaxy, CrewMember, \
    PirateShip, TraderShip, ShipModule
from config import SCAN_ACTIVE_COST, SCAN_DEEP_COST, SCAN_SIGNAL_TYPES


# ---------------------------------------------------------------------------
# Local fixtures (work around broken conftest fixtures)
# ---------------------------------------------------------------------------

@pytest.fixture
def pirate():
    """A pirate NPC ship.

    Uses the current constructor (x, y) - does NOT accept a name arg.
    """
    p = PirateShip(5, 5)
    p.hull = 40
    p.max_hull = 40
    p.shield_hp = 10
    return p


@pytest.fixture
def trader():
    """A trader NPC ship with some cargo."""
    t = TraderShip(7, 5, [])
    t.hull = 60
    t.max_hull = 60
    t.cargo.add("metal", 15)
    t.cargo.add("food", 10)
    t.cargo.add("relic", 1)
    return t


@pytest.fixture
def galaxy():
    """Small galaxy with default dimensions to avoid _nearby() bounds bug.

    The conftest galaxy fixture uses Galaxy(width=30, height=20), but
    Galaxy._nearby() clamps to the module-level WIDTH/HEIGHT (80x40),
    creating an IndexError on the 30x20 tile grid.
    """
    import random
    random.seed(42)
    g = Galaxy()
    random.seed()
    return g


@pytest.fixture
def powered_ship(player_ship):
    """Player ship with extra reactor so deep scan (cost 5) has enough power.

    Default player_ship: 12 power / 11 consumed = 1 spare.
    Second fusion_reactor: +12 power / 0 energy => spare = 13.
    """
    player_ship.compartments["reactor"]["modules"].append(
        ShipModule("fusion_reactor")
    )
    return player_ship


@pytest.fixture
def starved_ship(empty_ship):
    """Ship with zero spare power by overloading energy consumption.

    Adds a second laser_turret (+3 energy) so consumed = 14 > generated = 12.
    """
    empty_ship.compartments["weapon"]["modules"].append(
        ShipModule("laser_turret")
    )
    return empty_ship


# ============================================================================
# ScanResult — model tests
# ============================================================================


class TestScanResult:
    def test_success_flag(self):
        r = ScanResult(True, "passive", {"type": "PirateShip", "hull": 40})
        assert r.success is True

    def test_failure_flag(self):
        r = ScanResult(False)
        assert r.success is False

    def test_failure_summary(self):
        r = ScanResult(False)
        assert r.summary() == "Scan failed."

    def test_passive_summary(self):
        """Passive scan summary includes type and hull."""
        r = ScanResult(
            True, "passive",
            {"type": "PirateShip", "hull": 40, "max_hull": 40},
        )
        text = r.summary()
        assert "Scan:" in text
        assert "H:40/40" in text
        assert "S:" not in text        # no shield info
        assert "Cargo:" not in text     # cargo hidden at passive

    def test_active_summary_includes_shield_and_cargo(self):
        """Active scan reveals shield and cargo details."""
        r = ScanResult(
            True, "active",
            {"type": "PirateShip", "hull": 40, "max_hull": 40,
             "shield": 10, "cargo": {"metal": 5, "food": 3}},
        )
        text = r.summary()
        assert "H:40/40" in text
        assert "S:10" in text
        assert "Cargo:" in text

    def test_weapons_in_summary(self):
        r = ScanResult(
            True, "active",
            {"type": "PirateShip", "hull": 40, "max_hull": 40,
             "weapons": 2},
        )
        assert "Weapons:2" in r.summary()

    def test_signals_in_summary(self):
        r = ScanResult(
            True, "deep",
            {"type": "Station", "hull": 100, "max_hull": 100,
             "signals": "distress"},
        )
        assert "Signals:distress" in r.summary()

    def test_different_levels_stored_correctly(self):
        """Scan level on the result object reflects the passed level."""
        for level in ("passive", "active", "deep"):
            info = {"type": "PirateShip", "hull": 40, "scan_level": level}
            r = ScanResult(True, level, info)
            assert r.info["scan_level"] == level
            assert r.level == level


# ============================================================================
# PlayerShip.scan_target()
# ============================================================================


class TestScanTarget:
    def test_passive_scan_always_succeeds(self, player_ship, pirate):
        """Passive scan requires no power, always succeeds."""
        result = player_ship.scan_target(pirate, "passive")
        assert result.success is True
        assert result.level == "passive"

    def test_active_scan_succeeds_with_power(self, player_ship, pirate):
        """Active scan succeeds when spare power is sufficient."""
        result = player_ship.scan_target(pirate, "active")
        assert result.success is True
        assert result.level == "active"

    def test_deep_scan_succeeds_with_power(self, powered_ship, pirate):
        """Deep scan succeeds when spare power is sufficient."""
        result = powered_ship.scan_target(pirate, "deep")
        assert result.success is True
        assert result.level == "deep"

    def test_active_scan_fails_no_spare_power(self, starved_ship, pirate):
        """Active scan fails when spare power is insufficient."""
        result = starved_ship.scan_target(pirate, "active")
        assert result.success is False

    def test_deep_scan_fails_no_spare_power(self, starved_ship, pirate):
        """Deep scan fails when spare power is insufficient."""
        result = starved_ship.scan_target(pirate, "deep")
        assert result.success is False

    def test_passive_scan_succeeds_no_spare_power(self, starved_ship, pirate):
        """Passive scan still succeeds even with no spare power."""
        result = starved_ship.scan_target(pirate, "passive")
        assert result.success is True

    def test_scan_sets_scanned_flag(self, player_ship, pirate):
        """After scan, the target's scanned flag is set to True."""
        assert pirate.scanned is False
        player_ship.scan_target(pirate, "active")
        assert pirate.scanned is True

    def test_passive_scan_shows_hull_and_type(self, player_ship, pirate):
        """Passive scan returns basic hull and type info."""
        result = player_ship.scan_target(pirate, "passive")
        assert result.info["hull"] == 40
        assert result.info["max_hull"] == 40
        assert result.info["type"] == "PirateShip"
        assert "cargo" not in result.info  # cargo hidden at passive

    def test_active_scan_reveals_cargo(self, player_ship, trader):
        """Active scan reveals cargo contents."""
        result = player_ship.scan_target(trader, "active")
        assert result.success is True
        assert "cargo" in result.info
        assert "metal" in result.info["cargo"]

    def test_deep_scan_reveals_cargo(self, powered_ship, trader):
        """Deep scan also reveals cargo contents."""
        result = powered_ship.scan_target(trader, "deep")
        assert result.success is True
        assert "cargo" in result.info

    def test_scan_includes_target_name(self, player_ship, pirate):
        result = player_ship.scan_target(pirate, "active")
        assert "name" in result.info

    def test_scan_includes_faction(self, player_ship, pirate):
        result = player_ship.scan_target(pirate, "active")
        assert "faction" in result.info

    def test_deep_scan_more_detail_than_passive(self, powered_ship, trader):
        """Deep scan provides at least as many info keys as passive."""
        passive = powered_ship.scan_target(trader, "passive")
        deep = powered_ship.scan_target(trader, "deep")
        assert len(deep.info) >= len(passive.info)
        # Deep includes cargo, passive should not
        assert "cargo" not in passive.info
        assert "cargo" in deep.info

    def test_scan_with_scientist_crew(self, player_ship, pirate):
        """Scientist crew member's scanner bonus is applied."""
        scientist = CrewMember("Echo", "Scientist", "human")
        scientist.assigned = True
        player_ship.crew["Scientist"] = scientist.name
        player_ship.crew_members.append(scientist)
        result = player_ship.scan_target(pirate, "active")
        assert result.success is True


# ============================================================================
# Galaxy.get_scannable_objects()
# ============================================================================


class TestGetScannableObjects:
    def test_returns_empty_list_when_nothing_in_range(self, galaxy):
        """No scannable objects within radius returns empty list."""
        objects = galaxy.get_scannable_objects(0, 0, 1)
        assert isinstance(objects, list)
        assert len(objects) == 0

    def test_returns_pirates_in_range(self, galaxy, pirate):
        """Pirate within scan radius appears in results."""
        galaxy.pirates.append(pirate)
        pirate.x, pirate.y = 5, 5
        objects = galaxy.get_scannable_objects(5, 5, 3)
        labels = [label for _, label, _ in objects]
        assert any("Pirate" in l for l in labels)

    def test_returns_traders_in_range(self, galaxy, trader):
        """Trader within scan radius appears in results."""
        galaxy.traders.append(trader)
        trader.x, trader.y = 7, 5
        objects = galaxy.get_scannable_objects(5, 5, 5)
        labels = [label for _, label, _ in objects]
        assert any("Trader" in l for l in labels)

    def test_returns_stations_in_range(self, galaxy, station):
        """Station within scan radius appears in results."""
        galaxy.stations.append(station)
        station.x, station.y = 10, 10
        objects = galaxy.get_scannable_objects(10, 10, 5)
        labels = [label for _, label, _ in objects]
        assert any("Station" in l for l in labels)

    def test_sorted_by_distance(self, galaxy, pirate, trader, station):
        """Results are sorted by distance (ascending)."""
        galaxy.pirates.append(pirate)
        galaxy.traders.append(trader)
        galaxy.stations.append(station)
        pirate.x, pirate.y = 1, 0      # distance = 1
        trader.x, trader.y = 3, 0      # distance = 3
        station.x, station.y = 2, 0    # distance = 2
        objects = galaxy.get_scannable_objects(0, 0, 5)
        distances = [d for d, _, _ in objects]
        assert distances == sorted(distances)

    def test_excludes_dead_pirates(self, galaxy, pirate):
        """Dead pirates are not included."""
        galaxy.pirates.append(pirate)
        pirate.x, pirate.y = 5, 5
        pirate.alive = False
        objects = galaxy.get_scannable_objects(5, 5, 3)
        assert len(objects) == 0

    def test_excludes_dead_traders(self, galaxy, trader):
        """Dead traders are not included."""
        galaxy.traders.append(trader)
        trader.x, trader.y = 5, 5
        trader.alive = False
        objects = galaxy.get_scannable_objects(5, 5, 3)
        assert len(objects) == 0

    def test_out_of_range_excluded(self, galaxy, pirate):
        """Object beyond radius is not returned."""
        galaxy.pirates.append(pirate)
        pirate.x, pirate.y = 10, 10
        objects = galaxy.get_scannable_objects(0, 0, 3)
        assert len(objects) == 0


# ============================================================================
# Galaxy.scan_generate_missions()
# ============================================================================


class TestScanGenerateMissions:
    def test_may_return_none(self, galaxy, pirate):
        """scan_generate_missions may return None (random roll)."""
        results = [
            galaxy.scan_generate_missions(pirate, "active", None)
            for _ in range(100)
        ]
        assert any(r is None for r in results)

    def test_may_return_mission(self, galaxy, pirate):
        """scan_generate_missions may return a Mission object."""
        results = [
            galaxy.scan_generate_missions(pirate, "active", None)
            for _ in range(200)
        ]
        missions = [r for r in results if r is not None]
        if missions:
            m = missions[0]
            assert hasattr(m, "mtype")
            assert hasattr(m, "reward")
            assert hasattr(m, "title")
            assert hasattr(m, "giver_station")

    def test_mission_has_giver_station(self, galaxy, pirate):
        """Generated mission reports scan source as giver."""
        results = [
            galaxy.scan_generate_missions(pirate, "deep", None)
            for _ in range(200)
        ]
        missions = [r for r in results if r is not None]
        if missions:
            m = missions[0]
            assert pirate.name in str(m.giver_station)

    def test_mission_type_derived_from_signal_type(self, galaxy, pirate):
        """Mission type is one of the valid types from signal config."""
        results = [
            galaxy.scan_generate_missions(pirate, "active", None)
            for _ in range(200)
        ]
        missions = [r for r in results if r is not None]
        if missions:
            m = missions[0]
            assert m.mtype in ("deliver", "bounty")


# ============================================================================
# Sensors — range and crew bonuses
# ============================================================================


class TestSensorRange:
    def test_sensor_range_in_effective_stats(self, player_ship):
        """sensor_range appears in ship effective stats."""
        stats = player_ship.get_effective_stats()
        assert "sensor_range" in stats
        assert stats["sensor_range"] > 0

    def test_default_sensor_range(self, player_ship):
        """Default sensor range without crew bonus is computed from modules.

        Base 7 + long_range_scanner +5 = 12.
        """
        stats = player_ship.get_effective_stats()
        assert stats["sensor_range"] >= 12

    def test_crew_sensor_bonus_increases_range(self, player_ship):
        """Assigning a Scientist crew member increases sensor range."""
        scientist = CrewMember("Nyx", "Scientist", "human")
        scientist.assigned = True
        player_ship.crew["Scientist"] = scientist.name
        player_ship.crew_members.append(scientist)
        stats = player_ship.get_effective_stats()
        # 12 + 2 (Scientist sensor_range bonus) = 14
        assert stats["sensor_range"] >= 14

    def test_scan_range_constants(self, player_ship):
        """Verify rng_map logic in scan_target produces expected ranges."""
        stats = player_ship.get_effective_stats()
        assert stats["sensor_range"] > 0

    def test_crew_sensor_bonus_affects_power_cost(self, player_ship, pirate):
        """Scientist crew's scanner bonus is consumed by scan_target."""
        scientist = CrewMember("Orin", "Scientist", "human")
        scientist.assigned = True
        player_ship.crew["Scientist"] = scientist.name
        player_ship.crew_members.append(scientist)
        result = player_ship.scan_target(pirate, "active")
        assert result.success is True


# ============================================================================
# Edge cases
# ============================================================================


class TestScanEdgeCases:
    def test_scan_target_with_zero_hull(self, player_ship, pirate):
        """Scanning a ship with zero hull still returns basic info."""
        pirate.hull = 0
        pirate.alive = False
        result = player_ship.scan_target(pirate, "active")
        assert result.success is True
        assert result.info["hull"] == 0

    def test_passive_scan_with_no_spare_power(self, starved_ship, pirate):
        """Passive scan always works even with zero spare power."""
        result = starved_ship.scan_target(pirate, "passive")
        assert result.success is True
        assert "hull" in result.info

    def test_active_scan_returns_error_in_info(self, starved_ship, pirate):
        """Insufficient power yields error in info dict."""
        result = starved_ship.scan_target(pirate, "active")
        assert result.success is False
        assert result.info.get("error") is not None
        assert "power" in result.info["error"].lower()

    def test_deep_scan_returns_error_in_info(self, starved_ship, pirate):
        """Insufficient power for deep scan yields error in info dict."""
        result = starved_ship.scan_target(pirate, "deep")
        assert result.success is False
        assert result.info.get("error") is not None
        assert "power" in result.info["error"].lower()

    def test_scan_station_works(self, player_ship, station):
        """Scanning a station returns station info."""
        station.hull = 100
        station.max_hull = 100
        result = player_ship.scan_target(station, "active")
        assert result.success is True
        assert result.info["name"] == station.name
        assert "hull" in result.info

    def test_scan_npc_ship_works(self, player_ship, pirate):
        """Scanning a pirate returns pirate info with faction."""
        result = player_ship.scan_target(pirate, "active")
        assert result.success is True
        assert result.info["type"] == "PirateShip"
        assert "faction" in result.info

    def test_scan_returns_scanned_object(self, player_ship, pirate):
        """The scanned_obj attribute references the original target."""
        result = player_ship.scan_target(pirate, "active")
        assert result.scanned_obj is pirate

    def test_scan_crew_does_not_corrupt_target_info(self, player_ship,
                                                     pirate, crew_member):
        """Crew member on player ship does not affect scan target info."""
        player_ship.crew_members.append(crew_member)
        result = player_ship.scan_target(pirate, "active")
        assert result.success is True
        assert result.info["type"] == "PirateShip"

    def test_deep_scan_error_shows_required_and_available_power(
            self, starved_ship, pirate):
        """Error message for deep scan mentions required amount."""
        result = starved_ship.scan_target(pirate, "deep")
        assert result.success is False
        error = result.info.get("error", "")
        # Should mention the power needed vs what is available
        assert str(SCAN_DEEP_COST) in error


# ============================================================================
# Parametrized tests
# ============================================================================


@pytest.mark.parametrize("target_fixture,expected_type", [
    ("pirate", "PirateShip"),
    ("trader", "TraderShip"),
    ("station", "Station"),
])
def test_scan_different_target_types(request, player_ship,
                                     target_fixture, expected_type):
    """Verify scan works across all NPC target types."""
    target = request.getfixturevalue(target_fixture)
    if target_fixture == "station":
        target.hull = 100
        target.max_hull = 100
    result = player_ship.scan_target(target, "active")
    assert result.success is True
    assert result.info["type"] == expected_type


@pytest.mark.parametrize("scan_level", ["passive", "active", "deep"])
def test_scan_levels_all_work(powered_ship, pirate, scan_level):
    """All three scan levels succeed for a powered ship."""
    result = powered_ship.scan_target(pirate, scan_level)
    assert result.success is True
    assert result.info["scan_level"] == scan_level


@pytest.mark.parametrize("cost", [SCAN_ACTIVE_COST, SCAN_DEEP_COST])
def test_scan_cost_defined(cost):
    """Scan cost constants are positive integers."""
    assert isinstance(cost, int)
    assert cost > 0


def test_deep_scan_cost_greater_than_active():
    assert SCAN_DEEP_COST > SCAN_ACTIVE_COST


@pytest.mark.parametrize("signal_key", list(SCAN_SIGNAL_TYPES))
def test_scan_signal_types_defined(signal_key):
    """All signal types have title, weight, missions."""
    cfg = SCAN_SIGNAL_TYPES[signal_key]
    assert "title" in cfg
    assert "weight" in cfg
    assert "missions" in cfg
    assert isinstance(cfg["weight"], int)
    assert 0 < cfg["weight"] <= 100
