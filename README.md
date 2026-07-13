# Galaxy Map — Console Space RPG

A procedurally generated galaxy explorer built with Python and [Textual](https://textual.textualize.io/).

Navigate a living galaxy of 80×40 tiles — trade at stations, fight pirates, manage your ship's modules and power, build reputation with warring factions, and survive random events.

![Python](https://img.shields.io/badge/python-3.12-blue)
![Textual](https://img.shields.io/badge/textual-0.80+-orange)

---

## Quick Start

```bash
# Requires Python 3.12+
pip install textual

python galaxy_map.py
```

Press `1`–`5` to choose your race, then explore the galaxy.

---

## Controls

| Key | Action |
|-----|--------|
| `W`/`↑` `A`/`←` `S`/`↓` `D`/`→` | Move ship |
| `Space` | Wait — advance time 1 turn |
| `E` | Interact with nearby objects |
| `F` | Fire at adjacent pirate |
| `I` | Inspect / free look around |
| `B` | Open trade screen (at station) |
| `N` | Galaxy news |
| `H` | Help screen |
| `F1` | Bridge — ship status & modules |
| `F2` | Engineering — power distribution |
| `F5` | Crew management |
| `` ` `` / `~` | Console |
| `Esc` | Pause / close screen |
| `Q` | Quit |

---

## Features

### 1. Procedural Galaxy
Each game generates a unique 80×40 map with stars, planets, stations, black holes, wormholes, and drifting asteroid fields. Gravity pulls you toward black holes, radiation burns near stars.

### 2. Dynamic Economy
8 resource types (Ore, Ice, Silicon, Metal, Electronics, Fuel Cells, Shield Modulators, Alien Relics) with base prices. Station prices fluctuate with supply and demand. Market history tracks the last 20 ticks.

### 3. Factions & Diplomacy
6 factions (Imperium, Chaos Cult, Xenos Horde, Machine Collective, Free Traders, Void Covenant) with dynamic diplomatic relations that change through political events and player actions.

### 4. Ship Management
7 compartments (Reactor, Engine, Weapon, Shield, Sensor, Life Support, Cargo) each with modules. Power system — generated vs consumed energy affects all systems. Install new modules to upgrade your ship.

### 5. NPCs & Combat
- **Traders** — follow trade routes, buy/sell at stations
- **Pirates** — scan for targets, attack, steal cargo, flee when damaged
- Fire at pirates with `F`, destroy them for rewards

### 6. Reputation
Your actions affect standing with each faction. High reputation → trade discounts. Low reputation (< -20) → trade blocked (use black market). Attack faction ships → reputation penalty.

### 7. Races
5 playable races with unique traits:
- **Human** — universal, no penalties
- **Mutant** — 50% radiation resistance
- **Xenos Bio** — organic resource bonus
- **Machine Cult** — auto-repair, hated by religions
- **Voidborn** — immune to black hole gravity, hated by all factions

### 8. Random Events
Crusades, warp invasions, church schisms, plagues, supernovae, trade treaties, pirate raids, economic crises — all dynamically generated.

### 9. Console
Press `` ` `` to open the console. Full list of commands:
- `help` — command list
- `scan` — sector info
- `inv` / `inventory` — cargo contents
- `trade buy/sell <res> <amt>` — station trade
- `prices` — station prices
- `market scan [range]` — prices of nearby stations
- `market history <station> <res>` — price trend
- `power <comp> <val>` — set compartment power
- `modules list` — installed modules
- `cargo jettison <res> [amt]` — discard cargo
- `cargo sellall` — sell all raw resources
- `reputation` — faction standing
- `diplomacy` — inter-faction relations
- `declare war <faction>` — declare war
- `attack <name>` — attack NPC by name
- `hail` — talk to nearby NPC
- `smuggle <res> <amt>` — sell contraband
- `blackmarket list` — black market goods
- `news` — galaxy news
- `exit` — quit

---

## Architecture

```
galaxy_map.py    — Main game file (~1300 lines)
game_logger.py   — Logging service with categories & timestamps
rules.md         — Design document
```

Key classes:

- `Galaxy` — world simulation, tile map, stations, NPCs, tick system
- `PlayerShip` — player ship with compartments, modules, power, cargo, crew
- `Station` — independent economy with dynamic pricing
- `NPCShip` / `TraderShip` / `PirateShip` — NPC ships with AI
- `CargoHold` — inventory with capacity limits
- `GalaxyMapApp` — Textual app with game loop, screens, overlays
- `CommandScreen` / `CargoScreen` / `TradeScreen` — UI screens
- `BridgeScreen` / `EngineeringScreen` / `CrewScreen` — ship management

---

## License

MIT License — see [LICENSE](LICENSE)
