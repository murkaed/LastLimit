"""
ui.py — Все экраны интерфейса игры LastLimit.

Содержит классы экранов (Screen) для Textual-приложения:
  - ShipHubScreen, BridgeScreen, CommandScreen — навигация и управление
  - EngineeringScreen — распределение энергии и модули отсеков
  - TacticalScreen — оружие, цели и бой
  - CargoScreen, TradeScreen — инвентарь и торговля на станции
  - CrewScreen, HireScreen — экипаж и найм в таверне
  - MissionsScreen, MissionScreen, MissionListScreen — активные и доступные миссии
  - StationServicesScreen — меню услуг станции
  - ModuleShopScreen, ShipyardScreen — магазины модулей и корпусов
  - CraftingScreen — крафт предметов в мастерской
  - LandingPrepScreen — подготовка к высадке на поверхность
  - ScanScreen — активное сканирование объектов в радиусе сенсоров
  - ActionMenu — контекстное меню, вызываемое клавишей E
  - SettingsScreen — настройки языка, автсохранения и клавиш
"""

from textual.screen import Screen
from textual.widgets import Static, Input, DataTable, Footer
from config import RESOURCES, COMPARTMENTS, SHIP_MODULES, SHIP_HULLS, UPGRADES, RECIPES, CREW_SPECIALTIES
# ═══════════════════════════════════════════════════════════════════════

def _box(title, lines, width=54):
    """Wrap content in a single-line box: ┌─ title ─┐ ... └──────┘"""
    t = f" {title} "
    pad = width - 2 - len(t)
    header = "┌" + t + "─" * max(0, pad) + "┐"
    body = [f"│ {ln:<{width-4}} │" for ln in lines]
    footer = "└" + "─" * (width - 2) + "┘"
    return "\n".join([header] + body + [footer])


# ═══════════════════════════════════════════════════════════════════════
# Ship Hub (F1)
# ═══════════════════════════════════════════════════════════════════════

class ShipHubScreen(Screen):
    """Экран быстрой навигации по отсекам корабля (F1). Показывает сводку состояния корпуса, щитов, энергии, груза, экипажа."""

    def compose(self):
        """Создаёт виджет для отображения информации о корабле."""
        yield Static(id="hub-content")

    def on_mount(self):
        """Собирает и отображает сводку по кораблю: корпус, щиты, энергия, груз, экипаж."""
        app = self.app
        if not hasattr(app, "ship"):
            return
        s = app.ship
        st = s.get_effective_stats()
        p_gen = s.total_power_generated()
        p_con = s.total_power_consumed()
        eff = 100 if p_con <= p_gen else max(30, int(p_gen / max(1, p_con) * 100))
        mh = s.max_hull + st.get("hull_bonus", 0)
        crew_n = sum(1 for v in s.crew.values() if v)
        mission_n = len(s.missions)

        # Compartment power summary
        pw_parts = []
        for c in COMPARTMENTS:
            pw = s.compartments[c]["power"]
            mods = s.compartments[c]["modules"]
            if mods:
                pw_parts.append(f"{c}={pw}")
        pw_line = " ".join(pw_parts) if pw_parts else "all=5"

        cargo_val = s.cargo.total_value()
        cb = st.get("cargo_bonus", 0)

        lines = [
            f"┌─ SHIP ─ {s.name} ─ Cr:{s.credits} ──────────────────────┐",
            f"│                                                │",
            f"│  [1] BRIDGE       H:{s.hull}/{mh}  "
            f"🛡{s.shield_hp}/{st['shield_cap']}  ⚡{p_gen}/{p_con} {eff}%  │",
            f"│  [2] ENGINEERING  {pw_line:<30}    │",
            f"│  [3] TACTICAL     ⚔{st['damage']} dmg  "
            f"🎯{st['accuracy']}%  📏rng:{st.get('range',1)}  "
            f"🛡ev:{st['evasion']}%     │",
            f"│  [4] CARGO        {s.cargo.used()}/{s.cargo.capacity + cb} used  "
            f"val:{cargo_val}cr         │",
            f"│  [5] CREW         {crew_n}/4 assigned  "
            f"missions:{mission_n}                 │",
            f"│                                                │",
            f"│  Press 1-5 or Esc to return                    │",
            f"└────────────────────────────────────────────────┘",
        ]
        self.query_one("#hub-content").update("\n".join(lines))

    def on_key(self, event):
        """Обрабатывает нажатия клавиш: 1-5 для перехода к экранам, Escape для возврата."""
        if event.key == "escape":
            event.stop(); self.dismiss()
        elif event.key == "1":
            self.dismiss()
            if hasattr(self.app, "push_screen"):
                self.app.push_screen(BridgeScreen())
        elif event.key == "2":
            self.dismiss()
            if hasattr(self.app, "push_screen"):
                self.app.push_screen(EngineeringScreen())
        elif event.key == "3":
            self.dismiss()
            if hasattr(self.app, "push_screen"):
                self.app.push_screen(TacticalScreen())
        elif event.key == "4":
            self.dismiss()
            if hasattr(self.app, "push_screen"):
                self.app.push_screen(CargoScreen())
        elif event.key == "5":
            self.dismiss()
            if hasattr(self.app, "push_screen"):
                self.app.push_screen(CrewScreen())


# ═══════════════════════════════════════════════════════════════════════
# Command console
# ═══════════════════════════════════════════════════════════════════════

class CommandScreen(Screen):
    """Экран командной консоли. Принимает текстовую команду и передаёт ее в app.process_command()."""

    def compose(self):
        """Создаёт поле ввода текстовой команды."""
        yield Input(placeholder="Enter command (help for list)...", id="cmd-input")

    def on_input_submitted(self, event):
        """Передаёт введённую команду в app.process_command() и закрывает экран."""
        app = self.app
        if hasattr(app, "process_command"):
            app.process_command(event.value)
        self.dismiss()


# ═══════════════════════════════════════════════════════════════════════
# Cargo Screen (from bridge)
# ═══════════════════════════════════════════════════════════════════════

CATEGORY_LABELS = {"raw": "Raw", "refined": "Refined", "advanced": "Adv", "special": "Special"}
CATEGORY_ORDER = {"raw": 0, "refined": 1, "advanced": 2, "special": 3, "module": 4}


class CargoScreen(Screen):
    """Экран грузового отсека. Отображает содержимое трюма, фильтры по категориям, позволяет использовать или выбрасывать предметы."""

    def __init__(self):
        """Инициализирует экран: фильтр «все» и индекс выбранного элемента."""
        super().__init__()
        self._filter = "all"  # текущий фильтр категории: all/raw/refined/advanced/special/module
        self._selected = 0  # индекс выбранной строки в списке

    def compose(self):
        """Создаёт виджеты заголовка, фильтров, таблицы, подвала и поля поиска."""
        yield Static(id="cargo-header")
        yield Static(id="cargo-filters")
        yield Static(id="cargo-table")
        yield Static(id="cargo-footer")
        yield Input(placeholder="search: type item name  |  close", id="cargo-input")

    def on_mount(self):
        """При монтировании обновляет отображение груза."""
        self._refresh()

    # -- helpers --
    def _item_cat(self, rid):
        """Возвращает категорию ресурса (raw/refined/advanced/special/module)."""
        info = RESOURCES.get(rid, {})
        if info: return info.get("cat", "unknown")
        if rid in SHIP_MODULES: return "module"
        return "unknown"

    def _item_name(self, rid):
        """Возвращает отображаемое имя предмета по его идентификатору."""
        info = RESOURCES.get(rid, {})
        if info: return info.get("name", rid)
        info = SHIP_MODULES.get(rid, {})
        if info: return info.get("name", rid)
        return rid

    def _item_price(self, rid):
        """Возвращает базовую цену предмета (из ресурсов или модулей)."""
        info = RESOURCES.get(rid, {})
        if info: return info.get("base_price", 0)
        info = SHIP_MODULES.get(rid, {})
        if info: return info.get("cost", 0)
        return 0

    def _item_icon(self, rid):
        """Возвращает иконку для отображения категории предмета."""
        info = RESOURCES.get(rid, {})
        if info:
            return {"raw":"⛏","refined":"■","advanced":"◆","special":"★","consumable":"⚡"}.get(info.get("cat",""), "·")
        return "◈"

    def _filtered(self):
        """Возвращает отфильтрованный список предметов в трюме."""
        items = list(self.app.ship.cargo.items.items())
        if self._filter == "all": return items
        return [(r,a) for r,a in items if self._item_cat(r) == self._filter]

    def _at_station(self):
        """Проверяет, пристыкован ли игрок к станции, и возвращает её."""
        app = self.app
        return app.galaxy.get_station_at(app.player_x, app.player_y)

    def _refresh(self):
        app = self.app
        if not hasattr(app,"ship"): return
        s = app.ship; c = s.cargo
        cb = s.get_effective_stats().get("cargo_bonus", 0)
        items = self._filtered()
        items.sort(key=lambda x: (CATEGORY_ORDER.get(self._item_cat(x[0]), 99), self._item_name(x[0])))
        self._selected = min(self._selected, max(0, len(items)-1))
        st = self._at_station()

        # Header
        self.query_one("#cargo-header").update(
            "┌────────────────────────────────────────────────────────────────┐\n"
            f"│  CARGO HOLD: {c.used():>3}/{c.capacity+cb:<3} used  |  Value: {c.total_value():>5}cr  |  Credits: {s.credits}cr{'':>20}│\n"
            "└────────────────────────────────────────────────────────────────┘"
        )

        # Filters
        fnames = [("all","All"),("raw","Raw"),("refined","Refined"),
                  ("advanced","Adv"),("special","Special"),("module","Mods")]
        fline = "│  "
        for key,label in fnames:
            fline += f"[{label}] " if self._filter == key else f" {label}  "
        fline = fline.rstrip() + "            │"
        self.query_one("#cargo-filters").update(
            "┌────────────────────────────────────────────────────────────────┐\n" + fline + "\n└────────────────────────────────────────────────────────────────┘"
        )

        # Table
        lines = ["┌────────────────────────────────────────────────────────────────┐",
                 f"│ {'':>2} {'Item':<18} {'Category':<10} {'Qty':>4} {'Price':>7} {'Total':>7} │",
                 "├────────────────────────────────────────────────────────────────┤"]
        if not items:
            lines.append("│  (no items matching filter)                              │")
        else:
            for i,(rid,amt) in enumerate(items):
                sel = "▶" if i == self._selected else " "
                icon = self._item_icon(rid)
                name = self._item_name(rid)
                cat = self._item_cat(rid)
                cl = CATEGORY_LABELS.get(cat, SHIP_MODULES.get(rid,{}).get("comp","Mod") if cat=="module" else cat)
                price = self._item_price(rid)
                total = price*amt
                lines.append(f"│{sel}{icon} {name:<18} {cl:<10} {amt:>4} {price:>5}cr {total:>5}cr│")
        lines.append("└────────────────────────────────────────────────────────────────┘")
        self.query_one("#cargo-table").update("\n".join(lines))

        # Footer
        f = "┌────────────────────────────────────────────────────────────────┐\n"
        f += f"│  [Enter] Use Item  [Delete] Jettison"
        if st: f += "  [S] Sell Raw"
        f += f"{'':>24}│\n"
        f += "│  [1-6] Filter  [↑↓] Select{'':>38}│\n"
        f += "└────────────────────────────────────────────────────────────────┘"
        self.query_one("#cargo-footer").update(f)

    # -- actions --
    def _use_item(self):
        """Использует выбранный предмет: устанавливает модуль из груза или активирует расходник."""
        items = self._filtered()
        if not items or self._selected >= len(items): return
        rid,_ = items[self._selected]
        cat = self._item_cat(rid)
        if cat in ("raw","refined","advanced","special"):
            self.app.logger.system(f"'{rid}' is a resource — use at trade.")
            return
        s = self.app.ship
        if rid in SHIP_MODULES:
            msg,_ = s.install_module_from_cargo(rid)
        else:
            msg,_ = s.use_item(rid,1)
        self.app.logger.system(msg)
        self._refresh()

    def _jettison(self):
        """Выбрасывает 1 единицу выбранного предмета за борт."""
        items = self._filtered()
        if not items or self._selected >= len(items): return
        rid,amt = items[self._selected]
        qty = 1
        self.app.ship.cargo.remove(rid,qty)
        self.app.logger.system(f"Jettisoned {qty}x {rid}.")
        self._selected = min(self._selected, max(0,len(self._filtered())-1))
        self._refresh()

    def _sell_junk(self):
        """Продаёт всё сырьё (junk) станции, если игрок пристыкован."""
        st = self._at_station()
        if not st: self.app.logger.system("Not docked at a station."); return
        msg,_ = st.buy_all_junk(self.app.ship)
        self.app.logger.system(msg)
        self._refresh()

    # -- keys --
    def on_key(self, event):
        """Обрабатывает клавиши: Escape, стрелки, Enter, Delete, S, 1-6."""
        if event.key == "escape":
            event.stop(); self.app.dismiss_to_bridge(self); return
        items = self._filtered()
        if event.key == "up" and items:
            self._selected = (self._selected-1) % len(items); self._refresh()
        elif event.key == "down" and items:
            self._selected = (self._selected+1) % len(items); self._refresh()
        elif event.key == "enter":
            self._use_item()
        elif event.key == "delete":
            self._jettison()
        elif event.key in ("s","S"):
            self._sell_junk()
        elif event.key in "123456":
            fkeys = ["all","raw","refined","advanced","special","module"]
            idx = int(event.key)-1
            if idx < len(fkeys): self._filter = fkeys[idx]; self._selected = 0; self._refresh()

    def on_input_submitted(self, event):
        """Обрабатывает текстовый ввод (close/exit/quit для выхода, иначе заглушка поиска)."""
        v = event.value.strip().lower()
        if v in ("close","exit","quit"): event.stop(); self.dismiss(); return
        # Simple search: filter by keyword
        if v:
            self.app.logger.system(f"Search not implemented yet.")
        event.value = ""


# ═══════════════════════════════════════════════════════════════════════
# Trade screen
# ═══════════════════════════════════════════════════════════════════════

class TradeScreen(Screen):
    """Экран торговли на станции. Показывает цены покупки/продажи ресурсов и содержимое трюма."""

    def __init__(self, station):
        """Сохраняет ссылку на станцию для торговли."""
        super().__init__()
        self.station = station  # объект станции, с которой ведётся торговля

    def compose(self):
        """Создаёт виджеты заголовка, таблицы цен и поля ввода команд."""
        yield Static(id="trade-header")
        yield Static(id="trade-prices")
        yield Input(placeholder="buy <res> <amt>  |  sell <res> <amt>  |  close", id="trade-input")

    def on_mount(self):
        """Формирует и отображает таблицу цен на ресурсы и текущий груз игрока."""
        app = self.app
        if not hasattr(app, "ship"):
            return
        st = self.station
        s = app.ship

        self.query_one("#trade-header").update(
            f"┌─ TRADE ─ {st.name} [{st.faction}] ─ Cr:{s.credits} "
            f"Cargo:{s.cargo.used()}/{s.cargo.capacity} ─┐"
        )

        lines = [f"│ {'Resource':<14} {'Stock':>5} {'Buy':>6} {'Sell':>6} │"]
        lines.append("│" + "─" * 35 + "│")
        for rid in sorted(RESOURCES):
            name = RESOURCES[rid]["name"]
            stk = st.inventory.get(rid, 0)
            bp, _ = st.price_for_player(rid, True, s)
            sp, _ = st.price_for_player(rid, False, s)
            marker = ""
            if stk == 0:
                marker = " —"
            lines.append(f"│ {name:<14} {stk:>5}{marker} {bp:>5}cr {sp:>5}cr │")
        lines.append("│" + "─" * 35 + "│")
        lines.append("│ Your cargo:                           │")
        for rid, amt in sorted(s.cargo.items.items()):
            name = RESOURCES.get(rid, {}).get("name", rid)
            lines.append(f"│   {name:<12} x{amt:<3}                    │")
        if not s.cargo.items:
            lines.append("│   (empty)                              │")
        lines.append("└" + "─" * 35 + "┘")
        self.query_one("#trade-prices").update("\n".join(lines))

    def on_key(self, event):
        """Закрывает экран по Escape или Q."""
        if event.key in ("escape", "q"):
            event.stop(); self.dismiss()

    def on_input_submitted(self, event):
        """Обрабатывает команды buy/sell, добавляя префикс 'trade', иначе передаёт app.process_command()."""
        app = self.app
        if not hasattr(app, "process_command"):
            return
        v = event.value.strip().lower()
        if v in ("close", "exit", "quit"):
            self.dismiss(); return
        p = v.split()
        if p and p[0] in ("buy", "sell"):
            v = "trade " + v
        app.process_command(v)
        self.on_mount()


# ═══════════════════════════════════════════════════════════════════════
# Bridge (F1) — main ship management hub
# ═══════════════════════════════════════════════════════════════════════

def _bar(pct, width=10):
    """Draw a progress bar: [████░░░░]"""
    filled = int(pct / 100 * width)
    return f"[{'█' * filled}{'░' * (width - filled)}]"


class BridgeScreen(Screen):
    """Главный экран мостика (F1). Показывает состояние корабля и меню перехода к отсекам и функциям."""
    MENU_ITEMS = [
        ("1", "Engineering", "Power distribution & module management"),
        ("2", "Tactical", "Weapons & combat targets"),
        ("3", "Cargo", "Inventory & item management"),
        ("4", "Crew", "Crew roster & post assignment"),
        ("5", "Missions", "Active mission overview"),
        ("6", "Scanner", "Active scan of nearby objects"),
    ]

    def compose(self):
        """Создаёт виджеты верхней панели, меню и подвала."""
        yield Static(id="bridge-top")
        yield Static(id="bridge-menu")
        yield Static(id="bridge-footer")

    def on_mount(self):
        """При монтировании обновляет отображение мостика."""
        self._refresh()

    def _at_station(self):
        """Check if player is at a station."""
        app = self.app
        if not hasattr(app, "galaxy") or not hasattr(app, "ship"):
            return None
        return app.galaxy.get_station_at(app.player_x, app.player_y)

    def _refresh(self):
        """Обновляет панель состояния корабля (корпус, щиты, энергия, скорость, экипаж) и меню команд."""
        app = self.app
        if not hasattr(app, "ship") or not hasattr(app, "galaxy"):
            self.query_one("#bridge-top").update("No ship data.")
            return
        s = app.ship
        st = s.get_effective_stats()
        p_gen = s.total_power_generated()
        p_con = s.total_power_consumed()
        eff = 100 if p_con <= p_gen else max(30, int(p_gen / max(1, p_con) * 100))
        max_h = s.max_hull + st.get("hull_bonus", 0)
        crew_n = sum(1 for v in s.crew.values() if v)
        station = self._at_station()

        # ── Top status panel ──
        hp_pct = int(s.hull / max(1, max_h) * 100)
        sh_pct = int(s.shield_hp / max(1, st['shield_cap']) * 100) if st['shield_cap'] > 0 else 0
        top = [
            "┌" + "─" * 54 + "┐",
            f"│  {s.name:<20} {'CREDITS':>8}: {s.credits:<6}    │",
            f"│  HULL    {_bar(hp_pct, 15)} {s.hull:>4}/{max_h:<4}  │",
            f"│  SHIELDS {_bar(sh_pct, 15)} {s.shield_hp:>3}/{st['shield_cap']:<3}  │",
            f"│  POWER   {p_gen:>3} gen / {p_con:<3} used  ({eff}% eff)        │",
            f"│  FUEL    {s.fuel:<3}     CARGO {s.cargo.used()}/{s.cargo.capacity + st.get('cargo_bonus', 0)}   │",
            f"│  SPEED {st['speed']:>2}  EVASION {st['evasion']:>3}%  SENSORS +{st['sensor_range']:<2}  │",
            f"│  CREW {crew_n}/4 assigned      MISSIONS {len(s.missions)}        │",
            "└" + "─" * 54 + "┘",
        ]
        self.query_one("#bridge-top").update("\n".join(top))

        # ── Menu ──
        items = list(self.MENU_ITEMS)
        if station:
            items.append(("7", "Station Services", f"Dock at {station.name} [{station.stype}]"))
        menu = ["┌" + "─" * 54 + "┐", "│" + "  COMMANDS  ".center(52) + "│", "├" + "─" * 54 + "┤"]
        for key, name, desc in items:
            menu.append(f"│  [{key}] {name:<20}  {desc:<28}│")
        menu.append("├" + "─" * 54 + "┤")
        menu.append("│" + "  [Esc] Back to Galaxy        [↑↓/1-6] Select".center(52) + "│")
        menu.append("└" + "─" * 54 + "┘")
        self.query_one("#bridge-menu").update("\n".join(menu))

        self.query_one("#bridge-footer").update("")

    def on_key(self, event):
        """Обрабатывает клавиши: 1-7 для перехода к экранам, Escape для возврата на карту."""
        if event.key == "escape":
            event.stop(); self.dismiss()
            # Refresh game info panel on return
            if hasattr(self.app, "update_info"):
                self.app.update_info()
            return

        target = None
        if event.key == "1":
            target = EngineeringScreen
        elif event.key == "2":
            target = TacticalScreen
        elif event.key == "3":
            target = CargoScreen
        elif event.key == "4":
            target = CrewScreen
        elif event.key == "5":
            target = MissionsScreen
        elif event.key == "6":
            target = ScanScreen
        elif event.key == "7":
            station = self._at_station()
            if station:
                target = StationServicesScreen

        if target:
            event.stop()
            if target is ScanScreen:
                self.app.push_screen(ScanScreen())
            elif target in (StationServicesScreen, MissionListScreen):
                self.app.push_screen(target(station=self._at_station()))
            else:
                self.app.push_screen(target())


# ═══════════════════════════════════════════════════════════════════════
# Mission List (view from bridge)
# ═══════════════════════════════════════════════════════════════════════

class MissionListScreen(Screen):
    """Устаревший экран списка миссий — сохранён для совместимости. Используйте MissionsScreen."""

    def __init__(self, station=None):
        """Сохраняет ссылку на станцию (для обратной совместимости)."""
        super().__init__()
        self.station = station  # станция, с которой получены миссии

    def compose(self):
        """Создаёт виджет для отображения списка миссий."""
        yield Static(id="mlist-content")

    def on_mount(self):
        """Формирует и отображает список активных миссий."""
        app = self.app
        if not hasattr(app, "ship"):
            return
        s = app.ship
        lines = [
            "┌" + "─" * 58 + "┐",
            "│" + "ACTIVE MISSIONS".center(58) + "│",
            "├" + "─" * 58 + "┤",
        ]
        if s.missions:
            for m in s.missions:
                lines.append(f"│  {m.title[:30]:<30}  {m.ticks:>3}t  +{m.reward}cr  {m.status:<9}│")
        else:
            lines.append("│  (no active missions)                           │")
        lines.append("├" + "─" * 58 + "┤")
        lines.append("│" + "[Esc] Back to Bridge".center(58) + "│")
        lines.append("└" + "─" * 58 + "┘")
        self.query_one("#mlist-content").update("\n".join(lines))

    def on_key(self, event):
        """Закрывает экран по Escape."""
        if event.key == "escape":
            event.stop(); self.dismiss()


# ═══════════════════════════════════════════════════════════════════════
# Missions Screen (from bridge)
# ═══════════════════════════════════════════════════════════════════════

class MissionsScreen(Screen):
    """Экран журнала миссий. Показывает активные и доступные миссии с возможностью принятия, отслеживания и детального просмотра."""

    def __init__(self):
        """Инициализирует экран: вкладка «активные» и индекс выбранной миссии."""
        super().__init__()
        self._tab = "active"  # активные/доступные: "active" | "available"
        self._selected = 0  # индекс выбранной строки в списке

    def compose(self):
        """Создаёт виджеты содержимого миссий и поля ввода команд."""
        yield Static(id="msn-content")
        yield Input(placeholder="accept <num> | abandon <num> | track <num> | detail <num>  | close", id="msn-input")

    def on_mount(self):
        """При монтировании обновляет список миссий."""
        self._refresh()

    def _at_station(self):
        """Проверяет, пристыкован ли игрок к станции."""
        app = self.app
        return app.galaxy.get_station_at(app.player_x, app.player_y)

    def _refresh(self):
        """Формирует и отображает таблицу активных или доступных миссий с репутацией и выбором вкладки."""
        app = self.app
        if not hasattr(app, "ship"):
            return
        s = app.ship
        st = self._at_station()
        rep_line = "  ".join(f"{f}:{s.reputation.get(f,0)}" for f in sorted(s.reputation) if f != "pirates")
        lines = [
            "┌" + "─" * 62 + "┐",
            "│" + "MISSION LOG".center(62) + "│",
            f"│  Active: {len(s.missions)}/{s.MAX_MISSIONS}  |  {rep_line[:50]}│",
            "├" + "─" * 62 + "┤",
        ]

        # Tabs
        tab_act = "[Active]" if self._tab == "active" else " Active "
        tab_avl = "[Available]" if self._tab == "available" else " Available"
        lines.append(f"│  {tab_act}  |  {tab_avl}" + " " * 26 + "│")

        if self._tab == "active":
            lines.append("├" + "─" * 62 + "┤")
            lines.append(f"│ {'ID':>3} {'Title':<30} {'Turns':>5} {'Reward':>6} {'Status':<10}│")
            lines.append("├" + "─" * 62 + "┤")
            if s.missions:
                for i, m in enumerate(s.missions):
                    sel = "▶" if i == self._selected else " "
                    t = m.title[:28]
                    sts = "✓" if m.status == "completed" else "✗" if m.status == "failed" else "●"
                    lines.append(f"│{sel}{m.id:>3} {t:<30} {m.ticks:>5} {m.reward:>5}cr {sts:<10}│")
            else:
                lines.append("│  (no active missions — visit a station)            │")
        else:
            lines.append("├" + "─" * 62 + "┤")
            lines.append(f"│ {'ID':>3} {'Title':<30} {'Turns':>5} {'Reward':>6} {'Giver':<12}│")
            lines.append("├" + "─" * 62 + "┤")
            if st and st.missions:
                for i, m in enumerate(st.missions):
                    sel = "▶" if i == self._selected else " "
                    lines.append(f"│{sel}{m.id:>3} {m.title[:28]:<30} {m.ticks:>5} {m.reward:>5}cr {st.name[:10]:<12}│")
            elif not st:
                lines.append("│  (not docked at a station)                        │")
            else:
                lines.append("│  (no missions available here)                    │")

        lines.append("├" + "─" * 62 + "┤")

        # Actions
        if self._tab == "active":
            lines.append("│  [Enter] Track    [A] Abandon    [D] Details         │")
        else:
            lines.append("│  [Enter] Accept   [D] Details                        │")
        lines.append("│  [1] Active missions  [2] Available missions           │")
        lines.append("├" + "─" * 62 + "┤")
        lines.append("│" + "[Esc] Back to Bridge".center(62) + "│")
        lines.append("└" + "─" * 62 + "┘")

        self.query_one("#msn-content").update("\n".join(lines))

    def _selected_mission(self):
        """Get the current mission list (active or available) and selected item."""
        s = self.app.ship
        if self._tab == "active":
            lst = s.missions
        else:
            st = self._at_station()
            lst = st.missions if st else []
        if not lst or self._selected >= len(lst):
            return None, None
        return lst[self._selected], lst

    def on_key(self, event):
        """Обрабатывает клавиши: 1-2 для вкладок, Enter/стрелки, A-отмена, D-детали, Escape-выход."""
        if event.key == "escape":
            event.stop(); self.app.dismiss_to_bridge(self); return
        app = self.app; s = app.ship

        if event.key == "1":
            self._tab = "active"; self._selected = 0; self._refresh()
        elif event.key == "2":
            self._tab = "available"; self._selected = 0; self._refresh()
        elif event.key == "up":
            lst = s.missions if self._tab == "active" else (self._at_station().missions if self._at_station() else [])
            if lst:
                self._selected = (self._selected - 1) % len(lst); self._refresh()
        elif event.key == "down":
            lst = s.missions if self._tab == "active" else (self._at_station().missions if self._at_station() else [])
            if lst:
                self._selected = (self._selected + 1) % len(lst); self._refresh()
        elif event.key == "enter":
            m, lst = self._selected_mission()
            if not m:
                return
            if self._tab == "available":
                st = self._at_station()
                if st and m in st.missions:
                    msg, ok = s.add_mission(m)
                    if ok: st.missions.remove(m)
                    app.logger.system(msg)
                    self._selected = min(self._selected, max(0, len(st.missions) - 1))
            else:
                s.track_mission(m.id)
                app.logger.system(f"Tracking: {m.title[:30]}")
            self._refresh()
        elif event.key in ("a", "A") and self._tab == "active":
            m, _ = self._selected_mission()
            if m:
                msg, _ = s.abandon_mission(m.id)
                app.logger.system(msg)
                self._selected = min(self._selected, max(0, len(s.missions) - 1))
                self._refresh()
        elif event.key in ("d", "D"):
            m, _ = self._selected_mission()
            if m:
                app.logger.system(f"{m.title}")
                app.logger.system(f"  {m.description}")
                app.logger.system(f"  Status: {m.status}  TTL: {m.ticks}t  Reward: {m.reward}cr")

    def on_input_submitted(self, event):
        """Обрабатывает текстовые команды: accept, abandon, track, detail, close."""
        app = self.app; s = app.ship
        v = event.value.strip().lower()
        if v in ("close", "exit", "quit"):
            event.stop(); self.dismiss(); return
        p = v.split()
        if not p:
            return
        if p[0] == "accept" and len(p) >= 2:
            try:
                idx = int(p[1]) - 1
                st = self._at_station()
                if st and 0 <= idx < len(st.missions):
                    m = st.missions[idx]
                    msg, ok = s.add_mission(m)
                    if ok: st.missions.remove(m)
                    app.logger.system(msg)
            except ValueError:
                pass
        elif p[0] == "abandon" and len(p) >= 2:
            try:
                mid = int(p[1])
                msg, _ = s.abandon_mission(mid)
                app.logger.system(msg)
            except ValueError:
                pass
        elif p[0] == "track" and len(p) >= 2:
            try:
                mid = int(p[1])
                m = s.track_mission(mid)
                if m:
                    app.logger.system(f"Tracking: {m.title}")
                else:
                    app.logger.system("Mission not found.")
            except ValueError:
                pass
        elif p[0] == "detail" and len(p) >= 2:
            try:
                mid = int(p[1])
                for m in s.missions:
                    if m.id == mid:
                        app.logger.system(f"{m.title}")
                        app.logger.system(f"  {m.description}")
                        app.logger.system(f"  Status: {m.status}  TTL: {m.ticks}t  Reward: {m.reward}cr")
            except ValueError:
                pass
        self._refresh()


# ═══════════════════════════════════════════════════════════════════════
# Station Services (bridge -> services)
# ═══════════════════════════════════════════════════════════════════════

class StationServicesScreen(Screen):
    """Экран услуг станции. Показывает меню доступных действий: торговля, модули, верфь, мастерская, найм, миссии."""

    def __init__(self, station=None):
        """Сохраняет ссылку на станцию."""
        super().__init__()
        self.station = station  # объект станции

    def compose(self):
        """Создаёт виджеты содержимого и подвала."""
        yield Static(id="svc-content")
        yield Static(id="svc-footer")

    def on_mount(self):
        """Формирует меню услуг в зависимости от типа станции."""
        app = self.app
        st = self.station
        if not st:
            self.query_one("#svc-content").update("Not at a station.")
            return
        s = app.ship
        lines = [
            f"┌─ STATION SERVICES ─ {st.name} [{st.faction}] ─ Cr:{s.credits} ──┐",
            "│                                              │",
            "│  [1] Trade — buy/sell resources              │",
        ]
        if st.modules_for_sale:
            lines.append(f"│  [2] Modules — {len(st.modules_for_sale)} available{'':>24}│")
        if st.stype == "shipyard":
            lines.append(f"│  [3] Shipyard — hulls & upgrades{'':>26}│")
        if st.stype == "workshop":
            lines.append(f"│  [4] Workshop — crafting{'':>35}│")
        if st.stype == "tavern":
            lines.append(f"│  [5] Tavern — hire crew{'':>34}│")
        if st.missions:
            lines.append(f"│  [6] Missions — {len(st.missions)} contracts{'':>29}│")
        lines.append("│                                              │")
        lines.append("│  [Esc] Back to Bridge                        │")
        lines.append("└──────────────────────────────────────────────┘")
        self.query_one("#svc-content").update("\n".join(lines))
        self.query_one("#svc-footer").update("")

    def on_key(self, event):
        """Обрабатывает клавиши: 1-6 для выбора услуги, Escape для возврата."""
        st = self.station
        app = self.app
        if event.key == "escape":
            event.stop(); self.app.dismiss_to_bridge(self); return
        if event.key == "1":
            if st: app.push_screen(TradeScreen(st))
        elif event.key == "2" and st and st.modules_for_sale:
            app.push_screen(ModuleShopScreen(st))
        elif event.key == "3" and st and st.stype == "shipyard":
            app.push_screen(ShipyardScreen(st))
        elif event.key == "4" and st and st.stype == "workshop":
            app.push_screen(CraftingScreen(st))
        elif event.key == "5" and st and st.stype == "tavern":
            app.push_screen(HireScreen(st))
        elif event.key == "6" and st and st.missions:
            app.push_screen(MissionScreen(st))
        event.stop()


# ═══════════════════════════════════════════════════════════════════════
# Engineering (from bridge)
# ═══════════════════════════════════════════════════════════════════════

class EngineeringScreen(Screen):
    """Экран инженерного отсека. Показывает распределение энергии по отсекам, состояние и уровень модулей."""

    def __init__(self):
        """Инициализирует экран: выбранный отсек — None (не выбран)."""
        super().__init__()
        self._selected_comp = None  # идентификатор выбранного отсека (например, "weapon")

    def compose(self):
        """Создаёт виджет содержимого и поле ввода команд."""
        yield Static(id="eng-content")
        yield Input(placeholder="power <comp> <0-10>  |  repair <comp>  |  upgrade <num>  |  close", id="eng-input")

    def on_mount(self):
        """При монтировании обновляет инженерную панель."""
        self._refresh()

    def _refresh(self):
        """Формирует и отображает таблицу отсеков с энергией, модулями и их прочностью."""
        app = self.app
        if not hasattr(app, "ship"):
            return
        s = app.ship
        p_gen = s.total_power_generated()
        p_con = s.total_power_consumed()
        eff = 100 if p_con <= p_gen else max(30, int(p_gen / max(1, p_con) * 100))
        crew_eng_bonus = s._crew_bonus("power_bonus", 0)

        lines = [
            "┌" + "─" * 56 + "┐",
            "│" + "ENGINEERING".center(56) + "│",
            "├" + "─" * 56 + "┤",
            f"│  Reactor: {p_gen} gen  │  Load: {p_con} used  ({eff}% eff)"
            f"{'  Crew +' + str(crew_eng_bonus) + '%' if crew_eng_bonus else ''}{'':>8}│",
            "├" + "─" * 56 + "┤",
        ]

        for i, c in enumerate(COMPARTMENTS, 1):
            mods = s.compartments[c]["modules"]
            pw = s.compartments[c]["power"]
            pbar = _bar(pw * 10, 10)
            energy = sum(m.energy_consumption for m in mods if m.active and not m.is_broken())
            sel = "▸" if self._selected_comp == c else " "
            lines.append(f"│{sel}{i}. {c:<14} power:{pw:>2} {pbar}  ⚡{energy:<3}     │")

            if not mods:
                lines.append(f"│     (empty{'':>48}│")
            else:
                for m in mods:
                    dur_pct = int(m.durability / max(1, m.max_durability) * 100)
                    dbar = _bar(dur_pct, 6)
                    sts = "☠" if m.is_broken() else "✓"
                    lvl = f"Lv{m.level}" if m.level > 1 else "   "
                    lines.append(
                        f"│     {sts} {m.name:<18} {lvl} {dbar} "
                        f"{m.durability:>3}/{m.max_durability:<3} "
                        f"{'⚡'+str(m.energy_consumption) if m.energy_consumption else '   '}  │"
                    )

        lines.append("├" + "─" * 56 + "┤")

        # Help
        lines.append("│  [1-7] select compartment  [0-9] set power          │")
        lines.append("│  repair <comp> — fix modules  upgrade <num> — Lv up│")
        lines.append("├" + "─" * 56 + "┤")
        lines.append("│" + "[Esc] Back to Bridge".center(56) + "│")
        lines.append("└" + "─" * 56 + "┘")
        self.query_one("#eng-content").update("\n".join(lines))

    def on_key(self, event):
        """Обрабатывает клавиши: 1-7 для выбора отсека, 0-9 для установки энергии, Escape для выхода."""
        if event.key == "escape":
            event.stop(); self.app.dismiss_to_bridge(self); return

        # 1-7 select compartment, 0-9 set power for selected
        if event.key in "1234567":
            idx = int(event.key) - 1
            if idx < len(COMPARTMENTS):
                self._selected_comp = COMPARTMENTS[idx]
                self._refresh()
            return
        if event.key in "089" and self._selected_comp:
            val = int(event.key)
            self.app.ship.compartments[self._selected_comp]["power"] = val
            self._refresh()
            return

    def on_input_submitted(self, event):
        """Обрабатывает текстовые команды: power, repair, upgrade, close."""
        app = self.app
        if not hasattr(app, "process_command"):
            return
        v = event.value.strip().lower()
        if v in ("close", "exit"):
            event.stop(); self.dismiss(); return
        app.process_command(v)
        self._refresh()


# ═══════════════════════════════════════════════════════════════════════
# Tactical (from bridge)
# ═══════════════════════════════════════════════════════════════════════

class TacticalScreen(Screen):
    """Экран тактического отсека. Показывает оружие, цели в радиусе сенсоров, позволяет инициировать бой."""

    def __init__(self):
        """Инициализирует экран: активная панель «оружие», индексы выбранного оружия и цели."""
        super().__init__()
        self._active_panel = "weapons"  # активная панель: "weapons" | "targets"
        self._sel_weapon = 0  # индекс выбранного оружия
        self._sel_target = 0  # индекс выбранной цели

    def compose(self):
        """Создаёт виджет тактического содержимого."""
        yield Static(id="tac-content")

    def on_mount(self):
        """При монтировании обновляет тактическую панель."""
        self._refresh()

    def _get_weapons(self):
        """Возвращает список активных и не сломанных модулей оружия."""
        return [m for m in self.app.ship.compartments["weapon"]["modules"]
                if m.active and not m.is_broken()]

    def _get_targets(self):
        """Возвращает список целей (пираты и торговцы) в радиусе сенсоров, отсортированных по дистанции."""
        app = self.app
        g = app.galaxy
        rng = app.ship.get_effective_stats().get("sensor_range", 7)
        targets = []
        px, py = app.player_x, app.player_y
        for p in g.pirates:
            if p.alive:
                d = max(abs(p.x - px), abs(p.y - py))
                if d <= rng:
                    hpct = int(p.hull / max(1, p.max_hull) * 100)
                    targets.append((d, p, "☠ Pirate", "Hostile", hpct, getattr(p, 'shield_hp', 0)))
        for t in g.traders:
            if t.alive:
                d = max(abs(t.x - px), abs(t.y - py))
                if d <= rng:
                    hpct = int(t.hull / max(1, t.max_hull) * 100)
                    targets.append((d, t, "T Trader", "Neutral", hpct, getattr(t, 'shield_hp', 0)))
        targets.sort(key=lambda x: x[0])
        return targets

    def _refresh(self):
        """Формирует и отображает панели оружия и целей с состоянием корпуса и щитов."""
        app = self.app
        if not hasattr(app, "ship"):
            return
        s = app.ship
        stats = s.get_effective_stats()
        weapons = self._get_weapons()
        targets = self._get_targets()

        # Ensure selection indices are valid
        self._sel_weapon = min(self._sel_weapon, max(0, len(weapons) - 1))
        self._sel_target = min(self._sel_target, max(0, len(targets) - 1))

        # Clamp selected indices
        panels = {"weapons": self._sel_weapon, "targets": self._sel_target}

        # ── Top status bar ──
        hull_pct = int(s.hull / max(1, s.max_hull) * 100)
        sh_pct = int(s.shield_hp / max(1, stats['shield_cap']) * 100) if stats['shield_cap'] > 0 else 0
        hbar = _bar(hull_pct, 10)
        shbar = _bar(sh_pct, 10)
        alarms = ""
        if hull_pct < 30:
            alarms = "  ⚠ HULL CRITICAL"
        elif hull_pct < 60:
            alarms = "  ⚡ Hull damaged"

        lines = [
            "┌" + "─" * 56 + "┐",
            "│" + "TACTICAL".center(56) + "│",
            "├" + "─" * 56 + "┤",
            f"│  HULL    {hbar}  {s.hull:>3}/{s.max_hull:<3}     │",
            f"│  SHIELDS {shbar}  {s.shield_hp:>3}/{stats['shield_cap']:<3}{alarms:<20}│",
            "├" + "─" * 56 + "┤",
            # ── Weapons panel ──
            f"│  {'═' * 25} WEAPONS {'═' * 21}│",
        ]

        if not weapons:
            lines.append("│  No weapons installed.                        │")
        else:
            for i, w in enumerate(weapons):
                dp = w.stats.get('damage', 0)
                ac = w.stats.get('accuracy', 0)
                ec = w.energy_consumption
                dur_pct = int(w.durability / max(1, w.max_durability) * 100)
                active = "▶" if i == self._sel_weapon and self._active_panel == "weapons" else " "
                selected = "*ACTIVE*" if i == self._sel_weapon else "         "
                lines.append(
                    f"│{active}{i+1}. {w.name:<14} Lv{w.level}  "
                    f"⚔{dp:>3} 🎯{ac:>2}% ⚡{ec}  {_bar(dur_pct, 5)} {selected}│"
                )

        # ── Targets panel ──
        lines.append(f"│  {'═' * 25} TARGETS {'═' * 21}│")
        if not targets:
            lines.append("│  No targets in sensor range.                  │")
        else:
            for i, (d, npc, label, status, hpct, sh) in enumerate(targets):
                sel = "▶" if i == self._sel_target and self._active_panel == "targets" else " "
                st_icon = "☠" if status == "Hostile" else "☮" if status == "Neutral" else "?"
                lines.append(
                    f"│{sel}{i+1}. {label:<12} "
                    f"H:{_bar(hpct, 6)} {npc.hull:>3}/{npc.max_hull:<3} "
                    f"{'🛡'+str(sh) if sh else '   '} d:{d} {st_icon}│"
                )

        # ── Stats line ──
        lines.append("├" + "─" * 56 + "┤")
        lines.append(
            f"│  Effective: ⚔{stats['damage']} dmg  🎯{stats['accuracy']}%  "
            f"📡 +{stats['sensor_range']} range          │"
        )

        # ── Action footer ──
        can_engage = weapons and targets
        lines.append("├" + "─" * 56 + "┤")
        lines.append(
            f"│  [Enter] {'Engage' if can_engage else '(Engage — select weapon & target)'}"
            f"{'':<20}│"
        )
        lines.append(
            f"│  {'[F] Fire at Will (auto)':<30}"
            f"{'[Tab] Switch panel':<25}│"
        )
        lines.append("├" + "─" * 56 + "┤")
        lines.append(
            f"│  [↑↓] Navigate  [Tab] Weapons/Targets  [Enter] Battle"
            f"{'':<10}│"
        )
        lines.append("│" + "[Esc] Back to Bridge".center(56) + "│")
        lines.append("└" + "─" * 56 + "┘")

        self.query_one("#tac-content").update("\n".join(lines))

    def on_key(self, event):
        """Обрабатывает клавиши: стрелки для навигации, Tab для переключения панели, Enter/F для атаки, Escape для выхода."""
        if event.key == "escape":
            event.stop(); self.app.dismiss_to_bridge(self); return

        weapons = self._get_weapons()
        targets = self._get_targets()

        if event.key == "up":
            if self._active_panel == "weapons" and weapons:
                self._sel_weapon = (self._sel_weapon - 1) % len(weapons)
            elif self._active_panel == "targets" and targets:
                self._sel_target = (self._sel_target - 1) % len(targets)
            self._refresh()
        elif event.key == "down":
            if self._active_panel == "weapons" and weapons:
                self._sel_weapon = (self._sel_weapon + 1) % len(weapons)
            elif self._active_panel == "targets" and targets:
                self._sel_target = (self._sel_target + 1) % len(targets)
            self._refresh()
        elif event.key == "tab":
            self._active_panel = "targets" if self._active_panel == "weapons" else "weapons"
            self._refresh()
        elif event.key in ("f", "F"):
            # Fire at Will: auto-target nearest hostile
            hostiles = [(d, npc) for d, npc, _, st, _, _ in targets
                        if st == "Hostile"]
            if weapons and hostiles:
                _, target = hostiles[0]
                self._start_battle(target)
        elif event.key == "enter":
            # Engage: selected weapon × selected target
            sel_w = self._sel_weapon if self._active_panel == "weapons" else self._sel_target
            if weapons and targets:
                if self._active_panel == "weapons":
                    tgt = targets[self._sel_target][1] if targets else None
                else:
                    tgt = targets[self._sel_target][1]
                if tgt:
                    self._start_battle(tgt)

    def _start_battle(self, target_npc):
        """Запускает экран боя (BattleScreen) для указанной цели."""
        app = self.app
        from battle import BattleController, BattleScreen
        bc = BattleController(app.ship, target_npc, app, selected_weapon_idx=self._sel_weapon)
        app.push_screen(BattleScreen(bc))
        self.dismiss()


# ═══════════════════════════════════════════════════════════════════════
# Module Shop
# ═══════════════════════════════════════════════════════════════════════

class ModuleShopScreen(Screen):
    """Экран магазина модулей на станции. Показывает доступные для покупки и уже установленные модули."""

    def __init__(self, station):
        """Сохраняет ссылку на станцию."""
        super().__init__()
        self.station = station  # объект станции

    def compose(self):
        """Создаёт виджет содержимого и поле ввода команд."""
        yield Static(id="shop-content")
        yield Input(placeholder="buy <num>  |  close", id="shop-input")

    def on_mount(self):
        """Формирует список доступных и установленных модулей."""
        app = self.app
        st = self.station
        s = app.ship

        lines = [
            f"┌─ MODULE SHOP ─ {st.name} [{st.faction}] ─ Cr:{s.credits} ──────┐",
            f"│                                              │",
            f"│  ══ FOR SALE ══                              │",
        ]
        for i, mid in enumerate(st.modules_for_sale, 1):
            info = SHIP_MODULES.get(mid, {})
            desc = info.get("desc", "")
            lines.append(
                f"│  [{i}] {info.get('name', mid):<18} "
                f"{info.get('comp','?'):<12} "
                f"{info.get('cost',0):>5}cr  "
                f"⚡{info.get('energy',0)}  "
            )
            if desc:
                lines.append(f"│      {desc[:44]}")
        if not st.modules_for_sale:
            lines.append("│  (sold out)                                   │")
        lines.append(f"│                                              │")
        lines.append(f"│  ══ INSTALLED ══                              │")

        for c in COMPARTMENTS:
            for m in s.compartments[c]["modules"]:
                sts = "✗" if m.is_broken() else "✓"
                lines.append(f"│  [{sts}] {m.name:<18} {c:<12}                │")
        lines.append("└──────────────────────────────────────────────┘")
        self.query_one("#shop-content").update("\n".join(lines))

    def on_key(self, event):
        """Закрывает экран по Escape или Q."""
        if event.key in ("escape", "q"):
            event.stop(); self.dismiss()

    def on_input_submitted(self, event):
        """Обрабатывает команду buy <num> или передаёт ввод в process_command()."""
        app = self.app
        st = self.station
        s = app.ship
        v = event.value.strip().lower()
        if v in ("close", "exit", "quit"):
            self.dismiss(); return
        parts = v.split()
        if parts and parts[0] == "buy" and len(parts) >= 2:
            try:
                idx = int(parts[1]) - 1
            except ValueError:
                return
            if 0 <= idx < len(st.modules_for_sale):
                mid = st.modules_for_sale[idx]
                info = SHIP_MODULES.get(mid, {})
                cost = info.get("cost", 0)
                if s.credits < cost:
                    app.logger.system(f"Need {cost}cr, have {s.credits}cr.")
                elif s.install_module(mid):
                    s.credits -= cost
                    st.modules_for_sale.pop(idx)
                    app.logger.system(
                        f"Installed {info.get('name', mid)} for {cost}cr!")
                else:
                    app.logger.system(f"Can't install {mid}.")
                self.dismiss()
        else:
            app.process_command(v)
            self.dismiss()


# ═══════════════════════════════════════════════════════════════════════
# Missions
# ═══════════════════════════════════════════════════════════════════════

class MissionScreen(Screen):
    """Экран списка миссий на станции. Показывает доступные контракты и уже взятые миссии."""

    def __init__(self, station):
        """Сохраняет ссылку на станцию."""
        super().__init__()
        self.station = station  # объект станции

    def compose(self):
        """Создаёт виджет содержимого и поле ввода."""
        yield Static(id="missions-content")
        yield Input(placeholder="accept <num>  |  close", id="missions-input")

    def on_mount(self):
        """Формирует список доступных и активных миссий."""
        app = self.app
        st = self.station
        s = app.ship

        lines = [
            f"┌─ MISSIONS ─ {st.name} [{st.faction}] ────────────┐",
            f"│                                              │",
            f"│  ══ AVAILABLE ══                              │",
        ]
        for i, m in enumerate(st.missions, 1):
            name = RESOURCES.get(m.resource, {}).get("name", m.resource)
            lines.append(
                f"│  [{i}] Deliver {m.amount}x {name:<12} → {m.target_station:<10}  │"
            )
            lines.append(
                f"│      Reward: {m.reward:>5}cr  │  {m.ticks} ticks              │"
            )
        if not st.missions:
            lines.append("│  (no contracts available)                     │")
        lines.append(f"│                                              │")
        lines.append(f"│  ══ YOUR MISSIONS ══                           │")
        if s.missions:
            for m in s.missions:
                name = RESOURCES.get(m.resource, {}).get("name", m.resource)
                lines.append(
                    f"│  → {m.amount}x {name:<12} to {m.target_station:<10} +{m.reward}cr   │"
                )
        else:
            lines.append("│  (none)                                       │")
        lines.append("└──────────────────────────────────────────────┘")
        self.query_one("#missions-content").update("\n".join(lines))

    def on_key(self, event):
        """Закрывает экран по Escape или Q."""
        if event.key in ("escape", "q"):
            event.stop(); self.dismiss()

    def on_input_submitted(self, event):
        """Обрабатывает команду accept <num> или передаёт ввод в process_command()."""
        app = self.app
        st = self.station
        s = app.ship
        v = event.value.strip().lower()
        if v in ("close", "exit", "quit"):
            self.dismiss(); return
        parts = v.split()
        if parts and parts[0] == "accept" and len(parts) >= 2:
            try:
                idx = int(parts[1]) - 1
            except ValueError:
                return
            if 0 <= idx < len(st.missions):
                m = st.missions.pop(idx)
                if len(s.missions) < 5:
                    s.missions.append(m)
                    name = RESOURCES.get(m.resource, {}).get("name", m.resource)
                    app.logger.system(
                        f"Mission: {m.amount}x {name} → {m.target_station} +{m.reward}cr"
                    )
                else:
                    app.logger.system("Mission log full (max 5).")
                self.dismiss()
        else:
            app.process_command(v)
            self.dismiss()


# ═══════════════════════════════════════════════════════════════════════
# Crew (F5)
# ═══════════════════════════════════════════════════════════════════════

class CrewScreen(Screen):
    """Экран экипажа. Показывает назначенные посты и информацию о бонусах специальностей."""

    def compose(self):
        """Создаёт виджеты содержимого и поля ввода команд."""
        yield Static(id="crew-content")
        yield Input(placeholder="assign <name> <post>  |  close", id="crew-input")

    def on_mount(self):
        """Формирует список постов экипажа и описание бонусов."""
        app = self.app
        if not hasattr(app, "ship"):
            return
        s = app.ship

        lines = [
            f"┌─ CREW ─ {s.name} ────────────────────────────┐",
            f"│                                              │",
            f"│  ══ POSTS ══                                  │",
        ]
        icons = {"Pilot": "✦", "Engineer": "⚙", "Tactical": "⚔", "Scientist": "🔬"}
        for post, member in s.crew.items():
            icon = icons.get(post, "?")
            name = member if member else "(vacant)"
            lines.append(f"│  {icon} {post:<12} → {name:<20}     │")
        lines.append(f"│                                              │")
        lines.append(f"│  ══ INFO ══                                   │")
        lines.append(f"│  Assign crew to posts for bonuses:            │")
        lines.append(f"│  Pilot → +evasion   Engineer → +power         │")
        lines.append(f"│  Tactical → +dmg    Scientist → +sensors      │")
        lines.append(f"│  Hire crew members at stations.               │")
        lines.append("└──────────────────────────────────────────────┘")
        self.query_one("#crew-content").update("\n".join(lines))

    def on_key(self, event):
        """Обрабатывает Escape для выхода, F1 для перехода на мостик."""
        if event.key == "escape":
            event.stop(); self.dismiss()
        elif event.key in ("f1", "F1"):
            self.dismiss()
            if hasattr(self.app, "push_screen"):
                self.app.push_screen(BridgeScreen())

    def on_input_submitted(self, event):
        """Обрабатывает assign <name> <post> или close."""
        app = self.app
        if not hasattr(app, "process_command"):
            return
        v = event.value.strip().lower()
        if v in ("close", "exit"):
            self.dismiss(); return
        app.process_command(v)
        self.on_mount()


# ═══════════════════════════════════════════════════════════════════════
# Shipyard (hulls, modules, upgrades)
# ═══════════════════════════════════════════════════════════════════════

class ShipyardScreen(Screen):
    """Экран верфи. Позволяет просматривать и покупать корпуса, модули и улучшения."""

    def __init__(self, station):
        """Сохраняет ссылку на станцию и устанавливает вкладку «корпуса»."""
        super().__init__(); self.station = station; self.tab = "hulls"  # активная вкладка: hulls/modules/upgrades
    def compose(self):
        """Создаёт виджет содержимого и поле ввода команд."""
        yield Static(id="yard-content"); yield Input(placeholder="buy/sell <id>  |  (h)ulls (m)odules (u)pgrades  | close", id="yard-input")
    def on_mount(self): self._refresh()
    def _refresh(self):
        """Обновляет отображение вкладки верфи (корпуса/модули/улучшения)."""
        app = self.app; st = self.station; s = app.ship
        lines = [f"┌─ SHIPYARD ─ {st.name} [{st.faction}] ─ Cr:{s.credits} ──────┐", "│                                              │", "│  ══ TABS: (H)ulls  (M)odules  (U)pgrades ══  │", "│                                              │"]
        if self.tab == "hulls":
            lines.append("│  ── HULLS FOR SALE ──                           │")
            for i, hid in enumerate(st.hulls_for_sale, 1):
                c = SHIP_HULLS.get(hid, {}); own = "✓" if hid in s.owned_hulls else ""; cur = "→" if hid == s.hull_id else ""
                lines.append(f"│  [{i}] {c.get('name', hid):<14} H:{c.get('hull',0):>3} C:{c.get('cargo',0):>3} S:{c.get('speed',0)} {c.get('cost',0):>5}cr {own}{cur}    │")
                lines.append(f"│      {c.get('desc', '')[:46]}")
            lines.append("│  ── OWNED HULLS ──                             │")
            for hid in s.owned_hulls:
                c = SHIP_HULLS.get(hid, {}); cur = " ◀ CURRENT" if hid == s.hull_id else ""
                lines.append(f"│  {c.get('name', hid):<16}{cur:<30}│")
            lines.append("│  sell <hid> / switch <hid> / buy <num>        │")
        elif self.tab == "modules":
            lines.append("│  ── MODULES FOR SALE ──                         │")
            for i, mid in enumerate(st.modules_for_sale, 1):
                info = SHIP_MODULES.get(mid, {}); d2 = info.get("desc", "")
                lines.append(f"│  [{i}] {info.get('name', mid):<18} {info.get('comp','?'):<12} {info.get('cost',0):>5}cr  ⚡{info.get('energy',0)}  │")
                if d2: lines.append(f"│      {d2[:44]}")
            if not st.modules_for_sale: lines.append("│  (sold out)                                   │")
            lines.append("│  buy mod <num>                                  │")
        elif self.tab == "upgrades":
            lines.append("│  ── HULL UPGRADES ──                            │")
            for uid, c in UPGRADES.items():
                done = "✓" if s.has_upgrade(uid) else " "; inp = " ".join(f"{a}{r[0]}" for r, a in c.get("inputs", {}).items())
                lines.append(f"│  {done} {c.get('name', uid):<20} {c.get('cost',0):>5}cr  {inp:<12}   │")
                lines.append(f"│      {c.get('desc', '')[:46]}")
            lines.append("│  upgrade <id>                                   │")
        lines.append("└──────────────────────────────────────────────┘")
        self.query_one("#yard-content").update("\n".join(lines))
    def on_key(self, event):
        """Обрабатывает клавиши: H/M/U для вкладок, Escape для выхода."""
        if event.key in ("escape", "q"): event.stop(); self.dismiss()
        elif event.key in ("h","H"): self.tab = "hulls"; self._refresh()
        elif event.key in ("m","M"): self.tab = "modules"; self._refresh()
        elif event.key in ("u","U"): self.tab = "upgrades"; self._refresh()
    def on_input_submitted(self, event):
        """Обрабатывает команды: buy, sell, switch, upgrade, close."""
        app = self.app; st = self.station; s = app.ship; v = event.value.strip().lower()
        if v in ("close","exit","quit"): self.dismiss(); return
        p = v.split()
        if not p: return
        if p[0] == "sell" and len(p) >= 2: msg, ok = s.sell_hull(p[1]); app.logger.system(msg)
        elif p[0] == "switch" and len(p) >= 2: msg, ok = s.switch_hull(p[1]); app.logger.system(msg)
        elif p[0] == "buy":
            if len(p) >= 2:
                try:
                    idx = int(p[1]) - 1
                    if self.tab == "hulls" and 0 <= idx < len(st.hulls_for_sale):
                        hid = st.hulls_for_sale[idx]; msg, ok = s.buy_hull(hid)
                        if ok: st.hulls_for_sale.pop(idx); app.logger.system(msg)
                except ValueError: pass
            if len(p) >= 3 and p[1] == "mod":
                try:
                    idx = int(p[2]) - 1
                    if 0 <= idx < len(st.modules_for_sale):
                        mid = st.modules_for_sale[idx]; info = SHIP_MODULES.get(mid, {}); cost = info.get("cost", 0)
                        if s.credits < cost: app.logger.system(f"Need {cost}cr, have {s.credits}cr.")
                        elif s.install_module(mid): s.credits -= cost; st.modules_for_sale.pop(idx); app.logger.system(f"Installed {info.get('name', mid)} for {cost}cr!")
                        else: app.logger.system(f"Can't install {mid}.")
                except ValueError: pass
        elif p[0] == "upgrade" and len(p) >= 2: msg, ok = s.apply_upgrade(p[1]); app.logger.system(msg)
        else: app.process_command(v)
        self._refresh()


# ═══════════════════════════════════════════════════════════════════════
# Crafting (workshop)
# ═══════════════════════════════════════════════════════════════════════

class CraftingScreen(Screen):
    """Экран мастерской. Показывает доступные рецепты крафта и содержимое трюма."""

    def __init__(self, station):
        """Сохраняет ссылку на станцию."""
        super().__init__(); self.station = station  # объект станции
    def compose(self):
        """Создаёт виджеты содержимого и поля ввода команд."""
        yield Static(id="craft-content"); yield Input(placeholder="craft <num> <item>  |  close", id="craft-input")
    def on_mount(self):
        """Формирует список рецептов и текущий груз."""
        app = self.app; st = self.station; s = app.ship
        lines = [f"┌─ WORKSHOP ─ {st.name} [{st.faction}] ─ Cr:{s.credits} ──────┐", "│                                              │", "│  ══ RECIPES ══                                │"]
        for rid in st.recipes_available:
            rc = RECIPES.get(rid, {}); inp = " + ".join(f"{amt}x {RESOURCES.get(r,{}).get('name',r)}" for r, amt in rc.get("inputs",{}).items())
            lines.append(f"│  {rc.get('name', rid):<18}  {rc.get('craft_time',0)}t  needs:{inp[:30]}  │")
            lines.append(f"│      → {rc.get('desc', '')[:46]}")
        if not st.recipes_available: lines.append("│  (no recipes available)                        │")
        lines.append("│  ── CARGO ──                                     │")
        for rid, amt in sorted(s.cargo.items.items()):
            lines.append(f"│  {RESOURCES.get(rid,{}).get('name', rid):<14} x{amt:<4}                    │")
        if not s.cargo.items: lines.append("│  (empty)                                      │")
        lines.append(f"│  {s.cargo.used()}/{s.cargo.capacity} used  Val:{s.cargo.total_value()}cr        │")
        lines.append("└──────────────────────────────────────────────┘")
        self.query_one("#craft-content").update("\n".join(lines))
    def on_key(self, event):
        """Закрывает экран по Escape или Q."""
        if event.key in ("escape","q"): event.stop(); self.dismiss()
    def on_input_submitted(self, event):
        """Обрабатывает команду craft [кол-во] <item> или передаёт ввод в process_command()."""
        app = self.app; s = app.ship; v = event.value.strip().lower()
        if v in ("close","exit","quit"): self.dismiss(); return
        p = v.split()
        if p and p[0] == "craft":
            amount = 1; target = ""
            if len(p) >= 3:
                try: amount = int(p[1]); target = p[2]
                except ValueError: target = p[1]
            if not target: app.logger.system("craft [amount] <item_id>"); self.dismiss(); return
            matched = None
            for rid in self.station.recipes_available:
                if rid.startswith(target) or RECIPES.get(rid,{}).get("name","").lower().startswith(target):
                    matched = rid; break
            if not matched: app.logger.system(f"Recipe '{target}' not available here.")
            else: msg, ok = s.craft(matched, amount); app.logger.system(msg)
            self.dismiss(); return
        app.process_command(v); self.dismiss()


# ═══════════════════════════════════════════════════════════════════════
# Hiring (tavern)
# ═══════════════════════════════════════════════════════════════════════

class HireScreen(Screen):
    """Экран найма экипажа в таверне. Показывает доступных кандидатов и текущий экипаж."""

    def __init__(self, station):
        """Сохраняет ссылку на станцию."""
        super().__init__(); self.station = station  # объект станции
    def compose(self):
        """Создаёт виджеты содержимого и поля ввода команд."""
        yield Static(id="hire-content"); yield Input(placeholder="hire <num>  |  close", id="hire-input")
    def on_mount(self):
        """Формирует список доступных для найма членов экипажа и текущий состав."""
        app = self.app; st = self.station; s = app.ship
        lines = [f"┌─ TAVERN ─ {st.name} [{st.faction}] ─ Cr:{s.credits} ──────┐", "│                                              │", "│  ══ AVAILABLE CREW ══                         │"]
        for i, cm in enumerate(st.crew_for_hire, 1):
            sn = CREW_SPECIALTIES.get(cm.specialty,{}).get("name", cm.specialty)
            lines.append(f"│  [{i}] {cm.name:<14} {sn:<12} Lv{cm.level}  salary:{cm.salary}cr  │")
        if not st.crew_for_hire: lines.append("│  (nobody looking for work)                    │")
        lines.append(f"│  ── YOUR CREW ({len(s.crew_members)}/{s._max_crew_slots()}) ──               │")
        for cm in s.crew_members:
            sn = CREW_SPECIALTIES.get(cm.specialty,{}).get("name", cm.specialty)
            a = " (on duty)" if cm.assigned else ""
            lines.append(f"│  {cm.name:<14} {sn:<12} Lv{cm.level}{a}  │")
        if not s.crew_members: lines.append("│  (no crew)                                    │")
        lines.append("└──────────────────────────────────────────────┘")
        self.query_one("#hire-content").update("\n".join(lines))
    def on_key(self, event):
        """Закрывает экран по Escape или Q."""
        if event.key in ("escape","q"): event.stop(); self.dismiss()
    def on_input_submitted(self, event):
        """Обрабатывает команду hire <num> или передаёт ввод в process_command()."""
        app = self.app; st = self.station; s = app.ship; v = event.value.strip().lower()
        if v in ("close","exit","quit"): self.dismiss(); return
        p = v.split()
        if p and p[0] == "hire" and len(p) >= 2:
            try: idx = int(p[1]) - 1
            except ValueError: app.logger.system("hire <num>"); return
            if 0 <= idx < len(st.crew_for_hire):
                cm = st.crew_for_hire.pop(idx); msg, ok = s.hire_crew(cm); app.logger.system(msg)
        else: app.process_command(v)
        self.on_mount()


# ═══════════════════════════════════════════════════════════════════════
# Landing Prep Screen
# ═══════════════════════════════════════════════════════════════════════

class LandingPrepScreen(Screen):
    """Экран подготовки к высадке. Позволяет выбрать члена экипажа для наземной экспедиции."""

    def __init__(self, site_type="station", site_name="Unknown"):
        """Сохраняет параметры места высадки и сбрасывает индекс выбора."""
        super().__init__()
        self.site_type = site_type  # тип места высадки: "station", "planet", "asteroid"
        self.site_name = site_name  # название места высадки
        self._selected = 0  # индекс выбранного члена экипажа

    def compose(self):
        """Создаёт виджеты содержимого и поля ввода."""
        yield Static(id="landing-content")
        yield Input(placeholder="L to land on  |  close", id="landing-input")

    def on_mount(self):
        """При монтировании обновляет экран подготовки."""
        self._refresh()

    def _refresh(self):
        """Формирует список доступного (неназначенного) экипажа для экспедиции."""
        app = self.app
        if not hasattr(app, "ship"):
            return
        s = app.ship
        lines = [
            "┌" + "─" * 56 + "┐",
            "│" + "LANDING PREP".center(56) + "│",
            f"│  Site: {self.site_name:<15} Type: {self.site_type:<12}│",
            "├" + "─" * 56 + "┤",
            "│  Available crew:                                     │",
        ]
        # Show unassigned crew members
        available = [cm for cm in s.crew_members if not cm.assigned]
        if not available:
            lines.append("│  (no unassigned crew)                             │")
        else:
            for i, cm in enumerate(available):
                sel = "▶" if i == self._selected else " "
                wpn = cm.weapon or "none"
                arm = cm.armor or "none"
                lines.append(f"│{sel}{i+1}. {cm.desc():<20} HP:{cm.hp:>2}/{cm.max_hp:<2} W:{wpn:<8} A:{arm:<8}│")

        lines.append("├" + "─" * 56 + "┤")
        lines.append("│  [Enter] Select crew member for expedition         │")
        lines.append("│  [D] Deploy now (select from cargo)               │")
        lines.append("│  [Esc] Cancel                                     │")
        lines.append("└" + "─" * 56 + "┘")
        self.query_one("#landing-content").update("\n".join(lines))

    def on_key(self, event):
        """Обрабатывает стрелки для выбора, Enter/D для запуска экспедиции, Escape для отмены."""
        app = self.app
        if event.key == "escape":
            event.stop(); self.app.dismiss_to_bridge(self); return

        s = app.ship
        available = [cm for cm in s.crew_members if not cm.assigned]

        if event.key == "up":
            if available:
                self._selected = (self._selected - 1) % len(available)
            self._refresh()
        elif event.key == "down":
            if available:
                self._selected = (self._selected + 1) % len(available)
            self._refresh()
        elif event.key == "enter" and available:
            idx = min(self._selected, len(available) - 1)
            cm = available[idx]
            self._launch(cm)
        elif event.key in ("d", "D") and available:
            idx = min(self._selected, len(available) - 1)
            cm = available[idx]
            self._launch(cm)

    def _launch(self, crew_member):
        """Запускает ExpeditionScreen с выбранным членом экипажа."""
        app = self.app
        from expedition import ExpeditionMap, ExpeditionController, ExpeditionScreen
        emp = ExpeditionMap(site_type=self.site_type)
        ctrl = ExpeditionController(crew_member, emp)
        app.push_screen(ExpeditionScreen(ctrl))
        self.dismiss()


# ═══════════════════════════════════════════════════════════════════════
# Scan Screen
# ═══════════════════════════════════════════════════════════════════════

class ScanScreen(Screen):
    """Экран сканера. Показывает объекты в радиусе сенсоров и результаты активного сканирования."""

    def __init__(self):
        """Инициализирует экран: пустой список целей, режим выбора, без результата."""
        super().__init__()
        self._selected = 0  # индекс выбранной цели
        self._targets = []  # список доступных для сканирования объектов
        self._result = None  # результат последнего сканирования
        self._mode = "select"  # режим: "select" (выбор цели) | "result" (просмотр результата)

    def compose(self):
        """Создаёт виджет отображения сканера."""
        yield Static(id="scan-content")

    def on_mount(self):
        """Загружает цели и отображает интерфейс сканера."""
        self._refresh_targets()
        self._update_display()

    def _refresh_targets(self):
        """Обновляет список сканируемых объектов в радиусе сенсоров."""
        app = self.app
        rng = app.ship.get_effective_stats().get("sensor_range", 5) * 2
        self._targets = app.galaxy.get_scannable_objects(app.player_x, app.player_y, rng)
        self._selected = min(self._selected, max(0, len(self._targets) - 1))

    def _update_display(self):
        """Формирует и отображает список целей или результат сканирования."""
        app = self.app
        s = app.ship
        lines = []
        W = 64

        if self._mode == "result" and self._result:
            lines.append("┌" + "─" * W + "┐")
            lines.append("│" + "SCAN RESULT".center(W) + "│")
            lines.append("├" + "─" * W + "┤")
            info = self._result.info
            for k, v in info.items():
                if k in ("scanned", "scan_level", "type"):
                    continue
                val = str(v)[:W - 10]
                lines.append(f"│  {k:<12} {val:<{W-17}}│")
            if self._result.level == "active":
                lines.append("│" + "─" * W + "┤")
                lines.append("│  [Enter] Deep scan (costs more)                │")
            lines.append("├" + "─" * W + "┤")
            lines.append("│" + "[Esc] Back to targets".center(W) + "│")
            lines.append("└" + "─" * W + "┘")
        elif self._mode == "select":
            lines.append("┌" + "─" * W + "┐")
            lines.append("│" + "SCANNER".center(W) + "│")
            lines.append(f"│  Sensor range: {s.get_effective_stats().get('sensor_range', 5)}  Energy: {s.total_power_generated() - s.total_power_consumed()} spare{'':>20}│")
            lines.append("├" + "─" * W + "┤")
            lines.append(f"│ {'':>2} {'Target':<25} {'Dist':>4} {'Status':<15}│")
            lines.append("├" + "─" * W + "┤")
            if not self._targets:
                lines.append("│  (no targets in sensor range)                   │")
            else:
                for i, (d, label, obj) in enumerate(self._targets):
                    sel = "▶" if i == self._selected else " "
                    scanned = getattr(obj, "scanned", False)
                    status = "Scanned" if scanned else "Unknown"
                    lines.append(f"│{sel}{i+1:>2}. {label:<25} {d:>3}  {status:<15}│")
            lines.append("├" + "─" * W + "┤")
            lines.append("│  [Enter] Active scan  [↑↓] Select  [Esc] Close    │")
            lines.append("└" + "─" * W + "┘")
        self.query_one("#scan-content").update("\n".join(lines))

    def on_key(self, event):
        """Обрабатывает клавиши: стрелки для выбора, Enter для сканирования, Escape для выхода/назад."""
        if event.key == "escape":
            if self._mode == "result":
                self._mode = "select"
                self._update_display()
            else:
                event.stop(); self.dismiss()
            return

        if self._mode == "select":
            if event.key == "up":
                self._selected = (self._selected - 1) % max(1, len(self._targets))
                self._update_display()
            elif event.key == "down":
                self._selected = (self._selected + 1) % max(1, len(self._targets))
                self._update_display()
            elif event.key == "enter" and self._targets:
                _, _, obj = self._targets[self._selected]
                app = self.app
                result = app.ship.scan_target(obj, "active", app.galaxy)
                self._result = result
                self._mode = "result"
                if result.success:
                    app.logger.system(f"Active scan: {result.summary()}")
                    # Check if a mission was generated
                    if hasattr(result, 'scanned_obj') and result.scanned_obj:
                        pass
                else:
                    err = result.info.get("error", "Scan failed.")
                    app.logger.system(f"Scan error: {err}")
                self._update_display()


# ═══════════════════════════════════════════════════════════════════════
# Action Menu
# ═══════════════════════════════════════════════════════════════════════

from locales import t
from config import load_settings, save_settings


class ActionMenu(Screen):
    """Контекстное меню действий, вызываемое клавишей E. Содержит разделы «Корабль», «Взаимодействие», «Система»."""

    def __init__(self):
        """Инициализирует экран: сброс индекса выбора и разделов."""
        super().__init__()
        self._selected = 0  # индекс выбранного действия
        self._sections = []  # список разделов: каждый — кортеж (название, список действий)

    def compose(self):
        """Создаёт виджет отображения меню."""
        yield Static(id="action-content")

    def on_mount(self):
        """Строит разделы меню и отображает их."""
        self._build_sections()
        self._refresh_ui()

    def _at_station(self):
        """Проверяет, пристыкован ли игрок к станции."""
        app = self.app
        return app.galaxy.get_station_at(app.player_x, app.player_y) if hasattr(app, "galaxy") else None

    def _nearby_npc(self):
        """Ищет NPC (пирата или торговца) на соседних клетках."""
        app = self.app
        if not hasattr(app, "galaxy"): return None
        px, py = app.player_x, app.player_y
        for p in app.galaxy.pirates:
            if p.alive and max(abs(p.x-px),abs(p.y-py)) <= 1: return p
        for t in app.galaxy.traders:
            if t.alive and max(abs(t.x-px),abs(t.y-py)) <= 1: return t
        return None

    def _build_sections(self):
        """Формирует разделы меню в зависимости от контекста (станция, тайл)."""
        app = self.app
        if not hasattr(app, "galaxy"):
            self._sections = [("System", [("q", "Close", lambda: self.dismiss())])]
            return
        st = self._at_station()
        self._sections = []

        ship_actions = [
            ("b", t("action.bridge"), "bridge"),
            ("e", t("action.engineering"), "engineering"),
            ("t", t("action.tactical"), "tactical"),
            ("c", t("action.cargo"), "cargo"),
            ("r", t("action.crew"), "crew"),
            ("m", t("action.missions"), "missions"),
            ("s", t("action.scan"), "scan"),
        ]
        self._sections.append((t("action.ship"), ship_actions))

        interact = []
        if st:
            interact.append(("d", t("action.trade"), "trade"))
            if st.modules_for_sale:
                interact.append(("p", t("action.trade")+" mod", "modules"))
            if st.stype == "shipyard":
                interact.append(("y", t("action.shipyard"), "shipyard"))
            if st.stype == "workshop":
                interact.append(("k", t("action.craft"), "craft"))
            if st.stype == "tavern":
                interact.append(("h", t("action.crew")+" hire", "hire"))
            interact.append(("f", t("action.refuel"), "refuel"))
            interact.append(("x", t("action.repair"), "repair"))
        tile = app.galaxy.tiles[app.player_y][app.player_x] if hasattr(app, "galaxy") else ""
        if tile in ("o", "÷", "◈"):
            interact.append(("l", t("action.land"), "land"))
        if interact:
            self._sections.append((t("action.interact"), interact))

        sys_actions = [
            ("g", t("action.settings"), "settings"),
            ("q", t("action.close"), "close"),
        ]
        self._sections.append((t("action.system"), sys_actions))

    def _dispatch(self, action_id):
        """Выполняет действие по его идентификатору и закрывает меню."""
        app = self.app
        st = self._at_station()
        # Все действия, которые открывают новый экран или выполняют
        # игровую логику, сначала закрывают ActionMenu, чтобы избежать
        # конфликта с новым экраном.
        if action_id == "close":
            self.dismiss(); return
        self.dismiss()
        m = {
            "bridge": lambda: app.push_screen(BridgeScreen()),
            "engineering": lambda: app.push_screen(EngineeringScreen()),
            "tactical": lambda: app.push_screen(TacticalScreen()),
            "cargo": lambda: app.push_screen(CargoScreen()),
            "crew": lambda: app.push_screen(CrewScreen()),
            "missions": lambda: app.push_screen(MissionsScreen()),
            "scan": lambda: app.push_screen(ScanScreen()),
            "trade": lambda: app.push_screen(TradeScreen(st)),
            "modules": lambda: app.push_screen(ModuleShopScreen(st)),
            "shipyard": lambda: app.push_screen(ShipyardScreen(st)),
            "craft": lambda: app.push_screen(CraftingScreen(st)),
            "hire": lambda: app.push_screen(HireScreen(st)),
            "refuel": lambda: app._act_refuel(),
            "repair": lambda: app._act_repair(),
            "land": lambda: app._try_landing(),
            "settings": lambda: app.push_screen(SettingsScreen()),
        }
        fn = m.get(action_id)
        if fn: fn()

    def _refresh_ui(self):
        """Отрисовывает меню действий с учётом выбранного элемента."""
        lines = []; W = 60
        lines.append("┌"+"─"*W+"┐")
        lines.append("│"+"ACTIONS".center(W)+"│")
        lines.append("├"+"─"*W+"┤")
        idx = 0
        for sec_name, acts in self._sections:
            lines.append("│"+"─"*W+"│")
            lines.append("│"+f"  {sec_name}".ljust(W-2)+"│")
            for key, label, _ in acts:
                sel = "▶" if idx == self._selected else " "
                lines.append(f"│{sel} [{key}] {label:<{W-8}}│")
                idx += 1
        lines.append("├"+"─"*W+"┤")
        lines.append("│"+" [↑↓] Navigate  [Enter/Key] Select  [Esc] Close".center(W)+"│")
        lines.append("└"+"─"*W+"┘")
        self.query_one("#action-content").update("\n".join(lines))

    def on_key(self, event):
        """Обрабатывает клавиши: стрелки для навигации, Enter/буква для выбора, Escape для закрытия."""
        if event.key == "escape":
            event.stop(); self.app.dismiss_to_bridge(self); return
        event.stop()
        all_actions = [a for _, acts in self._sections for a in acts]
        if event.key == "up" and all_actions:
            self._selected = (self._selected-1)%len(all_actions); self._refresh_ui()
        elif event.key == "down" and all_actions:
            self._selected = (self._selected+1)%len(all_actions); self._refresh_ui()
        elif event.key == "enter" and all_actions:
            _, _, aid = all_actions[self._selected]; self._dispatch(aid)
        for i, (key, _, aid) in enumerate(all_actions):
            if event.key == key:
                self._dispatch(aid); return


# ═══════════════════════════════════════════════════════════════════════
# Settings
# ═══════════════════════════════════════════════════════════════════════

class SettingsScreen(Screen):
    """Экран настроек игры. Позволяет изменить язык, автсохранение и привязки клавиш."""

    def __init__(self):
        """Загружает настройки, сбрасывает индекс выбора и режим ожидания клавиши."""
        super().__init__()
        self._settings = load_settings()  # словарь с текущими настройками
        self._selected = 0  # индекс выбранной строки
        self._waiting = None  # идентификатор действия, ожидающего нажатия клавиши

    def compose(self):
        """Создаёт виджеты содержимого и поля ввода."""
        yield Static(id="settings-content")
        yield Input(placeholder="change <action> <key>  |  close", id="settings-input")

    def on_mount(self):
        """При монтировании отображает панель настроек."""
        self._refresh_ui()

    def _refresh_ui(self):
        """Формирует и отображает список опций настроек: язык, автсохранение, клавиши, сброс."""
        s = self._settings; W = 60
        lines = ["┌"+"─"*W+"┐", "│"+t("ui.settings.title").center(W)+"│", "├"+"─"*W+"┤"]
        opts = []

        # Language
        lang_v = "Русский" if s["lang"]=="ru" else "English"
        opts.append(("lang", t("ui.lang"), lang_v))

        # Autosave
        asv = t("ui.autosave_on") if s["autosave"] else t("ui.autosave_off")
        opts.append(("autosave", t("ui.autosave"), asv))

        # Keys
        lines.append("│"+"  Keys".ljust(W-2)+"│")
        for action, key in s["keys"].items():
            label = t(f"ctrl.{action}") if t(f"ctrl.{action}")[:1]!="❌" else action
            mk = " [press key]" if self._waiting == action else ""
            opts.append(("key_"+action, f"  {label}", f"{key}{mk}"))

        # Reset
        opts.append(("reset", t("ui.reset_defaults"), ""))

        for i, (oid, name, val) in enumerate(opts):
            sel = "▶" if i==self._selected else " "
            lines.append(f"│{sel} {name:<20} {val:<{W-25}}│")

        lines.append("├"+"─"*W+"┤")
        lines.append("│"+" [Enter] Toggle/Change  [↑↓]  [Esc] Save & Close".center(W)+"│")
        lines.append("└"+"─"*W+"┘")
        self.query_one("#settings-content").update("\n".join(lines))

    def _opts(self):
        """Возвращает список опций для навигации: (id, значение)."""
        s = self._settings
        r = [("lang", s["lang"]), ("autosave", s["autosave"])]
        for k in s["keys"]: r.append(("key_"+k, s["keys"][k]))
        r.append(("reset", None))
        return r

    def on_key(self, event):
        """Обрабатывает клавиши: Enter для переключения/изменения, стрелки, Escape для сохранения и выхода."""
        if self._waiting:
            action = self._waiting
            self._waiting = None
            if event.key not in ("escape","enter"):
                self._settings["keys"][action] = event.key
            self._refresh_ui(); return
        if event.key == "escape":
            self._save_close(); return
        if event.key == "up":
            self._selected = (self._selected-1)%len(self._opts()); self._refresh_ui()
        elif event.key == "down":
            self._selected = (self._selected+1)%len(self._opts()); self._refresh_ui()
        elif event.key == "enter":
            opts = self._opts()
            if self._selected >= len(opts): return
            oid, val = opts[self._selected]
            if oid == "lang":
                s["lang"] = "en" if s["lang"]=="ru" else "ru"
                from locales import set_lang; set_lang(s["lang"])
                self._refresh_ui()
            elif oid == "autosave":
                s["autosave"] = not s["autosave"]
                self._refresh_ui()
            elif oid.startswith("key_"):
                action = oid[4:]
                self._waiting = action
                self._refresh_ui()
            elif oid == "reset":
                from config import DEFAULT_SETTINGS
                self._settings = dict(DEFAULT_SETTINGS)
                from locales import set_lang; set_lang(self._settings["lang"])
                self._refresh_ui()

    def on_input_submitted(self, event):
        """Обрабатывает текстовую команду change <action> <key> или close."""
        v = event.value.strip().lower()
        if v in ("close","exit","quit"):
            self._save_close(); return
        p = v.split()
        if p[0]=="change" and len(p)>=3 and p[1] in self._settings["keys"]:
            self._settings["keys"][p[1]] = p[2]
        self._refresh_ui()

    def _save_close(self):
        """Сохраняет настройки в файл, обновляет язык интерфейса и закрывает экран."""
        save_settings(self._settings)
        from locales import set_lang; set_lang(self._settings["lang"])
        self.dismiss()
