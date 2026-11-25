# Pong Dojo — arena 2026

**The game is Marek Matas's.** Pong Dojo was written in autumn 2022 by Marek Matas, with ultra_kevyk and the
other students of his Python course (github.com/MatasMarek/pong_dojo). Their files in this folder —
`pong_dojo.py`, `config.py`, `bot_template.py`, `text_handling.py`, `stery.txt` — are left exactly as they were
at commit `9111df8` (22 Nov 2022). The code carries no licence; this branch (`arena-2026`) is offered back to
the original repository as a pull request, and the original authors decide what happens with it.

The course's goal was an **ultimate pong player**: one function, `robot_move_paddle(ball, left_paddle,
right_paddle, whoami)`, returning two booleans (move or not, up or down), called every tick. Everything in
`dojo/` and `tests/` was added beside the original in November 2026 to finish that idea.

## What is new

| Part | What it does |
|---|---|
| `dojo/engine.py` | The original physics, repeated without pygame, so bots can play headless. |
| `dojo/contract.py` | The bot contract: read-only copies in, at most one key event out per tick. |
| `dojo/bots/tygr.py` | **TYGR · the Ultimate** — the attacker: simulates every reachable shot and spin, winds the spin up. |
| `dojo/bots/drak.py` | **DRAK · the Nemesis** — the reader: same knowledge and limits, reads the opponent's possible shots, hits with the paddle's sweet spot. |
| `dojo/taunts/*.txt` | Each bot's own taunts. The original `stery.txt` is still used too. |
| `dojo/arena.py` | The new arena: menu, four modes, match intro, name cards, score pips, skins, trails, sparks, sound, taunt box, final stats. |
| `dojo/tournament.py` | Headless bot-vs-bot series. |
| `tests/test_physics_unchanged.py` | Proof that the physics and the player limits are unchanged. |

## Added later the same day (G's choices, 16 Nov 12:05)

| Part | What it does |
|---|---|
| `dojo/rules.py` | Rule sets. **Originál 2022** stays locked and is the default. **Realistický**, **Arkáda**, **Zpomalený** and **Vlastní** run the realistic engine; the rules screen has 12 sliders. |
| `dojo/physics2.py` | The realistic engine: paddles with mass (accelerate, top speed, brake), return angle from the contact point, paddle speed passed to the ball, spin from paddle speed that bends the flight and fades, rallies that speed up to a cap, swept collisions (no overshoot, no stuck ball). |
| `dojo/bots/real.py` | TYGR's and DRAK's brain for the realistic engine (same contract, same limits). |
| `dojo/players.py`, `dojo/editor.py` | The player creator: name, title, motto, colours, 7 paddle patterns, avatar face, voice, taunt level, own lines, human or bot (TYGR or DRAK style, skill 1-10). Saved in `players/`. |
| `dojo/looks.py` | Paddle skins and the avatar faces, drawn from code. |
| `dojo/voice.py` | Shouting avatars: Windows' Czech voice (Microsoft Jakub), offline, reshaped per player (growl, echo, robot, pitch); the mouth follows the loudness. Cache in `.voice_cache/` (shipped pre-rendered). |
| `dojo/paths.py` | Where players, voices, rules and settings live: inside the repository, or in `PONG_DOJO_HOME`. |
| `dojo/taunts/*_drsne.txt`, `*_brutalni.txt`, `obecne*.txt` | Three taunt levels: slušné, drsné, brutální. The friend's `stery.txt` sits in the drsné and brutální pools. |
| `tests/test_realistic.py` | Limits under every realistic preset: paddle and ball never exceed their caps, the ball never leaves the field, every preset finishes a bot match. |

Why the realistic presets are tuned the way they are: with a slow ball two perfect bots never miss.
A rally starts slow and speeds up by `zrychlení za úder` until the ball outruns a paddle — that is when
points fall. Realistický: start 5, +0.45 per hit, cap 17 px/tick, paddle 4.5 px/tick.

## Run it

Setup and the full guide: `README-ARENA.md`. In short: `play.cmd` (Windows, double-click) or `./play.sh`,
or `play.cmd --mode bots`. By hand, in this folder: `python -m dojo.arena` (needs pygame-ce, see `requirements.txt`).

Menu: 1 TYGR vs DRAK · 2 you vs TYGR · 3 new match (any two players, any rules) · 4 rules · 5 player creator.
Keys: P pause · +/- speed in a bot match · M sound · F11 (or Alt+Enter) fullscreen, remembered · F12 screenshot · Esc menu.

The stock voice lines come pre-rendered in `.voice_cache/` and play everywhere. New lines (your own taunts) are
rendered with PowerShell 7 (`pwsh`): only it sees Windows' Czech voice, Microsoft Jakub. Windows PowerShell 5.1
sees just the English voices; the renderer refuses to use them, and the taunt then shows without sound. Without
Windows the new lines stay silent too.

## What stayed the same

Field 700 × 500, paddles 20 × 100 moving 2 px per tick, ball radius 7 at 5 px per tick, the spin rule
(a key held at the moment of the hit adds spin; spin bends the ball and is reset only by a goal), 60 ticks per
second, first to 10, the stuck-ball-on-the-wall behaviour. A bot moves exactly as a human does: one key per
direction per tick.

`python -m unittest -v tests.test_physics_unchanged` runs the original code and the new engine side by side on
the same key presses (six runs of up to 30,000 ticks; the last test run compared 166,427 ticks with 1,177 paddle
hits and 294 goals) and fails on the first difference. It also checks that the original files
are byte-identical to `9111df8`.

One case is handled differently: the original crashes with a ZeroDivisionError if the spin accumulator lands on
exactly 0.0 (it happened once in 180,000 test ticks). The engine treats that tick as "no spin change" instead.

## Why spin decides everything

A paddle waiting in the middle can reach any landing spot in time: the ball needs about 124 ticks to cross, and
the paddle covers 248 px in that time. So two perfect defenders rally forever. The only way through is the
spin rule: spin is never reset during a rally, so it grows hit by hit, the ball starts to bend hard, and at
high spin it overshoots the wall for one tick. A ball that is beyond the edge on the receiver's hit tick
cannot be reached by any paddle position. Both bots know this; every point between them is won that way.

## How equal are they

Headless series, `python -m dojo.tournament --matches 20 --seed 1000` (sides swap every match):
**TYGR 13 – 7 DRAK, points 176 – 148** — DRAK takes 46 % of the points. Matches last 4–6 minutes of game time,
rallies up to about 20 hits. TYGR against itself splits evenly (9 – 10), so neither side of the field has an
edge. TYGR keeps a slight lead: it is the Ultimate, DRAK its near-equal.
