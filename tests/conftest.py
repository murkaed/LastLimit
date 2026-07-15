# Фикстуры pytest для всех модульных тестов проекта.
# Предоставляют предварительно настроенные объекты: корабль игрока,
# станцию, галактику, NPC, членов экипажа, модули, миссии и т.д.
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
    """Вернуть корабль игрока с базовыми модулями, грузом и кредитами.

    Возвращает:
        PlayerShip: корабль "TestShip" с 5000 кредитов, 80 топлива
                    и небольшим запасом ресурсов.
    """
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
    """Вернуть корабль игрока с минимальным корпусом и без груза.

    Возвращает:
        PlayerShip: корабль "Minimal" с 50 хп корпуса, без груза.
    """
    return PlayerShip("Minimal", 50)


@pytest.fixture
def station():
    """Вернуть торговую станцию со стандартным ассортиментом.

    Создаёт Galaxy для получения корректной карты цен, затем —
    Station типа "trade_hub" с предустановленным инвентарём.

    Возвращает:
        Station: станция "TestHub" на координатах (10, 10).
    """
    g = Galaxy()
    s = Station(10, 10, "TestHub", "trade_hub", "free_traders")
    # Устанавливаем стандартный инвентарь для предсказуемости тестов
    s.inventory = {"metal": 30, "food": 20, "electronics": 10, "ice": 15}
    s.update_prices()
    return s


@pytest.fixture
def galaxy():
    """Вернуть небольшую галактику с фиксированным seed для воспроизводимости.

    Возвращает:
        Galaxy: галактика 30x20, сгенерированная с random.seed(42).
    """
    random.seed(42)  # Фиксируем seed, чтобы тесты были детерминированы
    g = Galaxy(width=30, height=20)
    random.seed()  # Сбрасываем seed, чтобы не влиять на другие тесты
    return g


@pytest.fixture
def pirate():
    """Вернуть NPC-корабль пирата с базовыми характеристиками.

    Возвращает:
        PirateShip: пират "Raider" с 40 ед. корпуса и 10 щитов.
    """
    p = PirateShip(5, 5, "Raider")
    p.hull = 40
    p.max_hull = 40
    p.shield_hp = 10
    return p


@pytest.fixture
def trader():
    """Вернуть NPC-корабль торговца с грузом.

    Возвращает:
        TraderShip: торговец "Merchant" с 60 корпуса и ресурсами.
    """
    t = TraderShip(7, 5, "Merchant")
    t.hull = 60
    t.max_hull = 60
    t.cargo.add("metal", 15)
    t.cargo.add("food", 10)
    t.cargo.add("relic", 1)
    return t


@pytest.fixture
def crew_member():
    """Вернуть члена экипажа с базовыми характеристиками и снаряжением.

    Возвращает:
        CrewMember: член экипажа "Zara", пилот-человек с пистолетом
                    и бронёй, 30 хп, 50 боевого навыка.
    """
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
    """Вернуть базовый корабельный модуль для тестирования.

    Возвращает:
        ShipModule: модуль "laser_turret" с параметрами из конфига.
    """
    return ShipModule("laser_turret")


@pytest.fixture
def cargo_hold():
    """Вернуть грузовой отсек с несколькими предметами.

    Возвращает:
        CargoHold: отсек на 100 единиц, заполненный металлом (20),
                   электроникой (10) и едой (5).
    """
    ch = CargoHold(100)
    ch.add("metal", 20)
    ch.add("electronics", 10)
    ch.add("food", 5)
    return ch


@pytest.fixture
def mission():
    """Вернуть стандартную миссию на доставку ресурсов.

    Возвращает:
        Mission: миссия типа "deliver" — доставить 5 металла
                 на станцию "TargetStation" за награду 200 кредитов.
    """
    m = Mission(
        "deliver", "metal", 5, "TargetStation", 200, 30,
        title="Test Delivery", description="Deliver 5 metal.",
    )
    return m


@pytest.fixture
def settings_file(tmp_path):
    """Создать временный файл настроек и подменить путь в config.

    Использует tmp_path для изоляции тестов от реального settings.json.

    Возвращает:
        str: путь к временному файлу настроек.
    """
    import os
    old = os.path.join(os.getcwd(), "settings.json")
    new = str(tmp_path / "settings.json")
    # Подменяем путь в модуле config, чтобы тесты не трогали реальный файл
    import config as cfg
    cfg.SETTINGS_FILE = new
    return new


@pytest.fixture
def expedition_map():
    """Вернуть предварительно сгенерированную карту экспедиции с фиксированным seed.

    Возвращает:
        ExpeditionMap: карта 20x15 с точкой назначения "station".
    """
    from expedition import ExpeditionMap
    random.seed(42)  # Детерминированная генерация карты
    emp = ExpeditionMap(20, 15, "station")
    random.seed()  # Сбрасываем seed
    return emp
