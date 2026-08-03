"""Coverage tests — expedition screen & helpers (2026-08-03)."""

import pytest

from galaxy_map import GalaxyMapApp
from expedition import (
    ExpeditionMap, ExpeditionController, ExpeditionScreen,
    create_quick_expedition_character,
)
from models import CrewMember


def _make(map_type="station"):
    m = ExpeditionMap(20, 15, map_type)
    cm = CrewMember("Exped", "Pilot")
    ctrl = ExpeditionController(cm, m)
    return m, cm, ctrl


@pytest.mark.asyncio
async def test_expedition_screen_movement_and_menu():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        m, cm, ctrl = _make()
        screen = ExpeditionScreen(ctrl)
        app.push_screen(screen)
        await pilot.pause()
        await pilot.pause()
        assert app.screen is screen
        # движение
        x0, y0 = ctrl.px, ctrl.py
        await pilot.press("w")
        await pilot.pause()
        assert (ctrl.px, ctrl.py) != (x0, y0) or ctrl.crew.ap < ctrl.crew.max_ap
        # меню действий
        await pilot.press("space")
        await pilot.pause()
        assert screen._show_action_menu
        await pilot.press("1")  # атака
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()
        await pilot.press("2")  # лечение
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()
        await pilot.press("3")  # ожидание
        await pilot.pause()
        await pilot.press("space")
        await pilot.pause()
        await pilot.press("4")  # открыть дверь
        await pilot.pause()
        # выход по «5»
        await pilot.press("space")
        await pilot.pause()
        await pilot.press("5")
        await pilot.pause()
        assert ctrl.over is True
        # следующий ключ применяет результат и закрывает экран
        await pilot.press("w")
        await pilot.pause()
        assert app.screen is not screen or len(app.screen_stack) == 1


@pytest.mark.asyncio
async def test_expedition_screen_quick_mode_outcome():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        m, cm, ctrl = _make()
        ctrl.victory = True
        ctrl.crew.hp = 10
        screen = ExpeditionScreen(ctrl, quick_expedition=True)
        app.push_screen(screen)
        await pilot.pause()
        await pilot.pause()
        screen._apply_outcome()
        assert screen._quick_outcome is not None
        # смерть в быстром режиме
        ctrl.crew.hp = 0
        screen2 = ExpeditionScreen(ctrl, quick_expedition=True)
        screen2._apply_outcome()
        assert "died" in screen2._quick_outcome


@pytest.mark.asyncio
async def test_expedition_outcome_normal_transfers_cargo():
    app = GalaxyMapApp()
    async with app.run_test(size=(80, 44)) as pilot:
        m, cm, ctrl = _make()
        screen = ExpeditionScreen(ctrl)
        app.push_screen(screen)
        await pilot.pause()
        await pilot.pause()
        ctrl.victory = True
        cm.inventory["metal"] = 3
        screen._apply_outcome()
        assert app.ctrl.ship.cargo.has("metal") >= 3
        assert not cm.inventory


def test_create_quick_expedition_character():
    cm = create_quick_expedition_character()
    assert cm.hp == 100
    assert cm.ap == 10
    assert cm.combat_skill >= 50


def test_expedition_controller_heal_and_wait():
    m, cm, ctrl = _make()
    cm.hp = 20
    cm.inventory["repair_kit"] = 1
    ctrl.crew.ap = 4
    ctrl.heal()  # тратит 2 AP и ремкомплект
    assert cm.hp == cm.max_hp  # 20+15 упёрлись в max_hp (30)
    assert ctrl.crew.ap == 2
    ctrl.wait()
    assert ctrl.crew.ap == 0


def test_expedition_attack_and_death():
    m, cm, ctrl = _make()
    # ставим врага рядом
    e = m.enemies[0]
    e.x, e.y = ctrl.px + 1, ctrl.py
    cm.hp = 5  # слабый
    ctrl.crew.ap = 4
    ctrl.attack()
    # враг мог умереть или нанести ответный урон — без краша
    assert ctrl.crew.ap >= 0
