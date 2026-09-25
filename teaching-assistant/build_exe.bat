@echo off
cd /d "%~dp0"
if not exist .venv py -3 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt pyinstaller
.venv\Scripts\python -m PyInstaller --noconfirm --onefile --windowed --name TeachMark --collect-all winrt app.py
echo.
echo Done. Your app is: dist\TeachMark.exe
pause
