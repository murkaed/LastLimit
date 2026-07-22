"""Tests for race bonus mechanics."""

import pytest
from models import PlayerShip
from config import RACES


class TestRaceBonuses:
    """Tests that race bonuses are applied correctly to PlayerShip."""

    def test_default_race_is_human(self):
        ship = PlayerShip()
        assert ship.race == "human"
        # Before apply_race_bonus, race_data is empty
        assert ship._race_bonus("accuracy") == 0

    def test_apply_race_bonus_human(self):
        ship = PlayerShip()
        ship.apply_race_bonus("human")
        assert ship.race == "human"
        # Human: +5 accuracy, +3 evasion, +1 shield_regen
        assert ship._race_bonus("accuracy") == 5
        assert ship._race_bonus("evasion") == 3
        assert ship._race_bonus("shield_regen") == 1

    def test_apply_race_bonus_mutant(self):
        ship = PlayerShip()
        original_hull = ship.max_hull
        ship.apply_race_bonus("mutant")
        assert ship.race == "mutant"
        # Mutant: +25 max_hull, +8 damage, +3 power_bonus, -10 accuracy, -5 evasion
        assert ship.max_hull == original_hull + 25
        assert ship._race_bonus("damage") == 8
        assert ship._race_bonus("power_bonus") == 3
        assert ship._race_bonus("accuracy") == -10
        assert ship._race_bonus("evasion") == -5

    def test_apply_race_bonus_xenos(self):
        ship = PlayerShip()
        original_hull = ship.max_hull
        ship.apply_race_bonus("xenos_bio")
        # Xenos: +8 evasion, +1 speed, +3 sensor, -15 max_hull, -3 damage
        assert ship.max_hull == original_hull - 15
        assert ship._race_bonus("evasion") == 8
        assert ship._race_bonus("speed") == 1
        assert ship._race_bonus("sensor_range") == 3
        assert ship._race_bonus("damage") == -3

    def test_apply_race_bonus_machine(self):
        ship = PlayerShip()
        ship.apply_race_bonus("machine_cult")
        # Machine: +10 accuracy, +5 power_bonus, +10 shield_cap, -5 evasion, -1 speed
        assert ship._race_bonus("accuracy") == 10
        assert ship._race_bonus("power_bonus") == 5
        assert ship._race_bonus("shield_cap") == 10
        assert ship._race_bonus("evasion") == -5
        assert ship._race_bonus("speed") == -1

    def test_apply_race_bonus_voidborn(self):
        ship = PlayerShip()
        ship.apply_race_bonus("voidborn")
        # Voidborn: +15 shield_cap, +3 shield_regen, +5 evasion, -1 speed, -5 accuracy
        assert ship._race_bonus("shield_cap") == 15
        assert ship._race_bonus("shield_regen") == 3
        assert ship._race_bonus("evasion") == 5
        assert ship._race_bonus("speed") == -1
        assert ship._race_bonus("accuracy") == -5

    def test_race_bonus_affects_get_effective_stats(self):
        ship = PlayerShip()
        # Apply starter modules so stats are populated
        ship.apply_race_bonus("human")
        stats = ship.get_effective_stats()
        # Human: +5 accuracy, +3 evasion, +1 shield_regen
        assert stats["accuracy"] >= 5
        assert stats["evasion"] >= 3
        assert stats["shield_regen"] >= 1

    def test_race_bonus_affects_power_generated(self):
        ship = PlayerShip()
        ship.apply_race_bonus("machine_cult")
        # Machine: +5 power_bonus
        power = ship.total_power_generated()
        # Reactor gives power, plus race bonus
        assert power >= 5

    def test_race_bonus_applied_via_select_race(self, monkeypatch):
        """Simulate the GalaxyMapApp.select_race flow."""
        ship = PlayerShip()
        # Simulate what galaxy_map.py does
        race_id = "mutant"
        ship.race = race_id
        ship.apply_race_bonus()
        assert ship._race_bonus("damage") == 8
        assert ship.max_hull > 100  # +25 from base corvette hull

    def test_unknown_race_falls_back_to_human(self):
        ship = PlayerShip()
        ship.apply_race_bonus("nonexistent")
        # Falls back to human in apply_race_bonus (RACES.get fallback)
        assert ship.race == "nonexistent"  # race string is still set
        # But bonuses are human's (fallback)
        assert ship._race_bonus("accuracy") == 5  # human bonus

    def test_race_data_is_dict(self):
        ship = PlayerShip()
        ship.apply_race_bonus("human")
        assert isinstance(ship.race_data, dict)
        assert "accuracy" in ship.race_data

    def test_all_races_have_valid_names(self):
        for rid, cfg in RACES.items():
            assert "name" in cfg
            assert "desc" in cfg
            assert "bonus" in cfg
            assert "penalty" in cfg
