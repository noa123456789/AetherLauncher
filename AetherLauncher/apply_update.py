from __future__ import annotations
import sys, time, shutil
from pathlib import Path

def main():
    if len(sys.argv)<4: raise SystemExit("Usage: apply_update.py SOURCE INSTALL_DIR ARCHIVE")
    source=Path(sys.argv[1]).resolve()
    target=Path(sys.argv[2]).resolve()
    archive=Path(sys.argv[3]).resolve()
    # Give the launcher time to close before replacing files.
    time.sleep(2.5)
    for item in source.iterdir():
        dest=target/item.name
        if item.name in {"config.json",".minecraft"}: continue
        if item.is_dir():
            if dest.exists(): shutil.rmtree(dest)
            shutil.copytree(item,dest)
        else:
            shutil.copy2(item,dest)
    # Keep updater and downloaded archive available until the next launch.
    # The application config and game files live under APPDATA and are untouched.
    try: archive.unlink(missing_ok=True)
    except Exception: pass
    # Relaunch through start.bat on Windows, or main.py as a fallback.
    start=target/"start.bat"
    if start.exists():
        import subprocess
        subprocess.Popen(["cmd","/c",str(start)],cwd=str(target))
    else:
        import subprocess
        subprocess.Popen([sys.executable,str(target/"main.py")],cwd=str(target))

if __name__=="__main__":
    main()
