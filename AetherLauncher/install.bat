@echo off
title AetherLauncher Setup
cd /d "%~dp0"
py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt
if errorlevel 1 (echo Installatie mislukt. Controleer Python 3.11+ en internetverbinding.& pause & exit /b 1)
echo Installatie voltooid. Start met start.bat.
pause
