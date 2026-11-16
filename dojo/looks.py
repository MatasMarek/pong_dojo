"""Paddle skins and avatar faces, drawn from code (no image files).

draw_avatar(...) takes the player's avatar spec plus two live values from the arena:
mouth (0 = shut, 1 = wide open, driven by the voice) and shake (px, when screaming).
"""
import math
import random

import pygame

from config import PADDLE_WIDTH


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def paddle_skin(ident, height):
    w, h = PADDLE_WIDTH, int(height)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    p, q, g = ident['primary'], ident['secondary'], ident['glow']
    kind = ident.get('paddle', 'plain')
    rng = random.Random(7)
    if kind == 'stripes':
        s.fill(p)
        y = -8
        while y < h + 8:
            th, slant = rng.randint(4, 7), rng.randint(5, 9)
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
        pygame.draw.rect(s, g, (0, 0, w, h), 2)
    elif kind == 'flames':
        s.fill(q)
        for y in range(h, -20, -14):
            for x0 in (0, 10):
                pts = [(x0, y), (x0 + 5, y - rng.randint(14, 22)), (x0 + 10, y)]
                pygame.draw.polygon(s, p, pts)
                pygame.draw.polygon(s, g, [(x0 + 3, y), (x0 + 5, y - 9), (x0 + 7, y)])
    elif kind == 'lightning':
        s.fill(q)
        y = 0
        x = w // 2
        pts = [(x, 0)]
        while y < h:
            y += rng.randint(8, 14)
            x = rng.randint(3, w - 3)
            pts.append((x, min(h, y)))
        pygame.draw.lines(s, g, False, pts, 4)
        pygame.draw.lines(s, p, False, pts, 2)
    elif kind == 'checker':
        for yy in range(0, h, 10):
            for xx in range(0, w, 10):
                pygame.draw.rect(s, p if (xx // 10 + yy // 10) % 2 == 0 else q, (xx, yy, 10, 10))
    elif kind == 'dots':
        s.fill(q)
        for yy in range(5, h, 10):
            for xx in (5, 15):
                pygame.draw.circle(s, p if (yy // 10) % 2 else g, (xx, yy), 3)
    else:
        for y in range(h):
            t = abs(y - h / 2) / (h / 2)
            pygame.draw.line(s, mix(p, q, 0.15 + 0.5 * t), (0, y), (w, y))
        pygame.draw.rect(s, (255, 255, 255), (2, 0, 2, h))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=6)
    s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return s


def draw_avatar(surf, center, size, spec, t=0.0, mouth=0.0, shake=0.0, blink_seed=0):
    """Draw a face of diameter ~size centred at center."""
    cx, cy = center
    if shake:
        cx += math.sin(t * 61) * shake
        cy += math.cos(t * 47) * shake * 0.6
    u = size / 100.0
    skin = spec.get('skin', (240, 200, 170))
    acc = spec.get('accent', (40, 30, 30))
    dark = mix(skin, (0, 0, 0), 0.55)
    light = mix(skin, (255, 255, 255), 0.35)
    shape = spec.get('shape', 'round')

    # head outline rect
    if shape == 'long':
        hw, hh = 64 * u, 92 * u
    elif shape == 'square':
        hw, hh = 82 * u, 82 * u
    elif shape == 'triangle':
        hw, hh = 88 * u, 86 * u
    else:
        hw, hh = 84 * u, 84 * u
    head = pygame.Rect(0, 0, int(hw), int(hh))
    head.center = (int(cx), int(cy))

    # top features behind the head
    top = spec.get('top', 'none')
    if top == 'ears':
        for sx in (-1, 1):
            ex = cx + sx * hw * 0.36
            pts = [(ex - 14 * u, head.top + 14 * u), (ex + sx * 4 * u, head.top - 16 * u), (ex + 14 * u, head.top + 10 * u)]
            pygame.draw.polygon(surf, skin, pts)
            pygame.draw.polygon(surf, dark, pts, max(1, int(2 * u)))
            inner = [(ex - 7 * u, head.top + 10 * u), (ex + sx * 3 * u, head.top - 6 * u), (ex + 7 * u, head.top + 8 * u)]
            pygame.draw.polygon(surf, mix(skin, (255, 180, 190), 0.5), inner)
    elif top == 'horns':
        for sx in (-1, 1):
            bx = cx + sx * hw * 0.28
            pts = [(bx - 6 * u, head.top + 8 * u), (bx + sx * 18 * u, head.top - 26 * u), (bx + 7 * u, head.top + 6 * u)]
            pygame.draw.polygon(surf, acc, pts)
            pygame.draw.polygon(surf, mix(acc, (0, 0, 0), 0.4), pts, max(1, int(2 * u)))
    elif top == 'spikes':
        for i in range(5):
            bx = head.left + hw * (0.15 + i * 0.175)
            pygame.draw.polygon(surf, acc, [(bx - 7 * u, head.top + 8 * u), (bx, head.top - 14 * u), (bx + 7 * u, head.top + 8 * u)])
    elif top == 'antennae':
        for sx in (-1, 1):
            bx = cx + sx * hw * 0.2
            tip = (bx + sx * 12 * u, head.top - 22 * u)
            pygame.draw.line(surf, acc, (bx, head.top + 4 * u), tip, max(1, int(3 * u)))
            pygame.draw.circle(surf, acc, tip, int(5 * u))

    # head
    if shape == 'triangle':
        pts = [(head.left, head.top + 10 * u), (head.right, head.top + 10 * u), (cx, head.bottom)]
        pygame.draw.polygon(surf, skin, pts)
        pygame.draw.polygon(surf, dark, pts, max(1, int(3 * u)))
    elif shape == 'square':
        pygame.draw.rect(surf, skin, head, border_radius=int(16 * u))
        pygame.draw.rect(surf, dark, head, max(1, int(3 * u)), border_radius=int(16 * u))
    else:
        pygame.draw.ellipse(surf, skin, head)
        pygame.draw.ellipse(surf, dark, head, max(1, int(3 * u)))

    # markings
    marks = spec.get('marks', 'none')
    clip = surf.get_clip()
    surf.set_clip(head)
    if marks == 'stripes':
        for i, sx in enumerate((-1, 1)):
            for k in range(3):
                y = head.top + hh * (0.22 + k * 0.16)
                x0 = cx + sx * hw * 0.5
                pygame.draw.polygon(surf, acc, [(x0, y), (x0 - sx * 22 * u, y + 4 * u), (x0, y + 9 * u)])
        pygame.draw.polygon(surf, acc, [(cx - 6 * u, head.top), (cx, head.top + 18 * u), (cx + 6 * u, head.top)])
    elif marks == 'scales':
        for row in range(6):
            for col in range(6):
                x = head.left + col * 15 * u + (7 * u if row % 2 else 0)
                y = head.top + row * 14 * u
                pygame.draw.arc(surf, mix(skin, acc, 0.35), (x, y, 14 * u, 12 * u), math.pi, 2 * math.pi, max(1, int(u)))
    elif marks == 'spots':
        rng = random.Random(3)
        for _ in range(9):
            pygame.draw.circle(surf, mix(skin, acc, 0.6),
                               (head.left + rng.random() * hw, head.top + rng.random() * hh * 0.6), int(rng.uniform(3, 6) * u))
    elif marks == 'scar':
        pygame.draw.line(surf, (150, 40, 50), (cx + 8 * u, head.top + 18 * u), (cx + 26 * u, head.top + 52 * u), max(1, int(3 * u)))
    surf.set_clip(clip)

    if spec.get('muzzle'):
        pygame.draw.ellipse(surf, light, (cx - 24 * u, cy + 4 * u, 48 * u, 32 * u))

    # eyes
    eyes = spec.get('eyes', 'calm')
    blink = (int(t * 10) + blink_seed) % 37 == 0 and mouth < 0.2
    ey = cy - 10 * u
    for sx in (-1, 1):
        ex = cx + sx * 17 * u
        if blink or eyes == 'sleepy':
            pygame.draw.line(surf, (20, 20, 20), (ex - 8 * u, ey + 2 * u), (ex + 8 * u, ey + 2 * u), max(1, int(3 * u)))
            if eyes == 'sleepy' and not blink:
                pygame.draw.circle(surf, (20, 20, 20), (ex, ey + 4 * u), int(3 * u))
            continue
        white = (250, 250, 240) if eyes != 'slit' else (255, 220, 60)
        er = 9 * u if eyes != 'crazy' else (11 * u if sx < 0 else 7 * u)
        pygame.draw.ellipse(surf, white, (ex - er, ey - er * 0.8, 2 * er, 1.6 * er))
        if eyes == 'slit':
            pygame.draw.ellipse(surf, (10, 10, 10), (ex - 2 * u, ey - er * 0.75, 4 * u, 1.5 * er))
        else:
            pr = 4 * u if eyes != 'crazy' else (5 * u if sx < 0 else 2.5 * u)
            pygame.draw.circle(surf, (15, 15, 25), (ex + math.sin(t * 2) * 2 * u, ey), int(pr))
        if eyes == 'angry' or eyes == 'slit':
            brow = [(ex - sx * 12 * u, ey - 14 * u), (ex + sx * 12 * u, ey - 6 * u)]
            pygame.draw.line(surf, mix(acc, (0, 0, 0), 0.3), brow[0], brow[1], max(2, int(4 * u)))

    # mouth (opens with the voice)
    m = max(0.0, min(1.0, mouth))
    style = spec.get('mouth', 'grin')
    my = cy + 20 * u
    mw = 34 * u
    mh = 4 * u + 26 * u * m
    rect = pygame.Rect(0, 0, int(mw), int(max(2, mh)))
    rect.center = (int(cx), int(my + mh / 3))
    if style == 'beak':
        top_pts = [(cx - 16 * u, my - 4 * u), (cx + 16 * u, my - 4 * u), (cx, my + 10 * u)]
        bot_pts = [(cx - 12 * u, my + 2 * u + mh * 0.6), (cx + 12 * u, my + 2 * u + mh * 0.6), (cx, my + 14 * u + mh * 0.6)]
        pygame.draw.polygon(surf, (40, 10, 10), [(cx - 14 * u, my), (cx + 14 * u, my), (cx, my + 12 * u + mh * 0.6)])
        pygame.draw.polygon(surf, (250, 190, 60), bot_pts)
        pygame.draw.polygon(surf, (255, 210, 80), top_pts)
        return
    pygame.draw.ellipse(surf, (40, 8, 12), rect)
    if m > 0.3:
        tongue = pygame.Rect(0, 0, int(mw * 0.5), int(mh * 0.4))
        tongue.midbottom = rect.midbottom
        pygame.draw.ellipse(surf, (200, 60, 80), tongue)
    if style == 'fangs':
        for sx in (-1, 1):
            fx = cx + sx * 10 * u
            pygame.draw.polygon(surf, (255, 255, 245), [(fx - 4 * u, rect.top), (fx + 4 * u, rect.top), (fx, rect.top + 10 * u)])
            pygame.draw.polygon(surf, (255, 255, 245), [(fx - 3 * u, rect.bottom), (fx + 3 * u, rect.bottom), (fx, rect.bottom - 7 * u)])
    elif style == 'teeth':
        n = 5
        for i in range(n):
            x = rect.left + (i + 0.5) * rect.width / n
            pygame.draw.rect(surf, (250, 250, 240), (x - 3 * u, rect.top, 6 * u, min(rect.height, 7 * u)))
    elif style == 'grin' and m < 0.3:
        pygame.draw.arc(surf, (40, 8, 12), (cx - 18 * u, my - 12 * u, 36 * u, 24 * u), math.pi * 1.1, math.pi * 1.9, max(2, int(3 * u)))

    if spec.get('smoke') and m > 0.25:
        for i in range(3):
            a = t * 3 + i * 2.1
            r = (4 + i * 3) * u * (0.5 + m)
            pygame.draw.circle(surf, (170, 170, 180), (cx + 30 * u + i * 10 * u, my - 10 * u - i * 8 * u + math.sin(a) * 3 * u), int(r), max(1, int(u)))
