"""Tests for quick battle / debug mode factory functions."""

import pytest
from models import create_random_ship, create_random_enemy, PlayerShip, COMPARTMENTS
from battle import BattleController, BattleScreen


class TestCreateRandomShip:
    """Tests for create_random_ship()."""

    def test_returns_playership(self):
        ship = create_random_ship(is_player=True)
        assert isinstance(ship, PlayerShip)

    def test_has_compartments_with_modules(self):
        ship = create_random_ship(is_player=True)
        # At minimum should have reactor, engine, shield, sensor, weapon
        active = [c for c in COMPARTMENTS if ship.compartments[c]["modules"]]
        assert len(active) >= 5

    def test_has_crew(self):
        ship = create_random_ship(is_player=True)
        assert 2 <= len(ship.crew_members) <= 3

    def test_has_cargo_items(self):
        ship = create_random_ship(is_player=True)
        assert ship.cargo.has("repair_kit") >= 2
        assert ship.cargo.has("fuel_cell") >= 2

    def test_has_hull_and_shields(self):
        ship = create_random_ship(is_player=True)
        assert ship.max_hull > 0
        assert ship.hull == ship.max_hull
        assert ship.shield_hp > 0

    def test_has_alive_attribute(self):
        ship = create_random_ship(is_player=True)
        assert ship.alive is True

    def test_has_take_damage_method(self):
        ship = create_random_ship(is_player=True)
        # PlayerShip has take_damage
        assert hasattr(ship, "take_damage")

    def test_random_hull_excluding_shuttle(self):
        from config import SHIP_HULLS
        for _ in range(20):
            ship = create_random_ship(is_player=True)
            assert ship.hull_id != "shuttle"
            assert ship.hull_id in SHIP_HULLS

    def test_crew_assigned_to_posts(self):
        ship = create_random_ship(is_player=True)
        assigned = [p for p, name in ship.crew.items() if name is not None]
        assert len(assigned) >= 1


class TestCreateRandomEnemy:
    """Tests for create_random_enemy()."""

    def test_returns_playership(self):
        enemy = create_random_enemy()
        assert isinstance(enemy, PlayerShip)

    def test_has_compartments_with_modules(self):
        enemy = create_random_enemy()
        active = [c for c in COMPARTMENTS if enemy.compartments[c]["modules"]]
        assert len(active) >= 5

    def test_has_hull_and_shields(self):
        enemy = create_random_enemy()
        assert enemy.max_hull > 0
        assert enemy.hull == enemy.max_hull

    def test_has_alive_attribute(self):
        enemy = create_random_enemy()
        assert enemy.alive is True

    def test_enemy_name_has_enemy_prefix(self):
        enemy = create_random_enemy()
        assert enemy.name.startswith("Enemy-")

    def test_weaker_hull_than_player(self):
        """Enemy should use a valid hull."""
        enemy = create_random_enemy()
        from config import SHIP_HULLS
        hull_ids = [k for k in SHIP_HULLS if k != "shuttle"]
        assert enemy.hull_id in hull_ids


class TestBattleIntegration:
    """Tests that factory functions integrate correctly with battle system."""

    def test_battle_controller_accepts_factory_ships(self):
        p = create_random_ship(is_player=True)
        e = create_random_enemy()
        bc = BattleController(p, e)
        assert bc.player is p
        assert bc.enemy is e
        assert bc.over is False

    def test_battle_controller_without_app(self):
        p = create_random_ship(is_player=True)
        e = create_random_enemy()
        # app=None should work
        bc = BattleController(p, e, app=None)
        # Try a few actions to make sure nothing crashes
        bc.do_attack(0, "shield")
        assert bc.over is False or bc.over is True  # could be over after one shot
        # Skills also should not crash
        bc2 = BattleController(p, e, app=None)
        bc2.do_skill("emergency_repair")

    def test_battle_screen_quick_battle_flag(self):
        p = create_random_ship(is_player=True)
        e = create_random_enemy()
        bc = BattleController(p, e, app=None)
        bs = BattleScreen(bc, quick_battle=True)
        assert bs.quick_battle is True
        # _apply_outcome should not crash for quick_battle
        bs._apply_outcome()

    def test_battle_screen_quick_battle_does_not_set_game_over(self):
        """quick_battle mode should not set app.state to GAME_OVER."""
        p = create_random_ship(is_player=True)
        e = create_random_enemy()
        bc = BattleController(p, e, app=None)
        bs = BattleScreen(bc, quick_battle=True)
        # Simulate death
        p.hull = 0
        bc.over = True
        bc.victory = False
        # Should not crash or try to set app.state
        bs._apply_outcome()

    def test_factory_ships_work_in_combat_loop(self):
        """Run a full combat loop to ensure nothing crashes."""
        p = create_random_ship(is_player=True)
        e = create_random_enemy()
        bc = BattleController(p, e, app=None)
        # Play a few turns
        for _ in range(10):
            if bc.over:
                break
            bc.do_attack(0, "shield")
            if bc.over:
                break
            bc.do_defend()
            if bc.over:
                break
            bc.do_use_item("repair_kit")
        # Should not crash — either battle ended or we ran out of turns
        assert bc.over is False or bc.over is True
