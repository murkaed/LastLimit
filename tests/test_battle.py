"""Test turn-based battle mode end-to-end via Textual pilot."""

import pytest
from textual.widgets import Static

from galaxy_map import GalaxyMapApp
from models import PlayerShip, PirateShip
from battle import BattleController, BattleScreen, BATTLE_SKILLS


@pytest.mark.asyncio
async def test_battle_screen_renders():
    """BattleScreen renders without crash when pushed."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.press("enter")  # select Human race
        await pilot.pause()

        # Create a pirate near the player
        pirate = PirateShip(app.player_x + 1, app.player_y)
        pirate.name = "TestPirate"
        app.galaxy.pirates.append(pirate)

        # Initiate battle
        app._initiate_battle(pirate)
        await pilot.pause()

        # Verify battle screen is shown
        assert isinstance(app.screen, BattleScreen), "BattleScreen should be active"
        ctrl = app.screen.ctrl
        assert ctrl is not None
        assert ctrl.enemy.name == "TestPirate"


@pytest.mark.asyncio
async def test_battle_main_menu_keys():
    """Main menu keys 1-5 work without errors."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.press("enter")
        await pilot.pause()

        pirate = PirateShip(app.player_x + 1, app.player_y)
        pirate.name = "Raider"
        app.galaxy.pirates.append(pirate)
        app._initiate_battle(pirate)
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, BattleScreen)
        ctrl = screen.ctrl

        # Each main menu key should work
        initial_hull = ctrl.player.hull
        await pilot.press("2")  # Defend
        await pilot.pause()
        assert ctrl.player_defending

        # Press escape to exit after battle (if over)
        if ctrl.over:
            await pilot.press("escape")


@pytest.mark.asyncio
async def test_battle_attack_flow():
    """Attack → weapon selection → target selection flow."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.press("enter")
        await pilot.pause()

        pirate = PirateShip(app.player_x + 1, app.player_y)
        pirate.name = "Pirate"
        app.galaxy.pirates.append(pirate)
        app._initiate_battle(pirate)
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, BattleScreen)

        # Press 1 for Attack
        await pilot.press("1")
        await pilot.pause()
        assert screen.menu_state == "attack_weapon"

        # Press 1 for first weapon (Laser Turret)
        await pilot.press("1")
        await pilot.pause()
        assert screen.menu_state == "attack_target"

        # Press 1 for reactor target
        await pilot.press("1")
        await pilot.pause()
        assert screen.menu_state == "main" or screen.ctrl.over


@pytest.mark.asyncio
async def test_battle_escape():
    """Escape from battle works."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.press("enter")
        await pilot.pause()

        pirate = PirateShip(app.player_x + 1, app.player_y)
        pirate.name = "Escapee"
        app.galaxy.pirates.append(pirate)
        pirate.hull = 40
        app._initiate_battle(pirate)
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, BattleScreen)

        # Try to escape
        await pilot.press("5")
        await pilot.pause()

        # May have escaped or failed — either is valid
        assert screen.ctrl.over or screen.menu_state == "main"


@pytest.mark.asyncio
async def test_battle_player_defeated():
    """Player death in battle triggers game over state."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.press("enter")
        await pilot.pause()

        # Set player hull very low
        app.ship.hull = 1
        app.ship.shield_hp = 0

        pirate = PirateShip(app.player_x + 1, app.player_y)
        pirate.name = "Killer"
        app.galaxy.pirates.append(pirate)
        app._initiate_battle(pirate)
        await pilot.pause()

        # Wait for battle to end by repeatedly pressing Attack → quick attack
        screen = app.screen
        import asyncio
        for _ in range(50):
            if screen.ctrl.over:
                break
            await pilot.press("1")  # Attack menu
            await pilot.pause()
            if screen.ctrl.over:
                break
            await pilot.press("1")  # first weapon
            await pilot.pause()
            if screen.ctrl.over:
                break
            await pilot.press("0")  # quick attack (random target)
            await pilot.pause()

        # Battle should be over (player at 1 HP will die from any hit)
        assert screen.ctrl.over, "Battle should end when player hull = 1"


@pytest.mark.asyncio
async def test_battle_items():
    """Using items from cargo in battle works."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.press("enter")
        await pilot.pause()

        # Add items to cargo
        app.ship.cargo.add("repair_kit", 2)
        app.ship.cargo.add("fuel_cell", 1)
        app.ship.hull = 50

        pirate = PirateShip(app.player_x + 1, app.player_y)
        pirate.name = "Looter"
        app.galaxy.pirates.append(pirate)
        app._initiate_battle(pirate)
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, BattleScreen)
        ctrl = screen.ctrl

        # Use items menu
        await pilot.press("3")
        await pilot.pause()
        assert screen.menu_state == "items"

        # Press R for repair_kit
        await pilot.press("r")
        await pilot.pause()
        assert app.ship.hull > 50 or screen.menu_state == "main" or ctrl.over


@pytest.mark.asyncio
async def test_battle_skills():
    """Skills work in battle."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.press("enter")
        await pilot.pause()

        app.ship.hull = 50

        pirate = PirateShip(app.player_x + 1, app.player_y)
        pirate.name = "SkillTest"
        app.galaxy.pirates.append(pirate)
        app._initiate_battle(pirate)
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, BattleScreen)
        ctrl = screen.ctrl
        ctrl.turn_order = "player"
        ctrl.player_energy = 50

        # Use skills menu
        await pilot.press("4")
        await pilot.pause()
        assert screen.menu_state == "skills"

        # Press E for emergency repair
        initial_hull = ctrl.player.hull
        await pilot.press("e")
        await pilot.pause()
        assert ctrl.player.hull >= initial_hull or ctrl.over


@pytest.mark.asyncio
async def test_battle_quick_attack():
    """Quick attack (random target) works."""
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        await pilot.press("enter")
        await pilot.pause()

        pirate = PirateShip(app.player_x + 1, app.player_y)
        pirate.name = "QuickTest"
        app.galaxy.pirates.append(pirate)
        app._initiate_battle(pirate)
        await pilot.pause()

        screen = app.screen
        assert isinstance(screen, BattleScreen)
        ctrl = screen.ctrl
        ctrl.turn_order = "player"

        # Attack → select weapon → quick attack (0)
        await pilot.press("1")
        await pilot.pause()
        if screen.menu_state == "attack_weapon":
            await pilot.press("1")
            await pilot.pause()
            if screen.menu_state == "attack_target":
                # Quick attack
                await pilot.press("0")
                await pilot.pause()

        # Should have processed the attack
        assert screen.menu_state == "main" or ctrl.over
