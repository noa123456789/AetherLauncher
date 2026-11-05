from __future__ import annotations
import sys, os, json, uuid, subprocess, threading, traceback, re, shutil, urllib.request
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QObject, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import *

APP_NAME = "AetherLauncher"
BASE = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
GAME_DIR = BASE / ".minecraft"
CONFIG = BASE / "config.json"
DEFAULT = {"version":"26.3","ram":6,"java_path":"","username":"Player",
           "server_name":"AetherSMP","server_host":"aethersmp.playit.plus","server_port":25565,
           "theme":"dark"}

def read_config():
    try: data=json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception: data={}
    return {**DEFAULT, **data}

def save_config(data):
    BASE.mkdir(parents=True,exist_ok=True)
    CONFIG.write_text(json.dumps(data,indent=2),encoding="utf-8")

def find_java(explicit=""):
    candidates=[explicit, shutil.which("java"), r"C:\Program Files\Java\jdk-25\bin\java.exe",
                r"C:\Program Files\Eclipse Adoptium\jdk-25\bin\java.exe",
                r"C:\Program Files\Microsoft\jdk-25\bin\java.exe"]
    for c in candidates:
        if c and (Path(c).is_file() or shutil.which(c)):
            return c
    return "java"

def java_major(executable):
    try:
        p=subprocess.run([executable,"-version"],capture_output=True,text=True,timeout=8)
        s=p.stderr+" "+p.stdout
        m=re.search(r'version "(\d+)',s)
        return int(m.group(1)) if m else None
    except Exception:
        return None

class Signals(QObject):
    log=Signal(str); progress=Signal(int); finished=Signal(bool,str)
class BackgroundTask:
    def __init__(self,fn):
        self.fn=fn; self.signals=Signals()
    def start(self):
        def worker():
            try: self.signals.finished.emit(True,str(self.fn(self.signals.log.emit,self.signals.progress.emit) or "Klaar"))
            except Exception as e:
                self.signals.log.emit(traceback.format_exc())
                self.signals.finished.emit(False,str(e))
        threading.Thread(target=worker,daemon=True).start()

class Launcher(QMainWindow):
    def __init__(self):
        super().__init__()
        BASE.mkdir(parents=True,exist_ok=True)
        self.cfg=read_config(); self.task=None
        self.setWindowTitle("AetherLauncher")
        self.setMinimumSize(1080,700); self.resize(1280,820)
        self.setStyleSheet("""
        QWidget{font-family:'Segoe UI';color:#f4f1ff;background:#0b0b12;font-size:13px}
        QFrame#sidebar{background:#10101a;border-right:1px solid #252337}
        QLabel#brand{font-size:25px;font-weight:900;color:#c5a7ff;letter-spacing:2px}
        QLabel#muted{color:#9693aa}
        QLabel#pageTitle{font-size:29px;font-weight:800;color:#fff}
        QLabel#section{font-size:16px;font-weight:750;color:#f4f1ff}
        QFrame#panel{background:#151522;border:1px solid #29283d;border-radius:17px}
        QFrame#hero{background:#201a35;border:1px solid #4a386c;border-radius:22px}
        QPushButton{background:#211f30;border:1px solid #37334d;border-radius:10px;padding:11px 15px;font-weight:650}
        QPushButton:hover{background:#302744;border-color:#a887ff}
        QPushButton#primary{background:#895cf6;border:0;color:white;font-size:15px;font-weight:800;padding:15px 20px}
        QPushButton#primary:hover{background:#a078ff}
        QPushButton#nav{background:transparent;border:0;text-align:left;padding:14px 15px;color:#aaa6bd;font-size:14px}
        QPushButton#nav:checked{background:#28213a;color:#d5c1ff;border-left:3px solid #a27aff}
        QLineEdit,QComboBox,QSpinBox{background:#0e0e18;border:1px solid #343149;border-radius:9px;padding:10px;color:#fff;selection-background-color:#895cf6}
        QTextEdit{background:#090910;border:1px solid #29283d;border-radius:10px;color:#b9e8c5;font-family:Consolas;font-size:12px;padding:8px}
        QProgressBar{background:#0e0e18;border:0;border-radius:5px;height:9px;text-align:center}
        QProgressBar::chunk{background:#9b75ff;border-radius:5px}
        QScrollBar:vertical{background:#10101a;width:8px} QScrollBar::handle:vertical{background:#40365c;border-radius:4px}
        """)
        central=QWidget(); self.setCentralWidget(central)
        outer=QHBoxLayout(central); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        side=QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(232)
        sv=QVBoxLayout(side); sv.setContentsMargins(18,27,18,20); sv.setSpacing(7)
        brand=QLabel("✦ AETHER"); brand.setObjectName("brand"); sv.addWidget(brand)
        tagline=QLabel("MINECRAFT LAUNCHER"); tagline.setObjectName("muted"); sv.addWidget(tagline)
        sv.addSpacing(34)
        self.stack=QStackedWidget(); self.nav=[]
        for name,ico in [("Home","⌂"),("Minecraft Java","◈"),("Bedrock","▣"),("Instellingen","⚙")]:
            b=QPushButton(f"{ico}    {name}"); b.setObjectName("nav"); b.setCheckable(True)
            b.clicked.connect(lambda checked=False,n=name:self.navigate(n))
            sv.addWidget(b); self.nav.append(b)
        sv.addStretch()
        divider=QFrame(); divider.setFrameShape(QFrame.HLine); divider.setStyleSheet("color:#28263a"); sv.addWidget(divider)
        self.profile_label=QLabel(); self.profile_label.setObjectName("muted"); self.profile_label.setWordWrap(True); sv.addWidget(self.profile_label)
        outer.addWidget(side)
        content=QWidget(); cv=QVBoxLayout(content); cv.setContentsMargins(0,0,0,0); cv.setSpacing(0)
        top=QFrame(); top.setFixedHeight(62); top.setStyleSheet("background:#0e0e17;border-bottom:1px solid #252337")
        tl=QHBoxLayout(top); tl.setContentsMargins(28,0,28,0)
        self.top_status=QLabel("●  READY"); self.top_status.setStyleSheet("color:#7fe0a0;font-weight:800")
        tl.addWidget(self.top_status); tl.addStretch()
        self.top_version=QLabel("JAVA EDITION  •  26.3"); self.top_version.setObjectName("muted"); tl.addWidget(self.top_version)
        cv.addWidget(top); cv.addWidget(self.stack,1); outer.addWidget(content,1)
        self.stack.addWidget(self.home_page()); self.stack.addWidget(self.java_page())
        self.stack.addWidget(self.bedrock_page()); self.stack.addWidget(self.settings_page())
        self.nav[0].setChecked(True); self.update_profile()
        self.statusBar().showMessage("AetherLauncher • Klaar")

    def panel(self):
        f=QFrame(); f.setObjectName("panel"); return f
    def heading(self,title,sub):
        box=QVBoxLayout(); a=QLabel(title); a.setObjectName("pageTitle"); b=QLabel(sub); b.setObjectName("muted")
        box.addWidget(a); box.addWidget(b); return box
    def home_page(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(34,27,34,25); l.setSpacing(19)
        l.addLayout(self.heading("Welkom terug.","Alles klaar voor je volgende avontuur?"))
        hero=QFrame(); hero.setObjectName("hero"); h=QHBoxLayout(hero); h.setContentsMargins(30,27,30,27)
        left=QVBoxLayout(); tag=QLabel("✦  AETHERSMP NETWORK"); tag.setStyleSheet("color:#c4a8ff;font-weight:800;letter-spacing:1px")
        title=QLabel("Jouw wereld.\nJouw avontuur."); title.setStyleSheet("font-size:37px;font-weight:900;line-height:1.2")
        desc=QLabel("Start Minecraft Java 26.3 en spring direct naar AetherSMP."); desc.setObjectName("muted")
        self.home_play=QPushButton("▶   SPEEL NU"); self.home_play.setObjectName("primary"); self.home_play.clicked.connect(self.launch_java)
        left.addWidget(tag); left.addSpacing(8); left.addWidget(title); left.addWidget(desc); left.addSpacing(17); left.addWidget(self.home_play,0,Qt.AlignLeft); left.addStretch()
        right=QVBoxLayout(); emblem=QLabel("✦"); emblem.setAlignment(Qt.AlignCenter); emblem.setStyleSheet("font-size:150px;color:#b99aff;background:#2b2143;border:1px solid #584477;border-radius:24px")
        right.addWidget(emblem); h.addLayout(left,3); h.addLayout(right,2); l.addWidget(hero,3)
        row=QHBoxLayout()
        for label,value,sub in [("GAME VERSION","26.3","Latest stable release"),("PROFILE",self.cfg["username"],"Offline Java profile"),("SERVER",self.cfg["server_name"],self.cfg["server_host"])]:
            c=self.panel(); v=QVBoxLayout(c); v.setContentsMargins(18,15,18,15)
            a=QLabel(label); a.setObjectName("muted"); b=QLabel(value); b.setStyleSheet("font-size:19px;font-weight:800"); d=QLabel(sub); d.setObjectName("muted")
            v.addWidget(a); v.addWidget(b); v.addWidget(d); row.addWidget(c)
        l.addLayout(row)
        activity=QLabel("RECENTE ACTIVITEIT"); activity.setObjectName("section"); l.addWidget(activity)
        self.logs=QTextEdit(); self.logs.setReadOnly(True); self.logs.setMaximumHeight(125); l.addWidget(self.logs)
        self.progress=QProgressBar(); self.progress.setRange(0,100); self.progress.setValue(0); l.addWidget(self.progress)
        self.log("AetherLauncher is gestart. Minecraft 26.3 staat geselecteerd.")
        return w

    def java_page(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(34,27,34,25); l.setSpacing(18)
        l.addLayout(self.heading("Minecraft Java","Beheer je versie, profiel en game-installatie."))
        c=self.panel(); f=QFormLayout(c); f.setContentsMargins(24,22,24,22); f.setVerticalSpacing(17)
        self.version=QComboBox(); self.version.setEditable(True)
        self.version.addItems(["26.3","26.2","26.1.2","26.1.1","26.1","1.21.11","1.21.10","1.21.9","1.21.8"])
        self.version.setCurrentText(self.cfg.get("version","26.3")); f.addRow("Minecraft-versie",self.version)
        self.username=QLineEdit(self.cfg.get("username","Player")); self.username.setMaxLength(16); f.addRow("Spelersnaam",self.username)
        self.install_btn=QPushButton("↓   DOWNLOAD / REPAREREN"); self.install_btn.clicked.connect(self.install_java); f.addRow("",self.install_btn)
        self.play_btn=QPushButton("▶   START MINECRAFT"); self.play_btn.setObjectName("primary"); self.play_btn.clicked.connect(self.launch_java); f.addRow("",self.play_btn)
        l.addWidget(c)
        note=self.panel(); nv=QVBoxLayout(note); nv.setContentsMargins(22,18,22,18)
        nt=QLabel("BELANGRIJK • JAVA 25"); nt.setStyleSheet("color:#c7a9ff;font-weight:900")
        nd=QLabel("Minecraft 26.3 vereist Java 25 of nieuwer. De launcher controleert dit voordat de game start. Java wordt niet stilzwijgend vervangen.")
        nd.setWordWrap(True); nd.setObjectName("muted"); nv.addWidget(nt); nv.addWidget(nd); l.addWidget(note)
        l.addStretch(); return w

    def bedrock_page(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(34,27,34,25); l.addLayout(self.heading("Minecraft Bedrock","Open de officiële Minecraft for Windows-app."))
        c=self.panel(); v=QVBoxLayout(c); v.setContentsMargins(24,24,24,24)
        t=QLabel("BEDROCK EDITION"); t.setStyleSheet("font-size:23px;font-weight:850")
        d=QLabel("AetherLauncher opent de Bedrock-app die via Microsoft Store/Xbox is geïnstalleerd. Je Microsoft-account en aankoop blijven bij Microsoft.")
        d.setWordWrap(True); d.setObjectName("muted")
        b=QPushButton("OPEN MINECRAFT BEDROCK"); b.setObjectName("primary"); b.clicked.connect(self.launch_bedrock)
        s=QPushButton("OPEN MICROSOFT STORE"); s.clicked.connect(lambda:os.startfile("ms-windows-store://pdp/?productid=9NBLGGH2JHXJ"))
        v.addWidget(t); v.addWidget(d); v.addSpacing(12); v.addWidget(b); v.addWidget(s); l.addWidget(c); l.addStretch(); return w

    def settings_page(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(34,27,34,25); l.addLayout(self.heading("Instellingen","Stel je profiel en serververbinding in."))
        c=self.panel(); f=QFormLayout(c); f.setContentsMargins(24,22,24,22); f.setVerticalSpacing(15)
        self.username_settings=QLineEdit(self.cfg.get("username","Player")); self.username_settings.setMaxLength(16); f.addRow("Offline spelersnaam",self.username_settings)
        self.ram=QSpinBox(); self.ram.setRange(2,64); self.ram.setValue(int(self.cfg.get("ram",6))); self.ram.setSuffix(" GB"); f.addRow("RAM voor Minecraft",self.ram)
        self.java=QLineEdit(self.cfg.get("java_path","")); self.java.setPlaceholderText("Automatisch zoeken")
        choose=QPushButton("Bladeren…"); choose.clicked.connect(self.choose_java)
        java_row=QHBoxLayout(); java_row.addWidget(self.java,1); java_row.addWidget(choose); f.addRow("Java 25 executable",java_row)
        self.host=QLineEdit(self.cfg.get("server_host","")); f.addRow("AetherSMP-adres",self.host)
        self.port=QSpinBox(); self.port.setRange(1,65535); self.port.setValue(int(self.cfg.get("server_port",25565))); f.addRow("Serverpoort",self.port)
        save=QPushButton("OPSLAAN"); save.setObjectName("primary"); save.clicked.connect(self.save_settings); f.addRow("",save)
        l.addWidget(c)
        warning=QLabel("Offline profiel werkt uitsluitend op servers met online-mode=false. Namen zijn niet centraal geverifieerd; gebruik serverauthenticatie zoals AuthMeReloaded.")
        warning.setWordWrap(True); warning.setStyleSheet("color:#e9bd78;padding:8px"); l.addWidget(warning); l.addStretch(); return w

    def navigate(self,name):
        idx={"Home":0,"Minecraft Java":1,"Bedrock":2,"Instellingen":3}[name]
        self.stack.setCurrentIndex(idx)
        for i,b in enumerate(self.nav): b.setChecked(i==idx)
    def log(self,msg):
        if hasattr(self,"logs"): self.logs.append(str(msg))
    def update_profile(self):
        self.profile_label.setText(f"◉  {self.cfg.get('username','Player')}\\nOffline Java profile")
    def choose_java(self):
        p,_=QFileDialog.getOpenFileName(self,"Kies Java 25","", "Java executable (java.exe)")
        if p: self.java.setText(p)
    def save_settings(self):
        name=self.username.text().strip() if hasattr(self,"username") else self.username_settings.text().strip()
        if not re.fullmatch(r"[A-Za-z0-9_]{3,16}",name):
            QMessageBox.warning(self,"Ongeldige naam","Gebruik 3–16 letters, cijfers of underscores."); return
        self.username.setText(name); self.username_settings.setText(name)
        self.cfg.update(username=name,ram=self.ram.value(),java_path=self.java.text().strip(),
                        server_host=self.host.text().strip(),server_port=self.port.value(),
                        version=self.version.currentText().strip())
        save_config(self.cfg); self.update_profile(); self.statusBar().showMessage("Instellingen opgeslagen",4000)
        self.log("Instellingen opgeslagen.")
    def run_task(self,fn,button):
        button.setEnabled(False); self.top_status.setText("●  BEZIG…"); self.top_status.setStyleSheet("color:#f1c66d;font-weight:800")
        self.progress.setRange(0,0)
        task=BackgroundTask(fn); self.task=task
        task.signals.log.connect(self.log); task.signals.progress.connect(self.progress.setValue)
        def done(ok,msg):
            button.setEnabled(True); self.progress.setRange(0,100); self.progress.setValue(100 if ok else 0)
            self.top_status.setText("●  READY" if ok else "●  ERROR")
            self.top_status.setStyleSheet("color:#7fe0a0;font-weight:800" if ok else "color:#ff8585;font-weight:800")
            self.statusBar().showMessage(msg,10000); self.log(("✓ " if ok else "✕ ")+msg)
            if not ok: QMessageBox.critical(self,"AetherLauncher",msg)
        task.signals.finished.connect(done); task.start()
    def install_java(self):
        version=self.version.currentText().strip()
        if not version: return
        self.cfg["version"]=version; save_config(self.cfg)
        def work(log,progress):
            log(f"Minecraft Java {version} downloaden/controleren…")
            try: import minecraft_launcher_lib as mll
            except Exception as e: raise RuntimeError("minecraft-launcher-lib ontbreekt. Voer install.bat opnieuw uit.") from e
            def status(s): log(s)
            def set_progress(v): progress(int(v))
            mll.install.install_minecraft_version(version,str(GAME_DIR),
                callback={"setStatus":status,"setProgress":set_progress,"setMax":lambda m:None})
            return f"Minecraft Java {version} is geïnstalleerd."
        self.run_task(work,self.install_btn)
    def launch_java(self):
        self.save_settings()
        username=self.cfg["username"]; version=self.version.currentText().strip()
        java=find_java(self.cfg.get("java_path",""))
        major=java_major(java)
        required=25 if version.startswith("26.") else (21 if version.startswith("1.21.") else 17)
        if major is None or major < required:
            QMessageBox.warning(self,"Java-versie te oud",
                f"Minecraft {version} vereist Java {required} of nieuwer.\\n\\nGevonden Java: {major or 'niet gevonden'}\\n\\nInstalleer Java {required} en stel eventueel java.exe in bij Instellingen.")
            return
        def work(log,progress):
            import minecraft_launcher_lib as mll
            log(f"Controleren van Minecraft {version}…")
            mll.install.install_minecraft_version(version,str(GAME_DIR))
            raw=__import__("hashlib").md5(("OfflinePlayer:"+username).encode("utf-8")).digest()
            offline_uuid=str(uuid.UUID(bytes=raw,version=3))
            options={"username":username,"uuid":offline_uuid,"token":"","executablePath":java,
                     "jvmArguments":[f"-Xmx{self.cfg['ram']}G","-Xms1G"],
                     "server":self.cfg["server_host"],"port":str(self.cfg["server_port"])}
            log(f"Starten van {version} met Java {major}…")
            command=mll.command.get_minecraft_command(version,str(GAME_DIR),options)
            subprocess.Popen(command,cwd=str(GAME_DIR))
            return f"Minecraft {version} gestart."
        self.run_task(work,self.play_btn)
    def launch_bedrock(self):
        try: os.startfile("minecraft://")
        except Exception as e: QMessageBox.warning(self,"Bedrock niet gevonden",
            "Windows kon Minecraft Bedrock niet openen. Installeer Minecraft for Windows via Microsoft Store.\\n\\n"+str(e))

if __name__=="__main__":
    app=QApplication(sys.argv); app.setApplicationName(APP_NAME)
    win=Launcher(); win.show(); sys.exit(app.exec())
