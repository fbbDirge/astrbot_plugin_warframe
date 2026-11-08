"""Run native command diagnostics in an isolated host stub; no chat messages sent."""
import json
import os
from pathlib import Path
import subprocess
import sys

if __name__ == '__main__':
    environment=dict(os.environ,WF_SMOKE_LIVE='1')
    if sys.argv[1:]:environment['WF_SMOKE_QUERIES']=json.dumps(sys.argv[1:],ensure_ascii=False)
    raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).resolve().parents[1]/'tests/native_smoke.py')],env=environment))
