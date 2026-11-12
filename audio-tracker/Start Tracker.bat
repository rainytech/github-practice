@echo off
title Audio Equipment Tracker
cd /d "%~dp0"

set "PY=py"
where py >nul 2>nul
if errorlevel 1 set "PY=python"

%PY% -m tracker %*
if errorlevel 1 (
  echo.
  echo The tracker stopped because of the problem shown above.
  echo Details are also saved in data\tracker.log
  echo.
  pause
)
