# ============================================================================
# game_logger.py — Улучшенная система логирования с категориями, фильтрами
# и уровнями детализации.
#
# Сообщение = LogMessage (dataclass):
#   - timestamp, level (LogLevel), category (LogCategory), text, context dict
# Фильтрация: по категории, min_level, detail, поиск по тексту.
# Цвета категорий: Rich-разметка для Textual.
# ============================================================================

from __future__ import annotations

from enum import IntEnum, auto
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════

class LogLevel(IntEnum):
    """Уровни важности сообщения. Чем больше число, тем важнее."""
    DEBUG = 0
    MOVEMENT = 1
    EXPLORATION = 2
    SYSTEM = 3
    INFO = 4
    TRADE = 5
    COMBAT = 6
    DANGER = 7


class LogCategory(IntEnum):
    """Категории сообщений — кто/что источник события."""
    WORLD = auto()       # события галактики
    SHIP = auto()        # состояние корабля
    COMBAT = auto()      # боевые действия
    ECONOMY = auto()     # торговля, крафт, цены
    MISSION = auto()     # миссии
    NPC = auto()         # действия NPC
    CREW = auto()        # экипаж
    SYSTEM = auto()      # технические сообщения
    MOVEMENT = auto()    # перемещения
    EXPLORATION = auto() # исследование


class DetailLevel(IntEnum):
    """Уровень детализации лога для игрока (настройка)."""
    LOW = 0      # только DANGER + миссии + SYSTEM
    MEDIUM = 1   # + COMBAT + TRADE + MOVEMENT
    HIGH = 2     # + всё остальное (кроме DEBUG)
    DEBUG = 3    # всё, включая debug


# ═══════════════════════════════════════════════════════════════════════
# Соответствие категория → минимальный уровень детализации для показа
# ═══════════════════════════════════════════════════════════════════════

CATEGORY_VISIBILITY = {
    LogCategory.WORLD:       DetailLevel.HIGH,
    LogCategory.SHIP:        DetailLevel.MEDIUM,
    LogCategory.COMBAT:      DetailLevel.MEDIUM,
    LogCategory.ECONOMY:     DetailLevel.MEDIUM,
    LogCategory.MISSION:     DetailLevel.LOW,
    LogCategory.NPC:         DetailLevel.HIGH,
    LogCategory.CREW:        DetailLevel.HIGH,
    LogCategory.SYSTEM:      DetailLevel.LOW,
    LogCategory.MOVEMENT:    DetailLevel.MEDIUM,
    LogCategory.EXPLORATION: DetailLevel.MEDIUM,
}

# ═══════════════════════════════════════════════════════════════════════
# Цвета категорий (Rich-разметка)
# ═══════════════════════════════════════════════════════════════════════

CATEGORY_COLOR = {
    LogCategory.WORLD:       "grey58",
    LogCategory.SHIP:        "cyan",
    LogCategory.COMBAT:      "red",
    LogCategory.ECONOMY:     "green",
    LogCategory.MISSION:     "blue",
    LogCategory.NPC:         "magenta",
    LogCategory.CREW:        "yellow",
    LogCategory.SYSTEM:      "white",
    LogCategory.MOVEMENT:    "dim white",
    LogCategory.EXPLORATION: "dim cyan",
}

CATEGORY_LABEL = {
    LogCategory.WORLD:       "WORLD",
    LogCategory.SHIP:        "SHIP",
    LogCategory.COMBAT:      "COMBAT",
    LogCategory.ECONOMY:     "ECO",
    LogCategory.MISSION:     "MISSION",
    LogCategory.NPC:         "NPC",
    LogCategory.CREW:        "CREW",
    LogCategory.SYSTEM:      "SYS",
    LogCategory.MOVEMENT:    "MOVE",
    LogCategory.EXPLORATION: "EXPL",
}

LEVEL_ICON = {
    LogLevel.DEBUG: "···",
    LogLevel.MOVEMENT: " →",
    LogLevel.EXPLORATION: "✦",
    LogLevel.SYSTEM: "⚙",
    LogLevel.INFO: "i",
    LogLevel.TRADE: "$",
    LogLevel.COMBAT: "⚔",
    LogLevel.DANGER: "☠",
}

LEVEL_NAME = {
    LogLevel.DEBUG: "DEBUG",
    LogLevel.MOVEMENT: "MOVE",
    LogLevel.EXPLORATION: "EXPL",
    LogLevel.SYSTEM: "SYSTEM",
    LogLevel.INFO: "INFO",
    LogLevel.TRADE: "TRADE",
    LogLevel.COMBAT: "COMBAT",
    LogLevel.DANGER: "DANGER",
}

DETAIL_NAME = {
    DetailLevel.LOW: "low",
    DetailLevel.MEDIUM: "medium",
    DetailLevel.HIGH: "high",
    DetailLevel.DEBUG: "debug",
}


# ═══════════════════════════════════════════════════════════════════════
# LogMessage — одно сообщение в логе
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class LogMessage:
    """Одно сообщение в игровом логе."""
    timestamp: datetime = field(default_factory=datetime.now)
    level: LogLevel = LogLevel.INFO
    category: LogCategory = LogCategory.SYSTEM
    text: str = ""
    context: dict = field(default_factory=dict)
    turn: int = 0

    def format(self, show_turn: bool = False) -> str:
        """Форматирует сообщение как строку с Rich-разметкой.

        Returns:
            str вида "ЧЧ:ММ:СС [icon] [категория] сообщение (context)".
        """
        time_str = self.timestamp.strftime("%H:%M:%S")
        icon = LEVEL_ICON.get(self.level, "?")
        cat_label = CATEGORY_LABEL.get(self.category, "?")
        cat_color = CATEGORY_COLOR.get(self.category, "white")
        prefix = f"[{icon}]" if icon else ""
        turn_str = f" T{self.turn:03d}" if show_turn and self.turn > 0 else ""
        ctx = ""
        if self.context:
            parts = []
            for k, v in self.context.items():
                if isinstance(v, (int, float)):
                    parts.append(f"{k}={v}")
                else:
                    parts.append(f"{k}={v}")
            ctx = " (" + " ".join(parts) + ")"
        return (
            f"{time_str} {prefix}"
            f" [{cat_color}]{cat_label}[/]"
            f"{turn_str} {self.text}{ctx}"
        )

    def format_plain(self) -> str:
        """Форматирует без Rich-разметки (для консоли/поиска)."""
        icon = LEVEL_ICON.get(self.level, "?")
        cat_label = CATEGORY_LABEL.get(self.category, "?")
        time_str = self.timestamp.strftime("%H:%M:%S")
        ctx = ""
        if self.context:
            ctx = " (" + " ".join(f"{k}={v}" for k, v in self.context.items()) + ")"
        return f"{time_str} [{icon}] [{cat_label}] {self.text}{ctx}"


# ═══════════════════════════════════════════════════════════════════════
# GameLogger — кольцевой буфер с фильтрацией
# ═══════════════════════════════════════════════════════════════════════

class GameLogger:
    """Улучшенный кольцевой буфер логов с категориями, фильтрами, детализацией.

    Примеры:
        logger = GameLogger(max_entries=1000)
        logger.log(LogLevel.COMBAT, LogCategory.COMBAT, "Missile hit!")
        logger.combat("Ship destroyed!")  # backward compat → category=COMBAT
        logger.info("Docking complete.", category=LogCategory.SHIP,
                     context={"station": "A-7", "x": 5, "y": 12})
        msgs = logger.get_messages(category=LogCategory.COMBAT, min_level=LogLevel.INFO)
    """

    def __init__(self, max_entries: int = 1000):
        self.entries: deque[LogMessage] = deque(maxlen=max_entries)
        self.turn: int = 0
        self.detail_level: DetailLevel = DetailLevel.MEDIUM  # настройка игрока

    # ── Счётчик ходов ──

    def new_turn(self) -> int:
        self.turn += 1
        return self.turn

    # ── Основной метод логирования ──

    def log(
        self,
        level: LogLevel,
        category: LogCategory,
        text: str,
        **context,
    ) -> None:
        """Добавляет запись в лог.

        Args:
            level: уровень важности.
            category: категория события.
            text: текст сообщения.
            **context: дополнительный контекст (координаты, ID, значения).
        """
        self.entries.append(LogMessage(
            timestamp=datetime.now(),
            level=level,
            category=category,
            text=text,
            context=context,
            turn=self.turn,
        ))

    # ── Удобные методы с авто-категорией (backward compat + улучшенные) ──

    def debug(self, text: str, **context) -> None:
        self.log(LogLevel.DEBUG, LogCategory.SYSTEM, text, **context)

    def movement(self, direction: str, x: int, y: int) -> None:
        self.log(LogLevel.MOVEMENT, LogCategory.MOVEMENT,
                 f"Moved {direction} → ({x}, {y})", x=x, y=y)

    def blocked(self, direction: str, obj: str, **context) -> None:
        self.log(LogLevel.MOVEMENT, LogCategory.MOVEMENT,
                 f"Blocked {direction} — {obj}", **context)

    def exploration(self, text: str, **context) -> None:
        self.log(LogLevel.EXPLORATION, LogCategory.EXPLORATION, text, **context)

    def system(self, text: str, **context) -> None:
        self.log(LogLevel.SYSTEM, LogCategory.SYSTEM, text, **context)

    def trade(self, text: str, **context) -> None:
        self.log(LogLevel.TRADE, LogCategory.ECONOMY, text, **context)

    def combat(self, text: str, **context) -> None:
        self.log(LogLevel.COMBAT, LogCategory.COMBAT, text, **context)

    def danger(self, text: str, **context) -> None:
        self.log(LogLevel.DANGER, LogCategory.COMBAT, text, **context)

    def info(self, text: str, category: LogCategory = LogCategory.SYSTEM,
             **context) -> None:
        self.log(LogLevel.INFO, category, text, **context)

    def ship(self, text: str, **context) -> None:
        self.log(LogLevel.INFO, LogCategory.SHIP, text, **context)

    def mission(self, text: str, **context) -> None:
        self.log(LogLevel.INFO, LogCategory.MISSION, text, **context)

    def economy(self, text: str, **context) -> None:
        self.log(LogLevel.INFO, LogCategory.ECONOMY, text, **context)

    def world(self, text: str, **context) -> None:
        self.log(LogLevel.INFO, LogCategory.WORLD, text, **context)

    def npc(self, text: str, **context) -> None:
        self.log(LogLevel.INFO, LogCategory.NPC, text, **context)

    def crew(self, text: str, **context) -> None:
        self.log(LogLevel.INFO, LogCategory.CREW, text, **context)

    # ── Фильтрация ──

    def get_messages(
        self,
        category: LogCategory | None = None,
        min_level: LogLevel | None = None,
        detail: DetailLevel | None = None,
        search: str | None = None,
        n: int = 0,
    ) -> list[LogMessage]:
        """Возвращает записи лога с фильтрацией.

        Args:
            category: показать только эту категорию (None = все).
            min_level: минимальный уровень важности.
            detail: уровень детализации. None = self.detail_level.
            search: поиск по тексту (case-insensitive substring).
            n: макс. количество (0 = все).

        Returns:
            Список LogMessage, отфильтрованный и отсортированный по времени.
        """
        if detail is None:
            detail = self.detail_level
        result = list(self.entries)
        # Фильтр по категории
        if category is not None:
            result = [e for e in result if e.category == category]
        # Фильтр по уровню
        if min_level is not None:
            result = [e for e in result if e.level >= min_level]
        # Фильтр по детализации: категория должна быть видна при текущем detail
        result = [e for e in result if CATEGORY_VISIBILITY.get(e.category, DetailLevel.HIGH) <= detail]
        # Поиск по тексту
        if search:
            sl = search.lower()
            result = [e for e in result if sl in e.text.lower()]
        # Последние N
        if n > 0:
            result = result[-n:]
        return result

    def get_last(self, n: int = 10) -> list[LogMessage]:
        """Возвращает последние N записей (без фильтрации)."""
        return list(self.entries)[-n:]

    def get_by_level(self, level: LogLevel, n: int = 20) -> list[LogMessage]:
        """Возвращает последние N записей указанного уровня. (Устаревший метод.)"""
        return self.get_messages(min_level=level, n=n)

    # ── Форматированный вывод ──

    def render(
        self,
        n: int = 10,
        show_turn: bool = False,
        category: LogCategory | None = None,
        search: str | None = None,
    ) -> str:
        """Возвращает отформатированный текст для вставки в Rich-виджет.

        Учитывает self.detail_level и фильтры.

        Returns:
            Многострочная строка с Rich-разметкой.
        """
        msgs = self.get_messages(category=category, search=search, n=n)
        return "\n".join(
            e.format(show_turn=show_turn) for e in msgs
        )

    def render_plain(self, n: int = 10, search: str | None = None) -> str:
        """То же, но без Rich-разметки (для консольных команд)."""
        msgs = self.get_messages(search=search, n=n)
        return "\n".join(e.format_plain() for e in msgs)

    def clear(self) -> None:
        self.entries.clear()
        self.turn = 0
