"""Render entrypoint. No shell expansion required; uses the platform PORT."""
import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def command(env=None):
    env=os.environ if env is None else env
    port=int(env.get("PORT","10000"))
    if not 1<=port<=65535:
        raise ValueError("PORT must be between 1 and 65535")
    return [sys.executable,"-m","streamlit","run",str(ROOT/"app.py"),
            "--server.address=0.0.0.0",f"--server.port={port}",
            "--server.headless=true","--server.fileWatcherType=none",
            "--browser.gatherUsageStats=false"]
if __name__=="__main__":
    os.chdir(ROOT)
    os.execv(sys.executable,command())

