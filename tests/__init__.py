
import tempfile
from pathlib import Path
# Windows managed sessions can expose an unwritable OS temp directory.
_root=Path(__file__).resolve().parents[1]
_temp=_root / 'data' / 'test_tmp'
assert _temp.resolve().is_relative_to(_root)
_temp.mkdir(parents=True,exist_ok=True)
tempfile.tempdir=str(_temp)
