"""Where the arena keeps its files.

By default everything lives inside this repository, so a fresh clone is self-contained:
  players/        created players (JSON, one file each)
  .voice_cache/   pre-rendered voice lines (WAV); new lines are rendered here on Windows
  rules.json      the rules you used last (local, not in git)
  rules.default.json  the rules a fresh clone starts with (Originál 2022)
  arena.json      per-PC settings such as fullscreen (local, not in git)
  shots/          screenshots (F12) and recordings (local, not in git)

Set the environment variable PONG_DOJO_HOME to keep players, voices, settings and shots
in another folder instead (the default rules still come from the repository).
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.environ.get('PONG_DOJO_HOME') or REPO

PLAYERS_DIR = os.path.join(HOME, 'players')
VOICE_CACHE = os.path.join(HOME, '.voice_cache')
RULES_FILE = os.path.join(HOME, 'rules.json')
RULES_DEFAULT = os.path.join(REPO, 'rules.default.json')
SETTINGS = os.path.join(HOME, 'arena.json')
SHOTS_DIR = os.path.join(HOME, 'shots')
