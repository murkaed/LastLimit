"""Coverage tests — game_logger, config, colony gaps (2026-08-03)."""

import json
import os

import pytest

from game_logger import (
    GameLogger, LogMessage, LogLevel, LogCategory, DetailLevel, CATEGORY_LABEL,
    CATEGORY_VISIBILITY,
)
from config import load_settings, save_settings, DEFAULT_SETTINGS
from colony import ColonyManager, ResourceNode, SURFACE_SIZE


# =============================================================================
# game_logger
# =============================================================================

def test_log_message_format_with_context_and_turn():
    m = LogMessage(
        level=LogLevel.DANGER,
        category=LogCategory.COMBAT,
        text="Missile hit!",
        context={"x": 5, "ship": "Raider"},
        turn=7,
    )
    out = m.format(show_turn=True)
    assert "T007" in out
    assert "x=5" in out
    assert "ship=Raider" in out
    assert CATEGORY_LABEL[LogCategory.COMBAT] in out
    plain = m.format_plain()
    assert "Missile hit!" in plain


def test_logger_log_with_context_and_filters():
    lg = GameLogger(max_entries=10)
    lg.log(LogLevel.DANGER, LogCategory.COMBAT, "hit", x=1)
    lg.log(LogLevel.INFO, LogCategory.SYSTEM, "docked", station="A")
    lg.log(LogLevel.DANGER, LogCategory.COMBAT, "miss", x=2)
    # фильтр по категории
    combat = lg.get_messages(category=LogCategory.COMBAT)
    assert len(combat) == 2
    # фильтр по уровню
    danger = lg.get_messages(min_level=LogLevel.DANGER)
    assert len(danger) == 2
    # поиск
    found = lg.get_messages(search="miss")
    assert len(found) == 1
    assert found[0].text == "miss"
    # n
    assert len(lg.get_messages(n=1)) == 1
    # detail — SYSTEM виден на LOW, COMBAT — нет
    lg.detail_level = DetailLevel.LOW
    low = lg.get_messages()
    assert all(CATEGORY_VISIBILITY.get(e.category, DetailLevel.HIGH) <= DetailLevel.LOW
               for e in low)


def test_logger_ring_buffer_overflow():
    lg = GameLogger(max_entries=3)
    for i in range(10):
        lg.log(LogLevel.INFO, LogCategory.SYSTEM, f"msg {i}")
    assert len(lg.entries) == 3
    assert lg.entries[0].text == "msg 7"
    assert lg.get_last(2)[0].text == "msg 8"


def test_logger_render_and_clear():
    lg = GameLogger()
    lg.combat("boom")
    lg.system("notice")
    rendered = lg.render(n=5, show_turn=True)
    assert "boom" in rendered
    plain = lg.render_plain(n=5, search="boom")
    assert "boom" in plain
    assert "notice" not in plain
    lg.clear()
    assert len(lg.entries) == 0


# =============================================================================
# config — settings load/save
# =============================================================================

def test_load_settings_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("config.SETTINGS_FILE", str(tmp_path / "nope.json"))
    assert load_settings() == dict(DEFAULT_SETTINGS)


def test_load_settings_corrupt_json(tmp_path, monkeypatch):
    f = tmp_path / "settings.json"
    f.write_text("{ not json !!", encoding="utf-8")
    monkeypatch.setattr("config.SETTINGS_FILE", str(f))
    assert load_settings() == dict(DEFAULT_SETTINGS)


def test_load_settings_merges_partial(tmp_path, monkeypatch):
    f = tmp_path / "settings.json"
    f.write_text(json.dumps({"lang": "en"}), encoding="utf-8")
    monkeypatch.setattr("config.SETTINGS_FILE", str(f))
    result = load_settings()
    assert result["lang"] == "en"
    assert result["autosave"] == DEFAULT_SETTINGS["autosave"]


def test_save_settings_writes_file(tmp_path, monkeypatch):
    f = tmp_path / "settings.json"
    monkeypatch.setattr("config.SETTINGS_FILE", str(f))
    save_settings({"lang": "ru", "autosave": False})
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data == {"lang": "ru", "autosave": False}


def test_save_settings_oserror_silent(tmp_path, monkeypatch):
    def _raise(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr("config.SETTINGS_FILE", str(tmp_path / "x.json"))
    monkeypatch.setattr("builtins.open", _raise)
    save_settings({"lang": "ru"})  # не должно бросать


# =============================================================================
# colony
# =============================================================================

def _colony():
    c = ColonyManager("C", "temperate")
    c.surface = [["plain"] * SURFACE_SIZE for _ in range(SURFACE_SIZE)]
    c.storage = {"metal": 50, "electronics": 50, "silicon": 50,
                 "ice": 50, "ore": 50, "fuel_cell": 0}
    c.colonists = 20
    c.happiness = 100
    c.max_storage = 1000
    return c


def test_can_place_building_out_of_bounds():
    c = _colony()
    ok, reason = c.can_place_building("mine", -1, 5)
    assert not ok and "Out of bounds" in reason


def test_can_place_building_on_water():
    c = _colony()
    c.surface[5][5] = "water"
    ok, reason = c.can_place_building("mine", 5, 5)
    assert not ok and "can't build" in reason.lower()


def test_can_place_building_overlap_and_limit():
    c = _colony()
    assert c.place_building("mine", 5, 5)
    # тайл уже "building" — нельзя строить поверх
    ok, reason = c.can_place_building("smelter", 5, 5)
    assert not ok and "can't build" in reason.lower()
    # лимит: без командного центра максимум 3 здания
    c.place_building("power_plant_solar", 9, 9)
    c.place_building("smelter", 2, 2)
    ok, reason = c.can_place_building("habitat", 12, 12)
    assert not ok and "limit" in reason.lower()


def test_remove_building_frees_tile():
    c = _colony()
    assert c.place_building("mine", 5, 5)
    assert c.get_building_at(5, 5) is not None
    assert c.remove_building(5, 5)
    assert c.get_building_at(5, 5) is None
    assert c.surface[5][5] == "plain"


def test_get_resource_node_at():
    c = _colony()
    c.resource_nodes = [ResourceNode("ore", 50, 3, 3)]
    node = c.get_resource_node_at(3, 3)
    assert node is not None and node.resource_id == "ore"
    assert c.get_resource_node_at(9, 9) is None


def test_tick_power_shortage_event():
    c = _colony()
    c.place_building("smelter", 5, 5)  # потребляет энергию, без электростанции
    events = c.tick()
    assert any("Power shortage" in e for e in events)


def test_update_power_geothermal_bonus():
    c = _colony()
    c.planet_info["energy_bonus"] = {"geothermal": 50}
    c.place_building("power_plant_geothermal", 5, 5)
    c.tick()
    # -20 базово + 50% = 30
    assert c.power_produced == 30


def test_transfer_limits_and_negative():
    from models import CargoHold
    c = _colony()
    c.storage["metal"] = 10
    cargo = CargoHold(100)
    cargo.add("metal", 5)
    # перегруз: трюм мал — передаётся только влезающее
    small = CargoHold(2)
    moved = c.transfer_to_ship("metal", 10, small)
    assert moved == 2
    assert small.has("metal") == 2
    assert c.storage.get("metal", 0) == 8  # остальное осталось в колонии
    # отрицательные суммы игнорируются
    assert c.transfer_to_ship("metal", -5, cargo) == 0
    assert c.transfer_from_ship("metal", -5, cargo) == 0
