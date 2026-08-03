"""Coverage tests — game_controller gaps (2026-08-03)."""

import random

from game_controller import GameController, GameState
from models import Station


def _ctrl_at_station():
    ctrl = GameController()
    st = ctrl.galaxy.stations[0]
    ctrl.player_x, ctrl.player_y = st.x, st.y
    return ctrl, st


# =============================================================================
# process_command — remaining branches
# =============================================================================

def test_trade_buy_and_sell():
    ctrl, st = _ctrl_at_station()
    ctrl.ship.credits = 5000
    ctrl.process_command("trade buy ore 5")
    assert ctrl.ship.cargo.has("ore") >= 5
    assert ctrl.ship.credits < 5000  # покупка списала кредиты
    ctrl.process_command("trade sell metal 5")  # металла может не быть — без краша
    assert ctrl.ship.credits >= 5000 - 100  # продажа не должна списать кредиты


def test_prices_command():
    ctrl, st = _ctrl_at_station()
    ctrl.process_command("prices")
    rendered = ctrl.logger.render_plain(n=20)
    assert "buy=" in rendered


def test_market_scan_and_history():
    ctrl, st = _ctrl_at_station()
    ctrl.process_command("market scan 5")
    rendered = ctrl.logger.render_plain(n=20)
    assert any(s.name.lower() in rendered.lower() for s in ctrl.galaxy.stations[:3])
    # история цен конкретной станции
    ctrl.process_command(f"market history {st.name.lower()} metal")


def test_reputation_and_diplomacy_commands():
    ctrl = GameController()
    ctrl.process_command("reputation")
    ctrl.process_command("diplomacy")
    rendered = ctrl.logger.render_plain(n=30)
    assert len(rendered) > 0


def test_declare_war():
    ctrl = GameController()
    ctrl.process_command("declare war imperium")
    assert ctrl.ship.reputation["imperium"] == -100


def test_attack_no_npc():
    ctrl = GameController()
    result = ctrl.process_command("attack NobodyHere")
    assert result is None
    rendered = ctrl.logger.render_plain(n=10)
    assert "NobodyHere" in rendered


def test_hail_no_npc():
    ctrl = GameController()
    ctrl.process_command("hail")
    rendered = ctrl.logger.render_plain(n=10)
    assert len(rendered) > 0


def test_smuggle_success():
    ctrl, st = _ctrl_at_station()
    ctrl.ship.cargo.add("relic", 2)
    credits_before = ctrl.ship.credits
    ctrl.process_command("smuggle relic 1")
    assert ctrl.ship.cargo.has("relic") == 1
    assert ctrl.ship.credits > credits_before


def test_news_command():
    ctrl = GameController()
    ctrl.galaxy.add_news("Headline", "Body")
    ctrl.process_command("news")
    rendered = ctrl.logger.render_plain(n=10)
    assert "Headline" in rendered


def test_modules_list_command():
    ctrl = GameController()
    ctrl.process_command("modules list")
    rendered = ctrl.logger.render_plain(n=10)
    assert len(rendered) > 0


# =============================================================================
# handle_log_command branches
# =============================================================================

def test_log_show_and_empty():
    ctrl = GameController()
    ctrl.logger.clear()
    ctrl.handle_log_command(["log", "show"])
    rendered = ctrl.logger.render_plain(n=10)
    assert "Log empty" in rendered


def test_log_search_no_match():
    ctrl = GameController()
    ctrl.handle_log_command(["log", "search", "zzz_not_here"])
    rendered = ctrl.logger.render_plain(n=10)
    assert "No matches" in rendered


def test_log_unknown_filter():
    ctrl = GameController()
    ctrl.handle_log_command(["log", "filter", "bogus"])
    rendered = ctrl.logger.render_plain(n=10)
    assert "Unknown filter" in rendered


def test_log_detail_command():
    ctrl = GameController()
    ctrl.handle_log_command(["log", "detail", "low"])
    assert ctrl.logger.detail_level.value <= 2
    ctrl.handle_log_command(["log", "detail", "bogus"])  # не валидно — без краша


# =============================================================================
# _act_land / _act_religion
# =============================================================================

def test_act_land_outcomes():
    ctrl = GameController()
    random.seed(3)
    ctrl._act_land()
    rendered = ctrl.logger.render_plain(n=5)
    assert len(rendered) > 0


def test_act_religion_joins_temple():
    ctrl = GameController()
    st = ctrl.galaxy.stations[0]
    st.stype = "temple"
    st.religion = "machine_god"
    ctrl.player_x, ctrl.player_y = st.x, st.y
    ctrl._act_religion()
    assert ctrl.ship.religion == "machine_god"
    # уже есть религия
    ctrl._act_religion()
    rendered = ctrl.logger.render_plain(n=10).lower()
    assert "already" in rendered or "уже" in rendered


# =============================================================================
# move_player
# =============================================================================

def test_move_blocked_at_edge():
    ctrl = GameController()
    ctrl.state = GameState.PLAYING
    ctrl.player_x, ctrl.player_y = 0, 0
    moved, pending = ctrl.move_player(-1, 0)
    assert moved is False
    assert pending is None


def test_move_consumes_fuel():
    ctrl = GameController()
    ctrl.state = GameState.PLAYING
    px, py = ctrl.player_x, ctrl.player_y
    ctrl.ship.fuel = 5
    # ищем проходимую клетку рядом
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if ctrl.galaxy.is_passable(px + dx, py + dy):
            moved, pending = ctrl.move_player(dx, dy)
            assert moved is True
            assert ctrl.ship.fuel == 4
            return
    pytest.skip("no passable neighbor")


def test_move_into_wormhole_teleports():
    ctrl = GameController()
    ctrl.state = GameState.PLAYING
    from config import TILE_WORMHOLE
    ctrl.galaxy.wormholes = [(10, 10), (20, 20)]
    ctrl.galaxy.tiles[10][10] = TILE_WORMHOLE
    ctrl.galaxy.objects[(10, 10)] = "wormhole"
    ctrl.player_x, ctrl.player_y = 11, 10
    moved, _ = ctrl.move_player(-1, 0)  # шаг на червоточину (10,10)
    assert moved is True
    assert (ctrl.player_x, ctrl.player_y) in [(10, 10), (20, 20)]


def test_move_into_wormhole_collapses():
    ctrl = GameController()
    ctrl.state = GameState.PLAYING
    from config import TILE_WORMHOLE
    ctrl.galaxy.wormholes = [(10, 10)]
    ctrl.galaxy.tiles[10][10] = TILE_WORMHOLE
    ctrl.galaxy.objects[(10, 10)] = "wormhole"
    ctrl.player_x, ctrl.player_y = 11, 10
    moved, _ = ctrl.move_player(-1, 0)
    assert moved is True
    assert (10, 10) not in ctrl.galaxy.wormholes


import pytest
