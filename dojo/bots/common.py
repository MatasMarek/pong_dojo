"""Shared knowledge for the dojo bots: the public rules of the game.

Any student could read pong_dojo.py, so both bots may simulate the ball with the same
rules (dojo.engine). Both get exactly this module; they differ only in what they do
with it. Nothing here touches the live match: it works on copies of the views.
"""
import random

from config import HEIGHT, PADDLE_HEIGHT
from dojo.engine import (Ball, Paddle, wall_bounce, crosses_face, apply_hit, LEFT_X, RIGHT_X,
                         LEFT_UP, LEFT_DOWN, RIGHT_UP, RIGHT_DOWN)
from config import PADDLE_WIDTH

VEL = Paddle.VEL
TOP, BOTTOM = 0, HEIGHT - PADDLE_HEIGHT
CENTER = HEIGHT // 2 - PADDLE_HEIGHT // 2
FACE_X = {'left': LEFT_X, 'right': RIGHT_X}
SPINS = ('up', 'none', 'down')


def other(side):
    return 'right' if side == 'left' else 'left'


def ball_from_view(v):
    b = Ball(v.x, v.y, v.radius)
    b.x_vel, b.y_vel = v.x_vel, v.y_vel
    b.rotation, b.y_vel_from_rotation = v.rotation, v.y_vel_from_rotation
    return b


def heading_to(ball, side):
    return ball.x_vel < 0 if side == 'left' else ball.x_vel > 0


def fly_to_face(ball, side, max_ticks=1500):
    """Advance `ball` (a copy, mutated) tick by tick until the tick on which the original
    code tests it against `side`'s paddle. Returns the tick count, or None if the ball
    already passed that face."""
    if not heading_to(ball, side):
        return None
    for t in range(1, max_ticks):
        ball.move()
        wall_bounce(ball)
        if crosses_face(ball, FACE_X[side], PADDLE_WIDTH, side):
            return t
        if (side == 'left' and ball.x < FACE_X['left']) or (side == 'right' and ball.x > FACE_X['right'] + PADDLE_WIDTH):
            return None
    return None


def spin_event(side, spin):
    if spin == 'none':
        return []
    if side == 'left':
        return [LEFT_UP if spin == 'up' else LEFT_DOWN]
    return [RIGHT_UP if spin == 'up' else RIGHT_DOWN]


def last_move(spin):
    return -VEL if spin == 'up' else VEL if spin == 'down' else 0


def clamp(y):
    return max(TOP, min(BOTTOM, y))


def cover_range(ball_y):
    """Paddle y values that keep `ball_y` on the paddle (inclusive), clipped to the field."""
    lo, hi = max(TOP, ball_y - PADDLE_HEIGHT), min(BOTTOM, ball_y)
    return (lo, hi) if lo <= hi else None


def travel_needed(paddle_y, ball_y):
    """Pixels the paddle must travel to cover ball_y; None if no paddle position can."""
    r = cover_range(ball_y)
    if r is None:
        return None
    lo, hi = r
    if paddle_y < lo:
        return lo - paddle_y
    if paddle_y > hi:
        return paddle_y - hi
    return 0


def shot_outcome(contact_ball, paddle_y, side, spin):
    """Ball state after our hit at paddle_y with `spin`, flown to the other face.
    Returns (ticks_to_their_face, ball_y_there, ball_at_their_face) or None."""
    b = contact_ball.copy()
    apply_hit(b, paddle_y, PADDLE_HEIGHT, side, spin_event(side, spin))
    t = fly_to_face(b, other(side))
    if t is None:
        return None
    return t, b.y, b


def candidate_shots(contact_ball, k, my_y, side, step=2):
    """Every (paddle_y, spin) we can reach for a contact k ticks from now.
    The paddle gets k moves; the k-th one (on the contact tick) is the spin move."""
    r = cover_range(contact_ball.y)
    if r is None:
        return
    lo, hi = r
    for spin in SPINS:
        lm = last_move(spin)
        reach = VEL * (k - 1)
        for p in range(int(lo) + (int(lo) % 2), int(hi) + 1, step):
            if p < lo or p > hi:
                continue
            before = p - lm
            if before < TOP or before > BOTTOM:
                continue
            if abs(before - my_y) > reach:
                continue
            yield p, spin


def step_toward(my_y, target):
    """(move, up) that brings the paddle 2 px closer to `target` y, or stays."""
    if target < my_y - 1:
        return True, True
    if target > my_y + 1:
        return True, False
    return False, False


class Planner:
    """Plans one hit per incoming ball, executes it tick by tick.
    Subclasses choose the shot (score_shot) and where to wait (idle_target)."""

    REFINE_AT = 24  # re-plan this many ticks before contact, with fresh opponent position
    TOLERANCE = 6.0  # shots scoring within this of the best are equally good: pick one at random

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.plan = None  # (paddle_y, spin, contact_ball_y, k_at_plan)
        self.flight = None
        self.refined = False
        self.idle_y = CENTER
        self.idle_flight = None
        self.stats = {'plans': 0, 'winners_seen': 0}

    # --- to override -------------------------------------------------------
    def score_shot(self, outcome, opp_y, p, spin, contact_ball):
        raise NotImplementedError

    def idle_target(self, ball, me, opp, side):
        return CENTER

    # --- contract ----------------------------------------------------------
    def robot_move_paddle(self, ball, left_paddle, right_paddle, whoami):
        me, opp = (left_paddle, right_paddle) if whoami == 'left' else (right_paddle, left_paddle)
        b = ball_from_view(ball)
        if not heading_to(b, whoami):
            self.plan, self.flight, self.refined = None, None, False
            return step_toward(me.y, self.idle_target(ball, me, opp, whoami))

        contact = b.copy()
        k = fly_to_face(contact, whoami)
        if k is None:  # already past us: chase anyway
            return step_toward(me.y, clamp(int(b.y) - PADDLE_HEIGHT // 2))

        flight_id = (ball.rotation, round(contact.y, 6))
        if self.plan is None or self.flight != flight_id or (k <= self.REFINE_AT and not self.refined):
            if self.plan is not None and k <= self.REFINE_AT:
                self.refined = True
            self.flight = flight_id
            self.plan = self.choose(contact, k, me.y, opp.y, whoami)

        if self.plan is None:  # nothing reachable: get as close as possible
            return step_toward(me.y, clamp(int(contact.y) - PADDLE_HEIGHT // 2))

        p, spin = self.plan
        if k == 1:  # the contact tick: the spin move
            if spin == 'none':
                return False, False
            return True, spin == 'up'
        return step_toward(me.y, p - last_move(spin))

    def choose(self, contact, k, my_y, opp_y, side):
        scored = []
        step = 2 if k <= self.REFINE_AT else 4
        for p, spin in candidate_shots(contact, k, my_y, side, step):
            out = shot_outcome(contact, p, side, spin)
            if out is None:
                continue
            scored.append((self.score_shot(out, opp_y, p, spin, contact), p, spin))
        self.stats['plans'] += 1
        if not scored:
            return None
        top = max(s for s, _, _ in scored)
        pool = [(p, spin) for s, p, spin in scored if s >= top - self.TOLERANCE]
        if top >= 10000:
            self.stats['winners_seen'] += 1
        return self.rng.choice(pool)


def margin(outcome, opp_y):
    """How far out of the opponent's reach the shot lands: needed travel minus what the
    opponent can travel in time. > 0 means a perfect opponent cannot get there.
    Landing outside every paddle position (ball beyond the edge) counts as 1000."""
    t, y, _ = outcome
    need = travel_needed(opp_y, y)
    if need is None:
        return 1000.0
    return need - VEL * t
