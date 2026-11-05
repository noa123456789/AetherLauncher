@echo off
cd /d "%~dp0"
py -3 -m pip install pyinstaller
py -3 -m PyInstaller --noconfirm --windowed --name AetherLauncher --collect-all minecraft_launcher_lib main.py
pause
