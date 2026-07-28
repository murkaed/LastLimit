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
        assert hasattr(ui, "TacticalScreen")
        assert hasattr(ui, "ShipHubScreen")

    def test_galaxy_map(self):
        import galaxy_map
        assert hasattr(galaxy_map, "GalaxyMapApp")

    def test_game_controller(self):
        from game_controller import GameController, GameState
        assert hasattr(GameState, "PLAYING")


class TestAppCreate:
    def test_create_no_crash(self):
        from galaxy_map import GalaxyMapApp
        app = GalaxyMapApp()
        assert app.ship.name == "Endeavour"
        assert app.ship.hull == 100

    def test_render_help(self):
        from game_controller import GameController
        ctrl = GameController()
        result = ctrl.render_help_screen()
        assert "HELP" in result
        assert "MOVEMENT" in result


class TestRollHit:
    def test_hit_chance_100(self):
        from game_controller import GameController
        hits = sum(GameController._roll_hit(100, 0) for _ in range(200))
        assert hits > 150  # should hit most of the time

    def test_hit_chance_0(self):
        from game_controller import GameController
        hits = sum(GameController._roll_hit(5, 95) for _ in range(200))
        assert hits < 50  # floor 5% chance

    def test_accuracy_minus_evasion(self):
        from game_controller import GameController
        random.seed(123)
        hits = 0
        for _ in range(1000):
            if GameController._roll_hit(50, 20):
                hits += 1
        assert 200 < hits < 400  # ~300 expected

    def test_clamped_to_5_95(self):
        from game_controller import GameController
        random.seed(456)
        hits = sum(GameController._roll_hit(0, 200) for _ in range(500))
        assert 10 < hits < 50  # ~25 expected
        misses = sum(not GameController._roll_hit(200, 0) for _ in range(500))
        assert 10 < misses < 50  # ~25 expected


class TestDirectionName:
    def test_all(self):
        from game_controller import GameController
        assert GameController._direction_name(0, -1) == "N"
        assert GameController._direction_name(0, 1) == "S"
        assert GameController._direction_name(-1, 0) == "W"
        assert GameController._direction_name(1, 0) == "E"
        assert GameController._direction_name(-1, -1) == "NW"
        assert GameController._direction_name(1, -1) == "NE"
        assert GameController._direction_name(-1, 1) == "SW"
        assert GameController._direction_name(1, 1) == "SE"


class TestScanNearby:
    def test_returns_string(self):
        from game_controller import GameController
        ctrl = GameController()
        result = ctrl._scan_nearby()
        assert isinstance(result, str)

    def test_empty_galaxy(self):
        from game_controller import GameController
        ctrl = GameController()
        ctrl.galaxy.objects = {}
        ctrl.galaxy.traders = []
        ctrl.galaxy.pirates = []
        ctrl.galaxy.stations = []
        ctrl.player_x = 40
        ctrl.player_y = 20
        result = ctrl._scan_nearby()
        assert "Nothing" in result
