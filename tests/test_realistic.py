"""Checks for the realistic engine and the rule presets.

    python -m unittest -v tests.test_realistic

- "Originál 2022" still runs the original engine (dojo/engine.Match), locked.
- Under every realistic preset, for many thousand ticks of bot play: no paddle ever moves
  faster than paddle_speed, the ball never exceeds max_ball_speed, the ball never leaves
  the field vertically (swept collisions), and both sides get the same limits.
- A created bot with low skill is handicapped; TYGR and DRAK are not.
- Every preset finishes a TYGR vs DRAK match.
"""
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import HEIGHT  # noqa: E402
from dojo import rules as R  # noqa: E402
from dojo.physics2 import make_match, RealMatch  # noqa: E402
from dojo.engine import Match  # noqa: E402
from dojo.contract import ask_bot, Handicap  # noqa: E402
from dojo.bots import tygr, drak  # noqa: E402


class Presets(unittest.TestCase):
    def test_original_is_the_original_engine(self):
        self.assertTrue(R.ORIGINAL.locked)
        self.assertIsInstance(make_match(R.ORIGINAL), Match)
        self.assertEqual(R.PRESETS[0], R.ORIGINAL)

    def test_slider_change_never_touches_original(self):
        r = R.custom_from(R.ORIGINAL, ball_speed=9.0)
        self.assertEqual(r.engine, 'realistic')
        self.assertEqual(r.name, 'Vlastní')
        self.assertEqual(R.ORIGINAL.ball_speed, 5.0)
        self.assertIsInstance(make_match(r), RealMatch)


class Limits(unittest.TestCase):
    def run_preset(self, rules, ticks=20000, seed=3):
        m = make_match(rules, seed)
        lb, rb = tygr.make(seed, rules), drak.make(seed + 1, rules)
        worst = {'paddle': 0.0, 'ball': 0.0, 'y_out': 0.0}
        hits = goals = 0
        for _ in range(ticks):
            hit, scorer = m.step(ask_bot(lb, m, 'left') + ask_bot(rb, m, 'right'))
            hits += bool(hit)
            goals += bool(scorer)
            worst['paddle'] = max(worst['paddle'], abs(m.left.vy), abs(m.right.vy))
            if not scorer:
                worst['ball'] = max(worst['ball'], math.hypot(m.ball.x_vel, m.ball.y_vel))
            r = m.ball.radius
            worst['y_out'] = max(worst['y_out'], r - m.ball.y, m.ball.y + r - HEIGHT)
            for p in (m.left, m.right):
                self.assertGreaterEqual(p.y, 0)
                self.assertLessEqual(p.y + p.height, HEIGHT)
        return worst, hits, goals

    def test_every_realistic_preset(self):
        for rules in R.PRESETS[1:]:
            with self.subTest(preset=rules.name):
                worst, hits, goals = self.run_preset(rules)
                self.assertLessEqual(worst['paddle'], rules.paddle_speed + 1e-9)
                self.assertLessEqual(worst['ball'], rules.max_ball_speed + 1e-6)
                self.assertLessEqual(worst['y_out'], 1e-6, 'ball left the field vertically')
                self.assertGreater(hits, 20)
                print(f'\n  {rules.name}: {hits} hits, {goals} goals; max paddle {worst["paddle"]:.2f} '
                      f'(limit {rules.paddle_speed}), max ball {worst["ball"]:.2f} (limit {rules.max_ball_speed})')


class Skill(unittest.TestCase):
    def test_handicap_only_below_ten(self):
        bot = tygr.make(1, R.REALISTIC)
        self.assertEqual(Handicap(bot, 10).delay, 0)
        self.assertGreater(Handicap(bot, 3).delay, 0)


class Finishes(unittest.TestCase):
    def test_each_preset_finishes(self):
        from dojo.tournament import play
        for rules in R.PRESETS:
            with self.subTest(preset=rules.name):
                m, _, _ = play(tygr, drak, seed=11, rules=rules, max_ticks=60 * 60 * 20)
                self.assertIsNotNone(m.winner, f'{rules.name}: no winner in 20 minutes of game time')


if __name__ == '__main__':
    unittest.main(verbosity=2)
