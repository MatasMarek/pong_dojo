@echo off
rem PONG DOJO arena - double-click, or run with options, e.g.  play.cmd --mode bots
rem Uses .venv inside this folder if it exists, otherwise the Python on PATH.
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" -m dojo.arena %*
) else (
  python -m dojo.arena %*
)
if errorlevel 1 pause
