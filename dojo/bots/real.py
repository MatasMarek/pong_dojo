"""Bot brain for the realistic engine (dojo/physics2.py), shared by TYGR and DRAK.

Same idea as the original-rules planner: simulate the incoming ball with the public
rules, try every place on the paddle it can meet the ball with, fly each return to
the far side, and pick by the bot's style. Paddles now have mass, so the bot steers
with a brake-in-time controller instead of 2 px steps.
"""
import math
import random

from config import HEIGHT
from dojo.physics2 import RBall, advance, bounce_off_paddle

OFFSETS = [i / 10 for i in range(-9, 10, 2)]  # -0.9 ... 0.9


def ball_from_view(v):
    b = RBall(0)
    b.x, b.y, b.x_vel, b.y_vel, b.rotation = v.x, v.y, v.x_vel, v.y_vel, v.rotation
    return b


def heading_to(ball, side):
    return ball.x_vel < 0 if side == 'left' else ball.x_vel > 0


def fly_to(ball, side, rules, max_ticks=900):
    """Advance `ball` (a copy, mutated) until it crosses `side`'s paddle face.
    Returns (ticks, y); the ball is left in its state at the face. None if it never gets there."""
    if not heading_to(ball, side):
        return None
    for t in range(1, max_ticks):
        ev = advance(ball, rules, stop_at=side)
        if ev and ev[0] == 'cross':
            return t, ev[2]
    return None


def reach_ticks(distance, rules):
    """Ticks a resting paddle needs to travel `distance` px (accelerating, no braking)."""
    a, v = rules.paddle_accel, rules.paddle_speed
    if distance <= 0:
        return 0.0
    d_acc = v * v / (2 * a)
    if distance <= d_acc:
        return math.sqrt(2 * distance / a)
    return v / a + (distance - d_acc) / v


def need_travel(paddle_y, h, y, r):
    """Pixels the paddle must move so the ball at y meets it."""
    lo, hi = y - h - r * 0.6, y + r * 0.6  # paddle y range that covers y
    lo, hi = max(0, lo), min(HEIGHT - h, hi)
    if lo > hi:
        return None
    if paddle_y < lo:
        return lo - paddle_y
    if paddle_y > hi:
        return paddle_y - hi
    return 0.0


def steer(y, vy, target, rules):
    """(move, up): accelerate toward target, release (= brake) in time to stop on it."""
    d = target - y
    brake = 1.5 * rules.paddle_accel
    stop = vy * vy / (2 * brake) if brake > 0 else 0
    if abs(d) <= 1.5 and abs(vy) <= brake:
        return False, False
    if d > 0:
        if vy > 0 and stop >= d:
            return False, False
        return True, False
    if vy < 0 and stop >= -d:
        return False, False
    return True, True


class RealPlanner:
    def __init__(self, rules, style, seed=None):
        self.rules = rules
        self.style = style  # 'attack' (TYGR) or 'read' (DRAK)
        self.rng = random.Random(seed)
        self.plan_key = None
        self.target = None
        self.idle_key = None
        self.idle_y = None
        self.last_dist = None

    def robot_move_paddle(self, ball, left_paddle, right_paddle, whoami):
        me, opp = (left_paddle, right_paddle) if whoami == 'left' else (right_paddle, left_paddle)
        h = me.height
        center = HEIGHT / 2 - h / 2
        b = ball_from_view(ball)
        dist = abs(b.x - me.x)
        if self.last_dist is not None and dist > self.last_dist + 20:  # ball jumped back: a new serve
            self.plan_key, self.target, self.idle_key = None, None, None
        self.last_dist = dist
        if heading_to(b, whoami):
            late = dist < 120
            if self.plan_key is None or (late and self.plan_key != 'late'):
                self.plan_key = 'late' if late else 'early'  # plan once per flight, refine once near
                self.target = self.choose(b, me, opp, whoami)
            target = self.target if self.target is not None else center
        else:
            self.plan_key, self.target = None, None
            target = self.idle(b, me, opp, whoami, center)
        return steer(me.y, me.vy, target, self.rules)

    def choose(self, b, me, opp, side):
        rules = self.rules
        at_face = b.copy()
        hit = fly_to(at_face, side, rules)
        if hit is None:
            return None
        k, yc = hit
        h = me.height
        other = 'right' if side == 'left' else 'left'
        scored = []
        for rel in OFFSETS:
            py = yc - h / 2 - rel * h / 2          # paddle y that meets the ball at offset rel
            py = max(0, min(HEIGHT - h, py))
            if reach_ticks(abs(py - me.y), rules) > k + 2:
                continue
            out = at_face.copy()
            bounce_off_paddle(out, py, h, 0.0, side, rules, yc)
            land = fly_to(out, other, rules)
            if land is None:
                continue
            k2, y2 = land
            need = need_travel(opp.y, opp.height, y2, b.radius)
            margin = 999.0 if need is None else reach_ticks(need, rules) - k2
            if self.style == 'attack':
                score = margin
            else:
                score = margin - 6.0 * abs(rel)
            scored.append((score, py))
        if not scored:
            return max(0, min(HEIGHT - h, yc - h / 2))
        top = max(s for s, _ in scored)
        pool = [py for s, py in scored if s >= top - 2.0]
        return self.rng.choice(pool)

    def idle(self, b, me, opp, side, center):
        if self.style == 'attack':
            return center
        # DRAK: lean toward where the opponent's return is likely to land
        key = (round(b.x_vel, 3), round(b.y_vel, 2))
        if self.idle_key == key and self.idle_y is not None:
            return self.idle_y
        self.idle_key = key
        other = 'right' if side == 'left' else 'left'
        at_face = b.copy()
        hit = fly_to(at_face, other, self.rules)
        if hit is None:
            self.idle_y = center
            return center
        _, yc = hit
        lands = []
        for rel in (-0.9, -0.45, 0, 0.45, 0.9):
            out = at_face.copy()
            py = max(0, min(HEIGHT - opp.height, yc - opp.height / 2 - rel * opp.height / 2))
            bounce_off_paddle(out, py, opp.height, 0.0, other, self.rules, yc)
            land = fly_to(out, side, self.rules)
            if land:
                lands.append(land[1] - me.height / 2)
        if lands:
            read = (min(lands) + max(lands)) / 2
            self.idle_y = max(0, min(HEIGHT - me.height, 0.65 * center + 0.35 * read))
        else:
            self.idle_y = center
        return self.idle_y
