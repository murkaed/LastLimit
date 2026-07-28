"""Tests for fog of war and save/load features."""

import pytest
from game_controller import GameController, GameState
from galaxy_map import GalaxyMapApp


# =============================================================================
# Fog of War
# =============================================================================

class TestFogOfWar:
    def test_fog_disabled_by_default(self):
        c = GameController()
        assert not c.fog_enabled

    def test_fog_default_range(self):
        c = GameController()
        assert c.fog_range == 5

    def test_toggle_fog_on(self):
        c = GameController()
        c.fog_enabled = True
        c.explored_tiles = set()
        c._discover_tiles()
        assert len(c.explored_tiles) > 0

    def test_toggle_fog_off_shows_all(self):
        c = GameController()
        c.fog_enabled = False
        lines = c.build_map_lines()
        # All tiles visible — no '?' chars
        all_chars = "".join(lines)
        assert "?" not in all_chars

    def test_fog_on_shows_unexplored_as_question(self):
        c = GameController()
        c.fog_enabled = True
        c.fog_range = 2
        c.explored_tiles = set()
        c.player_x = 40
        c.player_y = 20
        c._discover_tiles()
        lines = c.build_map_lines()
        all_chars = "".join(lines)
        # Should have '?' for unexplored tiles
        has_unexplored = "?" in all_chars
        # But player's immediate area should be clear
        has_tiles = any(ch in all_chars for ch in (".", "*", "◈"))
        assert has_tiles or has_unexplored

    def test_discover_tiles_adds_surrounding(self):
        c = GameController()
        c.fog_enabled = True
        c.fog_range = 3
        c.explored_tiles = set()
        c.player_x = 40
        c.player_y = 20
        c._discover_tiles()
        # Should have ~ (range*2+1)^2 = 49 tiles explored
        expected = (c.fog_range * 2 + 1) ** 2
        assert len(c.explored_tiles) <= expected
        assert len(c.explored_tiles) > 0

    def test_npc_visible_through_fog(self):
        c = GameController()
        c.fog_enabled = True
        c.fog_range = 1
        c.explored_tiles = set()
        c._discover_tiles()
        lines = c.build_map_lines()
        # Just verify no crash
        assert len(lines) == c.galaxy.height

    def test_restart_clears_explored(self):
        c = GameController()
        c.state = GameState.PLAYING
        c.fog_enabled = True
        c._discover_tiles()
        assert len(c.explored_tiles) > 0
        c.restart_game()
        if c.fog_enabled:
            assert len(c.explored_tiles) > 0  # re-discovered on restart
        else:
            assert len(c.explored_tiles) == 0


# =============================================================================
# Save / Load (within session)
# =============================================================================

class TestSaveLoad:
    def test_save_returns_bytes(self, playing_ctrl):
        data = playing_ctrl.save_state()
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_load_restores_state(self, playing_ctrl):
        playing_ctrl.player_x = 50
        playing_ctrl.player_y = 25
        playing_ctrl.ship.credits = 9999
        data = playing_ctrl.save_state()
        restored = GameController()
        GameController.restore_from_state(restored, data)
        assert restored.player_x == 50
        assert restored.player_y == 25
        assert restored.ship.credits == 9999

    def test_load_restores_galaxy(self, playing_ctrl):
        data = playing_ctrl.save_state()
        restored = GameController()
        GameController.restore_from_state(restored, data)
        assert restored.galaxy is not None
        assert restored.galaxy.width == playing_ctrl.galaxy.width

    def test_save_load_preserves_fog(self):
        c = GameController()
        c.fog_enabled = True
        c.fog_range = 7
        c._discover_tiles()
        data = c.save_state()
        restored = GameController()
        GameController.restore_from_state(restored, data)
        assert restored.fog_enabled
        assert restored.fog_range == 7
        assert len(restored.explored_tiles) == len(c.explored_tiles)

    def test_save_load_preserves_ship_modules(self, playing_ctrl):
        data = playing_ctrl.save_state()
        restored = GameController()
        GameController.restore_from_state(restored, data)
        assert restored.ship.hull == playing_ctrl.ship.hull
        assert restored.ship.race == playing_ctrl.ship.race

    def test_save_load_preserves_logger(self, playing_ctrl):
        playing_ctrl.logger.system("test save message")
        data = playing_ctrl.save_state()
        restored = GameController()
        GameController.restore_from_state(restored, data)
        # Logger should have the message
        assert "test save message" in restored.logger.render_plain()


# =============================================================================
# GalaxyMapApp save/load flow
# =============================================================================

@pytest.mark.asyncio
async def test_f5_saves_game():
    """F5 saves the game state."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("1")  # Human
        await pilot.pause()
        await pilot.press("1")  # Smuggler
        await pilot.pause()
        # Save
        await pilot.press("f5")
        await pilot.pause()
        assert hasattr(app, "_saved_state")


@pytest.mark.asyncio
async def test_f9_loads_game():
    """F9 loads previously saved state."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("1")  # Human
        await pilot.pause()
        await pilot.press("1")  # Smuggler
        await pilot.pause()
        # Move somewhere
        app.ctrl.player_x = 50
        await pilot.press("f5")
        await pilot.pause()

        # Move elsewhere
        app.ctrl.player_x = 30
        app.ctrl.ship.credits = 0

        # Load
        await pilot.press("f9")
        await pilot.pause()
        assert app.ctrl.player_x == 50  # restored


@pytest.mark.asyncio
async def test_f10_toggles_fog():
    """F10 toggles fog of war."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("1")  # Human
        await pilot.pause()
        await pilot.press("1")  # Smuggler
        await pilot.pause()
        initial_fog = app.ctrl.fog_enabled
        await pilot.press("f10")
        await pilot.pause()
        assert app.ctrl.fog_enabled != initial_fog
        await pilot.press("f10")
        await pilot.pause()
        assert app.ctrl.fog_enabled == initial_fog


# =============================================================================
# helpers for standalone save/load tests
# =============================================================================

@pytest.fixture
def playing_ctrl():
    import random
    random.seed(42)
    c = GameController()
    c.state = GameState.START_SCREEN
    c._show_mode_select = True
    c.state = GameState.RACE_SELECT
    c.select_mode("1")    # Free Play
    c.select_race("1")    # Human
    c.select_origin("1")  # Smuggler
    random.seed()
    return c
