#!/bin/sh
# PONG DOJO arena - run with options, e.g.  ./play.sh --mode bots
# Uses .venv inside this folder if it exists, otherwise python3 on PATH.
cd "$(dirname "$0")" || exit 1
if [ -x .venv/bin/python ]; then
  exec .venv/bin/python -m dojo.arena "$@"
else
  exec python3 -m dojo.arena "$@"
fi
