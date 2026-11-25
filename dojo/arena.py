"""PONG DOJO - the arena (2026), on the original game by Marek Matas & co. (2022).

    python -m dojo.arena                    # menu
    python -m dojo.arena --mode bots        # TYGR vs DRAK straight away

Rules: "Originál 2022" (the friend's physics, unchanged and proven by
tests/test_physics_unchanged.py) or the realistic engine with presets and sliders.
Players: TYGR, DRAK, two humans, and every player made in the creator.

Keys: arrows + Enter in menus - P / Space pause - +/- speed (bot match) - M sound -
F12 screenshot - Esc back.
"""
import argparse
import array
import math
import os
import random
import time
from collections import deque

import pygame

from config import WIDTH as FW, HEIGHT as FH, FPS
from dojo.engine import LEFT_UP, LEFT_DOWN, RIGHT_UP, RIGHT_DOWN
from dojo.contract import ask_bot
from dojo.physics2 import make_match
from dojo import rules as R
from dojo import players as P
from dojo.looks import paddle_skin, draw_avatar, mix
from dojo.voice import Voice
from dojo import paths

REPO = paths.REPO
SHOTS_DIR = paths.SHOTS_DIR

SW, SH = 980, 730
FX, FY = (SW - FW) // 2, 150

BG_TOP, BG_BOT = (16, 14, 34), (4, 4, 10)
FIELD = (12, 14, 26)
INK = (226, 230, 245)
DIM = (120, 126, 150)
HOT = (255, 170, 60)

MENU = [
    ('quick_bots', 'TYGR  vs  DRAK', 'boti proti sobě, hned'),
    ('quick_tygr', 'TY  vs  TYGR', 'hraješ vlevo: W/S nebo šipky'),
    ('setup', 'NOVÝ ZÁPAS', 'vyber oba hráče (i ty vlastní) a pravidla'),
    ('rules', 'PRAVIDLA', ''),
    ('editor', 'TVORBA HRÁČE', 'vytvoř si vlastního hráče nebo bota'),
]


def font(size, bold=False):
    for name in ('bahnschrift', 'segoeui', 'arial'):
        f = pygame.font.SysFont(name, size, bold=bold)
        if f:
            return f
    return pygame.font.Font(None, size)


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


def glow_sprite(radius, color, strength=1.0):
    s = pygame.Surface((radius * 2, radius * 2))
    s.fill((0, 0, 0))
    for r in range(radius, 0, -1):
        t = (1 - r / radius) ** 2 * strength
        pygame.draw.circle(s, tuple(min(255, int(c * t)) for c in color), (radius, radius), r)
    return s


class Sfx:
    """Tiny synth for hits and goals: no sound files."""

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
        rate = pygame.mixer.get_init()[0]
        n = int(rate * dur)
        buf = array.array('h')
        phase = 0.0
        for i in range(n):
            t = i / n
            phase += 2 * math.pi * freq * (1 + (slide - 1) * t) / rate
            env = min(1.0, i / 200) * (1 - t) ** 1.5
            buf.append(int(32767 * vol * env * (1 if math.sin(phase) > 0 else -1) * 0.6))
        if pygame.mixer.get_init()[2] == 2:  # the device may insist on stereo
            st = array.array('h')
            for v in buf:
                st.extend((v, v))
            buf = st
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, name):
        if self.ok and self.on:
            getattr(self, name).play()


class Arena:
    def __init__(self, args):
        self.args = args
        if args.headless:
            os.environ['SDL_VIDEODRIVER'] = 'dummy'
            os.environ['SDL_AUDIODRIVER'] = 'dummy'
        pygame.mixer.pre_init(22050, -16, 1, 512)  # must come before pygame.init()
        pygame.init()
        pygame.display.set_caption('PONG DOJO - aréna 2026')
        self.settings = load_settings()
        self.fullscreen = bool(args.fullscreen or self.settings.get('fullscreen'))
        flags = 0 if args.headless else pygame.SCALED  # SCALED: the game keeps its 980x730 layout at any screen size
        if self.fullscreen and not args.headless:
            flags |= pygame.FULLSCREEN
        self.screen = pygame.display.set_mode((SW, SH), flags)
        pygame.key.set_repeat(280, 45)
        pygame.key.stop_text_input()
        self.clock = pygame.time.Clock()
        self.f_huge = font(84, True)
        self.f_big = font(46, True)
        self.f_mid = font(26, True)
        self.f_txt = font(19)
        self.f_small = font(15)
        self.sfx = Sfx()
        self.voice = Voice()
        self.rng = random.Random(args.seed)
        self.bg = self.make_background()
        self.field_bg = self.make_field()
        self.ball_glow = glow_sprite(26, (255, 255, 255), 0.55)
        self.speed = max(1, args.speed)
        self.rules = R.load_last()
        if args.rules:
            self.rules = next(p for p in R.PRESETS if p.name.lower().startswith(args.rules.lower()))
        self.reload_roster()
        self.pick = {'left': 0, 'right': 1}
        self.state = 'menu'
        self.menu_i = 0
        self.setup_i = 0
        self.rules_i = 0
        self.editor = None
        self.frame = 0
        self.shot_n = 0
        self.last_shot_t = 0
        self.record_n = 0
        self.mode = None
        self.match = None
        self.particles = []
        self.shake = 0.0
        self.taunt = None
        self.pending_shot = None
        if args.mode:
            self.quick(args.mode)

    def reload_roster(self):
        self.roster = P.roster()
        for side in ('left', 'right'):
            if hasattr(self, 'pick') and self.pick[side] >= len(self.roster):
                self.pick[side] = 0

    # --- static art -------------------------------------------------------------------
    def make_background(self):
        s = pygame.Surface((SW, SH))
        for y in range(SH):
            pygame.draw.line(s, mix(BG_TOP, BG_BOT, y / SH), (0, y), (SW, y))
        rng = random.Random(3)
        for _ in range(90):
            x, y = rng.randrange(SW), rng.randrange(SH)
            c = rng.randint(30, 60)
            s.set_at((x, y), (c, c, c + 20))
        return s

    def make_field(self):
        s = pygame.Surface((FW, FH))
        s.fill(FIELD)
        for x in range(0, FW, 50):
            pygame.draw.line(s, (18, 21, 38), (x, 0), (x, FH))
        for y in range(0, FH, 50):
            pygame.draw.line(s, (18, 21, 38), (0, y), (FW, y))
        cx, cy = FW // 2, FH // 2
        for i in range(14):
            r = 92 - i * 0.6
            rect = pygame.Rect(0, 0, int(2 * r), int(2 * r))
            rect.center = (cx + i % 3 - 1, cy + i % 2)
            pygame.draw.arc(s, (34 + i, 32 + i, 58 + i), rect, math.radians(-60 + i * 2), math.radians(250 - i * 3), 2)
        for y in range(10, FH, FH // 20):
            if y % 2 == 1:
                continue
            pygame.draw.rect(s, (44, 48, 78), (FW // 2 - 3, y, 6, FH // 20))
        return s

    # --- match lifecycle --------------------------------------------------------------
    def quick(self, mode):
        ids = {p['id']: i for i, p in enumerate(self.roster)}
        if mode in ('bots', 'quick_bots'):
            self.pick = {'left': ids['tygr'], 'right': ids['drak']}
        elif mode in ('tygr', 'quick_tygr'):
            self.pick = {'left': ids['human'], 'right': ids['tygr']}
        elif mode == 'drak':
            self.pick = {'left': ids['human'], 'right': ids['drak']}
        elif mode == 'duel':
            self.pick = {'left': ids['human'], 'right': ids['human2']}
        self.start()

    def start(self):
        seed = self.rng.randrange(1 << 30)
        self.match = make_match(self.rules, seed)
        lp, rp = self.roster[self.pick['left']], self.roster[self.pick['right']]
        humans = [p['brain'] == 'human' for p in (lp, rp)]
        self.players = []
        for i, p in enumerate((lp, rp)):
            bot = P.make_brain(p, seed + i, self.rules)
            if bot is None:
                keys = 'any' if humans.count(True) == 1 else ('ws' if i == 0 else 'arrows')
            else:
                keys = None
            pad = self.match.left if i == 0 else self.match.right
            self.players.append({'id': p, 'bot': bot, 'keys': keys, 'taunts': P.taunt_pool(p),
                                 'skin': paddle_skin(p, pad.height), 'glow': glow_sprite(40, p['glow'], 0.35)})
        self.mode = 'bots' if not any(humans) else 'human'
        lines = [t for pl in self.players for t, _ in pl['taunts']]
        self.voice.prepare(lines, [pl['id']['voice'] for pl in self.players])
        self.trail = deque(maxlen=22)
        self.particles = []
        self.shake = 0.0
        self.flash = None
        self.spin_angle = 0.0
        self.rally = 0
        self.last_hitter = None
        self.stats = {'hits': [0, 0], 'longest': 0, 'max_spin': 0.0, 'max_speed': 0.0}
        self.taunt = None
        self.intro_shot = self.final_shot = False
        self.state = 'intro'
        self.state_t = time.time()

    def human_events(self, side, keys_kind):
        k = pygame.key.get_pressed()
        if keys_kind == 'ws':
            up, dn = k[pygame.K_w], k[pygame.K_s]
        elif keys_kind == 'arrows':
            up, dn = k[pygame.K_UP], k[pygame.K_DOWN]
        else:
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
        self.spin_angle += b.rotation * (0.08 if isinstance(b.rotation, int) else 1.5)
        self.trail.append((b.x, b.y))
        spd = math.hypot(b.x_vel, b.y_vel)
        self.stats['max_speed'] = max(self.stats['max_speed'], spd)
        if hit:
            i = 0 if hit == 'left' else 1
            self.stats['hits'][i] += 1
            self.rally += 1
            self.stats['longest'] = max(self.stats['longest'], self.rally)
            self.stats['max_spin'] = max(self.stats['max_spin'], abs(b.rotation))
            self.last_hitter = i
            self.burst(b.x, b.y, self.players[i]['id']['primary'], 14, 1 if hit == 'left' else -1)
            self.sfx.play('hit_l' if hit == 'left' else 'hit_r')
        elif not scorer and vy_before != 0 and (vy_before > 0) != (b.y_vel > 0):
            self.burst(b.x, b.y, (150, 150, 190), 4, 0)
            self.sfx.play('wall')
        if scorer:
            self.on_goal(scorer)

    def on_goal(self, scorer):
        i = 0 if scorer == 'left' else 1
        p = self.players[i]
        self.shake = 14.0
        self.flash = (p['id']['primary'], time.time())
        self.rally = 0
        self.trail.clear()
        self.sfx.play('goal')
        pool = p['taunts'] or [('!', p['id']['name'])]
        text, src = self.rng.choice(pool)
        said = self.voice.say(text, p['id']['voice'])
        secs, env = said if said else (0.0, [])
        self.taunt = {'side': i, 'text': text, 'src': src, 't': time.time(), 'secs': secs, 'env': env}
        self.state = 'over' if self.match.winner else 'goal'
        self.state_t = time.time()
        self.pending_shot = f'goal_{self.match.score["left"]}-{self.match.score["right"]}'

    def burst(self, x, y, color, n, direction):
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi) if direction == 0 else \
                self.rng.uniform(-1.2, 1.2) + (0 if direction > 0 else math.pi)
            v = self.rng.uniform(1.5, 5.5)
            self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v, self.rng.uniform(0.4, 0.9), color])

    def mouth_of(self, i):
        tt = self.taunt
        if not tt or tt['side'] != i:
            return 0.0
        el = time.time() - tt['t']
        if tt['env']:
            k = int(el * 30)
            return tt['env'][k] if k < len(tt['env']) else 0.0
        return 0.6 + 0.4 * math.sin(el * 15) if el < 1.2 else 0.0  # no voice: mime it

    # --- main loop --------------------------------------------------------------------
    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return
                if self.state == 'editor':
                    if e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                        self.toggle_fullscreen()
                    else:
                        self.editor.on_event(e)
                    continue
                if e.type == pygame.KEYDOWN and not self.on_key(e):
                    return
            self.update()
            self.draw()
            pygame.display.flip()
            self.capture()
            self.frame += 1
            if self.args.autoquit and self.state == 'over' and time.time() - self.state_t > (0.3 if self.args.uncapped else 6.0):
                return
            if not self.args.uncapped:
                self.clock.tick(FPS)

    def toggle_fullscreen(self):
        if self.args.headless:
            return
        pygame.display.toggle_fullscreen()
        self.fullscreen = not self.fullscreen
        self.settings['fullscreen'] = self.fullscreen
        save_settings(self.settings)

    def on_key(self, e):
        k = e.key
        if k == pygame.K_F11 or (k == pygame.K_RETURN and e.mod & pygame.KMOD_ALT):
            self.toggle_fullscreen()
            return True
        if k == pygame.K_F12:
            self.save_shot('manual')
            return True
        if k == pygame.K_m:
            self.sfx.on = not self.sfx.on
            self.voice.on = self.sfx.on
            return True
        up = k in (pygame.K_UP, pygame.K_w)
        down = k in (pygame.K_DOWN, pygame.K_s)
        left = k in (pygame.K_LEFT, pygame.K_a)
        right = k in (pygame.K_RIGHT, pygame.K_d)
        enter = k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
        if self.state == 'menu':
            if k == pygame.K_ESCAPE:
                return False
            if up:
                self.menu_i = (self.menu_i - 1) % len(MENU)
            elif down:
                self.menu_i = (self.menu_i + 1) % len(MENU)
            elif pygame.K_1 <= k <= pygame.K_5:
                self.menu_i = k - pygame.K_1
                self.menu_go()
            elif enter:
                self.menu_go()
            return True
        if self.state == 'setup':
            rows = 4
            if k == pygame.K_ESCAPE:
                self.state = 'menu'
            elif up:
                self.setup_i = (self.setup_i - 1) % rows
            elif down:
                self.setup_i = (self.setup_i + 1) % rows
            elif left or right:
                d = 1 if right else -1
                if self.setup_i < 2:
                    side = 'left' if self.setup_i == 0 else 'right'
                    self.pick[side] = (self.pick[side] + d) % len(self.roster)
                elif self.setup_i == 2:
                    self.cycle_preset(d)
            elif enter:
                self.start() if self.setup_i == 3 else setattr(self, 'setup_i', 3)
            return True
        if self.state == 'rules':
            rows = self.rules_rows()
            if k == pygame.K_ESCAPE or (enter and rows[self.rules_i] == 'done'):
                R.save_last(self.rules)
                self.state = 'menu'
            elif up:
                self.rules_i = (self.rules_i - 1) % len(rows)
            elif down:
                self.rules_i = (self.rules_i + 1) % len(rows)
            elif left or right:
                d = 1 if right else -1
                row = rows[self.rules_i]
                if row == 'preset':
                    self.cycle_preset(d)
                    self.rules_i = min(self.rules_i, len(self.rules_rows()) - 1)
                elif row != 'done':
                    fld, _, lo, hi, step = row
                    v = getattr(self.rules, fld) + d * step
                    v = max(lo, min(hi, v))
                    v = int(round(v)) if isinstance(lo, int) else round(v, 3)
                    self.rules = R.custom_from(self.rules, **{fld: v})
            return True
        # in a match
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
            self.start()
        return True

    def menu_go(self):
        item = MENU[self.menu_i][0]
        if item.startswith('quick'):
            self.quick(item)
        elif item == 'setup':
            self.state, self.setup_i = 'setup', 3
        elif item == 'rules':
            self.state, self.rules_i = 'rules', 0
        elif item == 'editor':
            from dojo.editor import Editor
            self.editor = Editor(self)
            self.state = 'editor'

    def cycle_preset(self, d):
        names = [p.name for p in R.PRESETS]
        i = names.index(self.rules.name) if self.rules.name in names else 0
        self.rules = R.PRESETS[(i + d) % len(R.PRESETS)]

    def rules_rows(self):
        return ['preset'] + ([] if self.rules.locked else list(R.SLIDERS)) + ['done']

    def pause_len(self, base):
        if self.args.uncapped:
            return 0.25
        return base if self.mode != 'bots' else max(0.9, base / max(1, self.speed / 2))

    def goal_pause(self):
        tt = self.taunt
        base = max(2.4, min(5.5, tt['secs'] + 0.4)) if tt and tt['secs'] else 2.6
        return self.pause_len(base) if self.speed <= 2 else self.pause_len(2.6)

    def update(self):
        now = time.time()
        if self.state == 'intro' and now - self.state_t > self.pause_len(3.4):
            self.state = 'play'
            self.state_t = now
            self.sfx.play('go')
        elif self.state == 'goal' and now - self.state_t > self.goal_pause():
            self.state = 'play'
            self.taunt = None
        if self.state == 'play':
            for _ in range(self.speed if self.mode == 'bots' else 1):
                self.tick()
                if self.state != 'play':
                    break
        for pt in self.particles:
            pt[0] += pt[2]
            pt[1] += pt[3]
            pt[2] *= 0.93
            pt[3] *= 0.93
            pt[4] -= 1 / 40
        self.particles = [p for p in self.particles if p[4] > 0]
        self.shake *= 0.86

    # --- drawing ----------------------------------------------------------------------
    def draw(self):
        self.screen.blit(self.bg, (0, 0))
        st = self.state
        if st == 'menu':
            return self.draw_menu()
        if st == 'setup':
            return self.draw_setup()
        if st == 'rules':
            return self.draw_rules()
        if st == 'editor':
            return self.editor.draw(self.screen)
        ox = oy = 0
        if self.shake > 0.5:
            ox = int(self.rng.uniform(-self.shake, self.shake))
            oy = int(self.rng.uniform(-self.shake, self.shake))
        self.draw_hud()
        self.draw_field(FX + ox, FY + oy)
        self.draw_footer()
        if st == 'intro':
            self.draw_intro()
        elif st == 'paused':
            self.banner('PAUZA', 'pokračuj klávesou P nebo mezerníkem')
        elif st == 'over':
            self.draw_over()
        if self.taunt and st in ('goal', 'over'):
            self.draw_taunt()

    def draw_field(self, x0, y0):
        s = self.screen
        pygame.draw.rect(s, (40, 40, 70), (x0 - 6, y0 - 6, FW + 12, FH + 12), border_radius=10)
        s.blit(self.field_bg, (x0, y0))
        m = self.match
        for i, pad in enumerate((m.left, m.right)):
            p = self.players[i]
            g = p['glow']
            s.blit(g, (x0 + pad.x + pad.width // 2 - g.get_width() // 2,
                       y0 + int(pad.y) + pad.height // 2 - g.get_height() // 2), special_flags=pygame.BLEND_ADD)
            s.blit(p['skin'], (x0 + pad.x, y0 + int(pad.y)))
        col = self.players[self.last_hitter]['id']['primary'] if self.last_hitter is not None else (200, 200, 220)
        n = len(self.trail)
        r0 = m.ball.radius
        for j, (tx, ty) in enumerate(self.trail):
            t = (j + 1) / max(1, n)
            pygame.draw.circle(s, mix(FIELD, col, t * 0.8), (x0 + tx, y0 + ty), max(1, int(r0 * t)))
        b = m.ball
        bx, by = x0 + b.x, y0 + b.y
        s.blit(self.ball_glow, (bx - 26, by - 26), special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(s, (255, 255, 255), (bx, by), r0)
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
        now = time.time()
        cw = 280
        for i, side in enumerate(('left', 'right')):
            p = self.players[i]
            ident = p['id']
            card = pygame.Rect(FX if i == 0 else FX + FW - cw, 18, cw, 116)
            pygame.draw.rect(s, (22, 22, 42), card, border_radius=14)
            pygame.draw.rect(s, ident['primary'], card, 2, border_radius=14)
            ex = card.x + 48 if i == 0 else card.right - 48
            mouth = self.mouth_of(i)
            draw_avatar(s, (ex, card.y + 50), 66, ident['avatar'], now + i * 3, mouth, 2.5 * mouth, blink_seed=i * 11)
            name = self.f_mid.render(ident['name'], True, ident['primary'])
            sub = ident['title'] + ('  ·  bot' if p['bot'] is not None else '  ·  člověk')
            title = self.f_small.render(sub, True, DIM)
            nx = card.x + 92 if i == 0 else card.right - 92
            s.blit(name, (nx if i == 0 else nx - name.get_width(), card.y + 18))
            s.blit(title, (nx if i == 0 else nx - title.get_width(), card.y + 56))
            score = m.score[side]
            pts = self.target_points()
            step = 14 if pts <= 12 else max(5, 140 // pts)
            for k in range(pts):
                px = ex - 18 + k * step if i == 0 else ex + 18 - k * step
                c = ident['primary'] if k < score else (50, 50, 76)
                pygame.draw.circle(s, c, (px, card.y + 100), 5 if step >= 12 else 3)
        t = self.f_small.render('P O N G   D O J O', True, DIM)
        s.blit(t, t.get_rect(center=(SW // 2, 34)))
        ls = self.f_big.render(str(m.score['left']), True, self.players[0]['id']['primary'])
        rs = self.f_big.render(str(m.score['right']), True, self.players[1]['id']['primary'])
        colon = self.f_big.render(':', True, INK)
        s.blit(colon, colon.get_rect(center=(SW // 2, 70)))
        s.blit(ls, ls.get_rect(midright=(SW // 2 - 14, 70)))
        s.blit(rs, rs.get_rect(midleft=(SW // 2 + 14, 70)))
        rot = m.ball.rotation
        rtxt = f'rotace {rot:+d}' if isinstance(rot, int) else f'rotace {rot * 100:+.0f}'
        for j, txt in enumerate((f'výměna {self.rally}', rtxt)):
            info = self.f_small.render(txt, True, DIM)
            s.blit(info, info.get_rect(center=(SW // 2, 104 + 20 * j)))

    def target_points(self):
        return self.rules.points if not self.rules.locked else 10

    def draw_footer(self):
        s = self.screen
        y = FY + FH + 22
        r = self.rules
        if r.locked:
            txt = 'pravidla: Originál 2022 beze změny  ·  hřiště 700×500  ·  pálka 2 px/tik  ·  míček 5 px/tik  ·  60 tiků/s  ·  do 10'
        else:
            spd = math.hypot(self.match.ball.x_vel, self.match.ball.y_vel)
            txt = (f'pravidla: {r.name}  ·  míček {spd:.1f} px/tik (start {r.ball_speed:g}, max {r.max_ball_speed:g})  ·  '
                   f'pálka max {r.paddle_speed:g} px/tik  ·  do {r.points}')
        rules = self.f_small.render(txt, True, DIM)
        s.blit(rules, rules.get_rect(center=(SW // 2, y)))
        keys = 'P pauza  ·  M zvuk  ·  F11 celá obrazovka  ·  F12 snímek  ·  Esc menu'
        if self.mode == 'bots':
            keys = f'rychlost ×{self.speed} (+ / -)  ·  ' + keys
        k = self.f_small.render(keys, True, (90, 96, 124))
        s.blit(k, k.get_rect(center=(SW // 2, y + 24)))
        credit = self.f_small.render('originál: Marek Matas a spol. (2022)  ·  aréna, boti a realistická fyzika: 2026', True, (70, 74, 100))
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
        ease = 1 - (1 - min(1.0, el / 0.7)) ** 3
        for i, p in enumerate(self.players):
            ident = p['id']
            cx = SW // 2 + (-1 if i == 0 else 1) * (170 + (1 - ease) * 500)
            draw_avatar(s, (cx, FY + 110), 110, ident['avatar'], time.time() + i, 0.0, 0.0, blink_seed=i * 7)
            name = self.f_big.render(ident['name'], True, ident['primary'])
            s.blit(name, name.get_rect(center=(cx, FY + 210)))
            title = self.f_txt.render(ident['title'], True, INK)
            s.blit(title, title.get_rect(center=(cx, FY + 250)))
            motto = self.f_small.render('„' + ident['motto'] + '“', True, DIM)
            s.blit(motto, motto.get_rect(center=(cx, FY + 276)))
            r = pygame.Rect(0, 0, 22, 110)
            r.center = (cx, FY + 352)
            s.blit(pygame.transform.scale(p['skin'], r.size), r)
        if el > 0.5:
            vs = self.f_mid.render('VS', True, INK)
            s.blit(vs, vs.get_rect(center=(SW // 2, FY + 210)))
            rn = self.f_small.render(f'pravidla: {self.rules.name}', True, DIM)
            s.blit(rn, rn.get_rect(center=(SW // 2, FY + 250)))
        if el > 1.2:
            n = int(3 - (el - 1.2) / 0.55) if el < 2.85 else 0
            t = self.f_huge.render(str(n) if n > 0 else 'HAJIME!', True, INK if n > 0 else (255, 210, 90))
            s.blit(t, t.get_rect(center=(SW // 2, FY + 445)))

    def draw_taunt(self):
        s = self.screen
        tt = self.taunt
        i = tt['side']
        ident = self.players[i]['id']
        width = 330
        lines = wrap(tt['text'], self.f_mid if len(tt['text']) < 60 else self.f_txt, width - 32)
        lf = self.f_mid if len(tt['text']) < 60 else self.f_txt
        h = 50 + (lf.get_height() + 2) * len(lines)
        x = SW // 2 - width // 2 + (-110 if i == 0 else 110)
        y = FY + FH // 2 - h // 2 + 60 if self.state != 'over' else FY + FH - h - 84
        mouth = self.mouth_of(i)
        if self.state != 'over':  # the big screaming head, above the box
            draw_avatar(s, (x + width // 2, y - 80), 120, ident['avatar'], time.time(), mouth, 6 * mouth, blink_seed=3)
        box = pygame.Rect(x, y, width, h)
        sh = pygame.Surface(box.size, pygame.SRCALPHA)
        sh.fill((0, 0, 0, 220))
        s.blit(sh, box)
        pygame.draw.rect(s, ident['primary'], box, 2 + int(3 * mouth), border_radius=10)
        who = f'{ident["name"]} řve:' if tt['src'] != 'stery.txt' else f'{ident["name"]} · ze stery.txt'
        s.blit(self.f_small.render(who, True, ident['primary']), (x + 16, y + 12))
        for j, ln in enumerate(lines):
            s.blit(lf.render(ln, True, INK), (x + 16, y + 36 + (lf.get_height() + 2) * j))

    def draw_over(self):
        m = self.match
        i = 0 if m.winner == 'left' else 1
        ident = self.players[i]['id']
        s = self.screen
        ov = pygame.Surface((FW, FH), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 175))
        s.blit(ov, (FX, FY))
        t = self.f_huge.render(f'{ident["name"]} VYHRÁL', True, ident['primary'])
        if t.get_width() > FW - 40:
            t = self.f_big.render(f'{ident["name"]} VYHRÁL', True, ident['primary'])
        s.blit(t, t.get_rect(center=(SW // 2, FY + 100)))
        sc = self.f_big.render(f'{m.score["left"]} : {m.score["right"]}', True, INK)
        s.blit(sc, sc.get_rect(center=(SW // 2, FY + 175)))
        st = self.stats
        n0, n1 = self.players[0]['id']['name'], self.players[1]['id']['name']
        spin = f'{st["max_spin"]:.0f}' if self.rules.locked else f'{st["max_spin"] * 100:.0f}'
        rows = [f'údery  {n0} {st["hits"][0]}  ·  {n1} {st["hits"][1]}',
                f'nejdelší výměna {st["longest"]}  ·  nejvyšší rotace {spin}  ·  max. rychlost {st["max_speed"]:.1f} px/tik',
                f'herní čas {m.tick / FPS:.0f} s  ·  pravidla {self.rules.name}']
        for j, r in enumerate(rows):
            u = self.f_txt.render(r, True, DIM)
            s.blit(u, u.get_rect(center=(SW // 2, FY + 235 + 28 * j)))
        u = self.f_txt.render('Enter odveta  ·  Esc menu', True, INK)
        s.blit(u, u.get_rect(center=(SW // 2, FY + FH - 40)))

    def draw_menu(self):
        s = self.screen
        now = time.time()
        t = self.f_huge.render('PONG DOJO', True, INK)
        s.blit(t, t.get_rect(center=(SW // 2, 100)))
        u = self.f_txt.render('aréna 2026  ·  podle hry Marka Matase a spol. z roku 2022', True, DIM)
        s.blit(u, u.get_rect(center=(SW // 2, 158)))
        for i, (item, label, sub) in enumerate(MENU):
            r = pygame.Rect(SW // 2 - 250, 200 + i * 82, 500, 68)
            sel = i == self.menu_i
            pygame.draw.rect(s, (30, 30, 58) if sel else (20, 20, 38), r, border_radius=14)
            col = HOT if sel else (60, 62, 96)
            pygame.draw.rect(s, col, r, 2, border_radius=14)
            s.blit(self.f_mid.render(str(i + 1), True, col), (r.x + 22, r.y + 18))
            s.blit(self.f_mid.render(label, True, INK), (r.x + 64, r.y + 8))
            if item == 'rules':
                sub = f'teď: {self.rules.name}' + ('  (zamčená, původní fyzika z roku 2022)' if self.rules.locked else '  (realistická fyzika)')
            s.blit(self.f_small.render(sub, True, DIM), (r.x + 64, r.y + 42))
        for i, pid in enumerate(('tygr', 'drak')):
            p = next(x for x in self.roster if x['id'] == pid)
            cx = SW // 2 - 370 if i == 0 else SW // 2 + 370
            draw_avatar(s, (cx, 330), 130, p['avatar'], now + i * 2, 0.0, 0.0, blink_seed=i * 5)
            nm = self.f_mid.render(p['name'], True, p['primary'])
            s.blit(nm, nm.get_rect(center=(cx, 430)))
            tl = self.f_small.render(p['title'], True, DIM)
            s.blit(tl, tl.get_rect(center=(cx, 458)))
        k = self.f_small.render('1–5 nebo šipky + Enter  ·  F11 celá obrazovka  ·  Esc konec', True, DIM)
        s.blit(k, k.get_rect(center=(SW // 2, SH - 30)))

    def draw_setup(self):
        s = self.screen
        now = time.time()
        t = self.f_big.render('NOVÝ ZÁPAS', True, INK)
        s.blit(t, t.get_rect(center=(SW // 2, 50)))
        for i, side in enumerate(('left', 'right')):
            p = self.roster[self.pick[side]]
            cx = SW // 2 - 240 if i == 0 else SW // 2 + 240
            card = pygame.Rect(cx - 190, 90, 380, 400)
            sel = self.setup_i == i
            pygame.draw.rect(s, (22, 22, 42), card, border_radius=16)
            pygame.draw.rect(s, HOT if sel else p['primary'], card, 3 if sel else 2, border_radius=16)
            s.blit(self.f_small.render('LEVÝ' if i == 0 else 'PRAVÝ', True, DIM), (card.x + 16, card.y + 12))
            draw_avatar(s, (cx, 200), 140, p['avatar'], now + i, 0.0, 0.0, blink_seed=i * 9)
            nm = self.f_big.render(p['name'], True, p['primary'])
            s.blit(nm, nm.get_rect(center=(cx, 320)))
            tl = self.f_txt.render(p['title'], True, INK)
            s.blit(tl, tl.get_rect(center=(cx, 360)))
            br = P.BRAIN_CZ[p['brain']] + (f', dovednost {p.get("skill", 10)}' if p['brain'] != 'human' else '')
            b = self.f_small.render(br + f'  ·  nadávky: {p.get("level", "drsné")}', True, DIM)
            s.blit(b, b.get_rect(center=(cx, 390)))
            skin = pygame.transform.scale(paddle_skin(p, 100), (16, 72))
            s.blit(skin, skin.get_rect(center=(cx, 440)))
            if sel:
                s.blit(self.f_mid.render('<', True, HOT), (card.x + 14, 190))
                s.blit(self.f_mid.render('>', True, HOT), (card.right - 30, 190))
        vs = self.f_mid.render('VS', True, INK)
        s.blit(vs, vs.get_rect(center=(SW // 2, 290)))
        rr = pygame.Rect(SW // 2 - 300, 520, 600, 56)
        sel = self.setup_i == 2
        pygame.draw.rect(s, (30, 30, 58) if sel else (20, 20, 38), rr, border_radius=12)
        pygame.draw.rect(s, HOT if sel else (60, 62, 96), rr, 2, border_radius=12)
        s.blit(self.f_txt.render(f'pravidla:  < {self.rules.name} >', True, INK), (rr.x + 20, rr.y + 15))
        sr = pygame.Rect(SW // 2 - 120, 600, 240, 60)
        sel = self.setup_i == 3
        pygame.draw.rect(s, (60, 40, 20) if sel else (30, 26, 40), sr, border_radius=14)
        pygame.draw.rect(s, HOT if sel else (90, 80, 70), sr, 3, border_radius=14)
        st = self.f_mid.render('START', True, HOT if sel else INK)
        s.blit(st, st.get_rect(center=sr.center))
        k = self.f_small.render('nahoru/dolů vybírá  ·  vlevo/vpravo mění hráče a pravidla  ·  Enter start  ·  Esc zpět', True, DIM)
        s.blit(k, k.get_rect(center=(SW // 2, SH - 30)))

    def draw_rules(self):
        s = self.screen
        t = self.f_big.render('PRAVIDLA', True, INK)
        s.blit(t, t.get_rect(center=(SW // 2, 46)))
        rows = self.rules_rows()
        y = 100
        for i, row in enumerate(rows):
            sel = i == self.rules_i
            r = pygame.Rect(SW // 2 - 330, y, 660, 34)
            if sel:
                pygame.draw.rect(s, (34, 34, 64), r, border_radius=8)
                pygame.draw.rect(s, HOT, r, 1, border_radius=8)
            if row == 'preset':
                s.blit(self.f_txt.render('sada pravidel', True, HOT if sel else DIM), (r.x + 16, y + 6))
                s.blit(self.f_mid.render(f'< {self.rules.name} >', True, INK), (r.x + 300, y + 2))
            elif row == 'done':
                s.blit(self.f_txt.render('[ Hotovo ]', True, HOT if sel else INK), (r.x + 16, y + 6))
            else:
                fld, label, lo, hi, step = row
                v = getattr(self.rules, fld)
                s.blit(self.f_txt.render(label, True, HOT if sel else DIM), (r.x + 16, y + 6))
                bar = pygame.Rect(r.x + 300, y + 13, 240, 8)
                pygame.draw.rect(s, (50, 50, 76), bar, border_radius=4)
                fill = bar.copy()
                fill.width = int(bar.width * (v - lo) / (hi - lo))
                pygame.draw.rect(s, HOT if sel else (120, 140, 200), fill, border_radius=4)
                s.blit(self.f_txt.render(f'{v:g}', True, INK), (r.x + 560, y + 6))
            y += 38 if row != 'preset' else 46
        if self.rules.locked:
            info = ['Originál 2022 je hra Marka Matase přesně tak, jak ji napsal:',
                    'míček 5 px za tik, pálka 2 px za tik bez setrvačnosti, rotaci dává klávesa držená při úderu,',
                    'hřiště 700 × 500, hraje se do 10. Pravidla jsou zamčená a hlídá je test.',
                    'Šipkou vlevo nebo vpravo přepneš na realistickou fyziku s posuvníky.']
            for j, ln in enumerate(info):
                u = self.f_txt.render(ln, True, DIM)
                s.blit(u, u.get_rect(center=(SW // 2, 260 + 30 * j)))
        k = self.f_small.render('nahoru/dolů vybírá  ·  vlevo/vpravo mění  ·  pohnutím posuvníku vznikne sada Vlastní  ·  Esc nebo Hotovo uloží',
                                True, DIM)
        s.blit(k, k.get_rect(center=(SW // 2, SH - 24)))

    # --- screenshots and recording ----------------------------------------------------
    def save_shot(self, label):
        out = self.args.shots or SHOTS_DIR
        os.makedirs(out, exist_ok=True)
        self.shot_n += 1
        path = os.path.join(out, f'{self.shot_n:03d}_{label}.png')
        pygame.image.save(self.screen, path)
        return path

    def capture(self):
        a = self.args
        if self.pending_shot and a.shots:
            self.save_shot(self.pending_shot)
        self.pending_shot = None
        if not a.shots or self.match is None:
            pass
        elif self.state == 'intro' and not self.intro_shot and time.time() - self.state_t > self.pause_len(3.4) * 0.6:
            self.intro_shot = True
            self.save_shot('intro')
        elif self.state == 'play' and a.shot_every and self.match.tick - self.last_shot_t >= a.shot_every * FPS:
            self.last_shot_t = self.match.tick
            self.save_shot(f'play_t{self.match.tick // FPS:04d}s')
        elif self.state == 'over' and not self.final_shot and time.time() - self.state_t > 0.2:
            self.final_shot = True
            self.save_shot('final')
        if a.record and self.state not in ('menu', 'setup', 'rules', 'editor') and self.record_n < a.record_frames:
            os.makedirs(a.record, exist_ok=True)
            pygame.image.save(self.screen, os.path.join(a.record, f'f{self.record_n:05d}.png'))
            self.record_n += 1


SETTINGS = paths.SETTINGS  # per-PC settings (fullscreen), kept out of git


def load_settings():
    try:
        import json
        with open(SETTINGS, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_settings(d):
    try:
        import json
        with open(SETTINGS, 'w', encoding='utf-8') as fh:
            json.dump(d, fh)
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser(description='PONG DOJO arena')
    ap.add_argument('--fullscreen', action='store_true', help='start in fullscreen (F11 toggles)')
    ap.add_argument('--mode', choices=['bots', 'tygr', 'drak', 'duel'], help='skip the menu')
    ap.add_argument('--rules', help='preset name (Originál, Realistický, Arkáda, Zpomalený)')
    ap.add_argument('--speed', type=int, default=1, help='ticks per frame in a bot match')
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--shots', help='folder for automatic screenshots')
    ap.add_argument('--shot-every', type=int, default=0)
    ap.add_argument('--record', help='folder for frame-by-frame recording')
    ap.add_argument('--record-frames', type=int, default=0)
    ap.add_argument('--autoquit', action='store_true')
    ap.add_argument('--uncapped', action='store_true')
    ap.add_argument('--headless', action='store_true')
    args = ap.parse_args()
    Arena(args).run()
    pygame.quit()


if __name__ == '__main__':
    main()
