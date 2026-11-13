"""Create a clean handover archive without local databases, caches or credentials."""
import sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
output=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/"NEXUS_Implemented.zip"
output.parent.mkdir(parents=True,exist_ok=True)
excluded={"__pycache__",".venv",".git",".pytest_cache","test_tmp"}
files=[p for p in ROOT.rglob("*") if p.is_file() and not any(part in excluded for part in p.relative_to(ROOT).parts)
       and p.name not in {".env","secrets.toml"} and not p.name.endswith((".sqlite3",".sqlite3-journal",".sqlite3-wal",".sqlite3-shm",".pyc"))]
with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files):
        z.write(p,"NEXUS/"+p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(output) as z:
    bad=z.testzip()
    if bad:raise RuntimeError("Archive validation failed: "+bad)
print(str(output.resolve()))
print(f"{len(files)} files; {output.stat().st_size} bytes; ZIP integrity check passed")

