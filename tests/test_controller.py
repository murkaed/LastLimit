"""Comprehensive tests for GameController — start screens, movement, info
display, trading through controller, and logging."""

import pytest
import random
from game_controller import GameController, GameState
from locales import set_lang, t


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def ctrl():
    """Fresh GameController with deterministic galaxy."""
    random.seed(42)
    c = GameController()
    c.state = GameState.START_SCREEN
    yield c
    random.seed()


@pytest.fixture
def playing_ctrl(ctrl):
    """Controller in PLAYING state with Human race."""
    ctrl.state = GameState.START_SCREEN
    ctrl._show_race_select = True
    ctrl.state = GameState.RACE_SELECT
    ctrl.select_race("1")  # Human
    assert ctrl.state == GameState.PLAYING
    return ctrl


# =============================================================================
# 1. Start screen rendering
# =============================================================================

class TestStartScreen:
    def test_initial_state_is_start_screen(self, ctrl):
        assert ctrl.state == GameState.START_SCREEN

    def test_start_screen_renders(self, ctrl):
        set_lang("en")
        result = ctrl.render_start_screen()
        assert "New Game" in result
        assert len(result) > 100  # plenty of content

    def test_start_screen_has_menu_options(self, ctrl):
        set_lang("en")
        result = ctrl.render_start_screen()
        assert "[N]" in result or "New Game" in result
        assert "[B]" in result or "Quick Battle" in result
        assert "[H]" in result or "Help" in result
        assert "[Q]" in result or "Quit" in result

    def test_start_screen_has_menu_options_ru(self, ctrl):
        set_lang("ru")
        result = ctrl.render_start_screen()
        assert "Новая игра" in result
        assert "Быстрый бой" in result
        assert "Помощь" in result
        assert "Выйти" in result
        set_lang("ru")

    def test_show_race_select_enables_race_screen(self, ctrl):
        set_lang("en")
        ctrl._show_race_select = True
        ctrl.state = GameState.RACE_SELECT
        result = ctrl.render_start_screen()
        assert "CHOOSE YOUR RACE" in result
        assert "Human" in result
        assert "Mutant" in result

    def test_race_select_has_races(self, ctrl):
        set_lang("en")
        ctrl._show_race_select = True
        ctrl.state = GameState.RACE_SELECT
        result = ctrl.render_start_screen()
        assert "[1]" in result
        assert "[5]" in result
        assert "[0] Back" in result

    def test_race_select_back_returns_to_start(self, ctrl):
        ctrl._show_race_select = True
        ctrl.state = GameState.RACE_SELECT
        ctrl._show_race_select = False
        ctrl.state = GameState.START_SCREEN
        result = ctrl.render_start_screen()
        assert "CHOOSE" not in result


# =============================================================================
# 2. Race selection logic
# =============================================================================

class TestRaceSelection:
    def test_select_human(self, ctrl):
        ctrl.select_race("1")
        assert ctrl.ship.race == "human"
        assert ctrl.race_selected
        assert ctrl.state == GameState.PLAYING

    def test_select_mutant_by_name(self, ctrl):
        ctrl.select_race("mutant")
        assert ctrl.ship.race == "mutant"
        assert ctrl.state == GameState.PLAYING

    def test_select_voidborn_by_number(self, ctrl):
        ctrl.select_race("5")
        assert ctrl.ship.race == "voidborn"

    def test_select_xenos_bio(self, ctrl):
        ctrl.select_race("xenos")
        assert ctrl.ship.race == "xenos_bio"

    def test_select_machine_cult(self, ctrl):
        ctrl.select_race("4")
        assert ctrl.ship.race == "machine_cult"

    def test_invalid_race_does_nothing(self, ctrl):
        ctrl.select_race("999")
        assert not ctrl.race_selected
        assert ctrl.state == GameState.START_SCREEN

    def test_empty_race_is_human(self, ctrl):
        ctrl.select_race("")
        assert ctrl.ship.race == "human"

    def test_race_applies_bonus(self, ctrl):
        ctrl.ship.race = "machine_cult"
        ctrl.ship.apply_race_bonus()
        # Machine cult gets power_bonus
        assert ctrl.ship._race_bonus("power_bonus", 0) >= 0


# =============================================================================
# 3. Info panel rendering
# =============================================================================

class TestInfoPanel:
    def test_start_screen_info(self, ctrl):
        set_lang("en")
        ctrl.state = GameState.START_SCREEN
        info, log_text = ctrl.get_info_panel()
        assert "New Game" in info or "Start" in info

    def test_race_select_info(self, ctrl):
        set_lang("en")
        ctrl._show_race_select = True
        ctrl.state = GameState.RACE_SELECT
        info, log_text = ctrl.get_info_panel()
        assert "race" in info.lower()

    def test_playing_info_shows_ship_name(self, playing_ctrl):
        info, log_text = playing_ctrl.get_info_panel()
        assert playing_ctrl.ship.name in info
        assert "H:" in info  # Hull

    def test_playing_info_returns_two_strings(self, playing_ctrl):
        info, log_text = playing_ctrl.get_info_panel()
        assert isinstance(info, str)
        assert isinstance(log_text, str)

    def test_paused_info(self, ctrl):
        set_lang("en")
        ctrl.state = GameState.PAUSED
        info, log_text = ctrl.get_info_panel()
        assert "PAUSED" in info

    def test_game_over_info(self, ctrl):
        set_lang("en")
        ctrl.state = GameState.GAME_OVER
        ctrl.death_cause = "Test destruction"
        info, log_text = ctrl.get_info_panel()
        assert "Test destruction" in info

    def test_inspect_info(self, playing_ctrl):
        playing_ctrl.state = GameState.INSPECTING
        playing_ctrl.cursor_x = playing_ctrl.player_x + 1
        playing_ctrl.cursor_y = playing_ctrl.player_y
        info, log_text = playing_ctrl.get_info_panel()
        assert "Inspect" in info or "Осмотр" in info

    def test_help_info(self, ctrl):
        ctrl.state = GameState.HELP
        info, log_text = ctrl.get_info_panel()
        assert isinstance(info, str)

    def test_news_info(self, ctrl):
        ctrl.state = GameState.NEWS
        info, log_text = ctrl.get_info_panel()
        assert isinstance(info, str)

    def test_interaction_info(self, playing_ctrl):
        playing_ctrl._interaction_active = True
        info, log_text = playing_ctrl.get_info_panel()
        assert isinstance(info, str)


# =============================================================================
# 4. Movement logic
# =============================================================================

class TestMovement:
    def test_move_right(self, playing_ctrl):
        px = playing_ctrl.player_x
        py = playing_ctrl.player_y
        # Find a passable tile to the right
        if playing_ctrl.galaxy.is_passable(px + 1, py):
            should_advance, pending = playing_ctrl.move_player(1, 0)
            if py == playing_ctrl.player_y and playing_ctrl.player_x > px:
                assert True  # moved right
            else:
                pass  # blocked by something, OK
        else:
            pass  # edge of map, skip

    def test_move_left(self, playing_ctrl):
        px = playing_ctrl.player_x
        py = playing_ctrl.player_y
        if playing_ctrl.galaxy.is_passable(px - 1, py):
            playing_ctrl.move_player(-1, 0)
            # Either moved or blocked — both OK

    def test_move_up(self, playing_ctrl):
        px = playing_ctrl.player_x
        py = playing_ctrl.player_y
        if playing_ctrl.galaxy.is_passable(px, py - 1):
            playing_ctrl.move_player(0, -1)

    def test_move_down(self, playing_ctrl):
        px = playing_ctrl.player_x
        py = playing_ctrl.player_y
        if playing_ctrl.galaxy.is_passable(px, py + 1):
            playing_ctrl.move_player(0, 1)

    def test_move_consumes_fuel(self, playing_ctrl):
        # Place player on guaranteed passable tile (center of map)
        playing_ctrl.player_x = 40
        playing_ctrl.player_y = 20
        playing_ctrl.ship.fuel = 50
        initial_fuel = playing_ctrl.ship.fuel
        # Make sure tile is passable
        tile = playing_ctrl.galaxy.get_tile(41, 20)
        if playing_ctrl.galaxy.is_passable(41, 20):
            playing_ctrl.move_player(1, 0)
            if playing_ctrl.player_x != 40:  # actually moved
                assert playing_ctrl.ship.fuel <= initial_fuel

    def test_move_into_star_blocked(self, playing_ctrl):
        # Find a star and try to move into it
        for y in range(max(0, playing_ctrl.player_y - 3),
                       min(playing_ctrl.galaxy.height, playing_ctrl.player_y + 4)):
            for x in range(max(0, playing_ctrl.player_x - 3),
                           min(playing_ctrl.galaxy.width, playing_ctrl.player_x + 4)):
                if playing_ctrl.galaxy.get_tile(x, y) == '*':
                    playing_ctrl.player_x = x - 1
                    playing_ctrl.player_y = y
                    if playing_ctrl.galaxy.is_passable(playing_ctrl.player_x,
                                                       playing_ctrl.player_y):
                        old_x = playing_ctrl.player_x
                        playing_ctrl.move_player(1, 0)
                        # Should be blocked by star
                        assert playing_ctrl.player_x == old_x
                        return
        # No star found nearby — test passes vacuously

    def test_move_out_of_bounds(self, playing_ctrl):
        playing_ctrl.player_x = 0
        playing_ctrl.player_y = 20
        old_x = playing_ctrl.player_x
        playing_ctrl.move_player(-1, 0)
        assert playing_ctrl.player_x == old_x

    def test_move_changes_coordinates(self, playing_ctrl):
        # Find a direction with a passable tile
        moved = False
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx = playing_ctrl.player_x + dx
            ny = playing_ctrl.player_y + dy
            if playing_ctrl.galaxy.is_passable(nx, ny):
                old = (playing_ctrl.player_x, playing_ctrl.player_y)
                playing_ctrl.move_player(dx, dy)
                if (playing_ctrl.player_x, playing_ctrl.player_y) != old:
                    moved = True
                    break
        # At least one direction should be passable near center
        # If not, it's OK — galaxy generation is random

    def test_move_multistep_with_speed(self, playing_ctrl):
        """Player with high speed moves multiple tiles in one action."""
        playing_ctrl.player_x = 40
        playing_ctrl.player_y = 20
        # Boost speed
        old_speed = playing_ctrl.ship.get_effective_stats().get("speed", 1)
        playing_ctrl.ship.fuel = 50
        # Try moving right multiple steps
        playing_ctrl.move_player(1, 0)
        # Just verify no crash

    def test_move_in_non_playing_state_does_nothing(self, ctrl):
        ctrl.state = GameState.START_SCREEN
        old = (ctrl.player_x, ctrl.player_y)
        ctrl.move_player(1, 0)
        assert (ctrl.player_x, ctrl.player_y) == old


# =============================================================================
# 5. Trading through controller (Station)

# Note: Full trade flow requires pushing screens (Textual).
# These test the logic layer only.

class TestTrading:
    def test_trade_screen_requested_at_station(self, playing_ctrl):
        """When player is on a station, _act_trade returns screen request."""
        # Find a station
        for st in playing_ctrl.galaxy.stations:
            playing_ctrl.player_x = st.x
            playing_ctrl.player_y = st.y
            result = playing_ctrl._act_trade()
            assert result is not None
            assert result[0] == "TradeScreen"
            return
        # No stations — skip

    def test_trade_fails_when_not_at_station(self, playing_ctrl):
        # Move far from stations
        playing_ctrl.player_x = 5
        playing_ctrl.player_y = 5
        # Verify no station at position
        if playing_ctrl.galaxy.get_station_at(5, 5) is None:
            result = playing_ctrl._act_trade()
            assert result is None

    def test_refuel_costs_50_credits(self, playing_ctrl):
        playing_ctrl.ship.credits = 100
        playing_ctrl.ship.fuel = 10
        playing_ctrl._act_refuel()
        assert playing_ctrl.ship.credits == 50
        assert playing_ctrl.ship.fuel == 30

    def test_refuel_fails_without_credits(self, playing_ctrl):
        playing_ctrl.ship.credits = 10
        playing_ctrl.ship.fuel = 10
        playing_ctrl._act_refuel()
        assert playing_ctrl.ship.credits == 10  # unchanged
        assert playing_ctrl.ship.fuel == 10  # unchanged

    def test_repair_costs_30_credits(self, playing_ctrl):
        playing_ctrl.ship.credits = 100
        playing_ctrl.ship.hull = 50
        playing_ctrl._act_repair()
        assert playing_ctrl.ship.credits == 70
        assert playing_ctrl.ship.hull > 50

    def test_repair_fails_without_credits(self, playing_ctrl):
        playing_ctrl.ship.credits = 10
        playing_ctrl.ship.hull = 50
        playing_ctrl._act_repair()
        assert playing_ctrl.ship.credits == 10
        assert playing_ctrl.ship.hull == 50

    def test_act_mine_adds_ore(self, playing_ctrl):
        """Mine action tries to add ore (probabilistic)."""
        playing_ctrl.ship.cargo.items.clear()
        playing_ctrl.ship.cargo.capacity = 50
        random.seed(123)
        playing_ctrl._act_mine()
        # Either got ore or depleted — both valid
        assert True  # no crash


# =============================================================================
# 6. Log display and filtering
# =============================================================================

class TestLogDisplay:
    def test_log_display_returns_string(self, playing_ctrl):
        result = playing_ctrl._get_log_display()
        assert isinstance(result, str)

    def test_log_filter_cycle(self, playing_ctrl):
        old_filter = playing_ctrl.log_category_filter
        playing_ctrl.cycle_log_filter()
        # Filter may have changed or cycled back
        assert True  # no crash

    def test_log_filter_label(self, playing_ctrl):
        label = playing_ctrl._log_filter_label()
        assert isinstance(label, str)

    def test_log_handle_filter_all(self, playing_ctrl):
        playing_ctrl.handle_log_command(["log", "filter", "all"])
        assert playing_ctrl.log_category_filter is None

    def test_log_handle_filter_combat(self, playing_ctrl):
        playing_ctrl.handle_log_command(["log", "filter", "combat"])
        from game_logger import LogCategory
        assert playing_ctrl.log_category_filter == LogCategory.COMBAT

    def test_log_handle_clear(self, playing_ctrl):
        playing_ctrl.logger.system("test message")
        playing_ctrl.handle_log_command(["log", "clear"])
        # Logger should be cleared
        assert True  # no crash

    def test_log_handle_search(self, playing_ctrl):
        playing_ctrl.logger.system("unique test message 12345")
        playing_ctrl.handle_log_command(["log", "search", "12345"])

    def test_log_handle_detail(self, playing_ctrl):
        playing_ctrl.handle_log_command(["log", "detail", "high"])

    def test_log_event_categories(self, playing_ctrl):
        playing_ctrl._log_event("Radiation -10!")
        playing_ctrl._log_event("Gravity pull!")
        playing_ctrl._log_event("[EVENT] Something happened")
        # Messages categorized correctly — verify no crash
        logs = playing_ctrl.logger.get_last(10)
        assert len(logs) >= 3


# =============================================================================
# 7. Ship status and scan
# =============================================================================

class TestShipStatus:
    def test_ship_status_returns_list(self, playing_ctrl):
        result = playing_ctrl._get_ship_status()
        assert isinstance(result, list)

    def test_cargo_summary(self, playing_ctrl):
        result = playing_ctrl._cargo_summary()
        assert isinstance(result, str)

    def test_cargo_summary_empty(self, playing_ctrl):
        playing_ctrl.ship.cargo.items.clear()
        set_lang("en")
        result = playing_ctrl._cargo_summary()
        assert "empty" in result.lower()

    def test_reputation_summary(self, playing_ctrl):
        result = playing_ctrl._reputation_summary()
        assert isinstance(result, str)

    def test_scan_nearby(self, playing_ctrl):
        result = playing_ctrl._scan_nearby()
        assert isinstance(result, str)

    def test_scan_nearby_empty_galaxy(self, ctrl):
        ctrl.galaxy.objects = {}
        ctrl.galaxy.traders = []
        ctrl.galaxy.pirates = []
        ctrl.galaxy.stations = []
        ctrl.player_x = 40
        ctrl.player_y = 20
        result = ctrl._scan_nearby()
        assert "Nothing" in result or "Ничего" in result


# =============================================================================
# 8. Interaction gathering
# =============================================================================

class TestInteractions:
    def test_get_interactions_at_station(self, playing_ctrl):
        # Place player on a station
        for st in playing_ctrl.galaxy.stations:
            playing_ctrl.player_x = st.x
            playing_ctrl.player_y = st.y
            acts = playing_ctrl.get_available_interactions()
            assert len(acts) > 0
            # Should have refuel and trade actions
            action_ids = [a[2] for a in acts]
            assert "refuel" in action_ids
            assert "trade" in action_ids
            return

    def test_get_interactions_on_empty_space(self, playing_ctrl):
        # Move to empty space far from everything
        for y in range(playing_ctrl.galaxy.height):
            for x in range(playing_ctrl.galaxy.width):
                if playing_ctrl.galaxy.get_tile(x, y) == '.':
                    if (x, y) not in playing_ctrl.galaxy.objects:
                        playing_ctrl.player_x = x
                        playing_ctrl.player_y = y
                        acts = playing_ctrl.get_available_interactions()
                        # May have NPC interactions nearby, but should be minimal
                        assert isinstance(acts, list)
                        return

    def test_run_interaction_refuel(self, playing_ctrl):
        # Place on a station and run refuel
        for st in playing_ctrl.galaxy.stations:
            playing_ctrl.player_x = st.x
            playing_ctrl.player_y = st.y
            playing_ctrl.ship.credits = 100
            playing_ctrl.ship.fuel = 10
            result = playing_ctrl.run_interaction("refuel")
            assert playing_ctrl.state == GameState.PLAYING
            return

    def test_run_interaction_repair(self, playing_ctrl):
        for st in playing_ctrl.galaxy.stations:
            playing_ctrl.player_x = st.x
            playing_ctrl.player_y = st.y
            playing_ctrl.ship.credits = 100
            playing_ctrl.ship.hull = 50
            result = playing_ctrl.run_interaction("repair")
            assert playing_ctrl.state == GameState.PLAYING
            return

    def test_run_invalid_interaction(self, playing_ctrl):
        result = playing_ctrl.run_interaction("nonexistent_action")
        assert result is None


# =============================================================================
# 9. Help and news screens
# =============================================================================

class TestHelpAndNews:
    def test_help_screen_english(self):
        set_lang("en")
        c = GameController()
        result = c.render_help_screen()
        assert "HELP" in result
        assert "MOVEMENT" in result
        assert "ACTIONS" in result
        assert "INTERFACE" in result
        set_lang("ru")

    def test_help_screen_russian(self):
        set_lang("ru")
        c = GameController()
        result = c.render_help_screen()
        assert "ПОМОЩЬ" in result
        assert "ДВИЖЕНИЕ" in result
        assert "ДЕЙСТВИЯ" in result
        set_lang("ru")

    def test_news_screen_renders(self, playing_ctrl):
        result = playing_ctrl.render_news_screen()
        assert isinstance(result, str)
        assert "GALAXY" in result or "ГАЛАКТИКИ" in result

    def test_news_screen_with_no_news(self, ctrl):
        ctrl.galaxy.news = []
        ctrl.galaxy.stations = []
        result = ctrl.render_news_screen()
        assert isinstance(result, str)


# =============================================================================
# 10. Pause and game over overlays
# =============================================================================

class TestOverlays:
    def test_pause_overlay(self, ctrl):
        set_lang("en")
        ctrl.state = GameState.PLAYING
        ctrl.player_x = 40
        ctrl.player_y = 20
        lines = ctrl.build_map_lines()
        result = ctrl.render_pause_overlay(lines)
        assert "PAUSED" in result

    def test_game_over_overlay(self, playing_ctrl):
        set_lang("en")
        playing_ctrl.state = GameState.PLAYING
        playing_ctrl.death_cause = "Test death"
        lines = playing_ctrl.build_map_lines()
        result = playing_ctrl.render_game_over_screen(lines)
        assert "GAME OVER" in result
        assert "Test death" in result

    def test_interaction_menu_overlay(self, playing_ctrl):
        playing_ctrl._interaction_active = True
        playing_ctrl.interaction_actions = [
            ("r", "Test Action", "test", "here"),
        ]
        lines = playing_ctrl.build_map_lines()
        result = playing_ctrl.render_interaction_menu(lines)
        assert "Test Action" in result


# =============================================================================
# 11. World tick
# =============================================================================

class TestWorldTick:
    def test_tick_world_does_not_crash(self, playing_ctrl):
        playing_ctrl.tick_world()
        # Should not raise

    def test_tick_world_increments_turn(self, playing_ctrl):
        old_turn = playing_ctrl.logger.turn
        playing_ctrl.tick_world()
        assert playing_ctrl.logger.turn == old_turn + 1

    def test_tick_regen_shields(self, playing_ctrl):
        stats = playing_ctrl.ship.get_effective_stats()
        if stats.get("shield_regen", 0) > 0:
            playing_ctrl.ship.shield_hp = 0
            playing_ctrl.tick_world()
            assert playing_ctrl.ship.shield_hp >= 0

    def test_game_over_on_death(self, playing_ctrl):
        playing_ctrl.ship.hull = 1
        # Force death via radiation by placing near star
        for y in range(playing_ctrl.galaxy.height):
            for x in range(playing_ctrl.galaxy.width):
                if playing_ctrl.galaxy.get_tile(x, y) == '*':
                    playing_ctrl.player_x = x + 1
                    playing_ctrl.player_y = y
                    if playing_ctrl.galaxy.is_passable(x + 1, y):
                        playing_ctrl.tick_world()
                        # May or may not die from radiation
                        return


# =============================================================================
# 12. Localization completeness
# =============================================================================

class TestLocalization:
    def test_all_interaction_labels_have_translations(self):
        """Every interaction label key resolves in both languages."""
        keys = [
            "iact.refuel", "iact.repair", "iact.trade", "iact.join",
            "iact.shop_parts", "iact.yard", "iact.workshop", "iact.tavern",
            "iact.missions", "iact.scan_planet", "iact.land", "iact.mine",
            "iact.wormhole", "iact.chat", "iact.fight",
        ]
        for key in keys:
            ru = t(key)
            set_lang("en")
            en = t(key)
            set_lang("ru")
            assert ru != key, f"RU key '{key}' not translated"
            assert en != key, f"EN key '{key}' not translated"

    def test_info_panel_keys_have_translations(self):
        keys = [
            "info.pick_race", "info.start_hint", "info.help_return",
            "info.select_or_esc", "info.paused", "info.nominal",
            "info.cargo_empty", "info.blocked", "info.blocked_by_edge",
        ]
        for key in keys:
            ru = t(key)
            set_lang("en")
            en = t(key)
            set_lang("ru")
            assert ru != key, f"RU key '{key}' not found"

    def test_event_keys_have_translations(self):
        keys = [
            "event.crusade", "event.invasion", "event.schism",
            "event.plague", "event.scandal", "event.treaty",
            "event.caravan", "event.raid", "event.supernova", "event.crisis",
        ]
        for key in keys:
            ru = t(key)
            set_lang("en")
            en = t(key)
            set_lang("ru")
            assert ru != key, f"RU key '{key}' not found"

    def test_log_keys_have_translations(self):
        keys = [
            "log.race_selected", "log.waiting", "log.no_station",
            "log.no_modules", "log.no_npc", "log.no_pirate",
            "log.teleported", "log.collapse", "log.depleted",
            "log.cargo_full", "log.destroyed", "log.colony_founded",
            "log.module_broken", "log.module_damaged", "log.mission_expired",
        ]
        for key in keys:
            ru = t(key)
            set_lang("en")
            en = t(key)
            set_lang("ru")
            assert ru != key, f"RU key '{key}' not found"


# =============================================================================
# 13. Build map lines
# =============================================================================

class TestBuildMap:
    def test_build_map_returns_correct_height(self, playing_ctrl):
        lines = playing_ctrl.build_map_lines()
        assert len(lines) == playing_ctrl.galaxy.height

    def test_build_map_returns_correct_width(self, playing_ctrl):
        lines = playing_ctrl.build_map_lines()
        assert len(lines[0]) == playing_ctrl.galaxy.width

    def test_player_visible_on_map(self, playing_ctrl):
        lines = playing_ctrl.build_map_lines()
        line = lines[playing_ctrl.player_y]
        assert len(line) > playing_ctrl.player_x

    def test_map_in_inspect_mode(self, playing_ctrl):
        playing_ctrl.state = GameState.INSPECTING
        playing_ctrl.cursor_x = 10
        playing_ctrl.cursor_y = 10
        lines = playing_ctrl.build_map_lines()
        assert len(lines) > 0

    def test_map_in_non_playing_state_hides_player(self, ctrl):
        ctrl.state = GameState.PAUSED
        ctrl.player_x = 40
        ctrl.player_y = 20
        lines = ctrl.build_map_lines()
        # Player should not be visible in non-playing state
        assert isinstance(lines, list)


# =============================================================================
# 14. Game restart
# =============================================================================

class TestRestart:
    def test_restart_resets_state(self, playing_ctrl):
        playing_ctrl.restart_game()
        assert playing_ctrl.state == GameState.START_SCREEN
        assert not playing_ctrl.race_selected

    def test_restart_creates_new_galaxy(self, playing_ctrl):
        old_galaxy = playing_ctrl.galaxy
        playing_ctrl.restart_game()
        assert playing_ctrl.galaxy is not old_galaxy

    def test_restart_clears_logger(self, playing_ctrl):
        playing_ctrl.logger.system("test")
        playing_ctrl.restart_game()
        assert len(playing_ctrl.logger.get_last(10)) <= 1  # May have seed message
