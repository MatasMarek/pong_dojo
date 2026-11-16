"""DRAK - the Nemesis. Built 2026-11-16 by Claude for G, on Marek Matas's Pong Dojo.

Style: the reader. While the ball flies away, DRAK puts itself in the opponent's shoes:
it lists every shot the opponent can still make (every reachable place on the paddle,
every spin) and sees where each would land on its own side. It waits leaning 30 % from
the middle toward the middle of that landing range. (Leaning all the way lost badly in
testing: the opponent's real shot is always an extreme one.) When it hits, it winds the
spin up like TYGR, but always with the sweet spot of its paddle, never the edge.

Same contract, same information and same 2 px-per-tick limit as every other player.
"""
from dojo.bots.common import (Planner, margin, CENTER, ball_from_view, fly_to_face,
                              candidate_shots, shot_outcome, other, cover_range, clamp)
from config import PADDLE_HEIGHT

IDENTITY = {
    'name': 'DRAK',
    'title': 'the Nemesis',
    'motto': 'Vidím tvůj úder dřív, než ho zahraješ.',
    'primary': (40, 214, 160),     # jade
    'secondary': (8, 44, 40),      # deep sea
    'glow': (255, 214, 102),       # gold edge
    'paddle': 'scales',
    'taunts': 'drak.txt',
}


class Drak(Planner):
    LEAN = 0.3  # how far DRAK leans from the middle toward its read of the opponent
    SWEET_SPOT = 1.0  # how much DRAK prefers the paddle centre (8.0 cost it 17 of 20 matches)

    def score_shot(self, outcome, opp_y, p, spin, contact_ball):
        m = margin(outcome, opp_y)
        offset = abs(contact_ball.y - (p + PADDLE_HEIGHT / 2)) / (PADDLE_HEIGHT / 2)
        if m > 0:
            return 10000 + m - self.SWEET_SPOT * offset  # a winner, hit as cleanly as possible
        # No winner yet: wind the spin up, hit near the paddle centre, make the opponent run.
        return 100 * abs(outcome[2].rotation) + m - self.SWEET_SPOT * offset

    def idle_target(self, ball, me, opp, side):
        read = self.read_landing(ball, opp, side)
        return int(round(((1 - self.LEAN) * CENTER + self.LEAN * read) / 2)) * 2

    def read_landing(self, ball, opp, side):
        opp_side = other(side)
        key = (ball.rotation, round(ball.x_vel, 3), round(ball.y_vel, 3), round(ball.y_vel_from_rotation, 4))
        if self.idle_flight == key:
            return self.idle_y
        self.idle_flight = key
        b = ball_from_view(ball)
        k = fly_to_face(b, opp_side)
        if k is None:
            self.idle_y = CENTER
            return self.idle_y
        landing = []
        for p, spin in candidate_shots(b, k, opp.y, opp_side, step=6):
            out = shot_outcome(b, p, opp_side, spin)
            if out is None:
                continue
            r = cover_range(out[1])
            if r is not None:
                landing.append(sum(r) / 2)
        if landing:
            self.idle_y = clamp(int(round((min(landing) + max(landing)) / 4)) * 2)
        else:
            self.idle_y = CENTER
        return self.idle_y


def make(seed=None):
    return Drak(seed)
