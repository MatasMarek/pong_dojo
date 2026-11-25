"""The bot contract, from the last lines of the original pong_dojo.py:

    def robot_move_paddle(ball, left_paddle, right_paddle, whoami):
        whoami: "left" or "right"
        returns (move, up)   # move: does the paddle move at all; up: in which direction

Limits enforced here, the same for every bot and every human:
- A bot sees only read-only copies of the ball and the two paddles (frozen dataclasses),
  plus the public rules in config.py. It cannot touch the real match.
- The answer becomes at most ONE key event per tick, the same event a human key press
  makes ('w'/'s' for left, 'up'/'down' for right). So a bot moves 2 px per tick at most,
  and it adds spin exactly like a human holding a key at the moment of the hit.
"""
from dataclasses import dataclass

from dojo.engine import LEFT_UP, LEFT_DOWN, RIGHT_UP, RIGHT_DOWN


@dataclass(frozen=True)
class BallView:
    x: float
    y: float
    x_vel: float
    y_vel: float
    rotation: float
    y_vel_from_rotation: float
    radius: int


@dataclass(frozen=True)
class PaddleView:
    x: int
    y: int
    width: int
    height: int
    vy: float = 0.0  # paddle speed; always 0 under the original rules (no paddle mass there)


def views(match):
    b = match.ball
    ball = BallView(b.x, b.y, b.x_vel, b.y_vel, b.rotation, b.y_vel_from_rotation, b.radius)
    left = PaddleView(match.left.x, match.left.y, match.left.width, match.left.height, getattr(match.left, 'vy', 0.0))
    right = PaddleView(match.right.x, match.right.y, match.right.width, match.right.height, getattr(match.right, 'vy', 0.0))
    return ball, left, right


def to_events(move, up, whoami):
    """(move, up) -> list with at most one key event."""
    if not bool(move):
        return []
    if whoami == 'left':
        return [LEFT_UP if bool(up) else LEFT_DOWN]
    return [RIGHT_UP if bool(up) else RIGHT_DOWN]


def ask_bot(bot, match, whoami):
    ball, left, right = views(match)
    answer = bot.robot_move_paddle(ball, left, right, whoami)
    move, up = answer
    return to_events(move, up, whoami)


class Handicap:
    """Skill 1-10 for a created bot. Skill 10 = no handicap (TYGR and DRAK always play at 10).
    Lower skill = it sees the game a few ticks late and sometimes hesitates. Applied
    outside the bot, so every brain gets the same treatment."""

    def __init__(self, bot, skill, seed=None):
        import random
        self.bot = bot
        self.skill = max(1, min(10, int(skill)))
        self.delay = (10 - self.skill) * 2
        self.freeze = (10 - self.skill) * 0.03
        self.rng = random.Random(seed)
        self.history = []
        self.last = (False, False)

    def robot_move_paddle(self, ball, left, right, whoami):
        self.history.append((ball, left, right))
        if len(self.history) > self.delay + 1:
            self.history.pop(0)
        if self.rng.random() < self.freeze:
            return self.last
        b, l, r = self.history[0]
        self.last = self.bot.robot_move_paddle(b, l, r, whoami)
        return self.last
