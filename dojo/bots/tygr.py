"""TYGR - the Ultimate. Built 2026-11-16 by Claude for G, on Marek Matas's Pong Dojo.

Style: the attacker. On every incoming ball TYGR simulates each place on its paddle it
can still reach and each spin it can give (hold up / nothing / hold down on the hit
tick), flies each resulting ball to the far side, and picks the shot that lands
furthest outside the opponent's reach. Between shots it waits in the middle.

Same contract, same information and same 2 px-per-tick limit as every other player.
"""
from dojo.bots.common import Planner, margin, CENTER

IDENTITY = {
    'name': 'TYGR',
    'title': 'the Ultimate',
    'motto': 'Útok je nejlepší obrana.',
    'primary': (255, 140, 26),     # tiger orange
    'secondary': (24, 18, 14),     # stripe black
    'glow': (255, 196, 92),
    'paddle': 'stripes',
    'taunts': 'tygr.txt',
}


class Tygr(Planner):
    def score_shot(self, outcome, opp_y, p, spin, contact_ball):
        m = margin(outcome, opp_y)
        if m > 0:
            return 10000 + m  # a winner: take it
        # No winner yet: wind the spin up (the friend's rules never reset spin before a goal),
        # and among equal spin keep the opponent running as far as possible.
        return 100 * abs(outcome[2].rotation) + m

    def idle_target(self, ball, me, opp, side):
        return CENTER


def make(seed=None, rules=None):
    """Original rules: the 2022 planner. Any other preset: the realistic-engine brain."""
    if rules is not None and rules.engine != 'original':
        from dojo.bots.real import RealPlanner
        return RealPlanner(rules, 'attack', seed)
    return Tygr(seed)
