import random
from enum import Enum, auto
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Static, Header, Footer, Input, DataTable, Button, ProgressBar
from textual.reactive import reactive
from textual import events

from game_logger import GameLogger, LogLevel

WIDTH, HEIGHT = 80, 40
TILE_EMPTY="·"; TILE_STAR="*"; TILE_PLANET="o"; TILE_STATION="☐"; TILE_TEMPLE="⛪"
TILE_BLACK_HOLE="◉"; TILE_WORMHOLE="⭕"; TILE_ASTEROIDS="░"; TILE_SHIP="@"
TILE_OTHER_SHIP="▲"; TILE_CURSOR="◈"; TILE_TRADER="T"; TILE_PIRATE="P"
DIR_LABELS={(-1,-1):"NW",(0,-1):"N",(1,-1):"NE",(-1,0):"W",(1,0):"E",(-1,1):"SW",(0,1):"S",(1,1):"SE"}

RESOURCES={
    "ore":{"name":"Ore","cat":"raw","base_price":5},
    "ice":{"name":"Ice","cat":"raw","base_price":3},
    "silicon":{"name":"Silicon","cat":"raw","base_price":8},
    "metal":{"name":"Metal","cat":"refined","base_price":20},
    "electronics":{"name":"Electronics","cat":"refined","base_price":45},
    "fuel_cell":{"name":"Fuel Cell","cat":"refined","base_price":30},
    "shield_mod":{"name":"Shield Mod","cat":"advanced","base_price":120},
    "relic":{"name":"Alien Relic","cat":"special","base_price":500},
}
RACES={"human":{"name":"Human"},"mutant":{"name":"Mutant"},"xenos_bio":{"name":"Xenos Bio"},
       "machine_cult":{"name":"Machine"},"voidborn":{"name":"Voidborn"}}
RELIGIONS={"orthodox_church":{"name":"Orthodox Church"},"cult_of_the_void":{"name":"Cult of Void"},
           "machine_god":{"name":"Machine God"},"old_faith":{"name":"Old Faith"}}
FACTIONS={"imperium":{"name":"Imperium"},"chaos_cult":{"name":"Chaos Cult"},"xenos_horde":{"name":"Xenos Horde"},
          "machine_collective":{"name":"Machine Collective"},"free_traders":{"name":"Free Traders"},
          "void_covenant":{"name":"Void Covenant"}}
CONTRABAND={"imperium":["relic"],"orthodox_church":["relic"],"chaos_cult":["shield_mod"],"free_traders":[]}

# ---------- Модули корабля ----------
SHIP_MODULES={
    "fusion_reactor":{"name":"Fusion Reactor","comp":"reactor","energy":0,"power":12,"cost":800,"durability":100,
                      "desc":"Generates 12 power"},
    "ion_drive":{"name":"Ion Drive","comp":"engine","energy":2,"speed":1,"evasion":10,"cost":600,"durability":80,
                 "desc":"Speed +1, evasion +10"},
    "laser_turret":{"name":"Laser Turret","comp":"weapon","energy":3,"damage":15,"accuracy":80,"cost":500,
                    "durability":60,"desc":"Damage 15, accuracy 80"},
    "deflector_shield":{"name":"Deflector Shield","comp":"shield","energy":4,"shield_cap":30,"shield_regen":2,
                        "cost":700,"durability":90,"desc":"Shield +30, regen +2"},
    "long_range_scanner":{"name":"Long Range Scanner","comp":"sensor","energy":2,"sensor_range":5,"cost":400,
                          "durability":50,"desc":"Scan range +5"},
    "cargo_expander":{"name":"Cargo Expander","comp":"cargo","energy":0,"cargo_bonus":25,"cost":300,"durability":40,
                      "desc":"Cargo +25"},
    "life_support":{"name":"Life Support","comp":"life_support","energy":1,"crew_efficiency":10,"cost":200,
                    "durability":30,"desc":"Crew efficiency +10%"},
    "plasma_cannon":{"name":"Plasma Cannon","comp":"weapon","energy":5,"damage":30,"accuracy":60,"cost":900,
                     "durability":70,"desc":"Damage 30, accuracy 60"},
    "armor_plating":{"name":"Armor Plating","comp":"shield","energy":0,"hull_bonus":20,"cost":500,"durability":100,
                     "desc":"+20 hull"},
    "warp_drive":{"name":"Warp Drive","comp":"engine","energy":3,"speed":2,"evasion":5,"cost":1200,"durability":60,
                  "desc":"Speed +2, evasion +5"},
}

COMPARTMENTS=["reactor","engine","weapon","shield","sensor","life_support","cargo"]

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

# ---------- Корабль с отсеками ----------
class ShipModule:
    def __init__(self,mod_id):
        info=SHIP_MODULES.get(mod_id,{})
        self.id=mod_id; self.name=info.get("name",mod_id)
        self.comp=info.get("comp","reactor"); self.energy_consumption=info.get("energy",0)
        self.stats={k:v for k,v in info.items() if k in("power","speed","evasion","damage","accuracy",
                   "shield_cap","shield_regen","sensor_range","cargo_bonus","crew_efficiency","hull_bonus")}
        self.durability=info.get("durability",50); self.max_durability=self.durability
        self.cost=info.get("cost",100); self.active=True; self.desc=info.get("desc","")
    def is_broken(self): return self.durability<=0

class PlayerShip:
    def __init__(self,name="Endeavour",hull=100):
        self.name=name; self.hull=hull; self.fuel=80; self.credits=1000
        self.radiation_shield=False; self.race="human"; self.religion=None
        self.reputation={f:0 for f in FACTIONS}; self.reputation["pirates"]=-10
        self.skill_trade=0; self.cargo=CargoHold(50)
        # Отсеки: {compartment: {power: int, modules: [ShipModule]}}
        self.compartments={c:{"power":5,"modules":[]} for c in COMPARTMENTS}
        # Базовый реактор
        self.compartments["reactor"]["modules"].append(ShipModule("fusion_reactor"))
        self.compartments["engine"]["modules"].append(ShipModule("ion_drive"))
        self.compartments["shield"]["modules"].append(ShipModule("deflector_shield"))
        self.compartments["sensor"]["modules"].append(ShipModule("long_range_scanner"))
        self.crew={"Pilot":None,"Engineer":None,"Tactical":None,"Scientist":None}
    def take_damage(self,amt):
        self.hull=max(0,self.hull-amt); return self.hull>0
    def total_power_generated(self):
        return sum(m.stats.get("power",0) for m in self.compartments["reactor"]["modules"])
    def total_power_consumed(self):
        return sum(m.energy_consumption for c in COMPARTMENTS for m in self.compartments[c]["modules"] if m.active and not m.is_broken())
    def get_effective_stats(self):
        """Возвращает суммарные статы всех активных модулей с учётом энергии."""
        stats={"speed":1,"evasion":0,"damage":0,"accuracy":0,"shield_cap":0,"shield_regen":0,
               "sensor_range":7,"cargo_bonus":0,"crew_efficiency":0,"hull_bonus":0}
        total_power=self.total_power_generated()
        used_power=self.total_power_consumed()
        eff=1.0 if used_power<=total_power else max(0.3,total_power/max(1,used_power))
        for c in COMPARTMENTS:
            for m in self.compartments[c]["modules"]:
                if m.active and not m.is_broken():
                    for k in stats:
                        stats[k]=stats.get(k,0)+m.stats.get(k,0)*eff
        return {k: int(v) for k, v in stats.items()}
    def install_module(self,mod_id):
        """Устанавливает модуль в первый подходящий отсек."""
        info=SHIP_MODULES.get(mod_id)
        if not info: return False
        comp=info.get("comp","reactor")
        if comp not in self.compartments: return False
        self.compartments[comp]["modules"].append(ShipModule(mod_id))
        return True

# ---------- NPC ----------
class NPCShip:
    _id_counter=0
    def __init__(self,x,y,name,hull,faction,race=None,cc=100):
        NPCShip._id_counter+=1
        self.uid=NPCShip._id_counter; self.x=x; self.y=y; self.name=name
        self.hull=hull; self.max_hull=hull; self.faction=faction
        self.race=race or random.choice(list(RACES))
        self.cargo=CargoHold(cc); self.credits=500; self.alive=True
    def take_damage(self,amt):
        self.hull=max(0,self.hull-amt)
        if self.hull<=0: self.alive=False
        return self.alive

class TraderShip(NPCShip):
    TN=["Hornet","Mercury","Venture","Polaris","Comet","Drifter","Nomad"]
    def __init__(self,x,y,route):
        n=random.choice(self.TN)+str(random.randint(1,99))
        f=random.choice(["free_traders","imperium","machine_collective"])
        super().__init__(x,y,n,60,f,None,100)
        self.route=route; self.route_index=0
        self.cargo.add("fuel_cell",20); self.cargo.add("electronics",random.randint(3,8))
        self.cargo.add("metal",random.randint(5,15)); self.credits=random.randint(200,600); self.wait_ticks=0
    def current_target(self,s):
        return s[self.route[self.route_index%len(self.route)]] if self.route and s else None

class PirateShip(NPCShip):
    PN=["Raider","Reaver","Corsair","Buccaneer","Scourge","Viper","Wraith"]
    def __init__(self,x,y):
        n=random.choice(self.PN)+str(random.randint(1,99))
        f=random.choice(["chaos_cult","xenos_horde"])
        super().__init__(x,y,n,40,f,None,30)
        self.credits=random.randint(50,150); self.aggro_range=5; self.flee_threshold=8

# ---------- Станция ----------
class Station:
    NAMES=["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Theta","Nova","Prime","Sol","Haven","Forge"]
    def __init__(self,x,y,name=None,stype=None,faction=None):
        self.x=x; self.y=y; self.name=name or random.choice(self.NAMES)
        self.stype=stype or random.choice(["trade_hub","industrial","research","temple"])
        self.faction=faction or random.choice(list(FACTIONS)); self.religion=None
        self.inventory={}; self.prices={}; self.crisis_ticks=0
        self.price_history={r:[] for r in RESOURCES}; self.missions=[]
        self._init_inventory(); self.update_prices()
    def _init_inventory(self):
        for r in RESOURCES: self.inventory[r]=random.randint(8,25)
    def update_prices(self):
        for rid,info in RESOURCES.items():
            st=self.inventory.get(rid,0); b=info["base_price"]
            f=2.5 if st<4 else 1.8 if st<10 else 0.5 if st>40 else max(0.6,min(1.5,20/max(1,st)))
            bp=int(b*f*0.85); sp=int(b*f*1.15)
            self.prices[rid]=(max(1,bp),max(1,sp))
            self.price_history[rid].append((bp,sp))
            if len(self.price_history[rid])>20: self.price_history[rid]=self.price_history[rid][-20:]
    def update_economy(self):
        if self.crisis_ticks>0: self.crisis_ticks-=1; return
        ti={"trade_hub":{"consume":{"ice":1},"produce":{"electronics":1}},
            "industrial":{"consume":{"ore":2,"ice":1},"produce":{"metal":2}},
            "research":{"consume":{"electronics":1},"produce":{"shield_mod":1}},
            "temple":{"consume":{"relic":1},"produce":{"shield_mod":1}}}.get(self.stype,{})
        for r,a in ti.get("consume",{}).items():
            if r in self.inventory: self.inventory[r]=max(0,self.inventory[r]-a)
        for r,a in ti.get("produce",{}).items():
            self.inventory[r]=self.inventory.get(r,0)+a
        self.update_prices()
    def price_for_player(self,rid,buying,ship):
        if rid not in self.prices: return 0,""
        bp,sp=self.prices[rid]; p=sp if buying else bp; notes=[]
        rep=ship.reputation.get(self.faction,0)
        if buying:
            p=sp
            if rep>50: p=int(p*0.9); notes.append("friend -10%")
            elif rep<-20: p=int(p*1.5); notes.append("hostile +50%")
        else:
            p=bp
            if rep>50: p=int(p*1.1); notes.append("friend +10%")
            elif rep<-20: p=int(p*0.7); notes.append("hostile -30%")
        tb=1+ship.skill_trade*0.02
        p=int(p/tb) if buying else int(p*tb)
        return max(1,p)," ".join(notes)
    def buy_from(self,ship,rid,amt):
        info=RESOURCES.get(rid)
        if not info: return f"Unknown '{rid}'."
        rep=ship.reputation.get(self.faction,0)
        if rep<-20 and self.faction!="pirates": return f"Trade blocked (rep {rep})."
        if ship.cargo.has(rid)<amt: return f"Not enough {info['name']}."
        banned=CONTRABAND.get(self.faction,[])+CONTRABAND.get(self.religion,[])
        if rid in banned and rep>=-20: return f"Contraband! Use smuggle."
        p,_=self.price_for_player(rid,False,ship); t=p*amt
        if not ship.cargo.remove(rid,amt): return "Cargo error."
        ship.credits+=t; self.inventory[rid]=self.inventory.get(rid,0)+amt
        return f"Sold {amt} {info['name']} for {t}cr."
    def sell_to(self,ship,rid,amt):
        info=RESOURCES.get(rid)
        if not info: return f"Unknown '{rid}'."
        rep=ship.reputation.get(self.faction,0)
        if rep<-20 and self.faction!="pirates": return f"Trade blocked (rep {rep})."
        if self.inventory.get(rid,0)<amt: return f"Only {self.inventory.get(rid,0)} {info['name']}."
        p,_=self.price_for_player(rid,True,ship); t=p*amt
        if ship.credits<t: return f"Need {t}, have {ship.credits}."
        if not ship.cargo.add(rid,amt): return f"Cargo full."
        ship.credits-=t; self.inventory[rid]-=amt
        return f"Bought {amt} {info['name']} for {t}cr."
    def price_summary(self):
        parts=[f"{rid}:{sp}" for rid in sorted(RESOURCES) if self.inventory.get(rid,0)>0 for _,sp in [self.prices.get(rid,(0,0))]]
        return f"  {self.name}[{self.stype}] {self.faction}: {','.join(parts[:5])}"

class GameEvent:
    def __init__(self,n,d,dur=0): self.name=n; self.description=d; self.duration=dur
class NewsEntry:
    def __init__(self,h,b,t=0): self.headline=h; self.body=b; self.turn=t

# ---------- Галактика ----------
class Galaxy:
    def __init__(self,width=WIDTH,height=HEIGHT,seed=None):
        self.width=width; self.height=height
        self.seed=seed if seed else random.randint(0,999999)
        random.seed(self.seed)
        self.tiles=[[TILE_EMPTY for _ in range(width)] for _ in range(height)]
        self.objects={}; self.stations=[]; self.traders=[]; self.pirates=[]
        self.events_queue=[]; self.global_crisis_ticks=0
        self.diplomacy={f:{f2:"neutral" for f2 in FACTIONS if f2!=f} for f in FACTIONS}
        self.news=[NewsEntry("Galaxy News","A vast galaxy awaits...")]; self.tick_counter=0
        self._generate()
        self.black_holes=[p for p,o in self.objects.items() if o=='black_hole']
        self.wormholes=[p for p,o in self.objects.items() if o=='wormhole']
    def _generate(self):
        for y in range(self.height):
            for x in range(self.width):
                if random.random()<0.025:
                    self.tiles[y][x]=TILE_STAR; self.objects[(x,y)]="star"
                    if random.random()<0.2:
                        px,py=self._rn(x,y)
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
                x,y=self._rp()
                rt=random.sample(range(len(self.stations)),min(random.randint(3,5),len(self.stations)))
                self.traders.append(TraderShip(x,y,rt))
        for _ in range(random.randint(3,5)):
            x,y=self._rpn("asteroids",5); self.pirates.append(PirateShip(x,y))
    def _rp(self):
        for _ in range(500):
            x,y=random.randint(0,self.width-1),random.randint(0,self.height-1)
            if self.tiles[y][x]==TILE_EMPTY and (x,y) not in self.objects: return x,y
        return random.randint(0,self.width-1),random.randint(0,self.height-1)
    def _rpn(self,ot,sp=5):
        cand=[p for p,o in self.objects.items() if o==ot]
        if not cand: return self._rp()
        cx,cy=random.choice(cand)
        for _ in range(100):
            dx,dy=random.randint(-sp,sp),random.randint(-sp,sp)
            nx,ny=cx+dx,cy+dy
            if 0<=nx<self.width and 0<=ny<self.height and self.tiles[ny][nx]==TILE_EMPTY: return nx,ny
        return self._rp()
    def _rn(self,x,y,md=2):
        return max(0,min(self.width-1,x+random.randint(-md,md))),max(0,min(self.height-1,y+random.randint(-md,md)))
    def get_tile(self,x,y):
        if 0<=x<self.width and 0<=y<self.height: return self.tiles[y][x]
        return " "
    def get_object_info(self,x,y):
        for t in self.traders:
            if t.alive and t.x==x and t.y==y: return f"Trader {t.name}[{t.faction}]"
        for p in self.pirates:
            if p.alive and p.x==x and p.y==y: return f"Pirate {p.name}[{p.faction}]"
        o=self.objects.get((x,y))
        if o:
            n={"star":"Star","planet":"Planet","station":"Station","black_hole":"Black Hole",
               "wormhole":"Wormhole","asteroids":"Asteroids"}.get(o,o.title())
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
    def tick(self,px,py,ps):
        evs=[]
        for bh_x,bh_y in self.black_holes:
            d=max(abs(px-bh_x),abs(py-bh_y))
            if 0<d<=3:
                dx=1 if bh_x>px else -1 if bh_x<px else 0
                dy=1 if bh_y>py else -1 if bh_y<py else 0
                nx,ny=px+dx,py+dy
                if 0<=nx<self.width and 0<=ny<self.height:
                    px,py=nx,ny; evs.append("Gravity pull!")
                    if self.tiles[py][px]==TILE_BLACK_HOLE: evs.append("Black hole!"); return px,py,evs,True
        for y in range(max(0,py-1),min(self.height,py+2)):
            for x in range(max(0,px-1),min(self.width,px+2)):
                if self.tiles[y][x]==TILE_STAR and (x!=px or y!=py):
                    dmg=10
                    if hasattr(ps,'race') and ps.race=="mutant": dmg=int(dmg*0.5)
                    if not getattr(ps,'radiation_shield',False):
                        ps.take_damage(dmg); evs.append(f"Radiation -{dmg}!")
                        if ps.hull<=0: return px,py,evs,True
        if self.tiles[py][px]==TILE_ASTEROIDS and random.random()<0.3:
            ps.take_damage(5); evs.append("Asteroid -5!")
            if ps.hull<=0: return px,py,evs,True
        for s in self.stations: s.update_economy()
        return px,py,evs,False
    def step_npc(self,px,py,ps,out):
        for t in self.traders:
            if not t.alive: continue
            tg=t.current_target(self.stations)
            if not tg: continue
            if t.x==tg.x and t.y==tg.y:
                if t.wait_ticks<=0: t.wait_ticks=random.randint(2,5)
                else: t.wait_ticks-=1
                if t.wait_ticks<=0: t.route_index+=1; continue
            self._nmt(t,tg.x,tg.y)
            if max(abs(t.x-px),abs(t.y-py))<=1: out.append(f"Trader {t.name} nearby.")
        for p in self.pirates:
            if not p.alive: continue
            tgs=[]
            if max(abs(p.x-px),abs(p.y-py))<=p.aggro_range: tgs.append((px,py,"player"))
            for t in self.traders:
                if t.alive and max(abs(p.x-t.x),abs(p.y-t.y))<=p.aggro_range: tgs.append((t.x,t.y,"trader"))
            if tgs:
                tx,ty,tt=min(tgs,key=lambda c:max(abs(p.x-c[0]),abs(p.y-c[1])))
                if max(abs(p.x-tx),abs(p.y-ty))==1:
                    if tt=="player":
                        ps.take_damage(10); out.append(f"Pirate {p.name} attacks!")
                        if ps.cargo.items:
                            sid=random.choice(list(ps.cargo.items.keys()))
                            sa=max(1,ps.cargo.has(sid)//5); ps.cargo.remove(sid,sa)
                            out.append(f"Stole {sa} {sid}!")
                        if ps.hull<=0: out.append("Destroyed.")
                    else:
                        for t2 in self.traders:
                            if t2.alive and t2.x==tx and t2.y==ty:
                                t2.take_damage(15); out.append(f"Pirate attacks {t2.name}!")
                                if not t2.alive: out.append(f"{t2.name} destroyed."); break
                else: self._nmt(p,tx,ty)
            elif random.random()<0.3: self._nmr(p)
            if p.hull<=p.flee_threshold:
                dx=px-p.x; fx=p.x-(1 if dx>0 else -1 if dx<0 else 0)
                if self.is_passable(fx,p.y): p.x=fx
    def _nmt(self,n,tx,ty):
        dx=1 if tx>n.x else -1 if tx<n.x else 0; dy=1 if ty>n.y else -1 if ty<n.y else 0
        if dx!=0 and self.is_passable(n.x+dx,n.y) and not self._occ(n.x+dx,n.y): n.x+=dx
        elif dy!=0 and self.is_passable(n.x,n.y+dy) and not self._occ(n.x,n.y+dy): n.y+=dy
        else: self._nmr(n)
    def _nmr(self,n):
        for dx,dy in random.sample([(1,0),(-1,0),(0,1),(0,-1)],4):
            nx,ny=n.x+dx,n.y+dy
            if self.is_passable(nx,ny) and not self._occ(nx,ny): n.x,n.y=nx,ny; return
    def _occ(self,x,y):
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
    def compose(self):
        yield Static(id="cargo-header"); yield DataTable(id="cargo-table"); yield Static(id="cargo-footer")
    def on_mount(self):
        app=self.app
        if not isinstance(app,GalaxyMapApp): return
        s=app.ship; c=s.cargo
        self.query_one("#cargo-header").update(f"Cargo: {c.used()}/{c.capacity}  Value: {c.total_value()}cr")
        t=self.query_one("#cargo-table"); t.clear(); t.add_columns("Item","Cat","Qty","Price")
        catmap={"raw":"Raw","refined":"Refined","advanced":"Advanced","special":"Special"}
        for rid,amt in sorted(c.items.items()):
            info=RESOURCES.get(rid,{}); ct=catmap.get(info.get("cat",""),"Other")
            t.add_row(rid,ct,str(amt),f"{info.get('base_price',0)}cr")
        self.query_one("#cargo-footer").update("[Q] Close")
    def on_key(self,event):
        if event.key in("escape","q"): self.dismiss()

class TradeScreen(Screen):
    def __init__(self,station):
        super().__init__(); self.station=station
    def compose(self):
        yield Static(id="trade-header"); yield Static(id="station-goods")
        yield Static(id="player-cargo"); yield Input(placeholder="buy/sell <res> <amt> or close",id="trade-input")
    def on_mount(self):
        app=self.app
        if not isinstance(app,GalaxyMapApp): return
        st=self.station; s=app.ship
        hdr=f"Trading at {st.name}[{st.faction}]  Cr:{s.credits}  Cargo:{s.cargo.used()}/{s.cargo.capacity}"
        self.query_one("#trade-header").update(hdr)
        sg=["── Station ──"]
        for rid in sorted(RESOURCES):
            stk=st.inventory.get(rid,0)
            pb,_=st.price_for_player(rid,True,s); ps,_=st.price_for_player(rid,False,s)
            sg.append(f"  {rid:<12} stock:{stk:<3}  buy:{pb:>4}cr  sell:{ps:>4}cr")
        self.query_one("#station-goods").update("\n".join(sg))
        pc=["── Your Cargo ──"]
        for rid,amt in sorted(s.cargo.items.items()):
            pc.append(f"  {rid:<12} qty:{amt:<3}  val:{RESOURCES.get(rid,{}).get('base_price',0)*amt}cr")
        if not s.cargo.items: pc.append("  (empty)")
        self.query_one("#player-cargo").update("\n".join(pc))
    def on_key(self,event):
        if event.key in("escape","q"): self.dismiss()
    def on_input_submitted(self,event):
        app=self.app
        if not isinstance(app,GalaxyMapApp): return
        v=event.value.strip().lower()
        if v in("close","exit","quit"): self.dismiss(); return
        p=v.split()
        if p and p[0] in("buy","sell"): v="trade "+v
        app.process_command(v); self.on_mount()

# ---------- Экраны управления кораблём ----------
class BridgeScreen(Screen):
    """F1 - Капитанский мостик: сводка всех систем."""
    def compose(self):
        yield Static(id="bridge-title")
        yield Static(id="bridge-systems")
        yield Static(id="bridge-modules")
        yield Static(id="bridge-footer")
    def on_mount(self):
        app=self.app
        if not isinstance(app,GalaxyMapApp): return
        s=app.ship; st=s.get_effective_stats()
        p_gen=s.total_power_generated(); p_con=s.total_power_consumed()
        pct=100 if p_gen==0 else int(p_con/max(1,p_gen)*100)
        title=f"┏━ BRIDGE ━━━━━━━━━━━━━━━━━━ {s.name} ━━━━━━━━━━━━━━━━━━┓"
        sys=f"  Hull: {s.hull}  Fuel: {s.fuel}  Crew: {sum(1 for v in s.crew.values() if v)} assigned"
        sys+=f"\n  Power: {p_gen} gen / {p_con} used ({pct}%)"
        sys+=f"\n  Speed: {st['speed']}  Evasion: {st['evasion']}%"
        sys+=f"\n  Shields: {st['shield_cap']} cap  Regen: {st['shield_regen']}/t"
        sys+=f"\n  Weapons: {st['damage']} dmg  {st['accuracy']}% acc"
        sys+=f"\n  Sensors: {st['sensor_range']} range"
        sys+=f"\n  Credits: {s.credits}  Cargo: {s.cargo.used()}/{s.cargo.capacity+s.stats.get('cargo_bonus',0)}"
        self.query_one("#bridge-title").update(title)
        self.query_one("#bridge-systems").update(sys)
        mods=[]
        for c in COMPARTMENTS:
            for m in s.compartments[c]["modules"]:
                sts="ON" if m.active and not m.is_broken() else "OFF" if m.is_broken() else "ON"
                mods.append(f"  [{sts}] {m.name} ({m.comp}) dur:{m.durability}/{m.max_durability}")
        self.query_one("#bridge-modules").update("── Modules ──\n"+"\n".join(mods) if mods else "── Modules ──\n  None")
        self.query_one("#bridge-footer").update("[F2] Engineering  [F5] Crew  [Esc] Close")
    def on_key(self,event):
        app=self.app
        if not isinstance(app,GalaxyMapApp): return
        if event.key=="escape": self.dismiss()
        elif event.key=="f2": self.dismiss(); app.push_screen(EngineeringScreen())
        elif event.key=="f5": self.dismiss(); app.push_screen(CrewScreen())

class EngineeringScreen(Screen):
    """F2 - Инженерный экран: распределение энергии."""
    def compose(self):
        yield Static(id="eng-title")
        yield Static(id="eng-power")
        yield Static(id="eng-compartments")
        yield Input(placeholder="power <comp> <val> or +/- to adjust",id="eng-input")
    def on_mount(self):
        app=self.app
        if not isinstance(app,GalaxyMapApp): return
        s=app.ship
        title=f"┏━ ENGINEERING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓"
        p_gen=s.total_power_generated(); p_con=s.total_power_consumed()
        pwr=f"  Power: {p_gen} generated / {p_con} used"
        self.query_one("#eng-title").update(title)
        self.query_one("#eng-power").update(pwr)
        comps=[]
        for c in COMPARTMENTS:
            mods=s.compartments[c]["modules"]
            pwr_alloc=s.compartments[c]["power"]
            mod_list=", ".join(f"{m.name}"+("(OFF)"if m.is_broken()else"") for m in mods)
            comps.append(f"  {c:<16} power:{pwr_alloc}  {mod_list}")
        self.query_one("#eng-compartments").update("── Compartments ──\n"+"\n".join(comps))
    def on_key(self,event):
        if event.key=="escape": self.dismiss()
        elif event.key=="f1": self.dismiss(); self.app.push_screen(BridgeScreen()) if hasattr(self.app,'push_screen') else None
    def on_input_submitted(self,event):
        app=self.app
        if not isinstance(app,GalaxyMapApp): return
        v=event.value.strip().lower()
        if v in("close","exit"): self.dismiss(); return
        p=v.split()
        if len(p)>=3 and p[0]=="power" and p[1] in COMPARTMENTS:
            try:
                val=int(p[2]); app.ship.compartments[p[1]]["power"]=max(0,min(10,val))
                app.logger.system(f"Power to {p[1]} set to {val}.")
            except: app.logger.system("power <comp> <0-10>")
        else: app.logger.system("power <compartment> <value>")
        self.on_mount()

class CrewScreen(Screen):
    """F5 - Экипаж: назначение на посты."""
    def compose(self):
        yield Static(id="crew-title"); yield Static(id="crew-list")
        yield Input(placeholder="assign <name> <post> or close",id="crew-input")
    def on_mount(self):
        app=self.app
        if not isinstance(app,GalaxyMapApp): return
        s=app.ship
        title="┏━ CREW ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓"
        cl=["── Posts ──"]
        for post,member in s.crew.items():
            cl.append(f"  {post:<12} {member or '(vacant)'}")
        cl.append("── Available ──")
        cl.append("  (hire crew at stations)")
        self.query_one("#crew-title").update(title)
        self.query_one("#crew-list").update("\n".join(cl))
    def on_key(self,event):
        if event.key=="escape": self.dismiss()
        elif event.key=="f1": self.dismiss(); self.app.push_screen(BridgeScreen())
    def on_input_submitted(self,event):
        app=self.app
        if not isinstance(app,GalaxyMapApp): return
        v=event.value.strip().lower()
        if v in("close","exit"): self.dismiss(); return
        app.logger.system("Crew management: assign <name> <post> (Pilot/Engineer/Tactical/Scientist)")
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
    BridgeScreen Static, EngineeringScreen Static, CrewScreen Static{border:solid $primary;margin:1;padding:0 1;}
    EngineeringScreen Input, CrewScreen Input{dock:bottom;margin:1 2;}
    """
    player_x=reactive(WIDTH//2); player_y=reactive(HEIGHT//2)

    def __init__(self):
        super().__init__()
        self.state=GameState.RACE_SELECT; self.galaxy=Galaxy()
        self.ship=PlayerShip("Endeavour",100)
        self.logger=GameLogger(); self.death_cause=None; self.interaction_actions=[]
        self.cursor_x=WIDTH//2; self.cursor_y=HEIGHT//2
        self._politics_timer=0; self.race_selected=False
        self._prev_state=GameState.START_SCREEN
        self._interaction_active=False
        self._init_player_position()

    def _init_player_position(self):
        self.player_x=WIDTH//2; self.player_y=HEIGHT//2
        while not self.galaxy.is_passable(self.player_x,self.player_y):
            self.player_x=random.randint(0,WIDTH-1); self.player_y=random.randint(0,HEIGHT-1)

    def select_race(self,choice):
        c=choice.lower().strip()
        if c in("1","human",""): self.ship.race="human"
        elif c in("2","mutant"): self.ship.race="mutant"
        elif c in("3","xenos_bio","xenos"): self.ship.race="xenos_bio"
        elif c in("4","machine_cult","machine"): self.ship.race="machine_cult"
        elif c in("5","voidborn","void"): self.ship.race="voidborn"
        self.logger.system(f"Race: {RACES.get(self.ship.race,{}).get('name','Human')}.")
        self.race_selected=True; self.state=GameState.PLAYING; self.update_map(); self.update_info()

    def restart_game(self):
        NPCShip._id_counter=0
        self.state=GameState.RACE_SELECT; self.galaxy=Galaxy()
        self.ship=PlayerShip("Endeavour",100); self.logger.clear()
        self.death_cause=None; self.interaction_actions=[]; self.race_selected=False; self._interaction_active=False
        self._init_player_position(); self.update_map(); self.update_info()

    def compose(self):
        yield Header(); yield Container(Static(id="map"))
        yield Static(id="info-panel"); yield Static(id="log"); yield Footer()

    def on_mount(self): self.update_map(); self.update_info()

    def render_start_screen(self):
        if self.state==GameState.RACE_SELECT:
            self.query_one("#map").update("\n".join(["","","  ┏━ CHOOSE RACE ━━━━━━━━━━━━━━━┓",
                "  ┃ 1 Human    2 Mutant         ┃","  ┃ 3 Xenos Bio  4 Machine       ┃",
                "  ┃ 5 Voidborn                  ┃","  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛","",
                "  Press 1-5 or Enter for Human"])); return
        self.query_one("#map").update("\n".join(["","",
            "  ┏━ GALAXY MAP ━━━━━━━━━━━━━━━━━━━━━━━━┓",
            "  ┃ In the grim darkness of the far     ┃",
            "  ┃ future, there is only war.          ┃",
            "  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
            f"  Race: {RACES.get(self.ship.race,{}).get('name','Human')}",
            "","  WASD Move  E Interact  I Inspect  H Help",
            "  N News  F1 Bridge  F2 Engineering  ~ Console",
            "","  Press any key to start..."]))

    def render_help_screen(self):
        h=["  ┏━ HELP ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
           "  ┃                                                 ┃",
           "  ┃  MOVEMENT:                                      ┃",
           "  ┃    W/↑ N  A/← W  S/↓ S  D/→ E                  ┃",
           "  ┃    Space = wait (advance time 1 turn)            ┃",
           "  ┃                                                 ┃",
           "  ┃  ACTIONS:                                       ┃",
           "  ┃    E = interact with nearby objects              ┃",
           "  ┃    F = fire at adjacent pirate                   ┃",
           "  ┃    I = inspect / free look around                ┃",
           "  ┃    B = open trade screen (at station)            ┃",
           "  ┃                                                 ┃",
           "  ┃  SHIP MANAGEMENT:                               ┃",
           "  ┃    F1 = Bridge (ship status, modules, crew)     ┃",
           "  ┃    F2 = Engineering (power distribution)        ┃",
           "  ┃    F5 = Crew (assign crew to stations)          ┃",
           "  ┃                                                 ┃",
           "  ┃  INTERFACE:                                     ┃",
           "  ┃    H = this help screen      N = galaxy news     ┃",
           "  ┃    ~ = console               Esc = pause menu    ┃",
           "  ┃    Q = quit game                                 ┃",
           "  ┃                                                 ┃",
           "  ┃  CONSOLE COMMANDS (~):                          ┃",
           "  ┃    scan / inv / give/take / refuel / set hull    ┃",
           "  ┃    trade buy/sell <res> <amt> / prices           ┃",
           "  ┃    market scan [r] / market history <st> <res>  ┃",
           "  ┃    power <comp> <val> / modules list             ┃",
           "  ┃    cargo / cargo jettison <res> [amt]            ┃",
           "  ┃    reputation / diplomacy / declare war <f>      ┃",
           "  ┃    attack <name> / hail / smuggle / news / exit  ┃",
           "  ┃                                                 ┃",
           "  ┃  FACTIONS: imperium chaos_cult xenos_horde       ┃",
           "  ┃  machine_collective free_traders void_covenant   ┃",
           "  ┃                                                 ┃",
           "  ┃  RACES: human mutant xenos_bio machine_cult      ┃",
           "  ┃         voidborn                                ┃",
           "  ┃                                                 ┃",
           "  ┃  Rep < -20 = trade blocked (use blackmarket)     ┃",
           "  ┃  Contraband flagged per faction/religion         ┃",
           "  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"]
        lines=["" for _ in range(HEIGHT)]
        cy=max(0,(HEIGHT-len(h))//2)
        for i,ht in enumerate(h):
            if 0<=cy+i<HEIGHT: lines[cy+i]=" "*(max(0,WIDTH-len(ht))//2)+ht
        return "\n".join(lines)

    def render_news_screen(self):
        nt=["  ┏━ GALAXY NEWS ━━━━━━━━━━━━━━━━━━━━━━┓"]
        for e in self.galaxy.news[-8:]:
            nt.append(f"  ┃ [{e.turn}] {e.headline:<35}┃")
            nt.append(f"  ┃ {e.body:<45}┃")
        nt.append("  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
        nt.append("  Press N or any key to return")
        lines=["" for _ in range(HEIGHT)]
        cy=max(0,(HEIGHT-len(nt))//2)
        for i,ht in enumerate(nt):
            if 0<=cy+i<HEIGHT: lines[cy+i]=" "*(max(0,WIDTH-len(ht))//2)+ht
        return "\n".join(lines)

    def render_pause_overlay(self):
        lines=self._build_map_lines()
        ov=["","  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓","  ┃          PAUSED              ┃",
            "  ┃                            ┃","  ┃    C  —  Continue             ┃",
            "  ┃    R  —  Restart            ┃","  ┃    Q  —  Quit                 ┃",
            "  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"]
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
        ov=["  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓","  ┃         GAME OVER            ┃",
            "  ┃                            ┃",f"  ┃  {cause:^30}  ┃",
            "  ┃                            ┃","  ┃    R  —  Restart              ┃",
            "  ┃    Q  —  Quit               ┃","  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"]
        cy=len(lines)//2-len(ov)//2
        for i,o in enumerate(ov):
            idx=cy+i
            if 0<=idx<len(lines):
                pad=max(0,len(lines[0])-len(o))//2
                lines[idx]=lines[idx][:pad]+o+lines[idx][pad+len(o):]
        return "\n".join(lines)

    def render_interaction_menu(self):
        lines=self._build_map_lines()
        acts=self.interaction_actions or [("","Nothing.","","")]
        box_w=44
        ov=[f"  ┏{'━'*(box_w-2)}┓",f"  ┃{'INTERACTION MENU':^{box_w-2}}┃",f"  ┃{'':^{box_w-2}}┃"]
        for _,l,_,_ in acts:
            clean=l[:box_w-6]
            ov.append(f"  ┃  {clean:<{box_w-6}}  ┃")
        ov.extend([f"  ┃{'':^{box_w-2}}┃",f"  ┃{'Esc-Close':^{box_w-2}}┃",f"  ┗{'━'*(box_w-2)}┛"])
        cy=len(lines)//2-len(ov)//2
        for i,o in enumerate(ov):
            idx=cy+i
            if 0<=idx<len(lines):
                pad=max(0,len(lines[0])-len(o))//2
                lines[idx]=lines[idx][:pad]+o+lines[idx][pad+len(o):]
        return "\n".join(lines)

    def _build_map_lines(self):
        lines=[]; show=self.state in(GameState.PLAYING,GameState.INSPECTING)
        show=show or self._interaction_active
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
        elif self._interaction_active: self.query_one("#map").update(self.render_interaction_menu())
        elif self.state==GameState.INSPECTING: self.query_one("#map").update("\n".join(self._build_map_lines()))
        elif self.state==GameState.PAUSED: self.query_one("#map").update(self.render_pause_overlay())
        elif self.state==GameState.GAME_OVER: self.query_one("#map").update(self.render_game_over_screen())
        else: self.query_one("#map").update("\n".join(self._build_map_lines()))

    def _scan_nearby(self,radius=7):
        radius=int(self.ship.get_effective_stats().get("sensor_range",7))
        found=[]
        for dy in range(-radius,radius+1):
            for dx in range(-radius,radius+1):
                if dx==0 and dy==0: continue
                nx,ny=self.player_x+dx,self.player_y+dy; dist=max(abs(dx),abs(dy))
                dk=(1 if dx>0 else -1 if dx<0 else 0,1 if dy>0 else -1 if dy<0 else 0)
                d=DIR_LABELS[dk]
                npc=self.galaxy.get_npc_at(nx,ny)
                if npc:
                    found.append(f"{d}:{TILE_TRADER if isinstance(npc,TraderShip) else TILE_PIRATE}({dist})[{npc.name}]"); continue
                o=self.galaxy.objects.get((nx,ny))
                if o is None: continue
                ic={"star":TILE_STAR,"planet":TILE_PLANET,"station":TILE_STATION,
                    "black_hole":TILE_BLACK_HOLE,"wormhole":TILE_WORMHOLE,"asteroids":TILE_ASTEROIDS}.get(o,"?")
                e=f"{d}:{ic}({dist})"
                if o=="station" and dist<=1:
                    st=self.galaxy.get_station_at(nx,ny)
                    if st: e+=f"[{st.name}|{st.faction}]"
                found.append(e)
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
        cb=self.ship.get_effective_stats().get("cargo_bonus",0)
        return f"Cargo: {'  '.join(p)}  ({self.ship.cargo.used()}/{self.ship.cargo.capacity+cb})"

    def _reputation_summary(self):
        return "  ".join(f"{k}:{v}" for k,v in self.ship.reputation.items() if k in FACTIONS)

    def update_info(self):
        if self.state in(GameState.RACE_SELECT,GameState.START_SCREEN):
            self.query_one("#info-panel").update("H=Help  N=News  F1=Bridge"); self.query_one("#log").update(""); return
        if self.state==GameState.HELP:
            self.query_one("#info-panel").update("H to return."); self.query_one("#log").update(""); return
        if self.state==GameState.NEWS:
            self.query_one("#info-panel").update("N to close."); self.query_one("#log").update(""); return
        if self._interaction_active:
            self.query_one("#info-panel").update("Select or Esc."); self.query_one("#log").update(self.logger.render(10)); return
        if self.state==GameState.PAUSED:
            self.query_one("#info-panel").update("PAUSED"); self.query_one("#log").update(""); return
        if self.state==GameState.GAME_OVER:
            self.query_one("#info-panel").update(f"☠ {self.death_cause or 'Destroyed.'}  R=Restart Q=Quit")
            self.query_one("#log").update(self.logger.render(10)); return
        if self.state==GameState.INSPECTING:
            cx,cy=self.cursor_x,self.cursor_y
            desc=self.galaxy.get_object_info(cx,cy); dist=max(abs(cx-self.player_x),abs(cy-self.player_y))
            extra=""; st=self.galaxy.get_station_at(cx,cy)
            if st: extra=f"\n{st.price_summary()}"
            npc=self.galaxy.get_npc_at(cx,cy)
            if npc: extra=f"\nFaction:{npc.faction} Hull:{npc.hull}/{npc.max_hull}"
            self.query_one("#info-panel").update(f"Inspect: ({cx},{cy}) {desc}\nDist:{dist}{extra}")
            self.query_one("#log").update(self.logger.render(10)); return
        desc=self.galaxy.get_object_info(self.player_x,self.player_y)
        sl=self._get_ship_status(); sline="  "+" | ".join(sl) if sl else "  Nominal"
        nearby=self._scan_nearby(); cargo=self._cargo_summary()
        cval=self.ship.cargo.total_value()
        rn=RACES.get(self.ship.race,{}).get("name","Human"); rl=self.ship.religion or "none"
        rep=self._reputation_summary()
        stn=self.galaxy.get_nearest_station(self.player_x,self.player_y,1)
        econ="\n"+stn.price_summary() if stn else ""
        st=self.ship.get_effective_stats()
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
        et=random.choice(["crusade","invasion","schism","plague","scandal","treaty"])
        if et=="crusade": self.galaxy.add_news("Crusade!","Imperium vs Chaos!"); out.append("[EVENT] Crusade!")
        elif et=="invasion":
            for _ in range(random.randint(3,5)): x,y=self.galaxy._rp(); self.galaxy.pirates.append(PirateShip(x,y))
            self.galaxy.add_news("Invasion!","Hostiles spawned."); out.append("[EVENT] Invasion!")
        elif et=="schism":
            for s in self.galaxy.stations:
                if s.faction=="imperium" and random.random()<0.3: s.crisis_ticks=10
            self.galaxy.add_news("Schism!","Church divided."); out.append("[EVENT] Schism!")
        elif et=="plague":
            t=random.choice(list(FACTIONS))
            for s in self.galaxy.stations:
                if s.faction==t: s.crisis_ticks=10
            self.galaxy.add_news(f"Plague at {t}!"); out.append(f"[EVENT] Plague at {t}!")
        elif et=="scandal":
            f1,f2=random.sample(list(FACTIONS),2)
            if f2 in self.galaxy.diplomacy.get(f1,{}): self.galaxy.diplomacy[f1][f2]="war"
            self.galaxy.add_news("Scandal!"); out.append("[EVENT] Scandal!")
        elif et=="treaty":
            f1,f2=random.sample(list(FACTIONS),2)
            if f2 in self.galaxy.diplomacy.get(f1,{}): self.galaxy.diplomacy[f1][f2]="truce"
            self.galaxy.add_news("Treaty!"); out.append("[EVENT] Treaty!")

    def _check_random_events(self,out):
        if random.random()>0.03: return
        g=self.galaxy; et=random.choice(["caravan","raid","supernova","crisis"])
        if et=="caravan":
            for _ in range(3):
                x,y=g._rp()
                rt=random.sample(range(len(g.stations)),min(3,len(g.stations))) if g.stations else []
                t=TraderShip(x,y,rt); t.cargo=CargoHold(100)
                t.cargo.add("relic",random.randint(1,3)); t.cargo.add("electronics",random.randint(5,15))
                g.traders.append(t)
            g.add_news("Caravan!","Rare goods."); out.append("[EVENT] Caravan!")
        elif et=="raid":
            for _ in range(random.randint(2,4)): x,y=g._rp(); g.pirates.append(PirateShip(x,y))
            g.add_news("Raid!","Pirates."); out.append("[EVENT] Raid!")
        elif et=="supernova" and g.black_holes:
            bh=random.choice(g.black_holes)
            if max(abs(self.player_x-bh[0]),abs(self.player_y-bh[1]))<=10:
                self.ship.take_damage(10); out.append("Supernova! Hull -10.")
                if self.ship.hull<=0: self.death_cause="Supernova."
            g.add_news("Supernova!"); out.append("[EVENT] Supernova!")
        elif et=="crisis":
            g.global_crisis_ticks=10; g.add_news("Crisis!","Prices -30%."); out.append("[EVENT] Crisis!")

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
                    acts.append(("j",f"(J)oin {st.name}","_act_join_religion",f"Temple {dn}"))
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
        if self.ship.credits>=50: self.ship.credits-=50; self.ship.fuel=min(100,self.ship.fuel+20); self.logger.trade(f"Refuel +20. Fuel:{self.ship.fuel}")
        else: self.logger.system(f"Need 50cr.")
    def _act_repair(self):
        if self.ship.credits>=30: self.ship.credits-=30; o=self.ship.hull; self.ship.hull=min(100,self.ship.hull+15); self.logger.trade(f"Hull +{self.ship.hull-o}.")
        else: self.logger.system(f"Need 30cr.")
    def _act_open_trade(self):
        st=self.galaxy.get_station_at(self.player_x,self.player_y)
        if st: self.push_screen(TradeScreen(st))
        else: self.logger.system("No station.")
    def _act_join_religion(self):
        st=self.galaxy.get_station_at(self.player_x,self.player_y)
        if not st or st.stype!="temple": return
        if self.ship.religion: self.logger.system("Already have religion."); return
        if st.religion: self.ship.religion=st.religion; self.logger.system(f"Joined {st.religion}!")
        else: self.logger.system("No doctrine.")
    def _act_scan_planet(self):
        self.logger.exploration(f"Scan: {random.choice(['rocky','gas giant','ice','desert','oceanic'])}, {random.choice(['iron','silicon','water ice','minerals'])}.")
    def _act_land(self):
        outcomes=[("Ruins +50cr",50,""),("Wildlife! Hull-5",-5,""),("Resources +30cr",30,""),("Storm! Hull-8",-8,""),("Traded +20cr",20,""),("Minerals +2ore",0,"ore")]
        msg,delta,cid=random.choice(outcomes)
        if delta>0: self.ship.credits+=delta
        elif delta<0: self.ship.hull=max(0,self.ship.hull+delta)
        if cid and not self.ship.cargo.add(cid,2): msg+=" (full)"
        self.logger.exploration(f"Landed. {msg}")
        if self.ship.hull<=0: self.state=GameState.GAME_OVER; self.death_cause="Killed on planet."
    def _act_mine(self):
        if random.random()<0.6:
            amt=random.randint(2,6)
            if self.ship.cargo.add("ore",amt): self.logger.exploration(f"Mined {amt} ore ({self.ship.cargo.used()}/{self.ship.cargo.capacity})")
            else: self.logger.exploration("Cargo full!")
        else: self.logger.exploration("Depleted.")
    def _act_use_wormhole(self):
        if len(self.galaxy.wormholes)>1:
            o=(self.player_x,self.player_y)
            while o==(self.player_x,self.player_y): o=random.choice(self.galaxy.wormholes)
            self.player_x,self.player_y=o; self.logger.exploration("Teleported!"); self.logger.new_turn()
        else: self.logger.exploration("Collapse!"); self.galaxy.tiles[self.player_y][self.player_x]=TILE_EMPTY
    def _act_hail_npc(self):
        for t in self.galaxy.traders:
            if t.alive and max(abs(t.x-self.player_x),abs(t.y-self.player_y))<=1:
                self.logger.exploration(f"Trader {t.name}[{t.faction}]: Hull {t.hull}/{t.max_hull}"); return
        for p in self.galaxy.pirates:
            if p.alive and max(abs(p.x-self.player_x),abs(p.y-self.player_y))<=1:
                self.logger.danger(f"Pirate {p.name}: 'Back off!'"); return
        self.logger.system("No NPC.")
    def _act_fire_pirate(self):
        for p in self.galaxy.pirates:
            if p.alive and max(abs(p.x-self.player_x),abs(p.y-self.player_y))<=1:
                p.take_damage(20); self.logger.combat(f"Hit {p.name}! {p.hull}/{p.max_hull}")
                if not p.alive:
                    r=random.randint(50,150); self.ship.credits+=r; self.ship.cargo.add("relic",1)
                    self.ship.reputation["free_traders"]=min(100,self.ship.reputation.get("free_traders",0)+2)
                    self.logger.combat(f"{p.name} destroyed! +{r}cr")
                return
        self.logger.system("No pirate.")

    @staticmethod
    def _direction_name(dx,dy):
        return {(0,-1):"N",(0,1):"S",(-1,0):"W",(1,0):"E",(-1,-1):"NW",(1,-1):"NE",(-1,1):"SW",(1,1):"SE"}.get((dx,dy),"?")

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
        if over: self.state=GameState.GAME_OVER; self.death_cause=evs[-1] if evs else "Unknown"; self.logger.danger("Destroyed.")
        self.update_map(); self.update_info()

    def move_player(self,dx,dy):
        if self.state!=GameState.PLAYING: return
        dn=self._direction_name(dx,dy)
        nx,ny=self.player_x+dx,self.player_y+dy
        if 0<=nx<self.galaxy.width and 0<=ny<self.galaxy.height:
            tt=self.galaxy.get_tile(nx,ny)
            if not self.galaxy.is_passable(nx,ny): self.logger.blocked(dn,self.galaxy.get_object_info(nx,ny)); self.update_info(); return
            if tt==TILE_WORMHOLE:
                if len(self.galaxy.wormholes)>1:
                    o=(nx,ny)
                    while o==(nx,ny): o=random.choice(self.galaxy.wormholes)
                    nx,ny=o; self.logger.exploration("Teleported!")
                else: self.logger.exploration("Collapse.")
            self.player_x,self.player_y=nx,ny
            self.ship.fuel=max(0,self.ship.fuel-1)
            self.logger.movement(dn,self.player_x,self.player_y); self.logger.new_turn()
            self.tick_world()
        self.update_map(); self.update_info()

    def process_command(self,raw):
        raw=raw.strip()
        if not raw: self.logger.system("Type 'help'."); return
        p=raw.split(); c=p[0].lower()
        if c=="help":
            self.logger.system("── COMMANDS ──")
            self.logger.system("scan inv give/take refuel set hull")
            self.logger.system("trade buy/sell prices market scan/history")
            self.logger.system("cargo cargo jettison/sellall")
            self.logger.system("power <comp> <val>  modules list")
            self.logger.system("blackmarket list smuggle")
            self.logger.system("reputation diplomacy declare war attack hail missions news exit")
            self.logger.system("── KEYS ──")
            self.logger.system("WASD E I F N H F1 F2 F5 ~ Esc")
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
        elif c=="refuel": self.ship.fuel=100; self.logger.system("Refuelled to 100.")
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
                pb,_=st.price_for_player(rid,True,self.ship); ps,_=st.price_for_player(rid,False,self.ship)
                sk=st.inventory.get(rid,0)
                self.logger.system(f"  {rid:<12} buy:{pb:>4} sell:{ps:>4} stock:{sk}")
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
                            sp,_=st.price_for_player(rid,True,self.ship); bp,_=st.price_for_player(rid,False,self.ship)
                            self.logger.system(f"    {rid:<12} buy:{sp:>4} sell:{bp:>4} stock:{st.inventory.get(rid,0)}")
            elif len(p)>=4 and p[1]=="history":
                sname=p[2]; rid=p[3]
                st=None
                for s in self.galaxy.stations:
                    if s.name.lower()==sname.lower(): st=s; break
                if not st: self.logger.system(f"Station '{sname}' not found."); return
                if rid not in RESOURCES: self.logger.system(f"Unknown '{rid}'."); return
                hist=st.price_history.get(rid,[])
                if not hist: self.logger.system("No history.")
                else:
                    self.logger.system(f"History for {rid} at {st.name}:")
                    for i,(b,s) in enumerate(hist[-10:]): self.logger.system(f"  t-{len(hist)-i}: buy:{b} sell:{s}")
            else: self.logger.system("market scan [range] | market history <station> <res>")
        elif c=="power" and len(p)>=3:
            comp=p[1]
            try: val=int(p[2])
            except: self.logger.system("power <comp> <0-10>"); return
            if comp not in COMPARTMENTS: self.logger.system(f"Unknown: {comp}"); return
            self.ship.compartments[comp]["power"]=max(0,min(10,val))
            self.logger.system(f"Power to {comp} set to {val}.")
        elif c=="modules" and len(p)>=2 and p[1]=="list":
            self.logger.system("── Installed Modules ──")
            for c2 in COMPARTMENTS:
                for m in self.ship.compartments[c2]["modules"]:
                    sts="ON" if m.active and not m.is_broken() else "OFF" if m.is_broken() else "ON"
                    self.logger.system(f"  [{sts}] {m.name} ({c2}) dur:{m.durability}/{m.max_durability} pow:{m.energy_consumption}")
        elif c=="cargo":
            if len(p)>=2 and p[1]=="jettison":
                rid=p[2] if len(p)>=3 else ""; amt=int(p[3]) if len(p)>=4 else 1
                if rid not in RESOURCES: self.logger.system(f"Unknown '{rid}'."); return
                if self.ship.cargo.remove(rid,amt): self.logger.system(f"Jettisoned {amt} {rid}.")
                else: self.logger.system(f"Not enough {rid}.")
            elif len(p)>=2 and p[1]=="sellall":
                st=self.galaxy.get_nearest_station(self.player_x,self.player_y,1)
                if not st: self.logger.system("No station."); return
                total=0
                for rid in list(self.ship.cargo.items.keys()):
                    if RESOURCES.get(rid,{}).get("cat")=="raw":
                        amt=self.ship.cargo.has(rid)
                        if amt>0 and "Sold" in st.buy_from(self.ship,rid,amt): total+=1
                self.logger.system(f"Sold {total} raw items.")
            else: self.push_screen(CargoScreen())
        elif c=="blackmarket" and len(p)>=2 and p[1]=="list":
            st=self.galaxy.get_nearest_station(self.player_x,self.player_y,1)
            if not st: self.logger.system("No station."); return
            if self.ship.reputation.get(st.faction,0)>=-20: self.logger.system("No black market."); return
            self.logger.system(f"Black market at {st.name}:")
            for rid in sorted(RESOURCES):
                sk=st.inventory.get(rid,0)
                if sk>0:
                    bp,sp=st.prices.get(rid,(0,0))
                    self.logger.system(f"  {rid:<12} buy:{int(bp*random.uniform(2,5)):>4} sell:{int(sp*random.uniform(2,5)):>4}")
        elif c=="smuggle" and len(p)>=3:
            rid=p[1]
            try: amt=int(p[2])
            except: self.logger.system("smuggle <res> <amt>"); return
            st=self.galaxy.get_nearest_station(self.player_x,self.player_y,1)
            if not st: self.logger.system("No station."); return
            banned=CONTRABAND.get(st.faction,[])+CONTRABAND.get(st.religion,[])
            if rid not in banned: self.logger.system(f"{rid} not contraband here."); return
            if self.ship.cargo.has(rid)<amt: self.logger.system(f"Not enough {rid}."); return
            if random.random()<0.2:
                self.ship.cargo.remove(rid,amt); self.ship.reputation[st.faction]=max(-100,self.ship.reputation.get(st.faction,0)-5)
                self.logger.danger(f"Scanned! Lost {amt} {rid}.")
            else:
                bp,_=st.prices.get(rid,(0,0)); t=int(bp*random.uniform(2,4))*amt
                self.ship.cargo.remove(rid,amt); self.ship.credits+=t
                self.logger.exploration(f"Smuggled {amt} {rid} for {t}cr!")
        elif c=="reputation":
            self.logger.system("Reputation:")
            for f in sorted(FACTIONS): self.logger.system(f"  {FACTIONS[f]['name']:<18} {self.ship.reputation.get(f,0):>4}")
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
            self.galaxy.add_news(f"War on {t}!"); self.logger.system(f"War on {t}!")
        elif c=="attack" and len(p)>=2:
            name=" ".join(p[1:])
            npc=self.galaxy.get_npc_by_name(name)
            if not npc or not npc.alive or max(abs(npc.x-self.player_x),abs(npc.y-self.player_y))>1:
                self.logger.system(f"No '{name}' nearby."); return
            npc.take_damage(25); self.logger.combat(f"Hit {npc.name}! {npc.hull}/{npc.max_hull}")
            if npc.faction in self.ship.reputation: self.ship.reputation[npc.faction]=max(-100,self.ship.reputation[npc.faction]-5)
            if not npc.alive: self.ship.credits+=random.randint(50,150); self.logger.combat(f"{npc.name} destroyed!")
        elif c=="hail": self._act_hail_npc()
        elif c=="missions":
            if self.galaxy.events_queue: self.logger.system("Active events.")
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
            if event.key=="h": self._prev_state=GameState.START_SCREEN; self.state=GameState.HELP; self.update_map(); self.update_info(); return
            if event.key=="n": self._prev_state=GameState.START_SCREEN; self.state=GameState.NEWS; self.update_map(); self.update_info(); return
            self.state=GameState.PLAYING; self.logger.system("Journey begins..."); self.update_map(); self.update_info(); return
        if self.state==GameState.HELP: self.state=self._prev_state; self.update_map(); self.update_info(); return
        if self.state==GameState.NEWS: self.state=self._prev_state; self.update_map(); self.update_info(); return
        if self.state==GameState.GAME_OVER:
            if event.key=="r": self.restart_game()
            elif event.key=="q": self.exit()
            return
        # INTERACTING is now handled via _interaction_active flag in PLAYING section above
        if self.state==GameState.INSPECTING:
            if event.key in("escape","i"): self.state=GameState.PLAYING; self.update_map(); self.update_info(); return
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
        elif self._interaction_active and len(event.key)==1 and event.key.isalnum():
            if event.key=="escape":
                self._interaction_active=False; self.update_map(); self.update_info()
            else:
                for k,_,hn,_ in self.interaction_actions:
                    if event.key==k:
                        self._interaction_active=False
                        self._run_interaction(hn)
                        break
                else:
                    self._interaction_active=False; self.update_map(); self.update_info()
        elif event.key in ("up","w"): self.move_player(0,-1)
        elif event.key in ("down","s"): self.move_player(0,1)
        elif event.key in ("left","a"): self.move_player(-1,0)
        elif event.key in ("right","d"): self.move_player(1,0)
        elif event.key=="q": self.exit()
        elif event.key=="e":
            self.interaction_actions=self._get_available_interactions()
            if self.interaction_actions:
                self._interaction_active=True
                self.update_map(); self.update_info()
            else: self.logger.system("Nothing.")
        elif event.key=="h":
            self._prev_state=self.state; self.state=GameState.HELP; self.update_map(); self.update_info()
        elif event.key=="i": self.state=GameState.INSPECTING; self.cursor_x,self.cursor_y=self.player_x,self.player_y; self.logger.system("Inspect."); self.update_map(); self.update_info()
        elif event.key=="n": self._prev_state=self.state; self.state=GameState.NEWS; self.update_map(); self.update_info()
        elif event.key=="b":
            st=self.galaxy.get_station_at(self.player_x,self.player_y)
            if st: self.push_screen(TradeScreen(st)); self.update_map(); self.update_info()
            else: self.logger.system("No station.")
        elif event.key=="f":
            for p in self.galaxy.pirates:
                if p.alive and max(abs(p.x-self.player_x),abs(p.y-self.player_y))<=1: self._act_fire_pirate(); break
            else: self.logger.system("No pirate.")
            self.update_map(); self.update_info()
        elif event.key in ("f1","F1"): self.push_screen(BridgeScreen())
        elif event.key in ("f2","F2"): self.push_screen(EngineeringScreen())
        elif event.key in ("f5","F5"): self.push_screen(CrewScreen())
        elif event.key==" ":
            self.logger.system("Waiting..."); self.tick_world()
        elif event.key in ("`","grave_accent","asciitilde"): self.push_screen(CommandScreen())

if __name__=="__main__":
    app=GalaxyMapApp(); app.run()
