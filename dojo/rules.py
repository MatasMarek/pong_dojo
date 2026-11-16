"""Rule sets for the arena.

"Originál 2022" is the friend's game exactly (dojo/engine.py, proven by
tests/test_physics_unchanged.py) and cannot be edited. Every other preset runs the
realistic engine (dojo/physics2.py) with the numbers below, and the rules screen can
change them. Both players, human or bot, always play under the same numbers.
"""
import json
import os
from dataclasses import dataclass, asdict, field, replace

from config import HEIGHT, PADDLE_HEIGHT, WINNING_SCORE


@dataclass
class Rules:
    name: str = 'Originál 2022'
    engine: str = 'original'          # 'original' or 'realistic'
    ball_speed: float = 5.0           # px per tick at the serve
    speedup: float = 0.25             # px per tick added by every paddle hit
    max_ball_speed: float = 11.0      # px per tick cap
    paddle_speed: float = 6.0         # top paddle speed, px per tick
    paddle_accel: float = 0.6         # px per tick², how fast a paddle gets going
    paddle_height: int = PADDLE_HEIGHT
    max_angle: float = 55.0           # steepest return, degrees from horizontal
    transfer: float = 0.35            # share of the paddle's speed passed to the ball
    spin_from_paddle: float = 0.06    # spin per px/tick of paddle speed at contact
    curve: float = 0.9                # how hard spin bends the ball
    spin_decay: float = 0.985         # spin kept per tick (air drag)
    points: int = WINNING_SCORE

    @property
    def locked(self):
        return self.engine == 'original'

    def to_json(self):
        return asdict(self)

    @staticmethod
    def from_json(d):
        known = {k: v for k, v in d.items() if k in Rules.__dataclass_fields__}
        return Rules(**known)


ORIGINAL = Rules()
# Tuned with bot-vs-bot series (2026-11-16): a rally starts slow and speeds up until the
# ball can outrun a paddle, so points come from play, not from an exploit.
REALISTIC = Rules(name='Realistický', engine='realistic', ball_speed=5.0, speedup=0.45, max_ball_speed=17.0,
                  paddle_speed=4.5, paddle_accel=0.4)
ARCADE = Rules(name='Arkáda', engine='realistic', ball_speed=7.0, speedup=0.7, max_ball_speed=22.0,
               paddle_speed=6.0, paddle_accel=0.6, max_angle=60.0, transfer=0.5, spin_from_paddle=0.09,
               curve=1.3, spin_decay=0.99, points=7)
SLOWMO = Rules(name='Zpomalený', engine='realistic', ball_speed=3.0, speedup=0.3, max_ball_speed=12.0,
               paddle_speed=3.2, paddle_accel=0.3, curve=0.7)
PRESETS = [ORIGINAL, REALISTIC, ARCADE, SLOWMO]

# (field, label, min, max, step) - what the rules screen lets G change
SLIDERS = [
    ('ball_speed', 'rychlost míčku', 2.0, 12.0, 0.5),
    ('speedup', 'zrychlení za úder', 0.0, 1.5, 0.05),
    ('max_ball_speed', 'max. rychlost míčku', 4.0, 24.0, 0.5),
    ('paddle_speed', 'rychlost pálky', 2.0, 16.0, 0.5),
    ('paddle_accel', 'akcelerace pálky', 0.1, 3.0, 0.05),
    ('paddle_height', 'výška pálky', 40, 200, 10),
    ('max_angle', 'max. úhel odrazu', 20.0, 75.0, 5.0),
    ('transfer', 'přenos pohybu pálky', 0.0, 1.0, 0.05),
    ('spin_from_paddle', 'rotace z pohybu pálky', 0.0, 0.2, 0.01),
    ('curve', 'zakřivení rotací', 0.0, 3.0, 0.1),
    ('spin_decay', 'udržení rotace', 0.9, 1.0, 0.005),
    ('points', 'body do výhry', 1, 21, 1),
]

STORE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'rules.json')


def custom_from(base, **changes):
    r = replace(base, **changes)
    if r.engine == 'original':
        r = replace(r, engine='realistic')
    r.name = 'Vlastní'
    return r


def load_last():
    try:
        with open(STORE, encoding='utf-8') as fh:
            return Rules.from_json(json.load(fh))
    except (OSError, ValueError, TypeError):
        return ORIGINAL


def save_last(rules):
    try:
        with open(STORE, 'w', encoding='utf-8') as fh:
            json.dump(rules.to_json(), fh, ensure_ascii=False, indent=1)
    except OSError:
        pass
