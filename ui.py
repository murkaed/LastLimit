"""UI screens: command, cargo, trade, bridge, engineering, crew."""

from textual.screen import Screen
from textual.widgets import Static, Input, DataTable, Footer
from config import RESOURCES, COMPARTMENTS

# ---------------------------------------------------------------------------
# Command console
# ---------------------------------------------------------------------------

class CommandScreen(Screen):
    def compose(self):
        yield Input(placeholder="Enter command (help for list)...", id="cmd-input")

    def on_input_submitted(self, event):
        app = self.app
        if hasattr(app, "process_command"):
            app.process_command(event.value)
        self.dismiss()

# ---------------------------------------------------------------------------
# Cargo inventory
# ---------------------------------------------------------------------------

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
        self.query_one("#cargo-header").update(
            f"Cargo: {c.used()}/{c.capacity}  Value: {c.total_value()}cr"
        )
        table = self.query_one("#cargo-table")
        table.clear()
        table.add_columns("Item", "Cat", "Qty", "Price")
        catmap = {"raw": "Raw", "refined": "Refined", "advanced": "Advanced", "special": "Special"}
        for rid, amt in sorted(c.items.items()):
            info = RESOURCES.get(rid, {})
            ct = catmap.get(info.get("cat", ""), "Other")
            table.add_row(rid, ct, str(amt), f"{info.get('base_price', 0)}cr")
        self.query_one("#cargo-footer").update("[Q] Close")

    def on_key(self, event):
        if event.key in ("escape", "q"):
            self.dismiss()

# ---------------------------------------------------------------------------
# Trade screen
# ---------------------------------------------------------------------------

class TradeScreen(Screen):
    def __init__(self, station):
        super().__init__()
        self.station = station

    def compose(self):
        yield Static(id="trade-header")
        yield Static(id="station-goods")
        yield Static(id="player-cargo")
        yield Input(placeholder="buy/sell <res> <amt> or close", id="trade-input")

    def on_mount(self):
        app = self.app
        if not hasattr(app, "ship"):
            return
        st = self.station
        s = app.ship

        hdr = (f"Trading at {st.name}[{st.faction}]  "
               f"Cr:{s.credits}  Cargo:{s.cargo.used()}/{s.cargo.capacity}")
        self.query_one("#trade-header").update(hdr)

        sg = ["── Station ──"]
        for rid in sorted(RESOURCES):
            stk = st.inventory.get(rid, 0)
            pb, _ = st.price_for_player(rid, True, s)
            ps, _ = st.price_for_player(rid, False, s)
            sg.append(f"  {rid:<12} stock:{stk:<3}  buy:{pb:>4}cr  sell:{ps:>4}cr")
        self.query_one("#station-goods").update("\n".join(sg))

        pc = ["── Your Cargo ──"]
        for rid, amt in sorted(s.cargo.items.items()):
            pc.append(f"  {rid:<12} qty:{amt:<3}  val:"
                      f"{RESOURCES.get(rid, {}).get('base_price', 0) * amt}cr")
        if not s.cargo.items:
            pc.append("  (empty)")
        self.query_one("#player-cargo").update("\n".join(pc))

    def on_key(self, event):
        if event.key in ("escape", "q"):
            self.dismiss()

    def on_input_submitted(self, event):
        app = self.app
        if not hasattr(app, "process_command"):
            return
        v = event.value.strip().lower()
        if v in ("close", "exit", "quit"):
            self.dismiss()
            return
        p = v.split()
        if p and p[0] in ("buy", "sell"):
            v = "trade " + v
        app.process_command(v)
        self.on_mount()

# ---------------------------------------------------------------------------
# Bridge (F1)
# ---------------------------------------------------------------------------

class BridgeScreen(Screen):
    def compose(self):
        yield Static(id="bridge-title")
        yield Static(id="bridge-systems")
        yield Static(id="bridge-modules")
        yield Static(id="bridge-footer")

    def on_mount(self):
        app = self.app
        if not hasattr(app, "ship"):
            return
        s = app.ship
        st = s.get_effective_stats()
        p_gen = s.total_power_generated()
        p_con = s.total_power_consumed()

        title = f"┏━ BRIDGE ━━━━━━━━━━━━━━━━━━ {s.name} ━━━━━━━━━━━━━━━━━━┓"
        sys = (
            f"  Hull: {s.hull}  Fuel: {s.fuel}  "
            f"Crew: {sum(1 for v in s.crew.values() if v)} assigned\n"
            f"  Power: {p_gen} gen / {p_con} used\n"
            f"  Speed: {st['speed']}  Evasion: {st['evasion']}%\n"
            f"  Shields: {st['shield_cap']} cap  Regen: {st['shield_regen']}/t\n"
            f"  Weapons: {st['damage']} dmg  {st['accuracy']}% acc\n"
            f"  Sensors: {st['sensor_range']} range\n"
            f"  Credits: {s.credits}  "
            f"Cargo: {s.cargo.used()}/{s.cargo.capacity}"
        )
        self.query_one("#bridge-title").update(title)
        self.query_one("#bridge-systems").update(sys)

        mods = []
        for c in COMPARTMENTS:
            for m in s.compartments[c]["modules"]:
                sts = ("ON" if m.active and not m.is_broken()
                       else "OFF" if m.is_broken() else "ON")
                mods.append(f"  [{sts}] {m.name} ({c}) "
                            f"dur:{m.durability}/{m.max_durability}")
        mtext = "── Modules ──\n" + "\n".join(mods) if mods else "── Modules ──\n  None"
        self.query_one("#bridge-modules").update(mtext)
        self.query_one("#bridge-footer").update("[F2] Engineering  [F5] Crew  [Esc] Close")

    def on_key(self, event):
        if event.key == "escape":
            self.dismiss()
        elif event.key in ("f2", "F2"):
            self.dismiss()
            if hasattr(self.app, "push_screen"):
                self.app.push_screen(EngineeringScreen())
        elif event.key in ("f5", "F5"):
            self.dismiss()
            if hasattr(self.app, "push_screen"):
                self.app.push_screen(CrewScreen())

# ---------------------------------------------------------------------------
# Engineering (F2)
# ---------------------------------------------------------------------------

class EngineeringScreen(Screen):
    def compose(self):
        yield Static(id="eng-title")
        yield Static(id="eng-power")
        yield Static(id="eng-compartments")
        yield Input(placeholder="power <comp> <val> or close", id="eng-input")

    def on_mount(self):
        app = self.app
        if not hasattr(app, "ship"):
            return
        s = app.ship
        self.query_one("#eng-title").update("┏━ ENGINEERING ━━━━━━━━━━━━━━━━━━━━━━━┓")
        self.query_one("#eng-power").update(
            f"  Power: {s.total_power_generated()} gen / {s.total_power_consumed()} used"
        )
        comps = []
        for c in COMPARTMENTS:
            mods = s.compartments[c]["modules"]
            pw = s.compartments[c]["power"]
            ml = ", ".join(f"{m.name}{'(OFF)' if m.is_broken() else ''}" for m in mods)
            comps.append(f"  {c:<16} power:{pw}  {ml}")
        self.query_one("#eng-compartments").update("── Compartments ──\n" + "\n".join(comps))

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
            self.dismiss()
            return
        app.process_command(v)
        self.on_mount()

# ---------------------------------------------------------------------------
# Crew (F5)
# ---------------------------------------------------------------------------

class CrewScreen(Screen):
    def compose(self):
        yield Static(id="crew-title")
        yield Static(id="crew-list")
        yield Input(placeholder="assign <name> <post> or close", id="crew-input")

    def on_mount(self):
        app = self.app
        if not hasattr(app, "ship"):
            return
        s = app.ship
        self.query_one("#crew-title").update("┏━ CREW ━━━━━━━━━━━━━━━━━━━━━━━┓")
        cl = ["── Posts ──"]
        for post, member in s.crew.items():
            cl.append(f"  {post:<12} {member or '(vacant)'}")
        cl.append("── Available ──\n  (hire crew at stations)")
        self.query_one("#crew-list").update("\n".join(cl))

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
            self.dismiss()
            return
        app.process_command(v)
        self.on_mount()
