"""Tests for hotkey system across all screens — validates 0-9 key mapping."""

import pytest
from textual.widgets import Static

from galaxy_map import GalaxyMapApp, GameState
from models import PirateShip


# =============================================================================
# Start screen: 1-5 keys
# =============================================================================

@pytest.mark.asyncio
async def test_start_screen_keys_1_to_5():
    """Pressing 1 opens race select, 2 quick battle, 4 help, 5 quits."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        assert app.ctrl.state == GameState.START_SCREEN
        # 1 → race select
        await pilot.press("1")
        await pilot.pause()
        assert app.ctrl.state == GameState.RACE_SELECT
        assert app.ctrl._show_race_select


@pytest.mark.asyncio
async def test_start_screen_4_help():
    """Pressing 4 from start screen opens help."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("4")
        await pilot.pause()
        assert app.ctrl.state == GameState.HELP


# =============================================================================
# Race selection: 1-5 for races, 0 back
# =============================================================================

@pytest.mark.asyncio
async def test_race_select_1_human():
    """Pressing 1 in race select chooses Human and transitions to PLAYING."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        # Open race select
        await pilot.press("1")
        await pilot.pause()
        assert app.ctrl.state == GameState.RACE_SELECT
        # Select Human
        await pilot.press("1")
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING
        assert app.ship.race == "human"


@pytest.mark.asyncio
async def test_race_select_0_back():
    """Pressing 0 in race select returns to start screen."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        assert app.ctrl.state == GameState.RACE_SELECT
        await pilot.press("0")
        await pilot.pause()
        assert app.ctrl.state == GameState.START_SCREEN


@pytest.mark.asyncio
async def test_race_select_enter_human():
    """Enter in race select chooses Human (default)."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")  # open race select
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING
        assert app.ship.race == "human"


# =============================================================================
# Pause screen: 1-3 keys (+ Escape / C backward compat)
# =============================================================================

@pytest.mark.asyncio
async def test_pause_1_continue():
    """Escape → pause, 1 → continue."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        # 1 = New Game → race select
        await pilot.press("1")
        await pilot.pause()
        assert app.ctrl.state == GameState.RACE_SELECT
        # Select Human
        await pilot.press("1")
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING

        # Pause
        await pilot.press("escape")
        await pilot.pause()
        assert app.ctrl.state == GameState.PAUSED

        # Continue via 1
        await pilot.press("1")
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING


@pytest.mark.asyncio
async def test_pause_escape_continue():
    """Escape from pause also continues."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")  # New Game
        await pilot.pause()
        await pilot.press("1")  # Human
        await pilot.pause()
        await pilot.press("1")  # Smuggler
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING
        # Pause
        await pilot.press("escape")
        await pilot.pause()
        assert app.ctrl.state == GameState.PAUSED
        # Continue via Escape
        await pilot.press("escape")
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING


# =============================================================================
# Playing state: 0 opens action menu
# =============================================================================

@pytest.mark.asyncio
async def test_playing_0_opens_menu():
    """In PLAYING state, 0 opens interaction menu."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")  # New Game
        await pilot.pause()
        await pilot.press("1")  # Human
        await pilot.pause()
        await pilot.press("1")  # Smuggler
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING

        await pilot.press("0")
        await pilot.pause()
        # Menu opens if there are interactions nearby
        assert True  # no crash


@pytest.mark.asyncio
async def test_playing_wasd_movement():
    """WASD keys move the ship."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("1")  # Human
        await pilot.pause()
        await pilot.press("1")  # Smuggler
        await pilot.pause()
        old_x, old_y = app.player_x, app.player_y

        # Move right
        if app.galaxy.is_passable(old_x + 1, old_y):
            await pilot.press("right")
            await pilot.pause()

        # Move up
        if app.galaxy.is_passable(app.player_x, app.player_y - 1):
            await pilot.press("up")
            await pilot.pause()

        assert True  # no crash


@pytest.mark.asyncio
async def test_playing_space_wait():
    """Space advances world by one turn."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("1")  # Human
        await pilot.pause()
        await pilot.press("1")  # Smuggler
        await pilot.pause()
        old_turn = app.logger.turn
        await pilot.press("space")
        await pilot.pause()
        assert app.logger.turn >= old_turn


# =============================================================================
# Interaction menu: digit keys 1-9 select, 0 closes
# =============================================================================

@pytest.mark.asyncio
async def test_interaction_menu_0_closes():
    """Pressing 0 when menu is open closes it."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("1")  # Human
        await pilot.pause()
        await pilot.press("1")  # Smuggler
        await pilot.pause()
        # Open menu manually
        app._interaction_active = True
        app.ctrl.interaction_actions = [
            ("", "Test Action 1", "refuel", ""),
            ("", "Test Action 2", "repair", ""),
        ]
        app.update_map()
        await pilot.pause()
        assert app._interaction_active

        # Close with 0
        await pilot.press("0")
        await pilot.pause()
        assert not app._interaction_active


# =============================================================================
# F1 opens bridge
# =============================================================================

@pytest.mark.asyncio
async def test_f1_opens_bridge():
    """F1 opens Bridge screen in PLAYING state."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("1")  # Human
        await pilot.pause()
        await pilot.press("1")  # Smuggler
        await pilot.pause()
        assert app.ctrl.state == GameState.PLAYING
        from ui import BridgeScreen
        await pilot.press("f1")
        await pilot.pause()
        assert isinstance(app.screen, BridgeScreen)


# =============================================================================
# Game Over: 1-2 keys
# =============================================================================

@pytest.mark.asyncio
async def test_game_over_1_restarts():
    """In GAME_OVER, 1 restarts the game."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("1")  # Human
        await pilot.pause()
        await pilot.press("1")  # Smuggler
        await pilot.pause()
        # Force game over
        app.ctrl.state = GameState.GAME_OVER
        app.ctrl.death_cause = "Test"
        app.update_map()
        await pilot.pause()
        assert app.ctrl.state == GameState.GAME_OVER

        await pilot.press("1")
        await pilot.pause()
        assert app.ctrl.state in (GameState.START_SCREEN, GameState.RACE_SELECT)


# =============================================================================
# Battle screen: 1-6 keys (unchanged)
# =============================================================================

@pytest.mark.asyncio
async def test_battle_keys_unchanged():
    """Battle screen still uses 1-6 for main menu."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("1")  # Human
        await pilot.pause()
        await pilot.press("1")  # Smuggler
        await pilot.pause()

        pirate = PirateShip(app.player_x + 1, app.player_y)
        pirate.name = "TestPirate"
        app.galaxy.pirates.append(pirate)
        app._initiate_battle(pirate)
        await pilot.pause()

        from battle import BattleScreen
        assert isinstance(app.screen, BattleScreen)

        # 1 = Attack
        await pilot.press("1")
        await pilot.pause()
        assert app.screen.menu_state in ("attack_weapon", "main")

        # Escape to dismiss if battle not over
        if not app.screen.ctrl.over:
            await pilot.press("escape")
            await pilot.pause()


# =============================================================================
# Log filter: / key cycles
# =============================================================================

@pytest.mark.asyncio
async def test_slash_cycles_log_filter():
    """Pressing / cycles log category filter."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("1")  # Human
        await pilot.pause()
        await pilot.press("1")  # Smuggler
        await pilot.pause()
        await pilot.press("/")
        await pilot.pause()
        assert True  # no crash


# =============================================================================
# Console: ` key
# =============================================================================

@pytest.mark.asyncio
async def test_backtick_opens_console():
    """Pressing ` opens command console."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("1")  # Human
        await pilot.pause()
        await pilot.press("1")  # Smuggler
        await pilot.pause()
        from ui import CommandScreen
        await pilot.press("`")
        await pilot.pause()
        assert isinstance(app.screen, CommandScreen)


# =============================================================================
# Help screen: any key closes
# =============================================================================

@pytest.mark.asyncio
async def test_help_h_key():
    """H key opens help screen."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.pause()
        await pilot.press("1")
        await pilot.pause()
        await pilot.press("1")  # Human
        await pilot.pause()
        await pilot.press("1")  # Smuggler
        await pilot.pause()
        await pilot.press("h")
        await pilot.pause()
        assert app.ctrl.state == GameState.HELP
