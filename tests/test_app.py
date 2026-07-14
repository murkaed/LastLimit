"""Smoke tests — verify app can be imported and initialized without crashing."""

import pytest


class TestImports:
    def test_import_config(self):
        import config
        assert config.WIDTH == 80

    def test_import_models(self):
        import models
        assert hasattr(models, "CargoHold")
        assert hasattr(models, "PlayerShip")
        assert hasattr(models, "Galaxy")

    def test_import_game_logger(self):
        import game_logger
        assert hasattr(game_logger, "GameLogger")

    def test_import_ui(self):
        import ui
        assert hasattr(ui, "CommandScreen")
        assert hasattr(ui, "BridgeScreen")

    def test_import_galaxy_map_no_crash(self):
        """Verify galaxy_map imports without crashing (no TUI started)."""
        import galaxy_map
        assert hasattr(galaxy_map, "GalaxyMapApp")
        assert hasattr(galaxy_map, "GameState")


class TestGalaxyMapInit:
    def test_app_creation_no_crash(self):
        from galaxy_map import GalaxyMapApp
        app = GalaxyMapApp()
        assert app.ship.name == "Endeavour"
        assert app.ship.hull == 100
        assert app.state is not None
        assert app.galaxy is not None

    def test_update_map_no_crash_without_screen(self):
        """update_map requires a mounted app — verify it doesn't crash at init time."""
        from galaxy_map import GalaxyMapApp
        app = GalaxyMapApp()
        # Without compose/on_mount, query_one will fail. Test that the
        # render methods produce strings without errors.
        result = app.render_help_screen()
        assert "HELP" in result

    def test_update_info_no_crash_without_screen(self):
        from galaxy_map import GalaxyMapApp
        app = GalaxyMapApp()
        # Test that helper methods work
        app.ship.race = "mutant"
        status = app._get_ship_status()
        assert isinstance(status, list)


class TestDirectionName:
    def test_all_directions(self):
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
        import models
        models.NPCShip_id_counter = 0
        app = GalaxyMapApp()
        result = app._scan_nearby()
        assert isinstance(result, str)

    def test_returns_nothing_when_empty(self):
        from galaxy_map import GalaxyMapApp
        import models
        models.NPCShip_id_counter = 0
        app = GalaxyMapApp()
        # Place player far from everything
        app.galaxy = type(app.galaxy).__new__(app.galaxy.__class__)
        app.galaxy.width = 80
        app.galaxy.height = 40
        app.galaxy.tiles = [["·"] * 80 for _ in range(40)]
        app.galaxy.objects = {}
        app.galaxy.traders = []
        app.galaxy.pirates = []
        app.galaxy.stations = []
        app.player_x = 40
        app.player_y = 20
        result = app._scan_nearby()
        assert "Nothing" in result
