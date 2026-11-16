"""The realistic engine (2026). Used by every preset except "Originál 2022".

What is different from the friend's physics, and why:
- Paddles have mass: a key accelerates the paddle up to a top speed, releasing
  both keys brakes it. (Original: a fixed 2 px jump per tick.)
- The return angle comes from where the ball meets the paddle, capped at max_angle,
  and the paddle's own speed is partly passed to the ball (transfer).
- Spin comes from the paddle's speed at contact. It bends the ball sideways to its
  flight (like the Magnus effect), fades every tick (spin_decay), and loses a quarter
  at each wall. (Original: +-1 per held key, never fading, unbounded.)
- Every hit adds a little speed up to a cap; a goal resets it.
- Collisions are swept: the ball moves in small sub-steps and bounces at the exact
  wall line or paddle face. (Original: the ball can overshoot a wall for a tick and
  can get stuck on the edge.)

Same field (700 x 500), same paddle columns, same 60 ticks per second, same key
events as the original, so the bot contract and the arena work unchanged.
"""
import math
import random

from config import WIDTH, HEIGHT, PADDLE_WIDTH, BALL_RADIUS
from dojo.engine import LEFT_UP, LEFT_DOWN, RIGHT_UP, RIGHT_DOWN, LEFT_X, RIGHT_X


class RPaddle:
    def __init__(self, x, height):
        self.x = x
        self.width = PADDLE_WIDTH
        self.height = height
        self.y = HEIGHT // 2 - height // 2
        self.vy = 0.0

    def drive(self, up, down, rules):
        a, vmax = rules.paddle_accel, rules.paddle_speed
        if up and not down:
            self.vy = max(-vmax, self.vy - a)
        elif down and not up:
            self.vy = min(vmax, self.vy + a)
        else:  # no key (or both): brake
            brake = 1.5 * a
            self.vy = 0.0 if abs(self.vy) <= brake else self.vy - math.copysign(brake, self.vy)
        self.y += self.vy
        if self.y < 0:
            self.y, self.vy = 0, 0.0
        elif self.y > HEIGHT - self.height:
            self.y, self.vy = HEIGHT - self.height, 0.0


class RBall:
    def __init__(self, speed):
        self.radius = BALL_RADIUS
        self.x, self.y = WIDTH / 2, HEIGHT / 2
        self.x_vel, self.y_vel = speed, 0.0
        self.rotation = 0.0             # spin; > 0 bends clockwise relative to the flight
        self.y_vel_from_rotation = 0.0  # kept for the bot view; unused here

    def copy(self):
        b = RBall(0)
        b.__dict__.update(self.__dict__)
        return b

    @property
    def speed(self):
        return math.hypot(self.x_vel, self.y_vel)


def bend(ball, rules):
    """Spin bends the flight sideways (speed unchanged), then fades."""
    s = ball.speed
    if ball.rotation and s > 0:
        a = 0.1 * rules.curve * ball.rotation
        nx, ny = -ball.y_vel / s, ball.x_vel / s
        vx, vy = ball.x_vel + a * nx, ball.y_vel + a * ny
        k = s / math.hypot(vx, vy)
        vx, vy = vx * k, vy * k
        lim = math.radians(75)  # never steeper than 75 degrees: no endless wall-to-wall bouncing
        ang = math.atan2(vy, abs(vx))
        if abs(ang) > lim:
            ang = math.copysign(lim, ang)
            vx, vy = math.copysign(s * math.cos(ang), vx), s * math.sin(ang)
        ball.x_vel, ball.y_vel = vx, vy
    ball.rotation *= rules.spin_decay


def bounce_off_paddle(ball, paddle_y, paddle_h, paddle_vy, side, rules, contact_y):
    rel = max(-1.0, min(1.0, (contact_y - (paddle_y + paddle_h / 2)) / (paddle_h / 2)))
    s = min(rules.max_ball_speed, ball.speed + rules.speedup)
    lim = math.radians(rules.max_angle)
    d = 1 if side == 'left' else -1
    vy = s * math.sin(rel * lim) + rules.transfer * paddle_vy
    vx = s * math.cos(rel * lim)
    ang = max(-lim, min(lim, math.atan2(vy, vx)))
    ball.x_vel, ball.y_vel = d * s * math.cos(ang), s * math.sin(ang)
    ball.rotation = 0.3 * ball.rotation - d * rules.spin_from_paddle * paddle_vy


def advance(ball, rules, left=None, right=None, stop_at=None):
    """Move the ball one tick in sub-steps. With paddles given, bounce off them.
    stop_at='left'/'right': stop where the ball crosses that paddle face (prediction).
    Returns ('hit', side, y) / ('cross', side, y) / ('wall', None, y) / None."""
    bend(ball, rules)
    r = ball.radius
    n = max(1, math.ceil(ball.speed / 3.0))
    result = None
    for _ in range(n):
        x0, y0 = ball.x, ball.y
        x1, y1 = x0 + ball.x_vel / n, y0 + ball.y_vel / n
        if y1 - r < 0:
            y1 = 2 * r - y1
            ball.y_vel = -ball.y_vel
            ball.rotation *= 0.75
            result = result or ('wall', None, y1)
        elif y1 + r > HEIGHT:
            y1 = 2 * (HEIGHT - r) - y1
            ball.y_vel = -ball.y_vel
            ball.rotation *= 0.75
            result = result or ('wall', None, y1)
        for side, fx, pad in (('left', LEFT_X + PADDLE_WIDTH, left), ('right', RIGHT_X, right)):
            moving_in = ball.x_vel < 0 if side == 'left' else ball.x_vel > 0
            if not moving_in:
                continue
            before = (x0 - r >= fx) if side == 'left' else (x0 + r <= fx)
            after = (x1 - r < fx) if side == 'left' else (x1 + r > fx)
            if not (before and after):
                continue
            edge0 = x0 - r if side == 'left' else x0 + r
            edge1 = x1 - r if side == 'left' else x1 + r
            t = (edge0 - fx) / (edge0 - edge1) if edge0 != edge1 else 0.0
            yc = y0 + (y1 - y0) * t
            if stop_at == side:
                ball.x, ball.y = fx + (r if side == 'left' else -r), yc
                return ('cross', side, yc)
            if pad is not None and pad.y - r * 0.6 <= yc <= pad.y + pad.height + r * 0.6:
                bounce_off_paddle(ball, pad.y, pad.height, pad.vy, side, rules, yc)
                ball.x, ball.y = fx + (r if side == 'left' else -r), yc
                return ('hit', side, yc)
        ball.x, ball.y = x1, y1
    return result


class RealMatch:
    """Same interface as engine.Match: left, right, ball, score, tick, step(), winner."""

    def __init__(self, rules, seed=None):
        self.rules = rules
        self.rng = random.Random(seed)
        self.left = RPaddle(LEFT_X, rules.paddle_height)
        self.right = RPaddle(RIGHT_X, rules.paddle_height)
        self.ball = RBall(rules.ball_speed)
        self.score = {'left': 0, 'right': 0}
        self.tick = 0
        self.serve(direction=1)

    def serve(self, direction):
        b = self.ball
        b.x, b.y = WIDTH / 2, HEIGHT / 2
        ang = math.radians(self.rng.uniform(-18, 18))
        s = self.rules.ball_speed
        b.x_vel, b.y_vel = direction * s * math.cos(ang), s * math.sin(ang)
        b.rotation = 0.0
        for p in (self.left, self.right):
            p.y, p.vy = HEIGHT // 2 - p.height // 2, 0.0

    def step(self, current_events):
        self.tick += 1
        self.left.drive(LEFT_UP in current_events, LEFT_DOWN in current_events, self.rules)
        self.right.drive(RIGHT_UP in current_events, RIGHT_DOWN in current_events, self.rules)
        ev = advance(self.ball, self.rules, self.left, self.right)
        hit = ev[1] if ev and ev[0] == 'hit' else None
        b = self.ball
        scorer = None
        if b.x - b.radius > self.right.x + self.right.width and b.x_vel > 0:
            scorer = 'left'
        elif b.x + b.radius < self.left.x and b.x_vel < 0:
            scorer = 'right'
        if scorer:
            self.score[scorer] += 1
            # as in the original, the serve goes on toward the side that just conceded
            self.serve(1 if b.x_vel > 0 else -1)
        return hit, scorer

    @property
    def winner(self):
        for side in ('left', 'right'):
            if self.score[side] >= self.rules.points:
                return side
        return None


def make_match(rules, seed=None):
    if rules.engine == 'original':
        from dojo.engine import Match
        return Match()
    return RealMatch(rules, seed)
