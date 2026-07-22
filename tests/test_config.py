"""Tests for config.py — constants and data integrity."""

import pytest
from config import (
    WIDTH, HEIGHT,
    TILE_EMPTY, TILE_STAR, TILE_PLANET, TILE_STATION,
    TILE_BLACK_HOLE, TILE_WORMHOLE, TILE_ASTEROIDS,
    TILE_SHIP, TILE_OTHER_SHIP, TILE_CURSOR,
    TILE_TRADER, TILE_PIRATE,
    DIR_LABELS, RESOURCES, RACES, RELIGIONS, FACTIONS,
    CONTRABAND, SHIP_MODULES, COMPARTMENTS,
)


class TestDimensions:
    def test_map_size(self):
        assert WIDTH == 80
        assert HEIGHT == 40

    def test_all_directions(self):
        assert len(DIR_LABELS) == 8
        assert DIR_LABELS[(-1, -1)] == "NW"
        assert DIR_LABELS[(0, -1)] == "N"
        assert DIR_LABELS[(1, -1)] == "NE"
        assert DIR_LABELS[(-1, 0)] == "W"
        assert DIR_LABELS[(1, 0)] == "E"
        assert DIR_LABELS[(-1, 1)] == "SW"
        assert DIR_LABELS[(0, 1)] == "S"
        assert DIR_LABELS[(1, 1)] == "SE"


class TestTiles:
    def test_all_unique(self):
        tiles = [
            TILE_EMPTY, TILE_STAR, TILE_PLANET, TILE_STATION,
            TILE_BLACK_HOLE, TILE_WORMHOLE, TILE_ASTEROIDS,
            TILE_SHIP, TILE_OTHER_SHIP, TILE_CURSOR,
            TILE_TRADER, TILE_PIRATE,
        ]
        assert len(tiles) == len(set(tiles))


class TestResources:
    def test_all_have_required_fields(self):
        for rid, info in RESOURCES.items():
            assert "name" in info, f"{rid} missing name"
            assert "cat" in info, f"{rid} missing cat"
            assert "base_price" in info, f"{rid} missing base_price"
            assert info["base_price"] > 0, f"{rid} base_price must be positive"
            assert info["cat"] in ("raw", "refined", "advanced", "special", "consumable"), \
                f"{rid} unknown category: {info['cat']}"

    def test_resource_count(self):
        assert len(RESOURCES) == 10


class TestRaces:
    def test_all_have_name(self):
        for rid, info in RACES.items():
            assert "name" in info, f"{rid} missing name"

    def test_race_count(self):
        assert len(RACES) == 5


class TestFactions:
    def test_all_have_name(self):
        for fid, info in FACTIONS.items():
            assert "name" in info, f"{fid} missing name"

    def test_faction_count(self):
        assert len(FACTIONS) == 6

    def test_contraband_keys_match_factions(self):
        for faction in CONTRABAND:
            assert faction in FACTIONS or faction in RELIGIONS, \
                f"Contraband key '{faction}' not a faction or religion"


class TestShipModules:
    def test_all_have_required_fields(self):
        for mid, info in SHIP_MODULES.items():
            assert "name" in info, f"{mid} missing name"
            assert "comp" in info, f"{mid} missing comp"
            assert "cost" in info, f"{mid} missing cost"
            assert "durability" in info, f"{mid} missing durability"
            assert info["cost"] > 0, f"{mid} cost must be positive"

    def test_compartments_valid(self):
        for mid, info in SHIP_MODULES.items():
            assert info["comp"] in COMPARTMENTS, \
                f"{mid} comp '{info['comp']}' not in COMPARTMENTS"

    def test_module_count(self):
        assert len(SHIP_MODULES) == 14


class TestCompartments:
    def test_compartment_count(self):
        assert len(COMPARTMENTS) == 7

    def test_required_compartments(self):
        required = {"reactor", "engine", "weapon", "shield", "sensor", "life_support", "cargo"}
        assert set(COMPARTMENTS) == required
