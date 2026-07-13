Ты — ведущий гейм-дизайнер и разработчик космической RPG-песочницы на Python (Textual).  
Игра находится в активной разработке. Текущая версия содержит:

- Генерацию галактики, перемещение игрока, NPC (торговцы, пираты), станции, бой.
- Базовую модульную систему: слоты (weapon, shield, engine, utility), модули с характеристиками, установку/снятие.
- Постоянные апгрейды корпуса (hull, cargo, сенсоры).
- Экипаж (задел — список членов, команда `crew`).
- Торговлю, экономику, репутацию, фракции.

Текущее управление кораблём рассеяно по консольным командам (`status`, `modules`, `install`, `repair`). Необходимо **спроектировать единую систему управления кораблём** с полноценными экранами, продумать строение корабля, роли модулей и их взаимодействие, вдохновляясь играми FTL, Starsector, Star Traders: Frontiers.

### Задача: создать дизайн-документ и код для следующих подсистем

#### 1. Архитектура корабля — «отсеки» и энергосистема

Корабль больше не плоский список слотов. Он разделён на **отсеки** (compartments), каждый из которых может содержать определённые модули и потреблять энергию.

- **Реакторный отсек** — генерирует энергию (базово 10 единиц). Модули: реактор (мощность), дополнительные генераторы.
- **Двигательный отсек** — определяет скорость перемещения по карте (сейчас 1 клетка/ход) и уклонение в бою. Модули: двигатели (увеличивают скорость, evasion).
- **Оружейный отсек** — вмещает оружие, влияет на damage, accuracy, скорострельность (пока не используется). Модули: лазеры, плазма, ракеты, турели.
- **Защитный отсек** — щиты и броня. Модули: генератор щита (ёмкость, регенерация), бронепластины (снижение урона по hull).
- **Сенсорный отсек** — радар, сканеры (радиус обзора, обнаружение скрытых объектов, экономический сканер).
- **Отсек жизнеобеспечения** — для экипажа (пока задел). Влияет на мораль, эффективность, потребляет ресурсы (food, oxygen).
- **Грузовой трюм** — объём, может расширяться модулями.

**Энергосистема**: реактор производит энергию. Каждый активный модуль потребляет энергию. Игрок может вручную распределять энергию между отсеками (аналог FTL) через инженерный экран. Если потребление превышает генерацию, эффективность систем падает пропорционально. При нуле энергии щиты отключаются, оружие не стреляет, скорость падает.

#### 2. Экраны управления кораблём

Внедрить в Textual-приложение многоэкранный интерфейс, вызываемый по клавишам:

- **F1 – Статус / Капитанский мостик**: сводка всех систем, тревоги, быстрые команды. Показывает hull, щиты, энергию, топливо, экипаж, текущие задания.
- **F2 – Инженерный экран**: схематичное изображение отсеков (можно ASCII-схему в отдельном виджете), распределение энергии ползунками/кнопками, состояние модулей (прочность модуля, возможность ремонта).
- **F3 – Тактический экран**: управление оружием (выбор активного оружия, режим стрельбы), состояние щитов, наведение на ближайшие цели (список целей в радиусе, выбор).
- **F4 – Трюм и снаряжение**: детальное управление грузом (таблица с фильтрами), установка/снятие модулей (drag-and-drop невозможно в консоли, но можно через меню).
- **F5 – Экипаж**: список членов, их навыки, назначение на посты (пилот, инженер, тактик, учёный), задания (ремонт, исследование). Пока реализовать заглушку «назначить на пост», приносящую бонус к соответствующему отсеку.
- **F6 – Миссии и контракты**: журнал заданий, торговые контракты, политические квесты.
- **F7 – Звёздная карта** (уже есть основная, можно добавить глобальный обзор с фракциями).
- **Escape** – вернуться к основной карте.

Каждый экран — наследник `Screen` с навигацией по клавишам, таблицами и формами.

#### 3. Консольные команды для управления

Дополнить существующий `CommandScreen` командами, дублирующими и расширяющими возможности экранов:

- `power set <compartment> <value>` – установить энергию на отсек.
- `power status` – текущее распределение.
- `modules list` – список всех установленных модулей по отсекам с состоянием.
- `modules repair <module_id>` – начать ремонт модуля (требует ресурсы и время).
- `target <enemy_name>` – выбрать цель для атаки.
- `fire` – атаковать выбранную цель.
- `crew assign <name> <station>` – назначить члена экипажа на пост.
- `bridge` – быстрый переход на капитанский мостик (F1).
- `engineering` – на инженерный экран (F2) и т.д.

#### 4. Проработка модулей и их функционал

Создать подробный справочник модулей (около 15–20 штук), разделённых по типам отсеков. Каждый модуль имеет:

- `id`, `name`, `description`.
- `compartment` (reactor, engine, weapon, shield, sensor, life_support, cargo).
- `energy_consumption` — сколько потребляет при активации.
- `stats` — словарь эффектов (например, `power_output`, `speed_bonus`, `damage`, `accuracy`, `shield_capacity`, `shield_regen`, `sensor_range`, `cargo_bonus`).
- `durability` — прочность (может получать повреждения в бою или при событиях).
- `cost` — цена покупки.

Примеры:

- Реактор: «Термоядерный реактор Mk1» — мощность 12, потребление 0, durability 100, стоимость 800.
- Двигатель: «Ионный двигатель» — speed +1, evasion +10, потребление 2.
- Оружие: «Лазерная турель» — damage 15, accuracy 80, потребление 3.
- Щит: «Дефлекторный экран» — shield +30, regen 2, потребление 4.
- Сенсор: «Дальний сканер» — range +5, потребление 2.
- Жизнеобеспечение: «Система рециркуляции» — снижает потребление еды/воды экипажем на 30%, потребление 1.
- Грузовой: «Грузовой модуль» — cargo +25.

Модули могут быть уникальными для фракций/религий (уже есть задел), их список дополнить.

#### 5. Интеграция с существующими механиками

- Боевая система должна использовать выбранное оружие и распределение энергии: если энергия на оружие ниже требуемой, урон и точность снижаются. Щиты без энергии не работают.
- При перемещении по галактике скорость зависит от мощности двигателей и текущей энергии. Если энергии недостаточно, скорость падает до 0.5 (движение раз в два тика).
- Ремонт модулей — через инженерный экран или команду: требует ресурсы (metal, electronics) и время (несколько тиков), экипаж может ускорять.
- Повреждения модулей: при получении удара по hull (после щитов) есть шанс повредить случайный модуль (снижение durability). Если durability=0, модуль отключается до ремонта.
- Сенсоры влияют на радиус экономического сканера (`market scan`), обнаружение скрытых пиратов, аномалий.

#### 6. Интерфейс в стиле Textual

- Использовать виджеты: `DataTable`, `ListView`, `Static`, `Input`, `Button`, `RadioSet`, `ProgressBar` (для энергии).
- Все экраны должны поддерживать клавиатурную навигацию (Tab, стрелки, Enter).
- Дизайн в тёмных тонах, соответствующей атмосфере (Warhammer 40k).

#### 7. Технические требования

- Реализовать описанные экраны как наследники `Screen`, подключить их к приложению.
- В классе `PlayerShip` заменить текущую систему слотов на словарь отсеков, каждый из которых содержит список модулей и текущую выделенную энергию.
- Добавить методы `distribute_power(compartment, amount)`, `get_effective_stats()`.
- Обновить консольные команды.
- Сохранить обратную совместимость: старая команда `status` продолжает работать, но может быть расширена.
- Выдать полный обновлённый файл `galaxy_map.py` или, если изменений много, — критические фрагменты (новые классы, экраны) с инструкцией по вставке.

Ответ должен содержать:

1. Дизайн-документ (краткое описание архитектуры корабля, экранов, модулей).
2. Код для:
   - класса `ShipCompartment` и `ShipModule` (переработанные).
   - новых экранов (хотя бы `BridgeScreen` и `EngineeringScreen`).
   - изменений в `PlayerShip` (отсеки, энергия).
   - обновлённого `CommandScreen` с новыми командами.
3. Примеры консольных команд и их эффекты.
4. Список модулей в формате Python-словаря (для конфига).
5. Инструкцию по интеграции (если код разбит на куски).

Ниже текущий код `galaxy_map.py`, в который необходимо внедрить эту систему.

```python
import random
from enum import Enum, auto
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Static, Header, Footer, Input, DataTable, Button
from textual.reactive import reactive
from textual import events

from game_logger import GameLogger, LogLevel

WIDTH, HEIGHT = 80, 40
TILE_EMPTY = "·"
TILE_STAR = "*"
TILE_PLANET = "o"
TILE_STATION = "☐"
TILE_TEMPLE = "⛪"
TILE_BLACK_HOLE = "◉"
TILE_WORMHOLE = "⭕"
TILE_ASTEROIDS = "░"
TILE_SHIP = "@"
TILE_OTHER_SHIP = "▲"
TILE_CURSOR = "◈"
TILE_TRADER = "T"
TILE_PIRATE = "P"

DIR_LABELS = {(-1,-1):"NW",(0,-1):"N",(1,-1):"NE",(-1,0):"W",(1,0):"E",(-1,1):"SW",(0,1):"S",(1,1):"SE"}

RESOURCES = {
    "ore":        {"name":"Ore","cat":"raw","base_price":5},
    "ice":        {"name":"Ice","cat":"raw","base_price":3},
    "silicon":    {"name":"Silicon","cat":"raw","base_price":8},
    "metal":      {"name":"Metal","cat":"refined","base_price":20},
    "electronics":{"name":"Electronics","cat":"refined","base_price":45},
    "fuel_cell":  {"name":"Fuel Cell","cat":"refined","base_price":30},
    "shield_mod": {"name":"Shield Mod","cat":"advanced","base_price":120},
    "relic":      {"name":"Alien Relic","cat":"special","base_price":500},
}

RACES = {
    "human":       {"name":"Human",     "desc":"Universal","rep_mod":{},"rad_resist":0.0,"bonus":""},
    "mutant":      {"name":"Mutant",    "desc":"Rad resist 50%","rep_mod":{},"rad_resist":0.5,"bonus":"organic"},
    "xenos_bio":   {"name":"Xenos Bio", "desc":"Organic bonus","rep_mod":{},"rad_resist":0.0,"bonus":"organic"},
    "machine_cult":{"name":"Machine",   "desc":"Auto-repair","rep_mod":{},"rad_resist":0.0,"bonus":"repair"},
    "voidborn":    {"name":"Voidborn",  "desc":"BH immune","rep_mod":{},"rad_resist":0.0,"bonus":"void"},
}

RELIGIONS = {
    "orthodox_church":{"name":"Orthodox Church","desc":"Trade bonus","modules":[],"rep_mod":{}},
    "cult_of_the_void":{"name":"Cult of Void","desc":"+dmg","modules":[],"rep_mod":{}},
    "machine_god":{"name":"Machine God","desc":"+repair","modules":[],"rep_mod":{}},
    "old_faith":{"name":"Old Faith","desc":"+mining","modules":[],"rep_mod":{}},
}

FACTIONS = {
    "imperium":{"name":"Imperium","desc":"Human empire"},
    "chaos_cult":{"name":"Chaos Cult","desc":"Warp cultists"},
    "xenos_horde":{"name":"Xenos Horde","desc":"Aggressive xenos"},
    "machine_collective":{"name":"Machine Collective","desc":"Machines"},
    "free_traders":{"name":"Free Traders","desc":"Neutral"},
    "void_covenant":{"name":"Void Covenant","desc":"Warp entities"},
}

CONTRABAND = {
    "imperium": ["relic"],
    "orthodox_church": ["relic"],
    "chaos_cult": ["shield_mod"],
    "free_traders": [],
}

class GameState(Enum):
    RACE_SELECT=auto(); START_SCREEN=auto(); PLAYING=auto(); PAUSED=auto()
    INTERACTING=auto(); INSPECTING=auto(); HELP=auto(); NEWS=auto(); GAME_OVER=auto()

class CargoHold:
    def __init__(self,capacity=50):
        self.capacity=capacity; self.items={}
    def used(self): return sum(self.items.values())
    def free(self): return max(0,self.capacity-self.used())
    def add(self,rid,amt):
        if self.free()<amt: return False
        self.items[rid]=self.items.get(rid,0)+amt; return True
    def remove(self,rid,amt):
        if self.items.get(rid,0)<amt: return False
        self.items[rid]-=amt
        if self.items[rid]<=0: del self.items[rid]
        return True
    def has(self,rid): return self.items.get(rid,0)
    def total_value(self):
        return sum(RESOURCES.get(r,{}).get("base_price",0)*a for r,a in self.items.items())

class PlayerShip:
    def __init__(self,name="Endeavour",hull=100):
        self.name=name; self.hull=hull; self.fuel=80; self.credits=1000
        self.radiation_shield=False; self.cargo=CargoHold(50)
        self.race="human"; self.religion=None
        self.reputation={f:0 for f in FACTIONS}
        self.reputation["pirates"]=-10
        self.modules=[]; self.skill_trade=0
    def take_damage(self,amt):
        self.hull=max(0,self.hull-amt); return self.hull>0

class NPCShip:
    _id_counter=0
    def __init__(self,x,y,name,hull,faction,race=None,cargo_capacity=100):
        NPCShip._id_counter+=1
        self.uid=NPCShip._id_counter; self.x=x; self.y=y
        self.name=name; self.hull=hull; self.max_hull=hull
        self.faction=faction; self.race=race or random.choice(list(RACES))
        self.cargo=CargoHold(cargo_capacity); self.credits=500; self.alive=True
    def take_damage(self,amt):
        self.hull=max(0,self.hull-amt)
        if self.hull<=0: self.alive=False
        return self.alive

class TraderShip(NPCShip):
    TRADER_NAMES=["Hornet","Mercury","Venture","Polaris","Comet","Drifter","Nomad"]
    def __init__(self,x,y,route):
        name=random.choice(self.TRADER_NAMES)+str(random.randint(1,99))
        f=random.choice(["free_traders","imperium","machine_collective"])
        super().__init__(x,y,name,60,f,None,100)
        self.route=route; self.route_index=0
        self.cargo.add("fuel_cell",20); self.cargo.add("electronics",random.randint(3,8))
        self.cargo.add("metal",random.randint(5,15)); self.credits=random.randint(200,600)
        self.wait_ticks=0
    def current_target(self,s): return s[self.route[self.route_index%len(self.route)]] if self.route and s else None

class PirateShip(NPCShip):
    PIRATE_NAMES=["Raider","Reaver","Corsair","Buccaneer","Scourge","Viper","Wraith"]
    def __init__(self,x,y):
        name=random.choice(self.PIRATE_NAMES)+str(random.randint(1,99))
        f=random.choice(["chaos_cult","xenos_horde"])
        super().__init__(x,y,name,40,f,None,30)
        self.credits=random.randint(50,150); self.target=None; self.aggro_range=5; self.flee_threshold=8

# ---------- Станция ----------
class Station:
    NAMES=["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Theta","Nova","Prime","Sol","Haven","Forge"]
    def __init__(self,x,y,name=None,stype=None,faction=None):
        self.x=x; self.y=y; self.name=name or random.choice(self.NAMES)
        self.stype=stype or random.choice(["trade_hub","industrial","research","temple"])
        self.faction=faction or random.choice(list(FACTIONS))
        self.religion=None
        self.inventory={}; self.prices={}; self.crisis_ticks=0
        self.price_history={r:[] for r in RESOURCES}
        self.missions=[]
        self._init_inventory(); self.update_prices()
    def _init_inventory(self):
        for r in RESOURCES: self.inventory[r]=random.randint(8,25)
    def update_prices(self):
        for rid,info in RESOURCES.items():
            stock=self.inventory.get(rid,0); base=info["base_price"]
            if stock<4: factor=2.5
            elif stock<10: factor=1.8
            elif stock>40: factor=0.5
            else: factor=max(0.6,min(1.5,20/max(1,stock)))
            b=int(base*factor*0.85); s=int(base*factor*1.15)
            self.prices[rid]=(max(1,b),max(1,s))
            self.price_history[rid].append((b,s))
            if len(self.price_history[rid])>20: self.price_history[rid]=self.price_history[rid][-20:]
    def update_economy(self):
        if self.crisis_ticks>0: self.crisis_ticks-=1; return
        ti={"trade_hub":{"consume":{"ice":1},"produce":{"electronics":1}},
            "industrial":{"consume":{"ore":2,"ice":1},"produce":{"metal":2}},
            "research":{"consume":{"electronics":1},"produce":{"shield_mod":1}},
            "temple":{"consume":{"relic":1},"produce":{"shield_mod":1}}}.get(self.stype,{})
        for rid,amt in ti.get("consume",{}).items():
            if rid in self.inventory: self.inventory[rid]=max(0,self.inventory[rid]-amt)
        for rid,amt in ti.get("produce",{}).items():
            self.inventory[rid]=self.inventory.get(rid,0)+amt
        self.update_prices()
    def price_for_player(self,rid,is_buying,ship):
        """Возвращает цену с учётом репутации, навыка, чёрного рынка."""
        if rid not in self.prices: return 0, ""
        bp,sp=self.prices[rid]
        price=bp if is_buying else sp
        notes=[]
        rep=ship.reputation.get(self.faction,0)
        if is_buying:
            price=sp  # station sells
            if rep>50: price=int(price*0.9); notes.append("friend -10%")
            elif rep<-20: price=int(price*1.5); notes.append("hostile +50%")
        else:
            price=bp  # station buys
            if rep>50: price=int(price*1.1); notes.append("friend +10%")
            elif rep<-20: price=int(price*0.7); notes.append("hostile -30%")
        # Trade skill
        trade_bonus=1+ship.skill_trade*0.02
        if is_buying: price=int(price/trade_bonus)
        else: price=int(price*trade_bonus)
        return max(1,price), " ".join(notes)
    def buy_from(self,ship,rid,amt):
        info=RESOURCES.get(rid)
        if not info: return f"Unknown '{rid}'."
        rep=ship.reputation.get(self.faction,0)
        if rep<-20 and self.faction!="pirates":
            return f"Trade blocked (rep {rep}). Try blackmarket."
        if ship.cargo.has(rid)<amt: return f"Not enough {info['name']}."
        # Contraband check
        banned=CONTRABAND.get(self.faction,[])+CONTRABAND.get(self.religion,[])
        if rid in banned and rep>=-20:
            return f"{info['name']} is contraband here! Use smuggle."
        price,notes=self.price_for_player(rid,False,ship)
        total=price*amt
        if not ship.cargo.remove(rid,amt): return "Cargo error."
        ship.credits+=total
        self.inventory[rid]=self.inventory.get(rid,0)+amt
        return f"Sold {amt} {info['name']} for {total}cr ({price}cr/unit) {notes}".strip()
    def sell_to(self,ship,rid,amt):
        info=RESOURCES.get(rid)
        if not info: return f"Unknown '{rid}'."
        rep=ship.reputation.get(self.faction,0)
        if rep<-20 and self.faction!="pirates":
            return f"Trade blocked (rep {rep}). Try blackmarket."
        if self.inventory.get(rid,0)<amt: return f"Only {self.inventory.get(rid,0)} {info['name']} in stock."
        price,notes=self.price_for_player(rid,True,ship)
        total=price*amt
        if ship.credits<total: return f"Need {total}, have {ship.credits}."
        if not ship.cargo.add(rid,amt): return f"Cargo full ({ship.cargo.free()} free)."
        ship.credits-=total
        self.inventory[rid]-=amt
        return f"Bought {amt} {info['name']} for {total}cr ({price}cr/unit) {notes}".strip()
    def price_summary(self):
        parts=[f"{rid}:{sp}" for rid in sorted(RESOURCES) if self.inventory.get(rid,0)>0 for _,sp in [self.prices.get(rid,(0,0))]]
        return f"  {self.name}[{self.stype}] {self.faction}: {','.join(parts[:5])}"
    def gen_mission(self):
        """Генерирует торговую миссию."""
        rid=random.choice(list(RESOURCES))
        amt=random.randint(3,10)
        reward=amt*RESOURCES[rid]["base_price"]*random.randint(2,4)
        target=random.choice([s for s in self.__class__.stations if s!=self]) if hasattr(self.__class__,'stations') else None
        if target:
            self.missions.append({"id":len(self.missions)+1,"type":"deliver","res":rid,
                "amount":amt,"target":target.name,"reward":reward,"ticks":random.randint(15,30)})
    @classmethod
    def set_stations(cls,stations): cls.stations=stations

class GameEvent:
    def __init__(self,n,d,dur=0): self.name=n; self.description=d; self.duration=dur
class NewsEntry:
    def __init__(self,h,b,t=0): self.headline=h; self.body=b; self.turn=t

# ---------- Галактика ----------
class Galaxy:
    def __init__(self,width=WIDTH,height=HEIGHT,seed=None):
        self.width,self.height=width,height
        self.seed=seed if seed else random.randint(0,999999)
        random.seed(self.seed)
        self.tiles=[[TILE_EMPTY for _ in range(width)] for _ in range(height)]
        self.objects={}; self.stations=[]; self.traders=[]; self.pirates=[]
        self.events_queue=[]; self.global_crisis_ticks=0
        self.diplomacy={f:{f2:"neutral" for f2 in FACTIONS if f2!=f} for f in FACTIONS}
        self.news=[NewsEntry("Galaxy News","A vast galaxy awaits...")]
        self.tick_counter=0
        self._generate()
        self.black_holes=[p for p,o in self.objects.items() if o=='black_hole']
        self.wormholes=[p for p,o in self.objects.items() if o=='wormhole']
        Station.set_stations(self.stations)
    def _generate(self):
        for y in range(self.height):
            for x in range(self.width):
                if random.random()<0.025:
                    self.tiles[y][x]=TILE_STAR; self.objects[(x,y)]="star"
                    if random.random()<0.2:
                        px,py=self._random_nearby(x,y)
                        if self.tiles[py][px]==TILE_EMPTY: self.tiles[py][px]=TILE_PLANET; self.objects[(px,py)]="planet"
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y][x]==TILE_EMPTY and random.random()<0.01:
                    self.tiles[y][x]=TILE_STATION; self.objects[(x,y)]="station"; self.stations.append(Station(x,y))
        for _ in range(int(self.width*self.height*0.0025)):
            x,y=random.randint(0,self.width-1),random.randint(0,self.height-1)
            if self.tiles[y][x]==TILE_EMPTY: self.tiles[y][x]=TILE_BLACK_HOLE; self.objects[(x,y)]="black_hole"
        for _ in range(int(self.width*self.height*0.0015)):
            x,y=random.randint(0,self.width-1),random.randint(0,self.height-1)
            if self.tiles[y][x]==TILE_EMPTY: self.tiles[y][x]=TILE_WORMHOLE; self.objects[(x,y)]="wormhole"
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y][x]==TILE_EMPTY and random.random()<0.015:
                    self.tiles[y][x]=TILE_ASTEROIDS; self.objects[(x,y)]="asteroids"
        self.objects={k:v for k,v in self.objects.items() if v!="ship"}
        if self.stations:
            for _ in range(random.randint(8,12)):
                x,y=self._random_passable()
                route=random.sample(range(len(self.stations)),min(random.randint(3,5),len(self.stations)))
                self.traders.append(TraderShip(x,y,route))
        for _ in range(random.randint(3,5)):
            x,y=self._random_passable_near_obj("asteroids",5); self.pirates.append(PirateShip(x,y))
    def _random_passable(self):
        for _ in range(500):
            x,y=random.randint(0,self.width-1),random.randint(0,self.height-1)
            if self.tiles[y][x]==TILE_EMPTY and (x,y) not in self.objects: return x,y
        return random.randint(0,self.width-1),random.randint(0,self.height-1)
    def _random_passable_near_obj(self,ot,sp=5):
        cand=[p for p,o in self.objects.items() if o==ot]
        if not cand: return self._random_passable()
        cx,cy=random.choice(cand)
        for _ in range(100):
            dx,dy=random.randint(-sp,sp),random.randint(-sp,sp)
            nx,ny=cx+dx,cy+dy
            if 0<=nx<self.width and 0<=ny<self.height and self.tiles[ny][nx]==TILE_EMPTY: return nx,ny
        return self._random_passable()
    def _random_nearby(self,x,y,md=2):
        return max(0,min(self.width-1,x+random.randint(-md,md))),max(0,min(self.height-1,y+random.randint(-md,md)))
    def get_tile(self,x,y):
        if 0<=x<self.width and 0<=y<self.height: return self.tiles[y][x]
        return " "
    def get_object_info(self,x,y):
        for t in self.traders:
            if t.alive and t.x==x and t.y==y: return f"Trader {t.name}[{t.faction}]"
        for p in self.pirates:
            if p.alive and p.x==x and p.y==y: return f"Pirate {p.name}[{p.faction}]"
        obj=self.objects.get((x,y))
        if obj:
            n={"star":"Star","planet":"Planet","station":"Station","black_hole":"Black Hole",
               "wormhole":"Wormhole","asteroids":"Asteroids"}.get(obj,obj.title())
            st=self.get_station_at(x,y)
            if st: n+=f" {st.name}[{st.faction}]"
            return n
        return "Empty"
    def is_passable(self,x,y):
        if not(0<=x<self.width and 0<=y<self.height): return False
        return self.tiles[y][x] not in(TILE_STAR,TILE_BLACK_HOLE)
    def get_station_at(self,x,y):
        for s in self.stations:
            if s.x==x and s.y==y: return s
        return None
    def get_nearest_station(self,x,y,md=1):
        for s in self.stations:
            if max(abs(s.x-x),abs(s.y-y))<=md: return s
        return None
    def get_npc_at(self,x,y):
        for t in self.traders:
            if t.alive and t.x==x and t.y==y: return t
        for p in self.pirates:
            if p.alive and p.x==x and p.y==y: return p
        return None
    def get_npc_by_name(self,name):
        for t in self.traders:
            if t.alive and t.name.lower()==name.lower(): return t
        for p in self.pirates:
            if p.alive and p.name.lower()==name.lower(): return p
        return None
    def add_news(self,h,b):
        self.news.append(NewsEntry(h,b,self.tick_counter))
        if len(self.news)>50: self.news=self.news[-50:]
    def stations_in_range(self,x,y,r):
        return [s for s in self.stations if max(abs(s.x-x),abs(s.y-y))<=r]

    # ---------- WORLD TICK ----------
    def tick(self,player_x,player_y,player_ship):
        """Мировой тик: гравитация, радиация, астероиды, экономика."""
        events=[]
        for bh_x,bh_y in self.black_holes:
            dist=max(abs(player_x-bh_x),abs(player_y-bh_y))
            if 0<dist<=3:
                dx=1 if bh_x>player_x else -1 if bh_x<player_x else 0
                dy=1 if bh_y>player_y else -1 if bh_y<player_y else 0
                nx,ny=player_x+dx,player_y+dy
                if 0<=nx<self.width and 0<=ny<self.height:
                    player_x,player_y=nx,ny
                    events.append("Gravity pull towards BH!")
                    if self.tiles[player_y][player_x]==TILE_BLACK_HOLE:
                        events.append("Pulled into black hole. Game Over.")
                        return player_x,player_y,events,True
        for y in range(max(0,player_y-1),min(self.height,player_y+2)):
            for x in range(max(0,player_x-1),min(self.width,player_x+2)):
                if self.tiles[y][x]==TILE_STAR and (x!=player_x or y!=player_y):
                    dmg=10
                    if hasattr(player_ship,'race') and player_ship.race=="mutant": dmg=int(dmg*0.5)
                    if not getattr(player_ship,'radiation_shield',False):
                        player_ship.take_damage(dmg)
                        events.append(f"Radiation! Hull -{dmg}")
                        if player_ship.hull<=0: return player_x,player_y,events,True
        if self.tiles[player_y][player_x]==TILE_ASTEROIDS:
            if random.random()<0.3:
                player_ship.take_damage(5); events.append("Asteroid! Hull -5")
                if player_ship.hull<=0: return player_x,player_y,events,True
        for s in self.stations: s.update_economy()
        return player_x,player_y,events,False

    def step_npc(self,player_x,player_y,player_ship,events_out):
        """NPC movement and AI."""
        for t in self.traders:
            if not t.alive: continue
            target=t.current_target(self.stations)
            if not target: continue
            if t.x==target.x and t.y==target.y:
                if t.wait_ticks<=0: t.wait_ticks=random.randint(2,5)
                else: t.wait_ticks-=1
                if t.wait_ticks<=0: t.route_index+=1
                continue
            self._npc_move_towards(t,target.x,target.y)
            if max(abs(t.x-player_x),abs(t.y-player_y))<=1: events_out.append(f"Trader {t.name} nearby.")
        for p in self.pirates:
            if not p.alive: continue
            targets=[]
            if max(abs(p.x-player_x),abs(p.y-player_y))<=p.aggro_range: targets.append((player_x,player_y,"player"))
            for t in self.traders:
                if t.alive and max(abs(p.x-t.x),abs(p.y-t.y))<=p.aggro_range: targets.append((t.x,t.y,"trader"))
            if targets:
                tx,ty,ttype=min(targets,key=lambda c:max(abs(p.x-c[0]),abs(p.y-c[1])))
                if max(abs(p.x-tx),abs(p.y-ty))==1:
                    if ttype=="player":
                        player_ship.take_damage(10); events_out.append(f"Pirate {p.name} attacks! Hull -10.")
                        if player_ship.cargo.items:
                            sid=random.choice(list(player_ship.cargo.items.keys()))
                            sa=max(1,player_ship.cargo.has(sid)//5)
                            player_ship.cargo.remove(sid,sa); events_out.append(f"Stole {sa} {sid}!")
                        if player_ship.hull<=0: events_out.append("Destroyed by pirates.")
                    else:
                        for t2 in self.traders:
                            if t2.alive and t2.x==tx and t2.y==ty:
                                t2.take_damage(15); events_out.append(f"Pirate attacks trader {t2.name}!")
                                if not t2.alive: events_out.append(f"Trader {t2.name} destroyed.")
                                break
                else: self._npc_move_towards(p,tx,ty)
            elif random.random()<0.3: self._npc_random_move(p)
            if p.hull<=p.flee_threshold:
                dx=player_x-p.x; fx=p.x-(1 if dx>0 else -1 if dx<0 else 0)
                if self.is_passable(fx,p.y): p.x=fx

    def _npc_move_towards(self,npc,tx,ty):
        dx=1 if tx>npc.x else -1 if tx<npc.x else 0
        dy=1 if ty>npc.y else -1 if ty<npc.y else 0
        if dx!=0 and self.is_passable(npc.x+dx,npc.y) and not self._occupied(npc.x+dx,npc.y): npc.x+=dx
        elif dy!=0 and self.is_passable(npc.x,npc.y+dy) and not self._occupied(npc.x,npc.y+dy): npc.y+=dy
        else: self._npc_random_move(npc)

    def _npc_random_move(self,npc):
        for dx,dy in random.sample([(1,0),(-1,0),(0,1),(0,-1)],4):
            nx,ny=npc.x+dx,npc.y+dy
            if self.is_passable(nx,ny) and not self._occupied(nx,ny): npc.x,npc.y=nx,ny; return

    def _occupied(self,x,y):
        for t in self.traders:
            if t.alive and t.x==x and t.y==y: return True
        for p in self.pirates:
            if p.alive and p.x==x and p.y==y: return True
        return (x,y) in self.objects

# ---------- Экраны ----------
class CommandScreen(Screen):
    def compose(self):
        yield Input(placeholder="Enter command (help for list)...",id="cmd-input")
    def on_input_submitted(self,event):
        app=self.app
        if isinstance(app,GalaxyMapApp): app.process_command(event.value)
        self.dismiss()

class CargoScreen(Screen):
    BINDINGS=[("escape","close","Close")]
    def compose(self):
        yield Static(id="cargo-header")
        yield DataTable(id="cargo-table")
        yield Static(id="cargo-footer")
    def on_mount(self):
        app=self.app
        if not isinstance(app,GalaxyMapApp): return
        ship=app.ship; cargo=ship.cargo
        self.query_one("#cargo-header").update(f"Cargo: {cargo.used()}/{cargo.capacity}  Value: {cargo.total_value()}cr")
        table=self.query_one("#cargo-table")
        table.clear()
        table.add_columns("Item","Cat","Qty","Price","Actions")
        categories={"raw":"Raw","refined":"Refined","advanced":"Advanced","special":"Special"}
        for rid,amt in sorted(cargo.items.items()):
            info=RESOURCES.get(rid,{})
            cat=categories.get(info.get("cat",""),"Other")
            bp=info.get("base_price",0)
            table.add_row(rid,cat,str(amt),f"{bp}cr",f"[J]ettison")
        self.query_one("#cargo-footer").update("[J] Jettison  [1-5] Quick slot  [Q] Close")
    def on_key(self,event):
        app=self.app
        if not isinstance(app,GalaxyMapApp): return
        if event.key=="escape" or event.key=="q":
            self.dismiss()
        elif event.key=="j":
            self.query_one("#cargo-footer").update("Select item to jettison (click row)")
        elif event.key.isdigit() and 1<=int(event.key)<=5:
            self.query_one("#cargo-footer").update(f"Quick slot {event.key}: select item")

class TradeScreen(Screen):
    def __init__(self,station):
        super().__init__()
        self.station=station
    def compose(self):
        yield Static(id="trade-header")
        yield Static(id="station-goods")
        yield Static(id="player-cargo")
        yield Input(placeholder="buy/sell <res> <amt> or 'close'",id="trade-input")
    def on_mount(self):
        app=self.app
        if not isinstance(app,GalaxyMapApp): return
        st=self.station; ship=app.ship
        # Prices for player (with rep)
        hdr=(f"Trading at {st.name}[{st.faction}]  Credits:{ship.credits}  "
             f"Cargo:{ship.cargo.used()}/{ship.cargo.capacity}")
        self.query_one("#trade-header").update(hdr)
        sgoods=["── Station Stock ──"]
        for rid in sorted(RESOURCES):
            stock=st.inventory.get(rid,0)
            bp,sp=st.prices.get(rid,(0,0))
            pb,_=st.price_for_player(rid,True,ship)
            ps,_=st.price_for_player(rid,False,ship)
            sgoods.append(f"  {rid:<12} stock:{stock:<3}  buy:{pb:>4}cr  sell:{ps:>4}cr")
        self.query_one("#station-goods").update("\n".join(sgoods))
        pc=["── Your Cargo ──"]
        for rid,amt in sorted(ship.cargo.items.items()):
            bp=RESOURCES.get(rid,{}).get("base_price",0)
            pc.append(f"  {rid:<12} qty:{amt:<3}  val:{bp*amt}cr")
        if not ship.cargo.items: pc.append("  (empty)")
        self.query_one("#player-cargo").update("\n".join(pc))
    def on_key(self,event):
        if event.key in("escape","q"): self.dismiss()
    def on_input_submitted(self,event):
        app=self.app
        if not isinstance(app,GalaxyMapApp): return
        val=event.value.strip().lower()
        if val in("close","exit","quit"): self.dismiss(); return
        # Auto-prefix "trade " for convenience
        parts=val.split()
        if parts and parts[0] in ("buy","sell"):
            val="trade "+val
        app.process_command(val)
        # Refresh display
        self.on_mount()

# ---------- Приложение ----------
class GalaxyMapApp(App):
    CSS="""
    #map{height:1fr;content-align:center middle;}
    #info-panel{height:15;border:solid green;margin:1;padding:0 1;}
    #log{height:10;border:solid yellow;margin:1;padding:0 1;color:yellow;}
    CommandScreen Input{dock:bottom;margin:1 2;}
    CargoScreen DataTable{height:1fr;}
    TradeScreen Input{dock:bottom;margin:1 2;}
    """
    player_x=reactive(WIDTH//2); player_y=reactive(HEIGHT//2)

    def __init__(self):
        super().__init__()
        self.state=GameState.RACE_SELECT
        self.galaxy=Galaxy()
        self.ship=PlayerShip("Endeavour",100)
        self.logger=GameLogger()
        self.death_cause=None; self.interaction_actions=[]
        self.cursor_x=WIDTH//2; self.cursor_y=HEIGHT//2
        self._politics_timer=0; self.race_selected=False
        self._prev_state=GameState.START_SCREEN
        self._init_player_position()

    def _init_player_position(self):
        self.player_x=WIDTH//2; self.player_y=HEIGHT//2
        while not self.galaxy.is_passable(self.player_x,self.player_y):
            self.player_x=random.randint(0,WIDTH-1); self.player_y=random.randint(0,HEIGHT-1)

    def select_race(self,choice):
        choice=choice.lower().strip()
        if choice in("1","human",""): self.ship.race="human"
        elif choice in("2","mutant"): self.ship.race="mutant"
        elif choice in("3","xenos_bio","xenos"): self.ship.race="xenos_bio"
        elif choice in("4","machine_cult","machine"): self.ship.race="machine_cult"
        elif choice in("5","voidborn","void"): self.ship.race="voidborn"
        r=RACES.get(self.ship.race,{}).get("name","Human")
        self.logger.system(f"Race: {r}. In the grim darkness...")
        self.race_selected=True; self.state=GameState.PLAYING
        self.update_map(); self.update_info()

    def restart_game(self):
        NPCShip._id_counter=0
        self.state=GameState.RACE_SELECT; self.galaxy=Galaxy()
        self.ship=PlayerShip("Endeavour",100); self.logger.clear()
        self.death_cause=None; self.interaction_actions=[]; self.race_selected=False
        self._init_player_position()
        self.update_map(); self.update_info()

    def compose(self):
        yield Header(); yield Container(Static(id="map"))
        yield Static(id="info-panel"); yield Static(id="log"); yield Footer()

    def on_mount(self): self.update_map(); self.update_info()

    def render_start_screen(self):
        if self.state==GameState.RACE_SELECT:
            lines=["","","  ╔══════════════════════════════╗","  ║     CHOOSE YOUR RACE        ║",
                "  ╚══════════════════════════════╝","","  1 Human    2 Mutant  3 Xenos Bio",
                "  4 Machine  5 Voidborn","","  Press 1-5 or Enter for Human"]
            self.query_one("#map").update("\n".join(lines)); return
        lines=["","","  ╔══════════════════════════════════════╗","  ║  In the grim darkness of the far     ║",
            "  ║  future, there is only war.        ║","  ║         GALAXY MAP                   ║",
            "  ╚══════════════════════════════════════╝","",
            f"  Race: {RACES.get(self.ship.race,{}).get('name','Human')}","",
            "  WASD Move  E Interact  I Inspect  H Help","  N News  ~ Console  F Fire  Space Wait","",
            "  Press any key to start..."]
        self.query_one("#map").update("\n".join(lines))

    def render_help_screen(self):
        lines=["" for _ in range(HEIGHT)]
        ht=["  ╔══════════════════════════════════════╗","  ║              HELP                 ║",
            "  ╚══════════════════════════════════════╝","","  MOVE: WASD  Space=Wait  E=Interact  I=Inspect",
            "  F=Fire  N=News  H=Help  ~=Console  Esc=Pause","",
            "  TRADE: ~ → trade buy/sell <res> <amt>","  ~ → market scan [range]  ~ → prices",
            "  ~ → market history <station> <res>","  ~ → cargo  ~ → blackmarket list",
            "  ~ → smuggle <res> <amt>","",
            "  CARGO: ~ → cargo jettison <res> [amt]","  ~ → cargo sellall","  B key = open trade screen (at station)","",
            "  Rep < -20 = blocked trade (use blackmarket)","  Contraband flagged per faction/religion","",
            "        Press H or any key to return"]
        cy=max(0,(HEIGHT-len(ht))//2)
        for i,h in enumerate(ht):
            if 0<=cy+i<HEIGHT: lines[cy+i]=" "*(max(0,WIDTH-len(h))//2)+h
        return "\n".join(lines)

    def render_news_screen(self):
        lines=["" for _ in range(HEIGHT)]
        nt=["  ╔══════════════════════════════════════╗","  ║         GALAXY NEWS              ║",
            "  ╚══════════════════════════════════════╝",""]
        for e in self.galaxy.news[-8:]:
            nt.append(f"  [{e.turn}] {e.headline}"); nt.append(f"  {e.body}"); nt.append("")
        nt.append("  Press N or any key to return")
        cy=max(0,(HEIGHT-len(nt))//2)
        for i,h in enumerate(nt):
            if 0<=cy+i<HEIGHT: lines[cy+i]=" "*(max(0,WIDTH-len(h))//2)+h
        return "\n".join(lines)

    def render_pause_overlay(self):
        lines=self._build_map_lines()
        ov=["","  ╔══════════════════════════════╗","  ║          PAUSED              ║",
            "  ║                              ║","  ║    C  —  Continue             ║",
            "  ║    R  —  Restart             ║","  ║    Q  —  Quit                 ║",
            "  ╚══════════════════════════════╝"]
        cy=len(lines)//2-len(ov)//2
        for i,o in enumerate(ov):
            idx=cy+i
            if 0<=idx<len(lines):
                pad=max(0,len(lines[0])-len(o))//2
                lines[idx]=lines[idx][:pad]+o+lines[idx][pad+len(o):]
        return "\n".join(lines)

    def render_game_over_screen(self):
        lines=self._build_map_lines()
        cause=self.death_cause or f"{self.ship.name} lost."
        if len(cause)>36: cause=cause[:33]+"..."
        ov=["  ╔══════════════════════════════╗","  ║         GAME OVER            ║",
            "  ║                              ║",f"  ║  {cause:^30}  ║",
            "  ║                              ║","  ║    R  —  Restart              ║",
            "  ║    Q  —  Quit                 ║","  ╚══════════════════════════════╝"]
        cy=len(lines)//2-len(ov)//2
        for i,o in enumerate(ov):
            idx=cy+i
            if 0<=idx<len(lines):
                pad=max(0,len(lines[0])-len(o))//2
                lines[idx]=lines[idx][:pad]+o+lines[idx][pad+len(o):]
        return "\n".join(lines)

    def render_interaction_menu(self):
        lines=self._build_map_lines()
        acts=self.interaction_actions or [("","  Nothing here.","","")]
        box_w=44
        ov=[f"  ╔{'═'*(box_w-2)}╗",
            f"  ║{'INTERACTION MENU':^{box_w-2}}║",
            f"  ║{'':^{box_w-2}}║"]
        for _,l,_,_ in acts:
            clean=l[:box_w-8]
            ov.append(f"  ║    {clean:<{box_w-8}}  ║")
        ov.extend([f"  ║{'':^{box_w-2}}║",f"  ║{'Esc  —  Close':^{box_w-2}}║",f"  ╚{'═'*(box_w-2)}╝"])
        cy=len(lines)//2-len(ov)//2
        for i,o in enumerate(ov):
            idx=cy+i
            if 0<=idx<len(lines):
                pad=max(0,len(lines[0])-len(o))//2
                lines[idx]=lines[idx][:pad]+o+lines[idx][pad+len(o):]
        return "\n".join(lines)

    def _build_map_lines(self):
        lines=[]; show=self.state in(GameState.PLAYING,GameState.INSPECTING)
        nc={}
        for t in self.galaxy.traders:
            if t.alive: nc[(t.x,t.y)]=TILE_TRADER
        for p in self.galaxy.pirates:
            if p.alive: nc[(p.x,p.y)]=TILE_PIRATE
        for y in range(self.galaxy.height):
            line=""
            for x in range(self.galaxy.width):
                if x==self.player_x and y==self.player_y and show: line+=TILE_SHIP
                elif self.state==GameState.INSPECTING and x==self.cursor_x and y==self.cursor_y: line+=TILE_CURSOR
                elif (x,y) in nc: line+=nc[(x,y)]
                else: line+=self.galaxy.get_tile(x,y)
            lines.append(line)
        return lines

    def update_map(self):
        if self.state==GameState.RACE_SELECT: self.render_start_screen()
        elif self.state==GameState.HELP: self.query_one("#map").update(self.render_help_screen())
        elif self.state==GameState.NEWS: self.query_one("#map").update(self.render_news_screen())
        elif self.state==GameState.START_SCREEN: self.render_start_screen()
        elif self.state==GameState.INTERACTING: self.query_one("#map").update(self.render_interaction_menu())
        elif self.state==GameState.INSPECTING: self.query_one("#map").update("\n".join(self._build_map_lines()))
        elif self.state==GameState.PAUSED: self.query_one("#map").update(self.render_pause_overlay())
        elif self.state==GameState.GAME_OVER: self.query_one("#map").update(self.render_game_over_screen())
        else: self.query_one("#map").update("\n".join(self._build_map_lines()))

    def _scan_nearby(self,radius=7):
        found=[]
        for dy in range(-radius,radius+1):
            for dx in range(-radius,radius+1):
                if dx==0 and dy==0: continue
                nx,ny=self.player_x+dx,self.player_y+dy; dist=max(abs(dx),abs(dy))
                dk=(1 if dx>0 else -1 if dx<0 else 0,1 if dy>0 else -1 if dy<0 else 0)
                d=DIR_LABELS[dk]
                npc=self.galaxy.get_npc_at(nx,ny)
                if npc:
                    tag=TILE_TRADER if isinstance(npc,TraderShip) else TILE_PIRATE
                    found.append(f"{d}:{tag}({dist})[{npc.name}]"); continue
                obj=self.galaxy.objects.get((nx,ny))
                if obj is None: continue
                ic={"star":TILE_STAR,"planet":TILE_PLANET,"station":TILE_STATION,
                    "black_hole":TILE_BLACK_HOLE,"wormhole":TILE_WORMHOLE,"asteroids":TILE_ASTEROIDS}.get(obj,"?")
                entry=f"{d}:{ic}({dist})"
                if obj=="station" and dist<=1:
                    st=self.galaxy.get_station_at(nx,ny)
                    if st: entry+=f"[{st.name}|{st.faction}]"
                found.append(entry)
        if not found: return "  Nothing within scan range"
        def dk(s):
            try: return int(s.split("(")[1].split(")")[0])
            except: return 99
        found.sort(key=dk)
        return "  "+"  ".join(found[:8])

    def _get_ship_status(self):
        eff=[]; px,py=self.player_x,self.player_y
        for bh_x,bh_y in self.galaxy.black_holes:
            dist=max(abs(px-bh_x),abs(py-bh_y))
            dk=(1 if bh_x>px else -1 if bh_x<px else 0,1 if bh_y>py else -1 if bh_y<py else 0)
            dl=DIR_LABELS.get(dk,"?")
            if self.ship.race=="voidborn": continue
            if 0<dist<=3: eff.append(f"⚠Gravity {dl}-{dist}")
            elif 3<dist<=5: eff.append(f"○Gravity {dl}-{dist}")
        for dy in(-1,0,1):
            for dx in(-1,0,1):
                if dx==0 and dy==0: continue
                if self.galaxy.objects.get((px+dx,py+dy))=="star": eff.append("⚠Radiation"); break
        if self.galaxy.objects.get((px,py))=="asteroids": eff.append("⚠Asteroids")
        for wx,wy in self.galaxy.wormholes:
            if max(abs(px-wx),abs(py-wy))<=2: eff.append("○Wormhole"); break
        return eff

    def _cargo_summary(self):
        if not self.ship.cargo.items: return "Cargo: empty"
        p=[f"{RESOURCES.get(r,{}).get('name',r)}:{a}" for r,a in sorted(self.ship.cargo.items.items())]
        return f"Cargo: {'  '.join(p)}  ({self.ship.cargo.used()}/{self.ship.cargo.capacity})"

    def _reputation_summary(self):
        return "  ".join(f"{k}:{v}" for k,v in self.ship.reputation.items() if k in FACTIONS)

    def update_info(self):
        if self.state in(GameState.RACE_SELECT,GameState.START_SCREEN):
            self.query_one("#info-panel").update("H=Help  N=News"); self.query_one("#log").update(""); return
        if self.state==GameState.HELP:
            self.query_one("#info-panel").update("Press H to return."); self.query_one("#log").update(""); return
        if self.state==GameState.NEWS:
            self.query_one("#info-panel").update("Press N to close."); self.query_one("#log").update(""); return
        if self.state==GameState.INTERACTING:
            self.query_one("#info-panel").update("Select action or Esc."); self.query_one("#log").update(self.logger.render(10)); return
        if self.state==GameState.PAUSED:
            self.query_one("#info-panel").update("PAUSED"); self.query_one("#log").update(""); return
        if self.state==GameState.GAME_OVER:
            c=self.death_cause or "Destroyed."
            self.query_one("#info-panel").update(f"☠ {c}  R=Restart Q=Quit")
            self.query_one("#log").update(self.logger.render(10)); return
        if self.state==GameState.INSPECTING:
            cx,cy=self.cursor_x,self.cursor_y
            desc=self.galaxy.get_object_info(cx,cy)
            dist=max(abs(cx-self.player_x),abs(cy-self.player_y)); extra=""
            st=self.galaxy.get_station_at(cx,cy)
            if st: extra=f"\n{st.price_summary()}"
            npc=self.galaxy.get_npc_at(cx,cy)
            if npc: extra=f"\nFaction:{npc.faction} Hull:{npc.hull}/{npc.max_hull}"
            self.query_one("#info-panel").update(f"Inspect: ({cx},{cy}) {desc}\nDist:{dist}{extra}")
            self.query_one("#log").update(self.logger.render(10)); return
        # PLAYING
        desc=self.galaxy.get_object_info(self.player_x,self.player_y)
        sl=self._get_ship_status()
        sline="  "+" | ".join(sl) if sl else "  Nominal"
        nearby=self._scan_nearby(); cargo=self._cargo_summary()
        cval=self.ship.cargo.total_value()
        rn=RACES.get(self.ship.race,{}).get("name","Human")
        rl=self.ship.religion or "none"
        rep=self._reputation_summary()
        stn=self.galaxy.get_nearest_station(self.player_x,self.player_y,1)
        econ="\n"+stn.price_summary() if stn else ""
        self.query_one("#info-panel").update(
            f"({self.player_x},{self.player_y}) {desc}\n{self.ship.name}[{rn}] Rel:{rl}  "
            f"Hull:{self.ship.hull} Fuel:{self.ship.fuel} Cr:{self.ship.credits}\n"
            f"{cargo}  Val:{cval}cr\nRep:{rep}\nStatus:{sline}{econ}")
        self.query_one("#log").update(self.logger.render(10))

    def _log_event(self,m):
        ml=m.lower()
        if "radiation"in ml or "collision"in ml: self.logger.combat(m)
        elif any(x in ml for x in["gravity","pulled","destroyed","attack","stole"]): self.logger.danger(m)
        elif "[event]"in m: self.logger.system(m)
        else: self.logger.exploration(m)

    def _check_political_events(self,out):
        self._politics_timer+=1
        if self._politics_timer<random.randint(30,60): return
        self._politics_timer=0
        et=random.choice(["crusade","warp_invasion","schism","plague","scandal","treaty"])
        if et=="crusade":
            self.galaxy.add_news("Crusade!","The Imperium declares war on Chaos!"); out.append("[EVENT] Crusade!")
        elif et=="warp_invasion":
            for _ in range(random.randint(3,5)):
                x,y=self.galaxy._random_passable(); self.galaxy.pirates.append(PirateShip(x,y))
            self.galaxy.add_news("Warp Invasion!","Hostiles spawned."); out.append("[EVENT] Warp invasion!")
        elif et=="schism":
            for s in self.galaxy.stations:
                if s.faction=="imperium" and random.random()<0.3: s.crisis_ticks=10
            self.galaxy.add_news("Schism!","Church divided."); out.append("[EVENT] Church schism!")
        elif et=="plague":
            t=random.choice(list(FACTIONS))
            for s in self.galaxy.stations:
                if s.faction==t: s.crisis_ticks=10
            self.galaxy.add_news(f"Plague at {t}!","Production halted."); out.append(f"[EVENT] Plague at {t}!")
        elif et=="scandal":
            f1,f2=random.sample(list(FACTIONS),2)
            if f2 in self.galaxy.diplomacy.get(f1,{}): self.galaxy.diplomacy[f1][f2]="war"
            self.galaxy.add_news("Scandal!","Diplomatic relations collapse."); out.append("[EVENT] Scandal!")
        elif et=="treaty":
            f1,f2=random.sample(list(FACTIONS),2)
            if f2 in self.galaxy.diplomacy.get(f1,{}): self.galaxy.diplomacy[f1][f2]="truce"
            self.galaxy.add_news("Treaty!","Trade route opened."); out.append("[EVENT] Trade treaty!")

    def _check_random_events(self,out):
        if random.random()>0.03: return
        g=self.galaxy
        et=random.choice(["caravan","raid","supernova","crisis"])
        if et=="caravan":
            for _ in range(3):
                x,y=g._random_passable()
                rt=random.sample(range(len(g.stations)),min(3,len(g.stations))) if g.stations else []
                t=TraderShip(x,y,rt); t.cargo=CargoHold(100)
                t.cargo.add("relic",random.randint(1,3)); t.cargo.add("electronics",random.randint(5,15))
                g.traders.append(t)
            g.add_news("Caravan!","Traders with rare goods arrived."); out.append("[EVENT] Caravan!")
        elif et=="raid":
            for _ in range(random.randint(2,4)):
                x,y=g._random_passable(); g.pirates.append(PirateShip(x,y))
            g.add_news("Raid!","Pirates inbound."); out.append("[EVENT] Pirate raid!")
        elif et=="supernova" and g.black_holes:
            bh=random.choice(g.black_holes)
            if max(abs(self.player_x-bh[0]),abs(self.player_y-bh[1]))<=10:
                self.ship.take_damage(10)
                out.append("Supernova shockwave! Hull -10.")
                if self.ship.hull<=0: self.death_cause="Supernova."
            g.add_news("Supernova!","Shockwave detected."); out.append("[EVENT] Supernova!")
        elif et=="crisis":
            g.global_crisis_ticks=10
            g.add_news("Economic Crisis!","Prices drop 30%."); out.append("[EVENT] Economic crisis!")

    OBJ_LABELS={"planet":("Planet",TILE_PLANET),"station":("Station",TILE_STATION),
                "asteroids":("Asteroids",TILE_ASTEROIDS),"wormhole":("Wormhole",TILE_WORMHOLE)}

    def _get_available_interactions(self):
        acts=[]; px,py=self.player_x,self.player_y
        def add(ot,x,y,dx,dy):
            dn=self._direction_name(dx,dy) if(dx or dy) else "here"
            nm,ic=self.OBJ_LABELS.get(ot,(ot.capitalize(),"?"))
            if ot=="station" and dx==0 and dy==0:
                st=self.galaxy.get_station_at(x,y)
                tag=f"[{st.faction}]" if st else ""
                acts.append(("r",f"(R)efuel-50cr {tag}","_act_refuel",f"Station {dn}"))
                acts.append(("h",f"Repair(H)ull-30cr {tag}","_act_repair",f"Station {dn}"))
                acts.append(("b",f"(B)uy/Sell {tag}","_act_open_trade",f"Station {dn}"))
                if st and st.stype=="temple" and self.ship.religion is None:
                    acts.append(("j",f"(J)oin religion {st.name}","_act_join_religion",f"Temple {dn}"))
            elif ot=="planet":
                acts.append(("s",f"(S)can {ic} {nm}","_act_scan_planet",f"{nm} {dn}"))
                acts.append(("l",f"(L)and {ic}","_act_land",f"{nm} {dn}"))
            elif ot=="asteroids" and dx==0 and dy==0:
                acts.append(("m",f"(M)ine {ic}","_act_mine",f"{nm} {dn}"))
            elif ot=="wormhole" and dx==0 and dy==0:
                acts.append(("u",f"(U)se Wormhole {ic}","_act_use_wormhole",f"{nm} {dn}"))
        for t in self.galaxy.traders:
            if t.alive and max(abs(t.x-px),abs(t.y-py))<=1:
                nn=self._direction_name(t.x-px,t.y-py) if(t.x!=px or t.y!=py) else ""
                acts.append(("c",f"(C)hat {t.name}[{t.faction}]","_act_hail_npc",f"Trader {nn}"))
        for p in self.galaxy.pirates:
            if p.alive and max(abs(p.x-px),abs(p.y-py))<=1:
                nn=self._direction_name(p.x-px,p.y-py) if(p.x!=px or p.y!=py) else ""
                acts.append(("f",f"(F)ire {p.name}","_act_fire_pirate",f"Pirate {nn}"))
        ob=self.galaxy.objects.get((px,py))
        if ob: add(ob,px,py,0,0)
        for dy in(-1,0,1):
            for dx in(-1,0,1):
                if dx==0 and dy==0: continue
                nob=self.galaxy.objects.get((px+dx,py+dy))
                if nob: add(nob,px+dx,py+dy,dx,dy)
        return acts

    def _run_interaction(self,mn):
        h=getattr(self,mn,None)
        if h:
            h()
            if self.state!=GameState.GAME_OVER: self.state=GameState.PLAYING
            self.update_map(); self.update_info()

    def _act_refuel(self):
        if self.ship.credits>=50:
            self.ship.credits-=50; self.ship.fuel=min(100,self.ship.fuel+20)
            self.logger.trade(f"Refuel +20 (-50cr). Fuel:{self.ship.fuel}")
        else: self.logger.system(f"Need 50cr, have {self.ship.credits}")

    def _act_repair(self):
        if self.ship.credits>=30:
            self.ship.credits-=30; o=self.ship.hull; self.ship.hull=min(100,self.ship.hull+15)
            self.logger.trade(f"Hull +{self.ship.hull-o} (-30cr).")
        else: self.logger.system(f"Need 30cr, have {self.ship.credits}")

    def _act_trade(self):
        st=self.galaxy.get_station_at(self.player_x,self.player_y)
        if st: self.logger.system(f"{st.name}[{st.faction}]: ~ trade buy/sell <res> <amt> or B for screen")
        else: self.logger.system("No station here.")

    def _act_open_trade(self):
        st=self.galaxy.get_station_at(self.player_x,self.player_y)
        if st: self.push_screen(TradeScreen(st))
        else: self.logger.system("No station here.")

    def _act_join_religion(self):
        st=self.galaxy.get_station_at(self.player_x,self.player_y)
        if not st or st.stype!="temple": return
        if self.ship.religion: self.logger.system("Already have a religion."); return
        if st.religion: self.ship.religion=st.religion; self.logger.system(f"Joined {st.religion}!")
        else: self.logger.system("No doctrine here.")

    def _act_scan_planet(self):
        a=random.choice(["rocky","gas giant","ice","desert","oceanic"])
        r=random.choice(["iron","silicon","water ice","minerals","titanium"])
        self.logger.exploration(f"Scan: {a}, deposits of {r}.")

    def _act_land(self):
        outcomes=[("Ruins +50cr",50,""),("Wildlife! Hull-5",-5,""),("Resources +30cr",30,""),
                  ("Storm! Hull-8",-8,""),("Traded +20cr",20,""),("Minerals +2ore",0,"ore")]
        msg,delta,cid=random.choice(outcomes)
        if delta>0: self.ship.credits+=delta
        elif delta<0: self.ship.hull=max(0,self.ship.hull+delta)
        if cid and not self.ship.cargo.add(cid,2): msg+=" (full)"
        self.logger.exploration(f"Landed. {msg}")
        if self.ship.hull<=0: self.state=GameState.GAME_OVER; self.death_cause="Killed on planet."

    def _act_mine(self):
        if random.random()<0.6:
            amt=random.randint(2,6)
            if self.ship.cargo.add("ore",amt):
                self.logger.exploration(f"Mined {amt} ore ({self.ship.cargo.used()}/{self.ship.cargo.capacity})")
            else: self.logger.exploration("Cargo full!")
        else: self.logger.exploration("Depleted.")

    def _act_use_wormhole(self):
        if len(self.galaxy.wormholes)>1:
            other=(self.player_x,self.player_y)
            while other==(self.player_x,self.player_y): other=random.choice(self.galaxy.wormholes)
            self.player_x,self.player_y=other; self.logger.exploration("Teleported!"); self.logger.new_turn()
        else:
            self.logger.exploration("Wormhole collapses!")
            self.galaxy.tiles[self.player_y][self.player_x]=TILE_EMPTY

    def _act_hail_npc(self):
        for t in self.galaxy.traders:
            if t.alive and max(abs(t.x-self.player_x),abs(t.y-self.player_y))<=1:
                self.logger.exploration(f"Trader {t.name}[{t.faction}]: Hull {t.hull}/{t.max_hull}"); return
        for p in self.galaxy.pirates:
            if p.alive and max(abs(p.x-self.player_x),abs(p.y-self.player_y))<=1:
                self.logger.danger(f"Pirate {p.name}: 'Back off!'"); return
        self.logger.system("No NPC nearby.")

    def _act_fire_pirate(self):
        for p in self.galaxy.pirates:
            if p.alive and max(abs(p.x-self.player_x),abs(p.y-self.player_y))<=1:
                p.take_damage(20)
                self.logger.combat(f"Hit {p.name}! Hull {p.hull}/{p.max_hull}")
                if not p.alive:
                    r=random.randint(50,150); self.ship.credits+=r; self.ship.cargo.add("relic",1)
                    self.ship.reputation["free_traders"]=min(100,self.ship.reputation.get("free_traders",0)+2)
                    self.logger.combat(f"{p.name} destroyed! +{r}cr")
                return
        self.logger.system("No pirate adjacent.")

    @staticmethod
    def _direction_name(dx,dy):
        return {(0,-1):"N",(0,1):"S",(-1,0):"W",(1,0):"E",(-1,-1):"NW",(1,-1):"NE",(-1,1):"SW",(1,1):"SE"}.get((dx,dy),"?")

    # ---------- TICK ----------
    def tick_world(self):
        self.logger.new_turn()
        nx,ny,evs,over=self.galaxy.tick(self.player_x,self.player_y,self.ship)
        self.player_x,self.player_y=nx,ny
        for ev in evs: self._log_event(ev)
        npc_ev=[]; self.galaxy.step_npc(self.player_x,self.player_y,self.ship,npc_ev)
        for ev in npc_ev: self._log_event(ev)
        pol_ev=[]; self._check_political_events(pol_ev)
        for ev in pol_ev: self._log_event(ev)
        rand_ev=[]; self._check_random_events(rand_ev)
        for ev in rand_ev: self._log_event(ev)
        if over:
            self.state=GameState.GAME_OVER; self.death_cause=evs[-1] if evs else "Unknown"
            self.logger.danger(f"Destroyed.")
        self.update_map(); self.update_info()

    def move_player(self,dx,dy):
        if self.state!=GameState.PLAYING: return
        dn=self._direction_name(dx,dy)
        nx,ny=self.player_x+dx,self.player_y+dy
        if 0<=nx<self.galaxy.width and 0<=ny<self.galaxy.height:
            tt=self.galaxy.get_tile(nx,ny)
            if not self.galaxy.is_passable(nx,ny):
                self.logger.blocked(dn,self.galaxy.get_object_info(nx,ny)); self.update_info(); return
            if tt==TILE_WORMHOLE:
                if len(self.galaxy.wormholes)>1:
                    other=(nx,ny)
                    while other==(nx,ny): other=random.choice(self.galaxy.wormholes)
                    nx,ny=other; self.logger.exploration("Teleported!")
                else: self.logger.exploration("Wormhole collapsed.")
            self.player_x,self.player_y=nx,ny
            self.ship.fuel=max(0,self.ship.fuel-1)
            self.logger.movement(dn,self.player_x,self.player_y); self.logger.new_turn()
            self.tick_world()
        self.update_map(); self.update_info()

    # ---------- CONSOLE ----------
    def process_command(self,raw):
        raw=raw.strip()
        if not raw: self.logger.system("Type 'help'."); return
        p=raw.split(); c=p[0].lower()
        if c=="help":
            self.logger.system("── COMMANDS ──")
            self.logger.system("scan inv give/take refuel set hull")
            self.logger.system("trade buy/sell prices market scan/history")
            self.logger.system("cargo cargo jettison/sellall")
            self.logger.system("blackmarket list smuggle")
            self.logger.system("reputation diplomacy declare war attack hail missions news exit")
            self.logger.system("── KEYS ──")
            self.logger.system("WASD move E interact I inspect F fire")
            self.logger.system("N news H help B trade screen ~ console")
        elif c=="scan":
            self.logger.system(f"Sector ({self.player_x},{self.player_y}): {self.galaxy.get_object_info(self.player_x,self.player_y)}")
            self.logger.system(self._scan_nearby()); self.logger.system(self._cargo_summary())
        elif c in("inv","inventory"):
            if not self.ship.cargo.items: self.logger.system("Cargo empty.")
            else:
                p2=[f"{RESOURCES.get(r,{}).get('name',r)}:{a}" for r,a in sorted(self.ship.cargo.items.items())]
                self.logger.system(f"Cargo: {'  '.join(p2)} ({self.ship.cargo.used()}/{self.ship.cargo.capacity}) Val:{self.ship.cargo.total_value()}cr")
        elif c=="give" and len(p)>=3:
            rid=p[1]
            try: amt=int(p[2])
            except: self.logger.system("give <res> <amt>"); return
            if rid not in RESOURCES: self.logger.system(f"Unknown '{rid}'."); return
            if self.ship.cargo.add(rid,amt): self.logger.system(f"Added {amt} {RESOURCES[rid]['name']}.")
            else: self.logger.system("Cargo full!")
        elif c=="take" and len(p)>=3:
            rid=p[1]
            try: amt=int(p[2])
            except: self.logger.system("take <res> <amt>"); return
            if self.ship.cargo.remove(rid,amt): self.logger.system(f"Removed {amt}.")
            else: self.logger.system(f"Not enough {rid}.")
        elif c=="refuel":
            o=self.ship.fuel; self.ship.fuel=100; self.logger.system(f"Refuel {o}->100.")
        elif c=="set" and len(p)>=3 and p[1]=="hull":
            try: self.ship.hull=max(0,min(100,int(p[2]))); self.logger.system(f"Hull={self.ship.hull}.")
            except: self.logger.system("set hull <n>")
        elif c=="trade" and len(p)>=4:
            st=self.galaxy.get_nearest_station(self.player_x,self.player_y,1)
            if not st: self.logger.system("No station."); return
            act,rid,amt_s=p[1],p[2],p[3]
            try: amt=int(amt_s)
            except: self.logger.system("trade buy/sell <res> <amt>"); return
            if rid not in RESOURCES: self.logger.system(f"Unknown '{rid}'."); return
            if act=="buy": self.logger.system(st.sell_to(self.ship,rid,amt))
            elif act=="sell": self.logger.system(st.buy_from(self.ship,rid,amt))
            else: self.logger.system("trade buy/sell <res> <amt>")
        elif c=="prices":
            st=self.galaxy.get_nearest_station(self.player_x,self.player_y,1)
            if not st: self.logger.system("No station."); return
            self.logger.system(f"Prices at {st.name}[{st.faction}]:")
            for rid in sorted(RESOURCES):
                b,s=st.prices.get(rid,(0,0)); sk=st.inventory.get(rid,0)
                # Price for player
                pb,_=st.price_for_player(rid,True,self.ship)
                ps,_=st.price_for_player(rid,False,self.ship)
                self.logger.system(f"  {rid:<12} buy:{pb:>4} sell:{ps:>4} base:{b:>4}/{s:<4} stock:{sk}")
        elif c=="market":
            if len(p)>=2 and p[1]=="scan":
                rng=7
                if len(p)>=3:
                    try: rng=int(p[2])
                    except: pass
                stations=self.galaxy.stations_in_range(self.player_x,self.player_y,rng)
                self.logger.system(f"Market scan (range {rng}):")
                for st in stations:
                    dist=max(abs(st.x-self.player_x),abs(st.y-self.player_y))
                    self.logger.system(f"  {st.name}[{st.faction}] dist:{dist}")
                    for rid in sorted(RESOURCES):
                        if st.inventory.get(rid,0)>0:
                            sp,_=st.price_for_player(rid,True,self.ship)
                            bp,_=st.price_for_player(rid,False,self.ship)
                            self.logger.system(f"    {rid:<12} buy:{sp:>4} sell:{bp:>4} stock:{st.inventory.get(rid,0)}")
            elif len(p)>=4 and p[1]=="history":
                sname=p[2]; rid=p[3]
                st=None
                for s in self.galaxy.stations:
                    if s.name.lower()==sname.lower(): st=s; break
                if not st: self.logger.system(f"Station '{sname}' not found."); return
                if rid not in RESOURCES: self.logger.system(f"Unknown resource '{rid}'."); return
                hist=st.price_history.get(rid,[])
                if not hist: self.logger.system("No history yet.")
                else:
                    self.logger.system(f"Price history for {rid} at {st.name} (last {len(hist)} ticks):")
                    for i,(b,s) in enumerate(hist[-10:]):
                        self.logger.system(f"  t-{len(hist)-i}: buy:{b} sell:{s}")
            else: self.logger.system("market scan [range] | market history <station> <resource>")
        elif c=="cargo":
            if len(p)>=2 and p[1]=="jettison":
                rid=p[2] if len(p)>=3 else ""
                amt=int(p[3]) if len(p)>=4 else 1
                if rid not in RESOURCES: self.logger.system(f"Unknown '{rid}'."); return
                if self.ship.cargo.remove(rid,amt): self.logger.system(f"Jettisoned {amt} {rid}.")
                else: self.logger.system(f"Not enough {rid}.")
            elif len(p)>=2 and p[1]=="sellall":
                st=self.galaxy.get_nearest_station(self.player_x,self.player_y,1)
                if not st: self.logger.system("No station nearby."); return
                total=0
                for rid in list(self.ship.cargo.items.keys()):
                    info=RESOURCES.get(rid,{})
                    if info.get("cat")=="raw":
                        amt=self.ship.cargo.has(rid)
                        if amt>0:
                            msg=st.buy_from(self.ship,rid,amt)
                            if "Sold" in msg: total+=1
                self.logger.system(f"Sellall complete. {total} raw items sold.")
            else:
                self.push_screen(CargoScreen())
        elif c=="blackmarket" and len(p)>=2 and p[1]=="list":
            st=self.galaxy.get_nearest_station(self.player_x,self.player_y,1)
            if not st: self.logger.system("No station."); return
            if self.ship.reputation.get(st.faction,0)>=-20:
                self.logger.system("No black market here (rep >= -20).")
                return
            self.logger.system(f"Black market at {st.name} (prices ×2-5):")
            for rid in sorted(RESOURCES):
                stock=st.inventory.get(rid,0)
                if stock>0:
                    bp,sp=st.prices.get(rid,(0,0))
                    bm_b=int(bp*random.uniform(2,5)); bm_s=int(sp*random.uniform(2,5))
                    self.logger.system(f"  {rid:<12} buy:{bm_b:>4} sell:{bm_s:>4} stock:{stock}")
        elif c=="smuggle" and len(p)>=3:
            rid=p[1]
            try: amt=int(p[2])
            except: self.logger.system("smuggle <res> <amt>"); return
            st=self.galaxy.get_nearest_station(self.player_x,self.player_y,1)
            if not st: self.logger.system("No station."); return
            banned=CONTRABAND.get(st.faction,[])+CONTRABAND.get(st.religion,[])
            if rid not in banned: self.logger.system(f"{rid} is not contraband here."); return
            if self.ship.cargo.has(rid)<amt: self.logger.system(f"Not enough {rid}."); return
            if random.random()<0.2:  # 20% scan chance
                self.ship.cargo.remove(rid,amt)
                self.ship.reputation[st.faction]=max(-100,self.ship.reputation.get(st.faction,0)-5)
                self.logger.danger(f"Patrol scanned you! {amt} {rid} confiscated. Rep -5.")
            else:
                bp,_=st.prices.get(rid,(0,0))
                price=int(bp*random.uniform(2,4))
                total=price*amt
                self.ship.cargo.remove(rid,amt); self.ship.credits+=total
                self.logger.exploration(f"Smuggled {amt} {rid} for {total}cr!")
        elif c=="reputation":
            self.logger.system("Reputation:")
            for f in sorted(FACTIONS):
                v=self.ship.reputation.get(f,0)
                self.logger.system(f"  {FACTIONS[f]['name']:<18} {v:>4}")
        elif c=="diplomacy":
            self.logger.system("Diplomacy:")
            for f1 in sorted(FACTIONS):
                for f2,st in self.galaxy.diplomacy.get(f1,{}).items():
                    if f1<f2: self.logger.system(f"  {FACTIONS[f1]['name']:<14} vs {FACTIONS[f2]['name']:<14} = {st}")
        elif c=="declare" and len(p)>=3 and p[1]=="war":
            t=p[2]
            if t not in FACTIONS: self.logger.system(f"Unknown. Options: {', '.join(FACTIONS)}"); return
            for f in FACTIONS:
                if f!=t and t in self.galaxy.diplomacy.get(f,{}): self.galaxy.diplomacy[f][t]="war"
            self.ship.reputation[t]=max(-100,self.ship.reputation.get(t,0)-20)
            self.galaxy.add_news(f"War on {t}!",f"Captain declares war!"); self.logger.system(f"War on {t}!")
        elif c=="attack" and len(p)>=2:
            name=" ".join(p[1:])
            npc=self.galaxy.get_npc_by_name(name)
            if not npc or not npc.alive or max(abs(npc.x-self.player_x),abs(npc.y-self.player_y))>1:
                self.logger.system(f"No NPC '{name}' nearby."); return
            npc.take_damage(25); self.logger.combat(f"Hit {npc.name}! {npc.hull}/{npc.max_hull}")
            if npc.faction in self.ship.reputation:
                self.ship.reputation[npc.faction]=max(-100,self.ship.reputation[npc.faction]-5)
            if not npc.alive:
                r=random.randint(50,150); self.ship.credits+=r; self.logger.combat(f"{npc.name} destroyed! +{r}cr")
        elif c=="hail": self._act_hail_npc()
        elif c=="missions":
            if self.galaxy.events_queue:
                for ev in self.galaxy.events_queue: self.logger.system(f"Event: {ev.name}")
            else: self.logger.system("No missions.")
        elif c=="news":
            self._prev_state=self.state; self.state=GameState.NEWS; self.update_map(); self.update_info()
        elif c=="exit": self.exit()
        else: self.logger.system(f"Unknown '{c}'. Type 'help'.")

    def on_key(self,event):
        if self.state==GameState.RACE_SELECT:
            if event.key in("1","2","3","4","5"): self.select_race(event.key)
            elif event.key in("enter"," "): self.select_race("")
            return
        if self.state==GameState.START_SCREEN:
            if event.key=="h": self.state=GameState.HELP; self.update_map(); self.update_info(); return
            if event.key=="n": self._prev_state=GameState.START_SCREEN; self.state=GameState.NEWS; self.update_map(); self.update_info(); return
            self.state=GameState.PLAYING
            self.logger.system(f"{RACES.get(self.ship.race,{}).get('name','A traveller')} ventures forth...")
            self.update_map(); self.update_info(); return
        if self.state==GameState.HELP: self.state=GameState.START_SCREEN; self.update_map(); self.update_info(); return
        if self.state==GameState.NEWS: self.state=self._prev_state; self.update_map(); self.update_info(); return
        if self.state==GameState.GAME_OVER:
            if event.key=="r": self.restart_game()
            elif event.key=="q": self.exit()
            return
        if self.state==GameState.INTERACTING:
            if event.key=="escape":
                self.logger.system("Cancelled."); self.state=GameState.PLAYING; self.update_map(); self.update_info()
            else:
                for k,_,hn,_ in self.interaction_actions:
                    if event.key==k: self._run_interaction(hn); break
                else: self.state=GameState.PLAYING; self.update_map(); self.update_info()
            return
        if self.state==GameState.INSPECTING:
            if event.key in("escape","i"):
                self.state=GameState.PLAYING; self.update_map(); self.update_info(); return
            if event.key in("up","w"): self.cursor_y=max(0,self.cursor_y-1)
            elif event.key in("down","s"): self.cursor_y=min(self.galaxy.height-1,self.cursor_y+1)
            elif event.key in("left","a"): self.cursor_x=max(0,self.cursor_x-1)
            elif event.key in("right","d"): self.cursor_x=min(self.galaxy.width-1,self.cursor_x+1)
            self.update_map(); self.update_info(); return
        if self.state==GameState.PAUSED:
            if event.key=="c": self.state=GameState.PLAYING; self.update_map(); self.update_info()
            elif event.key=="r": self.restart_game()
            elif event.key=="q": self.exit()
            return
        # PLAYING
        if event.key=="escape": self.state=GameState.PAUSED; self.update_map(); self.update_info()
        elif event.key in("up","w"): self.move_player(0,-1)
        elif event.key in("down","s"): self.move_player(0,1)
        elif event.key in("left","a"): self.move_player(-1,0)
        elif event.key in("right","d"): self.move_player(1,0)
        elif event.key=="q": self.exit()
        elif event.key=="e":
            self.interaction_actions=self._get_available_interactions()
            if self.interaction_actions:
                ts=list(dict.fromkeys(t for _,_,_,t in self.interaction_actions))
                self.logger.system(f"Interact: {', '.join(ts)}"); self.state=GameState.INTERACTING
            else: self.logger.system("Nothing here.")
            self.update_map(); self.update_info()
        elif event.key=="i":
            self.state=GameState.INSPECTING; self.cursor_x,self.cursor_y=self.player_x,self.player_y
            self.logger.system("Inspect mode."); self.update_map(); self.update_info()
        elif event.key=="n":
            self._prev_state=self.state; self.state=GameState.NEWS; self.update_map(); self.update_info()
        elif event.key=="b":
            st=self.galaxy.get_station_at(self.player_x,self.player_y)
            if st: self.push_screen(TradeScreen(st))
            else: self.logger.system("No station here.")
            self.update_map(); self.update_info()
        elif event.key=="f":
            for p in self.galaxy.pirates:
                if p.alive and max(abs(p.x-self.player_x),abs(p.y-self.player_y))<=1:
                    self._act_fire_pirate(); break
            else: self.logger.system("No pirate.")
            self.update_map(); self.update_info()
        elif event.key==" ":
            self.logger.system("Waiting..."); self.tick_world()
        elif event.key in("`","grave_accent","asciitilde"): self.push_screen(CommandScreen())

if __name__=="__main__":
    app=GalaxyMapApp(); app.run()

