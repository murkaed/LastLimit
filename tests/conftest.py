"""Shared fixtures for all tests."""

import pytest
import random

from models import (
    PlayerShip, Galaxy, Station, CargoHold, CrewMember,
    PirateShip, TraderShip, ShipModule, Mission,
)
from config import RESOURCES, SHIP_MODULES, COMPARTMENTS, GROUND_ENEMIES
from config import load_settings, save_settings


@pytest.fixture
def player_ship():
    """Player ship with basic modules, some cargo, and credits."""
    s = PlayerShip("TestShip", 100)
    s.credits = 5000
    s.fuel = 80
    s.cargo.add("metal", 10)
    s.cargo.add("electronics", 5)
    s.cargo.add("ice", 8)
    s.cargo.add("repair_kit", 2)
    s.cargo.add("fuel_cell", 1)
    return s


@pytest.fixture
def empty_ship():
    """Player ship with no cargo, minimal hull."""
    return PlayerShip("Minimal", 50)


@pytest.fixture
def station():
    """A trade hub station with standard inventory."""
    g = Galaxy()
    s = Station(10, 10, "TestHub", "trade_hub", "free_traders")
    # Ensure standard inventory
    s.inventory = {"metal": 30, "food": 20, "electronics": 10, "ice": 15}
    s.update_prices()
    return s


@pytest.fixture
def galaxy():
    """Small galaxy with fixed seed for reproducibility."""
    random.seed(42)
    g = Galaxy(width=30, height=20)
    random.seed()
    return g


@pytest.fixture
def pirate():
    """A pirate NPC ship."""
    p = PirateShip(5, 5, "Raider")
    p.hull = 40
    p.max_hull = 40
    p.shield_hp = 10
    return p


@pytest.fixture
def trader():
    """A trader NPC ship."""
    t = TraderShip(7, 5, "Merchant")
    t.hull = 60
    t.max_hull = 60
    t.cargo.add("metal", 15)
    t.cargo.add("food", 10)
    t.cargo.add("relic", 1)
    return t


@pytest.fixture
def crew_member():
    """A crew member with basic stats."""
    cm = CrewMember("Zara", "Pilot", "human")
    cm.hp = 30
    cm.max_hp = 30
    cm.weapon = "pistol"
    cm.armor = "vest"
    cm.inventory = {"repair_kit": 1}
    cm.combat_skill = 50
    return cm


@pytest.fixture
def module():
    """Basic ship module for testing."""
    return ShipModule("laser_turret")


@pytest.fixture
def cargo_hold():
    """Cargo hold with some items."""
    ch = CargoHold(100)
    ch.add("metal", 20)
    ch.add("electronics", 10)
    ch.add("food", 5)
    return ch


@pytest.fixture
def mission():
    """A standard delivery mission."""
    m = Mission(
        "deliver", "metal", 5, "TargetStation", 200, 30,
        title="Test Delivery", description="Deliver 5 metal.",
    )
    return m


@pytest.fixture
def settings_file(tmp_path):
    """Create a temporary settings file and return its path."""
    import os
    old = os.path.join(os.getcwd(), "settings.json")
    new = str(tmp_path / "settings.json")
    # Patch config's SETTINGS_FILE path
    import config as cfg
    cfg.SETTINGS_FILE = new
    return new


@pytest.fixture
def expedition_map():
    """Pre-generated expedition map."""
    from expedition import ExpeditionMap
    random.seed(42)
    emp = ExpeditionMap(20, 15, "station")
    random.seed()
    return emp
