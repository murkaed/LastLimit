"""Tests for game_logger.py."""

import pytest
from game_logger import GameLogger, LogLevel, LogEntry


class TestLogLevel:
    def test_ordering(self):
        assert LogLevel.DEBUG < LogLevel.MOVEMENT < LogLevel.EXPLORATION
        assert LogLevel.SYSTEM < LogLevel.TRADE < LogLevel.COMBAT < LogLevel.DANGER


class TestLogEntry:
    def test_format_basic(self):
        entry = LogEntry(LogLevel.COMBAT, "test message")
        result = entry.format()
        assert "[⚔]" in result
        assert "test message" in result

    def test_format_with_turn(self):
        entry = LogEntry(LogLevel.DANGER, "critical", turn=5)
        result = entry.format(show_turn=True)
        assert "T005" in result
        assert "critical" in result

    def test_format_without_turn_when_none(self):
        entry = LogEntry(LogLevel.SYSTEM, "msg", turn=None)
        result = entry.format(show_turn=True)
        assert "T" not in result or "TNone" not in result


class TestGameLogger:
    def test_initial_state(self):
        logger = GameLogger()
        assert logger.turn == 0
        assert len(logger.entries) == 0

    def test_new_turn_increments(self):
        logger = GameLogger()
        assert logger.new_turn() == 1
        assert logger.new_turn() == 2
        assert logger.turn == 2

    def test_log_adds_entry(self):
        logger = GameLogger()
        logger.log(LogLevel.SYSTEM, "hello")
        assert len(logger.entries) == 1
        assert logger.entries[0].message == "hello"
        assert logger.entries[0].level == LogLevel.SYSTEM

    def test_convenience_methods(self):
        logger = GameLogger()
        logger.debug("d")
        logger.movement("N", 10, 5)
        logger.blocked("S", "star")
        logger.exploration("found")
        logger.system("sys")
        logger.trade("trade")
        logger.combat("fight")
        logger.danger("boom")
        assert len(logger.entries) == 8
        levels = [e.level for e in logger.entries]
        assert levels == [
            LogLevel.DEBUG, LogLevel.MOVEMENT, LogLevel.MOVEMENT,
            LogLevel.EXPLORATION, LogLevel.SYSTEM, LogLevel.TRADE,
            LogLevel.COMBAT, LogLevel.DANGER,
        ]

    def test_movement_logs_direction(self):
        logger = GameLogger()
        logger.movement("NE", 15, 30)
        assert "NE" in logger.entries[0].message
        assert "15" in logger.entries[0].message
        assert "30" in logger.entries[0].message

    def test_blocked_logs_direction_and_obj(self):
        logger = GameLogger()
        logger.blocked("W", "black hole")
        assert "W" in logger.entries[0].message
        assert "black hole" in logger.entries[0].message

    def test_get_last(self):
        logger = GameLogger()
        for i in range(20):
            logger.system(f"msg{i}")
        last = logger.get_last(5)
        assert len(last) == 5
        assert last[-1].message == "msg19"

    def test_get_last_more_than_entries(self):
        logger = GameLogger()
        logger.system("only")
        assert len(logger.get_last(10)) == 1

    def test_get_by_level(self):
        logger = GameLogger()
        logger.system("s1")
        logger.combat("c1")
        logger.system("s2")
        logger.combat("c2")
        logger.system("s3")
        combat = logger.get_by_level(LogLevel.COMBAT, 10)
        assert len(combat) == 2
        assert all(e.level == LogLevel.COMBAT for e in combat)

    def test_get_by_level_limits(self):
        logger = GameLogger()
        for _ in range(30):
            logger.combat("hit")
        result = logger.get_by_level(LogLevel.COMBAT, 5)
        assert len(result) == 5

    def test_render(self):
        logger = GameLogger()
        logger.system("test")
        rendered = logger.render(1)
        assert "test" in rendered
        assert "⚙" in rendered

    def test_render_show_turn(self):
        logger = GameLogger()
        logger.new_turn()
        logger.system("t1")
        logger.new_turn()
        logger.system("t2")
        rendered = logger.render(2, show_turn=True)
        lines = rendered.split("\n")
        assert "T001" in lines[0]
        assert "T002" in lines[1]

    def test_clear(self):
        logger = GameLogger()
        logger.system("msg")
        logger.new_turn()
        logger.clear()
        assert len(logger.entries) == 0
        assert logger.turn == 0

    def test_ring_buffer_behavior(self):
        logger = GameLogger(max_entries=10)
        for i in range(15):
            logger.system(f"msg{i}")
        assert len(logger.entries) == 10
        assert logger.entries[0].message == "msg5"
        assert logger.entries[-1].message == "msg14"

    def test_entry_turn_defaults_to_logger_turn(self):
        logger = GameLogger()
        logger.new_turn()
        logger.new_turn()
        logger.system("msg")
        assert logger.entries[0].turn == 2
