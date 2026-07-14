"""Tests for galaxy_map.py — app-level logic (non-TUI)."""

import pytest
import random


class TestImports:
    def test_config(self):
        import config
        assert config.WIDTH == 80

    def test_models(self):
        import models
        assert hasattr(models, "CargoHold")
        assert hasattr(models, "Galaxy")

    def test_game_logger(self):
        import game_logger
        assert hasattr(game_logger, "GameLogger")

    def test_ui(self):
        import ui
        assert hasattr(ui, "BridgeScreen")

    def test_galaxy_map(self):
        import galaxy_map
        assert hasattr(galaxy_map, "GalaxyMapApp")


class TestAppCreate:
    def test_create_no_crash(self):
        from galaxy_map import GalaxyMapApp
        app = GalaxyMapApp()
        assert app.ship.name == "Endeavour"
        assert app.ship.hull == 100

    def test_render_help(self):
        from galaxy_map import GalaxyMapApp
        app = GalaxyMapApp()
        result = app.render_help_screen()
        assert "HELP" in result
        assert "WASD" in result or "MOVEMENT" in result


class TestRollHit:
    def test_hit_chance_100(self):
        from galaxy_map import GalaxyMapApp
        hits = sum(GalaxyMapApp._roll_hit(100, 0) for _ in range(200))
        assert hits > 150  # should hit most of the time

    def test_hit_chance_0(self):
        from galaxy_map import GalaxyMapApp
        hits = sum(GalaxyMapApp._roll_hit(5, 95) for _ in range(200))
        assert hits < 50  # floor 5% chance

    def test_accuracy_minus_evasion(self):
        from galaxy_map import GalaxyMapApp
        random.seed(123)
        # accuracy 50, evasion 20 → 30% hit
        hits = 0
        for _ in range(1000):
            if GalaxyMapApp._roll_hit(50, 20):
                hits += 1
        assert 200 < hits < 400  # ~300 expected

    def test_clamped_to_5_95(self):
        from galaxy_map import GalaxyMapApp
        random.seed(456)
        # Even with acc=0, ev=200, floor is 5%
        hits = sum(GalaxyMapApp._roll_hit(0, 200) for _ in range(500))
        assert 10 < hits < 50  # ~25 expected
        # Even with acc=200, ev=0, cap is 95%
        misses = sum(not GalaxyMapApp._roll_hit(200, 0) for _ in range(500))
        assert 10 < misses < 50  # ~25 expected


class TestDirectionName:
    def test_all(self):
        from galaxy_map import GalaxyMapApp
        assert GalaxyMapApp._direction_name(0, -1) == "N"
        assert GalaxyMapApp._direction_name(0, 1) == "S"
        assert GalaxyMapApp._direction_name(-1, 0) == "W"
        assert GalaxyMapApp._direction_name(1, 0) == "E"
        assert GalaxyMapApp._direction_name(-1, -1) == "NW"
        assert GalaxyMapApp._direction_name(1, -1) == "NE"
        assert GalaxyMapApp._direction_name(-1, 1) == "SW"
        assert GalaxyMapApp._direction_name(1, 1) == "SE"


class TestScanNearby:
    def test_returns_string(self):
        from galaxy_map import GalaxyMapApp
        app = GalaxyMapApp()
        result = app._scan_nearby()
        assert isinstance(result, str)

    def test_empty_galaxy(self):
        from galaxy_map import GalaxyMapApp
        app = GalaxyMapApp()
        app.galaxy.objects = {}
        app.galaxy.traders = []
        app.galaxy.pirates = []
        app.galaxy.stations = []
        app.player_x = 40
        app.player_y = 20
        result = app._scan_nearby()
        assert "Nothing" in result
