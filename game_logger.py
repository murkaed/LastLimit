"""
Сервис логирования игровых событий.
Уровни: DEBUG, MOVEMENT, EXPLORATION, SYSTEM, TRADE, COMBAT, DANGER.
Каждая запись содержит: timestamp, уровень, сообщение, номер хода.
"""

from enum import IntEnum
from datetime import datetime
from collections import deque
from typing import Optional


class LogLevel(IntEnum):
    DEBUG = 0
    MOVEMENT = 1
    EXPLORATION = 2
    SYSTEM = 3
    TRADE = 4
    COMBAT = 5
    DANGER = 6


LEVEL_ICON = {
    LogLevel.DEBUG: "···",
    LogLevel.MOVEMENT: " →",
    LogLevel.EXPLORATION: "✦",
    LogLevel.SYSTEM: "⚙",
    LogLevel.TRADE: "$",
    LogLevel.COMBAT: "⚔",
    LogLevel.DANGER: "☠",
}

LEVEL_NAME = {
    LogLevel.DEBUG: "DEBUG",
    LogLevel.MOVEMENT: "MOVE",
    LogLevel.EXPLORATION: "EXPL",
    LogLevel.SYSTEM: "SYS",
    LogLevel.TRADE: "TRADE",
    LogLevel.COMBAT: "COMBAT",
    LogLevel.DANGER: "DANGER",
}


class LogEntry:
    """Одна запись в логе."""

    __slots__ = ("timestamp", "level", "message", "turn")

    def __init__(self, level: LogLevel, message: str, turn: Optional[int] = None):
        self.timestamp = datetime.now()
        self.level = level
        self.message = message
        self.turn = turn

    def format(self, show_turn: bool = False) -> str:
        time_str = self.timestamp.strftime("%H:%M:%S")
        icon = LEVEL_ICON.get(self.level, "?")
        if show_turn and self.turn is not None:
            return f"{time_str} [{icon}] T{self.turn:03d} {self.message}"
        return f"{time_str} [{icon}] {self.message}"


class GameLogger:
    """Кольцевой буфер логов с категоризацией."""

    def __init__(self, max_entries: int = 500):
        self.entries: deque[LogEntry] = deque(maxlen=max_entries)
        self.turn: int = 0

    # ---- счётчик ходов ----

    def new_turn(self) -> int:
        self.turn += 1
        return self.turn

    # ---- низкоуровневый метод ----

    def log(self, level: LogLevel, message: str) -> None:
        self.entries.append(LogEntry(level, message, self.turn))

    # ---- удобные методы по категориям ----

    def debug(self, message: str) -> None:
        self.log(LogLevel.DEBUG, message)

    def movement(self, direction: str, x: int, y: int) -> None:
        self.log(LogLevel.MOVEMENT, f"Moved {direction} → ({x}, {y})")

    def blocked(self, direction: str, obj: str) -> None:
        self.log(LogLevel.MOVEMENT, f"Blocked {direction} — {obj}")

    def exploration(self, message: str) -> None:
        self.log(LogLevel.EXPLORATION, message)

    def system(self, message: str) -> None:
        self.log(LogLevel.SYSTEM, message)

    def trade(self, message: str) -> None:
        self.log(LogLevel.TRADE, message)

    def combat(self, message: str) -> None:
        self.log(LogLevel.COMBAT, message)

    def danger(self, message: str) -> None:
        self.log(LogLevel.DANGER, message)

    # ---- получение записей ----

    def get_last(self, n: int = 10) -> list[LogEntry]:
        return list(self.entries)[-n:]

    def get_by_level(self, level: LogLevel, n: int = 20) -> list[LogEntry]:
        filtered = [e for e in self.entries if e.level == level]
        return filtered[-n:]

    # ---- форматированный вывод ----

    def render(self, n: int = 10, show_turn: bool = False) -> str:
        return "\n".join(e.format(show_turn) for e in self.get_last(n))

    def clear(self) -> None:
        self.entries.clear()
        self.turn = 0
