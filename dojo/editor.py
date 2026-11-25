"""Player creator: make and style your own player (human or bot), with a live preview.

Keys: up/down choose a row - left/right change it - Enter edits a text row (Enter again
to finish) or presses a button - V hears the voice - Esc back. Mouse: click a row, click
its left/right half to change it, scroll to move.
"""
import json
import random
import time

import pygame

from dojo import players as P
from dojo.looks import paddle_skin, draw_avatar

INK = (226, 230, 245)
DIM = (120, 126, 150)
HOT = (255, 170, 60)


def _cycle(lst, cur, d):
    try:
        i = lst.index(cur)
    except ValueError:
        i = 0
    return lst[(i + d) % len(lst)]


class Editor:
    def __init__(self, arena):
        self.a = arena
        self.customs = P.load_custom()
        self.target = 0  # 0 = new player, k = customs[k-1]
        self.p = P.new_player()
        self.row = 1
        self.editing = None
        self.msg = ('', 0)
        self.scroll = 0
        self.rows = self.build_rows()

    def build_rows(self):
        R = []
        R.append(('target', 'Upravit hráče', 'target'))
        R.append(('name', 'Jméno', 'text'))
        R.append(('title', 'Titul', 'text'))
        R.append(('motto', 'Motto', 'text'))
        R.append(('primary', 'Hlavní barva', 'color'))
        R.append(('secondary', 'Druhá barva', 'color'))
        R.append(('glow', 'Záře', 'color'))
        R.append(('paddle', 'Vzor pálky', P.PATTERNS))
        R.append(('avatar.shape', 'Tvar hlavy', P.SHAPES))
        R.append(('avatar.skin', 'Barva obličeje', 'color'))
        R.append(('avatar.accent', 'Doplňková barva', 'color'))
        R.append(('avatar.eyes', 'Oči', P.EYES))
        R.append(('avatar.mouth', 'Ústa', P.MOUTHS))
        R.append(('avatar.top', 'Na hlavě', P.TOPS))
        R.append(('avatar.marks', 'Kresba', P.MARKS))
        R.append(('voice.pitch', 'Hlas: výška', 'pitch'))
        R.append(('voice.effect', 'Hlas: efekt', P.EFFECTS))
        R.append(('level', 'Nadávky', P.LEVELS))
        R.append(('lines', 'Vlastní hlášky (odděl znakem |)', 'lines'))
        R.append(('brain', 'Kdo hraje', P.BRAINS))
        R.append(('skill', 'Dovednost bota', 'skill'))
        R.append(('save', '[ Uložit ]', 'button'))
        R.append(('delete', '[ Smazat ]', 'button'))
        R.append(('back', '[ Zpět do menu ]', 'button'))
        return R

    # --- value access ---------------------------------------------------------------
    def get(self, key):
        if key.startswith('avatar.'):
            return self.p['avatar'].get(key[7:])
        if key.startswith('voice.'):
            return self.p['voice'].get(key[6:])
        return self.p.get(key)

    def set(self, key, val):
        if key.startswith('avatar.'):
            self.p['avatar'][key[7:]] = val
        elif key.startswith('voice.'):
            self.p['voice'][key[6:]] = val
        else:
            self.p[key] = val

    def shown(self, key, kind):
        v = self.get(key) if kind not in ('target', 'button') else None
        if kind == 'target':
            return 'nový hráč' if self.target == 0 else self.customs[self.target - 1]['name']
        if kind == 'button':
            return ''
        if kind == 'color':
            return ''
        if kind == 'pitch':
            return f'{v:.2f}'
        if kind == 'lines':
            return ' | '.join(self.p.get('lines', [])) or '(žádné, jen hlášky z balíčku)'
        if kind == 'skill':
            return f'{v} / 10' + ('' if self.p['brain'] != 'human' else '  (jen pro bota)')
        if key == 'paddle':
            return P.PATTERN_CZ.get(v, v)
        if key == 'brain':
            return P.BRAIN_CZ.get(v, v)
        if key.startswith('avatar.'):
            return P.CZ.get(v, v)
        return str(v)

    def change(self, d):
        key, _, kind = self.rows[self.row]
        if kind == 'target':
            self.target = (self.target + d) % (len(self.customs) + 1)
            self.p = P.new_player() if self.target == 0 else json.loads(json.dumps(self.customs[self.target - 1]))
            self.p = P._tuplify(self.p)
        elif kind == 'color':
            self.set(key, _cycle(P.PALETTE, tuple(self.get(key)), d))
        elif kind == 'pitch':
            self.set(key, round(max(0.6, min(1.6, self.get(key) + 0.05 * d)), 2))
        elif kind == 'skill':
            self.set(key, max(1, min(10, int(self.get(key)) + d)))
        elif isinstance(kind, list):
            self.set(key, _cycle(kind, self.get(key), d))

    def press(self):
        key, _, kind = self.rows[self.row]
        if kind in ('text', 'lines'):
            self.editing = key
            self.buffer = ' | '.join(self.p.get('lines', [])) if kind == 'lines' else str(self.get(key))
            pygame.key.start_text_input()
        elif key == 'save':
            if not self.p['name'].strip():
                self.flash('Jméno nesmí být prázdné.')
                return
            pid = P.save_custom(self.p)
            self.customs = P.load_custom()
            self.target = next((i + 1 for i, c in enumerate(self.customs) if c['id'] == pid), 0)
            self.a.reload_roster()
            self.flash(f'Uloženo: {self.p["name"]}. Najdeš ho v nabídce Nový zápas.')
        elif key == 'delete':
            if self.target == 0:
                self.flash('Nový hráč ještě není uložený.')
                return
            P.delete_custom(self.customs[self.target - 1]['id'])
            self.customs = P.load_custom()
            self.target, self.p = 0, P.new_player()
            self.a.reload_roster()
            self.flash('Smazáno.')
        elif key == 'back':
            self.a.state = 'menu'
        elif kind != 'button':
            self.change(1)

    def finish_text(self):
        if self.editing == 'lines':
            self.p['lines'] = [t.strip() for t in self.buffer.split('|') if t.strip()]
        else:
            self.set(self.editing, self.buffer.strip()[:24 if self.editing == 'name' else 60])
        self.editing = None
        pygame.key.stop_text_input()

    def flash(self, text):
        self.msg = (text, time.time())

    def hear(self):
        pool = P.taunt_pool(self.p)
        if not pool:
            return
        text = random.choice(pool)[0]
        prof = self.p['voice']
        if self.a.voice.say(text, prof) is None:
            self.a.voice.prepare([text], [prof])
            self.flash('Hlas se připravuje, zkus V znovu za chvíli.')
        else:
            self.speak = (text, time.time())

    # --- events -----------------------------------------------------------------------
    def on_event(self, e):
        if self.editing:
            if e.type == pygame.TEXTINPUT:
                self.buffer += e.text
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    self.finish_text()
                elif e.key == pygame.K_BACKSPACE:
                    self.buffer = self.buffer[:-1]
            return
        if e.type == pygame.KEYDOWN:
            k = e.key
            if k == pygame.K_ESCAPE:
                self.a.state = 'menu'
            elif k in (pygame.K_UP, pygame.K_w):
                self.row = (self.row - 1) % len(self.rows)
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.row = (self.row + 1) % len(self.rows)
            elif k in (pygame.K_LEFT, pygame.K_a):
                self.change(-1)
            elif k in (pygame.K_RIGHT, pygame.K_d):
                self.change(1)
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.press()
            elif k == pygame.K_v:
                self.hear()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, rect in getattr(self, 'hit', []):
                if rect.collidepoint(e.pos):
                    if i == self.row:
                        kind = self.rows[i][2]
                        if kind in ('text', 'lines', 'button'):
                            self.press()
                        else:
                            self.change(-1 if e.pos[0] < rect.centerx else 1)
                    self.row = i
        elif e.type == pygame.MOUSEWHEEL:
            self.row = (self.row - e.y) % len(self.rows)

    # --- drawing ----------------------------------------------------------------------
    def draw(self, s):
        a = self.a
        t = a.f_big.render('TVORBA HRÁČE', True, INK)
        s.blit(t, (40, 22))
        hint = a.f_small.render('šipky: výběr a změna  ·  Enter: psát / potvrdit  ·  V: poslechnout hlas  ·  F11: celá obrazovka  ·  Esc: zpět', True, DIM)
        s.blit(hint, (42, 78))
        top, rh, visible = 108, 25, 23
        if self.row < self.scroll:
            self.scroll = self.row
        if self.row >= self.scroll + visible:
            self.scroll = self.row - visible + 1
        self.hit = []
        for vi, i in enumerate(range(self.scroll, min(len(self.rows), self.scroll + visible))):
            key, label, kind = self.rows[i]
            y = top + vi * rh
            r = pygame.Rect(30, y, 520, rh - 3)
            self.hit.append((i, r))
            sel = i == self.row
            if sel:
                pygame.draw.rect(s, (34, 34, 64), r, border_radius=6)
                pygame.draw.rect(s, HOT, r, 1, border_radius=6)
            s.blit(a.f_small.render(label, True, HOT if sel else DIM), (40, y + 3))
            if self.editing == key:
                val = self.buffer + ('|' if int(time.time() * 2) % 2 else ' ')
                col = (255, 255, 255)
            else:
                val = self.shown(key, kind)
                col = INK
            if kind == 'color':
                c = tuple(self.get(key))
                pygame.draw.rect(s, c, (300, y + 3, 60, rh - 9), border_radius=4)
                pygame.draw.rect(s, (200, 200, 220), (300, y + 3, 60, rh - 9), 1, border_radius=4)
            else:
                txt = a.f_small.render(val, True, col)
                if txt.get_width() > 240:
                    txt = txt.subsurface((txt.get_width() - 240 if self.editing == key else 0, 0, 240, txt.get_height()))
                s.blit(txt, (300, y + 3))
            if sel and kind not in ('text', 'lines', 'button'):
                s.blit(a.f_small.render('<', True, HOT), (278, y + 3))
                s.blit(a.f_small.render('>', True, HOT), (530, y + 3))
        # preview
        px = 600
        card = pygame.Rect(px, 108, 350, 560)
        pygame.draw.rect(s, (22, 22, 42), card, border_radius=16)
        pygame.draw.rect(s, self.p['primary'], card, 2, border_radius=16)
        now = time.time()
        mouth = 0.0
        sp = getattr(self, 'speak', None)
        if sp and now - sp[1] < 5:
            mouth = 0.5 + 0.5 * abs(__import__('math').sin((now - sp[1]) * 14))
        draw_avatar(s, (px + 175, 250), 170, self.p['avatar'], now, mouth, 3 * mouth)
        n = a.f_big.render(self.p['name'] or '?', True, self.p['primary'])
        s.blit(n, n.get_rect(center=(px + 175, 380)))
        ti = a.f_txt.render(self.p['title'], True, INK)
        s.blit(ti, ti.get_rect(center=(px + 175, 418)))
        mo = a.f_small.render('„' + self.p['motto'] + '“', True, DIM)
        s.blit(mo, mo.get_rect(center=(px + 175, 444)))
        skin = pygame.transform.scale(paddle_skin(self.p, 100), (30, 150))
        s.blit(skin, (px + 160, 470))
        br = a.f_small.render(P.BRAIN_CZ[self.p['brain']] + (f', dovednost {self.p["skill"]}' if self.p['brain'] != 'human' else ''),
                              True, DIM)
        s.blit(br, br.get_rect(center=(px + 175, 640)))
        text, t0 = self.msg
        if text and now - t0 < 4:
            m = a.f_txt.render(text, True, (140, 230, 90))
            s.blit(m, m.get_rect(center=(480, 700)))
