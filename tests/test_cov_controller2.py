"""Coverage tests — game_controller round 2 (2026-08-03)."""

import random

from game_controller import GameController, GameState
from models import TraderShip, PirateShip, Station


def _ctrl():
    return GameController()


def _at_station(ctrl):
    st = ctrl.galaxy.stations[0]
    ctrl.player_x, ctrl.player_y = st.x, st.y
    return st


# =============================================================================
# process_command — more branches
# =============================================================================

def test_help_command():
    ctrl = _ctrl()
    ctrl.process_command("help")
    rendered = ctrl.logger.render_plain(n=20)
    assert "give" in rendered and "exit" in rendered


def test_scan_and_inventory_commands():
    ctrl = _ctrl()
    ctrl.process_command("scan")
    ctrl.process_command("inventory")
    ctrl.process_command("inv")
    rendered = ctrl.logger.render_plain(n=20)
    assert "Cargo" in rendered


def test_give_take_unknown_resource():
    ctrl = _ctrl()
    ctrl.process_command("give bogus 5")
    ctrl.process_command("take bogus 5")
    rendered = ctrl.logger.render_plain(n=10)
    assert "Unknown 'bogus'" in rendered


def test_trade_not_at_station():
    ctrl = _ctrl()
    ctrl.player_x, ctrl.player_y = 3, 3
    ctrl.process_command("trade buy ore 1")
    rendered = ctrl.logger.render_plain(n=10)
    assert "Not at station" in rendered


def test_market_scan_no_stations():
    ctrl = _ctrl()
    ctrl.player_x, ctrl.player_y = 3, 3
    ctrl.process_command("market scan 1")
    rendered = ctrl.logger.render_plain(n=10)
    assert "No stations" in rendered


def test_smuggle_not_at_station():
    ctrl = _ctrl()
    ctrl.player_x, ctrl.player_y = 3, 3
    ctrl.process_command("smuggle relic 1")
    rendered = ctrl.logger.render_plain(n=10)
    assert "Not at station" in rendered


def test_smuggle_not_enough():
    ctrl = _ctrl()
    _at_station(ctrl)
    ctrl.process_command("smuggle relic 5")  # реликвии нет
    rendered = ctrl.logger.render_plain(n=10)
    assert "Not enough" in rendered


def test_attack_npc_returns_battle():
    ctrl = _ctrl()
    p = PirateShip(ctrl.player_x + 1, ctrl.player_y)
    p.name = "TestPirate"
    ctrl.galaxy.pirates.append(p)
    result = ctrl.process_command("attack TestPirate")
    assert result is not None
    assert result[0] == "battle"
    assert result[1] is p


def test_hail_nearby_trader():
    ctrl = _ctrl()
    t = TraderShip(ctrl.player_x + 1, ctrl.player_y, [0])
    ctrl.galaxy.traders.append(t)
    ctrl.process_command("hail")
    rendered = ctrl.logger.render_plain(n=10)
    assert "Trader" in rendered


def test_cargo_sellall_at_station():
    ctrl = _ctrl()
    _at_station(ctrl)
    ctrl.ship.cargo.add("metal", 5)
    ctrl.process_command("cargo sellall")
    rendered = ctrl.logger.render_plain(n=10)
    assert len(rendered) > 0


# =============================================================================
# Political events — remaining branches
# =============================================================================

def _pol_event(seed):
    ctrl = _ctrl()
    ctrl._politics_timer = 100
    random.seed(seed)
    ctrl._check_political_events([])
    return ctrl


def test_political_schism():
    ctrl = _pol_event(4)
    headlines = " ".join(e.headline for e in ctrl.galaxy.news).lower()
    assert "schism" in headlines


def test_political_plague():
    ctrl = _pol_event(16)
    headlines = " ".join(e.headline for e in ctrl.galaxy.news).lower()
    assert "plague" in headlines


def test_political_scandal():
    ctrl = _pol_event(1)
    headlines = " ".join(e.headline for e in ctrl.galaxy.news).lower()
    assert "scandal" in headlines


def test_political_treaty():
    ctrl = _pol_event(20)
    headlines = " ".join(e.headline for e in ctrl.galaxy.news).lower()
    assert "treaty" in headlines


# =============================================================================
# Random events — caravan/raid
# =============================================================================

def test_random_event_caravan_spawns_traders():
    ctrl = _ctrl()
    n = len(ctrl.galaxy.traders)
    random.seed(31)
    ctrl._check_random_events([])
    assert len(ctrl.galaxy.traders) > n


def test_random_event_raid_spawns_pirates():
    ctrl = _ctrl()
    n = len(ctrl.galaxy.pirates)
    random.seed(176)
    ctrl._check_random_events([])
    assert len(ctrl.galaxy.pirates) > n


# =============================================================================
# tick_world / _act_land branches
# =============================================================================

def test_tick_world_runs_in_playing_state():
    ctrl = _ctrl()
    ctrl.state = GameState.PLAYING
    ctrl.tick_world()  # не должно падать


def test_act_land_damage_branch():
    ctrl = _ctrl()
    ctrl.ship.shield_hp = 0
    hull_before = ctrl.ship.hull
    random.seed(1)  # Wildlife/Storm — урон
    ctrl._act_land()
    assert ctrl.ship.hull <= hull_before


def test_act_land_ore_branch():
    ctrl = _ctrl()
    random.seed(19)  # Minerals +2ore
    ctrl._act_land()
    assert ctrl.ship.cargo.has("ore") == 2


def test_act_land_credits_branch():
    ctrl = _ctrl()
    cr_before = ctrl.ship.credits
    random.seed(2)  # Ruins +50cr
    ctrl._act_land()
    assert ctrl.ship.credits == cr_before + 50


# =============================================================================
# get_available_interactions
# =============================================================================

def test_interactions_at_station():
    ctrl = _ctrl()
    _at_station(ctrl)
    acts = ctrl.get_available_interactions()
    ids = [a[2] for a in acts]
    assert "trade" in ids
    assert "ship_screens" in ids  # субменю корабля


def test_interactions_near_pirate():
    ctrl = _ctrl()
    p = PirateShip(ctrl.player_x + 1, ctrl.player_y)
    ctrl.galaxy.pirates.append(p)
    acts = ctrl.get_available_interactions()
    ids = [a[2] for a in acts]
    assert "battle_pirate" in ids
