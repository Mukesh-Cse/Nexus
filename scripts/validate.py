"""Run deterministic tests and publish machine-readable evidence."""
import sys,unittest,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nexus.core.evaluation import evaluate
from nexus.models import utcnow
suite=unittest.defaultTestLoader.discover(str(ROOT/"tests"),top_level_dir=str(ROOT))
start=time.perf_counter()
result=unittest.TextTestRunner(verbosity=2).run(suite)
report={"executed_at":utcnow(),"runner":"unittest (pytest-compatible suite)","tests_run":result.testsRun,
 "failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),
 "duration_seconds":round(time.perf_counter()-start,2),"successful":result.wasSuccessful(),
 "live_integrations":"Not included; run scripts/live_check.py separately.",
 "evaluation":evaluate()}
(ROOT/"docs").mkdir(exist_ok=True)
(ROOT/"docs"/"validation_results.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
sys.exit(0 if result.wasSuccessful() else 1)

