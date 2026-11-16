"""PONG DOJO - the new arena (2026), on the original game by Marek Matas & co. (2022).

    python -m dojo.arena                    # menu
    python -m dojo.arena --mode bots        # TYGR vs DRAK straight away

The field (700 x 500), the paddles, the ball, the tick (60/s) and every rule are the
original ones, run by dojo/engine.py; only the look around them is new.

Keys: 1-4 / arrows + Enter in the menu - P or Space pause - +/- speed (bot match) -
M sound - F12 screenshot - Esc back to the menu.
"""
import argparse
import array
import math
import os
import random
import sys
import time
from collections import deque

import pygame

from config import WIDTH as FW, HEIGHT as FH, PADDLE_WIDTH, PADDLE_HEIGHT, BALL_RADIUS, FPS, WINNING_SCORE
from dojo.engine import Match, Paddle, Ball, LEFT_UP, LEFT_DOWN, RIGHT_UP, RIGHT_DOWN
from dojo.contract import ask_bot
from dojo.bots import tygr, drak

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS_DIR = os.path.join(os.path.dirname(REPO), 'shots')  # outside the friend's repo

SW, SH = 980, 730
FX, FY = (SW - FW) // 2, 150

BG_TOP, BG_BOT = (16, 14, 34), (4, 4, 10)
FIELD = (12, 14, 26)
INK = (226, 230, 245)
DIM = (120, 126, 150)

HUMAN = {'name': 'HRÁČ', 'title': 'člověk', 'motto': 'Klávesy W/S nebo šipky.',
         'primary': (214, 224, 255), 'secondary': (54, 64, 96), 'glow': (150, 180, 255),
         'paddle': 'plain', 'taunts': None}
HUMAN2 = {'name': 'HRÁČ 2', 'title': 'člověk', 'motto': 'Šipky nahoru a dolů.',
          'primary': (255, 128, 170), 'secondary': (80, 30, 56), 'glow': (255, 160, 200),
          'paddle': 'plain', 'taunts': None}
HUMAN1 = dict(HUMAN, motto='Klávesy W a S.')

MODES = [
    ('bots', 'TYGR  vs  DRAK', 'zápas robotů'),
    ('tygr', 'TY  vs  TYGR', 'hraješ vlevo: W/S nebo šipky'),
    ('drak', 'TY  vs  DRAK', 'hraješ vlevo: W/S nebo šipky'),
    ('duel', 'TY  vs  KAMARÁD', 'W/S proti šipkám, jako v originále'),
]


# ----------------------------------------------------------------------------- helpers
def font(size, bold=False):
    for name in ('bahnschrift', 'segoeui', 'arial'):
        f = pygame.font.SysFont(name, size, bold=bold)
        if f:
            return f
    return pygame.font.Font(None, size)


def load_lines(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return [ln.strip() for ln in fh if ln.strip()]
    except OSError:
        return []


def wrap(text, fnt, width):
    lines, cur = [], ''
    for word in text.split(' '):
        trial = (cur + ' ' + word).strip()
        if fnt.size(trial)[0] <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def glow_sprite(radius, color, strength=1.0):
    """Radial glow on black, for additive blending."""
    s = pygame.Surface((radius * 2, radius * 2))
    s.fill((0, 0, 0))
    for r in range(radius, 0, -1):
        t = (1 - r / radius) ** 2 * strength
        pygame.draw.circle(s, tuple(min(255, int(c * t)) for c in color), (radius, radius), r)
    return s


def paddle_skin(identity):
    w, h = PADDLE_WIDTH, PADDLE_HEIGHT
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    p, q = identity['primary'], identity['secondary']
    kind = identity['paddle']
    if kind == 'stripes':
        s.fill(p)
        rng = random.Random(7)
        y = -8
        while y < h + 8:
            th = rng.randint(4, 7)
            slant = rng.randint(5, 9)
            pygame.draw.polygon(s, q, [(0, y), (w, y - slant), (w, y - slant + th), (0, y + th)])
            y += rng.randint(13, 18)
        pygame.draw.rect(s, mix(p, (255, 255, 255), 0.35), (0, 0, 3, h))
    elif kind == 'scales':
        s.fill(q)
        for row, y in enumerate(range(-4, h + 6, 7)):
            off = 5 if row % 2 else 0
            for x in range(-off, w + 10, 10):
                pygame.draw.circle(s, p, (x + 5, y), 6)
                pygame.draw.circle(s, mix(p, q, 0.55), (x + 5, y), 6, 1)
        pygame.draw.rect(s, identity['glow'], (0, 0, w, h), 2)
    else:
        for y in range(h):
            t = abs(y - h / 2) / (h / 2)
            pygame.draw.line(s, mix(p, q, 0.15 + 0.5 * t), (0, y), (w, y))
        pygame.draw.rect(s, (255, 255, 255), (2, 0, 2, h))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=6)
    s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return s


class Sound:
    """Tiny synth: no sound files, no extra packages."""

    def __init__(self):
        self.on = True
        self.ok = False
        try:
            pygame.mixer.init(22050, -16, 1, 512)
            self.hit_l = self.tone(660, 0.05)
            self.hit_r = self.tone(520, 0.05)
            self.wall = self.tone(260, 0.03, vol=0.25)
            self.goal = self.tone(196, 0.35, vol=0.5, slide=0.5)
            self.go = self.tone(880, 0.18, vol=0.4)
            self.ok = True
        except pygame.error:
            pass

    @staticmethod
    def tone(freq, dur, vol=0.35, slide=1.0):
        rate = 22050
        n = int(rate * dur)
        buf = array.array('h')
        phase = 0.0
        for i in range(n):
            t = i / n
            f = freq * (1 + (slide - 1) * t)
            phase += 2 * math.pi * f / rate
            env = min(1.0, i / 200) * (1 - t) ** 1.5
            buf.append(int(32767 * vol * env * (1 if math.sin(phase) > 0 else -1) * 0.6))
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, name):
        if self.ok and self.on:
            getattr(self, name).play()


# ----------------------------------------------------------------------------- arena
class Arena:
    def __init__(self, args):
        self.args = args
        if args.headless:
            os.environ['SDL_VIDEODRIVER'] = 'dummy'
            os.environ['SDL_AUDIODRIVER'] = 'dummy'
        pygame.init()
        pygame.display.set_caption('PONG DOJO - arena 2026')
        self.screen = pygame.display.set_mode((SW, SH))
        self.clock = pygame.time.Clock()
        self.f_huge = font(84, True)
        self.f_big = font(46, True)
        self.f_mid = font(26, True)
        self.f_txt = font(19)
        self.f_small = font(15)
        self.sound = Sound()
        self.rng = random.Random(args.seed)
        self.stery = load_lines(os.path.join(REPO, 'stery.txt'))
        self.bg = self.make_background()
        self.field_bg = self.make_field()
        self.ball_glow = glow_sprite(26, (255, 255, 255), 0.55)
        self.speed = max(1, args.speed)
        self.state = 'menu'
        self.menu_i = 0
        self.frame = 0
        self.shot_n = 0
        self.last_shot_t = 0
        self.record_n = 0
        self.mode = None
        self.particles = []  # effects run on the menu too, before any match exists
        self.shake = 0.0
        if args.mode:
            self.start(args.mode)

    # --- static art --------------------------------------------------------------
    def make_background(self):
        s = pygame.Surface((SW, SH))
        for y in range(SH):
            pygame.draw.line(s, mix(BG_TOP, BG_BOT, y / SH), (0, y), (SW, y))
        rng = random.Random(3)
        for _ in range(90):  # faint dust
            x, y = rng.randrange(SW), rng.randrange(SH)
            c = rng.randint(30, 60)
            s.set_at((x, y), (c, c, c + 20))
        return s

    def make_field(self):
        s = pygame.Surface((FW, FH))
        s.fill(FIELD)
        for x in range(0, FW, 50):  # tatami grid
            pygame.draw.line(s, (18, 21, 38), (x, 0), (x, FH))
        for y in range(0, FH, 50):
            pygame.draw.line(s, (18, 21, 38), (0, y), (FW, y))
        cx, cy = FW // 2, FH // 2
        for i in range(14):  # enso: a brush circle with a gap
            r = 92 - i * 0.6
            a0 = math.radians(-60 + i * 2)
            a1 = math.radians(250 - i * 3)
            rect = pygame.Rect(0, 0, int(2 * r), int(2 * r))
            rect.center = (cx + i % 3 - 1, cy + i % 2)
            pygame.draw.arc(s, (34 + i, 32 + i, 58 + i), rect, a0, a1, 2)
        for y in range(10, FH, FH // 20):  # the original centre line, as dashes
            if y % 2 == 1:
                continue
            pygame.draw.rect(s, (44, 48, 78), (FW // 2 - 3, y, 6, FH // 20))
        return s

    # --- match lifecycle ---------------------------------------------------------
    def start(self, mode):
        self.mode = mode
        seed = self.rng.randrange(1 << 30)
        if mode == 'bots':
            self.players = [self.bot_player(tygr, seed), self.bot_player(drak, seed + 1)]
        elif mode in ('tygr', 'drak'):
            mod = tygr if mode == 'tygr' else drak
            self.players = [self.human_player(HUMAN, 'any'), self.bot_player(mod, seed)]
        else:
            self.players = [self.human_player(HUMAN1, 'ws'), self.human_player(HUMAN2, 'arrows')]
        for p in self.players:
            p['skin'] = paddle_skin(p['id'])
            p['glow'] = glow_sprite(40, p['id']['glow'], 0.35)
        self.match = Match()
        self.trail = deque(maxlen=22)
        self.particles = []
        self.shake = 0.0
        self.flash = None
        self.spin_angle = 0.0
        self.rally = 0
        self.last_hitter = None
        self.stats = {'hits': [0, 0], 'longest': 0, 'max_spin': 0}
        self.taunt = None
        self.state = 'intro'
        self.state_t = time.time()
        if not self.args.uncapped or self.speed == 1:
            pass

    def bot_player(self, mod, seed):
        ident = mod.IDENTITY
        lines = load_lines(os.path.join(REPO, 'dojo', 'taunts', ident['taunts']))
        return {'id': ident, 'bot': mod.make(seed), 'keys': None, 'taunts': lines}

    def human_player(self, ident, keys):
        return {'id': ident, 'bot': None, 'keys': keys, 'taunts': []}

    def human_events(self, side, keys_kind):
        k = pygame.key.get_pressed()
        if keys_kind == 'ws':
            up, dn = k[pygame.K_w], k[pygame.K_s]
        elif keys_kind == 'arrows':
            up, dn = k[pygame.K_UP], k[pygame.K_DOWN]
        else:  # either set, still one key per direction, like the original
            up = k[pygame.K_w] or k[pygame.K_UP]
            dn = k[pygame.K_s] or k[pygame.K_DOWN]
        u, d = (LEFT_UP, LEFT_DOWN) if side == 'left' else (RIGHT_UP, RIGHT_DOWN)
        return ([u] if up else []) + ([d] if dn else [])

    def tick(self):
        m = self.match
        events = []
        for side, p in zip(('left', 'right'), self.players):
            if p['bot'] is not None:
                events += ask_bot(p['bot'], m, side)
            else:
                events += self.human_events(side, p['keys'])
        vy_before = m.ball.y_vel
        hit, scorer = m.step(events)
        b = m.ball
        self.spin_angle += b.rotation * 0.08
        self.trail.append((b.x, b.y))
        if hit:
            i = 0 if hit == 'left' else 1
            self.stats['hits'][i] += 1
            self.rally += 1
            self.stats['longest'] = max(self.stats['longest'], self.rally)
            self.stats['max_spin'] = max(self.stats['max_spin'], abs(b.rotation))
            self.last_hitter = i
            self.burst(b.x, b.y, self.players[i]['id']['primary'], 14, 1 if hit == 'left' else -1)
            self.sound.play('hit_l' if hit == 'left' else 'hit_r')
        elif not scorer and (vy_before > 0) != (b.y_vel > 0) and vy_before != 0:
            self.burst(b.x, b.y, (150, 150, 190), 4, 0)
            self.sound.play('wall')
        if scorer:
            self.on_goal(scorer)

    def on_goal(self, scorer):
        i = 0 if scorer == 'left' else 1
        p = self.players[i]
        self.shake = 14.0
        self.flash = (p['id']['primary'], time.time())
        self.rally = 0
        self.trail.clear()
        self.sound.play('goal')
        own = p['taunts']
        if own and (not self.stery or self.rng.random() < 0.6):
            text, src = self.rng.choice(own), p['id']['name']
        else:
            text, src = (self.rng.choice(self.stery) if self.stery else '!'), 'stery.txt'
        self.taunt = {'side': i, 'text': text, 'src': src, 't': time.time()}
        if self.match.winner:
            self.state = 'over'
        else:
            self.state = 'goal'
        self.state_t = time.time()
        self.auto_shot(f'goal_{self.match.score["left"]}-{self.match.score["right"]}')

    def burst(self, x, y, color, n, direction):
        for _ in range(n):
            a = self.rng.uniform(-1.2, 1.2) + (0 if direction >= 0 else math.pi)
            if direction == 0:
                a = self.rng.uniform(0, 2 * math.pi)
            v = self.rng.uniform(1.5, 5.5)
            self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v, self.rng.uniform(0.4, 0.9), color])

    # --- main loop ---------------------------------------------------------------
    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return
                if e.type == pygame.KEYDOWN and not self.on_key(e):
                    return
            self.update()
            self.draw()
            pygame.display.flip()
            self.capture()
            self.frame += 1
            if self.args.autoquit and self.state == 'over' and time.time() - self.state_t > self.over_hold():
                return
            if not self.args.uncapped:
                self.clock.tick(FPS)

    def over_hold(self):
        return 4.0 if not self.args.uncapped else 0.3

    def on_key(self, e):
        k = e.key
        if k == pygame.K_F12:
            self.save_shot('manual')
            return True
        if k == pygame.K_m:
            self.sound.on = not self.sound.on
            return True
        if self.state == 'menu':
            if k == pygame.K_ESCAPE:
                return False
            if k in (pygame.K_UP, pygame.K_w):
                self.menu_i = (self.menu_i - 1) % len(MODES)
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.menu_i = (self.menu_i + 1) % len(MODES)
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.start(MODES[self.menu_i][0])
            elif pygame.K_1 <= k <= pygame.K_4:
                self.start(MODES[k - pygame.K_1][0])
            return True
        if k == pygame.K_ESCAPE:
            self.state = 'menu'
            return True
        if k in (pygame.K_p, pygame.K_SPACE) and self.state in ('play', 'paused'):
            self.state = 'paused' if self.state == 'play' else 'play'
        elif k in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS) and self.mode == 'bots':
            self.speed = min(16, self.speed * 2)
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS) and self.mode == 'bots':
            self.speed = max(1, self.speed // 2)
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.state == 'over':
            self.start(self.mode)
        return True

    def pause_len(self, base):
        if self.args.uncapped:
            return 0.25
        return base if self.mode != 'bots' else max(0.9, base / max(1, self.speed / 2))

    def update(self):
        now = time.time()
        if self.state == 'intro' and now - self.state_t > self.pause_len(3.4):
            self.state = 'play'
            self.state_t = now
            self.sound.play('go')
        elif self.state == 'goal' and now - self.state_t > self.pause_len(2.6):
            self.state = 'play'
            self.taunt = None
        if self.state == 'play':
            steps = self.speed if self.mode == 'bots' else 1
            for _ in range(steps):
                self.tick()
                if self.state != 'play':
                    break
        # effects run on frames, not on game ticks
        for pt in self.particles:
            pt[0] += pt[2]
            pt[1] += pt[3]
            pt[2] *= 0.93
            pt[3] *= 0.93
            pt[4] -= 1 / 40
        self.particles = [p for p in self.particles if p[4] > 0]
        self.shake *= 0.86

    # --- drawing -----------------------------------------------------------------
    def draw(self):
        self.screen.blit(self.bg, (0, 0))
        if self.state == 'menu':
            self.draw_menu()
            return
        ox = oy = 0
        if self.shake > 0.5:
            ox = int(self.rng.uniform(-self.shake, self.shake))
            oy = int(self.rng.uniform(-self.shake, self.shake))
        self.draw_hud()
        self.draw_field(FX + ox, FY + oy)
        self.draw_footer()
        if self.state == 'intro':
            self.draw_intro()
        elif self.state == 'paused':
            self.banner('PAUZA', 'P nebo mezerník pokračuje')
        elif self.state == 'over':
            self.draw_over()
        if self.taunt and self.state in ('goal', 'over'):
            self.draw_taunt()

    def draw_field(self, x0, y0):
        s = self.screen
        frame = pygame.Rect(x0 - 6, y0 - 6, FW + 12, FH + 12)
        pygame.draw.rect(s, (40, 40, 70), frame, border_radius=10)
        s.blit(self.field_bg, (x0, y0))
        m = self.match
        for i, (side, pad) in enumerate((('left', m.left), ('right', m.right))):
            p = self.players[i]
            g = p['glow']
            s.blit(g, (x0 + pad.x + PADDLE_WIDTH // 2 - g.get_width() // 2,
                       y0 + pad.y + PADDLE_HEIGHT // 2 - g.get_height() // 2), special_flags=pygame.BLEND_ADD)
            s.blit(p['skin'], (x0 + pad.x, y0 + pad.y))
        col = self.players[self.last_hitter]['id']['primary'] if self.last_hitter is not None else (200, 200, 220)
        n = len(self.trail)
        for j, (tx, ty) in enumerate(self.trail):
            t = (j + 1) / max(1, n)
            pygame.draw.circle(s, mix(FIELD, col, t * 0.8), (x0 + tx, y0 + ty), max(1, int(BALL_RADIUS * t)))
        b = m.ball
        bx, by = x0 + b.x, y0 + b.y
        s.blit(self.ball_glow, (bx - 26, by - 26), special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(s, (255, 255, 255), (bx, by), BALL_RADIUS)
        if b.rotation:
            a = self.spin_angle
            pygame.draw.line(s, col, (bx - math.cos(a) * 5, by - math.sin(a) * 5),
                             (bx + math.cos(a) * 5, by + math.sin(a) * 5), 2)
        for px, py, _, _, life, c in self.particles:
            pygame.draw.circle(s, mix(FIELD, c, min(1, life * 1.3)), (x0 + px, y0 + py), max(1, int(3 * life)))
        if self.flash:
            c, t0 = self.flash
            a = max(0.0, 1 - (time.time() - t0) / 0.5)
            if a > 0:
                ov = pygame.Surface((FW, FH))
                ov.fill(c)
                ov.set_alpha(int(70 * a))
                s.blit(ov, (x0, y0))

    def draw_hud(self):
        s = self.screen
        m = self.match
        cw = 280
        for i, side in enumerate(('left', 'right')):
            p = self.players[i]
            ident = p['id']
            card = pygame.Rect(FX if i == 0 else FX + FW - cw, 18, cw, 116)
            pygame.draw.rect(s, (22, 22, 42), card, border_radius=14)
            pygame.draw.rect(s, ident['primary'], card, 2, border_radius=14)
            outer = 1 if i == 0 else -1  # +1: things grow to the right
            ex = card.x + 46 if i == 0 else card.right - 46
            pygame.draw.circle(s, ident['secondary'], (ex, card.y + 46), 30)
            pygame.draw.circle(s, ident['primary'], (ex, card.y + 46), 30, 3)
            letter = self.f_big.render(ident['name'][0], True, ident['primary'])
            s.blit(letter, letter.get_rect(center=(ex, card.y + 46)))
            name = self.f_mid.render(ident['name'], True, ident['primary'])
            title = self.f_small.render(ident['title'] + ('  ·  bot' if p['bot'] else ''), True, DIM)
            nx = card.x + 88 if i == 0 else card.right - 88
            s.blit(name, (nx if i == 0 else nx - name.get_width(), card.y + 18))
            s.blit(title, (nx if i == 0 else nx - title.get_width(), card.y + 56))
            score = m.score[side]
            for k in range(WINNING_SCORE):  # score pips
                px = ex - 18 * outer + outer * k * 14 if i == 0 else ex + 18 + outer * k * 14
                c = ident['primary'] if k < score else (50, 50, 76)
                pygame.draw.circle(s, c, (px, card.y + 98), 5)
        title = self.f_small.render('P O N G   D O J O', True, DIM)
        s.blit(title, title.get_rect(center=(SW // 2, 34)))
        ls = self.f_big.render(str(m.score['left']), True, self.players[0]['id']['primary'])
        rs = self.f_big.render(str(m.score['right']), True, self.players[1]['id']['primary'])
        colon = self.f_big.render(':', True, INK)
        s.blit(colon, colon.get_rect(center=(SW // 2, 70)))
        s.blit(ls, ls.get_rect(midright=(SW // 2 - 14, 70)))
        s.blit(rs, rs.get_rect(midleft=(SW // 2 + 14, 70)))
        for j, txt in enumerate((f'výměna {self.rally}', f'rotace {m.ball.rotation:+d}')):
            info = self.f_small.render(txt, True, DIM)
            s.blit(info, info.get_rect(center=(SW // 2, 104 + 20 * j)))

    def draw_footer(self):
        s = self.screen
        y = FY + FH + 22
        rules = self.f_small.render(
            f'fyzika z originálu 2022 beze změny:  hřiště {FW}×{FH}  ·  pálka {Paddle.VEL} px/tik  ·  '
            f'míček {Ball.MAX_VEL} px/tik  ·  {FPS} tiků/s  ·  do {WINNING_SCORE}', True, DIM)
        s.blit(rules, rules.get_rect(center=(SW // 2, y)))
        keys = 'P pauza  ·  M zvuk  ·  F12 snímek  ·  Esc menu'
        if self.mode == 'bots':
            keys = f'rychlost ×{self.speed} (+ / -)  ·  ' + keys
        k = self.f_small.render(keys, True, (90, 96, 124))
        s.blit(k, k.get_rect(center=(SW // 2, y + 24)))
        credit = self.f_small.render('originál: Marek Matas & co. (2022)  ·  aréna a boti: 2026', True, (70, 74, 100))
        s.blit(credit, credit.get_rect(center=(SW // 2, SH - 14)))

    def banner(self, big, small, color=INK):
        s = self.screen
        ov = pygame.Surface((FW, FH), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        s.blit(ov, (FX, FY))
        t = self.f_huge.render(big, True, color)
        s.blit(t, t.get_rect(center=(SW // 2, FY + FH // 2 - 20)))
        u = self.f_txt.render(small, True, DIM)
        s.blit(u, u.get_rect(center=(SW // 2, FY + FH // 2 + 40)))

    def draw_intro(self):
        s = self.screen
        el = (time.time() - self.state_t) / self.pause_len(3.4) * 3.4
        ov = pygame.Surface((FW, FH), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        s.blit(ov, (FX, FY))
        slide = min(1.0, el / 0.7)
        ease = 1 - (1 - slide) ** 3
        for i, p in enumerate(self.players):
            ident = p['id']
            name = self.f_big.render(ident['name'], True, ident['primary'])
            title = self.f_txt.render(ident['title'], True, INK)
            motto = self.f_small.render('„' + ident['motto'] + '“', True, DIM)
            cx = SW // 2 + (-1 if i == 0 else 1) * (170 + (1 - ease) * 500)
            s.blit(name, name.get_rect(center=(cx, FY + 80)))
            s.blit(title, title.get_rect(center=(cx, FY + 124)))
            s.blit(motto, motto.get_rect(center=(cx, FY + 150)))
            r = pygame.Rect(0, 0, int(PADDLE_WIDTH * 1.5), int(PADDLE_HEIGHT * 1.5))
            r.center = (cx, FY + 260)
            s.blit(pygame.transform.scale(p['skin'], r.size), r)
        if el > 0.5:
            vs = self.f_mid.render('VS', True, INK)
            s.blit(vs, vs.get_rect(center=(SW // 2, FY + 90)))
        if el > 1.2:
            n = int(3 - (el - 1.2) / 0.55) if el < 2.85 else 0
            txt = str(n) if n > 0 else 'HAJIME!'
            col = INK if n > 0 else (255, 210, 90)
            t = self.f_huge.render(txt, True, col)
            s.blit(t, t.get_rect(center=(SW // 2, FY + 420)))

    def draw_taunt(self):
        s = self.screen
        tt = self.taunt
        p = self.players[tt['side']]
        ident = p['id']
        width = 300
        lines = wrap(tt['text'], self.f_txt, width - 32)
        h = 52 + 24 * len(lines)
        x = FX + 40 if tt['side'] == 0 else FX + FW - 40 - width
        y = FY + FH // 2 - h // 2 if self.state != 'over' else FY + FH - h - 84  # clear of the stats
        box = pygame.Rect(x, y, width, h)
        sh = pygame.Surface(box.size, pygame.SRCALPHA)
        sh.fill((0, 0, 0, 215))  # the original TODO: black background under the sassy text
        s.blit(sh, box)
        pygame.draw.rect(s, ident['primary'], box, 2, border_radius=10)
        who = self.f_small.render(f'{ident["name"]} říká:' if tt['src'] != 'stery.txt'
                                  else f'{ident["name"]} · ze stery.txt', True, ident['primary'])
        s.blit(who, (x + 16, y + 12))
        for j, ln in enumerate(lines):
            s.blit(self.f_txt.render(ln, True, INK), (x + 16, y + 38 + 24 * j))

    def draw_over(self):
        m = self.match
        i = 0 if m.winner == 'left' else 1
        ident = self.players[i]['id']
        s = self.screen
        ov = pygame.Surface((FW, FH), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 175))
        s.blit(ov, (FX, FY))
        t = self.f_huge.render(f'{ident["name"]} VYHRÁL', True, ident['primary'])
        s.blit(t, t.get_rect(center=(SW // 2, FY + 110)))
        sc = self.f_big.render(f'{m.score["left"]} : {m.score["right"]}', True, INK)
        s.blit(sc, sc.get_rect(center=(SW // 2, FY + 190)))
        st = self.stats
        rows = [f'údery  {self.players[0]["id"]["name"]} {st["hits"][0]}  ·  {self.players[1]["id"]["name"]} {st["hits"][1]}',
                f'nejdelší výměna {st["longest"]}  ·  nejvyšší rotace {st["max_spin"]}',
                f'herní čas {m.tick / FPS:.0f} s']
        for j, r in enumerate(rows):
            u = self.f_txt.render(r, True, DIM)
            s.blit(u, u.get_rect(center=(SW // 2, FY + 250 + 28 * j)))
        u = self.f_txt.render('Enter odveta  ·  Esc menu', True, INK)
        s.blit(u, u.get_rect(center=(SW // 2, FY + FH - 50)))

    def draw_menu(self):
        s = self.screen
        t = self.f_huge.render('PONG DOJO', True, INK)
        s.blit(t, t.get_rect(center=(SW // 2, 120)))
        u = self.f_txt.render('aréna 2026  ·  na dojo Marka Matase & spol. z roku 2022', True, DIM)
        s.blit(u, u.get_rect(center=(SW // 2, 180)))
        for i, (mode, label, sub) in enumerate(MODES):
            r = pygame.Rect(SW // 2 - 260, 240 + i * 92, 520, 76)
            sel = i == self.menu_i
            pygame.draw.rect(s, (30, 30, 58) if sel else (20, 20, 38), r, border_radius=14)
            col = (255, 170, 60) if sel else (60, 62, 96)
            pygame.draw.rect(s, col, r, 2, border_radius=14)
            n = self.f_mid.render(f'{i + 1}', True, col)
            s.blit(n, (r.x + 22, r.y + 22))
            lab = self.f_mid.render(label, True, INK)
            s.blit(lab, (r.x + 64, r.y + 12))
            sb = self.f_small.render(sub, True, DIM)
            s.blit(sb, (r.x + 64, r.y + 46))
        for i, ident in enumerate((tygr.IDENTITY, drak.IDENTITY)):
            skin = pygame.transform.scale(paddle_skin(ident), (PADDLE_WIDTH * 2, PADDLE_HEIGHT * 2))
            x = SW // 2 - 360 if i == 0 else SW // 2 + 320
            s.blit(skin, (x, 300))
            nm = self.f_small.render(f'{ident["name"]} · {ident["title"]}', True, ident['primary'])
            s.blit(nm, nm.get_rect(center=(x + PADDLE_WIDTH, 530)))
        k = self.f_small.render('1–4 nebo šipky + Enter  ·  Esc konec', True, DIM)
        s.blit(k, k.get_rect(center=(SW // 2, SH - 40)))

    # --- screenshots and recording -----------------------------------------------
    def save_shot(self, label):
        out = self.args.shots or SHOTS_DIR
        os.makedirs(out, exist_ok=True)
        self.shot_n += 1
        path = os.path.join(out, f'{self.shot_n:03d}_{label}.png')
        pygame.image.save(self.screen, path)
        return path

    def auto_shot(self, label):
        self.pending_shot = label  # taken after the next draw, so the taunt is on it

    def capture(self):
        label = getattr(self, 'pending_shot', None)
        if label and self.args.shots:
            self.save_shot(label)
        self.pending_shot = None
        if self.args.shots and self.state == 'intro' and not getattr(self, 'intro_shot', False) \
                and time.time() - self.state_t > self.pause_len(3.4) * 0.6:
            self.intro_shot = True
            self.save_shot('intro')
        if self.args.shots and self.state == 'play' and self.args.shot_every and \
                self.match.tick - self.last_shot_t >= self.args.shot_every * FPS:
            self.last_shot_t = self.match.tick
            self.save_shot(f'play_t{self.match.tick // FPS:04d}s')
        if self.args.shots and self.state == 'over' and not getattr(self, 'final_shot', False) \
                and time.time() - self.state_t > 0.2:
            self.final_shot = True
            self.save_shot('final')
        if self.args.record and self.state != 'menu':
            if self.record_n < self.args.record_frames:
                os.makedirs(self.args.record, exist_ok=True)
                pygame.image.save(self.screen, os.path.join(self.args.record, f'f{self.record_n:05d}.png'))
                self.record_n += 1


def main():
    ap = argparse.ArgumentParser(description='PONG DOJO arena')
    ap.add_argument('--mode', choices=[m[0] for m in MODES], help='skip the menu')
    ap.add_argument('--speed', type=int, default=1, help='ticks per frame in a bot match (1, 2, 4 ...)')
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--shots', help='folder for automatic screenshots')
    ap.add_argument('--shot-every', type=int, default=0, help='also a screenshot every N seconds of game time')
    ap.add_argument('--record', help='folder for frame-by-frame recording')
    ap.add_argument('--record-frames', type=int, default=0)
    ap.add_argument('--autoquit', action='store_true', help='close after the match')
    ap.add_argument('--uncapped', action='store_true', help='no frame cap, short pauses (for capture)')
    ap.add_argument('--headless', action='store_true', help='no window (for capture)')
    args = ap.parse_args()
    Arena(args).run()
    pygame.quit()


if __name__ == '__main__':
    main()
