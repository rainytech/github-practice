@echo off
cd /d "%~dp0"
if not exist .venv py -3 -m venv .venv
fc /b requirements.txt .venv\installed.txt >nul 2>&1 || (
  echo Installing / updating TeachMark - please wait, do not close this window...
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\python -m pip install -r requirements.txt && copy /y requirements.txt .venv\installed.txt >nul
)
start "" .venv\Scripts\pythonw app.py
