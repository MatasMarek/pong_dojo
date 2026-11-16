"""Headless bot-vs-bot series: no window, full speed, same engine and contract as the arena.

    python -m dojo.tournament                 # 10 matches, sides swap every match
    python -m dojo.tournament --matches 50
"""
import argparse
import time

from dojo.engine import Match
from dojo.contract import ask_bot
from dojo.bots import tygr, drak

BOTS = {'TYGR': tygr, 'DRAK': drak}
MAX_TICKS = 60 * 60 * 30  # 30 minutes of game time; a match this long is reported as unfinished


def play(left_mod, right_mod, max_ticks=MAX_TICKS, seed=None):
    m = Match()
    lb, rb = left_mod.make(seed), right_mod.make(None if seed is None else seed + 1000)
    rally = longest = hits = 0
    while m.winner is None and m.tick < max_ticks:
        events = ask_bot(lb, m, 'left') + ask_bot(rb, m, 'right')
        hit, scorer = m.step(events)
        if hit:
            rally += 1
            hits += 1
            longest = max(longest, rally)
        if scorer:
            rally = 0
    return m, longest, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--matches', type=int, default=10)
    ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()
    wins = {'TYGR': 0, 'DRAK': 0, 'unfinished': 0}
    points = {'TYGR': 0, 'DRAK': 0}
    t0 = time.time()
    for i in range(a.matches):
        ln, rn = ('TYGR', 'DRAK') if i % 2 == 0 else ('DRAK', 'TYGR')
        m, longest, hits = play(BOTS[ln], BOTS[rn], seed=a.seed + i)
        w = m.winner
        wins[{'left': ln, 'right': rn}[w] if w else 'unfinished'] += 1
        points[ln] += m.score['left']
        points[rn] += m.score['right']
        print(f'match {i + 1:2d}: {ln} (left) {m.score["left"]:2d} : {m.score["right"]:2d} {rn} (right)'
              f'  | {m.tick / 60:6.1f} s game time, {hits} hits, longest rally {longest}')
    print(f'\nseries: TYGR {wins["TYGR"]} - {wins["DRAK"]} DRAK'
          f' (unfinished {wins["unfinished"]}); points TYGR {points["TYGR"]} - {points["DRAK"]} DRAK;'
          f' {time.time() - t0:.1f} s wall time')


if __name__ == '__main__':
    main()
