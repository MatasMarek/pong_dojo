"""Players: the built-in four and the ones G creates in the editor.

A player is a plain dict (saved as JSON in players/, see dojo/paths.py):
name, title, motto, colours, paddle pattern, avatar face, voice, taunt level, own lines,
and a brain: 'human', 'tygr' or 'drak' (+ skill 1-10 for a created bot).
"""
import json
import os
import re
import random

from dojo import paths
from dojo.bots import tygr, drak

DOJO = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(DOJO)
TAUNTS = os.path.join(DOJO, 'taunts')
PLAYERS_DIR = paths.PLAYERS_DIR

LEVELS = ['slušné', 'drsné', 'brutální']
LEVEL_FILE = {'slušné': '', 'drsné': '_drsne', 'brutální': '_brutalni'}
PATTERNS = ['plain', 'stripes', 'scales', 'flames', 'lightning', 'checker', 'dots']
PATTERN_CZ = {'plain': 'hladká', 'stripes': 'pruhy', 'scales': 'šupiny', 'flames': 'plameny',
              'lightning': 'blesky', 'checker': 'šachovnice', 'dots': 'puntíky'}
PALETTE = [(255, 140, 26), (40, 214, 160), (214, 224, 255), (255, 128, 170), (255, 70, 70), (255, 214, 102),
           (120, 200, 255), (170, 120, 255), (140, 230, 90), (255, 255, 255), (60, 64, 96), (24, 18, 14),
           (8, 44, 40), (90, 20, 30), (20, 30, 90), (255, 160, 60)]
SHAPES = ['round', 'square', 'long', 'triangle']
EYES = ['angry', 'calm', 'crazy', 'sleepy', 'slit']
MOUTHS = ['fangs', 'grin', 'teeth', 'beak']
TOPS = ['ears', 'horns', 'spikes', 'antennae', 'none']
MARKS = ['stripes', 'scales', 'spots', 'scar', 'none']
EFFECTS = ['žádný', 'vrčení', 'ozvěna', 'robot']
CZ = {'round': 'kulatá', 'square': 'hranatá', 'long': 'protáhlá', 'triangle': 'trojúhelník',
      'angry': 'naštvané', 'calm': 'klidné', 'crazy': 'šílené', 'sleepy': 'ospalé', 'slit': 'hadí',
      'fangs': 'tesáky', 'grin': 'úsměv', 'teeth': 'zuby', 'beak': 'zobák',
      'ears': 'uši', 'horns': 'rohy', 'spikes': 'bodliny', 'antennae': 'tykadla', 'none': 'nic',
      'stripes': 'pruhy', 'scales': 'šupiny', 'spots': 'skvrny', 'scar': 'jizva'}
BRAINS = ['human', 'tygr', 'drak']
BRAIN_CZ = {'human': 'člověk (klávesy)', 'tygr': 'bot, hraje jako TYGR', 'drak': 'bot, hraje jako DRAK'}

TYGR = dict(tygr.IDENTITY, id='tygr', brain='tygr', skill=10, level='brutální', lines=[],
            avatar={'shape': 'round', 'skin': (255, 140, 26), 'accent': (24, 18, 14), 'eyes': 'angry',
                    'mouth': 'fangs', 'top': 'ears', 'marks': 'stripes', 'muzzle': True},
            voice={'pitch': 0.86, 'effect': 'vrčení'}, base='tygr')
DRAK = dict(drak.IDENTITY, id='drak', brain='drak', skill=10, level='brutální', lines=[],
            avatar={'shape': 'long', 'skin': (40, 214, 160), 'accent': (255, 214, 102), 'eyes': 'slit',
                    'mouth': 'fangs', 'top': 'horns', 'marks': 'scales', 'smoke': True},
            voice={'pitch': 0.74, 'effect': 'ozvěna'}, base='drak')
HUMAN = {'id': 'human', 'name': 'HRÁČ', 'title': 'člověk', 'motto': 'Klávesy W/S nebo šipky.',
         'primary': (214, 224, 255), 'secondary': (54, 64, 96), 'glow': (150, 180, 255), 'paddle': 'plain',
         'brain': 'human', 'skill': 10, 'level': 'drsné', 'lines': [],
         'avatar': {'shape': 'round', 'skin': (240, 200, 170), 'accent': (60, 40, 30), 'eyes': 'calm',
                    'mouth': 'grin', 'top': 'none', 'marks': 'none'},
         'voice': {'pitch': 1.0, 'effect': 'žádný'}, 'base': 'obecne'}
HUMAN2 = dict(HUMAN, id='human2', name='HRÁČ 2', motto='Šipky nahoru a dolů.', primary=(255, 128, 170),
              secondary=(80, 30, 56), glow=(255, 160, 200),
              avatar=dict(HUMAN['avatar'], skin=(200, 150, 120), eyes='crazy', top='spikes'),
              voice={'pitch': 1.15, 'effect': 'žádný'})
BUILTIN = [TYGR, DRAK, HUMAN, HUMAN2]


def new_player():
    p = json.loads(json.dumps(HUMAN))  # deep copy
    p.update(id='', name='NOVÁČEK', title='nová hvězda', motto='Ještě mě neznáš.', primary=(255, 70, 70),
             secondary=(90, 20, 30), glow=(255, 214, 102), paddle='flames', brain='human', level='brutální')
    p['avatar'].update(skin=(255, 70, 70), accent=(255, 214, 102), eyes='angry', mouth='teeth', top='horns')
    return p


def _tuplify(p):
    for k in ('primary', 'secondary', 'glow'):
        if k in p:
            p[k] = tuple(p[k])
    for k in ('skin', 'accent'):
        if k in p.get('avatar', {}):
            p['avatar'][k] = tuple(p['avatar'][k])
    return p


def load_custom():
    out = []
    if not os.path.isdir(PLAYERS_DIR):
        return out
    for fn in sorted(os.listdir(PLAYERS_DIR)):
        if fn.endswith('.json'):
            try:
                with open(os.path.join(PLAYERS_DIR, fn), encoding='utf-8') as fh:
                    p = _tuplify(json.load(fh))
                p['id'] = fn[:-5]
                p.setdefault('base', 'obecne')
                out.append(p)
            except (OSError, ValueError):
                pass
    return out


def slug(name):
    s = name.lower()
    for a, b in zip('áčďéěíňóřšťúůýž', 'acdeeinorstuuyz'):
        s = s.replace(a, b)
    return re.sub(r'[^a-z0-9]+', '_', s).strip('_') or 'hrac'


def save_custom(p):
    os.makedirs(PLAYERS_DIR, exist_ok=True)
    pid = p.get('id') or slug(p['name'])
    if pid in ('tygr', 'drak', 'human', 'human2'):
        pid += '_vlastni'
    p['id'] = pid
    with open(os.path.join(PLAYERS_DIR, pid + '.json'), 'w', encoding='utf-8') as fh:
        json.dump(p, fh, ensure_ascii=False, indent=1)
    return pid


def delete_custom(pid):
    try:
        os.remove(os.path.join(PLAYERS_DIR, pid + '.json'))
    except OSError:
        pass


def roster():
    return BUILTIN + load_custom()


def _lines(fname):
    try:
        with open(os.path.join(TAUNTS, fname), encoding='utf-8') as fh:
            return [ln.strip() for ln in fh if ln.strip()]
    except OSError:
        return []


def stery():
    try:
        with open(os.path.join(REPO, 'stery.txt'), encoding='utf-8') as fh:
            return [ln.strip() for ln in fh if ln.strip()]
    except OSError:
        return []


def taunt_pool(p):
    """(text, source) pairs this player may shout, by its level. The friend's stery.txt
    sits in the 'drsné' and 'brutální' pools; a player's own typed lines always count."""
    base = p.get('base', 'obecne')
    level = p.get('level', 'drsné')
    own = [(t, p['name']) for t in p.get('lines', []) if t.strip()]
    pool = [(t, p['name']) for t in _lines(base + LEVEL_FILE[level] + '.txt')]
    if level != 'slušné':
        st = stery()
        k = len(pool) // 3 if level == 'brutální' else len(pool)
        pool += [(t, 'stery.txt') for t in random.Random(len(st)).sample(st, min(k, len(st)))]
    return own * 3 + pool if own else pool


def make_brain(p, seed, rules):
    """None for a human; otherwise a bot, with the skill handicap for created bots."""
    from dojo.contract import Handicap
    brain = p.get('brain', 'human')
    if brain == 'human':
        return None
    mod = tygr if brain == 'tygr' else drak
    bot = mod.make(seed, rules)
    skill = int(p.get('skill', 10))
    return bot if skill >= 10 else Handicap(bot, skill, seed)
