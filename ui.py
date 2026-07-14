"""UI screens: command, cargo, trade, bridge, engineering, tactical, crew."""

from textual.screen import Screen
from textual.widgets import Static, Input, DataTable, Footer
from config import RESOURCES, COMPARTMENTS, SHIP_MODULES


# ═══════════════════════════════════════════════════════════════════════
# Helper — consistent box drawing
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
    """Unified ship management hub — press 1-5 or Esc."""

    def compose(self):
        yield Static(id="hub-content")

    def on_mount(self):
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
        if event.key == "escape":
            self.dismiss()
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
    def compose(self):
        yield Input(placeholder="Enter command (help for list)...", id="cmd-input")

    def on_input_submitted(self, event):
        app = self.app
        if hasattr(app, "process_command"):
            app.process_command(event.value)
        self.dismiss()


# ═══════════════════════════════════════════════════════════════════════
# Cargo inventory
# ═══════════════════════════════════════════════════════════════════════

class CargoScreen(Screen):
    def compose(self):
        yield Static(id="cargo-header")
        yield DataTable(id="cargo-table")
        yield Static(id="cargo-footer")

    def on_mount(self):
        app = self.app
        if not hasattr(app, "ship"):
            return
        s = app.ship
        c = s.cargo
        cb = s.get_effective_stats().get("cargo_bonus", 0)
        self.query_one("#cargo-header").update(
            f"┌─ CARGO HOLD ──────────────────────────────┐\n"
            f"│ {c.used()}/{c.capacity + cb} used  │  Value: {c.total_value()}cr                   │\n"
            f"└────────────────────────────────────────────┘"
        )
        table = self.query_one("#cargo-table")
        table.clear()
        table.add_columns("Resource", "Category", "Qty", "Unit Price")
        catmap = {"raw": "Raw", "refined": "Refined", "advanced": "Adv", "special": "Special"}
        for rid, amt in sorted(c.items.items()):
            info = RESOURCES.get(rid, {})
            ct = catmap.get(info.get("cat", ""), "Other")
            table.add_row(
                info.get("name", rid), ct, str(amt),
                f"{info.get('base_price', 0)}cr"
            )
        self.query_one("#cargo-footer").update("[Esc/Q] Close")

    def on_key(self, event):
        if event.key in ("escape", "q"):
            self.dismiss()


# ═══════════════════════════════════════════════════════════════════════
# Trade screen
# ═══════════════════════════════════════════════════════════════════════

class TradeScreen(Screen):
    def __init__(self, station):
        super().__init__()
        self.station = station

    def compose(self):
        yield Static(id="trade-header")
        yield Static(id="trade-prices")
        yield Input(placeholder="buy <res> <amt>  |  sell <res> <amt>  |  close", id="trade-input")

    def on_mount(self):
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
        if event.key in ("escape", "q"):
            self.dismiss()

    def on_input_submitted(self, event):
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
# Bridge (F1)
# ═══════════════════════════════════════════════════════════════════════

class BridgeScreen(Screen):
    def compose(self):
        yield Static(id="bridge-status")
        yield Static(id="bridge-modules")
        yield Static(id="bridge-cargo")
        yield Static(id="bridge-footer")

    def on_mount(self):
        app = self.app
        if not hasattr(app, "ship"):
            return
        s = app.ship
        st = s.get_effective_stats()
        p_gen = s.total_power_generated()
        p_con = s.total_power_consumed()
        eff = 100 if p_con <= p_gen else max(30, int(p_gen / max(1, p_con) * 100))

        race = s.race.title() if s.race else "Human"
        rel = s.religion or "none"
        crew_count = sum(1 for v in s.crew.values() if v)

        lines = [
            f"┌─ BRIDGE ─ {s.name} ─ {race} [{rel}] ─ Cr:{s.credits} ───┐",
            f"│                                              │",
            f"│  Hull    {s.hull:>4}/{s.max_hull + st.get('hull_bonus', 0):<4}  "
            f"Shields  {s.shield_hp:>3}/{st['shield_cap']:<3}  "
            f"Fuel {s.fuel:>3}      │",
            f"│  Power   {p_gen:>3} gen / {p_con:<3} used  ({eff}% eff)          │",
            f"│  Speed   {st['speed']:>2}   Evasion {st['evasion']:>3}%   "
            f"Sensors +{st['sensor_range']}         │",
            f"│  Damage  {st['damage']:>3}   Accuracy {st['accuracy']:>3}%  "
            f"Crew {crew_count}/4 assigned    │",
            f"│  Shields {st['shield_cap']:>3} cap  Regen {st['shield_regen']:>2}/t  "
            f"Range {st.get('range', 1)}           │",
            f"│                                              │",
        ]
        self.query_one("#bridge-status").update("\n".join(lines))

        # Modules — compact table
        mlines = ["┌─ MODULES ────────────────────────────────────┐"]
        for c in COMPARTMENTS:
            mods = s.compartments[c]["modules"]
            if not mods:
                continue
            for m in mods:
                dur_pct = int(m.durability / max(1, m.max_durability) * 100)
                bar = _bar(dur_pct, 10)
                sts = "BROKEN" if m.is_broken() else " ON"
                energy = f"⚡{m.energy_consumption}" if m.energy_consumption > 0 else "   "
                mlines.append(
                    f"│ [{sts}] {m.name:<18} {c:<12} dur:{bar} {energy} │"
                )
        mlines.append("└──────────────────────────────────────────────┘")
        self.query_one("#bridge-modules").update("\n".join(mlines))

        # Cargo summary
        clines = ["┌─ CARGO ──────────────────────────────────────┐"]
        if s.cargo.items:
            for rid, amt in sorted(s.cargo.items.items()):
                name = RESOURCES.get(rid, {}).get("name", rid)
                clines.append(f"│  {name:<14} x{amt:<4}                    │")
        else:
            clines.append("│  (empty)                                      │")
        cb = st.get("cargo_bonus", 0)
        clines.append(f"│  {s.cargo.used()}/{s.cargo.capacity + cb} used  │  {s.cargo.total_value()}cr                     │")
        clines.append("└──────────────────────────────────────────────┘")
        self.query_one("#bridge-cargo").update("\n".join(clines))

        self.query_one("#bridge-footer").update(
            "[Esc] Back  |  [F1] Hub  |  direct: F2 Eng  F3 Tac  F4 Cargo  F5 Crew"
        )

    def on_key(self, event):
        if event.key == "escape":
            self.dismiss()
        elif event.key in ("f2", "F2"):
            self.dismiss()
            if hasattr(self.app, "push_screen"):
                self.app.push_screen(EngineeringScreen())
        elif event.key in ("f3", "F3"):
            self.dismiss()
            if hasattr(self.app, "push_screen"):
                self.app.push_screen(TacticalScreen())
        elif event.key in ("f5", "F5"):
            self.dismiss()
            if hasattr(self.app, "push_screen"):
                self.app.push_screen(CrewScreen())


# ═══════════════════════════════════════════════════════════════════════
# Engineering (F2)
# ═══════════════════════════════════════════════════════════════════════

def _bar(pct, width=10):
    """Draw a progress bar: [████░░░░]"""
    filled = int(pct / 100 * width)
    return f"[{'█' * filled}{'░' * (width - filled)}]"


class EngineeringScreen(Screen):
    def compose(self):
        yield Static(id="eng-title")
        yield Static(id="eng-power-summary")
        yield Static(id="eng-compartments")
        yield Input(placeholder="power <comp> <0-10>  |  close", id="eng-input")

    def on_mount(self):
        app = self.app
        if not hasattr(app, "ship"):
            return
        s = app.ship
        p_gen = s.total_power_generated()
        p_con = s.total_power_consumed()
        eff = 100 if p_con <= p_gen else max(30, int(p_gen / max(1, p_con) * 100))

        self.query_one("#eng-title").update(
            f"┌─ ENGINEERING ────────────────────────────────┐"
        )
        self.query_one("#eng-power-summary").update(
            f"│  Reactor: {p_gen} generated  │  Load: {p_con} used  ({eff}%)  │\n"
            f"│──────────────────────────────────────────────│"
        )

        comp_lines = []
        for c in COMPARTMENTS:
            mods = s.compartments[c]["modules"]
            pw = s.compartments[c]["power"]
            pbar = _bar(pw * 10, 10)  # 0-10 → 0-100%
            mlist = ", ".join(
                f"{m.name}{' ✗' if m.is_broken() else ''}"
                for m in mods
            ) if mods else "(none)"
            energy = sum(m.energy_consumption for m in mods if m.active and not m.is_broken())
            comp_lines.append(
                f"│ {c:<14} power:{pw:>2} {pbar}  ⚡{energy}  {mlist[:40]}"
            )
        footer = "│                                              │\n└──────────────────────────────────────────────┘"
        self.query_one("#eng-compartments").update("\n".join(comp_lines) + "\n" + footer)

    def on_key(self, event):
        if event.key == "escape":
            self.dismiss()
        elif event.key in ("f1", "F1"):
            self.dismiss()
            if hasattr(self.app, "push_screen"):
                self.app.push_screen(BridgeScreen())

    def on_input_submitted(self, event):
        app = self.app
        if not hasattr(app, "process_command"):
            return
        v = event.value.strip().lower()
        if v in ("close", "exit"):
            self.dismiss(); return
        app.process_command(v)
        self.on_mount()


# ═══════════════════════════════════════════════════════════════════════
# Tactical (F3)
# ═══════════════════════════════════════════════════════════════════════

class TacticalScreen(Screen):
    def compose(self):
        yield Static(id="tac-header")
        yield Static(id="tac-content")
        yield Input(placeholder="fire <num>  |  close", id="tac-input")

    def on_mount(self):
        app = self.app
        if not hasattr(app, "ship"):
            return
        s = app.ship
        stats = s.get_effective_stats()

        lines = [
            f"┌─ TACTICAL ─ {s.name} ────────────────"
            f"H:{s.hull} Sh:{s.shield_hp}/{stats['shield_cap']} F:{s.fuel} ─┐",
            f"│                                              │",
            f"│  ══ WEAPONS ══                               │",
        ]

        weapons = [m for m in s.compartments["weapon"]["modules"]
                   if m.active and not m.is_broken()]
        if weapons:
            for i, w in enumerate(weapons, 1):
                dur_pct = int(w.durability / max(1, w.max_durability) * 100)
                lines.append(
                    f"│  [{i}] {w.name:<18} ⚔{w.stats.get('damage',0):>3} "
                    f"🎯{w.stats.get('accuracy',0)}%  "
                    f"dur:{_bar(dur_pct, 6)}  │"
                )
        else:
            lines.append("│  (no weapons installed)                       │")

        lines.append(f"│  Effective: ⚔{stats['damage']} dmg  🎯{stats['accuracy']}%  📏rng:{stats.get('range',1)}           │")
        lines.append(f"│                                              │")
        lines.append(f"│  ══ TARGETS (range {stats.get('range',1)}) ══                            │")

        g = app.galaxy
        targets = []
        rng = stats.get("range", 1)
        for p in g.pirates:
            if p.alive:
                d = max(abs(p.x - app.player_x), abs(p.y - app.player_y))
                if d <= rng:
                    targets.append((d, p.name, p.hull, p.max_hull,
                                    getattr(p, 'shield_hp', 0), "☠", p))
        for t in g.traders:
            if t.alive:
                d = max(abs(t.x - app.player_x), abs(t.y - app.player_y))
                if d <= rng:
                    targets.append((d, t.name, t.hull, t.max_hull,
                                    getattr(t, 'shield_hp', 0), "T", t))
        targets.sort(key=lambda x: x[0])

        if targets:
            for i, (d, name, hull, mhull, sh, icon, _) in enumerate(targets, 1):
                hpct = int(hull / max(1, mhull) * 100)
                hbar = _bar(hpct, 8)
                sh_str = f" 🛡{sh}" if sh > 0 else ""
                lines.append(
                    f"│  [{i}] {icon} {name:<18} {hbar} H:{hull}/{mhull}{sh_str} d:{d}  │"
                )
        else:
            lines.append("│  (no targets in weapon range)                 │")

        lines.append("└──────────────────────────────────────────────┘")
        self.query_one("#tac-content").update("\n".join(lines))

    def on_key(self, event):
        if event.key == "escape":
            self.dismiss()

    def on_input_submitted(self, event):
        app = self.app
        if not hasattr(app, "process_command"):
            return
        v = event.value.strip().lower()
        if v in ("close", "exit"):
            self.dismiss(); return
        parts = v.split()
        if parts and parts[0] == "fire" and len(parts) >= 2:
            try:
                idx = int(parts[1]) - 1
            except ValueError:
                return
            # Rebuild target list
            g = app.galaxy
            rng = app.ship.get_effective_stats().get("range", 1)
            tgts = []
            for p in g.pirates:
                if p.alive:
                    d = max(abs(p.x - app.player_x), abs(p.y - app.player_y))
                    if d <= rng:
                        tgts.append((d, p.name, p))
            for t in g.traders:
                if t.alive:
                    d = max(abs(t.x - app.player_x), abs(t.y - app.player_y))
                    if d <= rng:
                        tgts.append((d, t.name, t))
            tgts.sort(key=lambda x: x[0])
            if 0 <= idx < len(tgts):
                _, name, _ = tgts[idx]
                app.process_command(f"attack {name}")
            self.dismiss()
        else:
            app.process_command(v)
            self.dismiss()


# ═══════════════════════════════════════════════════════════════════════
# Module Shop
# ═══════════════════════════════════════════════════════════════════════

class ModuleShopScreen(Screen):
    def __init__(self, station):
        super().__init__()
        self.station = station

    def compose(self):
        yield Static(id="shop-content")
        yield Input(placeholder="buy <num>  |  close", id="shop-input")

    def on_mount(self):
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
        if event.key in ("escape", "q"):
            self.dismiss()

    def on_input_submitted(self, event):
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
    def __init__(self, station):
        super().__init__()
        self.station = station

    def compose(self):
        yield Static(id="missions-content")
        yield Input(placeholder="accept <num>  |  close", id="missions-input")

    def on_mount(self):
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
        if event.key in ("escape", "q"):
            self.dismiss()

    def on_input_submitted(self, event):
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
    def compose(self):
        yield Static(id="crew-content")
        yield Input(placeholder="assign <name> <post>  |  close", id="crew-input")

    def on_mount(self):
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
        if event.key == "escape":
            self.dismiss()
        elif event.key in ("f1", "F1"):
            self.dismiss()
            if hasattr(self.app, "push_screen"):
                self.app.push_screen(BridgeScreen())

    def on_input_submitted(self, event):
        app = self.app
        if not hasattr(app, "process_command"):
            return
        v = event.value.strip().lower()
        if v in ("close", "exit"):
            self.dismiss(); return
        app.process_command(v)
        self.on_mount()
