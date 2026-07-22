"""Tests for game_logger.py — категории, уровни, фильтры, контекст."""

import pytest
from game_logger import (
    GameLogger, LogLevel, LogCategory, DetailLevel, LogMessage,
    CATEGORY_VISIBILITY, CATEGORY_COLOR, CATEGORY_LABEL,
    LEVEL_ICON,
)


class TestLogLevel:
    """Level ordering."""

    def test_ordering(self):
        assert LogLevel.DEBUG < LogLevel.MOVEMENT < LogLevel.EXPLORATION
        assert LogLevel.SYSTEM < LogLevel.INFO
        assert LogLevel.INFO < LogLevel.TRADE < LogLevel.COMBAT < LogLevel.DANGER


class TestLogCategory:
    """Category enum integrity."""

    def test_all_categories_have_color(self):
        for cat in LogCategory:
            assert cat in CATEGORY_COLOR, f"{cat} missing color"

    def test_all_categories_have_label(self):
        for cat in LogCategory:
            assert cat in CATEGORY_LABEL, f"{cat} missing label"

    def test_all_categories_have_visibility(self):
        for cat in LogCategory:
            assert cat in CATEGORY_VISIBILITY, f"{cat} missing visibility"


class TestLogMessage:
    """LogMessage formatting."""

    def test_format_basic(self):
        msg = LogMessage(level=LogLevel.COMBAT, category=LogCategory.COMBAT,
                         text="test message")
        result = msg.format()
        assert "test message" in result
        # Rich markup: color tag
        assert "red" in result or "COMBAT" in result

    def test_format_with_turn(self):
        msg = LogMessage(level=LogLevel.DANGER, category=LogCategory.COMBAT,
                         text="critical", turn=5)
        result = msg.format(show_turn=True)
        assert "T005" in result
        assert "critical" in result

    def test_format_plain_has_no_markup(self):
        msg = LogMessage(level=LogLevel.SYSTEM, category=LogCategory.SYSTEM,
                         text="plain msg")
        result = msg.format_plain()
        assert "plain msg" in result
        assert "[/" not in result  # no Rich closing tags

    def test_context_in_format(self):
        msg = LogMessage(level=LogLevel.INFO, category=LogCategory.SHIP,
                         text="docking", context={"station": "A7", "x": 5})
        result = msg.format()
        assert "station=A7" in result
        assert "x=5" in result
        assert "docking" in result


class TestGameLoggerBasic:
    """Basic logger operations."""

    def test_initial_state(self):
        logger = GameLogger()
        assert logger.turn == 0
        assert len(logger.entries) == 0
        assert logger.detail_level == DetailLevel.MEDIUM

    def test_new_turn_increments(self):
        logger = GameLogger()
        assert logger.new_turn() == 1
        assert logger.new_turn() == 2
        assert logger.turn == 2

    def test_log_adds_entry(self):
        logger = GameLogger()
        logger.log(LogLevel.INFO, LogCategory.SYSTEM, "hello")
        assert len(logger.entries) == 1
        assert logger.entries[0].text == "hello"
        assert logger.entries[0].level == LogLevel.INFO
        assert logger.entries[0].category == LogCategory.SYSTEM

    def test_log_with_context(self):
        logger = GameLogger()
        logger.log(LogLevel.COMBAT, LogCategory.COMBAT, "hit!",
                   damage=15, target="pirate")
        e = logger.entries[0]
        assert e.context == {"damage": 15, "target": "pirate"}


class TestGameLoggerConvenience:
    """Convenience methods with auto-category."""

    def test_all_convenience_methods(self):
        logger = GameLogger()
        logger.debug("d")
        logger.movement("N", 10, 5)
        logger.blocked("S", "star")
        logger.exploration("found")
        logger.system("sys")
        logger.trade("trade")
        logger.combat("fight")
        logger.danger("boom")
        logger.info("info")
        logger.ship("ship")
        logger.mission("mission")
        logger.economy("eco")
        logger.world("world")
        logger.npc("npc")
        logger.crew("crew")
        assert len(logger.entries) == 15

    def test_category_mapping(self):
        logger = GameLogger()
        logger.combat("shot")
        assert logger.entries[-1].category == LogCategory.COMBAT
        logger.trade("sold")
        assert logger.entries[-1].category == LogCategory.ECONOMY
        logger.ship("hull low")
        assert logger.entries[-1].category == LogCategory.SHIP
        logger.mission("done")
        assert logger.entries[-1].category == LogCategory.MISSION


class TestGameLoggerFiltering:
    """Filtered retrieval."""

    def test_get_messages_by_category(self):
        logger = GameLogger()
        logger.combat("c1"); logger.trade("t1"); logger.combat("c2")
        msgs = logger.get_messages(category=LogCategory.COMBAT)
        assert len(msgs) == 2
        assert all(m.category == LogCategory.COMBAT for m in msgs)

    def test_get_messages_by_min_level(self):
        logger = GameLogger()
        logger.log(LogLevel.DEBUG, LogCategory.SYSTEM, "debug")
        logger.log(LogLevel.INFO, LogCategory.SYSTEM, "info")
        logger.log(LogLevel.COMBAT, LogCategory.COMBAT, "combat")
        msgs = logger.get_messages(min_level=LogLevel.INFO)
        assert len(msgs) == 2
        assert all(m.level >= LogLevel.INFO for m in msgs)

    def test_get_messages_search(self):
        logger = GameLogger()
        logger.combat("missile hit!"); logger.trade("sold iron")
        logger.system("game saved")
        msgs = logger.get_messages(search="missile")
        assert len(msgs) == 1
        assert "missile" in msgs[0].text

    def test_get_messages_search_case_insensitive(self):
        logger = GameLogger()
        logger.ship("HULL CRITICAL")
        msgs = logger.get_messages(search="hull")
        assert len(msgs) == 1

    def test_get_messages_limit(self):
        logger = GameLogger()
        for i in range(20):
            logger.system(f"msg{i}")
        msgs = logger.get_messages(n=5)
        assert len(msgs) == 5

    def test_get_messages_detail_filter(self):
        """Messages with visibility > detail_level should be hidden."""
        logger = GameLogger()
        logger.detail_level = DetailLevel.LOW
        # LOW: only MISSION and SYSTEM visible by default
        logger.mission("quest")
        logger.combat("fight")  # MEDIUM — should be hidden
        logger.ship("status")  # MEDIUM — should be hidden
        msgs = logger.get_messages()
        assert len(msgs) == 1
        assert msgs[0].category == LogCategory.MISSION

    def test_get_messages_detail_high_shows_all(self):
        logger = GameLogger()
        logger.detail_level = DetailLevel.HIGH
        logger.world("event")
        logger.crew("promoted")
        logger.npc("arrived")
        msgs = logger.get_messages()
        assert len(msgs) == 3

    def test_get_last(self):
        logger = GameLogger()
        for i in range(20):
            logger.system(f"msg{i}")
        last = logger.get_last(5)
        assert len(last) == 5
        assert last[-1].text == "msg19"

    def test_get_last_more_than_entries(self):
        logger = GameLogger()
        logger.system("only")
        assert len(logger.get_last(10)) == 1


class TestGameLoggerRender:
    """Rendering."""

    def test_render(self):
        logger = GameLogger()
        logger.system("test")
        rendered = logger.render(1)
        assert "test" in rendered

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

    def test_render_plain(self):
        logger = GameLogger()
        logger.combat("hit")
        plain = logger.render_plain()
        assert "[/" not in plain  # no Rich markup
        assert "hit" in plain


class TestGameLoggerClear:
    """Clear and ring buffer."""

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
        assert logger.entries[0].text == "msg5"
        assert logger.entries[-1].text == "msg14"
