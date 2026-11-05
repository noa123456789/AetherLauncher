# AetherLauncher v0.4.1

Windows Minecraft launcher with GitHub release update checking.

## Install
1. Windows 10/11 and Python 3.11+.
2. Extract this folder.
3. Run install.bat, then start.bat.

## Updates
The launcher checks `https://api.github.com/repos/noa123456789/AetherLauncher/releases/latest`.
Publish a GitHub Release with a version tag such as `v0.4.2` and attach a ZIP containing `main.py`, `apply_update.py`, `start.bat`, `install.bat`, and the other launcher files in one application folder.
The launcher checks for a ZIP asset, downloads it, validates ZIP structure and GitHub's SHA-256 digest when supplied, then starts a helper updater to replace application files. User config and Minecraft game files under `%APPDATA%\AetherLauncher` are kept.
