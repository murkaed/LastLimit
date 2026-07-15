"""Game data models: cargo, ship, station, galaxy, events."""

import random
from config import (
    WIDTH, HEIGHT, RESOURCES, FACTIONS, RACES, SHIP_MODULES,
    COMPARTMENTS, CONTRABAND, TILE_EMPTY, TILE_STAR, TILE_BLACK_HOLE,
    TILE_ASTEROIDS, TILE_PLANET, TILE_STATION, TILE_WORMHOLE,
    SHIP_HULLS, UPGRADES, RECIPES, CREW_SPECIALTIES, CREW_NAMES,
    STATION_TYPES, SCAN_SIGNAL_TYPES,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

MODULE_STAT_KEYS = {"power","speed","evasion","damage","accuracy",
                    "shield_cap","shield_regen","sensor_range",
                    "cargo_bonus","crew_efficiency","hull_bonus","range"}

STARTER_MODULE_MAP = {
    "reactor": "fusion_reactor",
    "engine": "ion_drive",
    "shield": "deflector_shield",
    "sensor": "long_range_scanner",
    "weapon": "laser_turret",
}

# ---------------------------------------------------------------------------
# Scan result
# ---------------------------------------------------------------------------

class ScanResult:
    def __init__(self, success, level="passive", info=None, scanned_obj=None):
        self.success = success
        self.level = level  # passive, active, deep
        self.info = info or {}
        self.scanned_obj = scanned_obj

    def summary(self):
        if not self.success:
            return "Scan failed."
        s = self.info
        parts = [f"Scan: {s.get('type', 'unknown')}"]
        if "hull" in s:
            parts.append(f"H:{s['hull']}/{s.get('max_hull', '?')}")
        if "shield" in s:
            parts.append(f"S:{s['shield']}")
        if "cargo" in s:
            parts.append(f"Cargo:{s['cargo']}")
        if "weapons" in s:
            parts.append(f"Weapons:{s['weapons']}")
        if "signals" in s:
            parts.append(f"Signals:{s['signals']}")
        return " | ".join(parts)

CREW_STAT_MAP = {
    "evasion": "evasion", "speed": "speed", "accuracy": "accuracy",
    "damage": "damage", "sensor_range": "sensor_range",
    "regen": "shield_regen",
}

UPGRADE_STAT_MAP = {
    "cargo_bonus": "cargo_bonus",
    "sensor_range": "sensor_range",
    "speed": "speed",
}

# ---------------------------------------------------------------------------
# Cargo
# ---------------------------------------------------------------------------

class CargoHold:
    def __init__(self, capacity=50):
        self.capacity = capacity
        self.items: dict[str, int] = {}

    def used(self):
        return sum(self.items.values())

    def free(self):
        return max(0, self.capacity - self.used())

    def add(self, res_id: str, amount: int) -> bool:
        if self.free() < amount:
            return False
        self.items[res_id] = self.items.get(res_id, 0) + amount
        return True

    def remove(self, res_id: str, amount: int) -> bool:
        if self.items.get(res_id, 0) < amount:
            return False
        self.items[res_id] -= amount
        if self.items[res_id] <= 0:
            del self.items[res_id]
        return True

    def has(self, res_id: str) -> int:
        return self.items.get(res_id, 0)

    def total_value(self) -> int:
        return sum(
            RESOURCES.get(r, {}).get("base_price", 0) * a
            for r, a in self.items.items()
        )

# ---------------------------------------------------------------------------
# Ship module
# ---------------------------------------------------------------------------

class ShipModule:
    def __init__(self, mod_id: str, level=1):
        info = SHIP_MODULES.get(mod_id, {})
        self.id = mod_id
        self.name = info.get("name", mod_id)
        self.comp = info.get("comp", "reactor")
        self.energy_consumption = info.get("energy", 0)
        self.stats = {k: v for k, v in info.items() if k in MODULE_STAT_KEYS}
        self.level = level
        self._apply_level_bonus()
        self.durability = info.get("durability", 50)
        self.max_durability = self.durability
        self.cost = info.get("cost", 100)
        self.active = True
        self.desc = info.get("desc", "")

    def is_broken(self):
        return self.durability <= 0

    def upgrade_cost(self):
        return int(self.cost * 0.6 * self.level)

    def upgrade_resources(self):
        return {"metal": self.level * 2, "electronics": self.level}

    def can_upgrade(self):
        return self.level < 5

    def upgrade(self):
        if not self.can_upgrade():
            return False
        self.level += 1
        self._apply_level_bonus()
        return True

    def _apply_level_bonus(self):
        if self.level <= 1:
            return
        info = SHIP_MODULES.get(self.id, {})
        factor = 1.0 + (self.level - 1) * 0.10
        self.stats = {k: int(info.get(k, 0) * factor) for k in MODULE_STAT_KEYS if k in info}
        self.energy_consumption = int(info.get("energy", 0) * factor)
        self.durability = int(info.get("durability", 50) * factor)
        self.max_durability = self.durability

# ---------------------------------------------------------------------------
# Crew member
# ---------------------------------------------------------------------------

class CrewMember:
    def __init__(self, name, specialty_id, race=None):
        self.name = name
        self.specialty = specialty_id
        self.race = race or random.choice(list(RACES))
        self.level = 1
        self.experience = 0
        spec = CREW_SPECIALTIES.get(specialty_id, {})
        self.post = spec.get("posts", [specialty_id])[0]
        self.bonus = dict(spec.get("bonus", {}))
        self.assigned = False
        self.salary = random.randint(20, 60) * self.level
        # Ground combat stats
        self.hp = 30
        self.max_hp = 30
        self.ap = 4       # action points per turn
        self.max_ap = 4
        self.weapon = "pistol"
        self.armor = "vest"
        self.inventory = {}  # item_id: qty
        self.combat_skill = 50  # base accuracy for ground combat

    def xp_for_next(self):
        return self.level * 50

    def add_xp(self, amount):
        self.experience += amount
        if self.experience >= self.xp_for_next():
            self.experience -= self.xp_for_next()
            self.level += 1
            # Scale bonuses
            for k in self.bonus:
                self.bonus[k] = int(self.bonus[k] * (1 + (self.level - 1) * 0.15))

    def desc(self):
        spec_name = CREW_SPECIALTIES.get(self.specialty, {}).get("name", self.specialty)
        return f"{self.name} ({spec_name} Lv{self.level})"

# ---------------------------------------------------------------------------
# Player ship
# ---------------------------------------------------------------------------

class PlayerShip:
    def __init__(self, name="Endeavour", hull=100):
        self.name = name
        self.hull_id = "corvette"
        hull_cfg = SHIP_HULLS.get("corvette", {})
        # hull parameter overrides the config hull (backward compat with tests)
        if hull != 100:
            self.hull = hull
            self.max_hull = hull
        else:
            self.hull = hull_cfg.get("hull", hull)
            self.max_hull = self.hull
        self.owned_hulls = ["corvette"]
        self.upgrades = {}  # upgrade_id -> True
        self.shield_hp = 30
        self.fuel = 80
        self.credits = 1000
        self.radiation_shield = False
        self.race = "human"
        self.religion = None
        self.reputation = {f: 0 for f in FACTIONS}
        self.reputation["pirates"] = -10
        self.skill_trade = 0
        # Crew: assigned posts + roster
        self.crew = {"Pilot": None, "Engineer": None, "Tactical": None, "Scientist": None}
        self.crew_members: list[CrewMember] = []
        # Calculate cargo from hull + upgrades
        cb = self._upgrade_bonus("cargo_bonus", 0)
        self.cargo = CargoHold(hull_cfg.get("cargo", 50) + cb)
        # Compartments
        self._init_compartments(hull_cfg)
        self._last_damaged_module = None
        self.missions: list[Mission] = []
        self.tracked_mission = None

    def _init_compartments(self, hull_cfg):
        """Set up compartments based on hull config."""
        num_comps = hull_cfg.get("compartments", 5)
        priority = ["reactor", "engine", "shield", "sensor", "weapon",
                    "cargo", "life_support"]
        active = set(priority[:num_comps])
        self.compartments = {}
        for c in COMPARTMENTS:
            self.compartments[c] = {"power": 5, "modules": []}
        for comp, mod_id in STARTER_MODULE_MAP.items():
            if comp in active:
                self.compartments[comp]["modules"].append(ShipModule(mod_id))

    # ---------- Upgrade helpers ----------

    def _upgrade_bonus(self, key, default=0):
        total = default
        for uid in self.upgrades:
            cfg = UPGRADES.get(uid, {})
            total += cfg.get("bonus", {}).get(key, 0)
        return total

    def _crew_bonus(self, key, default=0):
        total = default
        for post, member_name in self.crew.items():
            if not member_name:
                continue
            cm = self._get_crew(member_name)
            if cm and cm.assigned:
                total += cm.bonus.get(key, 0)
        return total

    def _get_crew(self, name):
        for cm in self.crew_members:
            if cm.name.lower() == name.lower():
                return cm
        return None

    # ---------- Hull management ----------

    def buy_hull(self, hull_id):
        """Buy a new hull at a shipyard. Returns (message, success)."""
        if hull_id in self.owned_hulls:
            return f"Already own {hull_id}.", False
        cfg = SHIP_HULLS.get(hull_id)
        if not cfg:
            return f"Unknown hull '{hull_id}'.", False
        if self.credits < cfg["cost"]:
            return f"Need {cfg['cost']}cr, have {self.credits}cr.", False
        self.credits -= cfg["cost"]
        self.owned_hulls.append(hull_id)
        return f"Purchased {cfg['name']} for {cfg['cost']}cr.", True

    def sell_hull(self, hull_id):
        """Sell a hull at a shipyard (50% price). Cannot sell current hull."""
        if hull_id not in self.owned_hulls:
            return f"Don't own {hull_id}.", False
        if hull_id == self.hull_id:
            return "Cannot sell current hull.", False
        cfg = SHIP_HULLS.get(hull_id)
        if not cfg:
            return f"Unknown hull '{hull_id}'.", False
        price = cfg["cost"] // 2
        self.credits += price
        self.owned_hulls.remove(hull_id)
        return f"Sold {cfg['name']} for {price}cr.", True

    def switch_hull(self, hull_id):
        """Switch to an owned hull, transferring modules where possible."""
        if hull_id not in self.owned_hulls:
            return f"Don't own {hull_id}.", False
        cfg = SHIP_HULLS.get(hull_id)
        if not cfg:
            return f"Unknown hull '{hull_id}'.", False
        # Collect all current modules
        all_modules = []
        for c in COMPARTMENTS:
            all_modules.extend(self.compartments[c]["modules"])
        # Set new hull
        self.hull_id = hull_id
        self.max_hull = cfg["hull"]
        self.hull = min(self.hull, self.max_hull)
        base_cap = cfg.get("cargo", 50)
        cb = self._upgrade_bonus("cargo_bonus", 0)
        self.cargo.capacity = base_cap + cb
        # Re-init compartments and reinstall what fits
        self._init_compartments(cfg)
        # Try to place excess modules
        leftover = []
        for m in all_modules:
            if m.comp in self.compartments and len(self.compartments[m.comp]["modules"]) <= 1:
                # Replace starter module with this one
                existing = [x for x in self.compartments[m.comp]["modules"]]
                if len(existing) == 1 and existing[0].id in ("fusion_reactor", "ion_drive",
                        "deflector_shield", "long_range_scanner", "laser_turret"):
                    self.compartments[m.comp]["modules"] = [m]
                    placed = True
            if not placed:
                leftover.append(m)
        return f"Switched to {cfg['name']}. {len(leftover)} modules moved to cargo (not implemented).", True

    # ---------- Permanent upgrades ----------

    def has_upgrade(self, upgrade_id):
        return self.upgrades.get(upgrade_id, False)

    def apply_upgrade(self, upgrade_id):
        """Apply a permanent hull upgrade. Returns (message, success)."""
        if self.has_upgrade(upgrade_id):
            return f"Already have {upgrade_id}.", False
        cfg = UPGRADES.get(upgrade_id)
        if not cfg:
            return f"Unknown upgrade '{upgrade_id}'.", False
        if self.credits < cfg["cost"]:
            return f"Need {cfg['cost']}cr, have {self.credits}cr.", False
        # Check resources
        for rid, amt in cfg["inputs"].items():
            if self.cargo.has(rid) < amt:
                return f"Need {amt} {rid}.", False
        # Consume
        self.credits -= cfg["cost"]
        for rid, amt in cfg["inputs"].items():
            self.cargo.remove(rid, amt)
        self.upgrades[upgrade_id] = True
        # Apply immediate bonuses
        bonus = cfg.get("bonus", {})
        if "max_hull" in bonus:
            self.max_hull += bonus["max_hull"]
            self.hull = min(self.hull + bonus["max_hull"], self.max_hull)
        if "cargo_bonus" in bonus:
            self.cargo.capacity += bonus["cargo_bonus"]
        return f"Installed {cfg['name']}.", True

    # ---------- Crafting ----------

    def craft(self, recipe_id, amount=1):
        """Craft items from recipe. Returns (message, success)."""
        recipe = RECIPES.get(recipe_id)
        if not recipe:
            return f"Unknown recipe '{recipe_id}'.", False
        # Check resources
        inputs = recipe["inputs"]
        for rid, amt in inputs.items():
            needed = amt * amount
            if self.cargo.has(rid) < needed:
                return f"Need {needed} {rid} (have {self.cargo.has(rid)}).", False
        # Check output space
        output_id = recipe_id
        if self.cargo.free() < amount:
            return f"Need {amount} cargo space (have {self.cargo.free()}).", False
        # Consume inputs
        for rid, amt in inputs.items():
            self.cargo.remove(rid, amt * amount)
        # Create output
        self.cargo.add(output_id, amount)
        return f"Crafted {amount}x {recipe['name']}.", True

    # ---------- Crew management ----------

    def hire_crew(self, crew_member):
        """Hire a crew member. Returns (message, success)."""
        if len(self.crew_members) >= self._max_crew_slots():
            return "Crew quarters full.", False
        if self.credits < crew_member.salary:
            return f"Need {crew_member.salary}cr salary.", False
        self.credits -= crew_member.salary
        self.crew_members.append(crew_member)
        return f"Hired {crew_member.name} ({crew_member.specialty}).", True

    def fire_crew(self, name):
        """Fire a crew member by name."""
        cm = self._get_crew(name)
        if not cm:
            return f"No crew named '{name}'.", False
        # Unassign if on duty
        for post, member in list(self.crew.items()):
            if member and member.lower() == name.lower():
                self.crew[post] = None
                cm.assigned = False
        self.crew_members.remove(cm)
        return f"Fired {cm.name}.", True

    def assign_crew(self, name, post):
        """Assign a crew member to a post. Returns (message, success)."""
        cm = self._get_crew(name)
        if not cm:
            return f"No crew named '{name}'.", False
        if post not in self.crew:
            return f"Unknown post '{post}'.", False
        spec_posts = CREW_SPECIALTIES.get(cm.specialty, {}).get("posts", [])
        if post not in spec_posts:
            spec_name = CREW_SPECIALTIES.get(cm.specialty, {}).get("name", cm.specialty)
            return f"{cm.name} ({spec_name}) cannot take '{post}' post.", False
        # Unassign from current post
        for p, member in list(self.crew.items()):
            if member and member.lower() == name.lower():
                self.crew[p] = None
                cm.assigned = False
        # Assign to new post
        old = self.crew[post]
        if old:
            old_cm = self._get_crew(old)
            if old_cm:
                old_cm.assigned = False
        self.crew[post] = cm.name
        cm.assigned = True
        return f"{cm.name} assigned to {post}.", True

    def _max_crew_slots(self):
        """Base crew slots from life support module."""
        base = 2
        for m in self.compartments.get("life_support", {}).get("modules", []):
            if m.active and not m.is_broken():
                base += m.stats.get("crew_efficiency", 0) // 5
        return base

    def use_item(self, item_id, amount=1):
        """Use a consumable item from cargo. Returns (message, success)."""
        BONUSES = {
            "repair_kit": {"hull": 20, "msg": "Restored {} hull"},
            "fuel_cell": {"fuel": 10, "msg": "Refined {} fuel"},
            "shield_booster": {"shield": 15, "msg": "Boosted {} shields"},
        }
        bonus = BONUSES.get(item_id)
        if not bonus:
            return f"Item '{item_id}' is not consumable.", False
        have = self.cargo.has(item_id)
        if have < amount:
            return f"Need {amount}, have {have}.", False
        if not self.cargo.remove(item_id, amount):
            return "Cargo error.", False
        applied = 0
        if "hull" in bonus:
            prev = self.hull
            self.hull = min(self.max_hull, self.hull + bonus["hull"] * amount)
            applied += self.hull - prev
        if "fuel" in bonus:
            self.fuel += bonus["fuel"] * amount
            applied += bonus["fuel"] * amount
        if "shield" in bonus:
            cap = self.get_effective_stats().get("shield_cap", 0)
            prev = self.shield_hp
            self.shield_hp = min(cap, self.shield_hp + bonus["shield"] * amount)
            applied += self.shield_hp - prev
        return (bonus["msg"].format(applied), True)

    def install_module_from_cargo(self, mod_id):
        """Install a module from cargo into matching compartment. Returns (message, success)."""
        have = self.cargo.has(mod_id)
        if not have:
            return f"No '{mod_id}' in cargo.", False
        info = SHIP_MODULES.get(mod_id)
        if not info:
            return f"Unknown module '{mod_id}'.", False
        comp = info.get("comp", "reactor")
        if comp not in self.compartments:
            return f"No '{comp}' compartment.", False
        if not self.cargo.remove(mod_id, 1):
            return "Cargo error.", False
        self.compartments[comp]["modules"].append(ShipModule(mod_id))
        return f"Installed {info.get('name', mod_id)} in {comp}.", True

    def take_damage(self, amount):
        """Deal damage: shields absorb first, remainder to hull. Returns True if alive."""
        if self.shield_hp > 0:
            absorbed = min(self.shield_hp, amount)
            self.shield_hp -= absorbed
            amount -= absorbed
        if amount > 0:
            self.hull = max(0, self.hull - amount)
            self._damage_random_module()
        return self.hull > 0

    def _damage_random_module(self):
        """Chance to damage a random active module when hull is hit."""
        import random
        if random.random() > 0.3:
            return
        candidates = [
            m for c in COMPARTMENTS
            for m in self.compartments[c]["modules"]
            if m.active and not m.is_broken()
        ]
        if candidates:
            m = random.choice(candidates)
            m.durability = max(0, m.durability - random.randint(5, 15))
            self._last_damaged_module = m

    def regen_shields(self):
        cap = self.get_effective_stats().get("shield_cap", 0)
        rate = self.get_effective_stats().get("shield_regen", 0)
        self.shield_hp = min(cap, self.shield_hp + rate)
        # Crew hull regen
        hr = self._crew_bonus("hull_regen", 0)
        if hr > 0 and self.hull < self.max_hull:
            self.hull = min(self.max_hull, self.hull + hr)

    def repair_module(self, comp_name, cost_metal=2, cost_electronics=1):
        """Repair the most damaged module in a compartment. Returns (msg, cost)."""
        if comp_name not in self.compartments:
            return f"Unknown compartment '{comp_name}'.", 0
        mods = self.compartments[comp_name]["modules"]
        damaged = [m for m in mods if m.durability < m.max_durability]
        if not damaged:
            return f"No damaged modules in {comp_name}.", 0
        m = max(damaged, key=lambda x: x.max_durability - x.durability)
        repair_amount = min(20, m.max_durability - m.durability)
        m.durability += repair_amount
        status = "repaired" if not m.is_broken() else "partially repaired"
        return f"{m.name} {status} (+{repair_amount} dur).", cost_metal + cost_electronics

    def total_power_generated(self):
        base = sum(
            m.stats.get("power", 0)
            for m in self.compartments["reactor"]["modules"]
        )
        bonus = self._upgrade_bonus("power_bonus", 0)
        return base + bonus

    def total_power_consumed(self):
        return sum(
            m.energy_consumption
            for c in COMPARTMENTS
            for m in self.compartments[c]["modules"]
            if m.active and not m.is_broken()
        )

    def get_effective_stats(self):
        stats = {
            "speed": 0, "evasion": 0, "damage": 0, "accuracy": 0,
            "shield_cap": 0, "shield_regen": 0, "sensor_range": 7,
            "cargo_bonus": 0, "crew_efficiency": 0, "hull_bonus": 0,
            "range": 1,
        }
        total = self.total_power_generated()
        used = self.total_power_consumed()
        eff = 1.0 if used <= total else max(0.3, total / max(1, used))
        for c in COMPARTMENTS:
            for m in self.compartments[c]["modules"]:
                if m.active and not m.is_broken():
                    for k in stats:
                        stats[k] += m.stats.get(k, 0) * eff
        # Apply upgrade bonuses
        for bonus_key, stat_key in UPGRADE_STAT_MAP.items():
            stats[stat_key] += self._upgrade_bonus(bonus_key, 0)
        # Apply crew bonuses
        for bonus_key, stat_key in CREW_STAT_MAP.items():
            stats[stat_key] += self._crew_bonus(bonus_key, 0)
        return {k: int(v) for k, v in stats.items()}

    def check_missions(self, station):
        """Check if any mission targets this station. Returns list of (mission, msg)."""
        completed = []
        for m in self.missions:
            if m.mtype == "deliver" and m.target_station == station.name:
                if self.cargo.has(m.resource) >= m.amount:
                    self.cargo.remove(m.resource, m.amount)
                    self.credits += m.reward
                    m.status = "completed"
                    completed.append((m, f"Mission complete! Delivered {m.amount} {m.resource} to {station.name}. +{m.reward}cr"))
        for m, _ in completed:
            self.missions.remove(m)
        return completed

    MAX_MISSIONS = 5

    def add_mission(self, mission):
        """Accept a mission. Returns (message, success)."""
        if len(self.missions) >= self.MAX_MISSIONS:
            return "Mission log full (max 5).", False
        if mission.id in (m.id for m in self.missions):
            return "Already have this mission.", False
        mission.status = "active"
        self.missions.append(mission)
        return f"Accepted: {mission.title}", True

    def abandon_mission(self, mission_id):
        """Abandon a mission by id. Returns (message, success)."""
        for m in self.missions:
            if m.id == mission_id:
                m.status = "abandoned"
                self.missions.remove(m)
                if m.giver_station:
                    penalty = -10
                    self.reputation[m.giver_station.faction] = \
                        self.reputation.get(m.giver_station.faction, 0) + penalty
                return f"Abandoned: {m.title}. Reputation penalty applied.", True
        return "Mission not found.", False

    def track_mission(self, mission_id):
        """Set tracked mission. Returns mission or None."""
        for m in self.missions:
            if m.id == mission_id:
                self.tracked_mission = mission_id
                return m
        self.tracked_mission = None
        return None

    def has_mission(self, mission_id):
        return any(m.id == mission_id for m in self.missions)

    def fail_expired_missions(self, galaxy_news):
        """Tick deadlines, fail expired missions. Returns list of fail messages."""
        failed = []
        for m in list(self.missions):
            if m.status != "active":
                continue
            m.ticks -= 1
            if m.ticks <= 0:
                m.status = "failed"
                self.missions.remove(m)
                failed.append(m)
                if galaxy_news is not None:
                    galaxy_news.append(NewsEntry("MISSION FAILED", m.title))
        return failed

    def scan_target(self, target, scan_type="active", galaxy=None):
        """Scan a target object. Returns ScanResult."""
        from config import SCAN_ACTIVE_COST, SCAN_DEEP_COST
        cost = SCAN_DEEP_COST if scan_type == "deep" else SCAN_ACTIVE_COST
        if self._crew_bonus("scanner", 0):
            cost = max(1, cost - self._crew_bonus("scanner", 0) // 5)
        if scan_type != "passive":
            spare = self.total_power_generated() - self.total_power_consumed()
            if spare < cost:
                return ScanResult(False, info={"error": f"Need {cost} spare power (have {spare})."})
        sensor_range = self.get_effective_stats().get("sensor_range", 5)
        rng_map = {"active": sensor_range * 2, "deep": sensor_range, "passive": sensor_range}
        rng = rng_map.get(scan_type, sensor_range)
        # Build info dict
        info = {"type": type(target).__name__, "scanned": True, "scan_level": scan_type}
        if hasattr(target, "hull"):
            info["hull"] = target.hull
            info["max_hull"] = getattr(target, "max_hull", target.hull)
        if hasattr(target, "shield_hp"):
            info["shield"] = target.shield_hp
        if hasattr(target, "cargo") and scan_type in ("active", "deep"):
            info["cargo"] = dict(target.cargo.items) if hasattr(target.cargo, "items") else {}
        if hasattr(target, "compartments") and scan_type == "deep":
            comps = {}
            for c in COMPARTMENTS:
                mods = target.compartments[c]["modules"]
                comps[c] = [{"name": m.name, "dur": m.durability, "max": m.max_durability, "broken": m.is_broken()} for m in mods]
            info["compartments"] = comps
        if hasattr(target, "name"):
            info["name"] = target.name
        if hasattr(target, "faction"):
            info["faction"] = target.faction
        # Mark target as scanned
        if hasattr(target, "scanned"):
            target.scanned = True
        if hasattr(target, "scan_level"):
            target.scan_level = scan_type
        # Check if scanning generates a mission
        generated_mission = None
        if galaxy and scan_type in ("active", "deep"):
            generated_mission = galaxy.scan_generate_missions(target, scan_type, self)
        return ScanResult(True, scan_type, info, scanned_obj=target)

    def install_module(self, mod_id: str) -> bool:
        info = SHIP_MODULES.get(mod_id)
        if not info:
            return False
        comp = info.get("comp", "reactor")
        if comp not in self.compartments:
            return False
        self.compartments[comp]["modules"].append(ShipModule(mod_id))
        return True

# ---------------------------------------------------------------------------
# NPC ships
# ---------------------------------------------------------------------------

NPCShip_id_counter = 0

class NPCShip:
    def __init__(self, x, y, name, hull, faction, race=None, cc=100):
        global NPCShip_id_counter
        NPCShip_id_counter += 1
        self.uid = NPCShip_id_counter
        self.x, self.y = x, y
        self.name = name
        self.hull = hull
        self.max_hull = hull
        self.shield_hp = 0
        self.faction = faction
        self.race = race or random.choice(list(RACES))
        self.cargo = CargoHold(cc)
        self.credits = 500
        self.alive = True
        self.scanned = False
        self.scan_level = None

    def take_damage(self, amount):
        if self.shield_hp > 0:
            absorbed = min(self.shield_hp, amount)
            self.shield_hp -= absorbed
            amount -= absorbed
        if amount > 0:
            self.hull = max(0, self.hull - amount)
        if self.hull <= 0:
            self.alive = False
        return self.alive

class TraderShip(NPCShip):
    NAMES = ["Hornet","Mercury","Venture","Polaris","Comet","Drifter","Nomad"]
    def __init__(self, x, y, route):
        name = random.choice(self.NAMES) + str(random.randint(1, 99))
        faction = random.choice(["free_traders", "imperium", "machine_collective"])
        super().__init__(x, y, name, 60, faction, None, 100)
        self.shield_hp = 20
        self.route = route
        self.route_index = 0
        self.cargo.add("fuel_cell", 20)
        self.cargo.add("electronics", random.randint(3, 8))
        self.cargo.add("metal", random.randint(5, 15))
        self.credits = random.randint(200, 600)
        self.wait_ticks = 0

    def current_target(self, stations):
        if not self.route or not stations:
            return None
        idx = self.route[self.route_index % len(self.route)]
        if 0 <= idx < len(stations):
            return stations[idx]
        return None

class PirateShip(NPCShip):
    NAMES = ["Raider","Reaver","Corsair","Buccaneer","Scourge","Viper","Wraith"]
    def __init__(self, x, y):
        name = random.choice(self.NAMES) + str(random.randint(1, 99))
        faction = random.choice(["chaos_cult", "xenos_horde"])
        super().__init__(x, y, name, 40, faction, None, 30)
        self.shield_hp = 10
        self.credits = random.randint(50, 150)
        self.aggro_range = 5
        self.flee_threshold = 8

# ---------------------------------------------------------------------------
# Station
# ---------------------------------------------------------------------------

DESIRED_STOCK = 20

class Station:
    NAMES = ["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Theta",
             "Nova","Prime","Sol","Haven","Forge"]

    def __init__(self, x, y, name=None, stype=None, faction=None):
        self.x, self.y = x, y
        self.name = name or random.choice(self.NAMES)
        stype_choices = list(STATION_TYPES)
        self.stype = stype or random.choice(stype_choices)
        self.faction = faction or random.choice(list(FACTIONS))
        self.religion = None
        self.inventory: dict[str, int] = {}
        self.prices: dict[str, tuple[int, int]] = {}
        self.crisis_ticks = 0
        self.price_history: dict[str, list] = {r: [] for r in RESOURCES}
        self.missions: list = []
        self.modules_for_sale: list[str] = []
        self.hulls_for_sale: list[str] = []    # shipyard
        self.recipes_available: list[str] = []  # workshop
        self.crew_for_hire: list = []           # tavern
        self.scanned = False
        self._init_inventory()
        self._init_modules()
        self._init_type_specific()
        self.update_prices()

    def _init_type_specific(self):
        """Init station-type-specific offerings."""
        st_cfg = STATION_TYPES.get(self.stype, {})
        if self.stype == "shipyard":
            hulls = st_cfg.get("hulls", [])
            # Filter a subset of hulls based on faction/random
            self.hulls_for_sale = random.sample(hulls, min(random.randint(2, 4), len(hulls)))
        elif self.stype == "workshop":
            recipes = st_cfg.get("recipes", [])
            self.recipes_available = random.sample(recipes, min(random.randint(2, 4), len(recipes)))
        elif self.stype == "tavern":
            slots = st_cfg.get("crew_slots", 3)
            specs = list(CREW_SPECIALTIES)
            for _ in range(random.randint(1, slots)):
                name = random.choice(CREW_NAMES) + str(random.randint(1, 99))
                spec = random.choice(specs)
                self.crew_for_hire.append(CrewMember(name, spec))

    def _init_inventory(self):
        for r in RESOURCES:
            self.inventory[r] = random.randint(8, 25)

    def _init_modules(self):
        import random
        from config import SHIP_MODULES
        available = list(SHIP_MODULES)
        # Exclude starter modules
        starter = {"fusion_reactor", "ion_drive", "deflector_shield", "long_range_scanner"}
        pool = [m for m in available if m not in starter]
        count = random.randint(2, 5)
        self.modules_for_sale = random.sample(pool, min(count, len(pool)))

    def gen_missions(self, all_stations):
        """Generate deliver missions to other stations."""
        others = [s for s in all_stations if s.name != self.name]
        if not others or len(self.missions) >= 4:
            return
        target = random.choice(others)
        et = random.choice(["deliver", "deliver", "bounty"])
        if et == "deliver":
            rid = random.choice(list(RESOURCES))
            amt = random.randint(3, 8)
            price = RESOURCES[rid]["base_price"]
            reward = price * amt * random.randint(2, 4)
            desc = f"Deliver {amt}x {RESOURCES[rid]['name']} to {target.name}."
            m = Mission("deliver", rid, amt, target.name, reward,
                       random.randint(20, 40), title=desc[:44],
                       description=desc, giver_station=self)
        else:  # bounty
            bounty = random.randint(3, 6) * 50
            desc = f"Hunt pirates near {self.name}. Reward: {bounty}cr."
            m = Mission("bounty", "credits", 1, self.name, bounty,
                       random.randint(15, 30), title=desc[:44],
                       description=desc, giver_station=self)
        self.missions.append(m)

    def update_prices(self):
        for rid, info in RESOURCES.items():
            stock = self.inventory.get(rid, 0)
            base = info["base_price"]
            if stock < 4:
                factor = 2.5
            elif stock < 10:
                factor = 1.8
            elif stock > 40:
                factor = 0.5
            else:
                factor = max(0.6, min(1.5, 20 / max(1, stock)))
            bp = int(base * factor * 0.85)
            sp = int(base * factor * 1.15)
            self.prices[rid] = (max(1, bp), max(1, sp))
            self.price_history[rid].append((bp, sp))
            if len(self.price_history[rid]) > 20:
                self.price_history[rid] = self.price_history[rid][-20:]

    def update_economy(self):
        if self.crisis_ticks > 0:
            self.crisis_ticks -= 1
            return
        ti = {
            "trade_hub":  {"consume": {"ice": 1},          "produce": {"electronics": 1}},
            "industrial": {"consume": {"ore": 2, "ice": 1},"produce": {"metal": 2}},
            "research":   {"consume": {"electronics": 1},  "produce": {"shield_mod": 1}},
            "temple":     {"consume": {"relic": 1},        "produce": {"shield_mod": 1}},
        }.get(self.stype, {})
        for r, a in ti.get("consume", {}).items():
            if r in self.inventory:
                self.inventory[r] = max(0, self.inventory[r] - a)
        for r, a in ti.get("produce", {}).items():
            self.inventory[r] = self.inventory.get(r, 0) + a
        self.update_prices()

    def price_for_player(self, rid, buying, ship):
        """Return (adjusted_price, notes) for a player trade."""
        if rid not in self.prices:
            return 0, ""
        bp, sp = self.prices[rid]
        rep = ship.reputation.get(self.faction, 0)
        notes = []
        if buying:
            price = sp
            if rep > 50:
                price = int(price * 0.9); notes.append("friend -10%")
            elif rep < -20:
                price = int(price * 1.5); notes.append("hostile +50%")
        else:
            price = bp
            if rep > 50:
                price = int(price * 1.1); notes.append("friend +10%")
            elif rep < -20:
                price = int(price * 0.7); notes.append("hostile -30%")
        tb = 1 + ship.skill_trade * 0.02
        price = int(price / tb) if buying else int(price * tb)
        return max(1, price), " ".join(notes)

    def buy_from(self, ship, rid, amount):
        """Station buys from ship (player sells)."""
        info = RESOURCES.get(rid)
        if not info:
            return f"Unknown '{rid}'."
        rep = ship.reputation.get(self.faction, 0)
        if rep < -20 and self.faction != "pirates":
            return f"Trade blocked (rep {rep})."
        if ship.cargo.has(rid) < amount:
            return f"Not enough {info['name']}."
        banned = CONTRABAND.get(self.faction, []) + CONTRABAND.get(self.religion, [])
        if rid in banned and rep >= -20:
            return f"Contraband! Use smuggle."
        price, _ = self.price_for_player(rid, False, ship)
        total = price * amount
        if not ship.cargo.remove(rid, amount):
            return "Cargo error."
        ship.credits += total
        self.inventory[rid] = self.inventory.get(rid, 0) + amount
        return f"Sold {amount} {info['name']} for {total}cr."

    def sell_to(self, ship, rid, amount):
        """Station sells to ship (player buys)."""
        info = RESOURCES.get(rid)
        if not info:
            return f"Unknown '{rid}'."
        rep = ship.reputation.get(self.faction, 0)
        if rep < -20 and self.faction != "pirates":
            return f"Trade blocked (rep {rep})."
        if self.inventory.get(rid, 0) < amount:
            return f"Only {self.inventory.get(rid, 0)} {info['name']}."
        price, _ = self.price_for_player(rid, True, ship)
        total = price * amount
        if ship.credits < total:
            return f"Need {total}, have {ship.credits}."
        if not ship.cargo.add(rid, amount):
            return "Cargo full."
        ship.credits -= total
        self.inventory[rid] -= amount
        return f"Bought {amount} {info['name']} for {total}cr."

    def price_summary(self):
        parts = []
        for rid in sorted(RESOURCES):
            if self.inventory.get(rid, 0) > 0:
                _, sp = self.prices.get(rid, (0, 0))
                parts.append(f"{rid}:{sp}")
        return f"  {self.name}[{self.stype}] {self.faction}: {','.join(parts[:5])}"

    def buy_all_junk(self, ship):
        """Buy all raw resources from player. Returns summary message."""
        total_credits = 0
        sold_items = []
        for rid, amt in list(ship.cargo.items.items()):
            info = RESOURCES.get(rid, {})
            if info.get("cat") == "raw":
                price, _ = self.price_for_player(rid, False, ship)
                t = price * amt
                if ship.cargo.remove(rid, amt):
                    ship.credits += t
                    total_credits += t
                    sold_items.append(f"{amt}x {info.get('name', rid)}")
                    self.inventory[rid] = self.inventory.get(rid, 0) + amt
        if not sold_items:
            return "No raw resources to sell.", False
        return f"Sold {', '.join(sold_items)} for {total_credits}cr.", True

# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class GameEvent:
    def __init__(self, name, description, duration=0):
        self.name = name
        self.description = description
        self.duration = duration

class NewsEntry:
    def __init__(self, headline, body, turn=0):
        self.headline = headline
        self.body = body
        self.turn = turn

class Mission:
    _id_counter = 0

    def __init__(self, mtype, resource, amount, target_station, reward, ticks=30,
                 title="", description="", giver_station=None):
        Mission._id_counter += 1
        self.id = Mission._id_counter
        self.mtype = mtype  # "deliver", "bounty", "exploration", "trade"
        self.resource = resource
        self.amount = amount
        self.target_station = target_station  # station name string
        self.reward = reward
        self.ticks = ticks  # remaining turns (deadline)
        self.status = "active"  # active, completed, failed, abandoned
        self.progress = 0  # e.g. how much already delivered
        self.title = title or f"{mtype.title()}: {amount}x {resource}"
        self.description = description or f"Deliver {amount} {resource} to {target_station}."
        self.giver_station = giver_station  # Station object or None

    def is_expired(self):
        return self.ticks <= 0 and self.status == "active"

    def check_completion(self, ship):
        """Returns True if mission objective is met."""
        if self.status != "active":
            return False
        if self.mtype == "deliver":
            return self.progress >= self.amount
        return False

# ---------------------------------------------------------------------------
# Galaxy
# ---------------------------------------------------------------------------

class Galaxy:
    def __init__(self, width=WIDTH, height=HEIGHT, seed=None):
        self.width = width
        self.height = height
        self.seed = seed if seed is not None else random.randint(0, 999999)
        random.seed(self.seed)

        self.tiles = [[TILE_EMPTY for _ in range(width)] for _ in range(height)]
        self.objects: dict = {}
        self.stations: list[Station] = []
        self.traders: list[TraderShip] = []
        self.pirates: list[PirateShip] = []
        self.events_queue: list[GameEvent] = []
        self.global_crisis_ticks = 0
        self.diplomacy: dict = {}
        self.news: list[NewsEntry] = []
        self.tick_counter = 0

        self._init_diplomacy()
        self.news.append(NewsEntry("Galaxy News", "A vast galaxy awaits…"))
        self._generate()

        self.black_holes = [p for p, o in self.objects.items() if o == "black_hole"]
        self.wormholes = [p for p, o in self.objects.items() if o == "wormhole"]

    def _init_diplomacy(self):
        defaults = {
            "imperium":  {"chaos_cult":"war","xenos_horde":"war","machine_collective":"neutral",
                          "free_traders":"neutral","void_covenant":"war"},
            "chaos_cult": {"imperium":"war","xenos_horde":"war","machine_collective":"war",
                           "free_traders":"neutral","void_covenant":"alliance"},
            "xenos_horde":{"imperium":"war","chaos_cult":"war","machine_collective":"war",
                           "free_traders":"neutral","void_covenant":"war"},
            "machine_collective":{"imperium":"neutral","chaos_cult":"war","xenos_horde":"war",
                                  "free_traders":"neutral","void_covenant":"war"},
            "free_traders":{"imperium":"neutral","chaos_cult":"neutral","xenos_horde":"neutral",
                            "machine_collective":"neutral","void_covenant":"neutral"},
            "void_covenant":{"imperium":"war","chaos_cult":"alliance","xenos_horde":"war",
                             "machine_collective":"war","free_traders":"war"},
        }
        self.diplomacy = {f: dict(d) for f, d in defaults.items()}

    # ---- Generation helpers ----

    def _random_passable(self):
        for _ in range(500):
            x, y = random.randint(0, self.width - 1), random.randint(0, self.height - 1)
            if self.tiles[y][x] == TILE_EMPTY and (x, y) not in self.objects:
                return x, y
        return random.randint(0, self.width - 1), random.randint(0, self.height - 1)

    def _random_passable_near(self, obj_type, spread=5):
        cand = [p for p, o in self.objects.items() if o == obj_type]
        if not cand:
            return self._random_passable()
        cx, cy = random.choice(cand)
        for _ in range(100):
            dx, dy = random.randint(-spread, spread), random.randint(-spread, spread)
            nx, ny = cx + dx, cy + dy
            if (0 <= nx < self.width and 0 <= ny < self.height
                    and self.tiles[ny][nx] == TILE_EMPTY):
                return nx, ny
        return self._random_passable()

    # ---- Generation ----

    def _generate(self):
        for y in range(self.height):
            for x in range(self.width):
                if random.random() < 0.025:
                    self.tiles[y][x] = TILE_STAR
                    self.objects[(x, y)] = "star"
                    if random.random() < 0.2:
                        px, py = self._nearby(x, y)
                        if self.tiles[py][px] == TILE_EMPTY:
                            self.tiles[py][px] = TILE_PLANET
                            self.objects[(px, py)] = "planet"
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y][x] == TILE_EMPTY and random.random() < 0.01:
                    self.tiles[y][x] = TILE_STATION
                    self.objects[(x, y)] = "station"
                    self.stations.append(Station(x, y))
        for _ in range(int(self.width * self.height * 0.0025)):
            x, y = random.randint(0, self.width - 1), random.randint(0, self.height - 1)
            if self.tiles[y][x] == TILE_EMPTY:
                self.tiles[y][x] = TILE_BLACK_HOLE
                self.objects[(x, y)] = "black_hole"
        for _ in range(int(self.width * self.height * 0.0015)):
            x, y = random.randint(0, self.width - 1), random.randint(0, self.height - 1)
            if self.tiles[y][x] == TILE_EMPTY:
                self.tiles[y][x] = TILE_WORMHOLE
                self.objects[(x, y)] = "wormhole"
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y][x] == TILE_EMPTY and random.random() < 0.015:
                    self.tiles[y][x] = TILE_ASTEROIDS
                    self.objects[(x, y)] = "asteroids"
        # Replace generic ships with NPCs
        self.objects = {k: v for k, v in self.objects.items() if v != "ship"}
        # Traders
        if self.stations:
            for _ in range(random.randint(8, 12)):
                x, y = self._random_passable()
                route = random.sample(
                    range(len(self.stations)),
                    min(random.randint(3, 5), len(self.stations)),
                )
                self.traders.append(TraderShip(x, y, route))
        # Pirates
        for _ in range(random.randint(3, 5)):
            x, y = self._random_passable_near("asteroids", 5)
            self.pirates.append(PirateShip(x, y))
        # Generate missions
        for s in self.stations:
            s.gen_missions(self.stations)

    @staticmethod
    def _nearby(x, y, md=2):
        return (
            max(0, min(WIDTH - 1, x + random.randint(-md, md))),
            max(0, min(HEIGHT - 1, y + random.randint(-md, md))),
        )

    # ---- Queries ----

    def get_tile(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return " "

    def get_object_info(self, x, y):
        for t in self.traders:
            if t.alive and t.x == x and t.y == y:
                return f"Trader {t.name}[{t.faction}]"
        for p in self.pirates:
            if p.alive and p.x == x and p.y == y:
                return f"Pirate {p.name}[{p.faction}]"
        obj = self.objects.get((x, y))
        if obj:
            n = {"star": "Star", "planet": "Planet", "station": "Station",
                 "black_hole": "Black Hole", "wormhole": "Wormhole",
                 "asteroids": "Asteroids"}.get(obj, obj.title())
            s = self.get_station_at(x, y)
            if s:
                n += f" {s.name}[{s.faction}]"
            return n
        return "Empty"

    def is_passable(self, x, y):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        return self.tiles[y][x] not in (TILE_STAR, TILE_BLACK_HOLE)

    def get_station_at(self, x, y):
        for s in self.stations:
            if s.x == x and s.y == y:
                return s
        return None

    def get_nearest_station(self, x, y, md=1):
        for s in self.stations:
            if max(abs(s.x - x), abs(s.y - y)) <= md:
                return s
        return None

    def get_npc_at(self, x, y):
        for t in self.traders:
            if t.alive and t.x == x and t.y == y:
                return t
        for p in self.pirates:
            if p.alive and p.x == x and p.y == y:
                return p
        return None

    def get_npc_by_name(self, name):
        for t in self.traders:
            if t.alive and t.name.lower() == name.lower():
                return t
        for p in self.pirates:
            if p.alive and p.name.lower() == name.lower():
                return p
        return None

    def add_news(self, headline, body):
        self.news.append(NewsEntry(headline, body, self.tick_counter))
        if len(self.news) > 50:
            self.news = self.news[-50:]

    def stations_in_range(self, x, y, r):
        return [s for s in self.stations if max(abs(s.x - x), abs(s.y - y)) <= r]

    def get_scannable_objects(self, x, y, radius):
        """Return list of (distance, label, object) within radius."""
        results = []
        for p in self.pirates:
            if p.alive:
                d = max(abs(p.x - x), abs(p.y - y))
                if d <= radius:
                    results.append((d, f"☠ Pirate {p.name}", p))
        for t in self.traders:
            if t.alive:
                d = max(abs(t.x - x), abs(t.y - y))
                if d <= radius:
                    results.append((d, f"T Trader {t.name}", t))
        for s in self.stations:
            d = max(abs(s.x - x), abs(s.y - y))
            if d <= radius:
                results.append((d, f"◈ Station {s.name}", s))
        results.sort(key=lambda x: x[0])
        return results

    def scan_generate_missions(self, target, scan_type, player_ship):
        """Scan may reveal hidden missions. Returns a Mission or None."""
        if not hasattr(target, "name"):
            return None
        from config import SCAN_SIGNAL_TYPES
        sig_type = random.choice(list(SCAN_SIGNAL_TYPES))
        cfg = SCAN_SIGNAL_TYPES[sig_type]
        if random.random() * 100 > cfg["weight"]:
            return None
        # Generate a title giver string
        giver_label = f"Scan: {cfg['title']} @ {target.name}"
        mission_types = cfg["missions"]
        mt = random.choice(mission_types)
        # Craft a simple mission
        rid = random.choice(list(RESOURCES))
        amt = random.randint(1, 5)
        reward = amt * RESOURCES[rid]["base_price"] * random.randint(3, 6)
        from config import FACTIONS
        target_station_name = target.name if hasattr(target, "name") else "Unknown"
        m = Mission(mt if mt in ("deliver", "bounty") else "deliver",
                     rid, amt, target_station_name, reward, random.randint(20, 40),
                     title=f"{cfg['title']} @ {target.name}",
                     description=f"Discovered via {scan_type} scan of {target.name}.",
                     giver_station=giver_label)
        return m

    def reset_npc_counter(self):
        global NPCShip_id_counter
        NPCShip_id_counter = 0

    # ---- World tick ----

    def tick(self, px, py, ps):
        events = []
        # Black holes
        for bh_x, bh_y in self.black_holes:
            d = max(abs(px - bh_x), abs(py - bh_y))
            if d == 0:
                events.append("Black hole!")
                return px, py, events, True
            if d <= 3:
                dx = 1 if bh_x > px else -1 if bh_x < px else 0
                dy = 1 if bh_y > py else -1 if bh_y < py else 0
                nx, ny = px + dx, py + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    px, py = nx, ny
                    events.append("Gravity pull!")
                    if self.tiles[py][px] == TILE_BLACK_HOLE:
                        events.append("Black hole!")
                        return px, py, events, True
        # Star radiation
        for y in range(max(0, py - 1), min(self.height, py + 2)):
            for x in range(max(0, px - 1), min(self.width, px + 2)):
                if self.tiles[y][x] == TILE_STAR and (x != px or y != py):
                    dmg = 10
                    if hasattr(ps, 'race') and ps.race == "mutant":
                        dmg = int(dmg * 0.5)
                    if not getattr(ps, 'radiation_shield', False):
                        ps.take_damage(dmg)
                        events.append(f"Radiation -{dmg}!")
                        if ps.hull <= 0:
                            return px, py, events, True
        # Asteroids
        if self.tiles[py][px] == TILE_ASTEROIDS and random.random() < 0.3:
            ps.take_damage(5)
            events.append("Asteroid -5!")
            if ps.hull <= 0:
                return px, py, events, True
        # Station economy
        for s in self.stations:
            s.update_economy()
        return px, py, events, False

    # ---- NPC step ----

    def step_npc(self, px, py, ps, out):
        for t in self.traders:
            if not t.alive:
                continue
            tg = t.current_target(self.stations)
            if not tg:
                continue
            if t.x == tg.x and t.y == tg.y:
                t.wait_ticks = random.randint(2, 5) if t.wait_ticks <= 0 else t.wait_ticks - 1
                if t.wait_ticks <= 0:
                    t.route_index += 1
                continue
            self._move_towards(t, tg.x, tg.y)
            if max(abs(t.x - px), abs(t.y - py)) <= 1:
                out.append(f"Trader {t.name} nearby.")
        for p in self.pirates:
            if not p.alive:
                continue
            targets = []
            if max(abs(p.x - px), abs(p.y - py)) <= p.aggro_range:
                targets.append((px, py, "player"))
            for t in self.traders:
                if t.alive and max(abs(p.x - t.x), abs(p.y - t.y)) <= p.aggro_range:
                    targets.append((t.x, t.y, "trader"))
            if targets:
                tx, ty, tt = min(targets, key=lambda c: max(abs(p.x - c[0]), abs(p.y - c[1])))
                if max(abs(p.x - tx), abs(p.y - ty)) == 1:
                    if tt == "player":
                        out.append(f"__BATTLE__:{p.uid}")
                    else:
                        for t2 in self.traders:
                            if t2.alive and t2.x == tx and t2.y == ty:
                                t2.take_damage(15)
                                out.append(f"Pirate attacks {t2.name}!")
                                if not t2.alive:
                                    out.append(f"{t2.name} destroyed.")
                                break
                else:
                    self._move_towards(p, tx, ty)
            elif random.random() < 0.3:
                self._random_move(p)
            if p.hull <= p.flee_threshold:
                dx = px - p.x
                fx = p.x - (1 if dx > 0 else -1 if dx < 0 else 0)
                if self.is_passable(fx, p.y):
                    p.x = fx

    def _move_towards(self, npc, tx, ty):
        dx = 1 if tx > npc.x else -1 if tx < npc.x else 0
        dy = 1 if ty > npc.y else -1 if ty < npc.y else 0
        if dx != 0 and self.is_passable(npc.x + dx, npc.y) and not self._occupied(npc.x + dx, npc.y):
            npc.x += dx
        elif dy != 0 and self.is_passable(npc.x, npc.y + dy) and not self._occupied(npc.x, npc.y + dy):
            npc.y += dy
        else:
            self._random_move(npc)

    def _random_move(self, npc):
        for dx, dy in random.sample([(1, 0), (-1, 0), (0, 1), (0, -1)], 4):
            nx, ny = npc.x + dx, npc.y + dy
            if self.is_passable(nx, ny) and not self._occupied(nx, ny):
                npc.x, npc.y = nx, ny
                return

    def _occupied(self, x, y):
        for t in self.traders:
            if t.alive and t.x == x and t.y == y:
                return True
        for p in self.pirates:
            if p.alive and p.x == x and p.y == y:
                return True
        return (x, y) in self.objects
