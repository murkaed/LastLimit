# ============================================================================
# game_logger.py — Сервис логирования игровых событий
#
# Предоставляет кольцевой буфер (deque) для ведения лога событий с
# категоризацией по уровням (DEBUG, MOVEMENT, EXPLORATION, SYSTEM, TRADE,
# COMBAT, DANGER) и форматированным выводом. Используется во всём проекте
# для записи и отображения игровых событий в интерфейсе.
# ============================================================================

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
    """Уровни логирования событий от наименее (DEBUG) до наиболее (DANGER) важного."""
    DEBUG = 0        # отладочная информация
    MOVEMENT = 1     # перемещение игрока
    EXPLORATION = 2  # исследование секторов
    SYSTEM = 3       # системные события (загрузка, сохранение)
    TRADE = 4        # торговые операции
    COMBAT = 5       # боевые события
    DANGER = 6       # опасные события (атаки, повреждения)


LEVEL_ICON = {
    LogLevel.DEBUG: "···",
    LogLevel.MOVEMENT: " →",
    LogLevel.EXPLORATION: "✦",
    LogLevel.SYSTEM: "⚙",
    LogLevel.TRADE: "$",
    LogLevel.COMBAT: "⚔",
    LogLevel.DANGER: "☠",
}  # иконки для каждого уровня лога

LEVEL_NAME = {
    LogLevel.DEBUG: "DEBUG",
    LogLevel.MOVEMENT: "MOVE",
    LogLevel.EXPLORATION: "EXPL",
    LogLevel.SYSTEM: "SYS",
    LogLevel.TRADE: "TRADE",
    LogLevel.COMBAT: "COMBAT",
    LogLevel.DANGER: "DANGER",
}  # текстовые метки уровней лога


class LogEntry:
    """Одна запись в логе."""

    __slots__ = ("timestamp", "level", "message", "turn")

    def __init__(self, level: LogLevel, message: str, turn: Optional[int] = None):
        """
        Инициализирует запись лога.

        Args:
            level:   Уровень события (LogLevel).
            message: Текстовое сообщение события.
            turn:    Номер хода, на котором произошло событие (необязательно).
        """
        self.timestamp = datetime.now()  # временная метка создания записи
        self.level = level               # уровень события
        self.message = message           # текст сообщения
        self.turn = turn                 # номер хода (может быть None)

    def format(self, show_turn: bool = False) -> str:
        """
        Форматирует запись в строку для вывода.

        Args:
            show_turn: Если True, добавляет номер хода в формат.

        Returns:
            str: Отформатированная строка вида "ЧЧ:ММ:СС [иконка] [TXXX] сообщение".
        """
        time_str = self.timestamp.strftime("%H:%M:%S")
        icon = LEVEL_ICON.get(self.level, "?")
        if show_turn and self.turn is not None:
            return f"{time_str} [{icon}] T{self.turn:03d} {self.message}"
        return f"{time_str} [{icon}] {self.message}"


class GameLogger:
    """Кольцевой буфер логов с категоризацией."""

    def __init__(self, max_entries: int = 500):
        """
        Инициализирует логгер с кольцевым буфером.

        Args:
            max_entries: Максимальное количество записей в буфере (по умолчанию 500).
        """
        self.entries: deque[LogEntry] = deque(maxlen=max_entries)  # кольцевой буфер записей
        self.turn: int = 0  # текущий номер хода

    # ---- счётчик ходов ----

    def new_turn(self) -> int:
        """
        Увеличивает счётчик ходов на 1.

        Returns:
            int: Новый номер хода.
        """
        self.turn += 1
        return self.turn

    # ---- низкоуровневый метод ----

    def log(self, level: LogLevel, message: str) -> None:
        """
        Добавляет запись в лог с указанным уровнем.

        Args:
            level:   Уровень события (LogLevel).
            message: Текстовое сообщение.
        """
        self.entries.append(LogEntry(level, message, self.turn))

    # ---- удобные методы по категориям ----

    def debug(self, message: str) -> None:
        """Добавляет отладочное сообщение в лог."""
        self.log(LogLevel.DEBUG, message)

    def movement(self, direction: str, x: int, y: int) -> None:
        """Добавляет запись о перемещении в указанном направлении."""
        self.log(LogLevel.MOVEMENT, f"Moved {direction} → ({x}, {y})")

    def blocked(self, direction: str, obj: str) -> None:
        """Добавляет запись о блокировке движения препятствием."""
        self.log(LogLevel.MOVEMENT, f"Blocked {direction} — {obj}")

    def exploration(self, message: str) -> None:
        """Добавляет сообщение об исследовании сектора."""
        self.log(LogLevel.EXPLORATION, message)

    def system(self, message: str) -> None:
        """Добавляет системное сообщение (загрузка, сохранение и т.п.)."""
        self.log(LogLevel.SYSTEM, message)

    def trade(self, message: str) -> None:
        """Добавляет запись о торговой операции."""
        self.log(LogLevel.TRADE, message)

    def combat(self, message: str) -> None:
        """Добавляет запись о боевом событии."""
        self.log(LogLevel.COMBAT, message)

    def danger(self, message: str) -> None:
        """Добавляет запись об опасном событии (атака, повреждение)."""
        self.log(LogLevel.DANGER, message)

    # ---- получение записей ----

    def get_last(self, n: int = 10) -> list[LogEntry]:
        """
        Возвращает последние N записей лога.

        Args:
            n: Количество записей (по умолчанию 10).

        Returns:
            list[LogEntry]: Список последних записей.
        """
        return list(self.entries)[-n:]

    def get_by_level(self, level: LogLevel, n: int = 20) -> list[LogEntry]:
        """
        Возвращает последние N записей указанного уровня.

        Args:
            level: Уровень для фильтрации (LogLevel).
            n:     Количество записей (по умолчанию 20).

        Returns:
            list[LogEntry]: Список отфильтрованных записей.
        """
        filtered = [e for e in self.entries if e.level == level]
        return filtered[-n:]

    # ---- форматированный вывод ----

    def render(self, n: int = 10, show_turn: bool = False) -> str:
        """
        Возвращает отформатированный текст последних N записей.

        Args:
            n:         Количество записей (по умолчанию 10).
            show_turn: Показывать номер хода.

        Returns:
            str: Многострочный текст лога, готовый для вывода в интерфейс.
        """
        return "\n".join(e.format(show_turn) for e in self.get_last(n))

    def clear(self) -> None:
        """Очищает все записи лога и сбрасывает счётчик ходов в ноль."""
        self.entries.clear()
        self.turn = 0
