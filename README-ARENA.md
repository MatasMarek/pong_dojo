# Pong Dojo — arena 2026

A new arena for **Pong Dojo**, the game Marek Matas wrote in autumn 2022 with ultra_kevyk and the other
students of his Python course — original repository: **[MatasMarek/pong_dojo](https://github.com/MatasMarek/pong_dojo)**.
The course's goal was an *ultimate pong player*: one function, `robot_move_paddle(...)`, that returns
"move or not, up or down" every tick. This branch finishes that idea and builds a full game around it.

The original files (`pong_dojo.py`, `config.py`, `bot_template.py`, `text_handling.py`, `stery.txt`) are
untouched, byte for byte, at commit `9111df8`; a test checks it. Everything new sits beside them in `dojo/`
and `tests/`. The history of the new parts is in `DOJO.md`.

## What is in it

- **Two ultimate bots.** **TYGR · the Ultimate** (attacker: simulates every reachable shot and spin) and
  **DRAK · the Nemesis** (reader: anticipates the opponent's shots). Same knowledge, same limits as a human:
  one key per direction per tick. Over 20 matches TYGR wins 13 – 7, DRAK takes 46 % of the points.
- **The arena.** Menu, four modes, match intro, name cards, score pips, paddle skins, trails, sparks, sound,
  shouting avatars with a taunt box, final statistics, fullscreen.
- **Rules.** *Originál 2022* — the original physics, proven identical and locked — plus a realistic engine
  with presets and 12 sliders.
- **Player creator.** Make your own player, human or bot.
- **Czech voices.** Taunts are shouted by Windows' Czech voice (Microsoft Jakub), reshaped per avatar. The
  stock lines ship pre-rendered in `.voice_cache/`, so they play on any system.

## Setup

You need Python 3 (tested with 3.14 on Windows 11).

```sh
git clone -b arena-2026 https://github.com/bitSrbak/pong_dojo.git
cd pong_dojo
python -m venv .venv
```

Windows:

```bat
.venv\Scripts\python -m pip install -r requirements.txt
play.cmd
```

macOS / Linux:

```sh
.venv/bin/python -m pip install -r requirements.txt
./play.sh
```

`requirements.txt` holds one package: `pygame-ce` 2.5.8. The launchers use `.venv` in this folder if it
exists, otherwise the Python on your PATH. By hand: `python -m dojo.arena` in this folder.

## How to play

**Menu:** `1` TYGR vs DRAK · `2` you vs TYGR · `3` new match (any two players, any rules) · `4` rules ·
`5` player creator. Arrows (or W/A/S/D) and Enter move through every screen; Esc goes back.

**In a match:**

| Key | What |
|---|---|
| W / S | left player up / down |
| ↑ / ↓ | right player up / down (alone against a bot, both sets work) |
| P or Space | pause |
| `+` / `-` | speed up / slow down a bot match |
| M | sound on / off |
| F11 or Alt+Enter | fullscreen on / off (remembered) |
| F12 | screenshot into `shots/` |
| Esc | back to the menu |

**Straight into a match:** `play.cmd --mode bots` (or `tygr`, `drak`, `duel`), with `--rules Realistický`,
`--fullscreen`, `--speed 3`, `--seed 42`. `python -m dojo.arena --help` lists everything.

**Spin decides everything (original rules).** Keep a key held at the moment you hit the ball and it gets
spin. Spin grows with every hit and is reset only by a goal; a strongly spun ball bends hard and can
overshoot the wall for one tick, out of anyone's reach. That is how the bots score against each other.

## Rules presets

| Preset | Engine | In short |
|---|---|---|
| **Originál 2022** (default, locked) | the original physics | Field 700 × 500, paddle 100 px at 2 px/tick, ball 5 px/tick, spin rule, first to 10 |
| **Realistický** | realistic | paddles with mass, return angle from the contact point, rallies speed up from 5 to 17 px/tick |
| **Arkáda** | realistic | fast ball, strong spin, first to 7 |
| **Zpomalený** | realistic | slow motion, good for learning |
| **Vlastní** | realistic | your own: 12 sliders on the rules screen (`4`) |

A fresh clone starts with `rules.default.json` (Originál 2022). The rules you play last are kept in
`rules.json`, which stays out of git.

## Player creator

Menu `5`. Name, title, motto, colours, 7 paddle patterns, an avatar face (shape, eyes, mouth, top, marks),
a voice (pitch and effect: growl, echo, robot), a taunt level (*slušné* polite, *drsné* rough, *brutální*
brutal), your own lines, and a brain: human (keys) or a bot in TYGR's or DRAK's style with skill 1 – 10.
Players are saved as JSON in `players/` (kept local by `.gitignore`; delete that line to share yours).

**Voices for new lines** (your own taunts) are rendered on Windows with PowerShell 7 (`pwsh`), the only
shell that sees the Czech voice Microsoft Jakub. Without it — or on macOS / Linux — new lines show in the
taunt box without sound; the game itself runs the same.

## Tests and the bot series

In this folder:

```sh
python -m unittest -v tests.test_physics_unchanged tests.test_realistic
```

10 tests, about a minute. `test_physics_unchanged` runs the original `pong_dojo.py` and the new engine side
by side on the same key presses for tens of thousands of ticks and fails on the first difference; it also
checks that the original files are unchanged (it needs the git history, so run it in a clone).
`test_realistic` checks the limits under every realistic preset.

Headless bot series (sides swap every match):

```sh
python -m dojo.tournament --matches 20 --seed 1000
python -m dojo.tournament --matches 20 --seed 1000 --rules Real
```

## Code map — where to improve it

| File | What it does |
|---|---|
| `dojo/engine.py` | the original physics without pygame (headless, proven identical) |
| `dojo/physics2.py` | the realistic engine: paddle mass, angles, speed transfer, spin, swept collisions |
| `dojo/rules.py` | rule presets, the slider list, saving the last rules |
| `dojo/contract.py` | the bot contract: read-only copies in, at most one key per direction out |
| `dojo/bots/tygr.py`, `drak.py` | the two ultimate bots for the original rules; `common.py` their shared shot simulation |
| `dojo/bots/real.py` | both bots' brain for the realistic engine |
| `dojo/arena.py` | the game: menu, modes, drawing, effects, sound, taunts, screenshots |
| `dojo/players.py`, `editor.py` | built-in and created players, the creator screen |
| `dojo/looks.py` | paddle skins and avatar faces, drawn from code |
| `dojo/voice.py` | voice rendering (Windows), per-avatar shaping, mouth movement |
| `dojo/taunts/*.txt` | taunts per bot and level; `stery.txt` (original) joins the rough and brutal pools |
| `dojo/paths.py` | where players, voices, rules and settings live |
| `dojo/tournament.py` | headless bot-vs-bot series |

**Write your own bot:** copy `dojo/bots/tygr.py`, keep its `make(seed, rules)` function, and add it in
`dojo/players.py` (`BRAINS` and `make_brain`). The contract in `dojo/contract.py` makes sure it plays with
a human's limits. Test it with `dojo.tournament`.

**Keep your files elsewhere:** set `PONG_DOJO_HOME` to a folder, and players, voices, settings and
screenshots go there instead of into this repository.

## Credit

The game, its physics and the bot contract: **Marek Matas**, ultra_kevyk and the students of the 2022
Python course — [MatasMarek/pong_dojo](https://github.com/MatasMarek/pong_dojo). The original code carries
no licence; this branch is offered back to them, and they decide what to do with it. The arena, the bots
TYGR and DRAK, the realistic engine and the player creator were added in November 2026 by bitSrbak, built
with Claude.
