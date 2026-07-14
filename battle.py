"""Energy- and crew-aware turn-based combat system."""

import random
from textual.screen import Screen
from textual.widgets import Static

from config import RESOURCES, COMPARTMENTS

# ---------------------------------------------------------------------------
# Battle consumables
# ---------------------------------------------------------------------------

BATTLE_CONSUMABLES = {
    "repair_kit": {"name": "Repair Kit", "desc": "Restore 20 hull", "effect": {"hull": 20}},
    "fuel_cell": {"name": "Fuel Cell", "desc": "Restore 10 energy", "effect": {"energy": 10}},
    "shield_booster": {"name": "Shield Booster", "desc": "Restore 15 shields", "effect": {"shield": 15}},
}

BATTLE_SKILLS = {
    "overload_shields": {"name": "Overload Shields", "desc": "Restore 30% shields (15e)", "energy_cost": 15},
    "precise_shot": {"name": "Precise Shot", "desc": "High-crit attack (10e)", "energy_cost": 10},
    "emergency_repair": {"name": "Emergency Repair", "desc": "Restore 30 hull (10e)", "energy_cost": 10},
}

# ── Compartment effects when destroyed ──────────────────────────────────
COMP_EFFECTS = {
    "reactor":     {"power_bonus": -3},
    "engine":      {"evasion": -4, "speed": -1},
    "weapon":      {"damage": -4, "accuracy": -10},
    "shield":      {"shield_cap": -8, "shield_regen": -2},
    "sensor":      {"accuracy": -8},
    "life_support": {"evasion": -2},
    "cargo":       {},
}

ENEMY_TARGET_PRIORITIES = {
    "pirate": ["shield", "weapon", "engine", "reactor", "sensor", "life_support", "cargo"],
    "trader": ["weapon", "engine", "shield", "reactor", "sensor", "life_support", "cargo"],
}


def _bar_s(current, maximum, width=10):
    if maximum <= 0: return "░" * width
    filled = int(current / maximum * width)
    return "█" * filled + "░" * (width - filled)


def _build_enemy_compartments(is_pirate):
    comps = {c: {"modules": [], "power": 3} for c in COMPARTMENTS}
    if is_pirate:
        comps["reactor"]["modules"].append({"name":"Scavenged Reactor","dur":40,"max_dur":40,"active":True,"armor":5})
        comps["engine"]["modules"].append({"name":"Booster Drive","dur":30,"max_dur":30,"active":True,"armor":3,"evasion":5})
        comps["weapon"]["modules"].append({"name":"Pirate Laser","dur":25,"max_dur":25,"active":True,"armor":5,"damage":8,"accuracy":60})
        comps["shield"]["modules"].append({"name":"Scrap Shield","dur":30,"max_dur":30,"active":True,"armor":8,"shield_cap":10,"shield_regen":1})
    else:
        comps["reactor"]["modules"].append({"name":"Civilian Reactor","dur":50,"max_dur":50,"active":True,"armor":5})
        comps["engine"]["modules"].append({"name":"Civilian Drive","dur":40,"max_dur":40,"active":True,"armor":5,"evasion":2})
        comps["weapon"]["modules"].append({"name":"Light Turret","dur":20,"max_dur":20,"active":True,"armor":5,"damage":5,"accuracy":50})
        comps["shield"]["modules"].append({"name":"Basic Shield","dur":35,"max_dur":35,"active":True,"armor":5,"shield_cap":15,"shield_regen":2})
    comps["sensor"]["modules"].append({"name":"Scanner","dur":20,"max_dur":20,"active":True,"armor":3})
    comps["life_support"]["modules"].append({"name":"Life Support","dur":20,"max_dur":20,"active":True,"armor":3})
    comps["cargo"]["modules"].append({"name":"Cargo Bay","dur":20,"max_dur":20,"active":True,"armor":3})
    return comps


def _total_enemy_stat(comps, key):
    total = 0
    for c in COMPARTMENTS:
        for m in comps[c]["modules"]:
            if m.get("active") and m.get("dur", 0) > 0:
                total += m.get(key, 0)
    return total


def _compartment_status_str(comp, comp_data, width=10):
    alive = [m for m in comp_data["modules"] if m.get("active") and m.get("dur", 0) > 0]
    total_dur = sum(m.get("dur", 0) for m in alive)
    max_dur = sum(m.get("max_dur", 1) for m in comp_data["modules"] if m.get("active", True))
    if not alive or total_dur <= 0:
        return f"{comp:<8} [☠DESTROYED]"
    pct = int(total_dur / max(1, max_dur) * 100)
    bar = _bar_s(pct, 100, width)
    return f"{comp:<8} {bar}"


class BattleController:
    """Handles combat logic with energy, crew bonuses, and compartment effects."""

    def __init__(self, player_ship, enemy_npc, app, selected_weapon_idx=0):
        self.player = player_ship
        self.enemy = enemy_npc
        self.app = app
        self.is_pirate = type(enemy_npc).__name__ == "PirateShip"
        self.enemy_comps = _build_enemy_compartments(self.is_pirate)
        self.enemy_max_hull = enemy_npc.max_hull
        self.enemy_shield_cap = getattr(enemy_npc, "shield_hp", 0) or _total_enemy_stat(self.enemy_comps, "shield_cap")
        self.enemy_items = ["repair_kit"] if random.random() < 0.3 else []
        self.player_energy = 50
        self.player_max_energy = 50
        self.selected_weapon_idx = selected_weapon_idx
        self.log = []
        self.over = False
        self.victory = False
        self.player_defending = False
        self._compute_turn_order()

    def _get_player_weapons(self):
        return [m for m in self.player.compartments["weapon"]["modules"] if m.active and not m.is_broken()]

    def _player_evasion(self):
        return self.player.get_effective_stats().get("evasion", 0)

    def _crew_bonus(self, key):
        return self.player._crew_bonus(key, 0) if hasattr(self.player, "_crew_bonus") else 0

    def _compute_turn_order(self):
        p_spd = self.player.get_effective_stats().get("speed", 1) + self._crew_bonus("speed")
        e_spd = _total_enemy_stat(self.enemy_comps, "evasion") // 5 + 2
        p_roll = p_spd + random.randint(1, 6)
        e_roll = e_spd + random.randint(1, 6)
        if e_roll > p_roll:
            self.turn_order = "enemy"
            self.add_log(f"☠ {self.enemy.name} moves first!")
        else:
            self.turn_order = "player"
            self.add_log(f"▶ {self.player.name} moves first!")

    def add_log(self, msg):
        self.log.append(msg)
        if len(self.log) > 30:
            self.log = self.log[-30:]

    def _enemy_stat_with_effects(self, key, default=0):
        base = _total_enemy_stat(self.enemy_comps, key) or default
        penalty = 0
        for c in COMPARTMENTS:
            alive = [m for m in self.enemy_comps[c]["modules"] if m.get("active") and m.get("dur", 0) > 0]
            if not alive:
                penalty += COMP_EFFECTS.get(c, {}).get(key, 0)
        return max(0, base + penalty)

    def _regen_player_energy(self):
        reactor_power = self.player.total_power_generated()
        eng_bonus = self._crew_bonus("power_bonus") // 10
        regen = max(5, reactor_power // 2) + eng_bonus
        old = self.player_energy
        self.player_energy = min(self.player_max_energy, self.player_energy + regen)
        if self.player_energy > old:
            self.add_log(f"⚡ Energy +{self.player_energy - old} (regen {regen}).")

    # ── Actions ────────────────────────────────────────────────────────

    def do_attack(self, weapon_idx, target_comp=None):
        self.player_defending = False
        weapons = self._get_player_weapons()
        if not weapons:
            self.add_log("No weapons!")
            self._next_turn(); return
        weapon = weapons[weapon_idx] if 0 <= weapon_idx < len(weapons) else weapons[0]
        base_dmg = weapon.stats.get("damage", 10)
        accuracy = weapon.stats.get("accuracy", 70)
        weapon_name = weapon.name
        en_cost = weapon.energy_consumption
        if self.player_energy < en_cost:
            self.add_log(f"⚡ Need {en_cost}e for {weapon_name} (have {self.player_energy}).")
            self._next_turn(); return
        self.player_energy -= en_cost
        p_gen = self.player.total_power_generated()
        p_con = self.player.total_power_consumed()
        eff = min(1.5, p_gen / max(1, p_con))
        damage = max(1, int(base_dmg * eff))
        crew_acc = self._crew_bonus("accuracy")
        crew_dmg = self._crew_bonus("damage")
        accuracy += crew_acc
        damage += crew_dmg
        e_evasion = self._enemy_stat_with_effects("evasion")
        hit_chance = max(5, min(95, accuracy - e_evasion))
        is_crit = random.random() < 0.10 + self._crew_bonus("accuracy") * 0.002
        if random.random() * 100 >= hit_chance:
            self.add_log(f"✗ {weapon_name} missed!")
            self._next_turn(); return
        if is_crit:
            damage = int(damage * 2)
            self.add_log(f"★ CRITICAL!")
        if target_comp is None or target_comp not in self.enemy_comps:
            target_comp = random.choice(COMPARTMENTS)
        comp = self.enemy_comps[target_comp]
        if self.enemy.shield_hp > 0:
            absorbed = min(self.enemy.shield_hp, damage)
            self.enemy.shield_hp -= absorbed
            damage -= absorbed
            if absorbed > 0:
                self.add_log(f"🛡 Shield absorbed {absorbed}.")
        if damage > 0:
            armor = sum(m.get("armor", 0) for m in comp["modules"])
            damage = max(1, damage - armor // 3)
            alive = [m for m in comp["modules"] if m.get("active") and m.get("dur", 0) > 0]
            if alive:
                hit = random.choice(alive)
                hit["dur"] = max(0, hit["dur"] - damage)
                if hit["dur"] <= 0:
                    hit["active"] = False
                    self.add_log(f"💥 {hit['name']} DESTROYED!")
                else:
                    self.add_log(f"🔧 {hit['name']} -{damage} dur ({hit['dur']}/{hit['max_dur']})")
            else:
                self.enemy.hull = max(0, self.enemy.hull - damage)
                self.add_log(f"💢 Hull hit! -{damage}")
        self.add_log(f"→ {weapon_name} @ {target_comp}  {'★' if is_crit else ''}")
        if self.enemy.hull <= 0:
            self._on_enemy_defeated(); return
        self._next_turn()

    def do_defend(self):
        self.player_defending = True
        stats = self.player.get_effective_stats()
        regen = stats.get("shield_regen", 0) * 2 + self._crew_bonus("regen")
        cap = stats.get("shield_cap", 30)
        old = self.player.shield_hp
        self.player.shield_hp = min(cap, self.player.shield_hp + regen)
        self.add_log(f"🛡 Defensive! Shields {self.player.shield_hp}/{cap} (+{self.player.shield_hp-old}).")
        self._next_turn()

    def do_use_item(self, item_rid):
        self.player_defending = False
        info = BATTLE_CONSUMABLES.get(item_rid)
        if not info: self.add_log(f"Unknown '{item_rid}'."); return
        if not self.player.cargo.has(item_rid): self.add_log(f"No {info['name']}!"); return
        self.player.cargo.remove(item_rid, 1)
        eff = info["effect"]
        if "hull" in eff:
            self.player.hull = min(self.player.max_hull, self.player.hull + eff["hull"])
            self.add_log(f"{info['name']}! Hull +{eff['hull']}.")
        elif "shield" in eff:
            cap = self.player.get_effective_stats().get("shield_cap", 30)
            old, s = self.player.shield_hp, self.player.shield_hp
            self.player.shield_hp = min(cap, self.player.shield_hp + eff["shield"])
            self.add_log(f"{info['name']}! Shield +{self.player.shield_hp - old}.")
        elif "energy" in eff:
            old = self.player_energy
            self.player_energy = min(self.player_max_energy, self.player_energy + eff["energy"])
            self.add_log(f"{info['name']}! Energy +{self.player_energy - old}.")
        self._next_turn()

    def do_skill(self, skill_id):
        self.player_defending = False
        skill = BATTLE_SKILLS.get(skill_id)
        if not skill: return
        if self.player_energy < skill["energy_cost"]:
            self.add_log(f"Need {skill['energy_cost']}e, have {self.player_energy}."); return
        self.player_energy -= skill["energy_cost"]
        if skill_id == "overload_shields":
            cap = self.player.get_effective_stats().get("shield_cap", 30)
            restore = int(cap * 0.3)
            self.player.shield_hp = min(cap, self.player.shield_hp + restore)
            self.add_log(f"⚡ Overload Shields! +{restore} shield.")
        elif skill_id == "precise_shot":
            dmg = 15 + self.player.get_effective_stats().get("damage", 0) + self._crew_bonus("damage")
            is_crit = random.random() < 0.5
            if is_crit: dmg *= 2; self.add_log("★ PRECISE SHOT CRIT!")
            self.enemy.take_damage(dmg)
            self.add_log(f"🎯 Precise Shot! {self.enemy.hull} hull remains.")
            if not self.enemy.alive: self._on_enemy_defeated(); return
        elif skill_id == "emergency_repair":
            self.player.hull = min(self.player.max_hull, self.player.hull + 30)
            self.add_log("🔧 Emergency Repair! +30 hull.")
        self._next_turn()

    def do_escape(self):
        p_spd = self.player.get_effective_stats().get("speed", 1) + self._crew_bonus("speed")
        e_spd = _total_enemy_stat(self.enemy_comps, "evasion") // 5 + 2
        base = 40 + (p_spd - e_spd) * 5
        chance = max(10, min(90, base))
        if random.random() * 100 < chance:
            self.add_log("✓ Escaped!"); self.over = True; self.victory = False
        else:
            self.add_log("✗ Escape failed!"); self._next_turn()

    def _next_turn(self):
        if self.over: return
        self._regen_player_energy()
        self._do_enemy_turn()

    def _do_enemy_turn(self):
        if self.over: return
        regen = _total_enemy_stat(self.enemy_comps, "shield_regen")
        self.enemy.shield_hp = min(self.enemy_shield_cap, self.enemy.shield_hp + regen)
        hull_pct = self.enemy.hull / max(1, self.enemy_max_hull)
        shield_pct = self.enemy.shield_hp / max(1, self.enemy_shield_cap)
        weapons = [m for m in self.enemy_comps["weapon"]["modules"] if m.get("active") and m.get("dur", 0) > 0]
        priorities = ENEMY_TARGET_PRIORITIES.get("pirate" if self.is_pirate else "trader", COMPARTMENTS)
        if hull_pct < 0.3 and "repair_kit" in self.enemy_items:
            self.enemy_items.remove("repair_kit")
            self.enemy.hull = min(self.enemy_max_hull, self.enemy.hull + 20)
            self.add_log(f"☠ {self.enemy.name} uses Repair Kit!")
            self._check_player_death(); return
        elif hull_pct < 0.2 and random.random() < 0.4:
            if random.random() < 0.5:
                self.add_log(f"☠ {self.enemy.name} fled!"); self.over = True; self.victory = True; return
        if weapons:
            weapon = random.choice(weapons)
            base_dmg = weapon.get("damage", 8)
            acc = weapon.get("accuracy", 60)
            hit_chance = max(5, min(95, acc - self._player_evasion()))
            if random.random() * 100 < hit_chance:
                damage = base_dmg
                if self.player_defending: damage = max(1, damage // 2)
                viable = [c for c in priorities if self.enemy_comps[c]["modules"]]
                tcomp = viable[0] if viable else random.choice(COMPARTMENTS)
                target = self.player.compartments[tcomp]
                if self.player.shield_hp > 0:
                    absorbed = min(self.player.shield_hp, damage)
                    self.player.shield_hp -= absorbed; damage -= absorbed
                if damage > 0:
                    alive = [m for m in target["modules"] if m.active and not m.is_broken()]
                    if alive:
                        hit = random.choice(alive)
                        hit.durability = max(0, hit.durability - damage)
                        self.add_log(f"☠ {self.enemy.name} hits {hit.name}! (-{damage})")
                        if hit.is_broken(): hit.active = False; self.add_log(f"💥 {hit.name} BROKEN!")
                    else:
                        self.player.hull = max(0, self.player.hull - damage)
                        self.add_log(f"☠ {self.enemy.name} hits hull! (-{damage})")
                self.add_log(f"☠ {self.enemy.name} attacks {tcomp}.")
            else:
                self.add_log(f"☠ {self.enemy.name} missed!")
        else:
            dmg = 10
            if self.player_defending: dmg = max(1, dmg // 2)
            self.player.take_damage(dmg)
            self.add_log(f"☠ {self.enemy.name} rams! -{dmg} hull.")
        self._check_player_death()

    def _check_player_death(self):
        if self.player.hull <= 0: self._on_player_defeated()

    def _on_enemy_defeated(self):
        self.over = True; self.victory = True
        loot_cr = random.randint(50, 150)
        self.player.credits += loot_cr
        loot_item = random.choice(["metal", "electronics", "shield_mod", "relic"])
        amt = random.randint(1, 3)
        self.player.cargo.add(loot_item, amt)
        if self.is_pirate:
            self.player.reputation["free_traders"] = min(100, self.player.reputation.get("free_traders", 0) + 2)
        self.add_log(f"★ {self.enemy.name} destroyed! +{loot_cr}cr, {amt}×{loot_item}.")
        if hasattr(self.app, "logger"):
            self.app.logger.combat(f"★ Victory! +{loot_cr}cr, {amt}×{loot_item}.")

    def _on_player_defeated(self):
        self.over = True; self.victory = False
        self.add_log(f"☠ {self.player.name} destroyed...")
        if hasattr(self.app, "death_cause"):
            self.app.death_cause = f"Destroyed by {self.enemy.name}."

    def debug_enemy_status(self):
        lines = []
        for c in COMPARTMENTS:
            alive = [m for m in self.enemy_comps[c]["modules"] if m.get("active") and m.get("dur", 0) > 0]
            if alive:
                for m in alive:
                    lines.append(f"  {c}/{m['name']} dur={m['dur']}/{m['max_dur']}")
            else:
                lines.append(f"  {c}: DESTROYED")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# BattleScreen
# ═══════════════════════════════════════════════════════════════════════

class BattleScreen(Screen):
    """Turn-based battle with compartment targeting."""

    def __init__(self, controller: BattleController):
        super().__init__()
        self.ctrl = controller
        self.menu_state = "main"
        self.menu_index = 0
        self.selected_weapon_idx = controller.selected_weapon_idx

    def compose(self):
        yield Static(id="battle-content")

    def on_mount(self):
        self._update_display()

    def _update_display(self):
        c = self.ctrl
        lines = []
        W = 74

        lines.append(f"  ┌{'─' * (W-4)}┐")
        lines.append(f"  │{'':^{W-4}}│")

        ps = c.player; pe = c.enemy
        lines.append(f"  │  {ps.name[:18]:<18}  {'':>7}  {pe.name[:18]:<18}  │")

        p_hull_pct = int(ps.hull / max(1, ps.max_hull) * 100)
        e_hull_pct = int(pe.hull / max(1, c.enemy_max_hull) * 100)
        p_sh_pct = int(ps.shield_hp / max(1, ps.get_effective_stats().get("shield_cap",1)) * 100)
        e_sh_pct = int(pe.shield_hp / max(1, c.enemy_shield_cap) * 100)
        lines.append(f"  │  H:{_bar_s(p_hull_pct,100,12)} {ps.hull:>3}/{ps.max_hull:<3}  vs  H:{_bar_s(e_hull_pct,100,12)} {pe.hull:>3}/{c.enemy_max_hull:<3}  │")
        lines.append(f"  │  S:{_bar_s(p_sh_pct,100,12)} {ps.shield_hp:>3}/{ps.get_effective_stats().get('shield_cap',1):<3}  vs  S:{_bar_s(e_sh_pct,100,12)} {pe.shield_hp:>3}/{c.enemy_shield_cap:<3}  │")
        e_bar = _bar_s(c.player_energy, c.player_max_energy, 12)
        lines.append(f"  │  E:{e_bar} {c.player_energy:>2}/{c.player_max_energy:<2}{'':>32}  │")

        # ── Compartment schematic ──
        lines.append(f"  │  {'─' * (W-6)}  │")
        lines.append(f"  │  {'ENEMY COMPARTMENTS':^{W-6}}  │")
        lines.append(f"  │  {'─' * (W-6)}  │")
        for i, comp_name in enumerate(COMPARTMENTS):
            cd = c.enemy_comps[comp_name]
            status = _compartment_status_str(comp_name, cd, 10)
            marker = f"[{i+1}]" if not c.over else "   "
            lines.append(f"  │  {marker} {status:<30}{'':>35}  │")

        # ── Battle log ──
        lines.append(f"  │  {'─' * (W-6)}  │")
        for entry in c.log[-5:]:
            lines.append(f"  │  {entry:<{W-6}}  │")

        # ── Menu ──
        lines.append(f"  │  {'─' * (W-6)}  │")
        if c.over:
            msg = "★ VICTORY! ★" if c.victory else "☠ DEFEATED ☠"
            lines.append(f"  │  {msg:^{W-6}}  │")
            lines.append(f"  │  {'':^{W-4}}  │")
            lines.append(f"  │  {'Press any key...':^{W-6}}  │")
        else:
            menu = self._render_menu()
            for ml in menu:
                lines.append(f"  │  {ml:<{W-6}}  │")

        lines.append(f"  │{'':^{W-4}}│")
        lines.append(f"  └{'─' * (W-4)}┘")
        self.query_one("#battle-content").update("\n".join(lines))

    def _render_menu(self):
        ms = self.menu_state; c = self.ctrl
        if ms == "main":
            return [
                "[1] Attack  [2] Defend  [3] Items  [4] Skills  [5] Escape",
                f"    Energy: {c.player_energy}/{c.player_max_energy}",
            ]
        elif ms == "attack_weapon":
            r = []
            for i, w in enumerate(c._get_player_weapons()):
                r.append(f"  [{i+1}] {w.name}  ⚔{w.stats.get('damage',0)} 🎯{w.stats.get('accuracy',0)}% ⚡{w.energy_consumption}")
            r.append("  [0] Back"); return r
        elif ms == "attack_target":
            r = []
            for i, cn in enumerate(COMPARTMENTS):
                alive = [m for m in c.enemy_comps[cn]["modules"] if m.get("active") and m.get("dur", 0) > 0]
                r.append(f"    [{i+1}] {cn:<14} ({len(alive)} mod)" if alive else f"    [{i+1}] {cn:<14} (inert)")
            r.append("    [0] Random")
            return r
        elif ms == "items":
            found = False; r = []
            for rid, info in BATTLE_CONSUMABLES.items():
                qty = c.player.cargo.has(rid)
                if qty > 0: found = True; r.append(f"  [{rid[0].upper()}] {info['name']:<16} x{qty}")
            if not found: r.append("  (no items)")
            r.append("  [0] Back"); return r
        elif ms == "skills":
            r = []
            for sid, sk in BATTLE_SKILLS.items():
                ok = "✓" if c.player_energy >= sk["energy_cost"] else "✗"
                r.append(f"  [{sid[0].upper()}] {sk['name']:<20} {sk['energy_cost']}e {ok}")
            r.append("  [0] Back"); return r
        return []

    def on_key(self, event):
        c = self.ctrl
        if c.over: self._apply_outcome(); self.dismiss(); return
        k = event.key
        if self.menu_state == "main":
            if k == "1":
                if c._get_player_weapons(): self.menu_state = "attack_weapon"
                else: c.add_log("No weapons!")
            elif k == "2": c.do_defend()
            elif k == "3": self.menu_state = "items"
            elif k == "4": self.menu_state = "skills"
            elif k == "5": c.do_escape()
            self._update_display()
        elif self.menu_state == "attack_weapon":
            wk = c._get_player_weapons()
            if k == "0": self.menu_state = "main"
            elif k in "123456789":
                idx = int(k) - 1
                if idx < len(wk): self.selected_weapon_idx = idx; self.menu_state = "attack_target"
            self._update_display()
        elif self.menu_state == "attack_target":
            if k == "0": c.do_attack(self.selected_weapon_idx, None); self.menu_state = "main"
            elif k.isdigit() and k != "0":
                idx = int(k) - 1
                if idx < len(COMPARTMENTS): c.do_attack(self.selected_weapon_idx, COMPARTMENTS[idx]); self.menu_state = "main"
            self._update_display()
        elif self.menu_state == "items":
            if k == "0": self.menu_state = "main"
            else:
                km = {"r": "repair_kit", "f": "fuel_cell", "s": "shield_booster"}
                if k in km and c.player.cargo.has(km[k]): c.do_use_item(km[k]); self.menu_state = "main"
            self._update_display()
        elif self.menu_state == "skills":
            if k == "0": self.menu_state = "main"
            else:
                km = {"o": "overload_shields", "p": "precise_shot", "e": "emergency_repair"}
                if k in km: c.do_skill(km[k]); self.menu_state = "main"
            self._update_display()

    def _apply_outcome(self):
        c = self.ctrl; app = self.app
        if not c.victory and c.player.hull <= 0:
            if hasattr(app, "GameState"):
                from galaxy_map import GameState
                app.state = GameState.GAME_OVER
            app.death_cause = f"Destroyed by {c.enemy.name}."
        if hasattr(app, "update_map"): app.update_map()
        if hasattr(app, "update_info"): app.update_info()
