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
    rotation: int
    y_vel_from_rotation: float
    radius: int


@dataclass(frozen=True)
class PaddleView:
    x: int
    y: int
    width: int
    height: int


def views(match):
    b = match.ball
    ball = BallView(b.x, b.y, b.x_vel, b.y_vel, b.rotation, b.y_vel_from_rotation, b.radius)
    left = PaddleView(match.left.x, match.left.y, match.left.width, match.left.height)
    right = PaddleView(match.right.x, match.right.y, match.right.width, match.right.height)
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
