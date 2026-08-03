"""Coverage tests — battle gaps (2026-08-03)."""

import random

from battle import BattleController, BattleScreen, BATTLE_SKILLS, _bar_s
from models import PirateShip, create_random_ship


def _bc(**kw):
    p = create_random_ship(is_player=True)
    e = PirateShip(1, 1)
    bc = BattleController(p, e, app=None)
    return bc, p, e


def _first_weapon(bc):
    return bc._get_player_weapons()[0]


# =============================================================================
# do_attack branches
# =============================================================================

def test_attack_no_weapons():
    bc, p, e = _bc()
    bc.player.compartments["weapon"]["modules"] = []
    bc.do_attack(0, "shield")
    from locales import t
    assert t("battle.no_weapons") in bc.log


def test_attack_out_of_ammo():
    bc, p, e = _bc()
    kw = _first_weapon(bc)
    kw.weapon_class = "kinetic"
    kw.ammo_capacity = 20
    kw.current_ammo = 0
    bc.do_attack(0, "shield")
    from locales import t
    assert t("battle.out_of_ammo", name=kw.name) in bc.log


def test_attack_not_enough_energy():
    bc, p, e = _bc()
    bc.player_energy = 0
    bc.do_attack(0, "shield")
    from locales import t
    assert t("battle.need_energy", cost=bc._get_player_weapons()[0].energy_consumption,
             name=bc._get_player_weapons()[0].name, have=0) in bc.log


def test_attack_miss():
    bc, p, e = _bc()
    kw = _first_weapon(bc)
    kw.stats["accuracy"] = 5
    p.cargo.capacity = 200
    random.seed(1)
    bc.do_attack(0, "shield")
    from locales import t
    assert t("battle.missed", name=kw.name) in bc.log


def test_attack_hits_hull_and_crit():
    bc, p, e = _bc()
    e.shield_hp = 0
    p.cargo.capacity = 200
    # ищем сид с попаданием и критом
    for seed in range(1, 300):
        bc2, p2, e2 = _bc()
        e2.shield_hp = 0
        random.seed(seed)
        bc2.do_attack(0, "shield")
        from locales import t
        if t("battle.critical") in bc2.log:
            assert any("→" in m for m in bc2.log)
            return
    assert False, "no crit seed found"


def test_attack_disruption():
    bc, p, e = _bc()
    kw = _first_weapon(bc)
    kw.weapon_class = "disruptor"
    e.shield_hp = 0
    initial = {m["name"]: m["dur"] for m in bc.enemy_comps["shield"]["modules"]}
    random.seed(42)
    bc.do_attack(0, "shield")
    # разрушитель бьёт по модулям напрямую
    damaged = any(m["dur"] < initial.get(m["name"], 0) for m in bc.enemy_comps["shield"]["modules"])
    assert damaged or any("Разрушитель" in m or "Disruptor" in m for m in bc.log)


def test_attack_ion_drain():
    bc, p, e = _bc()
    kw = _first_weapon(bc)
    kw.weapon_class = "ion"
    kw.loaded_ammo_type = "emp_charge"
    kw.ammo_capacity = 5
    kw.current_ammo = 5
    p.cargo.add("emp_charge", 10)
    random.seed(7)
    bc.do_attack(0, "shield")
    from locales import t
    assert any("Ион" in m or "Ion" in m for m in bc.log)


# =============================================================================
# do_skill branches
# =============================================================================

def test_skill_need_energy():
    bc, p, e = _bc()
    bc.player_energy = 0
    bc.do_skill("precise_shot")
    from locales import t
    assert t("battle.need_energy", cost=BATTLE_SKILLS["precise_shot"]["energy_cost"],
             name="Precise Shot", have=0) in bc.log


def test_skill_sensor_destroyed():
    bc, p, e = _bc()
    for m in p.compartments["sensor"]["modules"]:
        m.active = False
        m.durability = 0
    bc.do_skill("precise_shot")
    from locales import t
    assert t("battle.skill_unavailable", name="Precise Shot") in bc.log


def test_skill_overload_shields():
    bc, p, e = _bc()
    bc.player_energy = 50
    p.shield_hp = 10
    bc.do_skill("overload_shields")
    cap = p.get_effective_stats().get("shield_cap", 30)
    assert p.shield_hp == min(cap, 10 + int(cap * 0.3))


def test_skill_precise_shot():
    bc, p, e = _bc()
    bc.player_energy = 50
    e.hull = 40
    e.shield_hp = 0
    random.seed(3)
    bc.do_skill("precise_shot")
    assert any("Точный" in m or "Precise" in m for m in bc.log)


def test_skill_emergency_repair():
    bc, p, e = _bc()
    bc.player_energy = 50
    p.hull = 50
    bc.over = True  # не даём ходу врага сработать после навыка
    bc.do_skill("emergency_repair")
    assert p.hull == 80


# =============================================================================
# do_use_item — fuel/shield items
# =============================================================================

def test_use_item_energy_and_shield():
    bc, p, e = _bc()
    bc.over = True  # не даём ходу врага сработать
    bc.player_energy = 20
    p.cargo.add("fuel_cell", 1)
    bc.do_use_item("fuel_cell")
    assert bc.player_energy == 30
    p.shield_hp = 0
    p.cargo.add("shield_booster", 1)
    bc.do_use_item("shield_booster")
    cap = p.get_effective_stats().get("shield_cap", 0)
    assert p.shield_hp == min(cap, 15)


# =============================================================================
# do_reload branches
# =============================================================================

def test_reload_from_cargo_and_topped_up():
    bc, p, e = _bc()
    kw = _first_weapon(bc)
    kw.weapon_class = "kinetic"
    kw.ammo_capacity = 20
    kw.current_ammo = 0
    p.cargo.capacity = 200
    p.cargo.add("slug", 10)
    bc.do_reload()
    assert kw.current_ammo == 10
    # частичная догрузка
    p.cargo.add("slug", 10)
    bc.do_reload()
    assert kw.current_ammo == 20


def test_reload_all_loaded():
    bc, p, e = _bc()
    bc.do_reload()  # оружие заряжено по умолчанию
    from locales import t
    assert t("battle.all_loaded") in bc.log


# =============================================================================
# do_escape branches
# =============================================================================

def test_escape_engine_destroyed():
    bc, p, e = _bc()
    for m in p.compartments["engine"]["modules"]:
        m.active = False
        m.durability = 0
    bc.do_escape()
    from locales import t
    assert t("battle.engine_destroyed") in bc.log


def test_escape_succeeds():
    bc, p, e = _bc()
    # даём игроку максимум скорости, чтобы шанс побега был высоким
    for m in p.compartments["engine"]["modules"]:
        m.stats["speed"] = max(m.stats.get("speed", 1), 10)
    random.seed(1)  # random() = 0.134 < chance
    bc.do_escape()
    assert bc.over is True and bc.victory is False


# =============================================================================
# defeat handling
# =============================================================================

def test_on_enemy_defeated_with_app():
    class FakeLogger:
        def combat(self, msg):
            pass

    class FakeApp:
        logger = FakeLogger()
    bc, p, e = _bc()
    bc.app = FakeApp()
    bc.is_pirate = True
    bc._on_enemy_defeated()
    assert bc.over is True and bc.victory is True
    assert p.reputation["free_traders"] >= 2
    from locales import t
    assert any("уничтожен" in m or "destroyed" in m for m in bc.log)


def test_apply_outcome_quick_battle_returns():
    bc, p, e = _bc()
    bc.over = True
    bs = BattleScreen(bc, quick_battle=True)
    bs._apply_outcome()  # быстрый бой — ранний выход без побочных эффектов


# =============================================================================
# Rendering helpers
# =============================================================================

def test_bar_s():
    assert "█" in _bar_s(5, 10, 10)
    assert "░" in _bar_s(5, 10, 10)
    assert _bar_s(0, 0, 10)  # деление на ноль не падает


def test_compartment_status_strings():
    bc, p, e = _bc()
    from battle import _compartment_status_str, _player_comp_status_str
    comp = bc.enemy_comps["shield"]
    s1 = _compartment_status_str("shield", comp)
    assert "shield" in s1
    # уничтоженный отсек
    for m in comp["modules"]:
        m["active"] = False
        m["dur"] = 0
    s2 = _compartment_status_str("shield", comp)
    assert "DESTROYED" in s2 or "УНИЧТОЖЕН" in s2
    s3 = _player_comp_status_str("engine", p.compartments["engine"])
    assert isinstance(s3, str) and len(s3) > 0


def test_debug_enemy_status():
    bc, p, e = _bc()
    out = bc.debug_enemy_status()
    assert isinstance(out, str)
