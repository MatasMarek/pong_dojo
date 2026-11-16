"""Headless copy of the original game physics.

Source of every rule: pong_dojo.py and config.py by Marek Matas and ultra_kevyk
(github.com/MatasMarek/pong_dojo, commit 9111df8, 22 Nov 2022). Their files stay
untouched in this folder. This module repeats the same rules without pygame, so
bots can be run headless and the arena can draw the match however it likes.

tests/test_physics_unchanged.py runs this engine and the original code side by side,
tick by tick, and fails on the first difference.

One deliberate difference: the original Ball.move divides by abs(y_vel_from_rotation)
and crashes with ZeroDivisionError if that value is ever exactly 0.0. Here that case
counts as "no sign" and the tick goes on. Every state the original can reach without
crashing is reproduced exactly.
"""
from config import (WIDTH, HEIGHT, PADDLE_WIDTH, PADDLE_HEIGHT, BALL_RADIUS,
                    FPS, WINNING_SCORE)

# Key names the original uses for its four events.
LEFT_UP, LEFT_DOWN, RIGHT_UP, RIGHT_DOWN = 'w', 's', 'up', 'down'

LEFT_X = 10
RIGHT_X = WIDTH - 10 - PADDLE_WIDTH
START_Y = HEIGHT // 2 - PADDLE_HEIGHT // 2


class Paddle:
    VEL = 2

    def __init__(self, x, y, width=PADDLE_WIDTH, height=PADDLE_HEIGHT):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def move(self, up=True):
        if up:
            if self.y - self.VEL > 0:
                self.y -= self.VEL
            else:
                self.y = 0
        else:
            if self.y + PADDLE_HEIGHT + self.VEL < HEIGHT:
                self.y += self.VEL
            else:
                self.y = HEIGHT - PADDLE_HEIGHT


class Ball:
    MAX_VEL = 5
    AIR_DRAG = 2
    no_of_updates = WIDTH // MAX_VEL

    def __init__(self, x, y, radius=BALL_RADIUS):
        self.x = x
        self.y = y
        self.radius = radius
        self.x_vel = self.MAX_VEL
        self.y_vel = 0
        self.y_vel_from_rotation = 0.
        self.rotation = 0  # Every hit can increase by one

    def move(self):
        self.x += self.x_vel
        self.y += self.y_vel
        if self.rotation != 0:
            self.y_vel_from_rotation += float(self.AIR_DRAG * self.rotation) / self.no_of_updates * self.x_vel / abs(self.x_vel)
            acc = self.y_vel_from_rotation
            sign_of_y_vel_from_rotation = acc / abs(acc) if acc != 0 else 0.0  # original: ZeroDivisionError at 0.0
            if abs(self.y_vel_from_rotation) > 1.:
                self.y_vel += 1 * int(sign_of_y_vel_from_rotation)
                self.y_vel_from_rotation += -sign_of_y_vel_from_rotation

    def copy(self):
        b = Ball(self.x, self.y, self.radius)
        b.x_vel, b.y_vel = self.x_vel, self.y_vel
        b.y_vel_from_rotation, b.rotation = self.y_vel_from_rotation, self.rotation
        return b


def handle_paddle_movement(current_events, left_paddle, right_paddle):
    for event in current_events:
        if event == LEFT_UP:
            left_paddle.move(up=True)
        if event == LEFT_DOWN:
            left_paddle.move(up=False)
        if event == RIGHT_UP:
            right_paddle.move(up=True)
        if event == RIGHT_DOWN:
            right_paddle.move(up=False)


def wall_bounce(ball):
    """The top/bottom part of the original handle_collision (stuck-ball bug kept)."""
    if ball.y - ball.radius <= 0:
        ball.y_vel *= -1
    elif ball.y + ball.radius >= HEIGHT:
        ball.y_vel *= -1


def crosses_face(ball, paddle_x, paddle_width, side):
    """True on the tick the original would test the ball against `side`'s paddle face."""
    if side == 'left':
        return ball.x_vel < 0 and ball.x - ball.radius + ball.x_vel <= paddle_x + paddle_width <= ball.x - ball.radius
    return ball.x_vel > 0 and ball.x + ball.radius + ball.x_vel >= paddle_x >= ball.x + ball.radius


def apply_hit(ball, paddle_y, paddle_height, side, current_events):
    """ball_has_collided_with_paddle plus the y_vel rule, as in the original."""
    for event in current_events:
        if ball.x_vel < 0:
            if event == LEFT_UP:
                ball.rotation += 1
            if event == LEFT_DOWN:
                ball.rotation -= 1
        else:
            if event == RIGHT_UP:
                ball.rotation -= 1
            if event == RIGHT_DOWN:
                ball.rotation += 1
    ball.x_vel *= -1
    middle_y = paddle_y + paddle_height / 2
    difference_in_y = ball.y - middle_y
    relative_distance = difference_in_y / (paddle_height / 2)
    ball.y_vel = relative_distance * ball.MAX_VEL


def handle_collision(ball, left_paddle, right_paddle, current_events):
    """Returns 'left' or 'right' when that paddle hit the ball this tick, else None."""
    wall_bounce(ball)
    if ball.x_vel < 0:
        p = left_paddle
        if p.y <= ball.y <= p.y + p.height and crosses_face(ball, p.x, p.width, 'left'):
            apply_hit(ball, p.y, p.height, 'left', current_events)
            return 'left'
    else:
        p = right_paddle
        if p.y <= ball.y <= p.y + p.height and crosses_face(ball, p.x, p.width, 'right'):
            apply_hit(ball, p.y, p.height, 'right', current_events)
            return 'right'
    return None


def reset_after_goal(ball, left_paddle, right_paddle):
    right_paddle.x = WIDTH - 10 - PADDLE_WIDTH
    right_paddle.y = HEIGHT // 2 - PADDLE_HEIGHT // 2
    left_paddle.x = 10
    left_paddle.y = HEIGHT // 2 - PADDLE_HEIGHT // 2
    ball.x = WIDTH // 2
    ball.y = HEIGHT // 2
    ball.y_vel = 0
    ball.rotation = 0
    # As in the original: x_vel and y_vel_from_rotation are NOT reset.


def goal_check(ball, left_paddle, right_paddle):
    """Returns 'left' or 'right' for the side that scored this tick, else None."""
    if ball.x - ball.radius > right_paddle.x + right_paddle.width and ball.x_vel > 0:
        reset_after_goal(ball, left_paddle, right_paddle)
        return 'left'
    elif ball.x + ball.radius < left_paddle.x and ball.x_vel < 0:
        reset_after_goal(ball, left_paddle, right_paddle)
        return 'right'
    return None


class Match:
    """One game, stepped one tick at a time in the original order:
    paddle movement -> ball move -> collisions -> goal check."""

    def __init__(self):
        self.left = Paddle(LEFT_X, START_Y)
        self.right = Paddle(RIGHT_X, START_Y)
        self.ball = Ball(WIDTH // 2, HEIGHT // 2)
        self.score = {'left': 0, 'right': 0}
        self.tick = 0

    def step(self, current_events):
        """current_events: list of key names ('w','s','up','down') pressed this tick.
        Returns (hit_side or None, scorer or None)."""
        self.tick += 1
        handle_paddle_movement(current_events, self.left, self.right)
        self.ball.move()
        hit = handle_collision(self.ball, self.left, self.right, current_events)
        scorer = goal_check(self.ball, self.left, self.right)
        if scorer:
            self.score[scorer] += 1
        return hit, scorer

    @property
    def winner(self):
        for side in ('left', 'right'):
            if self.score[side] >= WINNING_SCORE:
                return side
        return None
