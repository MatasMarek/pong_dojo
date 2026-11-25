"""Proof that the game physics and the player limits are unchanged.

Run from the repository root:   python -m unittest -v tests.test_physics_unchanged

1. The friend's original files are byte-identical to commit 9111df8.
2. The physics constants and player limits still have their original values.
3. Differential run: the ORIGINAL pong_dojo.py code (loaded with a stub for its missing
   paddle_logic module) and dojo/engine.py are stepped side by side on the same key
   presses for many thousand ticks; every paddle, ball and score value must match on
   every tick.
4. The bot contract gives bots read-only copies and at most one key event per tick.
"""
import os
import random
import subprocess
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_COMMIT = '9111df808b11b494699444291867dd932328ee60'
ORIGINAL_FILES = ['pong_dojo.py', 'config.py', 'bot_template.py', 'text_handling.py', 'stery.txt']

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def load_original():
    """Import the original pong_dojo.py headless. Its missing paddle_logic is stubbed and
    the 4-second taunt pause is replaced by a no-op (presentation, not physics)."""
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
    stub = types.ModuleType('paddle_logic')
    stub.RobotMovePaddle = object
    sys.modules['paddle_logic'] = stub
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        import importlib
        orig = importlib.import_module('pong_dojo')
    finally:
        os.chdir(cwd)
    orig.write_something_sassy = lambda *a, **k: None
    return orig


class OriginalFilesUntouched(unittest.TestCase):
    def test_files_identical_to_base_commit(self):
        for name in ORIGINAL_FILES:
            with self.subTest(file=name):
                self.assertEqual(git('hash-object', name), git('rev-parse', f'{BASE_COMMIT}:{name}'),
                                 f'{name} differs from the original at {BASE_COMMIT[:7]}')


class ConstantsUnchanged(unittest.TestCase):
    def test_config_values(self):
        import config
        self.assertEqual((config.WIDTH, config.HEIGHT), (700, 500))
        self.assertEqual((config.PADDLE_WIDTH, config.PADDLE_HEIGHT), (20, 100))
        self.assertEqual(config.BALL_RADIUS, 7)
        self.assertEqual(config.FPS, 60)
        self.assertEqual(config.WINNING_SCORE, 10)

    def test_engine_matches_original_classes(self):
        orig = load_original()
        from dojo import engine
        self.assertEqual(engine.Paddle.VEL, orig.Paddle.VEL)
        self.assertEqual(engine.Paddle.VEL, 2)
        self.assertEqual(engine.Ball.MAX_VEL, orig.Ball.MAX_VEL)
        self.assertEqual(engine.Ball.MAX_VEL, 5)
        self.assertEqual(engine.Ball.AIR_DRAG, orig.Ball.AIR_DRAG)
        self.assertEqual(engine.Ball.no_of_updates, orig.Ball.no_of_updates)


class DifferentialRun(unittest.TestCase):
    """Same inputs into the original code and into dojo.engine; compare every tick."""

    def run_both(self, seed, ticks):
        orig = load_original()
        import pygame
        import pygame.locals as L
        from dojo import engine

        ev = {
            'w': pygame.event.Event(L.KEYDOWN, unicode="w", key=L.K_w, mod=L.KMOD_NONE),
            's': pygame.event.Event(L.KEYDOWN, unicode="s", key=L.K_s, mod=L.KMOD_NONE),
            'up': pygame.event.Event(L.KEYDOWN, unicode="up", key=L.K_UP, mod=L.KMOD_NONE),
            'down': pygame.event.Event(L.KEYDOWN, unicode="down", key=L.K_DOWN, mod=L.KMOD_NONE),
        }
        H, PH, PW, W = orig.HEIGHT, orig.PADDLE_HEIGHT, orig.PADDLE_WIDTH, orig.WIDTH
        o_left = orig.Paddle(10, H // 2 - PH // 2, PW, PH, orig.WHITE)
        o_right = orig.Paddle(W - 10 - PW, H // 2 - PH // 2, PW, PH, orig.WHITE)
        o_ball = orig.Ball(W // 2, H // 2, orig.BALL_RADIUS)
        o_ls = o_rs = 0
        m = engine.Match()

        rng = random.Random(seed)
        hits = goals = spins = 0
        for t in range(ticks):
            # Inputs: each side half-tracks the ball with noise, so rallies, hits,
            # spin, wall bounces and goals all happen. Sometimes both keys at once.
            names = []
            for side, (up_k, dn_k), pad in (('left', ('w', 's'), o_left), ('right', ('up', 'down'), o_right)):
                r = rng.random()
                if r < 0.55:
                    names.append(up_k if o_ball.y < pad.y + PH / 2 else dn_k)
                elif r < 0.75:
                    names.append(rng.choice((up_k, dn_k)))
                elif r < 0.80:
                    names += [up_k, dn_k]
            # the original: one event per key; order = as posted
            o_events = [ev[n] for n in names]
            try:
                orig.handle_paddle_movement(o_events, o_left, o_right, ev)
                rot_before = o_ball.rotation
                o_ball.move()
                orig.handle_collision(o_ball, o_left, o_right, o_events, ev)
                o_ls, o_rs = orig.goal_check(o_ball, o_right, o_left, o_ls, o_rs)
            except ZeroDivisionError:
                return hits, goals, spins, t  # the original's own crash; engine survives it
            hit, scorer = m.step(names)
            hits += bool(hit)
            goals += bool(scorer)
            spins += (o_ball.rotation != rot_before) and hit is not None

            got = (m.left.y, m.right.y, m.ball.x, m.ball.y, m.ball.x_vel, m.ball.y_vel,
                   m.ball.rotation, m.ball.y_vel_from_rotation, m.score['left'], m.score['right'])
            want = (o_left.y, o_right.y, o_ball.x, o_ball.y, o_ball.x_vel, o_ball.y_vel,
                    o_ball.rotation, o_ball.y_vel_from_rotation, o_ls, o_rs)
            if got != want:
                self.fail(f'seed {seed} tick {t}: engine {got} != original {want}')
        return hits, goals, spins, ticks

    def test_side_by_side(self):
        total_hits = total_goals = total_spins = total_ticks = 0
        for seed in range(6):
            h, g, s, t = self.run_both(seed, 30000)
            total_hits += h
            total_goals += g
            total_spins += s
            total_ticks += t
        print(f'\n  compared {total_ticks} ticks: {total_hits} paddle hits '
              f'({total_spins} with spin), {total_goals} goals - all identical')
        self.assertGreater(total_hits, 100)
        self.assertGreater(total_goals, 20)
        self.assertGreater(total_spins, 20)


class ContractLimits(unittest.TestCase):
    def test_one_event_and_read_only(self):
        from dojo import engine, contract
        m = engine.Match()

        class Greedy:
            def robot_move_paddle(self, ball, left, right, whoami):
                with self_.assertRaises(Exception):
                    ball.x = 0  # read-only copy
                with self_.assertRaises(Exception):
                    left.y = 0
                return (5, 'yes')  # truthy junk still means exactly one move

        self_ = self
        for whoami in ('left', 'right'):
            evs = contract.ask_bot(Greedy(), m, whoami)
            self.assertEqual(len(evs), 1)
        self.assertEqual(contract.to_events(False, True, 'left'), [])
        y0 = m.left.y
        m.step(contract.to_events(True, True, 'left'))
        self.assertEqual(y0 - m.left.y, engine.Paddle.VEL)


if __name__ == '__main__':
    unittest.main(verbosity=2)
